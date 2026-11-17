"""Streaming algorithms on the captured stream, each checked against the exact answer (rubric: streaming algorithms; E4).

The stream is the page-change events of enwiki in publish order (meta_dt, then meta_id), from
2026-10-19 23:00 UTC to the end of 2026-11-13 (lake_config.EXT_AS_OF). One pass, constant memory per sketch.

  1. HyperLogLog (p = 10, 12, 14) and Flajolet-Martin PCSA (m = 64, 256, 1024) for distinct editors and distinct
     pages; also one HLL per day, merged, against the exact union. Spark's approx_count_distinct (HLL++) beside them.
  2. Bloom filter on meta_id over the RAW Bronze stream (duplicates included), against the exact repeats that the
     Silver insert-only MERGE removed: true repeats found, false positives, memory, for two sizes.
  3. DGIM (time-based window of 1 h, r = 2 and r = 4 buckets per size): reverts in the last hour, wiki-wide and per
     page, against the exact count, at every 10-minute mark.
  4. Reservoir sampling (k = 10,000) of edits: revert-event share of the sample against the exact share.
  5. AMS (Alon-Matias-Szegedy) estimate of the second moment F2 of edits per page, against the exact F2.

Memory is the sketch's own size in bytes (registers, bits, buckets); the exact answer's memory is estimated as
8 bytes per distinct 64-bit hash (a lower bound for a hash set). These are estimates and are labeled so.

Run
    python -m etl.streaming_algos            # writes data/lake/_runs/streaming_algos.json
"""
from __future__ import annotations

import hashlib
import json
import math
import sys
import time
from collections import defaultdict, deque

import numpy as np
import pyarrow as pa
import pyarrow.compute as pc

from . import delta_io, lake_config, tables
from .hw2 import config

SEED = 226
EVAL_EVERY_S = 600
WINDOW_S = 3600


# ------------------------------------------------------------------ hashing
SALTS = ["", "a", "b", "c", "d"]     # 5 independent hash functions: each sketch is run 5 times


def hash64(values, salt: str = "") -> np.ndarray:
    """64-bit hash of each value (blake2b of salt + its text). Same input -> same hash in every run."""
    out = np.empty(len(values), dtype=np.uint64)
    for i, v in enumerate(values):
        out[i] = int.from_bytes(hashlib.blake2b((salt + str(v)).encode(), digest_size=8).digest(), "little")
    return out


def rho(w: np.ndarray, bits: int) -> np.ndarray:
    """Position of the first 1-bit (1-based) in the top `bits` bits of w; bits + 1 when they are all 0."""
    w = w.astype(np.uint64)
    out = np.full(w.shape, bits + 1, dtype=np.int64)
    found = np.zeros(w.shape, dtype=bool)
    for k in range(bits):
        bit = (w >> np.uint64(63 - k)) & np.uint64(1)
        hit = (bit == 1) & ~found
        out[hit] = k + 1
        found |= hit
    return out


# ------------------------------------------------------------------ HyperLogLog
class HLL:
    def __init__(self, p: int):
        self.p, self.m = p, 1 << p
        self.reg = np.zeros(self.m, dtype=np.uint8)

    def add_hashes(self, h: np.ndarray) -> None:
        idx = (h >> np.uint64(64 - self.p)).astype(np.int64)
        w = h << np.uint64(self.p)
        r = rho(w, 64 - self.p).astype(np.uint8)
        np.maximum.at(self.reg, idx, r)

    def merge(self, other: "HLL") -> None:
        np.maximum(self.reg, other.reg, out=self.reg)

    def estimate(self) -> float:
        m = self.m
        alpha = 0.7213 / (1 + 1.079 / m)
        e = alpha * m * m / np.sum(2.0 ** -self.reg.astype(np.float64))
        zeros = int(np.sum(self.reg == 0))
        if e <= 2.5 * m and zeros:
            e = m * math.log(m / zeros)            # small-range correction (linear counting)
        return float(e)

    def bytes(self) -> int:
        return math.ceil(self.m * 6 / 8)           # 6-bit registers


