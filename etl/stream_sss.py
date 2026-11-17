"""Spark Structured Streaming, Bronze -> Silver, replayed at fixed rates (rubric: stream processing framework; small E5).

Purpose
    The batch pipeline loads Bronze with delta-rs and parses it in Python. This demo shows the same Bronze -> Silver
    step as a Spark Structured Streaming query, and measures it:
      * a producer process appends captured page-change lines (from bronze/page_change_events, in capture order) to a
        demo Delta table `bronze_in` at a fixed rate R (one delta-rs commit per second, R rows each, stamped with
        produced_at just before the commit);
      * the streaming query reads `bronze_in` as a Delta stream (trigger every 1 s), parses raw_json with from_json,
        applies the Silver rules (enwiki, not canary, meta.id and meta.dt present, one row per meta_id), and in
        foreachBatch does an insert-only MERGE on meta_id into `silver_out` (as tested in research R3);
      * latency of an event = time its micro-batch MERGE committed - produced_at. Throughput = events / wall time.
    Rates 1,000 to 20,000 events/s, 30 s each; E5 asks for the rate where p95 latency passes 5 s (target >= 2,500/s).
    A last run pre-loads 500,000 lines and drains them with availableNow (maximum throughput, no rate limit).
    Correctness: the meta_ids in silver_out equal those of silver/page_change for the same Bronze lines.

Writes only under data/lake/stream_demo/ (one folder per run). The lake tables are only read.

Run
    python -m etl.stream_sss                       # all rates + drain; results in data/lake/_runs/stream_sss.json
    python -m etl.stream_sss --quick               # live demo, about 1 minute: one rate (2,500 events/s for 15 s),
                                                   # each micro-batch printed as it commits, then the parity check
    python -m etl.stream_sss --rates 2500,10000    # chosen rates, 30 s each, with the drain

Only the full run writes stream_sss.json. --quick and --rates write stream_sss_demo.json, so a demo never
replaces the full record. (The report's timings come from the frozen copy stream_sss.published_2026-11-15.json.)
Spark's start-up output goes to a log file (TRUTHLAG_SPARK_VERBOSE=1 shows it on the terminal).
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pyarrow as pa

from . import delta_io, lake_config, tables
from .hw2 import config

DEMO = lake_config.lake_root() / "stream_demo"
RATES = [1000, 2500, 5000, 10000, 20000]
SECONDS = 30
QUICK_RATE, QUICK_SECONDS = 2500, 15
DRAIN_ROWS = 500_000
START_DATE = "2026-10-20"
TS = pa.timestamp("us", tz="UTC")
SCHEMA_IN = pa.schema([("meta_id", pa.string()), ("meta_dt", TS), ("raw_json", pa.string()),
                       ("source_file", pa.string()), ("source_line", pa.int32()), ("produced_at", TS)])
EVENT_SCHEMA = ("meta STRUCT<id: STRING, dt: STRING, domain: STRING>, wiki_id STRING, page_change_kind STRING, "
                "page STRUCT<page_id: BIGINT, page_title: STRING, namespace_id: INT>, "
                "revision STRUCT<rev_id: BIGINT, rev_dt: STRING, rev_parent_id: BIGINT, rev_size: BIGINT>, "
                "performer STRUCT<user_id: BIGINT, is_bot: BOOLEAN, is_temp: BOOLEAN>")


# ------------------------------------------------------------------ source rows (capture order)
def source_rows(n: int, offset: int = 0) -> pa.Table:
    path = tables.bronze_spec(config.STREAM_PAGE_CHANGE).path()
    out, got, day = [], 0, datetime.fromisoformat(START_DATE).date()
    skip = offset
    while got < n:
        t = delta_io.read_table(path, columns=["meta_id", "meta_dt", "raw_json", "source_file", "source_line"],
                                predicate=f"event_date = '{day}'")
        t = t.sort_by([("source_file", "ascending"), ("source_line", "ascending")])
        if skip >= t.num_rows:
            skip -= t.num_rows
        else:
            t = t.slice(skip, n - got)
            skip = 0
            out.append(t)
            got += t.num_rows
        day = day.fromordinal(day.toordinal() + 1)
    return pa.concat_tables(out)


# ------------------------------------------------------------------ producer (separate process)
def produce(dest: str, rate: int, seconds: int, offset: int) -> None:
    from deltalake import DeltaTable, write_deltalake
    rows = source_rows(rate * seconds, offset)
    delta_io.ensure_table(dest, SCHEMA_IN, lake_config.KEEP_HISTORY)
    tbl = DeltaTable(dest)
    t0 = time.time()
    for i in range(seconds):
        due = t0 + i
        now = time.time()
        if due > now:
            time.sleep(due - now)
        chunk = rows.slice(i * rate, rate)
        stamp = datetime.now(timezone.utc)
        chunk = chunk.append_column("produced_at", pa.array([stamp] * chunk.num_rows, TS))
        write_deltalake(tbl, chunk.cast(SCHEMA_IN), mode="append")
    print(json.dumps({"produced": rows.num_rows, "seconds": round(time.time() - t0, 2)}), flush=True)


# ------------------------------------------------------------------ consumer
def _process(spark, silver_out: str, records: list, show: bool = False):
    """The foreachBatch function: parse one micro-batch, apply the Silver rules, MERGE it into silver_out.
    With show=True each micro-batch is printed when its MERGE commits."""
    from pyspark.sql import functions as F

    def fb(df, batch_id):
        t_start = time.time()
        e = df.select(F.from_json("raw_json", EVENT_SCHEMA).alias("e"), "produced_at", "meta_id")
        s = (e.where((F.col("e.wiki_id") == "enwiki") & (F.coalesce(F.col("e.meta.domain"), F.lit("")) != "canary")
                     & F.col("e.meta.id").isNotNull() & F.col("e.meta.dt").isNotNull())
              .select(F.col("e.meta.id").alias("meta_id"), F.to_timestamp("e.meta.dt").alias("meta_dt"),
                      F.col("e.page_change_kind").alias("kind"), F.col("e.page.page_id").alias("page_id"),
                      F.col("e.page.page_title").alias("page_title"), F.col("e.page.namespace_id").alias("ns"),
                      F.col("e.revision.rev_id").alias("rev_id"), F.to_timestamp("e.revision.rev_dt").alias("rev_dt"),
                      F.col("e.revision.rev_parent_id").alias("parent_id"), F.col("e.revision.rev_size").alias("rev_size"),
                      F.col("e.performer.user_id").alias("user_id"), F.col("e.performer.is_bot").alias("is_bot"),
                      F.col("e.performer.is_temp").alias("is_temp"), "produced_at")
              .dropDuplicates(["meta_id"]))
        s = s.persist()
        n = s.count()
        s.drop("produced_at").createOrReplaceTempView("sss_batch")
        s.sparkSession.sql(f"""MERGE INTO delta.`{silver_out}` t USING sss_batch b ON t.meta_id = b.meta_id
                               WHEN NOT MATCHED THEN INSERT *""")
        t_done = time.time()
        per_stamp = [(r["produced_at"].replace(tzinfo=timezone.utc).timestamp(), r["count"])
                     for r in s.groupBy("produced_at").count().collect()]
        s.unpersist()
        records.append({"batch_id": batch_id, "rows": n, "t_start": t_start, "t_done": t_done, "per_stamp": per_stamp})
        if show and n:
            oldest = t_done - min(st for st, _ in per_stamp)
            total = sum(r["rows"] for r in records)
            print(f"   micro-batch {batch_id:>3}: {n:>7,} events parsed and merged in {t_done - t_start:4.1f} s; "
                  f"oldest event waited {oldest:4.1f} s; total in Silver {total:>9,}", flush=True)

    return fb


def _silver_ddl(spark, path: str) -> None:
    spark.sql(f"""CREATE TABLE IF NOT EXISTS delta.`{path}` (meta_id STRING, meta_dt TIMESTAMP, kind STRING,
                  page_id BIGINT, page_title STRING, ns INT, rev_id BIGINT, rev_dt TIMESTAMP, parent_id BIGINT,
                  rev_size BIGINT, user_id BIGINT, is_bot BOOLEAN, is_temp BOOLEAN) USING DELTA""")


def summarize(records: list, label: str, rate: int | None) -> dict:
    lat, w = [], []
    for r in records:
        for stamp, c in r["per_stamp"]:
            lat.append(r["t_done"] - stamp)
            w.append(c)
    lat, w = np.array(lat), np.array(w)
    order = np.argsort(lat)
    lat, w = lat[order], w[order]
    cw = np.cumsum(w) / w.sum()
    pct = lambda q: float(lat[np.searchsorted(cw, q)])
    n = int(w.sum())
    first = min(s for r in records for s, _ in r["per_stamp"])
    last = max(r["t_done"] for r in records)
    return {"run": label, "target_rate_eps": rate, "events": n, "micro_batches": len(records),
            "throughput_eps": round(n / (last - first), 1), "latency_p50_s": round(pct(0.50), 3),
            "latency_p95_s": round(pct(0.95), 3), "latency_max_s": round(float(lat[-1]), 3),
            "mean_batch_rows": round(n / len(records), 1),
            "mean_batch_merge_s": round(float(np.mean([r["t_done"] - r["t_start"] for r in records])), 3)}


def run_rate(spark, rate: int, offset: int, seconds: int = SECONDS, show: bool = False) -> tuple[dict, str]:
    d = DEMO / f"rate_{rate}"
    shutil.rmtree(d, ignore_errors=True)
    d.mkdir(parents=True)
    src, out, ck = str(d / "bronze_in"), str(d / "silver_out"), str(d / "checkpoint")
    delta_io.ensure_table(src, SCHEMA_IN, lake_config.KEEP_HISTORY)
    _silver_ddl(spark, out)
    records: list = []
    q = (spark.readStream.format("delta").load(src).writeStream.foreachBatch(_process(spark, out, records, show))
         .option("checkpointLocation", ck).trigger(processingTime="1 second").start())
    time.sleep(3)
    prod = subprocess.run([sys.executable, "-m", "etl.stream_sss", "produce", src, str(rate), str(seconds), str(offset)],
                          capture_output=True, text=True, env=os.environ.copy())
    produced = rate * seconds
    t_wait = time.time()
    while sum(r["rows"] for r in records) < produced and time.time() - t_wait < 120:
        time.sleep(0.5)
    q.stop()
    res = summarize(records, f"rate {rate}", rate)
    res["producer"] = (prod.stdout or prod.stderr).strip().splitlines()[-1][:300] if (prod.stdout or prod.stderr) else None
    return res, out


def run_drain(spark) -> tuple[dict, str]:
    """Pre-load DRAIN_ROWS lines in 50 commits, then drain with availableNow, 5 files per micro-batch."""
    from deltalake import DeltaTable, write_deltalake
    d = DEMO / "drain"
    shutil.rmtree(d, ignore_errors=True)
    d.mkdir(parents=True)
    src, out, ck = str(d / "bronze_in"), str(d / "silver_out"), str(d / "checkpoint")
    rows = source_rows(DRAIN_ROWS)
    delta_io.ensure_table(src, SCHEMA_IN, lake_config.KEEP_HISTORY)
    tbl = DeltaTable(src)
    stamp = datetime.now(timezone.utc)
    for i in range(50):
        c = rows.slice(i * (DRAIN_ROWS // 50), DRAIN_ROWS // 50)
        write_deltalake(tbl, c.append_column("produced_at", pa.array([stamp] * c.num_rows, TS)).cast(SCHEMA_IN), mode="append")
    _silver_ddl(spark, out)
    records: list = []
    t0 = time.time()
    q = (spark.readStream.format("delta").option("maxFilesPerTrigger", 5).load(src).writeStream
         .foreachBatch(_process(spark, out, records)).option("checkpointLocation", ck)
         .trigger(availableNow=True).start())
    q.awaitTermination()
    wall = time.time() - t0
    n = sum(r["rows"] for r in records)
    return {"run": "drain (availableNow, 5 files per batch)", "events": n, "micro_batches": len(records),
            "wall_s": round(wall, 1), "throughput_eps": round(n / wall, 1),
            "mean_batch_rows": round(n / len(records), 1),
            "mean_batch_merge_s": round(float(np.mean([r["t_done"] - r["t_start"] for r in records])), 3)}, out


def parity(spark, out: str) -> dict:
    """meta_ids written by the stream against the batch Silver table for the same Bronze lines."""
    silver = tables.SILVER["page_change"].path()
    r = spark.sql(f"""SELECT (SELECT count(*) FROM delta.`{out}`) AS stream_rows,
                             (SELECT count(*) FROM delta.`{out}` o LEFT ANTI JOIN delta.`{silver}` s ON s.meta_id = o.meta_id) AS only_stream,
                             (SELECT count(*) FROM delta.`{out}` o JOIN delta.`{silver}` s ON s.meta_id = o.meta_id
                               WHERE NOT (o.rev_id <=> s.rev_id AND o.page_id <=> s.page_id AND o.kind <=> s.kind
                                          AND o.meta_dt <=> s.meta_dt)) AS differing""").first()
    return r.asDict()


def rate_line(res: dict) -> str:
    verdict = "keeps up" if res["latency_p95_s"] <= 5 else "falls behind (p95 over 5 s)"
    return (f"   {res['target_rate_eps']:>6,} events/s target: {res['events']:>9,} events in {res['micro_batches']:>3} micro-batches; "
            f"throughput {res['throughput_eps']:>8,.1f}/s; latency median {res['latency_p50_s']:.2f} s, "
            f"p95 {res['latency_p95_s']:.2f} s, max {res['latency_max_s']:.2f} s -> {verdict}")


def parity_lines(p: dict) -> None:
    print(f"   rows written by the stream: {p['stream_rows']:,}; not in batch Silver: {p['only_stream']:,}; "
          f"with a different value: {p['differing']:,}")
    print("   -> the streamed rows equal the batch pipeline's rows." if not p["only_stream"] and not p["differing"]
          else "   -> DIFFERENCE between the stream and the batch pipeline: look at the two tables.", flush=True)


def main() -> None:
    if len(sys.argv) > 1 and sys.argv[1] == "produce":
        produce(sys.argv[2], int(sys.argv[3]), int(sys.argv[4]), int(sys.argv[5]))
        return
    args = sys.argv[1:]
    quick = "--quick" in args
    rates, seconds = (list(RATES), SECONDS)
    if quick:
        rates, seconds = [QUICK_RATE], QUICK_SECONDS
    elif "--rates" in args:
        rates = [int(x) for x in args[args.index("--rates") + 1].split(",")]
    full = not quick and rates == RATES

    print("TruthLag Structured Streaming demo: the Bronze -> Silver step as a streaming query.")
    print("A producer process appends captured Wikipedia page-change events to a Delta table at a fixed rate.")
    print("A Spark streaming query reads that table every second, parses the JSON, applies the Silver rules")
    print("and MERGEs each micro-batch into a Silver table. Latency = MERGE commit time - time the event was produced.")
    print(f"This run: rates {', '.join(f'{r:,}' for r in rates)} events/s, {seconds} s each"
          + ("" if quick else "; then a drain of 500,000 pre-loaded events at full speed") + ".\n", flush=True)
    from .spark_session import get_spark
    spark = get_spark("truthlag_sss", shuffle_partitions=4, quiet=True)
    results, offset = [], 0
    for i, rate in enumerate(rates, 1):
        print(f"{i}. Replay at {rate:,} events/s for {seconds} s (about {seconds + 10} s with start and stop)", flush=True)
        res, out = run_rate(spark, rate, offset, seconds, show=quick)
        offset += rate * seconds
        print(rate_line(res) + "\n", flush=True)
        results.append(res)
    step = len(rates) + 1
    if quick:
        print(f"{step}. Correctness: the streamed rows against the batch Silver table for the same Bronze lines")
        par = parity(spark, out)
        parity_lines(par)
        doc = {"rates": results, "parity_with_batch_silver": par, "seconds_per_rate": seconds,
               "spark": spark.version, "master": spark.sparkContext.master, "mode": "quick"}
    else:
        print(f"{step}. Drain: {DRAIN_ROWS:,} events already waiting, processed as fast as possible (availableNow)", flush=True)
        drain, out = run_drain(spark)
        drain["parity_with_batch_silver"] = parity(spark, out)
        print(f"   {drain['events']:,} events in {drain['micro_batches']} micro-batches, {drain['wall_s']} s: "
              f"{drain['throughput_eps']:,.1f} events/s")
        print(f"\n{step + 1}. Correctness: the drained rows against the batch Silver table for the same Bronze lines")
        parity_lines(drain["parity_with_batch_silver"])
        doc = {"rates": results, "drain": drain, "seconds_per_rate": seconds, "spark": spark.version,
               "master": spark.sparkContext.master}
    name = "stream_sss.json" if full else "stream_sss_demo.json"
    path = lake_config.lake_root() / "_runs" / name
    path.write_text(json.dumps(doc, indent=1))
    print(f"\nSaved to {path}" + ("" if full else " (demo record; the full record stream_sss.json is untouched)"))
    spark.stop()


if __name__ == "__main__":
    main()
