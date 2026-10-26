#!/usr/bin/env python3
"""TruthLag Wikimedia EventStreams capture (stdlib only).
Usage: capture.py <conn_name> <streams_csv> <since_iso>
"""
import gzip, json, logging, os, shutil, socket, sys, time, uuid, urllib.request, urllib.error
from collections import OrderedDict

BASE = "/opt/truthlag"
UA = "TruthLag-DATA226/0.1 (SJSU student project; scottn66 on GitHub)"
RAW = os.path.join(BASE, "data/raw")
STATE_DIR = os.path.join(BASE, "state")
LOG_DIR = os.path.join(BASE, "logs")
MIN_FREE = 5 * 1024**3
STATE_EVERY = 500
MAX_WRITERS = 48

conn, streams, since = sys.argv[1], sys.argv[2], sys.argv[3]
os.makedirs(STATE_DIR, exist_ok=True); os.makedirs(LOG_DIR, exist_ok=True)
logging.basicConfig(filename=os.path.join(LOG_DIR, f"capture-{conn}.log"), level=logging.INFO,
                    format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger()
STATE = os.path.join(STATE_DIR, f"{conn}.json")
SESSION = time.strftime("%Y%m%dT%H%M%S", time.gmtime()) + "-" + uuid.uuid4().hex[:6]


def load_state():
    try:
        with open(STATE) as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def save_state(st):
    tmp = STATE + ".tmp"
    with open(tmp, "w") as f:
        json.dump(st, f); f.flush(); os.fsync(f.fileno())
    os.replace(tmp, STATE)
    d = os.open(STATE_DIR, os.O_RDONLY); os.fsync(d); os.close(d)


class Writers:
    def __init__(self):
        self.open = OrderedDict(); self.counter = {}
    def get(self, stream, dt):
        key = (stream, dt[:10], dt[11:13])
        w = self.open.get(key)
        if w is not None:
            self.open.move_to_end(key); return w[1]
        n = self.counter.get(key, 0); self.counter[key] = n + 1
        d = os.path.join(RAW, stream, f"dt={key[1]}", f"hour={key[2]}")
        os.makedirs(d, exist_ok=True)
        raw = open(os.path.join(d, f"part-{SESSION}-{n}.ndjson.gz"), "wb")
        gz = gzip.GzipFile(fileobj=raw, mode="wb")
        self.open[key] = (raw, gz)
        while len(self.open) > MAX_WRITERS:
            self._close(*self.open.popitem(last=False))
        return gz
    def _close(self, key, w):
        raw, gz = w
        gz.close(); raw.flush(); os.fsync(raw.fileno()); raw.close()
    def flush_all(self):
        for raw, gz in self.open.values():
            gz.flush(); raw.flush()
    def close_all(self):
        while self.open:
            self._close(*self.open.popitem(last=False))


def disk_ok():
    return shutil.disk_usage(BASE).free >= MIN_FREE


def run():
    st = load_state()
    writers = Writers()
    backoff = 1
    total = kept = 0
    last_dt = st.get("last_dt")
    try:
        while True:
            if not disk_ok():
                log.error("free disk < 5GB, stopping"); writers.close_all(); sys.exit(2)
            url = f"https://stream.wikimedia.org/v2/stream/{streams}"
            hdr = {"User-Agent": UA, "Accept": "text/event-stream"}
            if st.get("last_event_id"):
                hdr["Last-Event-ID"] = st["last_event_id"]
                log.info("connecting with Last-Event-ID (resume) last_dt=%s", last_dt)
            else:
                url += f"?since={since}"
                log.info("connecting fresh since=%s", since)
            try:
                resp = urllib.request.urlopen(urllib.request.Request(url, headers=hdr), timeout=90)
                backoff = 1
                ev_id = None; data = []
                for rawline in resp:
                    line = rawline.decode("utf-8", "replace").rstrip("\r\n")
                    if line.startswith("id:"):
                        ev_id = line[3:].strip()
                    elif line.startswith("data:"):
                        data.append(line[5:].lstrip())
                    elif line == "":
                        if not data:
                            continue
                        payload = "\n".join(data); data = []
                        total += 1
                        try:
                            ev = json.loads(payload)
                        except ValueError:
                            log.warning("bad json skipped"); continue
                        meta = ev.get("meta") or {}
                        wiki = ev.get("wiki_id") or ev.get("database")
                        if meta.get("domain") != "canary" and wiki == "enwiki" and meta.get("dt"):
                            stream = meta.get("stream", "unknown")
                            writers.get(stream, meta["dt"]).write((payload + "\n").encode())
                            kept += 1
                            last_dt = meta["dt"]
                        if ev_id:
                            st["last_event_id"] = ev_id
                        if total % STATE_EVERY == 0:
                            writers.flush_all()
                            st.update(last_dt=last_dt, total=st.get("total", 0) + STATE_EVERY,
                                      updated=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
                            save_state(st)
                            if total % (STATE_EVERY * 20) == 0:
                                log.info("seen=%d kept=%d last_dt=%s", total, kept, last_dt)
                                if not disk_ok():
                                    break
                log.warning("stream ended; reconnecting (last_dt=%s)", last_dt)
            except (urllib.error.URLError, socket.timeout, ConnectionError, OSError) as e:
                log.warning("connection error %r; gap possible after last_dt=%s; retry in %ss", e, last_dt, backoff)
            save_state(st)
            time.sleep(backoff); backoff = min(backoff * 2, 120)
    finally:
        writers.close_all()
        save_state(st)

if __name__ == "__main__":
    run()
