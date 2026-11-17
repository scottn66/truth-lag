#!/usr/bin/env python
# coding: utf-8

# ## **Privacy Analysis: k-Anonymity, l-Diversity, and Suppression** ##

# This notebook evaluates whether released Gold extracts could make an editor easier to single out. 
# 
# It checks k-anonymity using the number of distinct editors in each released row, 
# 
# evaluates l-diversity for the sensitive attribute reverted_4d, 
# 
# and measures the cost of suppressing small or homogeneous groups.

# ## **1. Load the Gold exports** ##
# 
# group_sizes_by_kind_hour.csv describes editor groups by cohort, editor kind, date, and hour. 
# 
# page_revert_summary.parquet describes page-level release rows.
# 
# The column distinct_editors is the group size used for the k-anonymity check.

# In[2]:


from pathlib import Path
import pandas as pd
from IPython.display import display

EXPORTS = Path(
    "truthlag_exports_2026-11-15/data/exports"
)

grid = pd.read_csv(
    EXPORTS / "group_sizes_by_kind_hour.csv"
)

page = pd.read_parquet(
    EXPORTS / "page_revert_summary.parquet"
)


grid = grid.rename(
    columns={"revisions": "edits"}
)

KS = (2, 5, 10, 20)
K = 5

print("Hourly grid rows:", len(grid))
print("Page summary rows:", len(page))


# ## **2. k-Anonymity check** ##
# A row satisfies k-anonymity when at least k distinct editors are represented in that row. 
# 
# We test k = 2, 5, 10, and 20. The main threshold is k = 5. 
# 
# Rows with distinct_editors < k are flagged as below the threshold.

# In[3]:


def k_table(df, table_name):
    rows = []

    for k in KS:
        below_k = df["distinct_editors"] < k

        rows.append({
            "table": table_name,
            "k": k,
            "rows": len(df),
            "rows_below_k": int(below_k.sum()),
            "rows_below_k_pct": round(
                100 * below_k.mean(), 2
            ),
            "edits_in_those_rows_pct": round(
                100
                * df.loc[below_k, "edits"].sum()
                / df["edits"].sum(),
                2,
            ),
        })

    return rows


k_summary = pd.DataFrame(
    k_table(grid, "kind x date x hour")
    + k_table(page, "page summary")
)

display(k_summary)


# ## **3. l-Diversity check** ##
# l-Diversity is a supplementary check. 
# 
# It asks whether a group contains both reverted and non-reverted edits. 
# 
# Here, reverted_4d is the sensitive attribute. A row is 2-diverse when 0 < reverted_4d < edits; 
# 
# a row whose edits are all reverted is homogeneous and can reveal sensitive information.

# In[4]:


def diversity(df, table_name):
    edits = df["edits"]
    reverted = df["reverted_4d"]

    both = (
        (reverted > 0)
        & (reverted < edits)
    )

    all_reverted = reverted == edits
    none_reverted = reverted == 0

    return {
        "table": table_name,
        "rows": len(df),
        "two_diverse_pct": round(
            100 * both.mean(), 2
        ),
        "all_reverted_rows": int(
            all_reverted.sum()
        ),
        "all_reverted_pct": round(
            100 * all_reverted.mean(), 3
        ),
        "none_reverted_pct": round(
            100 * none_reverted.mean(), 2
        ),
        "all_reverted_and_single_editor": int(
            (
                all_reverted
                & (df["distinct_editors"] == 1)
            ).sum()
        ),
    }


l_diversity_summary = pd.DataFrame([
    diversity(grid, "kind x date x hour"),
    diversity(page, "page summary"),
])

display(l_diversity_summary)


# ## **4. Suppression and its statistical cost** ##
# We use k = 5 and compare three release rules. 
# 
# Rule A removes rows with fewer than five editors. 
# 
# Rule B also removes rows whose edits were all reverted. 
# 
# Rule C keeps only rows that satisfy k-anonymity and are 2-diverse. 
# 
# We measure how many rows, edits, and reverts remain, and whether the released revert rate differs from the true rate.

# In[5]:


def release(df, rule, k=5):
    keep = df["distinct_editors"] >= k

    if rule == "B":
        keep &= df["reverted_4d"] < df["edits"]

    if rule == "C":
        keep &= (
            (df["reverted_4d"] > 0)
            & (df["reverted_4d"] < df["edits"])
        )

    return df[keep]


# In[6]:


suppression_rows = []

for cohort, data in page.groupby("cohort_id"):
    true_rate = (
        100 * data["reverted_4d"].sum()
        / data["edits"].sum()
    )

    for rule in ["A", "B", "C"]:
        released = release(data, rule, K)

        released_rate = (
            100 * released["reverted_4d"].sum()
            / released["edits"].sum()
        )

        suppression_rows.append({
            "cohort": cohort,
            "rule": rule,
            "rows_kept_pct": round(
                100 * len(released) / len(data),
                2,
            ),
            "edits_kept_pct": round(
                100
                * released["edits"].sum()
                / data["edits"].sum(),
                2,
            ),
            "reverts_kept_pct": round(
                100
                * released["reverted_4d"].sum()
                / data["reverted_4d"].sum(),
                2,
            ),
            "true_revert_rate_pct": round(
                true_rate, 2
            ),
            "released_revert_rate_pct": round(
                released_rate, 2
            ),
            "bias_points": round(
                released_rate - true_rate,
                2,
            ),
        })

suppression_summary = pd.DataFrame(
    suppression_rows
)

display(suppression_summary)


# ## **5. Overall Analysis** ##
# 
# 1. The privacy analysis shows that the hourly group grid and the page-level summary have very different disclosure risks.
# 
# 2. For the hourly group grid, only 3.95% of rows fall below k = 5, and these rows contain only 0.83% of the edits. This suggests that the hourly grid is relatively safe to release at the chosen threshold.
# 
# 3. The page-level summary is much more vulnerable. At k = 5, 98.42% of page rows fall below the threshold, and these rows contain 85.33% of the edits. Therefore, releasing page-level rows directly could make individual editors easier to single out.
# 
# 4. The l-diversity results support this conclusion. The hourly grid is 2-diverse for 92.69% of its rows, while only 4.80% of page-summary rows are 2-diverse. Page-level rows are therefore often homogeneous with respect to the reverted outcome.
# 
# 5. Suppression improves privacy, but it also reduces data utility and can introduce statistical bias. Because suppression preferentially retains busy pages, and busy pages are more likely to be reverted, the released revert rate is biased upward compared with the true rate. This shows that removing small or homogeneous page groups changes the composition of the released data.
# 
# 6. Overall, the hourly group grid is a safer release than the page-level summary. A page-level release should use additional protection, such as generalization, suppression, or noise, rather than publishing the raw page rows directly.

# ## **6. Save outputs** ##

# In[7]:


OUTPUT_DIR = Path("outputs/k_anonymity")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

k_summary.to_csv(
    OUTPUT_DIR / "k_summary.csv",
    index=False,
)

l_diversity_summary.to_csv(
    OUTPUT_DIR / "l_diversity_summary.csv",
    index=False,
)

suppression_summary.to_csv(
    OUTPUT_DIR / "suppression_summary.csv",
    index=False,
)

print("Saved:", OUTPUT_DIR / "k_summary.csv")
print("Saved:", OUTPUT_DIR / "l_diversity_summary.csv")
print("Saved:", OUTPUT_DIR / "suppression_summary.csv")


# 