# ------------------------------------------------------------------ Flajolet-Martin (PCSA)
class PCSA:
    """Probabilistic counting with stochastic averaging (Flajolet & Martin 1985): m bitmaps of 32 bits."""

    def __init__(self, m: int):
        self.m = m
        self.bitmaps = np.zeros(m, dtype=np.uint64)

    def add_hashes(self, h: np.ndarray) -> None:
        idx = (h % np.uint64(self.m)).astype(np.int64)
        w = h // np.uint64(self.m)
        # r = number of trailing zeros of w (FM's rho), capped at 31
        r = np.zeros(len(w), dtype=np.int64)
        x = w.copy()
        alive = np.ones(len(w), dtype=bool)
        for _ in range(31):
            z = alive & ((x & np.uint64(1)) == 0)
            r[z] += 1
            alive &= z
            x >>= np.uint64(1)
        np.bitwise_or.at(self.bitmaps, idx, (np.uint64(1) << r.astype(np.uint64)))

    def estimate(self) -> float:
        R = np.zeros(self.m)
        for i, b in enumerate(self.bitmaps):
            b = int(b)
            k = 0
            while b & (1 << k):
                k += 1
            R[i] = k
        return float(self.m / 0.77351 * 2 ** R.mean())

    def bytes(self) -> int:
        return self.m * 4


