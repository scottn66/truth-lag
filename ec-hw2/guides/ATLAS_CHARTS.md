# Atlas Charts: at least 2 charts, saved as PNG

**Who:** the Comparison+viz owner (any Project Owner can do it).
**Time:** about 45 minutes for the 2 required charts, and about 20 minutes more for the 2 optional ones.
**Spec item:** section 3, "Viz: ≥2 MongoDB Atlas Charts".
**Before you start:** Atlas is set up and loaded (`ATLAS_SETUP.md`, parts A to E), and you are a **Project Owner** of the project.

| # | chart | collection | required? | when |
|---|---|---|---|---|
| 1 | Mongo Q1: revert rate by hour of day x user kind | `chart_q1_hour_kind` | yes | from Sun 2026-10-25 (history cohort) |
| 2 | Mongo Q3: time to revert, in buckets | `chart_q3_time_to_revert` | yes | from Sun 2026-10-25 (history cohort) |
| 3 | Mongo Q5: the known-by curve | `chart_q5_known_by` | optional | after the live refresh on Mon 2026-10-26 (live cohort) |
| 4 | Mongo Q5: revert rate by risk decile | `chart_q5_risk_deciles` | optional | after the live refresh on Mon 2026-10-26 (live cohort) |

The chart collections are small summaries that `queries/run_mongo.py` writes and `load_mongo.py --target atlas` copies to Atlas. Their names and fields are frozen once the charts exist, so tell Scott before anyone renames a field.

The **live** rows are PROVISIONAL until the live cutoff: after Mon 2026-10-26 5:05 PM PT (2026-10-27 00:05 UTC). The history rows are final. Charts 1 and 2 use the history cohort, so you can make them now. The charts contain no editor names.

**Check numbers.** The checks below name keys of `report/FACTS.md` (for example `mongo_q3_history_lt_1min_pct`) instead of numbers. Look up the value there. FACTS gives percent (17.6), and Charts shows a fraction (0.176) until you set the number format to percent. Copy the live values again after the live refresh.

---

## The fields of the 4 chart collections

These are the real fields in the local MongoDB. Atlas has the same documents. Every document also has `_id` (text, for example `history:00:bot`) and `updated_at` (a date).

**`chart_q1_hour_kind`**: 147 documents, one per cohort x hour x user kind (history: 24 hours x 3 kinds + 3 "unknown" = 75; live: 72).

| field | type | values |
|---|---|---|
| `cohort` | text | `history`, `live` |
| `hour_utc` | number | 0 to 23 (hour of the edit, UTC) |
| `user_kind` | text | `bot`, `registered`, `temporary`, `unknown` |
| `edits` | number | revisions in the cell |
| `reverted` | number | of those, reverted (history: within 20 days; live: within 4 days) |
| `revert_rate` | number | reverted / edits, from 0 to 1 |

**`chart_q3_time_to_revert`**: one document per cohort and bucket.
- `history`: 11 buckets, reverts within 20 days.
- `history_4d`: the same history reverts, cut at 4 days. Use it to compare with the live cohort on the same horizon.
- `live`: reverts within 4 days. The live cohort is also still censored (not every edit has been followed for 4 days yet) until 2026-10-27 00:05 UTC.

| field | type | values |
|---|---|---|
| `cohort` | text | `history`, `history_4d`, `live` |
| `bucket` | text | `<1 min`, `1-5 min`, `5-15 min`, `15-60 min`, `1-6 h`, `6-24 h`, `1-2 d`, `2-4 d`, `4-7 d`, `7-14 d`, `14-20 d` |
| `bucket_order` | number | 1 to 11, the bucket in time order |
| `bucket_sorted` | text | `01 <1 min`, `02 1-5 min`, ... `11 14-20 d`: a label that sorts in time order as text |
| `bucket_lower_s`, `bucket_upper_s` | number | the bucket edges in seconds, [lower, upper) |
| `n` | number | reverted revisions in the bucket |
| `share` | number | n / all reverted revisions of the cohort row (`history_4d`: of the history reverts within 4 days) |
| `cum_share` | number | the running total of `share` |

