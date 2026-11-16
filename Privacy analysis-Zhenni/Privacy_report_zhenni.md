**TruthLag\_Privacy\_Analysis  Zhenni**

**Source: notebooks**: privacy\_k\_anonymity\&I-Diversity\&Suppression.ipynb             
                                   privacy\_laplace.ipynb  
               **figure:** docs/final/figures/privacy\_laplace.png.

**Tables checked:** group\_sizes\_by\_kind\_hour.csv(1,875 rows),    
                             page\_revert\_summary.parquet ( 1,559,483 rows),   
                             mart\_el\_curve.csv (153 rows).

**Overview of Privacy Analysis:** This section presents a comprehensive privacy analysis designed to evaluate and safeguard the release of Wikipedia editing data against re-identification and inference risks through a progressive, multi-layered framework:

First, k-anonymity inspects structural sparsity to ensure that each aggregated group contains a sufficient number of records, preventing individuals from being singled out.

Second, ***$l$***\-diversity examines the distribution of sensitive attributes (such as revert status) within groups to protect against attribute disclosure and homogeneity.

Third, Data Suppression acts as a hard-filtering mechanism to remove non-compliant rows that fail these privacy thresholds, allowing us to quantify information loss and measure statistical bias.

Finally, Laplace noise (differential privacy) is applied to continuous numerical metrics—specifically the Truth Lag curves E(L)—as an alternative to destructive suppression, mathematically bounding privacy loss while preserving macroeconomic data utility.

**K-anonymity:** This section evaluates the k-anonymity of the two release tables (group\_sizes\_by\_kind\_hour.csv and page\_revert\_summary.parquet) across thresholds k in {2, 5, 10, 20} (with k \= 5 as the primary threshold) to check whether the current data bucketing exposes individual editors to re-identification risks.

Hourly Group Grid:

* $k=2$: 0.37% rows below threshold (suppressing rows retains 99.99% of edits).  
* $k=5$ (Primary threshold): 3.95% rows below threshold (suppressing rows retains 99.17% of edits).  
* $k=10$: 11.15% rows below threshold (suppressing rows retains 96.96% of edits).  
* $k=20$: 33.44% rows below threshold (suppressing rows retains 74.60% of edits).

Page-Level Summary:

* $k=2$: 81.63% rows below threshold (suppressing rows retains 47.44%of edits).  
* $k=5$ (Primary threshold): 98.42% rows below threshold (suppressing rows retains 14.67% of edits).  
* $k=10$: 99.75% rows below threshold (suppressing rows retains 5.98% of edits).  
* $k=20$: 99.95% rows below threshold (suppressing rows retains 2.82% of edits).

*Note on Single Editors:* In the page summary, 0.14% ($2,170$ rows) consist of a single editor with entirely all-reverted edits, representing extreme disclosure vulnerability.

***$l$*****\-diversity:** This section evaluates l \= 2 diversity for the sensitive attribute reverted\_4d to check for group homogeneity.

$l=2$**:** 92.6% of grid cells and 4.80% of page rows hold both reverted and not-reverted edits. $2,526$ page rows hold only reverted edits, $2,170$ of them from a single editor.

**Suppression Rules & Statistical Bias:** This section evaluates the impact of Data Suppression—a hard-filtering mechanism used to enforce structural privacy by removing non-compliant records or groups. Within our testing framework, suppression rules vary in strictness: Rule A enforces structural k-anonymity (requiring at least 5 editors); Rule B enforces k-anonymity while additionally removing rows where all edits were reverted (reverted\_4d \== edits); and Rule C applies a strict composite filter requiring both k-anonymity and 2-diversity (0 \< reverted\_4d \< edits).

Considering that page-level sparse data suffers the most severe degradation under hard filtering, we focus on the most representative dataset—live\_ext (Live Extended)—and showcase Rule A versus Rule C: 

| Suppression Rule | Rows Kept  | Edits Kept  | Reverts Kept  | Released Revert Rate (True: 4.71%)  |
| :---: | :---: | :---: | :---: | :---: |
| **At least $5$ editors and 2-diverse (Rule C)**  | 1.04%  | 10.47%  | 42.05% | 18.92%  |
| **At least $5$ editors (Rule A)**  | 1.80% | 16.44%  | 42.08%  | 12.05%  |

Key Takeaway: Suppression alone biases the page-level release upward: because only busy, high-conflict pages survive, the released data suffers from severe information loss and an inflated revert rate compared to the baseline.