# ------------------------------------------------------------------ Bloom filter
class Bloom:
    def __init__(self, n_expected: int, fp_rate: float):
        self.m = int(math.ceil(-n_expected * math.log(fp_rate) / math.log(2) ** 2))
        self.k = max(1, round(self.m / n_expected * math.log(2)))
        self.bits = np.zeros((self.m + 7) // 8, dtype=np.uint8)

    def _positions(self, key: str) -> list[int]:
        d = hashlib.blake2b(key.encode(), digest_size=16).digest()
        h1, h2 = int.from_bytes(d[:8], "little"), int.from_bytes(d[8:], "little") | 1
        return [(h1 + i * h2) % self.m for i in range(self.k)]          # Kirsch-Mitzenmacher double hashing

    def check_and_add(self, key: str) -> bool:
        """True when the key was probably seen before. Adds it."""
        seen = True
        for p in self._positions(key):
            byte, bit = p >> 3, 1 << (p & 7)
            if not self.bits[byte] & bit:
                seen = False
                self.bits[byte] |= bit
        return seen

    def bytes(self) -> int:
        return len(self.bits)


# ------------------------------------------------------------------ DGIM (time-based window)
class DGIM:
    """Datar-Gionis-Indyk-Motwani count of 1s in the last WINDOW seconds. Buckets: (newest 1's time, size)."""

    def __init__(self, window_s: int, r: int = 2):
        self.w, self.r = window_s, r
        self.buckets: deque = deque()              # newest first

    def add_one(self, t: float) -> None:
        self.buckets.appendleft((t, 1))
        size = 1
        while True:
            same = [i for i, b in enumerate(self.buckets) if b[1] == size]
            if len(same) <= self.r:
                break
            i, j = same[-2], same[-1]                # the two oldest of this size: merge, keep the newer time
            t_new = self.buckets[i][0]
            del self.buckets[j]
            self.buckets[i] = (t_new, size * 2)
            size *= 2

    def expire(self, now: float) -> None:
        while self.buckets and self.buckets[-1][0] <= now - self.w:
            self.buckets.pop()

    def count(self, now: float) -> float:
        self.expire(now)
        if not self.buckets:
            return 0.0
        total = sum(b[1] for b in self.buckets)
        return total - self.buckets[-1][1] / 2      # half of the oldest bucket

    def n_buckets(self) -> int:
        return len(self.buckets)


# ------------------------------------------------------------------ data
def load_stream(as_of: str = lake_config.EXT_AS_OF):
    path = tables.SILVER["page_change"].path()
    q = f"""SELECT meta_id, meta_dt, page_id, user_name, user_id, kind, revert_method
            FROM t WHERE wiki_id = 'enwiki' AND meta_dt <= '{as_of.replace('T', ' ').replace('Z', '')}'"""
    t = delta_io.sql(path, q)
    t = t.sort_by([("meta_dt", "ascending"), ("meta_id", "ascending")])
    return t


def run() -> dict:
    t0 = time.time()
    res = {"as_of": lake_config.EXT_AS_OF, "seed": SEED}
    t = load_stream()
    n = t.num_rows
    meta_dt = pc.cast(t.column("meta_dt"), pa.int64()).to_numpy() / 1e6
    page = t.column("page_id").to_numpy(zero_copy_only=False)
    user = np.array([f"{a}|{b}" for a, b in zip(t.column("user_id").to_pylist(), t.column("user_name").to_pylist())],
                    dtype=object)
    kind = t.column("kind").to_pylist()
    is_revert = np.array([m is not None for m in t.column("revert_method").to_pylist()])
    res["stream"] = {"events": n, "first": str(t.column("meta_dt")[0]), "last": str(t.column("meta_dt")[n - 1]),
                     "revert_events": int(is_revert.sum())}

    # ---- 1. distinct counts ----
    hp, hu = hash64(page), hash64(user)
    exact = {"pages": int(len(np.unique(hp))), "editors": int(len(np.unique(hu)))}
    res["exact_distinct"] = exact
    res["exact_check_python"] = {"pages": int(len(set(page.tolist()))), "editors": int(len(set(user.tolist())))}
    rows = []
    hashes = {("pages", ""): hp, ("editors", ""): hu}
    for salt in SALTS[1:]:
        hashes[("pages", salt)] = hash64(page, salt)
        hashes[("editors", salt)] = hash64(user, salt)
    makers = [(f"HLL p={p}", (lambda p=p: HLL(p)), 1.04 / math.sqrt(1 << p)) for p in (10, 12, 14)] + \
             [(f"FM-PCSA m={m}", (lambda m=m: PCSA(m)), 0.78 / math.sqrt(m)) for m in (64, 256, 1024)]
    for what in ("pages", "editors"):
        for name, make, se in makers:
            errs, first = [], None
            for salt in SALTS:
                sk = make()
                sk.add_hashes(hashes[(what, salt)])
                e = sk.estimate()
                first = first if first is not None else (e, sk.bytes())
                errs.append(100 * (e - exact[what]) / exact[what])
            rows.append({"item": what, "sketch": name, "estimate_salt0": round(first[0]), "exact": exact[what],
                         "rel_error_salt0_pct": round(errs[0], 3), "mean_rel_error_5_salts_pct": round(float(np.mean(errs)), 3),
                         "sd_rel_error_5_salts_pct": round(float(np.std(errs, ddof=1)), 3),
                         "max_abs_error_5_salts_pct": round(float(np.max(np.abs(errs))), 3),
                         "theory_se_pct": round(100 * se, 2), "sketch_bytes": first[1], "exact_bytes_est": 8 * exact[what]})
    res["distinct"] = rows

    # per-day HLL sketches merged = union over the period (mergeability)
    day = (meta_dt // 86400).astype(np.int64)
    merged = HLL(12)
    per_day = []
    for d in np.unique(day):
        sel = day == d
        s = HLL(12)
        s.add_hashes(hu[sel])
        per_day.append({"day": str(np.datetime64(int(d), "D")), "editors_exact": int(len(np.unique(hu[sel]))),
                        "editors_hll12": round(s.estimate())})
        merged.merge(s)
    res["editors_per_day"] = per_day
    res["editors_merged_daily_hll12"] = {"estimate": round(merged.estimate()), "exact": exact["editors"],
                                         "rel_error_pct": round(100 * (merged.estimate() - exact["editors"]) / exact["editors"], 3),
                                         "sum_of_daily_exact": int(sum(r["editors_exact"] for r in per_day))}

    # ---- 2. Bloom filter on meta_id over the raw Bronze stream ----
    bt = delta_io.sql(tables.bronze_spec(config.STREAM_PAGE_CHANGE).path(),
                      f"SELECT meta_id, source_file, source_line FROM t WHERE meta_dt <= '{lake_config.EXT_AS_OF.replace('T', ' ').replace('Z', '')}'")
    order = sorted(range(bt.num_rows), key=lambda i: (bt.column("source_file")[i].as_py(), bt.column("source_line")[i].as_py()))
    ids = bt.column("meta_id").to_pylist()
    ids = [ids[i] for i in order]
    blooms = []
    for fp in (0.01, 0.001):
        b = Bloom(len(ids), fp)
        exact_seen: set[str] = set()
        tp = fp_n = fn = 0
        t1 = time.time()
        for mid in ids:
            dup = mid in exact_seen
            flag = b.check_and_add(mid)
            exact_seen.add(mid)
            if flag and dup:
                tp += 1
            elif flag and not dup:
                fp_n += 1
            elif dup and not flag:
                fn += 1
        blooms.append({"target_fp_rate": fp, "bits": b.m, "hashes": b.k, "bloom_bytes": b.bytes(),
                       "events": len(ids), "exact_repeats": tp + fn, "flagged": tp + fp_n, "true_repeats_found": tp,
                       "false_positives": fp_n, "false_negatives": fn,
                       "observed_fp_rate": round(fp_n / max(1, len(ids) - tp - fn), 6),
                       "exact_set_bytes_est": 8 * len(exact_seen), "seconds": round(time.time() - t1, 1)})
    res["bloom_meta_id"] = blooms

    # ---- 3. DGIM: reverts in the last hour ----
    marks = np.arange(math.ceil(meta_dt[0] / EVAL_EVERY_S) * EVAL_EVERY_S + WINDOW_S, meta_dt[-1], EVAL_EVERY_S)
    rev_t = meta_dt[is_revert]
    rev_page = page[is_revert]
    dg = []
    for r in (2, 4):
        g = DGIM(WINDOW_S, r)
        j = 0
        errs, max_buckets = [], 0
        for mk in marks:
            while j < len(rev_t) and rev_t[j] <= mk:
                g.add_one(rev_t[j])
                j += 1
            est = g.count(mk)
            ex = int(np.sum((rev_t > mk - WINDOW_S) & (rev_t <= mk)))
            max_buckets = max(max_buckets, g.n_buckets())
            if ex:
                errs.append(abs(est - ex) / ex)
        dg.append({"scope": "wiki-wide", "r": r, "eval_points": int(len(marks)), "mean_rel_error_pct": round(100 * float(np.mean(errs)), 2),
                   "p95_rel_error_pct": round(100 * float(np.percentile(errs, 95)), 2), "max_rel_error_pct": round(100 * float(np.max(errs)), 2),
                   "bound_pct": round(100 / r, 1), "max_buckets": max_buckets,
                   "dgim_bytes_est": max_buckets * 2 * 4, "exact_window_bytes_est": int(8 * max(
                       np.sum((rev_t > mk - WINDOW_S) & (rev_t <= mk)) for mk in marks[::6]))})
    # per page: the 200 pages with the most revert events
    top = np.argsort(-np.bincount(np.unique(rev_page, return_inverse=True)[1]))[:200]
    upages = np.unique(rev_page)[top]
    for r in (2,):
        errs, exact_n, sizes = [], 0, []
        for pg in upages:
            ts = rev_t[rev_page == pg]
            g = DGIM(WINDOW_S, r)
            j = 0
            lo, hi = ts[0], ts[-1] + WINDOW_S
            for mk in marks[(marks >= lo) & (marks <= hi)]:
                while j < len(ts) and ts[j] <= mk:
                    g.add_one(ts[j])
                    j += 1
                est = g.count(mk)
                ex = int(np.sum((ts > mk - WINDOW_S) & (ts <= mk)))
                if ex:
                    errs.append(abs(est - ex) / ex)
                    exact_n += 1
                sizes.append(g.n_buckets())
        dg.append({"scope": "per page (200 pages with most reverts)", "r": r, "eval_points": exact_n,
                   "mean_rel_error_pct": round(100 * float(np.mean(errs)), 2),
                   "p95_rel_error_pct": round(100 * float(np.percentile(errs, 95)), 2),
                   "max_rel_error_pct": round(100 * float(np.max(errs)), 2), "bound_pct": round(100 / r, 1),
                   "share_exact_pct": round(100 * float(np.mean(np.array(errs) == 0)), 2),
                   "max_buckets": int(max(sizes))})
    res["dgim_reverts_last_hour"] = dg

    # ---- 4. Reservoir sampling of edits ----
    rng = np.random.default_rng(SEED)
    is_edit = np.array([k == "edit" for k in kind])
    edit_rev = is_revert[is_edit]
    k = 10_000
    reservoir = list(range(k))
    for i in range(k, len(edit_rev)):
        j = rng.integers(0, i + 1)
        if j < k:
            reservoir[j] = i
    samp = edit_rev[np.array(reservoir)]
    p_hat, p = float(samp.mean()), float(edit_rev.mean())
    res["reservoir_edits"] = {"k": k, "stream_edits": int(len(edit_rev)), "exact_revert_event_share_pct": round(100 * p, 3),
                              "sample_share_pct": round(100 * p_hat, 3),
                              "sample_95ci_pct": [round(100 * (p_hat - 1.96 * math.sqrt(p_hat * (1 - p_hat) / k)), 3),
                                                  round(100 * (p_hat + 1.96 * math.sqrt(p_hat * (1 - p_hat) / k)), 3)]}

    # ---- 5. AMS second moment of edits per page ----
    ep = page[is_edit]
    _, counts = np.unique(ep, return_counts=True)
    f2 = float(np.sum(counts.astype(np.float64) ** 2))
    ams = []
    for n_var in (100, 1000):
        pos = np.sort(rng.choice(len(ep), size=n_var, replace=False))
        ests = []
        for q in pos:                                   # X = n * (2 * c - 1), c = occurrences of ep[q] from q on
            c = int(np.sum(ep[q:] == ep[q]))
            ests.append(len(ep) * (2 * c - 1))
        groups = np.array_split(np.array(ests, dtype=np.float64), 10)
        est = float(np.median([g.mean() for g in groups]))   # median of means
        ams.append({"variables": n_var, "estimate": round(est), "exact_f2": round(f2),
                    "rel_error_pct": round(100 * (est - f2) / f2, 2)})
    res["ams_f2_edits_per_page"] = ams
    res["seconds"] = round(time.time() - t0, 1)
    return res


def spark_hll(res: dict) -> dict:
    """Spark's built-in HyperLogLog++ (approx_count_distinct, rsd 0.05 and 0.01) on the same stream."""
    from .spark_session import get_spark
    spark = get_spark("truthlag_hll")
    path = tables.SILVER["page_change"].path()
    lim = lake_config.EXT_AS_OF.replace("T", " ").replace("Z", "")
    out = []
    for rsd in (0.05, 0.01):
        t0 = time.time()
        r = spark.sql(f"""SELECT approx_count_distinct(page_id, {rsd}) AS pages,
                                 approx_count_distinct(concat_ws('|', coalesce(CAST(user_id AS STRING), 'None'),
                                                                coalesce(user_name, 'None')), {rsd}) AS editors
                          FROM delta.`{path}` WHERE wiki_id = 'enwiki' AND meta_dt <= TIMESTAMP '{lim}'""").first()
        out.append({"rsd": rsd, "pages": r["pages"], "editors": r["editors"], "seconds": round(time.time() - t0, 1)})
    spark.stop()
    return out


def main() -> None:
    res = run()
    if "--no-spark" not in sys.argv:
        res["spark_approx_count_distinct"] = spark_hll(res)
    path = lake_config.lake_root() / "_runs" / "streaming_algos.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(res, indent=1, default=str))
    print(json.dumps(res, indent=1, default=str))


if __name__ == "__main__":
    main()
