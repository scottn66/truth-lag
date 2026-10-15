"""Minimal Wikimedia EventStreams collector: SSE -> hourly ndjson files.

Usage: python ingest/collect_eventstreams.py [stream] [out_dir]
Reconnects on drop and resumes with Last-Event-ID.
"""
import json, os, sys, time
from datetime import datetime, timezone
import requests

STREAM = sys.argv[1] if len(sys.argv) > 1 else "mediawiki.page_change.v1"
OUT = sys.argv[2] if len(sys.argv) > 2 else "data/raw"
URL = f"https://stream.wikimedia.org/v2/stream/{STREAM}"
UA = "TruthLag/0.1 (SJSU DATA 226 Group 9; class project) python-requests"
WIKI = os.environ.get("WIKI", "enwiki")  # client-side filter; "" = all wikis


def out_path(now):
    d = os.path.join(OUT, STREAM, now.strftime("dt=%Y-%m-%d"))
    os.makedirs(d, exist_ok=True)
    return os.path.join(d, now.strftime("hour=%H.ndjson"))


def sse_events(last_id):
    headers = {"User-Agent": UA, "Accept": "text/event-stream"}
    if last_id:
        headers["Last-Event-ID"] = last_id
    with requests.get(URL, headers=headers, stream=True, timeout=(10, 60)) as r:
        r.raise_for_status()
        ev_id, data = None, []
        for line in r.iter_lines(decode_unicode=True):
            if line == "":  # end of one event
                if data:
                    yield ev_id, "\n".join(data)
                ev_id, data = None, []
            elif line.startswith("id:"):
                ev_id = line[3:].strip()
            elif line.startswith("data:"):
                data.append(line[5:].lstrip())


def main():
    last_id, backoff = None, 1
    while True:
        try:
            for ev_id, raw in sse_events(last_id):
                last_id, backoff = ev_id or last_id, 1
                try:
                    ev = json.loads(raw)
                except ValueError:
                    continue
                if WIKI and ev.get("wiki_id", ev.get("wiki")) != WIKI:
                    continue
                now = datetime.now(timezone.utc)
                ev["_ingested_at"] = now.isoformat()
                with open(out_path(now), "a", encoding="utf-8") as f:
                    f.write(json.dumps(ev, ensure_ascii=False) + "\n")
        except KeyboardInterrupt:
            break
        except Exception as e:  # dropped connection, timeout, HTTP error
            print(f"{datetime.now(timezone.utc).isoformat()} reconnect after: {e}", file=sys.stderr)
            time.sleep(backoff)
            backoff = min(backoff * 2, 60)


if __name__ == "__main__":
    main()
