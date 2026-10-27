# Mongo Q3: time to revert ($bucket on the lag grid)

Mongo Q3 (spec 3.3): the distribution of the time to revert T_s (seconds from the reverted revision to the reverting revision), for revert_links with within_followup. Three series (field cohort): 'history' = history reverts within 20 days; 'live' = live reverts within 4 days; 'history_4d' = the history reverts with T_s <= 345600 s (4 days), with the shares computed again on that smaller total. Compare 'live' with 'history_4d' (the same 4-day horizon), not with 'history'. The live T is also cut by the capture until 2026-10-27T00:05:00+00:00 (provisional). One $bucket per series inside a $facet, with the lag grid of config.py as boundaries [lower, upper). The default bucket 'over_20d' must stay empty (run_mongo.py asserts this). Output: cohort (series), bucket label, bucket_lower_s, bucket_upper_s, n, share of the series, cumulative share. Empty buckets are not listed.

Rows: 27. Median time: 50.5 ms (7 warm runs after 1 warm-up).
Made by `ec-hw2/queries/run_mongo.py` on 2026-10-27 21:27 UTC (data-v2). Full table: `mongo_q3_time_to_revert.csv`.

| cohort     | bucket    |   bucket_lower_s |   bucket_upper_s |    n |     share |   cum_share |   bucket_order | bucket_sorted   |
|------------|-----------|------------------|------------------|------|-----------|-------------|----------------|-----------------|
| history    | <1 min    |                0 |               60 | 3470 | 0.176142  |    0.176142 |              1 | 01 <1 min       |
| history    | 1-5 min   |               60 |              300 | 2722 | 0.138173  |    0.314315 |              2 | 02 1-5 min      |
| history    | 5-15 min  |              300 |              900 | 1542 | 0.0782741 |    0.392589 |              3 | 03 5-15 min     |
| history    | 15-60 min |              900 |             3600 | 2088 | 0.10599   |    0.498579 |              4 | 04 15-60 min    |
| history    | 1-6 h     |             3600 |            21600 | 3078 | 0.156244  |    0.654822 |              5 | 05 1-6 h        |
| history    | 6-24 h    |            21600 |            86400 | 2797 | 0.14198   |    0.796802 |              6 | 06 6-24 h       |
| history    | 1-2 d     |            86400 |           172800 | 1028 | 0.0521827 |    0.848985 |              7 | 07 1-2 d        |
| history    | 2-4 d     |           172800 |           345600 |  921 | 0.0467513 |    0.895736 |              8 | 08 2-4 d        |
| history    | 4-7 d     |           345600 |           604800 |  808 | 0.0410152 |    0.936751 |              9 | 09 4-7 d        |
| history    | 7-14 d    |           604800 |          1209600 |  852 | 0.0432487 |    0.98     |             10 | 10 7-14 d       |
| history    | 14-20 d   |          1209600 |          1728001 |  394 | 0.02      |    1        |             11 | 11 14-20 d      |
| history_4d | <1 min    |                0 |               60 | 3470 | 0.196645  |    0.196645 |              1 | 01 <1 min       |
| history_4d | 1-5 min   |               60 |              300 | 2722 | 0.154256  |    0.350901 |              2 | 02 1-5 min      |
| history_4d | 5-15 min  |              300 |              900 | 1542 | 0.0873852 |    0.438286 |              3 | 03 5-15 min     |
| history_4d | 15-60 min |              900 |             3600 | 2088 | 0.118327  |    0.556613 |              4 | 04 15-60 min    |
| history_4d | 1-6 h     |             3600 |            21600 | 3078 | 0.17443   |    0.731044 |              5 | 05 1-6 h        |
| history_4d | 6-24 h    |            21600 |            86400 | 2797 | 0.158506  |    0.88955  |              6 | 06 6-24 h       |
| history_4d | 1-2 d     |            86400 |           172800 | 1028 | 0.0582568 |    0.947807 |              7 | 07 1-2 d        |
| history_4d | 2-4 d     |           172800 |           345600 |  921 | 0.0521931 |    1        |              8 | 08 2-4 d        |
| live       | <1 min    |                0 |               60 | 4148 | 0.232798  |    0.232798 |              1 | 01 <1 min       |
| live       | 1-5 min   |               60 |              300 | 2830 | 0.158828  |    0.391626 |              2 | 02 1-5 min      |
| live       | 5-15 min  |              300 |              900 | 1428 | 0.0801437 |    0.47177  |              3 | 03 5-15 min     |
| live       | 15-60 min |              900 |             3600 | 1923 | 0.107925  |    0.579695 |              4 | 04 15-60 min    |
| live       | 1-6 h     |             3600 |            21600 | 3076 | 0.172634  |    0.752329 |              5 | 05 1-6 h        |
| live       | 6-24 h    |            21600 |            86400 | 2532 | 0.142103  |    0.894433 |              6 | 06 6-24 h       |
| live       | 1-2 d     |            86400 |           172800 |  763 | 0.0428219 |    0.937254 |              7 | 07 1-2 d        |
| live       | 2-4 d     |           172800 |           345600 | 1118 | 0.0627455 |    1        |              8 | 08 2-4 d        |