**Laplace Noise on the E(L) Counts (1,000 Trials per epsilon):**This section evaluates the application of Laplace noise (differential privacy) to continuous numerical metrics—specifically the Truth Lag curves E(L)—as a non-destructive alternative to aggressive data suppression. To quantify the data utility and privacy trade-off, we simulate the Laplace mechanism across varying privacy budgets (ϵ=0.1,0.5, and 1.0) over 1,000independent trials. The resulting Mean Absolute Error (MAE) measures data distortion across different user cohorts and event scales (𝑛), demonstrating how calibrated noise mathematically bounds privacy loss while preserving high numerical utility.

To illustrate how data scale ($n$) affects utility under differential privacy, we select representative cohorts ranging from large-scale streams (live\_ext) to smaller subgroups (live temporary accounts), evaluating their Mean Absolute Error (MAE) across varying privacy budgets. 

| Series / User Kind | Eventual Reverts ($n$)  | MAE ($\epsilon =0.1$)  | MAE ($\epsilon =0.5$)  | MAE ($\epsilon =1.0$)  |
| :---- | :---- | :---- | :---- | :---- |
| **live\_ext, stream, all editors** | **$112,937$**  | **$0.000145$**  | **$0.000029$**  | **$0.000015$**  |
| **live, stream, all editors** | **$17,818$**  | **$0.000927$**  | **$0.000182$**  | **$0.000093$** |
| **live, stream, temporary accounts** | **$9,772$**  | **$0.001676$**  | **$0.000354$**  | **$0.000171$**  |
| **live, stream, bots** | **$141$**  | **$0.154684$**  | **$0.023457$**  | **$0.012041$**  |

Key takeaway: Evaluated across $1,000$ simulation trials per privacy budget ($\epsilon$), the Laplace mechanism preserves high data utility for large cohorts, where the resulting Mean Absolute Error (MAE) is negligible. However, for extremely small cohorts (such as the bot series with $n=141$), the added noise dominates the small sample size, severely distorting the $E(L)$ measurement and highlighting the inherent utility limitations of differential privacy on sparse subgroups. 

**Did you find or come across solutions to similar problems by using Generative AI or other sources?** Yes.  
**Tool/Model:** Gemini 3 Flash-lite  
**How it was used:** Generative AI was utilized strictly as an editorial and conceptual collaborator for clarifying privacy analysis frameworks ($k$\-anonymity, $l$\-diversity, data suppression bias, and Laplace noise/differential privacy), the optimal selection of epsilon, code logic review, syntax guidance, and verifying potential structural pitfalls in data processing scripts, refining professional technical terminology. All analytical framework decisions, interpretation of statistical results, data selections, and final conclusions were independently validated and established by the author.   
**Prompt:** 1.Can you help me clarify the conceptual logic and trade-offs between data suppression and differential privacy (specifically Laplace noise and MAE evaluation)?  
2\. How can I structure narrative explanations for statistical bias, such as the upward bias in released revert rates caused by hard filtering (Rules A, B, and C)?  
3: Can you review my Python data processing logic to check for potential performance errors and loop-indentation pitfalls?  
4: Could you help refine the technical descriptions for privacy metrics, evaluation rules, and the privacy budget ($\epsilon$) selection rationale?  
5: Can you assist in formatting and polishing markdown/document table layouts and visual alignments?

**Difficulties & Best Practice**  
**1\. Difficulties:** Distinguishing between and appropriately applying distinct privacy paradigms—determining when to deploy structural suppression ($k$\-anonymity / $l$\-diversity) versus differential privacy (Laplace noise) across vastly differentDatasets. Matching the right protection method to the correct data granularity without destroying analytical value was a major architectural challenge.   
**Best Practice:**Adopted a tiered defensive strategy—applying structural suppression to mitigate disclosure risks in vulnerable, sparse page-level rows, while applying the Laplace mechanism to continuous metric curves ($E(L)$) to quantitatively bound utility loss via Mean Absolute Error (MAE). 

**2\. Difficulties:** Faced with choosing the "best" epsilon without a universal mathematical optimum, it was challenging to weigh how much privacy protection to enforce versus how much error (MAE) is acceptable for downstream utility, especially when fixed noise disproportionately impacts small cohorts (like bots with n \= 141).  
**Best Practice:** Adopted a multi-point experimental gradient (\$\\epsilon \= 0.1, 0.5, 1.0\$) to map out the error (MAE) curve across different data scales. This allowed for a structured evaluation of the trade-off inflection points rather than guessing a single "optimal" value.

**3\. Difficulties:** Laplace noise is random, single-run evaluations risk capturing noise anomalies rather than true utility loss, yielding unstable and unreliable MAE metrics.  
**Best Practice:** Executed 1,000 independent simulation trials per privacy budget to neutralize single-draw random noise fluctuations, ensuring that the reported MAE metrics provide a statistically stable and robust evaluation of utility loss.