**`chart_q5_known_by`**: 72 documents, one per cohort x user kind x wait.

| field | type | values |
|---|---|---|
| `cohort` | text | `history`, `live` |
| `user_kind` | text | `all`, `bot`, `registered`, `temporary` |
| `wait` | text | `0`, `1 min`, `5 min`, `15 min`, `1 h`, `6 h`, `1 d`, `2 d`, `4 d` |
| `wait_s` | number | the same wait in seconds |
| `wait_sorted` | text | `01 0`, `02 1 min`, ... `09 4 d`: a label that sorts in time order as text |
| `n_edits` | number | revisions in the group |
| `n_reverted_4d` | number | of those, reverted within 4 days |
| `revert_rate_4d` | number | n_reverted_4d / n_edits |
| `known` | number | reverts already visible after this wait |
| `share_known` | number | known / n_reverted_4d, from 0 to 1 |

**`chart_q5_risk_deciles`** (live cohort): one document per risk decile, plus one `no score` group. The `no score` group holds the edits without a revert-risk score: page creations, plus edits whose score event was not captured.

| field | type | values |
|---|---|---|
| `group` | text | `decile 1` to `decile 10`, `no score` |
| `decile` | number or empty | 1 to 10; empty for `no score` |
| `risk_min`, `risk_max` | number or empty | the range of the revert-risk score in the decile |
| `n` | number | revisions |
| `n_reverted_4d`, `revert_rate_4d` | number | reverted within 4 days, and the rate |
| `median_T_s` | number | median time to revert, in seconds |
| `at_risk_now`, `reverted_after_now`, `p_now`, `ci_lo_now`, `ci_hi_now` | number | the decision table for "decide now" |
| the same with `_1h` and `_1d` | number | the decision table after waiting 1 hour and 1 day |

---

## Part A: open Charts and add the data source (about 5 minutes)

1. Open https://cloud.mongodb.com and the project. Click "Charts" (a tab at the top, or in the left menu). The first time, click "Activate Atlas Charts" (or "Activate Now").
   You should see the Charts home with "Dashboards" and "Data Sources".
2. Open "Data Sources" and click "+ Add Data Source". Choose the cluster `truthlag`, then the database `truthlag`, and tick the 4 `chart_...` collections (or the whole database). Click "Finish" (or "Connect").
   - Only a **Project Owner** can add a data source. If you do not see the button, ask Scott to make you Project Owner.
   You should see `truthlag.chart_q1_hour_kind` and the 3 others in the list.
3. Open "Dashboards" and click "+ Add Dashboard". Title: `Truth Lag EC HW2 (Group 9)`. Click "Save".

## Part B: chart 1, Mongo Q1 (about 15 minutes)

4. In the dashboard, click "Add Chart". In the data source list at the top left, choose `truthlag.chart_q1_hour_kind`.
5. Chart type: **Heatmap** (in the "Grid" group).
6. Drag the fields from the field list to the channels:
   - **X Axis**: `hour_utc`. Turn **Binning** on with a bin size of **1** (one column per hour), or turn binning off. Sort: by category, ascending (0 to 23).
   - **Y Axis**: `user_kind`. Sort: by value, descending (temporary at the top).
   - **Intensity**: `revert_rate`, aggregate **Mean**.
7. **Filters** (the "Filter" tab): drag `cohort` and keep only `history`. Drag `user_kind` and untick `unknown`.
   - Why: after these 2 filters, every cell has exactly one document, so "Mean" is the real rate. Without the cohort filter, a cell would mix the history and live rates. The `unknown` kind has only 3 edits (all reverted), so its cells would be 100% and make the other colours hard to read.
