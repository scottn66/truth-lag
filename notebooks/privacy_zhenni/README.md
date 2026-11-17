# Privacy analysis (Zhenni)

Zhenni's k-anonymity, l-diversity, suppression and Laplace-noise analysis. Her files were moved here from
`Privacy analysis-Zhenni/` at the repo root; the code is unchanged.

| File | What it is |
|---|---|
| `privacy_k_anonymity_I-Diversity_Suppression.ipynb` / `.py` | k-anonymity, l-diversity and suppression on the Gold exports |
| `privacy_laplace.ipynb` / `.py` | Laplace noise on the E(L) counts |
| `outputs/k_anonymity/*.csv`, `outputs/laplace/*` | The summary tables and figure the notebooks write |
| `TruthLag_privacy_analysis_report_zhenni.md` | Her report section |
| `TruthLag_Privacy_Slides_Content.md` | Her slide content |
| `TruthLag_MongoDB_Charts_analysis.md` | Her notes on the MongoDB Charts dashboard |

## How to run

The notebooks read the team exports from `truthlag_exports_2026-11-15/data/exports` and write to `outputs/`,
both relative to the folder they are run from. Unzip the exports zip into this folder (or link `data/exports`
to that path) and run the notebooks from this folder.

The numbers in `outputs/` are collected into `docs/final/results.json` under `zhenni.privacy.*`
by `scripts/make_results.py`.
