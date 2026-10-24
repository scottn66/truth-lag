# Glossary: the words we use in EC HW2

> **The Chinese columns were drafted by Claude (AI). Please correct them. That fix is a real contribution: log it in PROGRESS.md.**

How to use this page:
- Search for a word: Ctrl+F (Windows), Cmd+F (Mac), or "Find in page" on a phone.
- We always use the same word for the same thing (see [STYLE.md](STYLE.md)). For example, we say **revert**, not "rollback / undo / revert" mixed together.
- "History file" in the examples means the filtered dump file `enwiki_rev_ns0_2026-09-08_10.parquet` (300,564 rows). Its numbers are marked **(raw file, before clean-up)**. Do not copy them into the report.
- Numbers about the two cohorts are given as keys of `report/FACTS.md`, for example `history_median_T_h`. Look up the value there. The values can change; the keys do not.
- The words are in 5 groups: [Wikipedia](#1-wikipedia-words), [our study](#2-words-of-our-study), [data and files](#3-data-sources-and-files), [MongoDB](#4-mongodb), [Neo4j and SQL](#5-neo4j-and-sql). At the end: [proposal word -> HW2 word](#6-proposal-word---hw2-word) and [notes on the Chinese columns](#7-notes-on-the-chinese-columns-for-a-teammate-to-decide).

## 1. Wikipedia words

| Term | Plain meaning | Example from our data | 中文 (繁體) | 中文 (简体) |
|---|---|---|---|---|
| revision | One saved version of a page. Each edit makes a new revision with its own number, the rev_id. | History cohort rev_ids run from 1,373,793,295 to 1,374,274,457. | 修訂版本（頁面每次儲存的版本） | 修订版本（页面每次保存的版本） |
| edit | The act of changing a page and saving it. One edit makes one revision, so one row is both. | The history file has 300,564 edits from 2026-09-08 to 2026-09-10 UTC (raw file, before clean-up). After clean-up: `history_revisions`. | 編輯（修改並儲存頁面） | 编辑（修改并保存页面） |
| human edit | An edit by anyone who is not a bot: registered users, temporary accounts, and the 3 edits whose user is unknown. | `history_revert_rate_non_bot_pct` is the revert rate of human edits in the history cohort. | 人工編輯（非機器人的編輯） | 人工编辑（非机器人的编辑） |
| page | One Wikipedia page, with a page_id and a title. | The page `British_philosophy` has 235 edits in the history file (raw file, before clean-up). | 頁面 | 页面 |
| namespace 0 (article) | The part of Wikipedia that holds the articles. Talk pages and user pages are other namespaces. We keep only namespace 0. | 3,508,755 of the 5,266,843 September 2026 revisions (66.6%) are in namespace 0 (slim file; raw file, before clean-up). | 命名空間 0（條目） | 命名空间 0（条目） |
| revert | An edit that undoes earlier edits. It brings the page back to an earlier version. | In one hour of the live stream (2026-10-21 12:00 UTC) we saw 278 reverts (raw file, before clean-up). | 回退（把頁面改回較早的版本） | 回退（把页面改回较早的版本） |
| identity revert | A revert that makes the page text exactly the same as an earlier revision. The History dump counts only this kind. | 14,976 rows in the history file are identity reverts, `revision_is_identity_revert` = true (raw file, before clean-up). | 完全回退（內容與某個舊版本完全相同） | 完全回退（内容与某个旧版本完全相同） |
| exact revert | The live-stream word for an identity revert: the stream field `is_exact` is true. | In that hour, 273 of the 278 reverts were exact (raw file, before clean-up). | 精確回退（即時串流中的完全回退） | 精确回退（实时流中的完全回退） |
| rollback | A one-click tool for trusted users. It removes all the latest edits of one user on a page. It is one method of revert. | 75 rollbacks in that hour. The tag `mw-rollback` is on 3,764 rows of the history file (both: raw file, before clean-up). | 一鍵回退（rollback 工具） | 一键回退（rollback 工具） |
| undo | A link in the page history. It removes one edit (or a few) and lets the user write a comment. It is one method of revert. | 126 undos in that hour (raw file, before clean-up). The comment often starts with "Undid revision". | 撤銷（undo） | 撤销（undo） |
| manual revert | A revert made by hand: the user saves an older version without the tools. MediaWiki finds it only within the last 15 revisions. | 77 manual reverts in that hour. Tag `mw-manual-revert`: 2,960 rows of the history file (both: raw file, before clean-up). | 手動回退 | 手动回退 |
| mw-reverted tag | A tag that MediaWiki adds to an edit when a later revert undoes it. It is added only when the revert covers 15 revisions or fewer. | 19,345 rows of the history file have it. The tags stream showed 427 new ones in one hour, 2026-10-19 12:00 UTC (both: raw file, before clean-up). | mw-reverted 標籤（「已被回退」標記） | mw-reverted 标签（"已被回退"标记） |
| null revision | A revision that changes no text, such as a page move or a protection change. We drop these from both cohorts. | A page move makes a null revision with the comment "moved page ...". | 空修訂（內容沒有改變的修訂） | 空修订（内容没有改变的修订） |
| temporary account (logged-out editor) | Since 2025-11-04, English Wikipedia gives each logged-out editor a temporary account. The name looks like `~2026-12345-67`. There are no IP edits now. | History cohort edits by temporary accounts: `history_edits_temporary`. | 臨時帳號（未登入的編輯者） | 临时账号（未登录的编辑者） |
| registered user | An editor who made an account and is logged in, and is not a bot. | History cohort edits by registered users: `history_edits_registered`. | 註冊用戶 | 注册用户 |
| bot | A program that edits with its own approved account. In the dump, a bot has "group" in `event_user_is_bot_by`. Bots keep their real names in our results. | History cohort bot edits: `history_edits_bot`. The busiest bots are ZackBot, AnomieBOT and GreenC bot. | 機器人帳號（bot） | 机器人账号（bot） |
| Wikistats | Wikimedia's public statistics website. We use it to check our counts. | It shows 298,802 content edits for 2026-09-08 to 2026-09-10 (`wikistats_content_edits`). | Wikistats（維基媒體統計網站） | Wikistats（维基媒体统计网站） |

## 2. Words of our study

| Term | Plain meaning | Example from our data | 中文 (繁體) | 中文 (简体) |
|---|---|---|---|---|
| RQ1 / RQ2 (research questions) | The two research questions of the spec. RQ1: which edits get reverted, how fast, and where? RQ2: who reverts whom, and what structures go with edit wars? Mongo Q1-Q5 and Cypher Q1-Q5 are queries, not research questions. | The report has "Answer to RQ1" and "Answer to RQ2". | 研究問題 1／2（RQ1／RQ2） | 研究问题 1／2（RQ1／RQ2） |
| reverted (label) | Yes or no: was this edit undone by a later revert? History cohort: within 20 days. Live cohort: within 4 days. In Neo4j, `EDITED.reverted` is the same 20-day label. `reverted_by_other` and `reverting_rev_id` on `EDITED` count reverts at any time before the snapshot. | `history_reverted_20d` (within 20 days) and `history_reverted_any_time` (any time before the snapshot). | 已被回退（標籤） | 已被回退（标签） |
| stream label | Our revert label from EventStreams: the first exact revert that covers the edit, within 4 days. The live cohort uses it. | `live_reverted_4d` | 串流標籤（由即時串流得到的回退標籤） | 流标签（由实时流得到的回退标签） |
| dump label | The revert label from the MediaWiki History dump: an identity revert, here within 20 days. The history cohort uses it. | `history_reverted_20d` | 傾印檔標籤（由歷史傾印檔得到的回退標籤） | 转储标签（由历史转储文件得到的回退标签） |
| revert action | One reverting revision (one revert edit). One revert action can undo several revisions. | In Mongo Q4, `mongo_q4_made_by_bot_pct` is a share of revert actions. | 回退動作（一次回退編輯） | 回退动作（一次回退编辑） |
| reverted revision | A revision that a revert undid. | In Mongo Q4, `mongo_q4_made_by_bot_revisions_pct` is a share of reverted revisions. | 被回退的修訂 | 被回退的修订 |
| time to revert (T) | The time from an edit to the revert that undid it, in seconds. We call it T. We count only reverts within the follow-up window. | The history cohort median is `history_median_T_h` (about 1 hour). | 回退所需時間（T） | 回退所需时间（T） |
| self-revert | An editor reverts their own edit, for example to fix a mistake. It counts in Mongo Q1, Q3 and Q5, but not in Mongo Q2, Q4 or the graph. | The share of history reverts that are self-reverts: `history_self_revert_pct`. | 自我回退 | 自我回退 |
| reverter | The editor who made the revert. | The bot ClueBot NG is the top reverter in Cypher Q2 (`cypher_q2_top_pagerank_editor`, `cypher_q2_top_reverts_made`). | 回退者 | 回退者 |
| edit war | Two or more editors keep reverting each other on the same page. | We find them with mutual reverts (Cypher Q1): `cypher_q1_mutual_pairs` pairs of editors in the history cohort. | 編輯戰 | 编辑战 |
| mutual revert | Editor A reverted editor B, and B reverted A, on the same page. | Cypher Q1: `(a)-[:REVERTED]->(b)-[:REVERTED]->(a)` on one page. | 互相回退 | 互相回退 |
| warring editor | An editor who is in at least one mutual revert on a page. Cypher Q4 counts them per page. | The page `cypher_q4_top_page_title` has `cypher_q4_top_page_warring_editors` warring editors. | 參與編輯戰的編輯者 | 参与编辑战的编辑者 |
| contested page | A page with many reverts by other editors, compared with its human edits. The rule is in `config.py`. | Rule: at least 10 human edits, 2 reverted editors, 2 reverts, and a score of 0.2 or more. The top page in Mongo Q2: `mongo_q2_top_page_title`, with `mongo_q2_top_page_revert_actions` revert actions on `mongo_q2_top_page_edits` human edits. | 爭議頁面 | 争议页面 |
| user kind | Our 4 kinds of editor, checked in this order: unknown, bot, temporary, registered. | The field `user.kind` in every `revisions` document. | 使用者類型 | 用户类型 |
| editor key | A fixed id for one editor: `u:<user_id>` for registered users and bots, `t:<name>` for temporary accounts. | `u:12345` (a made-up example). | 編輯者識別碼 | 编辑者标识符 |
| pseudonym (alias) | A made-up name that hides a human editor in results, figures and screenshots. It is a keyed hash of the editor key (HMAC-SHA256 with a secret in `ec-hw2/.env`), so nobody can rebuild the key from it. It is a display mask on public data, not anonymization. Bots keep their real names. | `editor_7f3a2b1c9d` (a made-up example: `editor_` + 10 hex digits) | 化名（假名） | 化名（假名） |
| cohort | One group of revisions that we study together, chosen by a time window. We have two. | history cohort and live cohort | 世代（一組一起研究的樣本） | 队列（一组一起研究的样本） |
| history cohort | Revisions from 2026-09-08 to 2026-09-10 UTC, with dump labels (reverted within 20 days). | `config.HISTORY_WINDOW` = [2026-09-08, 2026-09-11) | 歷史世代（9 月的樣本） | 历史队列（9 月的样本） |
| live cohort | Revisions from 2026-10-20 to 2026-10-22 UTC, captured from EventStreams, with stream labels (reverted within 4 days). | `config.LIVE_WINDOW` = [2026-10-20, 2026-10-23). Final after 2026-10-27 00:05 UTC. | 即時世代（10 月的樣本） | 实时队列（10 月的样本） |
| follow-up window | How long we wait after an edit to see if it gets reverted. | 20 days for the history cohort, 4 days for the live cohort. | 追蹤期 | 跟踪期 |
| live cutoff | The time after which every live edit has been followed for 4 days, so the stream labels are final: 2026-10-27 00:05 UTC (Mon 2026-10-26 5:05 PM PT). | `live_final_after` | 即時資料截止時間 | 实时数据截止时间 |
| live refresh | After the live cutoff, Scott runs `refresh_live.sh`. It copies the newest data and rebuilds the live tables, MongoDB and the results. Then data-v2 is released. | After Mon 2026-10-26 5:05 PM PT (2026-10-27 00:05 UTC). | 即時資料更新 | 实时数据更新 |
| FINAL / PROVISIONAL | The status of each number in `report/FACTS.md`. FINAL: it will not change. PROVISIONAL: it depends on the live cohort (final after the live cutoff), or it is a timing still labelled draft. | `history_revisions` is FINAL; `live_revisions` is PROVISIONAL. | 定案／暫定 | 定案／暂定 |
| truth lag | The time between an edit going live and the moment the record shows the truth (that it was reverted). | An edit saved at 12:00 UTC is reverted at 13:00 UTC. For 1 hour, a crawler that copies the page gets the bad version. | 真相延遲 | 真相延迟 |
| RAG crawler | A program that copies web pages (here, Wikipedia) into a search index. An AI assistant then answers questions from that index. RAG means "retrieval-augmented generation". | The persona in our Impact section is the engineer of such a crawler. | RAG 爬蟲（為檢索增強生成抓取網頁的程式） | RAG 爬虫（为检索增强生成抓取网页的程序） |
| stream delay (K) | The seconds from a revert being saved (`rev_dt`) to the stream publishing it (`meta.dt`). | Half of the live reverts have K of `live_K_median_s` or less, and 90% have `live_K_p90_s` or less (a few seconds). | 串流延遲（K） | 流延迟（K） |
| known-by time | The time when a stream reader can know that an edit was reverted: T + K. Mongo Q5 uses it. | T = 1 hour and K = 3 seconds, so the reader knows after 1 hour and 3 seconds. | 可得知時間（T + K） | 可知时间（T + K） |
| revert-risk score | A number from 0 to 1 from a Wikimedia model ("revertrisk-language-agnostic", `report/references.md` W17). It is the model's probability that the edit will be reverted. It arrives about 3 seconds after the edit. | One edit on 2026-10-21 had a score of 0.43. | 回退風險分數 | 回退风险分数 |
| risk decile | We sort the scored live edits by revert-risk score and cut them into 10 groups of the same size. Decile 1 has the lowest scores, decile 10 the highest. Edits without a score form an extra "no score" group: page creations, plus edits whose score event was not captured. | The revert rate of decile 10: `risk_top_decile_revert_rate_pct`. | 風險十分位組 | 风险十分位组 |
| Wilson 95% interval | A range around a share (a percentage). With 95% confidence, the true share is inside this range. The Wilson method also works for small groups and for shares near 0% or 100%. | `risk_top_decile_visible_1h_ci` | Wilson 95% 信賴區間 | Wilson 95% 置信区间 |
| revert link | One row in `revert_links`: a reverted revision, the revert that undid it, and the time between them. | `history_revert_links` history revert links. | 回退連結（被回退的修訂與回退它的修訂） | 回退链接（被回退的修订与回退它的修订） |
| late revert | A September edit that the dump says is not reverted, but that the October stream shows being reverted. This is a small case study. The total counts all namespaces. | PROVISIONAL lower bounds: `late_reverts_rows` September revisions; by class `late_reverts_exact`, `late_reverts_inexact_undo`, `late_reverts_method_unknown`. | 遲來的回退 | 迟来的回退 |
| lower bound | The true number is at least this big, and may be bigger. | Our late-revert counts are lower bounds: nobody watched the stream from 2026-10-01 01:38 UTC until the capture started. | 下限 | 下限 |
| censoring | We cannot see what happens after our data ends. An edit that is not reverted yet may still be reverted later. | A live edit from 2026-10-22 23:00 UTC is followed only until the capture data ends. | 設限（看不到資料結束後的事） | 删失（看不到数据结束后的事） |
| UTC and PT | UTC is world time; we use it for all data. PT is Pacific Time (California); we use it for the schedule. | In October 2026, PT = UTC minus 7 hours. So 2026-10-27 00:05 UTC = Mon 2026-10-26 5:05 PM PT. From 2026-11-01, PT = UTC minus 8 hours. | 協調世界時（UTC）與太平洋時間（PT） | 协调世界时（UTC）与太平洋时间（PT） |
| half-open window [start, end) | A time range that includes the start but not the end. | [2026-09-08, 2026-09-11) includes 2026-09-10 23:59:59 but not 2026-09-11 00:00:00. | 半開區間（含開始，不含結束） | 半开区间（含开始，不含结束） |

## 3. Data sources and files

| Term | Plain meaning | Example from our data | 中文 (繁體) | 中文 (简体) |
|---|---|---|---|---|
| snapshot (dump) | A full copy of the data, made at one time. Edits after that time are not in it. | Snapshot 2026-09: its last revision is at 2026-10-01 01:38:27 UTC. | 快照（某一時間點的完整資料） | 快照（某一时间点的完整数据） |
| MediaWiki History dump | Monthly files from Wikimedia with every revision and many computed fields, such as revert labels. Only the last two snapshots stay online. | `2026-09.enwiki.2026-09.tsv.bz2`: 557,344,652 bytes, 78 columns, 6,369,430 rows (the download, before our filter). | MediaWiki 歷史傾印檔 | MediaWiki 历史转储文件 |
| EventStreams | A Wikimedia web service that sends every change as it happens, as a stream of events. | We capture 3 streams: `mediawiki.page_change.v1`, `mediawiki.page_revert_risk_prediction_change.v1` and `mediawiki.revision-tags-change`. | EventStreams（維基媒體即時事件串流） | EventStreams（维基媒体实时事件流） |
| replay | EventStreams can send past events again, from a start time you choose. It keeps between 7 and 31 days of events (`report/references.md`, W10). | The capture asked for a replay from 2026-10-19 23:00 UTC (page_change and revert risk) and from 2026-10-17 00:00 UTC (tags). The capture has saved these events, so it does not matter when they leave the replay. | 重播（重新傳送過去的事件） | 重放（重新发送过去的事件） |
| Parquet | A file format for tables. It stores data by column, so it is small and fast to read with pandas. | `enwiki_rev_ns0_2026-09-08_10.parquet`: 300,564 rows (raw file, before clean-up), 78 columns, all stored as text. | Parquet（欄式儲存的表格檔） | Parquet（列式存储的表格文件） |
| ndjson.gz | A text file with one JSON event per line (ndjson), compressed with gzip (.gz). | `data/raw/mediawiki.page_change.v1/dt=2026-10-21/hour=12/part-....ndjson.gz` | ndjson.gz（每行一筆 JSON 的壓縮檔） | ndjson.gz（每行一条 JSON 的压缩文件） |
| rsync | A program that copies files between computers. It copies only what is new. We never use `--delete`. | `rsync -az --partial vps-coin:/opt/truthlag/data/raw/ data/raw/` | rsync（檔案同步工具） | rsync（文件同步工具） |
| VPS | A rented server on the internet (virtual private server). Ours runs the capture all the time. | `vps-coin`: 7.8 GB of memory, no swap. | 虛擬專用伺服器（VPS） | 虚拟专用服务器（VPS） |
| systemd unit | A service setting on Linux. systemd starts the program and restarts it if it stops. | `truthlag-capture-a` (page_change + revert risk, replayed from 2026-10-19 23:00 UTC) and `truthlag-capture-b` (tags, replayed from 2026-10-17 00:00 UTC). Both units run since 2026-10-24 04:52 UTC. | systemd 服務單元 | systemd 服务单元 |
| data release | A set of our data files on GitHub (Releases), for teammates to download. | data-v1: planned for 2026-10-24, not published yet. data-v2: after the live refresh (after Mon 2026-10-26 5:05 PM PT). | 資料發佈版（GitHub Release） | 数据发布版（GitHub Release） |
| branch | A separate line of work in a Git repository. `main` is the default branch. | Our HW2 work is on the branch `ec-hw2`. | 分支 | 分支 |
| pull request | A request on GitHub to merge one branch into another. Teammates read the changes, comment and approve there. | The draft pull request from `ec-hw2` into `main`. | Pull Request（合併請求） | Pull Request（合并请求） |
| venv | A private Python folder for this project, so its packages do not mix with others. | `.venv/` in the repo folder. | 虛擬環境（venv） | 虚拟环境（venv） |
| .env file | A small text file with passwords and connection strings. Never commit it. | `ec-hw2/.env`, made from `ec-hw2/.env.example`. | .env 設定檔（存放密碼） | .env 配置文件（存放密码） |

## 4. MongoDB

| Term | Plain meaning | Example from our data | 中文 (繁體) | 中文 (简体) |
|---|---|---|---|---|
| document (MongoDB) | One record in MongoDB, like a JSON object. It can hold smaller parts inside it. | One document per revision: `{_id: "enwiki:<rev_id>", cohort, page: {...}, user: {...}, history: {...}}` | 文件（MongoDB 的一筆資料） | 文档（MongoDB 的一条数据） |
| collection | A group of documents, like a table in SQL. | `revisions`, `revert_links`, `page_hour`, `tag_events`, `late_reverts` | 集合 | 集合 |
| chart collection | A small collection with pre-computed rows for one Atlas Chart. Its names and fields are frozen once a chart uses them. | `chart_q1_hour_kind`, `chart_q3_time_to_revert`, `chart_q5_known_by`, `chart_q5_risk_deciles` | 圖表用集合 | 图表用集合 |
| aggregation pipeline | A MongoDB query made of steps (stages). Each stage changes the documents and passes them on. | `queries/mongo/q1_revert_rate_by_hour.json` (Mongo Q1) | 聚合管線 | 聚合管道 |
| $lookup | A stage that joins documents from another collection, like a SQL join. | Mongo Q5 joins `revisions` with `revert_links`. | $lookup（關聯另一個集合） | $lookup（关联另一个集合） |
| $bucket | A stage that puts numbers into ranges (buckets) and counts them. | Mongo Q3 puts time to revert into 11 buckets, from "<1 min" to "14-20 d". | $bucket（按區間分組計數） | $bucket（按区间分组计数） |
| $facet | A stage that runs several small pipelines on the same input at once. | Mongo Q4: reverts made by each user kind, and reverts received by each user kind. | $facet（同時跑多個子管線） | $facet（同时运行多个子管道） |
| index | A sorted helper list that makes queries fast. | `{"page.id": 1, ts: 1}` on `revisions` | 索引 | 索引 |
| view | A saved pipeline that you can read like a collection. It stores no data of its own. | Atlas Charts can use a view as a data source. | 檢視表（視圖） | 视图 |
| Atlas free tier (M0) | The free MongoDB cloud database. It holds up to 512 MB and cannot be sharded. | We load only the history cohort (without `comment`) and keep it under 400 MB. | Atlas 免費方案（M0） | Atlas 免费套餐（M0） |
| Data Explorer | The Atlas web page where you browse collections, read documents and run aggregation pipelines (the "Aggregations" tab). | `guides/ATLAS_SETUP.md`, part F. | Data Explorer（Atlas 的資料瀏覽頁面） | Data Explorer（Atlas 的数据浏览页面） |
| sharding | Splitting one collection over several servers (shards). Each shard holds part of the data. | Our demo runs 2 shards on Scott's Mac. | 分片 | 分片 |
| shard key | The field that decides which shard gets each document. | `page.id` | 分片鍵 | 分片键 |
| hashed shard key | The shard key is first turned into a random-looking number (a hash), so the documents spread evenly. | `{"page.id": "hashed"}` | 雜湊分片鍵 | 哈希分片键 |
| replica set | A group of MongoDB servers that keep copies of the same data. | In the demo, each shard is a replica set: `shard1rs`, `shard2rs`. | 複本集 | 副本集 |
| mongos | The router of a sharded cluster. Programs connect to mongos, and it sends each query to the right shards. | Port 27020 on Scott's Mac. | mongos（分片叢集的路由器） | mongos（分片集群的路由器） |
| chunk | A piece of a sharded collection: one range of shard-key values. MongoDB moves chunks between shards to keep them even. | Our demo shards the empty collection first, so the chunks spread over both shards from the start. | 資料塊（chunk） | 数据块（chunk） |
| config server | The small MongoDB server that remembers which chunk lives on which shard. | In the demo it is the container `cfg` (port 27019). | 設定伺服器 | 配置服务器 |
| SINGLE_SHARD | In `explain()`, the query went to one shard only (a targeted query). This is fast. | `find({"page.id": X})` shows SINGLE_SHARD, because page.id is the shard key. | 單一分片查詢 | 单一分片查询 |
| SHARD_MERGE | In `explain()`, the query went to every shard and mongos merged the answers (scatter-gather). | Grouping by hour of day shows SHARD_MERGE, because the hour is not the shard key. | 分片合併（散佈收集） | 分片合并（分散收集） |
| page_hour | Our live counters in MongoDB: edits and reverts seen per page and per hour. | Key: `<page_id>:<YYYY-MM-DDTHH>` | page_hour（每頁每小時的即時計數） | page_hour（每页每小时的实时计数） |

## 5. Neo4j and SQL

| Term | Plain meaning | Example from our data | 中文 (繁體) | 中文 (简体) |
|---|---|---|---|---|
| node | One thing in a graph. | Two kinds: `(:Editor)` and `(:Page)`. | 節點 | 节点 |
| relationship | A link between two nodes. It has a direction and a type. | `EDITED` (editor to page) and `REVERTED` (editor to editor, on one page). | 關係（有方向的連結） | 关系（有方向的连接） |
| Cypher | The query language of Neo4j. You draw the pattern with brackets and arrows. | `MATCH (a:Editor)-[:REVERTED]->(b:Editor) RETURN a, b` | Cypher（Neo4j 的查詢語言） | Cypher（Neo4j 的查询语言） |
| Neo4j Browser / Bloom | Neo4j Browser is the web page of Neo4j (http://localhost:7474). You run Cypher there and see the result as a graph or a table. Bloom is a separate picture tool. It is not part of the Community edition, so we use Browser. | `guides/NEO4J_SCREENSHOTS.md` | Neo4j Browser（瀏覽器介面）／ Bloom | Neo4j Browser（浏览器界面）／ Bloom |
| degree | The number of relationships of a node. Out-degree counts only the ones that go out. | Cypher Q2 (by degree): the reverts an editor made. This list answers "who reverts the most". | 度數（連接的數量） | 度（连接的数量） |
| PageRank | A score for how central a node is. It depends on the links from other central nodes. | Cypher Q2 runs it on the REVERTED edges in reverse. A high score means: this editor reverts editors who are themselves active reverters. | PageRank（網頁排名演算法） | PageRank（网页排名算法） |
| community / modularity | A community is a group of nodes with many links inside the group and few links to other groups. Modularity is a score for how well a split into communities fits the graph (higher is better, at most 1). | Cypher Q3: `cypher_q3_louvain_communities` and `cypher_q3_louvain_modularity`. Most communities are one editor with no revert. The large ones are a patroller and the editors they reverted. | 社群／模組度 | 社区／模块度 |
| Louvain | A method that splits a graph into communities. | Cypher Q3: communities of conflict. | Louvain 社群偵測演算法 | Louvain 社区发现算法 |
| WCC (connected components) | Weakly connected components: groups of nodes joined by any path, if we ignore the arrow directions. | Cypher Q3 also gives the sizes of these groups. | 弱連通分量（WCC） | 弱连通分量（WCC） |
| GDS | Neo4j Graph Data Science: a library of graph methods, such as PageRank, Louvain and WCC. | `RETURN gds.version()` gives 2026.10.1 on Scott's Mac. | GDS（圖資料科學函式庫） | GDS（图数据科学库） |
| LOAD CSV | The Cypher command that reads a CSV file and makes nodes and relationships. Every value arrives as text, so we convert it. | `queries/cypher/load.cypher` reads `editors.csv`, `pages.csv`, `edited.csv` and `reverted.csv`. | LOAD CSV（匯入 CSV 檔） | LOAD CSV（导入 CSV 文件） |
| SQLite | A small SQL database kept in one file. It needs no server. | `data/tables/truthlag.sqlite`: we compare it with MongoDB and Neo4j. | SQLite（單一檔案的 SQL 資料庫） | SQLite（单文件 SQL 数据库） |

## 6. Proposal word -> HW2 word

Our proposal used some words that we do not use in HW2. Use the HW2 word.

| Proposal word | HW2 word |
|---|---|
| Cohort A | history cohort or live cohort |
| H = 30 days | follow-up window (20 days for the history cohort, 4 days for the live cohort) |
| bronze / silver / gold | the folders `data/parsed/` and `data/tables/` |
| speed layer | the `page_hour` live counters in MongoDB |
| Kafka / Redpanda | final project only (not in HW2) |
| E0-E7 experiments | final project |
| V1 / V2 tiers | stream label / dump label |
| Q1 / Q2 (research questions) | RQ1 / RQ2 |

## 7. Notes on the Chinese columns (for a teammate to decide)

A reviewer (an AI agent, 2026-10-24) found no wrong translation, but a few terms can mislead. Nothing above was changed. Please choose, change the table if you agree, and log it in PROGRESS.md.

| Term | Now (繁體 / 简体) | Possible problem | Suggested option (繁體 / 简体) |
|---|---|---|---|
| identity revert | 完全回退 / 完全回退 | Can read as "a complete or full revert" (undo everything), not "the same text as an older version". | 還原至相同版本的回退 / 还原至相同版本的回退 |
| revert link | 回退連結 / 回退链接 | In Taiwan, 連結 strongly means a hyperlink. | 回退配對紀錄 / 回退配对记录 |
| pseudonym | 化名（假名） | 假名 also means Japanese kana. | 化名 only |
| SHARD_MERGE (scatter-gather) | 分片合併（散佈收集） | 散佈收集 is not the usual term for scatter-gather. | 分散-收集 |
| registered user (繁體) | 註冊用戶 | The 繁體 column mixes 用戶 with 使用者類型 (user kind). | 註冊使用者 |