8. **Customize** (the paint brush): Title: `Mongo Q1: revert rate by hour of day (UTC) and user kind, history cohort (2026-09-08 to 2026-09-10)`. X axis title `Hour of day (UTC)`, Y axis title `User kind`. Number format of the intensity: percent, 1 decimal.
9. Check before you save:
   - Temporary accounts are between `mongo_q1_history_temporary_hourly_min_pct` and `mongo_q1_history_temporary_hourly_max_pct` in every hour.
   - Registered editors are between `mongo_q1_history_registered_hourly_min_pct` and `mongo_q1_history_registered_hourly_max_pct`.
   - Every cell must match the history rows of `ec-hw2/results/mongo_q1_revert_rate_by_hour.md`.
10. Click "Save and close".

**Other option (grouped bar):** chart type "Column" > "Grouped". X Axis `hour_utc` (binning off), Y Axis `revert_rate` (Mean), Series `user_kind`. Same filters and title.

## Part C: chart 2, Mongo Q3 (about 15 minutes)

11. "Add Chart", data source `truthlag.chart_q3_time_to_revert`. Chart type: **Column** > **Grouped**.
12. **Use the stored label `bucket_sorted`.** It is already in the data, and it sorts in time order (`01 <1 min` ... `11 14-20 d`). Do not make a calculated field with the same name.
13. Channels:
    - **X Axis**: `bucket_sorted`. Sort: by category, ascending.
    - **Y Axis**: `share`, aggregate **Sum** (one document per bar, so Sum is the value).
    - **Series**: `cohort`.
14. **Filter** on `cohort`. Choose one of two versions:
    - **History only (20 days)**: keep only `history`. You can make this one now.
    - **Both cohorts on the same 4-day horizon**: keep only `history_4d` and `live`. Never put `history` next to `live`: their shares have different denominators (20 days and 4 days). Make this version after the live refresh, or mark it PROVISIONAL.
15. **Customize**:
    - Title: `Mongo Q3: time to revert (share of reverted revisions per bucket)`.
    - Subtitle or caption: `history: reverts within 20 days. history_4d and live: reverts within 4 days. The live cohort is capped at 4 days and censored until 2026-10-27 00:05 UTC.`
    - X axis title `Time to revert`, Y axis title `Share of reverted revisions`. Number format: percent.
16. Check:
    - The `history` bar for `01 <1 min` is `mongo_q3_history_lt_1min_pct`.
    - The `history` cumulative share at the end of `04 15-60 min` is `history_T_within_1h_pct`.
    - The `history_4d` cumulative share at the end of `04 15-60 min` is about `mongo_q5_history_known_1h_pct` (both are history reverts within 4 days).
    - The `live` bar for `01 <1 min` is `mongo_q3_live_lt_1min_pct` (PROVISIONAL).
    - Every bar must match `ec-hw2/results/mongo_q3_time_to_revert.md`.
17. Click "Save and close".

**Fallback for an older Atlas copy without `bucket_sorted`.** In the field list, click "+ Add Field" > "Calculated". Give it a **new** name, for example `bucket_label`. Value expression (paste it on one line):
```
{"$concat": [{"$substrCP": [{"$toString": {"$add": [101, {"$indexOfArray": [[0, 60, 300, 900, 3600, 21600, 86400, 172800, 345600, 604800, 1209600], "$bucket_lower_s"]}]}}, 1, 2]}, " ", "$bucket"]}
```
The numbers in the list are the lower bucket edges of `config.LAG_GRID_S`. Then use `bucket_label` on the X axis. Ask Scott to load Atlas again, so the stored field is there.

## Part D (optional): charts 3 and 4, Mongo Q5 (after the live refresh on Mon 2026-10-26)

