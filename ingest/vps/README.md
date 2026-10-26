# TruthLag (DATA 226 EC HW2) on vps-coin

Everything lives in /opt/truthlag. Services run as root (it's the only user on this VPS) and write only here.

## What runs
- `truthlag-capture-a`: SSE client for `mediawiki.page_change.v1,mediawiki.page_revert_risk_prediction_change.v1`, started at since=2026-10-19T23:00:00Z
- `truthlag-capture-b`: SSE client for `mediawiki.revision-tags-change`, started at since=2026-10-17T00:00:00Z
  - Keeps only enwiki, drops canary events, saves the full event JSON to
    `data/raw/<stream>/dt=YYYY-MM-DD/hour=HH/part-<session>-<n>.ndjson.gz` (partitioned by meta.dt)
  - Resume state (Last-Event-ID) is in `state/{a,b}.json`. Logs are in `logs/capture-{a,b}.log`
  - Restart=always, MemoryMax=500M. Stops when free disk drops under 5 GB.
- `filter_history.py` (one-off transient unit `truthlag-filter`): streams `data/history/2026-09.enwiki.2026-09.tsv.bz2` and writes
  - `data/history/enwiki_rev_ns0_2026-09-08_10.tsv.gz` (+ .parquet): all 78 columns, revision, ns0, Sep 8-10 UTC
  - `data/history/enwiki_rev_all_2026-09_slim.tsv.gz` (+ .parquet): all Sep revisions, slim columns for the reverter self-join
  - Stats are in `data/history/filter_stats.json`. Log is in `logs/filter.log`

## Status
    systemctl status truthlag-capture-a truthlag-capture-b
    tail -f /opt/truthlag/logs/capture-a.log
    cat /opt/truthlag/state/a.json | python3 -c 'import json,sys;print(json.load(sys.stdin)["last_dt"])'
    du -sh /opt/truthlag/data; df -h /

## Stop / start
    systemctl stop truthlag-capture-a truthlag-capture-b      # resumes from state on next start
    systemctl disable truthlag-capture-a truthlag-capture-b   # don't start at boot
    systemctl start truthlag-capture-a truthlag-capture-b
Fresh restart from `since`: stop the service, then delete state/<x>.json.

## Pull to the Mac
    rsync -avz --partial vps-coin:/opt/truthlag/data/raw/ ~/truthlag-data/raw/
    rsync -avz --partial --exclude '*.bz2' vps-coin:/opt/truthlag/data/history/ ~/truthlag-data/history/
(Part files that are still open have no gzip trailer yet. Pull hours that are older than the current meta.dt, or stop the services first.)