**Chart 3, the known-by curve** (`truthlag.chart_q5_known_by`):
- Chart type: **Line** > **Discrete Line**.
- **X Axis**: `wait_sorted` (stored in the data), sort by category ascending. **Y Axis**: `share_known`, aggregate Mean. **Series**: `cohort`.
- **Filter**: `user_kind` = `all` only (then each point is one document).
- Title: `Mongo Q5: share of the 4-day reverts already visible after waiting`. Y axis in percent.
- Check (live: PROVISIONAL until the live cutoff):
  - after `05 1 h`: history `mongo_q5_history_known_1h_pct`, live `mongo_q5_live_known_1h_pct`
  - after `07 1 d`: history `mongo_q5_history_known_1d_pct`, live `mongo_q5_live_known_1d_pct`.
- Fallback for an older Atlas copy without `wait_sorted`: a calculated field with a new name (for example `wait_label`), with this expression. The numbers are the values of `config.WAIT_POINTS_S`.
  ```
  {"$concat": [{"$substrCP": [{"$toString": {"$add": [101, {"$indexOfArray": [[0, 60, 300, 900, 3600, 21600, 86400, 172800, 345600], "$wait_s"]}]}}, 1, 2]}, " ", "$wait"]}
  ```

**Chart 4, the risk deciles** (`truthlag.chart_q5_risk_deciles`):
- Chart type: **Column** > **Grouped**.
- **X Axis**: `decile`, binning off, sort by category ascending. **Y Axis**: `revert_rate_4d`, aggregate Sum.
- **Filter**: `group` without `no score` (or `decile` not empty).
- Title: `Mongo Q5: revert rate within 4 days by revert-risk decile (live cohort)`. Y axis in percent.
- Check (PROVISIONAL): decile 1 is `risk_bottom_decile_revert_rate_pct`, and decile 10 is `risk_top_decile_revert_rate_pct`. Every bar must match `ec-hw2/results/mongo_q5_risk_deciles.md`.

## Part E: save as PNG and upload (about 5 minutes)

18. **Fresh data first.** On the free tier, a dashboard refreshes its data only **every 4 hours**. After a new load (for example the live refresh), open each chart in the chart builder (the pencil "Edit chart"): the builder always reads fresh data. Check the numbers again, then save.
19. **Save as PNG.** On the dashboard, right-click the chart > **Save as PNG** (or open the chart menu "..." at the top right of the chart > "Download" > "PNG"). Save it into `ec-hw2/results/figures/` with the collection name:
    - `chart_q1_hour_kind.png`
    - `chart_q3_time_to_revert.png`
    - optional: `chart_q5_known_by.png`, `chart_q5_risk_deciles.png`
20. **Upload it yourself** (so the commit carries your name):
    1. Open https://github.com/scottn66/truth-lag and switch the branch to `ec-hw2`.
    2. Open `ec-hw2/results/figures/`, click "Add file" > "Upload files", and drag the PNG files in.
    3. Write a message such as `Add Atlas Charts Q1 and Q3`.
    4. Choose "Commit directly to the ec-hw2 branch" and click "Commit changes".
    You should see the files in the folder, with your name on the last commit.
21. Optional: take one screenshot of the whole dashboard as `atlas_charts_dashboard.png`, for the report.

## If something goes wrong

| problem | what to do |
|---|---|
| no "+ Add Data Source" button | You are not a Project Owner. Ask Scott (`ATLAS_SETUP.md`, step 3). |
| the collections are not in the data source list | The load (`ATLAS_SETUP.md`, part E) has not run, or it ran before `queries/run_mongo.py` made the chart collections. Ask Scott to run part E again. |
| `bucket_sorted`, `wait_sorted` or the `history_4d` rows are missing | Atlas has an older load. Ask Scott to run `ATLAS_SETUP.md` step 17 again, or use the fallback calculated field. |
| the numbers in the chart are old | See step 18: open the chart builder. |
| a cell shows 100% in chart 1 | You forgot to untick `unknown` (step 7). |
| the bars of chart 2 are in a strange order | Use `bucket_sorted` (step 12), sorted by category. |
| the expression gives an error | Paste it again on one line, with straight quotes `"`, not curly quotes. |
