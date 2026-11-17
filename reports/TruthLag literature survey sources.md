# Five literatures bracket one unmeasured revert-delay curve

The research notes verify about 140 distinct published sources across the five survey areas, and together they leave one specific thing unreported: for Wikipedia reverts, the share of eventual labels still missing as a function of how long one waits, measured by comparing a live stream with a later snapshot. Stream learning assumes or simulates label delay, advertising and fraud work model it to repair training, statistics corrects counts for it (reporting delay, nowcasting, data vintages), and Wikipedia research reports time-to-revert as medians computed afterwards from complete history (**2.8 minutes** for mass deletions in 2003 data, **12.4 minutes** for all reverted edits in 2011, **21.4 minutes** with ClueBot NG offline). The systems papers define mechanisms for late data (watermarks, refinement modes, Open/Closed/Complete partitions, bitemporal tables) but none measures the error of an open result against the wait. All 23 entries in the existing reference list of `docs/final/report_draft.md` exist and are correctly attributed; the corrections are missing pages, DOIs, subtitles and author counts, plus one venue label ([17]), one page range ([25]) and one year question ([24]). The gap is a "not found in the sources checked" claim, so the survey must say "to our knowledge", and it must be narrowed if the unsearched post-2020 Wikimedia material turns out to contain a delay curve. This document is a source guide: the team writes the survey text; nothing here is meant to be pasted.

## How to read the entries and what each status label means

Every entry gives the full citation as the notes confirmed it, the page the record was confirmed on, what the source found or defined, how it relates to revert-label delay, and any flags. Source IDs carry an area prefix (D delayed labels, W Wikipedia, S streaming and systems, L MinHash and LSH, P privacy); they are local to this guide and are not IEEE reference numbers. The BibTeX keys in the appendix follow the same order.

| Label | Meaning in this guide |
|---|---|
| Confirmed | The bibliographic record was opened during the research session (usually the Crossref DOI record, or an official page). |
| Abstract-level | Findings come from the abstract only; the body was not read. |
| Full text read | The paper PDF or official page was read; figures come from the text. |
| [RECALL] | A standard result stated from the researcher's prior knowledge; the full text was not opened. Not confirmed. Check before quoting. |
| UNVERIFIED | A detail the notes could not confirm on any opened page. Not confirmed. Do not cite as fact. |

DBLP and the ACM Digital Library were unreachable in every research session, so no entry rests on them. Conference cities are from memory throughout and are flagged where they appear.

## Delayed labels: the delay is assumed, modelled or corrected, but not plotted for reverts

**What the literature establishes.** Stream learning has treated delayed labels since 2008-2010 as a problem for the learner: what to do while the label is missing and how to evaluate a classifier fairly. On abstract evidence, none of those papers reports an empirical delay distribution for a real labelling process; the delay is an input (fixed, simulated, or "never arrives"). "Verification latency" (D5, D11, D23) and "delayed labels/labelling" (D1, D2, D4, D6, D7, D9) name the same thing, so the survey should pick one term and note the synonym. Advertising work is the closest structural match, because only the positive label "arrives" and a negative is inferred from waiting long enough; a follow-up window is therefore part of the label's definition (up to a month in D12, 4 days in TruthLag). Statistics supplies three framings that fit the project's E(L): the survival function under censoring (D16), occurred-but-not-yet-reported events with a reporting-delay distribution (D17-D19b), and real-time data vintages with revisions (D20, D21). In those terms E(L), the share of eventual reverts not yet known after wait L within a 4-day window, is the survival function of a right-truncated reporting delay; reverts that arrive after 4 days are outside both numerator and denominator, and D17 and D18 are the sources for naming that limitation. Fraud detection (D22, D23) is the applied field with the same two-speed labelling as Wikipedia. The notes found no peer-reviewed paper on label latency in content moderation; that search was not deep, so report it as "not found", not "does not exist". Measured Wikipedia time-to-revert sources are listed in the next area (W8, W9, W11).

### Stream learning treats delay as a given condition

**D1. Kuncheva and Sánchez 2008.** L. I. Kuncheva and J. S. Sánchez, "Nearest Neighbour Classifiers for Streaming Data with Delayed Labelling," in Proc. 2008 Eighth IEEE International Conference on Data Mining (ICDM), Dec. 2008, pp. 869-874. DOI 10.1109/ICDM.2008.33. Confirmed on [Crossref](https://api.crossref.org/works/10.1109/ICDM.2008.33); abstract via [OpenAlex](https://api.openalex.org/works/https://doi.org/10.1109/ICDM.2008.33). Abstract-level.
*Found:* Studies streams where the true label arrives after a delay and asks whether online nearest-neighbour classifiers (IB2, IB3) should use still-unlabelled points; compares three strategies (do nothing, replace, forget) on **28 data sets**; IB2 gains from unlabelled data, IB3 does not.
*Relation:* An early statement of the setting TruthLag measures; the delay is an assumed condition, not a measured quantity.

**D2. Žliobaitė 2010.** I. Žliobaitė, "Change with Delayed Labeling: When is it Detectable?," in Proc. 2010 IEEE International Conference on Data Mining Workshops (ICDMW), Dec. 2010, pp. 843-850. DOI 10.1109/ICDMW.2010.49. Confirmed on [Crossref](https://api.crossref.org/works/10.1109/ICDMW.2010.49); abstract via [OpenAlex](https://api.openalex.org/works/https://doi.org/10.1109/ICDMW.2010.49). Abstract-level.
*Found:* Most adaptive learners assume labels are available immediately, which is often unrealistic because of labelling delay or cost; analyses which changes are detectable without labels; proposes a low-cost detector on the stream of classifier outputs.
*Relation:* Explains why the period before labels arrive matters; gives no measurement of how long it is.

**D3. Marrs, Hickey and Black 2010.** G. R. Marrs, R. J. Hickey, and M. M. Black, "The Impact of Latency on Online Classification Learning with Concept Drift," in Lecture Notes in Computer Science, Springer, 2010, pp. 459-469. DOI 10.1007/978-3-642-15280-1_42. Confirmed on [Crossref](https://api.crossref.org/works/10.1007/978-3-642-15280-1_42) (authors, title, LNCS, pages, year).
*Found:* Nothing confirmed beyond the title.
*Relation:* Title-level relevance only.
*Flags:* UNVERIFIED: LNCS volume (believed 6291) and the conference name KSEM 2010. UNVERIFIED: abstract and findings. Do not state that it coined "verification latency" without reading it; the origin of that term is not confirmed anywhere in the notes.

**D4. Plasse and Adams 2016.** J. Plasse and N. Adams, "Handling delayed labels in temporally evolving data streams," in Proc. 2016 IEEE International Conference on Big Data, Dec. 2016, pp. 2416-2424. DOI 10.1109/BigData.2016.7840877. Confirmed on [Crossref](https://api.crossref.org/works/10.1109/bigdata.2016.7840877); abstract via [OpenAlex](https://api.openalex.org/works/https://doi.org/10.1109/BigData.2016.7840877). Abstract-level.
*Found:* Labels for earlier feature vectors may arrive only after an appreciable lag, a problem the authors say the literature does not properly address; contributes a taxonomy of delayed labelling and a framework for folding late labels into a streaming classifier. No numbers in the abstract.
*Relation:* The taxonomy is the natural place to position revert labels (random, per-item delay; only the positive class arrives).
*Flags:* UNVERIFIED: the taxonomy's category names.

**D5. Souza, Silva, Gama and Batista 2015.** V. M. A. Souza, D. F. Silva, J. Gama, and G. E. A. P. A. Batista, "Data Stream Classification Guided by Clustering on Nonstationary Environments and Extreme Verification Latency," in Proc. 2015 SIAM International Conference on Data Mining (SDM), Jun. 2015, pp. 873-881. DOI 10.1137/1.9781611974010.98. Confirmed on [Crossref](https://api.crossref.org/works/10.1137/1.9781611974010.98); abstract via [OpenAlex](https://api.openalex.org/works/https://doi.org/10.1137/1.9781611974010.98). Abstract-level.
*Found:* Defines extreme verification latency as the case where true labels never become available; proposes SCARGC, a repeated clustering-then-classification loop.
*Relation:* Marks the far end of the delay scale (infinite). Revert labels sit in between: finite but heavy-tailed.

**D5b. Souza, Silva, Batista and Gama 2015 (companion).** V. M. A. Souza, D. F. Silva, G. E. A. P. A. Batista, and J. Gama, "Classification of Evolving Data Streams with Infinitely Delayed Labels," in Proc. 2015 IEEE 14th Int. Conf. Machine Learning and Applications (ICMLA), Dec. 2015, pp. 214-219. DOI 10.1109/ICMLA.2015.174. Confirmed on [Crossref](https://api.crossref.org/works/10.1109/icmla.2015.174). Bibliographic record only; findings not read.

**D6. Souza, Pinho and Batista 2018.** V. Souza, T. Pinho, and G. Batista, "Evaluating Stream Classifiers with Delayed Labels Information," in Proc. 2018 7th Brazilian Conference on Intelligent Systems (BRACIS), Oct. 2018, pp. 408-413. DOI 10.1109/BRACIS.2018.00077. Confirmed on [Crossref](https://api.crossref.org/works/10.1109/BRACIS.2018.00077); abstract via [OpenAlex](https://api.openalex.org/works/https://doi.org/10.1109/BRACIS.2018.00077). Abstract-level. OpenAlex spells the second author "Tiago Pinho da Silva".
*Found:* Calls the immediate-label assumption very optimistic; shows experimentally that ignoring latency biases conclusions; says few studies consider label delay when proposing algorithms; proposes the Kappa-Latency evaluation measure.
*Relation:* Argues the delay must be a reported variable; TruthLag reports that variable for one real label.

**D7. Grzenda, Gomes and Bifet 2020.** M. Grzenda, H. M. Gomes, and A. Bifet, "Delayed labelling evaluation for data streams," Data Mining and Knowledge Discovery, vol. 34, no. 5, pp. 1237-1266, 2020 (online 16 Nov. 2019). DOI 10.1007/s10618-019-00654-y. Confirmed on [Crossref](https://api.crossref.org/works/10.1007/s10618-019-00654-y) (with abstract). Abstract-level.
*Found:* Test-then-train evaluation assumes the label arrives right after the prediction; proposes "continuous re-evaluation" of how a prediction for an instance changes between the instance's arrival and its label's arrival.
*Relation:* Closest methodological relative. It evaluates predictions during the waiting period; TruthLag measures how incomplete the label itself is during the same period.
*Flags:* UNVERIFIED: data sets and delay lengths used.

**D8. Gomes, Read, Bifet, Barddal and Gama 2019.** H. M. Gomes, J. Read, A. Bifet, J. P. Barddal, and J. Gama, "Machine learning for streaming data: state of the art, challenges, and opportunities," ACM SIGKDD Explorations Newsletter, vol. 21, no. 2, pp. 6-22, Nov. 2019. DOI 10.1145/3373464.3373470. Confirmed on [Crossref](https://api.crossref.org/works/10.1145/3373464.3373470) (the Crossref title stops at "Machine learning for streaming data"). Abstract-level.
*Found:* Position and survey paper on open challenges in stream learning.
*Relation:* A general survey for "immediate labels are a common but unrealistic assumption", usable only after the body is checked.
*Flags:* UNVERIFIED: that the body has a dedicated discussion of delayed labels; the abstract does not say so.

**D9. Gomes et al. 2022.** H. M. Gomes, M. Grzenda, R. Mello, J. Read, M. H. Le Nguyen, and A. Bifet, "A Survey on Semi-supervised Learning for Delayed Partially Labelled Data Streams," ACM Computing Surveys, vol. 55, no. 4, pp. 1-42, Nov. 2022. DOI 10.1145/3523055. Confirmed on [Crossref](https://api.crossref.org/works/10.1145/3523055) and [arXiv:2106.09170](https://arxiv.org/abs/2106.09170). Abstract-level.
*Found:* Surveys methods that use unlabelled stream data; treats delayed labelling as an issue for both supervised and semi-supervised methods; proposes a unified problem setting.
*Relation:* The most recent survey that names delayed labelling as a core stream problem; suitable as the survey citation for the setting.
*Flags:* UNVERIFIED: article number within vol. 55 no. 4.

**D10. Gama et al. 2014.** J. Gama, I. Žliobaitė, A. Bifet, M. Pechenizkiy, and A. Bouchachia, "A survey on concept drift adaptation," ACM Computing Surveys, vol. 46, no. 4, pp. 1-37, Mar. 2014. DOI 10.1145/2523813. Confirmed on [Crossref](https://api.crossref.org/works/10.1145/2523813). Abstract-level.
*Found:* Defines concept drift as a change over time in the relation between input and target; categorises adaptation strategies and evaluation methodology.
*Relation:* Background for stream learning and evaluation; not a delayed-label source on the evidence of its abstract.
*Flags:* UNVERIFIED: article number (commonly cited as Article 44). UNVERIFIED: what the body says about delayed feedback.

**D11. Dyer, Capo and Polikar 2014 (optional).** K. B. Dyer, R. Capo, and R. Polikar, "COMPOSE: A Semisupervised Learning Framework for Initially Labeled Nonstationary Streaming Data," IEEE Transactions on Neural Networks and Learning Systems, vol. 25, no. 1, pp. 12-26, Jan. 2014. DOI 10.1109/TNNLS.2013.2277712. Confirmed on [Crossref](https://api.crossref.org/works/10.1109/TNNLS.2013.2277712); abstract via [OpenAlex](https://api.openalex.org/works/https://doi.org/10.1109/TNNLS.2013.2277712). Abstract-level.
*Found:* Learns from streams where labels are unavailable after an initial labelled set; the abstract calls this "extreme verification latency"; on NOAA weather data it is reported competitive with a fully supervised learner.
*Relation:* A second source for the term "extreme verification latency".

### Advertising and online learning share the one-sided label

**D12. Chapelle 2014.** O. Chapelle, "Modeling delayed feedback in display advertising," in Proc. 20th ACM SIGKDD International Conference on Knowledge Discovery and Data Mining (KDD '14), Aug. 2014, pp. 1097-1105. DOI 10.1145/2623330.2623634. Confirmed on [Crossref](https://api.crossref.org/works/10.1145/2623330.2623634); abstract via [OpenAlex](https://api.openalex.org/works/https://doi.org/10.1145/2623330.2623634). Abstract-level.
*Found:* Conversions can occur long after the impression, "up to a month"; adds a second model for the conversion delay, so an unconverted user counts as a negative only when the elapsed time exceeds the predicted delay.
*Relation:* Direct analogue: "not converted yet" equals "not reverted yet", both right-censored positives. Chapelle models the delay to fix training; TruthLag reports the delay curve itself.
*Flags:* UNVERIFIED: the share of conversions arriving within given waits, and the exponential form of the delay model (seen only second-hand).

**D13. Ktena et al. 2019.** S. I. Ktena, A. Tejani, L. Theis, P. K. Myana, D. Dilipkumar, F. Huszár, S. Yoo, and W. Shi, "Addressing delayed feedback for continuous training with neural networks in CTR prediction," in Proc. 13th ACM Conference on Recommender Systems (RecSys '19), Sep. 2019, pp. 187-195. DOI 10.1145/3298689.3347002. Confirmed on [Crossref](https://api.crossref.org/works/10.1145/3298689.3347002) and [arXiv:1907.06558](https://arxiv.org/abs/1907.06558). Abstract-level.
*Found:* Treating every item as negative until a positive arrives underestimates click-through rate; compares 5 loss functions; offline on **668 million** data points the proposed methods gain **3%** relative cross entropy; online, a **55%** gain in revenue per thousand requests against naive log loss.
*Relation:* Documents the cost of "count it as negative until told otherwise", which is what a live revert count does at short waits. It is a neural-network paper, included only because it is specifically about delayed labels.

**D14. Joulani, György and Szepesvári 2013.** P. Joulani, A. György, and C. Szepesvári, "Online Learning under Delayed Feedback," in Proc. 30th International Conference on Machine Learning (ICML), Proceedings of Machine Learning Research, vol. 28, no. 3, pp. 1453-1461, 2013. No DOI. Confirmed on [PMLR](https://proceedings.mlr.press/v28/joulani13.html) (abstract page read).
*Found:* Delay raises regret multiplicatively in adversarial problems and additively in stochastic problems; gives black-box meta-algorithms and modified UCB bandit algorithms for delayed feedback.
*Relation:* Theory for how much delay costs a learner; it needs the delay distribution as input, which TruthLag measures for one label.

**D15a. Mesterharm 2005 (optional, earlier theory).** C. Mesterharm, "On-line Learning with Delayed Label Feedback," in Lecture Notes in Computer Science, Springer, 2005, pp. 399-413. DOI 10.1007/11564089_31. Confirmed on [Crossref](https://api.crossref.org/works/10.1007/11564089_31).
*Flags:* UNVERIFIED: host conference (believed ALT 2005) and LNCS volume; abstract not available.

**D15b. Weinberger and Ordentlich 2002 (optional, earlier theory).** M. J. Weinberger and E. Ordentlich, "On delayed prediction of individual sequences," IEEE Transactions on Information Theory, vol. 48, no. 7, pp. 1959-1976, Jul. 2002. DOI 10.1109/TIT.2002.1013136. Confirmed on [Crossref](https://api.crossref.org/works/10.1109/tit.2002.1013136).
*Relation (both):* Show the delayed-feedback question predates the stream-mining papers; cite only if the survey needs the earlier theory.
*Flags:* UNVERIFIED: findings (abstract not read).

### Statistics already has the names: censoring, reporting delay, vintages

**D16. Kaplan and Meier 1958.** E. L. Kaplan and P. Meier, "Nonparametric Estimation from Incomplete Observations," Journal of the American Statistical Association, vol. 53, no. 282, pp. 457-481, Jun. 1958. DOI 10.1080/01621459.1958.10501452. Confirmed on [Crossref](https://api.crossref.org/works/10.1080/01621459.1958.10501452); abstract via [OpenAlex](https://api.openalex.org/works/https://doi.org/10.1080/01621459.1958.10501452). Abstract-level.
*Found:* Estimates P(t), the proportion of items whose lifetime exceeds t, when some lifetimes are censored, with no assumption on the form of P(t); defines the product-limit estimate; assumes lifetime is independent of the loss time; with no losses before t the estimate reduces to the observed proportion of survivors.
*Relation:* E(L) is a survival function of time-to-revert among eventual reverts. With a fixed 4-day follow-up for every edit, the plain observed proportion is the Kaplan-Meier estimate.

**D17. Höhle and an der Heiden 2014 (draft ref [12]).** M. Höhle and M. an der Heiden, "Bayesian nowcasting during the STEC O104:H4 outbreak in Germany, 2011," Biometrics, vol. 70, no. 4, pp. 993-1002, Dec. 2014 (online 13 Jun. 2014). DOI 10.1111/biom.12194. Confirmed on [Crossref](https://api.crossref.org/works/10.1111/biom.12194) (with abstract).
*Found:* Predicts occurred-but-not-yet-reported daily hospitalisations during the May-July 2011 outbreak; handles right-truncation of the reporting-delay distribution in a Bayesian framework; scored against retrospectively known counts; the delay distribution changed during the outbreak.
*Relation:* The same two-source design as TruthLag (real-time partial count against a later complete count), and evidence that a delay distribution is not stable over time.

**D18. Lawless 1994.** J. F. Lawless, "Adjustments for reporting delays and the prediction of occurred but not reported events," Canadian Journal of Statistics, vol. 22, no. 1, pp. 15-31, Mar. 1994. DOI as registered: 10.2307/3315826.n1. Confirmed on [Crossref](https://api.crossref.org/works/10.2307/3315826.n1); abstract via an [OpenAlex search record](https://api.openalex.org/works?search=Adjustments%20for%20reporting%20delays%20and%20the%20prediction%20of%20occurred%20but%20not%20reported%20events).
*Found:* Treats delays in reporting events such as disease cases or insurance claims; earlier methods ignore random fluctuation in reporting delays, which makes prediction limits too narrow; proposes random effects on recent reporting data.
*Relation:* The standard statistical name for "eventual reverts not yet known at wait L" is occurred-but-not-reported events; E(L) is one minus the cumulative reporting-delay distribution.
*Flags:* Citation trap: the DOI without ".n1" is a different article (see the trap list).

**D19. Zeger, See and Diggle 1989.** S. L. Zeger, L.-C. See, and P. J. Diggle, "Statistical methods for monitoring the AIDS epidemic," Statistics in Medicine, vol. 8, no. 1, pp. 3-21, Jan. 1989. DOI 10.1002/sim.4780080104. Confirmed on [Crossref](https://api.crossref.org/works/10.1002/sim.4780080104); abstract via [OpenAlex](https://api.openalex.org/works/https://doi.org/10.1002/sim.4780080104). Abstract-level.
*Found:* A log-linear model estimates incidence and growth rate while accounting for delays in case reporting; applied to US registry data as of September 1987; incidence doubling about every two years at that time.
*Relation:* An early worked example of correcting a recent count for reports that have not arrived.
*Companion (record only, findings not read):* R. Brookmeyer and A. Damiano, "Statistical methods for short-term projections of AIDS incidence," Statistics in Medicine, vol. 8, no. 1, pp. 23-34, 1989, DOI 10.1002/sim.4780080105.

**D19b. McGough et al. 2020 (optional).** S. F. McGough, M. A. Johansson, M. Lipsitch, and N. A. Menzies, "Nowcasting by Bayesian Smoothing: A flexible, generalizable model for real-time epidemic tracking," PLOS Computational Biology, vol. 16, no. 4, e1007735, Apr. 2020. DOI 10.1371/journal.pcbi.1007735. Confirmed on [Crossref](https://api.crossref.org/works/10.1371/journal.pcbi.1007735); abstract via [OpenAlex](https://api.openalex.org/works/https://doi.org/10.1371/journal.pcbi.1007735). Abstract-level.
*Found:* Nowcasting estimates complete counts from reports known to be incomplete; tested on dengue in Puerto Rico and influenza-like illness in the United States; linking cases across time helps when the delay distribution varies.
*Relation:* A recent, open-access statement of the nowcasting problem, and the possible next step after measuring E(L): scale a live count up by the known delay curve.

**D20. Croushore and Stark 2001 (draft ref [10]).** D. Croushore and T. Stark, "A real-time data set for macroeconomists," Journal of Econometrics, vol. 105, no. 1, pp. 111-130, Nov. 2001. DOI 10.1016/S0304-4076(01)00072-0. Confirmed on [Crossref](https://api.crossref.org/works/10.1016/S0304-4076%2801%2900072-0).
*Found (from the working-paper version, Federal Reserve Bank of Philadelphia Working Paper 99-4, 1999, DOI 10.21799/frbp.wp.1999.04, via an [OpenAlex search record](https://api.openalex.org/works?search=A%20real-time%20data%20set%20for%20macroeconomists)):* A data set of vintages, snapshots of the major macroeconomic data as available at quarterly intervals in real time; forecasts and policy analysis can change with the vintage.
*Relation:* The source for the "vintage" idea. TruthLag's stream-versus-dump comparison is a two-vintage data set for one label.
*Flags:* UNVERIFIED: that the journal text matches the working-paper abstract; no journal abstract was available.

**D21. Aruoba 2008 (draft ref [11]).** S. B. Aruoba, "Data Revisions Are Not Well Behaved," Journal of Money, Credit and Banking, vol. 40, no. 2-3, pp. 319-340, Mar. 2008. DOI 10.1111/j.1538-4616.2008.00115.x. Confirmed on [Crossref](https://api.crossref.org/works/10.1111/j.1538-4616.2008.00115.x) (with abstract).
*Found:* Revisions to major US macroeconomic variables do not have zero mean, are large relative to the original variables, and are predictable from information available at the first announcement.
*Relation:* Precedent for an early figure being biased in a known direction. An early revert count is biased low by construction, and E(L) gives the size of that bias.

### Fraud detection has the same fast and slow label channels

**D22. Dal Pozzolo et al. 2015.** A. Dal Pozzolo, G. Boracchi, O. Caelen, C. Alippi, and G. Bontempi, "Credit card fraud detection and concept-drift adaptation with delayed supervised information," in Proc. 2015 International Joint Conference on Neural Networks (IJCNN), Jul. 2015, pp. 1-8. DOI 10.1109/IJCNN.2015.7280527. Confirmed on [Crossref](https://api.crossref.org/works/10.1109/IJCNN.2015.7280527); abstract via [OpenAlex](https://api.openalex.org/works/https://doi.org/10.1109/IJCNN.2015.7280527). Abstract-level.
*Found:* Only a small set of alerted transactions gets fast labels from investigators; labels for the vast majority arrive several days later; fast feedback and delayed labels should be handled by separate classifiers. No numbers in the abstract.
*Relation:* The same two-speed labelling as Wikipedia (fast bot and tool reverts, slow human reverts; see W11). The delay is described as "several days" but not measured as a curve.

**D23. Dal Pozzolo et al. 2018.** A. Dal Pozzolo, G. Boracchi, O. Caelen, C. Alippi, and G. Bontempi, "Credit Card Fraud Detection: A Realistic Modeling and a Novel Learning Strategy," IEEE Transactions on Neural Networks and Learning Systems, vol. 29, no. 8, pp. 3784-3797, Aug. 2018. DOI 10.1109/TNNLS.2017.2736643. Confirmed on [Crossref](https://api.crossref.org/works/10.1109/TNNLS.2017.2736643); abstract via [OpenAlex](https://api.openalex.org/works/https://doi.org/10.1109/TNNLS.2017.2736643). Abstract-level.
*Found:* Names three challenges: concept drift, class imbalance and verification latency; experiments on a real stream of more than **75 million** transactions over three years.
*Relation:* A journal-level source that label timing must be modelled as it actually occurs, using "verification latency" in an applied setting.

**Not citable from this area.** Yoshikawa and Imai, "A Nonparametric Delayed Feedback Model for Conversion Rate Prediction": arXiv:1802.00255 exists as an identifier, but title and authors were not confirmed on a readable page. UNVERIFIED; do not cite without checking.

## Wikipedia reverts: medians in minutes, tails in months, and a label that lags by design

**What the literature establishes.** The standard research definition of a revert is the identity revert: a revision whose content checksum equals an earlier revision's, which marks the revisions in between as reverted. Three "revert" labels coexist and need not agree: the checksum identity revert in the MediaWiki History dataset (a SHA-1 field), the `mw-reverted` software tag (content match within 15 revisions, plus approval and depth conditions, applied by a deferred job), and diff-based reverts (W1). The report should state which one each number uses. Published repair times run from about 2-3 minutes for blatant mass deletions (2003 data) to about 12 minutes for all reverted edits on English Wikipedia in early 2011, rising to about 21 minutes when ClueBot NG was offline; every study also reports a long tail (11% of damage incidents lasting beyond 100 views; about 1 in 100 hoaxes surviving more than a year; median bot-bot time to revert of 62 days). These figures are not comparable across papers without care: W8 is 2003 data on mass deletions, W9 is 2002-2006 counted in views, W11 is 2011 across all reverted edits in seconds. All three measure repair time retrospectively from full history; none frames it as a label-completeness curve for a consumer of a live stream. Vandalism detection moved its label source from human annotation (W14, W18) to rollback (W15) to identity reverts from MediaWiki History (W19, W20a, W20b); only the last depends on revert-label delay. Mutual-revert work (W21, W22) defines conflict by pairs of editors reverting each other, and the bot-conflict debate (W23, W24) shows a raw pair count is not conflict. "Reverted" includes good-faith rejections (W27, W28), so the label means "rejected", not "vandalism". Since 4 November 2025 logged-out editors on English Wikipedia appear under temporary account names, which changes the editor-identity field (W25, W26). The notes found no time-to-revert distribution for data later than 2011 other than the bot-only figures in W24, no source on whether temporary accounts changed revert rates, and no peer-reviewed paper on ClueBot NG's own accuracy or latency.

### How reverts are defined and detected

**W1. Flöck, Vrandečić and Simperl 2012 (draft ref [18]).** F. Flöck, D. Vrandečić, and E. Simperl, "Revisiting reverts: accurate revert detection in Wikipedia," in Proc. 23rd ACM Conf. Hypertext and Social Media (HT '12), Milwaukee, WI, USA, 2012, pp. 3-12. DOI 10.1145/2309996.2310000. Confirmed on [Crossref](https://api.crossref.org/works/10.1145/2309996.2310000); abstract via [OpenAlex](https://api.openalex.org/works/doi:10.1145/2309996.2310000). Abstract-level.
*Found:* The then state of the art found reverts by matching MD5 hashes of revisions; the paper names three drawbacks (misses some reverts, labels too many edits as reverts, cannot separate full from partial reverts) and proposes detection from word tokens added or deleted, validated by a user study, at higher run time. The first author's dissertation summarises the result as **12% more full reverts** than the earlier method, plus partial reverts ([KIT dissertation](https://publikationen.bibliothek.kit.edu/1000058165/3879557)); the same figure is on [Research:Revert](https://meta.wikimedia.org/wiki/Research:Revert).
*Relation:* The label TruthLag waits for is the checksum definition this paper criticises, so the measured delay is for identity reverts only; partial reverts never get the label. It is also the argument for going beyond exact checksums in the text-similarity work; its method is word-level diffing, not LSH.
*Flags:* UNVERIFIED: the user-study sample size and exact accuracy figures in the HT paper itself. Citation trap on the DOI (see the trap list).

**W2. MediaWiki history dumps (Wikitech).** Wikimedia Foundation, "Data Platform/Data Lake/Edits/Mediawiki history dumps," Wikitech, last edited 5 July 2026. Confirmed on [Wikitech](https://wikitech.wikimedia.org/wiki/Data_Platform/Data_Lake/Edits/Mediawiki_history_dumps). Full text read.
*Found:* Field definitions for `revision_is_identity_reverted`, `revision_first_identity_reverting_revision_id`, `revision_seconds_to_identity_revert`, `revision_is_identity_revert`, `revision_text_sha1` and `revision_tags`. Released monthly around the end of the first week; each release holds full history since 2001; a snapshot is named YYYY-MM after the last month it covers; only the last two versions are kept; bzip2-compressed TSV.
*Relation:* The "late truth" source. Its monthly cadence means an identity-revert flag can be up to about five weeks behind the edit regardless of how fast the revert happened.

**W3. MediaWiki history (Wikitech).** Wikimedia Foundation, "Data Platform/Data Lake/Edits/MediaWiki history," Wikitech, last edited 5 July 2026. Confirmed on [Wikitech](https://wikitech.wikimedia.org/wiki/Data_Platform/Data_Lake/Edits/MediaWiki_history). Full text read.
*Found:* A new snapshot covering all of history is generated each month; `revision_tags` was added in 2019-04; known quality notes include null or zero page ids and apparent duplicates (2020-06).
*Relation:* The dataset is rebuilt in full each month, so a revert label can change between snapshots.
*Flags:* UNVERIFIED: the exact algorithm (window, SHA-1 comparison scope, whether self-reverts are included) that fills the identity-revert fields; no opened Wikimedia page states it.

**W4. Manual:Reverts (MediaWiki.org).** MediaWiki contributors, "Manual:Reverts," MediaWiki.org, last edited 21 June 2026. Confirmed on [MediaWiki.org](https://www.mediawiki.org/wiki/Manual:Reverts). Full text read.
*Found:* Software tags `mw-undo`, `mw-rollback`, `mw-manual-revert` (since MediaWiki 1.36) and `mw-reverted` (on the edits that were reverted, since 1.36). `mw-reverted` is applied by a queued `revertedTagUpdate` job after the reverting edit is saved, so it can be delayed on busy wikis. Conditions: the number of reverted edits must not exceed `$wgRevertedTagMaxDepth`, the reverting revision must not itself be reverted or deleted, and the reverting edit must be auto-approved, otherwise the update waits. Manual reverts are found by checking up to `$wgManualRevertSearchRadius` (default **15**) most recent revisions.
*Relation:* The mechanical reasons the stream-side label lags the revert (job queue, patrol approval) and why some reverted edits never receive it (depth limit, 15-revision radius). No documentation page states a typical delay of the job.

**W5. Research:Revert (Meta-Wiki).** Wikimedia Research, "Research:Revert," Meta-Wiki. Confirmed on [Meta-Wiki](https://meta.wikimedia.org/wiki/Research:Revert). Full text read.
*Found:* Defines reverting, reverted and reverted-to revisions and three revert types (identity revert, full revert plus changes, partial revert). Says nearly all reverts on English Wikipedia happen within **48 hours**, which is why 48 hours is a common cutoff; the mwreverts library defaults to a radius of 15 edits; warns that observation cutoffs censor late reverts. Reports, from Kiesel et al., that about 6% of identity reverts are pseudo reverts, 9% self-reverts and 11% in edit wars.
*Relation:* Names the censoring problem TruthLag measures and gives the 48-hour convention to compare against.
*Flags:* The Kiesel et al. percentages are second-hand (see W29). The page text says MD5 while its sample code uses the SHA-1 field.

**W6. mwreverts library.** A. Halfaker, "mwreverts" (Python library, MIT License), documentation. Confirmed on [pythonhosted.org](https://pythonhosted.org/mwreverts/).
*Found:* Detects reverts and checks the reverted status of edits; offers `mwreverts.Detector`, `mwreverts.detect()`, and status checks against the API and database.
*Relation:* The reference implementation of the identity-revert definition; a radius of 15 means a revert more than 15 revisions later is not counted.
*Flags:* UNVERIFIED: version number and release year. The default radius of 15 is stated on Research:Revert, not on the library's front page.

**W7. Lift Wing streams (Wikitech).** Wikimedia Foundation, "Machine Learning/LiftWing/Streams," Wikitech, last edited 13 May 2026. Confirmed on [Wikitech](https://wikitech.wikimedia.org/wiki/Machine_Learning/LiftWing/Streams). Full text read.
*Found:* The language-agnostic revert-risk model server consumes `mediawiki.page_change.v1` and emits `mediawiki.page_revert_risk_prediction_change.v1`. The page does not say which wikis are covered or whether the stream is in public EventStreams.
*Relation:* Where the at-edit-time revert-risk score in the stream comes from, the early signal TruthLag compares with the late label.

### How fast damage is reverted

**W8. Viégas, Wattenberg and Dave 2004.** F. B. Viégas, M. Wattenberg, and K. Dave, "Studying cooperation and conflict between authors with history flow visualizations," in Proc. SIGCHI Conf. Human Factors in Computing Systems (CHI '04), Vienna, Austria, 2004, pp. 575-582. DOI 10.1145/985692.985765. Confirmed on [Crossref](https://api.crossref.org/works/10.1145/985692.985765); full text read at [hint.fm](http://hint.fm/papers/history_flow.pdf) and [MIT](https://politics.media.mit.edu/papers/history_flowviegas.pdf).
*Found:* Wikipedia history as of May 2003; "survival time" is how long a revision stays before being modified. Table 1: all content, n = **618,502**, mean **22.3 days**, median **90.4 minutes**; mass deletions, n = 3,574, mean 7.7 days, median **2.8 minutes**; obscene mass deletions, n = 47, mean 1.8 days, median 1.7 minutes. A mass deletion is a version at least 90% smaller than the page's previous maximum, not a redirect, not made by an administrator.
*Relation:* The earliest measured repair-time figures, and direct evidence of a heavy tail (median in minutes, mean in days), which is why a curve over L says more than one number.

**W9. Priedhorsky et al. 2007 (draft ref [15]).** R. Priedhorsky, J. Chen, S. K. Lam, K. Panciera, L. Terveen, and J. Riedl, "Creating, destroying, and restoring value in Wikipedia," in Proc. 2007 Int. ACM Conf. Supporting Group Work (GROUP '07), Sanibel Island, FL, USA, 2007, pp. 259-268. DOI 10.1145/1316624.1316663. Confirmed on [Crossref](https://api.crossref.org/works/10.1145/1316624.1316663) (first page 259 only); full text read from the [archived author PDF](https://web.archive.org/web/2015/http://www-users.cs.umn.edu/~reid/papers/group282-priedhorsky.pdf).
*Found:* English Wikipedia, 1 September 2002 to 31 October 2006; 4.2 million editors and 58 million edits. Reverts detected by MD5 checksums of revision text; identity reverts only. **2,100,828** damage incidents; **42%** repaired within one estimated view; **11%** persist beyond 100 views; 0.75% beyond 1,000 views; 0.06% beyond 10,000 views. Of an estimated 51 billion views, 188 million were of damaged revisions (probability 0.0037 overall, 0.0067 in October 2006). Cites Kittur et al. for 94% of comment-identifiable reverts being identity reverts.
*Relation:* Measures damage lifetime in views instead of clock time, from complete history, and shows the heavy tail.
*Flags:* The end page 268 was not on the Crossref record; it comes from another paper's reference list and a university listing. UNVERIFIED: conference location. One research session could not open the full text and left the 42% figure unverified; the other read the archived PDF and confirmed it, which is the reading used here.

**W10. Geiger and Ribes 2010.** R. S. Geiger and D. Ribes, "The work of sustaining order in Wikipedia: the banning of a vandal," in Proc. 2010 ACM Conf. Computer Supported Cooperative Work (CSCW '10), Savannah, GA, USA, 2010, pp. 117-126. DOI 10.1145/1718918.1718941. Confirmed on [Crossref](https://api.crossref.org/works/10.1145/1718918.1718941); full text read at the [author PDF](https://stuartgeiger.com/papers/cscw-sustaining-order-wikipedia.pdf).
*Found:* A trace ethnography of one anonymous vandal blocked after about twenty edits in one hour. As of 2009, over **12 percent** of all edits were made with assisted tools. Tools leave markers in edit summaries, which is how tool-made reverts are identified.
*Relation:* Explains who produces fast reverts (bots, then tool users, then manual editors), the mechanism behind a multi-modal delay distribution.
*Flags:* UNVERIFIED: conference location.

**W11. Geiger and Halfaker 2013 (draft ref [17]).** R. S. Geiger and A. Halfaker, "When the levee breaks: without bots, what happens to Wikipedia's quality control processes?," in Proc. 9th Int. Symp. Open Collaboration (WikiSym '13), Hong Kong, China, Aug. 2013, pp. 1-6. DOI 10.1145/2491055.2491061. Confirmed on [Crossref](https://api.crossref.org/works/10.1145/2491055.2491061); full text read at the [author PDF](https://stuartgeiger.com/wikisym13-cluebot.pdf).
*Found:* Defines time-to-revert as the time between an edit and the later edit that removes it entirely by returning the article to a previous state, and says researchers have long used its median or mean as the quality-control metric. English Wikipedia, 1 January to 30 June 2011, Wednesdays and Thursdays only: with ClueBot NG up, median **744 s (12.4 min)**, geometric mean 941 s (15.7 min); with it down, median **1,286 s (21.4 min)**, geometric mean 1,674 s (27.9 min). While the bot was down the share of edits that were reverts was significantly lower (p < 0.001), but the share of revisions eventually reverted was not significantly different (p = 0.43): the same edits were reverted, later. In a normal month most fully automated reverts occur within one minute and manual in-browser reverts fall mostly between one minute and 24 hours. ClueBot NG first edited in November 2010 and had over 2 million edits by March 2013.
*Relation:* The closest prior work. The delay distribution shifts when the reviewing system changes while the eventual label stays the same, exactly the situation where E(L) changes and the final count does not. It reports medians and histograms from complete history, not the error of a live count at wait L.
*Flags:* The two research sessions summarise the sub-minute group differently (one says most Huggle-tool reverts came within one minute; the other says fully automated reverts do, with tool-assisted reverts in between). Read the paper's own figure before attributing the one-minute statement to a specific tool. UNVERIFIED: article number. See the trap list for the venue name.

**W12. Kumar, West and Leskovec 2016 (draft ref [16]).** S. Kumar, R. West, and J. Leskovec, "Disinformation on the Web: impact, characteristics, and detection of Wikipedia hoaxes," in Proc. 25th Int. Conf. World Wide Web (WWW '16), Montréal, Canada, 2016, pp. 591-602. DOI 10.1145/2872427.2883085. Confirmed on [Crossref](https://api.crossref.org/works/10.1145/2872427.2883085); full text read at the [author PDF](https://cs.stanford.edu/people/jure/pubs/hoax-www16.pdf).
*Found:* **21,218** English Wikipedia hoax articles. Of hoaxes eventually detected, **90%** are flagged within one hour of patrol, 92% within a day, 94% within a week, 96% within a month; about 1 in 100 survives more than a year. 80% of new articles are patrolled within an hour, 95% within a day.
*Relation:* A detection-delay curve for article-level falsehoods (deletion, not revert) with the same shape: most caught fast, a small share very late. It is the nearest published example of a completeness-by-wait series on Wikipedia, for a different label.
*Flags:* UNVERIFIED: conference location.

**W13. Kittur et al. 2007.** A. Kittur, B. Suh, B. A. Pendleton, and E. H. Chi, "He says, she says: conflict and coordination in Wikipedia," in Proc. SIGCHI Conf. Human Factors in Computing Systems (CHI '07), San Jose, CA, USA, Apr. 2007, pp. 453-462. DOI 10.1145/1240624.1240698. Confirmed on [Crossref](https://api.crossref.org/works/10.1145/1240624.1240698); abstract via [OpenAlex](https://api.openalex.org/works/doi:10.1145/1240624.1240698). Abstract-level.
*Found:* Studies the growth of non-direct work (conflict, coordination) and builds tools to characterise conflict. As reported by W9 (second-hand): among identity reverts plus reverts identifiable from edit comments, **94%** are identity reverts.
*Relation:* The source of the 94% coverage figure that justifies using identity reverts as the label; not a delay measurement.
*Flags:* The 94% figure was read in W9 and on Research:Revert, not in this paper. UNVERIFIED: any time-to-revert figure, the "Revert Graph" user clustering, the data year, and the conference location.

### Vandalism-detection systems and where their labels come from

**W14. Potthast, Stein and Gerling 2008.** M. Potthast, B. Stein, and R. Gerling, "Automatic vandalism detection in Wikipedia," in Advances in Information Retrieval (ECIR 2008), Lecture Notes in Computer Science. Berlin, Heidelberg: Springer, 2008, pp. 663-668. DOI 10.1007/978-3-540-78646-7_75. Confirmed on [Crossref](https://api.crossref.org/works/10.1007/978-3-540-78646-7_75); full text read at the [author-group PDF](https://webis.de/downloads/publications/papers/potthast_2008b.pdf).
*Found:* Frames vandalism detection as classification and releases a corpus; logistic regression reaches **83% precision at 77% recall**; features come from manual analysis of 301 vandalism cases.
*Relation:* Uses human-annotated labels, the alternative to waiting for a revert label.
*Flags:* UNVERIFIED: LNCS volume (commonly given as 4956) and the year 2008 (not in the Crossref record).

**W15. West, Kannan and Lee 2010 (EUROSEC).** A. G. West, S. Kannan, and I. Lee, "Detecting Wikipedia vandalism via spatio-temporal analysis of revision metadata," in Proc. 3rd European Workshop on System Security (EUROSEC '10), Paris, France, 2010, pp. 22-28. DOI 10.1145/1752046.1752050. Confirmed on [Crossref](https://api.crossref.org/works/10.1145/1752046.1752050); abstract via [OpenAlex](https://api.openalex.org/works/doi:10.1145/1752046.1752050). Abstract-level.
*Found:* Uses only revision metadata; labels come from administrative rollback; reports 85% accuracy at 50% recall and over 100 edits per second.
*Relation:* An early case of using a revert action as the training label, so label quality depends on when rollback happens.
*Flags:* The Crossref title carries a trailing "?". UNVERIFIED: workshop location.

**W16. West, Kannan and Lee 2010 (STiki demo).** A. G. West, S. Kannan, and I. Lee, "STiki: an anti-vandalism tool for Wikipedia using spatio-temporal analysis of revision metadata," in Proc. 6th Int. Symp. Wikis and Open Collaboration (WikiSym '10), Gdańsk, Poland, 2010, pp. 1-2. DOI 10.1145/1832772.1832814. Confirmed on [Crossref](https://api.crossref.org/works/10.1145/1832772.1832814); abstract via [OpenAlex](https://api.openalex.org/works/doi:10.1145/1832772.1832814). Abstract-level.
*Found:* A real-time tool: a server scores each revision and a client shows likely vandalism to human users who classify and revert.
*Relation:* One of the assisted tools whose queues put human reverts minutes, not seconds, after the edit.
*Flags:* UNVERIFIED: article number and symposium location. No time-to-revert figure in the abstract.

**W17. Adler et al. 2011.** B. T. Adler, L. de Alfaro, S. M. Mola-Velasco, P. Rosso, and A. G. West, "Wikipedia vandalism detection: combining natural language, metadata, and reputation features," in Computational Linguistics and Intelligent Text Processing (CICLing 2011), Lecture Notes in Computer Science, vol. 6609. Berlin, Heidelberg: Springer, 2011, pp. 277-288. DOI 10.1007/978-3-642-19437-5_23. Confirmed on [Crossref](https://api.crossref.org/works/10.1007/978-3-642-19437-5_23); abstract via [Semantic Scholar](https://api.semanticscholar.org/graph/v1/paper/DOI:10.1007/978-3-642-19437-5_23?fields=title,abstract,year,venue). Abstract-level.
*Found:* States that about **7%** of edits are vandalism; combines metadata, reputation and natural-language features; separates catching fresh vandalism at edit time from finding vandalism in the full history.
*Relation:* The "fresh versus historical" split is the same distinction as scoring before the label exists versus after it has settled.
*Flags:* UNVERIFIED: exact AUC figures on the PAN 2010 corpus. The PAN shared-task overview papers were not opened.

**W18. Halfaker and Geiger 2020 (ORES).** A. Halfaker and R. S. Geiger, "ORES: lowering barriers with participatory machine learning in Wikipedia," Proc. ACM Hum.-Comput. Interact., vol. 4, no. CSCW2, Article 148, pp. 1-37, Oct. 2020. DOI 10.1145/3415219. Preprint arXiv:1909.05189. Confirmed on [Crossref](https://api.crossref.org/works/10.1145/3415219) and [arXiv](https://arxiv.org/abs/1909.05189); full text read.
*Found:* A scoring service giving real-time scores from several classifiers. Example English Wikipedia "damaging" model: 19,445 labelled edits, 743 damaging (3.8%); ROC AUC **0.923**; precision 0.34 and recall 0.555 on the damaging class. Labels come from manual community labelling or from trace data, which the authors say needs care.
*Relation:* ORES "damaging" labels are human judgements, not reverts; the contrast with revert-trained models (W19) is a design choice about label timing.

**W19. Trokhymovych et al. 2023 (draft ref [19]).** M. Trokhymovych, M. Aslam, A.-J. Chou, R. Baeza-Yates, and D. Saez-Trumper, "Fair multilingual vandalism detection system for Wikipedia," in Proc. 29th ACM SIGKDD Conf. Knowledge Discovery and Data Mining (KDD '23), Long Beach, CA, USA, 2023, pp. 4981-4990. DOI 10.1145/3580305.3599823. Preprint arXiv:2306.01650. Confirmed on [Crossref](https://api.crossref.org/works/10.1145/3580305.3599823) and [arXiv](https://arxiv.org/abs/2306.01650); full text read.
*Found:* Covers **47 languages**; the target is whether a revision will be reverted, and the training record shown uses the MediaWiki History field `revision_is_identity_reverted`. Six months of training revisions, test set the following week; bot edits removed; "revision wars" filtered out. Inference median 1.0 s, 95th percentile 4.0 s on CPU. Notes about 16 pages edited per second on Wikipedia.
*Relation:* The model whose scores ride in the stream is trained on the late identity-revert label from a monthly snapshot; any label still missing at snapshot time is a training negative.
*Flags:* UNVERIFIED: headline AUC and accuracy figures (not extracted), and the conference location.

**W20a. Language-agnostic revert risk model card.** Wikimedia Foundation, "Machine learning models/Production/Language-agnostic revert risk," Meta-Wiki, last edited 14 August 2026. Confirmed on [Meta-Wiki](https://meta.wikimedia.org/wiki/Machine_learning_models/Production/Language-agnostic_revert_risk). Full text read.
*Found:* Predicts the probability a revision will be reverted; Wikipedia article namespace only; XGBoost; hosted on Lift Wing. Training data from MediaWiki History, snapshot 2023-05, observation period 2022-01-01 to 2023-01-01; bots removed. May be biased against new users, temporary accounts and IP editors. The performance section is empty.
*Relation:* This is the score in the stream. Its snapshot is four months after the observation window ends, so labels had time to settle.

**W20b. Multilingual revert risk model card.** Wikimedia Foundation, "Machine learning models/Production/Multilingual revert risk," Meta-Wiki, last edited 11 June 2026. Confirmed on [Meta-Wiki](https://meta.wikimedia.org/wiki/Machine_learning_models/Production/Multilingual_revert_risk). Full text read.
*Found:* Multilingual BERT text features plus a CatBoost classifier; 47 languages. Snapshot 2022-07, observation 2022-01-01 to 2022-07-01, test the following week; 8,586,362 training and 1,079,265 test revisions. Revert rate **0.08** in training and **0.07** in test.
*Relation:* Here the snapshot month equals the end of the observation window, so the most recent training edits had little time to be reverted. The lower test-week revert rate is consistent with that, though the card does not say so (an inference in the notes, not a finding of the card). Neither model card defines the revert label in words; W19's data example is the only place the field name appears.

### Edit wars and mutual reverts

**W21. Sumi et al. 2011.** R. Sumi, T. Yasseri, A. Rung, A. Kornai, and J. Kertész, "Edit wars in Wikipedia," in Proc. 2011 IEEE 3rd Int. Conf. Privacy, Security, Risk and Trust and 2011 IEEE 3rd Int. Conf. Social Computing (PASSAT/SocialCom), Boston, MA, USA, Oct. 2011, pp. 724-727. DOI 10.1109/PASSAT/SocialCom.2011.47. Preprint arXiv:1107.3689. Confirmed on [Crossref](https://api.crossref.org/works/10.1109/PASSAT/SocialCom.2011.47); full text read at [arXiv](https://arxiv.org/pdf/1107.3689).
*Found:* Defines mutual reverts as two editors reverting each other; about **24k** articles, under 1% of the 3 million in the November 2009 English dump, are called controversial; top-30 precision 85% by revert count, 92% by mutual-revert count, 95% by the final measure M.
*Relation:* Mutual-revert pairs are revert-of-revert chains, the case where an edit's reverted status and the reverting edit's own status both change after the fact.
*Flags:* UNVERIFIED: conference location.

**W22. Yasseri et al. 2012.** T. Yasseri, R. Sumi, A. Rung, A. Kornai, and J. Kertész, "Dynamics of conflicts in Wikipedia," PLoS ONE, vol. 7, no. 6, Art. no. e38869, Jun. 2012. DOI 10.1371/journal.pone.0038869. Confirmed on [PLoS ONE](https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0038869) and [Crossref](https://api.crossref.org/works/10.1371/journal.pone.0038869); publisher HTML read.
*Found:* Reverts found by MD5 hash of each revision's text; a mutual revert is a pair of editors who each reverted the other; self-reverts excluded. The controversy measure M weights each pair by the smaller of the two editors' edit counts, multiplies by the number of editors involved, and discounts the top pair. January 2010 English dump, 3.2 million articles; about 84k have M above zero, about **12k** are controversial, under 1%.
*Relation:* The method the side analysis follows. It uses MD5, not SHA-1, and counts pairs, so pair counts on fresh data are lower bounds until late reverts are labelled.
*Flags:* W21 and W22 differ (November 2009 dump and about 24k; January 2010 dump and about 12k) because of threshold and filtering. UNVERIFIED: which of two filtered sample sizes printed in the paper (223k and 233k) is the typo. The formula for M was read only in words.

**W23. Tsvetkova et al. 2017.** M. Tsvetkova, R. García-Gavilanes, L. Floridi, and T. Yasseri, "Even good bots fight: the case of Wikipedia," PLoS ONE, vol. 12, no. 2, Art. no. e0171774, Feb. 2017. DOI 10.1371/journal.pone.0171774. Confirmed on [PLoS ONE](https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0171774) and [Crossref](https://api.crossref.org/works/10.1371/journal.pone.0171774); publisher HTML read.
*Found:* 13 language editions, 2001-2010; reverts detected by matching hashes of full article text. Human revert gaps cluster near **2 minutes, 24 hours and 1 year**; bots' characteristic response time is about 1 month.
*Relation:* Three characteristic human revert time scales; a label wait shorter than a day misses the second mode.

**W24. Geiger and Halfaker 2017.** R. S. Geiger and A. Halfaker, "Operationalizing conflict and cooperation between automated software agents in Wikipedia: a replication and expansion of 'Even Good Bots Fight'," Proc. ACM Hum.-Comput. Interact., vol. 1, no. CSCW, Article 49, pp. 1-33, Nov. 2017. DOI 10.1145/3134684. Preprint arXiv:1810.07273. Confirmed on [Crossref](https://api.crossref.org/works/10.1145/3134684); full text read at [arXiv](https://arxiv.org/pdf/1810.07273).
*Found:* Replicates W23 and concludes most bot-bot reverts are routine or collaborative work. Bot-bot reverts are 0.5% to 1% of bot edits to articles. Median bot-bot time to revert across languages and years **62 days**; English mean 355 days, median 138 days; English median rose from 26 days (2008) to 299 days (2016).
*Relation:* Identity reverts can arrive months or years after the edit, and long-delay reverts mean something different from fast ones. Bot edits should be excluded or reported separately in any pair count.
*Flags:* Issue numbering differs between Crossref and the paper (see the trap list).

### Temporary accounts and reverts of newcomers

**W25. Temporary Accounts project pages (MediaWiki.org).** Wikimedia Foundation, "Trust and Safety Product/Temporary Accounts" (last edited 6 February 2026) and its "Updates" subpage (last edited 2 October 2026), MediaWiki.org. Confirmed on the [project page](https://www.mediawiki.org/wiki/Trust_and_Safety_Product/Temporary_Accounts) and the [Updates page](https://www.mediawiki.org/wiki/Trust_and_Safety_Product/Temporary_Accounts/Updates). Full text read.
*Found:* A new account type for unregistered editors; where enabled, IP addresses are no longer public. Rollout: test wiki July 2024; 29 October 2024 (five pilot wikis); 5 November 2024 (seven more); latter half of June 2025 (MediaWiki.org and 18 large and medium Wikipedias). By December 2025 about **96%** of unregistered editing across Wikimedia wikis came from temporary accounts. Name format `~YYYY-nnnnn-nnn`; accounts last 90 days.
*Relation:* Changes the editor-identity field in the stream and in MediaWiki History; an IP-based "anonymous" flag or an IP-keyed editor pair is not comparable before and after rollout.
*Flags:* UNVERIFIED: the date the rollout finished on all wikis.

**W26. English Wikipedia deployment.** Wikimedia Phabricator, task T409079, "Deploy Temporary accounts to English Wikipedia"; and English Wikipedia, "Wikipedia:Temporary accounts" (project page, last edited 19 October 2026). Confirmed on [Phabricator](https://phabricator.wikimedia.org/T409079) and the [project page](https://en.wikipedia.org/wiki/Wikipedia:Temporary_accounts). Full text read.
*Found:* English Wikipedia deployment on **4 November 2025** (config change synced from about 08:02 UTC). Accounts expire 90 days after creation; IP records are kept 90 days after each edit.
*Relation:* Fixes the date after which English Wikipedia stream events carry temporary-account names.
*Flags:* The official MediaWiki.org pages do not state the English Wikipedia date; it is documented only on these two pages. UNVERIFIED: 12 November 2025 for Spanish Wikipedia, Commons and Wikidata (search summary, not opened).

**W27. Halfaker et al. 2013.** A. Halfaker, R. S. Geiger, J. T. Morgan, and J. Riedl, "The rise and decline of an open collaboration system: how Wikipedia's reaction to popularity is causing its decline," American Behavioral Scientist, vol. 57, no. 5, pp. 664-688, May 2013 (online 28 Dec. 2012). DOI 10.1177/0002764212469365. Confirmed on [Crossref](https://api.crossref.org/works/10.1177/0002764212469365); full text read at the [author PDF](https://stuartgeiger.com/papers/abs-rise-and-decline-wikipedia.pdf).
*Found:* The share of good-faith newcomers with at least one reverted first-session edit rose from **6.1% to 18.2%** between the first half of 2006 and the first half of 2007; tool-based rejection of newcomer edits rose from 0% in 2006 to 40% in 2010; rejection is a significant negative predictor of retention.
*Relation:* Reverts are not a pure "damage" label (good-faith edits are reverted too), and faster, tool-driven reverts carry a social cost. No newcomer-specific time-to-revert figure was found.
*Flags:* UNVERIFIED: print month (May 2013).

**W28. Halfaker, Kittur and Riedl 2011.** A. Halfaker, A. Kittur, and J. Riedl, "Don't bite the newbies: how reverts affect the quantity and quality of Wikipedia work," in Proc. 7th Int. Symp. Wikis and Open Collaboration (WikiSym '11), Mountain View, CA, USA, 2011, pp. 163-172. DOI 10.1145/2038558.2038585. Confirmed on [Crossref](https://api.crossref.org/works/10.1145/2038558.2038585); abstract via [OpenAlex](https://api.openalex.org/works/doi:10.1145/2038558.2038585). Abstract-level.
*Found:* Analyses 400,000 revisions; reverts are strongly demotivating, but on net more quality work results than is lost; the most harmful case is new editors reverted by much more experienced editors.
*Relation:* Supports reading the revert label as "rejected", not "vandalism".
*Flags:* UNVERIFIED: symposium location.

**W29. Kiesel et al. 2017 (record only).** J. Kiesel, M. Potthast, M. Hagen, and B. Stein, "Spatio-temporal analysis of reverted Wikipedia edits," Proc. Int. AAAI Conf. Web and Social Media (ICWSM), vol. 11, no. 1, pp. 122-131, 2017. DOI [10.1609/icwsm.v11i1.14900](https://doi.org/10.1609/icwsm.v11i1.14900). Confirmed to exist; not read.
*Flags:* Its percentages (6% pseudo reverts, 9% self-reverts, 11% in edit wars) are known only second-hand through W5. Its relevance to text similarity is UNVERIFIED.

**Leads the notes saw but did not open (not citable as they stand).** A 2009 Wikipedia Signpost vandalism study (100 random articles; median time to correction reported as about four minutes), and 2026 Wikimedia Phabricator tasks proposing a median "time-to-live" metric for reverted edits with a 7-day window. Both were seen only in search-result summaries. The second matters for the gap statement and should be opened before submission.

## Streaming and lakehouse systems say when to stop waiting, not how wrong an early answer is

**What the literature establishes.** Every streaming algorithm the project uses has one identifiable founding paper, all confirmed by DOI. The sketches split into mergeable or linear ones (Flajolet-Martin, HyperLogLog, AMS, Count-Min), which can absorb a late event by updating the sketch of the window it belongs to, and order- or insert-dependent ones (DGIM, Bloom, Misra-Gries, reservoir by arrival order), which cannot undo or reorder. That split is the researcher's synthesis; none of the founding papers discusses out-of-order arrival or labels that change after the fact, and each assumes a single ordered pass. The systems lineage is fully citable: Kafka for the replayable log, RDDs and D-Streams for micro-batch recovery by lineage, MillWheel and the Dataflow model for event time, watermarks and triggers, and Structured Streaming, whose watermark is max(event time) minus a user-set delay. Four citable mechanisms correct results after the fact: Dataflow's refinement modes (discarding, accumulating, accumulating and retracting), Spark's bounded-lateness watermark with a one-directional guarantee, Golab and Johnson's per-partition consistency levels (Open, Closed, Complete), and bitemporal tables (valid time plus transaction time). Delta Lake and the Lakehouse paper are confirmed; the medallion (bronze/silver/gold) pattern has no founding paper and must be cited to Databricks documentation. The project's design (stream first, reconcile against the monthly dump later) is a Lambda-style arrangement in Kreps's description, and its reconciliation corresponds to Dataflow's Accumulating mode when the gold row is overwritten. None of these sources measures the size of the error in an Open result as a function of the wait; they define mechanisms and levels, not the error curve. That is an inference from the texts read, not a claim that no such work exists.

### Founding papers for the six stream techniques and the textbook

**S1. Vitter 1985 (reservoir sampling; in the draft list).** J. S. Vitter, "Random sampling with a reservoir," ACM Transactions on Mathematical Software, vol. 11, no. 1, pp. 37-57, Mar. 1985. DOI 10.1145/3147.3165. Confirmed on [Crossref](https://api.crossref.org/works/10.1145/3147.3165); [PDF read](https://www.cs.umd.edu/~samir/498/vitter.pdf).
*Found:* Draws a uniform sample of n records without replacement from a pool of unknown size N in one pass; the main result, Algorithm Z, runs in expected time O(n(1 + log(N/n))). [RECALL] Algorithm R is the simple baseline that keeps the first n records and replaces a random slot with probability n/t for the t-th record, at O(N) time.
*Relation:* A fixed-size uniform sample of edits can be held while the stream length is unknown; revert labels that arrive later can be joined to the sampled revision ids without changing inclusion probabilities, because inclusion does not depend on the label.

**S2. Bloom 1970 (in the draft list).** B. H. Bloom, "Space/time trade-offs in hash coding with allowable errors," Communications of the ACM, vol. 13, no. 7, pp. 422-426, July 1970. DOI 10.1145/362686.362692. Confirmed on [Crossref](https://api.crossref.org/works/10.1145/362686.362692). Bibliographic record only.
*Found:* [RECALL] Hash-coded set membership that tolerates a small fraction of false positives for much less space, with no false negatives; the second of two methods is what is now called a Bloom filter.
*Relation:* Membership tests in fixed memory; a standard Bloom filter cannot delete, so a label that later changes cannot be removed.

**S3. Broder and Mitzenmacher 2004.** A. Broder and M. Mitzenmacher, "Network applications of Bloom filters: A survey," Internet Mathematics, vol. 1, no. 4, pp. 485-509, 2004. DOI 10.1080/15427951.2004.10129096. Confirmed on [Crossref](https://api.crossref.org/works/10.1080/15427951.2004.10129096); [PDF read](https://www.eecs.harvard.edu/~michaelm/postscripts/im2005b.pdf).
*Found:* Defines a Bloom filter as a space-efficient randomized structure for membership queries that allows false positives, and surveys variants and network uses. [RECALL] The false-positive rate with m bits, n keys and k hash functions is about (1 - e^(-kn/m))^k, minimized at k = (m/n) ln 2; counting Bloom filters support deletion.
*Relation:* The source to cite for the false-positive formula when comparing a measured rate against theory, once the formula is checked in the text.

**S4. Flajolet and Martin 1985 (in the draft list).** P. Flajolet and G. N. Martin, "Probabilistic counting algorithms for data base applications," Journal of Computer and System Sciences, vol. 31, no. 2, pp. 182-209, Oct. 1985. DOI 10.1016/0022-0000(85)90041-8. Confirmed on [Crossref](https://api.crossref.org/works/10.1016/0022-0000%2885%2990041-8); [PDF read](https://algo.inria.fr/flajolet/Publications/FlMa85.pdf).
*Found:* Estimates the number of distinct elements in one pass with small extra storage from bit patterns of hashed values; the estimate is insensitive to repeats, and sketches can be used across distributed sites. [RECALL] The PCSA variant has standard error about 0.78/sqrt(m) with correction constant phi ≈ 0.77351.
*Relation:* Distinct editors or pages per window; duplicates from replays do not change the estimate, and sketches from separate partitions merge.

**S5. Flajolet et al. 2007 (HyperLogLog; draft ref [25]).** P. Flajolet, É. Fusy, O. Gandouet, and F. Meunier, "HyperLogLog: the analysis of a near-optimal cardinality estimation algorithm," in Proc. 2007 Conference on Analysis of Algorithms (AofA 07), Discrete Mathematics and Theoretical Computer Science Proceedings, vol. AH, pp. 127-146, 2007. DOI 10.46298/dmtcs.3545. Confirmed on [Crossref](https://api.crossref.org/works/10.46298/dmtcs.3545); [PDF read](https://algo.inria.fr/flajolet/Publications/FlFuGaMe07.pdf).
*Found:* With m registers the relative standard error is about **1.04/sqrt(m)**; cardinalities well beyond 10^9 at about 2% typical accuracy using 1.5 kilobytes; the algorithm parallelizes.
*Relation:* Mergeable distinct-count sketches per window can be re-merged when late events are assigned to an old window.
*Flags:* Page-range trap (see the trap list).

**S6. Heule, Nunkesser and Hall 2013 (HyperLogLog++).** S. Heule, M. Nunkesser, and A. Hall, "HyperLogLog in practice: Algorithmic engineering of a state of the art cardinality estimation algorithm," in Proc. 16th International Conference on Extending Database Technology (EDBT '13), pp. 683-692, Mar. 2013. DOI 10.1145/2452376.2452456. Confirmed on [Crossref](https://api.crossref.org/works/10.1145/2452376.2452456); [PDF read](https://static.googleusercontent.com/media/research.google.com/en//pubs/archive/40671.pdf).
*Found:* Uses a 64-bit hash, an empirical bias correction for small cardinalities and a sparse representation.
*Relation:* The candidate citation when the report compares Spark's built-in estimate with a hand-written HLL.
*Flags:* UNVERIFIED: that Spark's `approx_count_distinct` implements this variant; Spark source and docs were not checked.

**S7. Alon, Matias and Szegedy 1996 / 1999 (AMS; conference version in the draft list).** Conference: N. Alon, Y. Matias, and M. Szegedy, "The space complexity of approximating the frequency moments," in Proc. 28th Annual ACM Symposium on Theory of Computing (STOC '96), pp. 20-29, 1996. DOI 10.1145/237814.237823. Confirmed on [Crossref](https://api.crossref.org/works/10.1145/237814.237823). Journal: same authors and title, Journal of Computer and System Sciences, vol. 58, no. 1, pp. 137-147, Feb. 1999. DOI 10.1006/jcss.1997.1545. Confirmed on [Crossref](https://api.crossref.org/works/10.1006/jcss.1997.1545); [author PDF read](https://www.tau.ac.il/~nogaa/PDFS/amsz4.pdf).
*Found:* Defines the k-th frequency moment F_k; F_0, F_1 and F_2 can be approximated in logarithmic space; approximating F_k for k ≥ 6 needs n^Ω(1) space. [RECALL] The F_2 estimator uses four-wise independent ±1 hashes with median-of-means, O((1/ε²) log(1/δ)) counters.
*Relation:* F_2 of the edits-per-page distribution measures skew; the sketch is linear, so late edits can be added to their window's sketch.

**S8. Datar et al. 2002 (DGIM; in the draft list).** M. Datar, A. Gionis, P. Indyk, and R. Motwani, "Maintaining stream statistics over sliding windows," SIAM Journal on Computing, vol. 31, no. 6, pp. 1794-1813, 2002. DOI 10.1137/S0097539701398363. Confirmed on [Crossref](https://api.crossref.org/works/10.1137/S0097539701398363). Bibliographic record only.
*Found:* [RECALL] Counts the 1s among the last N bits with relative error at most ε using O((1/ε) log² N) bits, with a matching lower bound; extends to sums of bounded integers.
*Relation:* "How many of the last N edits were reverted" in small memory. The structure assumes bits arrive in order with their final value; a revert label that arrives after the edit's bit was recorded is outside the model.

**S9. Cormode and Muthukrishnan 2005 (Count-Min; related alternative, not used in the project).** G. Cormode and S. Muthukrishnan, "An improved data stream summary: the count-min sketch and its applications," Journal of Algorithms, vol. 55, no. 1, pp. 58-75, Apr. 2005. DOI 10.1016/j.jalgor.2003.12.001. Confirmed on [Crossref](https://api.crossref.org/works/10.1016/j.jalgor.2003.12.001). Bibliographic record only.
*Found:* [RECALL] A d × w counter array; a point query overestimates by at most ε·(total count) with probability at least 1 − δ; linear, so it accepts decrements.
*Relation:* Because decrements are allowed, a retracted label can be subtracted, which a Bloom filter or Misra-Gries summary cannot do.

**S10. Misra and Gries 1982.** J. Misra and D. Gries, "Finding repeated elements," Science of Computer Programming, vol. 2, no. 2, pp. 143-152, Nov. 1982. DOI 10.1016/0167-6423(82)90012-0. Confirmed on [Crossref](https://api.crossref.org/works/10.1016/0167-6423%2882%2990012-0). Bibliographic record only.
*Found:* [RECALL] Finds every value occurring more than n/k times using k − 1 counters in one pass; each count undercounts by at most n/k.
*Relation:* Most-edited or most-reverted pages in fixed memory; deterministic, insert-only.

**S11. Metwally, Agrawal and El Abbadi 2005 (Space-Saving; optional).** A. Metwally, D. Agrawal, and A. El Abbadi, "Efficient computation of frequent and top-k elements in data streams," in Database Theory - ICDT 2005, Lecture Notes in Computer Science vol. 3363, pp. 398-412, Springer, 2005. DOI 10.1007/978-3-540-30570-5_27. Confirmed on [Crossref](https://api.crossref.org/works/10.1007/978-3-540-30570-5_27) (Crossref lists the online date as 2004). Bibliographic record only.
*Found:* [RECALL] Keeps m counters and replaces the minimum counter when full, giving overestimates bounded by n/m.
*Relation:* Top-k pages by revert count; insert-only.
*Flags:* UNVERIFIED: LNCS volume number 3363.

**S12. Leskovec, Rajaraman and Ullman 2020 (textbook; also the LSH teaching reference).** J. Leskovec, A. Rajaraman, and J. D. Ullman, Mining of Massive Datasets, 3rd ed. Cambridge, U.K.: Cambridge University Press, 2020. DOI 10.1017/9781108684163. ISBN 9781108476348 (print). Confirmed on [Crossref](https://api.crossref.org/works/10.1017/9781108684163) (edition 3, issued 2020-01-09) and the [authors' book page](http://infolab.stanford.edu/~ullman/mmds.html).
*Found:* The authors' page lists a third edition and names Chapter 4 "Mining Data Streams" and Chapter 3 "Finding Similar Items". [RECALL] Chapter 4 covers the stream model, sampling, Bloom filters, Flajolet-Martin, AMS moments, DGIM and decaying windows. Chapter 3 facts confirmed from the authors' slide deck are under L11.
*Relation:* The course-level reference that ties the project's techniques together; cite it once for the stream model and cite the original papers for the bounds.
*Flags:* UNVERIFIED: section numbers in chapters 3 and 4; the chapter PDFs could not be opened.

### Stream processing systems

**S13. Kreps, Narkhede and Rao 2011 (Kafka).** J. Kreps, N. Narkhede, and J. Rao, "Kafka: a distributed messaging system for log processing," in Proc. 6th International Workshop on Networking Meets Databases (NetDB '11), Athens, Greece, June 12, 2011. No DOI found. [PDF read (mirror)](https://notes.stephenholiday.com/Kafka.pdf); the footer reads "NetDB'11, Jun. 12, 2011, Athens, Greece".
*Found:* A distributed messaging system for high volumes of log data with low latency; messages are addressed by logical offset in a partition log, and a consumer can deliberately rewind to an old offset and re-consume.
*Relation:* A retained, offset-addressed log is what makes reprocessing after late labels possible; the project's captured SSE files play the same role.
*Flags:* UNVERIFIED: page numbers (commonly cited as pp. 1-7) and the "6th" ordinal; no publisher page was opened.

**S14. Zaharia et al. 2012 (RDDs).** M. Zaharia, M. Chowdhury, T. Das, A. Dave, J. Ma, M. McCauley, M. J. Franklin, S. Shenker, and I. Stoica, "Resilient distributed datasets: A fault-tolerant abstraction for in-memory cluster computing," in Proc. 9th USENIX Symposium on Networked Systems Design and Implementation (NSDI '12), San Jose, CA, pp. 15-28, Apr. 2012. No DOI. Confirmed on the [USENIX page](https://www.usenix.org/conference/nsdi12/technical-sessions/presentation/zaharia).
*Found:* A distributed memory abstraction for fault-tolerant in-memory computation, built on coarse-grained transformations; implemented as Spark.
*Relation:* The batch side of the project runs on this engine; lineage-based recomputation allows deterministic rebuilds of silver and gold tables.
*Flags:* UNVERIFIED: spelling of the sixth author (the USENIX page prints "McCauly"; the paper PDF, not opened, is believed to print "McCauley").

**S15. Zaharia et al. 2013 (Discretized Streams).** M. Zaharia, T. Das, H. Li, T. Hunter, S. Shenker, and I. Stoica, "Discretized streams: Fault-tolerant streaming computation at scale," in Proc. 24th ACM Symposium on Operating Systems Principles (SOSP '13), pp. 423-438, Nov. 2013. DOI 10.1145/2517349.2522737. Confirmed on [Crossref](https://api.crossref.org/works/10.1145/2517349.2522737); [PDF read](https://people.csail.mit.edu/matei/papers/2013/sosp_spark_streaming.pdf).
*Found:* Treats a stream as a series of small deterministic batch computations and recovers lost state from lineage; reports over 60 million records per second on 100 nodes at sub-second latency.
*Relation:* The micro-batch model the project's streaming job runs under; D-Streams window by arrival time, the limitation event-time watermarks address.

**S16. Armbrust et al. 2018 (Structured Streaming; in the draft list).** M. Armbrust, T. Das, J. Torres, B. Yavuz, S. Zhu, R. Xin, A. Ghodsi, I. Stoica, and M. Zaharia, "Structured Streaming: A declarative API for real-time applications in Apache Spark," in Proc. 2018 International Conference on Management of Data (SIGMOD '18), pp. 601-613, May 2018. DOI 10.1145/3183713.3190664. Confirmed on [Crossref](https://api.crossref.org/works/10.1145/3183713.3190664); [PDF read](https://people.eecs.berkeley.edu/~matei/papers/2018/sigmod_structured_streaming.pdf).
*Found:* A query over a stream is written like a query over a table and incrementalized by the engine. The watermark for event-time column C with delay t_C is **max(C) − t_C** (section 4.3.1); watermarks decide when stateful operators can emit and forget state; lateness is bounded because arbitrarily late data would require arbitrarily old state.
*Relation:* The project's `withWatermark` call is exactly this definition; a revert later than the delay falls outside the streaming aggregate and must be picked up by a later batch reconciliation.

**S17. Apache Spark documentation (watermark semantics; official, not peer-reviewed).** Apache Software Foundation, "Structured Streaming Programming Guide: APIs on DataFrames and Datasets," Apache Spark documentation (the guide reported version 4.3.0 on the access date). Accessed Nov. 17, 2026. [Page read](https://spark.apache.org/docs/latest/streaming/apis-on-dataframes-and-datasets.html).
*Found:* Watermarking was introduced in Spark 2.1. The guarantee is one-directional: data delayed by less than the threshold is never dropped; data delayed by more is "not guaranteed to be dropped". In append mode a windowed aggregate is written only after the watermark passes the window end.
*Relation:* The precise statement to cite for why a streamed revert count is final only after the watermark and why very late reverts are not counted by the stream.

**S18. Carbone et al. 2015 (Flink).** P. Carbone, A. Katsifodimos, S. Ewen, V. Markl, S. Haridi, and K. Tzoumas, "Apache Flink: Stream and batch processing in a single engine," Bulletin of the IEEE Computer Society Technical Committee on Data Engineering, vol. 38, no. 4, pp. 28-38, Dec. 2015. No DOI. [PDF read](http://sites.computer.org/debull/A15dec/p28.pdf).
*Found:* Batch programs are a special case of streaming dataflows on one engine. A watermark carries a time t stating that all events with time lower than t have entered the operator; an operator with several inputs forwards the minimum incoming watermark (section 4.1).
*Relation:* The alternative record-at-a-time engine to name when justifying Spark; its watermark is the same concept.
*Flags:* UNVERIFIED: author order (the PDF's first page prints Carbone, Ewen, Haridi, Katsifodimos, Markl, Tzoumas in a three-column layout), end page 38, and volume/issue (from the file path and recall).

**S19. Akidau et al. 2013 (MillWheel).** T. Akidau, A. Balikov, K. Bekiroğlu, S. Chernyak, J. Haberman, R. Lax, S. McVeety, D. Mills, P. Nordstrom, and S. Whittle, "MillWheel: Fault-tolerant stream processing at Internet scale," Proceedings of the VLDB Endowment, vol. 6, no. 11, pp. 1033-1044, Aug. 2013. DOI 10.14778/2536222.2536229. Confirmed on [Crossref](https://api.crossref.org/works/10.14778/2536222.2536229). Bibliographic record only.
*Found:* [RECALL] Introduces the low watermark as a system-maintained bound on the event time of pending work; provides exactly-once delivery through per-key persistent state.
*Relation:* The origin of the watermark concept in this lineage.
*Flags:* Crossref holds only the short title "MillWheel"; the subtitle is from recall. UNVERIFIED: that reference [2] in both the Dataflow and Structured Streaming papers is MillWheel.

**S20. Akidau et al. 2015 (Dataflow model; draft ref [20]).** T. Akidau, R. Bradshaw, C. Chambers, S. Chernyak, R. J. Fernández-Moctezuma, R. Lax, S. McVeety, D. Mills, F. Perry, E. Schmidt, and S. Whittle, "The Dataflow model: A practical approach to balancing correctness, latency, and cost in massive-scale, unbounded, out-of-order data processing," Proceedings of the VLDB Endowment, vol. 8, no. 12, pp. 1792-1803, Aug. 2015. DOI 10.14778/2824032.2824076. Confirmed on [Crossref](https://api.crossref.org/works/10.14778/2824032.2824076); [PDF read](https://www.vldb.org/pvldb/vol8/p1792-Akidau.pdf).
*Found:* Stop treating unbounded data as something that eventually becomes complete; assume new data will arrive and "old data may be retracted". Separates event time from processing time; triggers decide when a pane is emitted. Watermarks alone are insufficient: they can be too fast (late data arrives behind them) or too slow. Three refinement modes relate successive panes of a window: Discarding, Accumulating, and Accumulating and Retracting (section 2.3). The paper describes the Lambda Architecture as streaming results later overwritten by batch results.
*Relation:* The vocabulary (event time, watermark, late datum, pane, refinement) for a live revert count that is revised as labels arrive.
*Flags:* UNVERIFIED: whether the 2015 paper itself names "allowed lateness"; that parameter belongs to the later Beam model.

**S21. Kreps 2014 (Kappa architecture; blog, not peer-reviewed).** J. Kreps, "Questioning the Lambda Architecture," O'Reilly Radar, July 2, 2014. [Page read](https://www.oreilly.com/radar/questioning-the-lambda-architecture/).
*Found:* Describes Lambda as an immutable input log feeding a batch pipeline and a stream pipeline in parallel, merged at query time; proposes a single stream system that reprocesses by replaying the retained log into a new output table.
*Relation:* The project is closer to Lambda (a live stream path plus a monthly-dump batch path that later overrides it); this is the citable source for the trade-off.

**S22. Marz and Warren 2015 (Lambda architecture; book).** N. Marz and J. Warren, Big Data: Principles and Best Practices of Scalable Realtime Data Systems. Shelter Island, NY: Manning, Apr. 2015. ISBN 978-1-61729-034-3. 328 pp. Confirmed on the [publisher page](https://www.manning.com/books/big-data), which states the book presents the Lambda Architecture.
*Found:* [RECALL] Three layers: batch, serving and speed.
*Relation:* The speed layer's results being overwritten by the batch layer is the analogue of stream labels being replaced by the later History snapshot.
*Flags:* UNVERIFIED: the layer names (not on the page read).

### Lakehouse storage and the medallion pattern

**S23. Armbrust et al. 2020 (Delta Lake; in the draft list).** M. Armbrust, T. Das, L. Sun, B. Yavuz, S. Zhu, M. Murthy, J. Torres, H. van Hovell, A. Ionescu, A. Łuszczak, M. Świtakowski, M. Szafrański, X. Li, T. Ueshin, M. Mokhtar, P. Boncz, A. Ghodsi, S. Paranjpye, P. Senster, R. Xin, and M. Zaharia, "Delta Lake: High-performance ACID table storage over cloud object stores," Proceedings of the VLDB Endowment, vol. 13, no. 12, pp. 3411-3424, Aug. 2020. DOI 10.14778/3415478.3415560. Confirmed on [Crossref](https://api.crossref.org/works/10.14778/3415478.3415560); [PDF read](https://www.vldb.org/pvldb/vol13/p3411-armbrust.pdf).
*Found:* An ACID table layer over cloud object stores; a transaction log stored in the object store determines each table version; optimistic concurrency control; time travel, UPSERT, DELETE and MERGE, and streaming ingest with exactly-once semantics.
*Relation:* MERGE is how a late label updates an already-written row; time travel by table version gives the "what did the table say at time X" axis.

**S24. Armbrust et al. 2021 (Lakehouse).** M. Armbrust, A. Ghodsi, R. Xin, and M. Zaharia, "Lakehouse: A new generation of open platforms that unify data warehousing and advanced analytics," in Proc. 11th Conference on Innovative Data Systems Research (CIDR '21), Jan. 2021. No DOI. [PDF read](https://www.cidrdb.org/cidr2021/papers/cidr2021_paper17.pdf).
*Found:* Defines a lakehouse as a data management system on low-cost, directly accessible storage that also provides ACID transactions, versioning, auditing, indexing, caching and query optimization. A text search of the paper finds no occurrence of "bronze", "medallion" or "gold".
*Relation:* Justifies keeping raw captures, cleaned tables and aggregates in one open-format store with versioning.
*Flags:* UNVERIFIED: the "11th" ordinal. CIDR papers have no page numbers in a bound volume.

**S25. Databricks documentation (medallion architecture; vendor documentation).** Databricks, "What is the medallion lakehouse architecture?," Databricks on AWS documentation, last updated Oct. 29, 2026. Accessed Nov. 17, 2026. [Page read](https://docs.databricks.com/aws/en/lakehouse/medallion).
*Found:* Bronze holds raw, unvalidated source data kept mostly unchanged; silver holds validated, cleaned, deduplicated data; gold holds refined, usually aggregated data. The page calls it a data design pattern, also known as multi-hop architecture, and gives no origin or academic citation.
*Relation:* Bronze = raw SSE events and dump rows, silver = cleaned edits joined to revert labels, gold = lag and error aggregates; keeping bronze unchanged permits re-deriving silver when labels arrive late.
*Flags:* The first public use of the term "medallion" was not established.

### Correcting results after the fact

**S26. Golab and Johnson 2011 (draft ref [21]).** L. Golab and T. Johnson, "Consistency in a stream warehouse," in Proc. 5th Biennial Conference on Innovative Data Systems Research (CIDR '11), Asilomar, CA, Jan. 9-12, 2011. No DOI. [PDF read](https://www.cidrdb.org/cidr2011/Papers/CIDR11_Paper13.pdf) (9 pages).
*Found:* Defines a stream warehouse as a continuously loaded warehouse; users want timely results but stable results need long delays. Each temporal partition has a consistency level: **Open** (more data may come), **Closed** (no more updates expected), **Complete** (Closed and all expected data arrived). Queries can be restricted to a required level.
*Relation:* A day's revert-rate partition is Open while reverts can still arrive, Closed after a chosen wait, and Complete once the monthly History snapshot covering it is loaded. This gives formal names to "how long to wait before trusting a count".
*Flags:* UNVERIFIED: proceedings page range (commonly cited as pp. 114-122).

**S27. Snodgrass (bitemporal tables; draft ref [24]).** R. T. Snodgrass, Developing Time-Oriented Database Applications in SQL. San Francisco, CA: Morgan Kaufmann, 504+xxiii pp., ISBN 1-55860-436-7. Confirmed on the [author's publications page](https://www2.cs.arizona.edu/~rts/publications.html), which gives the publication date as July 1999.
*Found:* [RECALL] Distinguishes valid time (when a fact was true in the world) from transaction time (when the database recorded it); a bitemporal table carries both. [RECALL] SQL patterns for current, sequenced and nonsequenced queries.
*Relation:* Edit timestamp = valid time; the time the pipeline learned of the revert = transaction time. The project's two-axis time travel is a bitemporal query.
*Flags:* UNVERIFIED: which year the title page prints (see the trap list). Chapter and page pointers are missing.

**S28. Kimball and Ross 2013 (draft ref [23]).** R. Kimball and M. Ross, The Data Warehouse Toolkit: The Definitive Guide to Dimensional Modeling, 3rd ed. Indianapolis, IN: Wiley, July 2013. ISBN 978-1-118-53080-1. 608 pp. Confirmed on the [publisher page](https://www.wiley.com/en-us/The+Data+Warehouse+Toolkit%3A+The+Definitive+Guide+to+Dimensional+Modeling%2C+3rd+Edition-p-9781118530801).
*Found:* [RECALL] Defines slowly changing dimension types (type 1 overwrite, type 2 new row with effective dates) and treats late-arriving facts and dimensions. The publisher page does not name these topics.
*Relation:* A revert label that arrives after the edit fact row was loaded is a late-arriving attribute; type 2 history on the label is the dimensional counterpart of a bitemporal row.
*Flags:* UNVERIFIED: chapter numbers.

**S29. Hellerstein, Haas and Wang 1997 (draft ref [22]).** J. M. Hellerstein, P. J. Haas, and H. J. Wang, "Online aggregation," in Proc. 1997 ACM SIGMOD International Conference on Management of Data (SIGMOD '97), pp. 171-182, 1997. DOI 10.1145/253260.253291. Confirmed on [Crossref](https://api.crossref.org/works/10.1145/253260.253291). Bibliographic record only.
*Found:* [RECALL] Shows a running estimate of an aggregate with a confidence interval that tightens as more tuples are processed; [RECALL] requires tuples in random order for the interval to be valid.
*Relation:* Precedent for reporting an early answer with a stated error. The difference to note: online aggregation's error comes from sampling, while a live revert rate's error comes from labels that have not yet arrived, which is not random.

**S30. Begoli et al. 2019 (optional).** E. Begoli, T. Akidau, F. Hueske, J. Hyde, K. Knight, and K. Knowles, "One SQL to rule them all: An efficient and syntactically idiomatic approach to management of streams and tables," in Proc. 2019 International Conference on Management of Data (SIGMOD '19), pp. 1757-1772, June 2019. DOI 10.1145/3299869.3314040. Confirmed on [Crossref](https://api.crossref.org/works/10.1145/3299869.3314040). Bibliographic record only.
*Found:* [RECALL] SQL extensions built on time-varying relations, event-time semantics with watermarks, and emitting changes as a stream with retractions.
*Relation:* Supports describing the revert-labelled edit table as a time-varying relation whose earlier answers are revised.

### Graph and document stores

**S31. Angles et al. 2017.** R. Angles, M. Arenas, P. Barceló, A. Hogan, J. Reutter, and D. Vrgoč, "Foundations of modern query languages for graph databases," ACM Computing Surveys, vol. 50, no. 5, Article 68, pp. 1-40, Sept. 2017. DOI 10.1145/3104031. Confirmed on [Crossref](https://api.crossref.org/works/10.1145/3104031). Bibliographic record only.
*Found:* [RECALL] Surveys edge-labelled graphs and property graphs and core query features; compares SPARQL, Cypher and Gremlin.
*Relation:* The formal definition of the property graph used to store revert links.
*Flags:* UNVERIFIED: article number 68.

**S32. Francis et al. 2018 (Cypher).** N. Francis, A. Green, P. Guagliardo, L. Libkin, T. Lindaaker, V. Marsault, S. Plantikow, M. Rydberg, P. Selmer, and A. Taylor, "Cypher: An evolving query language for property graphs," in Proc. 2018 International Conference on Management of Data (SIGMOD '18), pp. 1433-1445, May 2018. DOI 10.1145/3183713.3190657. Confirmed on [Crossref](https://api.crossref.org/works/10.1145/3183713.3190657). Bibliographic record only.
*Found:* [RECALL] Describes Cypher's design and a formal semantics for its core read fragment.
*Relation:* The citation for the query language used on the revert graph (mutual-revert pairs as a two-edge pattern).
*Flags:* Crossref holds only the short title "Cypher"; the subtitle is from recall.

**S33. Neo4j documentation (official).** Neo4j, Inc., "Graph database concepts," Neo4j Getting Started documentation. Accessed Nov. 17, 2026. [Page read](https://neo4j.com/docs/getting-started/appendix/graphdb-concepts/).
*Found:* Nodes can carry zero or more labels; a relationship has a direction and exactly one type; both can hold key-value properties.
*Relation:* Direction matters for reverts (who reverted whom); late revert links are added as new relationships.

**S34. Schultz, Avitabile and Cabral 2019 (MongoDB; peer-reviewed).** W. Schultz, T. Avitabile, and A. Cabral, "Tunable consistency in MongoDB," Proceedings of the VLDB Endowment, vol. 12, no. 12, pp. 2071-2081, Aug. 2019. DOI 10.14778/3352063.3352125. Confirmed on [Crossref](https://api.crossref.org/works/10.14778/3352063.3352125). Bibliographic record only.
*Found:* [RECALL] Describes MongoDB's replication and per-operation write concern and read concern.
*Relation:* The peer-reviewed citation for MongoDB as the serving store for gold results.

**S35. MongoDB documentation (official).** MongoDB, Inc., "Documents," MongoDB Database Manual. Accessed Nov. 17, 2026. [Page read](https://www.mongodb.com/docs/manual/core/document/).
*Found:* Records are BSON documents; maximum document size is 16 mebibytes; `_id` is the primary key, unique and immutable.
*Relation:* A deterministic `_id` makes re-loading corrected results an idempotent upsert. S31, S32 and S34 suffice for an IEEE list; S33 and S35 are needed only if the report states these specific data-model facts.

## MinHash and LSH: a confirmed chain from 1997, and Spark implements only the OR half

**What the literature establishes.** The founding chain is confirmed: Broder 1997 (resemblance by shingles and min sampling), Broder et al. 1998/2000 (min-wise independent permutations), Indyk-Motwani 1998 and Gionis et al. 1999 (LSH and hash-table amplification), Charikar 2002 (LSH defined as collision probability equal to similarity; SimHash), Datar et al. 2004 (Euclidean LSH), and Andoni-Indyk 2008 (survey with the amplification formula). Broder's papers predate the term LSH, so the accurate wording is that MinHash is an LSH family for Jaccard similarity in the sense of Charikar 2002. The citation for the banding S-curve formula is Andoni-Indyk (L8) or the textbook (L11), not Broder. Evaluations give concrete numbers: precision 0.38 for shingling against 0.50 for SimHash on 1.6 billion web pages (L9), and a storage reduction of at least 21.3 times for b-bit MinHash at resemblance 0.5 or more (L12). Spark's guide implements MinHash for Jaccard distance with OR-amplification only and cites Wikipedia, not the founding papers, so the report should cite the papers itself and cite the Spark guide only for implementation behaviour. The limits are documented: short items give few shingles, fewer bands or more rows trade false positives for false negatives, and candidate verification is a separate cost. Applications close to the project are few: two confirmed studies apply near-duplicate hashing to Wikipedia text (L18, L19), and revert research uses checksums or word-level diffs. The notes found no source applying MinHash or LSH to edit comments, diffs or revert detection; searches were limited to Crossref and OpenAlex title queries, so state this as "we found no prior work", not "none exists". No deep-learning methods are included. The notes suggest a core set of sixteen: L1-L9, L11, L12, L16-L19 and L21.

### Founding papers

**L1. Broder 1997 (in the draft list).** A. Z. Broder, "On the resemblance and containment of documents," in Proc. Compression and Complexity of SEQUENCES 1997 (Cat. No.97TB100171), IEEE Computer Society, pp. 21-29. DOI [10.1109/SEQUEN.1997.666900](https://doi.org/10.1109/SEQUEN.1997.666900). Confirmed on [Crossref](https://api.crossref.org/works/10.1109/SEQUEN.1997.666900); abstract via [OpenAlex](https://api.openalex.org/works/doi:10.1109/SEQUEN.1997.666900). Abstract-level.
*Found:* Defines resemblance r(A,B) and containment c(A,B) for "roughly the same" and "roughly contained"; reduces both to set-intersection problems estimated by random sampling done independently per document, with a fixed-size sample for resemblance; implemented with Rabin fingerprints.
*Relation:* The Jaccard-over-shingles definition the project's MinHash stage estimates; "containment" is the relevant notion when one edit comment or diff is a subset of another.
*Flags:* UNVERIFIED: the printed proceedings year (see the trap list) and the city (Salerno, Italy). UNVERIFIED: that the estimator is unbiased with variance shrinking as 1/(sample size).

**L2. Broder et al. 1997 (syntactic clustering).** A. Z. Broder, S. C. Glassman, M. S. Manasse, and G. Zweig, "Syntactic clustering of the Web," Computer Networks and ISDN Systems, vol. 29, no. 8-13, pp. 1157-1166, Sept. 1997 (Proc. 6th Int. WWW Conf.). DOI 10.1016/S0169-7552(97)00031-7. Confirmed on [Crossref](https://api.crossref.org/works/10.1016/S0169-7552%2897%2900031-7). Bibliographic record only.
*Found:* Nothing first-hand. L9 and L18 both treat this "shingling" method as the baseline near-duplicate algorithm.
*Relation:* The first large-scale use of shingle sketches to group similar documents, the same pipeline shape as shingle, MinHash, candidate pairs.
*Flags:* UNVERIFIED: about 30 million AltaVista pages, the resemblance threshold, and "super-shingles". Do not put numbers from this paper in the report without opening it.

**L3. Broder et al. 2000 / 1998 (min-wise independent permutations).** A. Z. Broder, M. Charikar, A. M. Frieze, and M. Mitzenmacher, "Min-wise independent permutations," Journal of Computer and System Sciences, vol. 60, no. 3, pp. 630-659, June 2000. DOI [10.1006/jcss.1999.1690](https://doi.org/10.1006/jcss.1999.1690). Conference version: "Min-wise independent permutations (extended abstract)," Proc. 30th ACM STOC, 1998, pp. 327-336. DOI [10.1145/276698.276781](https://doi.org/10.1145/276698.276781). Both confirmed on Crossref. Bibliographic record only.
*Found:* Second-hand, from Charikar's abstract: min-wise independent permutations give a hashing scheme whose collision probability equals |A∩B|/|A∪B|.
*Relation:* Justifies using cheap random hash functions in place of true random permutations of the shingle vocabulary.
*Flags:* UNVERIFIED: that it defines exact and approximate min-wise independent families and gives lower bounds on family size.

**L3b. Bohman, Cooper and Frieze 2000 (the family Spark uses).** T. Bohman, C. Cooper, and A. Frieze, "Min-wise independent linear permutations," Electronic Journal of Combinatorics, vol. 7, no. 1, R26, 2000. DOI 10.37236/1504. Confirmed on [Crossref](https://api.crossref.org/works/10.37236/1504). Spark's MinHashLSH [source comment](https://github.com/apache/spark/blob/master/mllib/src/main/scala/org/apache/spark/ml/feature/MinHashLSH.scala) cites it as the reason the hash family h(x) = ((x·a + b) mod prime) is approximately min-wise independent.

**L4. Indyk and Motwani 1998 (in the draft list).** P. Indyk and R. Motwani, "Approximate nearest neighbors: towards removing the curse of dimensionality," Proc. 30th ACM STOC, 1998, pp. 604-613. DOI [10.1145/276698.276876](https://doi.org/10.1145/276698.276876). Confirmed on [Crossref](https://api.crossref.org/works/10.1145/276698.276876) (the Crossref title is truncated to "Approximate nearest neighbors"; OpenAlex gives the full subtitle). Bibliographic record only.
*Found:* Second-hand, from L8's full text: the (R, cR, P1, P2)-sensitive definition and the n^ρ query bound are attributed to this line of work.
*Relation:* The source of the formal guarantee that near pairs collide with probability at least p1 and far pairs with probability at most p2.
*Flags:* UNVERIFIED: any specific theorem statement from this paper.

**L5. Gionis, Indyk and Motwani 1999.** A. Gionis, P. Indyk, and R. Motwani, "Similarity search in high dimensions via hashing," Proc. 25th Int. Conf. Very Large Data Bases (VLDB), 1999, pp. 518-529. No DOI. Confirmed on an [OpenAlex record](https://api.openalex.org/works?search=Similarity%20Search%20in%20High%20Dimensions%20via%20Hashing) only. Abstract-level.
*Found:* Tree indexes degrade to near linear scan beyond roughly 10-20 dimensions; proposes hashing so that close points collide more often than distant ones.
*Relation:* The multi-table (OR) scheme Spark exposes as `numHashTables` descends from this design.
*Flags:* The page range rests on OpenAlex only. UNVERIFIED: the publisher PDF URL (https://www.vldb.org/conf/1999/P49.pdf returned 403), the city (Edinburgh) and the publisher (Morgan Kaufmann).

**L6. Charikar 2002.** M. S. Charikar, "Similarity estimation techniques from rounding algorithms," Proc. 34th ACM STOC, 2002, pp. 380-388. DOI [10.1145/509907.509965](https://doi.org/10.1145/509907.509965). Confirmed on Crossref; abstract via [OpenAlex](https://api.openalex.org/works/doi:10.1145/509907.509965). Abstract-level.
*Found:* Defines an LSH scheme as a hash family with Pr[h(x)=h(y)] = sim(x,y); gives a random-hyperplane scheme usable for cosine similarity (later called SimHash).
*Relation:* The alternative to MinHash if edits were weighted token vectors (cosine) instead of shingle sets (Jaccard).

**L7. Datar et al. 2004.** M. Datar, N. Immorlica, P. Indyk, and V. S. Mirrokni, "Locality-sensitive hashing scheme based on p-stable distributions," Proc. 20th Annual Symp. Computational Geometry (SoCG), 2004, pp. 253-262. DOI [10.1145/997817.997857](https://doi.org/10.1145/997817.997857). Confirmed on Crossref; abstract via [OpenAlex](https://api.openalex.org/works/doi:10.1145/997817.997857). Abstract-level.
*Found:* LSH for l_p norms that works directly on Euclidean points; reports up to 40x speed-up over kd-trees on synthetic data.
*Relation:* The family behind Spark's BucketedRandomProjectionLSH; not the family the project uses, but the reason the Spark API has two LSH classes.

**L8. Andoni and Indyk 2008.** A. Andoni and P. Indyk, "Near-optimal hashing algorithms for approximate nearest neighbor in high dimensions," Communications of the ACM, vol. 51, no. 1, pp. 117-122, Jan. 2008. DOI [10.1145/1327452.1327494](https://doi.org/10.1145/1327452.1327494). Confirmed on Crossref; [full text read](https://people.csail.mit.edu/indyk/p117-andoni.pdf).
*Found:* Definition 2.3: a family is (R, cR, P1, P2)-sensitive if points within R collide with probability ≥ P1 and points beyond cR with probability ≤ P2. Amplification: with k concatenated functions per table and L tables, a near pair collides in at least one table with probability ≥ **1 − (1 − P1^k)^L**. Worst-case query time can reach Θ(n). Lists Jaccard/min-hash as one LSH family.
*Relation:* The citable form of the S-curve (k = rows, L = bands) used to predict recall of candidate generation.

### Variants, evaluations and the textbook

**L9. Henzinger 2006.** M. Henzinger, "Finding near-duplicate web pages: a large-scale evaluation of algorithms," Proc. 29th Annual Int. ACM SIGIR Conf., 2006, pp. 284-291. DOI [10.1145/1148170.1148222](https://doi.org/10.1145/1148170.1148222). Confirmed on Crossref; abstract via [OpenAlex](https://api.openalex.org/works/doi:10.1145/1148170.1148222). Abstract-level.
*Found:* Compares shingling with Charikar's method on **1.6 billion** web pages: precision **0.38** against **0.50**; a combined algorithm reached precision 0.79 at 79% of the recall.
*Relation:* Precedent for judging LSH candidate pairs by hand labels, and evidence that hash candidates need a second check. The figures are for web pages with boilerplate; they are not a prediction for edit text.

**L10. Manku, Jain and Das Sarma 2007.** G. S. Manku, A. Jain, and A. Das Sarma, "Detecting near-duplicates for web crawling," Proc. 16th Int. Conf. World Wide Web (WWW), 2007, pp. 141-150. DOI [10.1145/1242572.1242592](https://doi.org/10.1145/1242572.1242592). Confirmed on Crossref; abstract via [OpenAlex](https://api.openalex.org/works/doi:10.1145/1242572.1242592). Abstract-level.
*Found:* Charikar's fingerprint suits near-duplicate detection in a multi-billion-page repository; gives a method to find stored f-bit fingerprints within Hamming distance k of a query.
*Relation:* The streaming counterpart (one new item against a stored set), relevant if similar-edit lookup were done per incoming edit.
*Flags:* UNVERIFIED: 64-bit fingerprints, k = 3, 8 billion pages.

**L11. Leskovec, Rajaraman and Ullman 2020, chapter 3 (same book as S12).** Mining of Massive Datasets, 3rd ed., ch. 3 "Finding Similar Items". DOI [10.1017/9781108684163](https://doi.org/10.1017/9781108684163). The facts below are from the authors' official chapter-3 [slide deck](http://www.mmds.org/mmds/v2.1/ch03-lsh.pdf), full text read; the book chapter itself could not be opened.
*Found:* With b bands of r rows, a pair with similarity t becomes a candidate with probability **1 − (1 − t^r)^b**; the threshold is about (1/b)^(1/r). Worked example b = 20, r = 5: at similarity 0.8 the miss probability is 0.00035; at similarity 0.3, 4.74% become candidates. Shingle size: k = 5 for short documents, k = 10 for long ones.
*Relation:* The standard teaching reference for the pipeline the project runs (shingle, MinHash signature, band, verify).
*Flags:* UNVERIFIED: section numbers inside chapter 3. The k = 5 / k = 10 advice is for character shingles; the project uses token shingles, so the rule does not transfer directly.

**L12. Li and König 2010 (b-bit MinHash).** P. Li and A. C. König, "b-Bit minwise hashing," Proc. 19th Int. Conf. World Wide Web (WWW), 2010, pp. 671-680. DOI [10.1145/1772690.1772759](https://doi.org/10.1145/1772690.1772759). Confirmed on Crossref; full text read via [arXiv:0910.3349](https://arxiv.org/abs/0910.3349). Journal follow-up (record only): P. Li and A. C. König, "Theory and applications of b-bit minwise hashing," Commun. ACM, vol. 54, no. 8, pp. 101-109, Aug. 2011, DOI 10.1145/1978542.1978566.
*Found:* Stores only the lowest b bits of each min-hash with an unbiased estimator; b = 1 reduces storage by at least a factor of **21.3** at resemblance ≥ 0.5.
*Relation:* A way to shrink signatures if the number of edits grows; not available in Spark's MinHashLSH.

**L13. Li, Owen and Zhang 2012 (one permutation hashing).** P. Li, A. Owen, and C.-H. Zhang, "One permutation hashing," Advances in Neural Information Processing Systems 25 (NIPS 2012). No DOI. Confirmed on the [proceedings page](https://papers.nips.cc/paper/2012/hash/eaa32c96f620053cf442ad32258076b9-Abstract.html); [arXiv:1208.1259](https://arxiv.org/pdf/1208.1259) read.
*Found:* Standard minwise hashing needs e.g. k = 500 permutations; this uses one permutation split into k bins; empty bins are rare unless a set has few non-zeros relative to k.
*Relation:* The empty-bin caveat is exactly the short-text case (edit comments with few shingles), so this speed-up is risky for short items.
*Flags:* UNVERIFIED: page numbers.

**L14. Bawa, Condie and Ganesan 2005 (LSH forest).** M. Bawa, T. Condie, and P. Ganesan, "LSH forest: self-tuning indexes for similarity search," Proc. 14th Int. Conf. World Wide Web (WWW), 2005, p. 651 ff. DOI [10.1145/1060745.1060840](https://doi.org/10.1145/1060745.1060840). Confirmed on Crossref; abstract via [OpenAlex](https://api.openalex.org/works/doi:10.1145/1060745.1060840). Abstract-level.
*Found:* Removes the data-dependent parameters standard LSH needs hand-tuned.
*Relation:* Documents that fixed (bands, rows) settings are a known weakness; the project's fixed-parameter Spark join inherits it.
*Flags:* UNVERIFIED: end page (commonly cited as 651-660).

**L15. Das et al. 2007.** A. S. Das, M. Datar, A. Garg, and S. Rajaram, "Google news personalization: scalable online collaborative filtering," Proc. 16th Int. Conf. World Wide Web (WWW), 2007, pp. 271-280. DOI [10.1145/1242572.1242610](https://doi.org/10.1145/1242572.1242610). Confirmed on Crossref; abstract via [OpenAlex](https://api.openalex.org/works/doi:10.1145/1242572.1242610). Abstract-level.
*Found:* A production recommender combining MinHash clustering, PLSI and covisitation counts over a continually changing item set.
*Relation:* Evidence that MinHash scales over a continually changing item set, like an edit stream.
*Flags:* UNVERIFIED: that MinHash clustering was implemented on MapReduce.

**L16. Shrivastava and Li 2014.** A. Shrivastava and P. Li, "In defense of MinHash over SimHash," Proc. 17th Int. Conf. Artificial Intelligence and Statistics (AISTATS), PMLR vol. 33, pp. 886-894, 2014. Confirmed on [PMLR](https://proceedings.mlr.press/v33/shrivastava14.html). Abstract-level.
*Found:* For binary data, MinHash "virtually always outperforms SimHash"; uses the inequality S² ≤ R ≤ S/(2 − S) linking resemblance R and cosine S.
*Relation:* Supports choosing MinHash over SimHash when edits are binary shingle sets.

### The implementation the project runs

**L17. Apache Spark MLlib guide (official).** Apache Software Foundation, "Extracting, transforming and selecting features — Locality Sensitive Hashing," Apache Spark 4.3.0 MLlib Guide. [Section read](https://spark.apache.org/docs/latest/ml-features.html#locality-sensitive-hashing), accessed 2026-11-17.
*Found:* Defines an LSH family as (r1, r2, p1, p2)-sensitive. MinHash uses Jaccard distance on binary vectors; a vector with no non-zero entry cannot be transformed. `numHashTables` gives **OR-amplification**; each table's vector has dimension 1, and the guide says AND-amplification will come in future releases. `approxSimilarityJoin` returns pairs under a user threshold with a column giving the true distance of each returned pair. The guide links only to Wikipedia; the source comments cite Bohman-Cooper-Frieze 2000 (L3b) and, for BucketedRandomProjectionLSH, J. Wang, H. T. Shen, J. Song, and J. Ji, "Hashing for similarity search: A survey," [arXiv:1408.2927](https://arxiv.org/abs/1408.2927), 2014. Both classes are marked Since 2.1.0.
*Relation:* This is the code the project runs; empty-shingle edits must be dropped before hashing.
*Flags:* The Spark version the project runs was not checked against the 4.3.0 guide text. No Spark document states the default-parameter recall of MinHashLSH.

### Applications near the project and documented limits

**L18. Potthast and Stein 2008.** M. Potthast and B. Stein, "New issues in near-duplicate detection," in Data Analysis, Machine Learning and Applications (Studies in Classification, Data Analysis, and Knowledge Organization), Berlin, Heidelberg: Springer, 2008, pp. 601-609. DOI [10.1007/978-3-540-78246-9_71](https://doi.org/10.1007/978-3-540-78246-9_71). Confirmed on Crossref; [full text read](https://webis.de/downloads/publications/papers/potthast_2008c.pdf).
*Found:* Proposes the Wikipedia Revision Corpus (order of 6 million articles, 80 million revisions) as a near-duplicate benchmark that permits recall as well as precision measurement; evaluates fingerprint methods on 7 million document pairs; among fixed-size fingerprints shingling was best.
*Relation:* The closest prior use of Wikipedia revision text to evaluate shingling and LSH against a similarity threshold. It compares whole revisions, not edit diffs or comments.

**L19. Weissman et al. 2015.** S. Weissman, S. Ayhan, J. Bradley, and J. Lin, "Identifying duplicate and contradictory information in Wikipedia," Proc. 15th ACM/IEEE-CS Joint Conf. Digital Libraries (JCDL), 2015, pp. 57-60. DOI [10.1145/2756406.2756947](https://doi.org/10.1145/2756406.2756947). Confirmed on Crossref; full text read via [arXiv:1406.1143](https://arxiv.org/pdf/1406.1143).
*Found:* MapReduce MinHash over Wikipedia sentences, then clustering; manual inspection sorted clusters into six types. Parameters: K = 10 min-hashes per signature, M = 10 signatures per sentence, character shingles of length 12; sentences with fewer than **75** or more than 600 shingles discarded. A second verification pass was named but not implemented.
*Relation:* The nearest methodological match (MinHash on short Wikipedia text plus manual categorisation). They dropped very short texts, and the project's exact-Jaccard check is the step they left for future work.

**L20. Alshomary et al. 2019.** M. Alshomary, M. Völske, T. Licht, H. Wachsmuth, B. Stein, M. Hagen, and M. Potthast, "Wikipedia text reuse: within and without," in Advances in Information Retrieval (ECIR 2019), LNCS, Springer, 2019, pp. 747-754. DOI [10.1007/978-3-030-15712-8_49](https://doi.org/10.1007/978-3-030-15712-8_49). Confirmed on Crossref and [arXiv](https://arxiv.org/abs/1812.09221). Abstract-level.
*Found:* About 100 million reuse cases inside Wikipedia and 1.6 million outside.
*Relation:* Near-copy text is common inside Wikipedia, so similar-edit pairs are expected, not anomalies.
*Flags:* UNVERIFIED: LNCS volume (11437 recalled), and whether the candidate stage uses MinHash or LSH.

**L21. Flöck, Vrandečić and Simperl 2012.** Same paper as W1; listed here because the notes include it in the LSH core set as the argument for going beyond exact checksums.

**L22. Ekstrand and Riedl 2009.** M. D. Ekstrand and J. T. Riedl, "rv you're dumb: identifying discarded work in Wiki article history," Proc. 5th Int. Symp. Wikis and Open Collaboration (WikiSym), 2009, pp. 1-10 (article-numbered). DOI [10.1145/1641309.1641317](https://doi.org/10.1145/1641309.1641317). Confirmed on Crossref; abstract via [OpenAlex](https://api.openalex.org/works/doi:10.1145/1641309.1641317). Abstract-level.
*Found:* Detects when a revision discards the work of earlier revisions.
*Relation:* Revision-to-revision similarity used to find reverts that are not exact copies; not hashing-based.
*Flags:* UNVERIFIED: the similarity measure used.

**L23. Petrović, Osborne and Lavrenko 2010 (short-text streams).** S. Petrović, M. Osborne, and V. Lavrenko, "Streaming first story detection with application to Twitter," Proc. HLT-NAACL 2010, Los Angeles, ACL, pp. 181-189. Confirmed on the [ACL Anthology](https://aclanthology.org/N10-1021/); full text read.
*Found:* Pure LSH gave poor performance and high variance; adding an exact comparison against the 2000 most recent documents fixed it; run on 160 million tweets. Uses cosine/random-hyperplane LSH, not MinHash.
*Relation:* Evidence that LSH on short texts needs an exact check.

**L24. Xiao et al. 2008 (exact joins).** C. Xiao, W. Wang, X. Lin, and J. X. Yu, "Efficient similarity joins for near duplicate detection," Proc. 17th Int. Conf. World Wide Web (WWW), 2008, pp. 131-140. DOI 10.1145/1367497.1367516. Abstract via [OpenAlex](https://api.openalex.org/works/doi:10.1145/1367497.1367516). Abstract-level.
*Found:* Exact threshold joins by prefix filtering cut candidate sets, 2.6x-5x faster than prior algorithms.

**L25. Bayardo, Ma and Srikant 2007 (exact all-pairs).** R. J. Bayardo, Y. Ma, and R. Srikant, "Scaling up all pairs similarity search," Proc. 16th WWW, 2007, pp. 131-140. DOI 10.1145/1242572.1242591. Abstract via [OpenAlex](https://api.openalex.org/works/doi:10.1145/1242572.1242591). Abstract-level.
*Found:* Exact all-pairs above a threshold without approximation.
*Relation (L24, L25):* Verification of candidates is a separate cost that exact set-similarity joins try to cut.
*Flags:* The notes give the same page range, pp. 131-140, for both L24 and L25. Check both against the DOI records before citing; one may be a copying slip.

**Not verified and not listed.** Densified one-permutation hashing (Shrivastava and Li, 2014), and the variance formula s(1−s)/k for the MinHash estimator. The notes found no source that measures MinHash error as a function of text length for texts under about 20 tokens.

## Privacy: k-anonymity needs help, Laplace error is 1/epsilon, and Wikimedia already publishes with both

**What the literature establishes.** k-anonymity (1998-2002) requires every quasi-identifier combination to match at least k people, achieved by generalization and suppression. l-diversity (2006/2007) and t-closeness (2007) were introduced because k-anonymity does not stop disclosure of a sensitive attribute, and optimal k-anonymization is NP-hard (2004, 2005), so practical systems use greedy methods such as Mondrian (2006). The founding papers address microdata, one row per person; TruthLag publishes only grouped counts, so k-anonymity there means each published cell covers at least k distinct editors, and suppression is the only operation needed. Differential privacy (2006) bounds how much one person's data can change the output distribution; for a sensitivity-1 count the Laplace mechanism gives expected absolute error 1/epsilon regardless of data size, and privacy losses add across releases. Sensitivity 1 holds only if the protected unit is one edit; if the unit is one editor, contributions must be capped, which is why the Wikimedia release (P17) caps them. Three re-identification cases (search logs, movie ratings, location traces) show that removing names is not anonymization. The Wikimedia Foundation publishes pageview counts under differential privacy with threshold suppression on top of noise, while edit metadata is a permanent public record, so TruthLag's privacy analysis concerns what its derived tables add or make easier, not the secrecy of the edits. The notes verified one peer-reviewed study of profiling Wikipedia editors from edit metadata (P22) and found no verified study that links accounts to real identities from edit timestamps. No survey on the utility cost of k-anonymity was opened or verified.

### k-anonymity and its successors

**P1. Samarati and Sweeney 1998.** P. Samarati and L. Sweeney, "Protecting privacy when disclosing information: k-anonymity and its enforcement through generalization and suppression," Computer Science Laboratory, SRI International, Menlo Park, CA, Tech. Rep. SRI-CSL-98-04, 1998. No DOI. Confirmed on the [SRI report page](https://www.csl.sri.com/papers/sritr-98-04); full text read at the [EPIC copy](https://epic.org/wp-content/uploads/privacy/reidentification/Samarati_Sweeney_paper.pdf).
*Found:* Defines the k-anonymity requirement (Definition 2.2); introduces the term quasi-identifier; enforces k-anonymity with generalization and suppression; defines minimal generalization.
*Relation:* The group keys of the aggregate tables are the quasi-identifiers; a cell with fewer than k contributing editors is the case suppression removes.
*Flags:* Citation conflict; UNVERIFIED: any IEEE S&P 1998 version (see the trap list).

**P2. Samarati 2001.** P. Samarati, "Protecting respondents' identities in microdata release," IEEE Trans. Knowl. Data Eng., vol. 13, no. 6, pp. 1010-1027, Nov./Dec. 2001. DOI 10.1109/69.971193. Confirmed on [Crossref](https://api.crossref.org/works/10.1109/69.971193); abstract via [OpenAlex](https://api.openalex.org/works/https://doi.org/10.1109/69.971193). Abstract-level.
*Found:* Journal version of the model; generalization and suppression keep the released data truthful; gives an algorithm for a minimal generalization.
*Relation:* Suppression of small cells is the truthful-data option (published counts stay exact; some cells disappear), in contrast to noise addition.
*Flags:* UNVERIFIED: issue month. Crossref prints the title without the apostrophe.

**P3. Sweeney 2002.** L. Sweeney, "k-anonymity: A model for protecting privacy," Int. J. Uncertainty, Fuzziness and Knowledge-Based Systems, vol. 10, no. 5, pp. 557-570, Oct. 2002. DOI 10.1142/S0218488502001648. Confirmed on [Crossref](https://api.crossref.org/works/10.1142/S0218488502001648); abstract via [Semantic Scholar](https://api.semanticscholar.org/graph/v1/paper/DOI:10.1142/S0218488502001648?fields=title,abstract). Abstract-level.
*Found:* A release is k-anonymous if each person's information cannot be told apart from that of at least k−1 others; examines re-identification attacks that still work unless accompanying policies are followed.
*Relation:* The standard definition to quote for "k editors per published cell".
*Flags:* UNVERIFIED: whether this paper prints the 87% figure; cite P4 for that number.

**P4. Sweeney 2000.** L. Sweeney, "Simple demographics often identify people uniquely," Carnegie Mellon University, Pittsburgh, PA, Data Privacy Working Paper 3, 2000. No DOI. Confirmed on the [Data Privacy Lab page](https://dataprivacylab.org/projects/identifiability/).
*Found:* Using 1990 U.S. Census summary data, **87%** of the U.S. population (216 million of 248 million) was likely unique on 5-digit ZIP, gender and date of birth; about 53% on place, gender and date of birth; about 18% on county, gender and date of birth.
*Relation:* A few coarse attributes combined can single out a person; the analogue is hour by editor kind by wiki producing cells with one editor.

**P5. Machanavajjhala et al. 2007 / 2006 (l-diversity).** A. Machanavajjhala, D. Kifer, J. Gehrke, and M. Venkitasubramaniam, "l-diversity: Privacy beyond k-anonymity," ACM Trans. Knowl. Discov. Data, vol. 1, no. 1, Art. 3, Mar. 2007. DOI 10.1145/1217299.1217302. Conference version: A. Machanavajjhala, J. Gehrke, D. Kifer, and M. Venkitasubramaniam, same title, in Proc. 22nd Int. Conf. Data Engineering (ICDE), 2006, p. 24. DOI 10.1109/ICDE.2006.1. Confirmed on Crossref ([TKDD](https://api.crossref.org/works/10.1145/1217299.1217302), [ICDE](https://api.crossref.org/works/10.1109/ICDE.2006.1)); abstract via [OpenAlex](https://api.openalex.org/works/https://doi.org/10.1145/1217299.1217302). Abstract-level.
*Found:* Two attacks on k-anonymous data: homogeneity (a group has little diversity in the sensitive attribute) and background knowledge. Proposes l-diversity; as restated by P6, each equivalence class must contain at least l "well-represented" values of each sensitive attribute.
*Relation:* If "reverted or not" is the sensitive attribute, a k-anonymous group in which every edit was reverted reveals each member's outcome.
*Flags:* UNVERIFIED: the variant names "distinct", "entropy" and "recursive (c,l)". Author order differs between the two versions.

**P6. Li, Li and Venkatasubramanian 2007 (t-closeness).** N. Li, T. Li, and S. Venkatasubramanian, "t-closeness: Privacy beyond k-anonymity and l-diversity," in Proc. IEEE 23rd Int. Conf. Data Engineering (ICDE), Apr. 2007, pp. 106-115. DOI 10.1109/ICDE.2007.367856. Confirmed on [Crossref](https://api.crossref.org/works/10.1109/ICDE.2007.367856); abstract via [OpenAlex](https://api.openalex.org/works/https://doi.org/10.1109/ICDE.2007.367856). Abstract-level.
*Found:* Argues l-diversity is "neither necessary nor sufficient" to prevent attribute disclosure; requires the distribution of the sensitive attribute in every class to be within distance t (Earth Mover's Distance) of its distribution in the whole table.
*Relation:* A group whose revert rate is far from the overall revert rate leaks information about its members even when it is l-diverse.
*Flags:* UNVERIFIED: the names "skewness attack" and "similarity attack", and the conference city (Istanbul).

**P7. LeFevre, DeWitt and Ramakrishnan 2006 (Mondrian).** K. LeFevre, D. J. DeWitt, and R. Ramakrishnan, "Mondrian multidimensional k-anonymity," in Proc. 22nd Int. Conf. Data Engineering (ICDE), Apr. 2006, p. 25. DOI 10.1109/ICDE.2006.101. Confirmed on [Crossref](https://api.crossref.org/works/10.1109/ICDE.2006.101); abstract via [OpenAlex](https://api.openalex.org/works/https://doi.org/10.1109/ICDE.2006.101). Abstract-level.
*Found:* A multidimensional recoding model; optimal multidimensional anonymization is NP-hard; a simple greedy approximation often beats exhaustive optimal single-dimensional algorithms.
*Relation:* The alternative to suppressing small cells is to merge neighbouring cells until each holds k editors; Mondrian is the standard greedy way.
*Flags:* UNVERIFIED: city (Atlanta) and month.

**P8. Meyerson and Williams 2004.** A. Meyerson and R. Williams, "On the complexity of optimal k-anonymity," in Proc. 23rd ACM SIGMOD-SIGACT-SIGART Symp. Principles of Database Systems (PODS), Jun. 2004, pp. 223-228. DOI 10.1145/1055558.1055591. Confirmed on [Crossref](https://api.crossref.org/works/10.1145/1055558.1055591); abstract via [OpenAlex](https://api.openalex.org/works/https://doi.org/10.1145/1055558.1055591). Abstract-level.
*Found:* Two general versions of optimal k-anonymization are NP-hard, including the suppression version; gives an O(k log k)-approximation.
*Relation:* Justifies a simple rule (drop every cell below k) instead of a search for the minimum-loss suppression.
*Flags:* UNVERIFIED: city (Paris).

**P9. Bayardo and Agrawal 2005.** R. J. Bayardo and R. Agrawal, "Data privacy through optimal k-anonymization," in Proc. 21st Int. Conf. Data Engineering (ICDE), 2005, pp. 217-228. DOI 10.1109/ICDE.2005.42. Confirmed on [Crossref](https://api.crossref.org/works/10.1109/ICDE.2005.42); abstract via [OpenAlex](https://api.openalex.org/works/https://doi.org/10.1109/ICDE.2005.42). Abstract-level.
*Found:* Even simple restrictions of optimized k-anonymity are NP-hard; a search algorithm finds optimal k-anonymizations of real census data under two cost measures.
*Relation:* The source for scoring an anonymization by a cost measure, which is what "rows and edits suppressed at each k" reports.
*Flags:* UNVERIFIED: city (Tokyo) and month (April).

### Differential privacy

**P10. Dwork et al. 2006 (Laplace mechanism).** C. Dwork, F. McSherry, K. Nissim, and A. Smith, "Calibrating noise to sensitivity in private data analysis," in Theory of Cryptography (TCC 2006), Lecture Notes in Computer Science, vol. 3876. Berlin, Germany: Springer, 2006, pp. 265-284. DOI 10.1007/11681878_14. Confirmed on [Crossref](https://api.crossref.org/works/10.1007/11681878_14). Bibliographic record only.
*Found:* Second-hand: P12 (Section 3.7 notes) names it as the source of the Laplace mechanism, and P17 cites it as the basis for its epsilon-DP guarantee.
*Relation:* The primary citation for adding Laplace noise scaled to sensitivity/epsilon to each grouped count.
*Flags:* UNVERIFIED: LNCS volume 3876, and the paper's own wording of the definition.

**P11. Dwork 2006.** C. Dwork, "Differential privacy," in Automata, Languages and Programming (ICALP 2006), Part II, Lecture Notes in Computer Science, vol. 4052. Berlin, Germany: Springer, 2006, pp. 1-12. DOI 10.1007/11787006_1. Confirmed on [Crossref](https://api.crossref.org/works/10.1007/11787006_1). Bibliographic record only.
*Relation:* The citation for the term itself; use only as the naming citation.
*Flags:* UNVERIFIED: content, LNCS volume 4052 and "Part II".

**P12. Dwork and Roth 2014.** C. Dwork and A. Roth, "The algorithmic foundations of differential privacy," Foundations and Trends in Theoretical Computer Science, vol. 9, nos. 3-4, pp. 211-407, Aug. 2014. DOI 10.1561/0400000042. Confirmed on [Crossref](https://api.crossref.org/works/10.1561/0400000042); full text read at the [author PDF](https://www.cis.upenn.edu/~aaroth/Papers/privacybook.pdf).
*Found:* Definition 2.4 of (epsilon, delta)-differential privacy. Definitions 3.1 and 3.3 and Theorem 3.6: the Laplace mechanism adds Lap(sensitivity/epsilon) noise and is (epsilon, 0)-private. Example 3.1: a counting query has sensitivity 1, and the expected error is **1/epsilon**, "independent of the size of the database". Example 3.2: a histogram has sensitivity 1 as a whole. Theorem 3.16: basic composition, epsilons add.
*Relation:* The grouped edit and revert tables are histograms, so mean absolute error at each epsilon should be near 1/epsilon per cell; publishing several tables from the same data spends the sum of their epsilons.
*Flags:* Page-range conflict (see the trap list). UNVERIFIED: the exact form of the Theorem 3.8 tail bound. The notes' worked values (epsilon 0.1 gives 10, and so on) and relative-error examples are arithmetic, not from the source.

**P13. Dwork et al. 2010 (continual observation).** C. Dwork, M. Naor, T. Pitassi, and G. N. Rothblum, "Differential privacy under continual observation," in Proc. 42nd ACM Symp. Theory of Computing (STOC), Jun. 2010, pp. 715-724. DOI 10.1145/1806689.1806787. Confirmed on [Crossref](https://api.crossref.org/works/10.1145/1806689.1806787); abstract via [OpenAlex](https://api.openalex.org/works/https://doi.org/10.1145/1806689.1806787). Abstract-level.
*Found:* Earlier work assumed a static dataset and one-shot computation; starts the study of privacy under continual observation and identifies the private running counter as the core problem.
*Relation:* A live count republished every window is a continual-observation release; fresh Laplace noise per release makes the privacy loss grow with the number of releases.
*Flags:* UNVERIFIED: the error bound (order log^1.5 T / epsilon), and the city (Cambridge, MA).

**P14. Chan, Shi and Song 2011.** T.-H. H. Chan, E. Shi, and D. Song, "Private and continual release of statistics," ACM Trans. Inf. Syst. Secur., vol. 14, no. 3, Art. 26, pp. 1-24, Nov. 2011. DOI 10.1145/2043621.2043626. Confirmed on [Crossref](https://api.crossref.org/works/10.1145/2043621.2043626); abstract via [OpenAlex](https://api.openalex.org/works/https://doi.org/10.1145/2043621.2043626). Abstract-level.
*Found:* For a stream of 0s and 1s, outputs an approximate running count at every step under differential privacy with error polylogarithmic in the number of steps.
*Relation:* The direct reference for a private running revert count on a stream; the project's per-table Laplace noise is the one-shot case.
*Flags:* UNVERIFIED: article number 26, and the name "binary mechanism".

**P15. Erlingsson, Pihur and Korolova 2014 (optional).** Ú. Erlingsson, V. Pihur, and A. Korolova, "RAPPOR: Randomized aggregatable privacy-preserving ordinal response," in Proc. 2014 ACM SIGSAC Conf. Computer and Communications Security (CCS), Nov. 2014, pp. 1054-1067. DOI 10.1145/2660267.2660348. Confirmed on [Crossref](https://api.crossref.org/works/10.1145/2660267.2660348). Bibliographic record only.
*Relation:* Contrast case only. TruthLag adds noise centrally after aggregation; this adds it before collection.
*Flags:* UNVERIFIED: content, full subtitle (Crossref stores only "RAPPOR") and city (Scottsdale, AZ).

### Re-identification failures

**P16. Narayanan and Shmatikov 2008.** A. Narayanan and V. Shmatikov, "Robust de-anonymization of large sparse datasets," in Proc. 2008 IEEE Symp. Security and Privacy (S&P), May 2008, pp. 111-125. DOI 10.1109/SP.2008.33. Confirmed on [Crossref](https://api.crossref.org/works/10.1109/SP.2008.33); preprint at [arXiv cs/0610105](https://arxiv.org/abs/cs/0610105). Abstract-level.
*Found:* Statistical de-anonymization attacks on sparse microdata that tolerate errors in background knowledge; applied to the Netflix Prize dataset (about 500,000 subscribers), using the Internet Movie Database as background.
*Relation:* An editor's row-level history is the same kind of sparse high-dimensional record; this is the argument for publishing aggregates only.
*Flags:* UNVERIFIED: the figure that 8 ratings with dates within 14 days identify 99% of records, and the city (Oakland, CA).

**P17a. Barbaro and Zeller 2006 (AOL; PARTLY VERIFIED).** M. Barbaro and T. Zeller Jr., "A face is exposed for AOL searcher no. 4417749," The New York Times, Aug. 9, 2006. URL https://www.nytimes.com/2006/08/09/technology/09aol.html. The page could not be opened; headline, byline and date were confirmed only through search-result excerpts ([Searchblog](https://battellemedia.com/archives/2006/08/nyt_finds_an_aol_searcher)).
*Found (from the excerpt):* AOL released about 20 million search queries with users replaced by numbers; reporters identified the person behind one number from that user's queries.
*Relation:* A pseudonymous id attached to a detailed activity log does not prevent identification; aggregate counts carry no per-user log.
*Flags:* Treat all details as secondary until someone opens the article. UNVERIFIED: section and print page (commonly p. A1), and the count of about 650,000-658,000 users.

**P18. de Montjoye et al. 2013.** Y.-A. de Montjoye, C. A. Hidalgo, M. Verleysen, and V. D. Blondel, "Unique in the crowd: The privacy bounds of human mobility," Scientific Reports, vol. 3, Art. no. 1376, Mar. 2013. DOI 10.1038/srep01376. Confirmed on [Crossref](https://api.crossref.org/works/10.1038/srep01376) and [PubMed Central](https://pmc.ncbi.nlm.nih.gov/articles/PMC3607247/).
*Found:* 15 months of mobility records for about 1.5 million users; **four** spatio-temporal points uniquely identify about **95%** of individuals; uniqueness falls roughly as the 1/10 power of the resolution.
*Relation:* Coarsening hour to day does not by itself make small cells safe; the count of people per cell must be checked.

### Wikimedia practice and policy

**P17. Adeleye et al. 2023.** T. Adeleye, S. Berghel, D. Desfontaines, M. Hay, I. Johnson, C. Lemoisson, A. Machanavajjhala, T. Magerlein, G. Modena, D. Pujol, D. Simmons-Marengo, and H. Triedman, "Publishing Wikipedia usage data with strong privacy guarantees," arXiv:2308.16298, Aug. 2023 (v3, Jul. 2025); presented at Theory and Practice of Differential Privacy (TPDP) 2023. DOI 10.48550/arXiv.2308.16298. Confirmed on [arXiv](https://arxiv.org/abs/2308.16298); full text read ([PDF v3](https://arxiv.org/pdf/2308.16298)).
*Found:* Daily pageview counts per page, project and country, released from June 2023, built with Tumult Analytics. Zero-concentrated DP with **rho = 0.0151** for current data and pure **epsilon = 1** for historical data. Current data caps each device at 10 pageviews per day, adds Gaussian noise, and suppresses noisy counts below 90; historical data uses Laplace noise with thresholds 450 and 3500. Utility metrics: relative error, drop rate and spurious rate; for current data over 95% of counts have relative error below 50%.
*Relation:* The closest published precedent. It combines the two tools TruthLag uses (noise plus threshold suppression), reports error with drop and spurious rates, and uses epsilon = 1 as a reference value for count data.
*Flags:* The Tumult Analytics page cited inside the paper was not opened.

**P19. Wikimedia differential privacy pages.** Wikimedia Foundation, "Differential privacy," Meta-Wiki (last edited 29 Oct. 2024; accessed 17 Nov. 2026), with subpage "Differential privacy/Completed/Geoeditors/Feasibility report" (last edited 29 Aug. 2023). Confirmed on [Meta-Wiki](https://meta.wikimedia.org/wiki/Differential_privacy) and the [feasibility report](https://meta.wikimedia.org/wiki/Differential_privacy/Completed/Geoeditors/Feasibility_report).
*Found:* Lists the Foundation's differentially private releases, including Geoeditors (active editors by project, country and month, in buckets 1-4, 5-99 and 100+ edits). The report frames the release as a histogram query with Laplace noise of scale 1/epsilon and names a linkage risk: joining the release with public edit history could reveal an editor's country.
*Relation:* An official Wikimedia example of DP applied to editor counts, with the same structure as TruthLag's grouped counts and an explicit statement of the join-with-public-history risk.
*Flags:* UNVERIFIED: the epsilon and release threshold actually used for Geoeditors.

**P20. Wikimedia Privacy Policy and Data Retention Guidelines.** Wikimedia Foundation, "Privacy Policy," Wikimedia Foundation Governance Wiki (version approved 3 Sep. 2025, effective 6 Oct. 2025; accessed 17 Nov. 2026), with "Data Retention Guidelines" (last edited 20 Feb. 2026). Confirmed on the [Privacy Policy](https://foundation.wikimedia.org/wiki/Policy:Privacy_policy) and the [guidelines](https://foundation.wikimedia.org/wiki/Legal:Data_retention_guidelines).
*Found:* Edits are a permanent public record showing the account or temporary-account name and timestamp. Non-public personal data (IP address, user agent) is deleted, aggregated or de-identified after at most **90 days**. The guidelines define "aggregated" with the example of reporting "between 1 and 10 editors".
*Relation:* The input stream is public by policy; the Foundation's own "1 to 10 editors" range is a small-count suppression rule of the same kind.

**P21. Temporary accounts and IP access policy.** The same project and Updates pages as W25 and the Phabricator task in W26, plus "Wikimedia Access to Temporary Account IP Addresses Policy" (last edited 1 Apr. 2026), confirmed on the [access policy page](https://foundation.wikimedia.org/wiki/Policy:Wikimedia_Access_to_Temporary_Account_IP_Addresses_Policy).
*Found:* IP addresses of temporary accounts are visible to stewards, staff and local CheckUsers automatically, to administrators by opting in, and to other users only on request with an account at least 6 months old and at least 300 local edits; every reveal is logged; IP data is kept 90 days.
*Relation:* Explains the "temporary account" editor kind in the stream and why its definition changes by wiki and date; a temporary account is a pseudonym, so cells with few temporary accounts still need the k check.
*Flags:* A community newspaper ([Signpost, 10 Nov. 2025](https://signpost.news/2025-11-10/News_and_notes)) says more than one thousand other wikis had the feature before English Wikipedia; secondary source.

**P22. Rizoiu et al. 2016.** M.-A. Rizoiu, L. Xie, T. Caetano, and M. Cebrian, "Evolution of privacy loss in Wikipedia," in Proc. 9th ACM Int. Conf. Web Search and Data Mining (WSDM), Feb. 2016, pp. 215-224. DOI 10.1145/2835776.2835798. Confirmed on [Crossref](https://api.crossref.org/works/10.1145/2835776.2835798); abstract at [arXiv 1512.03523](https://arxiv.org/abs/1512.03523). Abstract-level.
*Found:* 13 years of edit history, **188,805,088** edits; using only the number of edits per broad topic category per time period, standard classifiers predicted undisclosed gender, religion and education; accuracy rose over time, including for users who had stopped editing.
*Relation:* Per-editor aggregate edit counts are themselves sensitive, which supports publishing only cells that cover many editors and never per-editor rows.
*Flags:* UNVERIFIED: city (San Francisco).

**P23. Ganta, Kasiviswanathan and Smith 2008.** S. R. Ganta, S. P. Kasiviswanathan, and A. Smith, "Composition attacks and auxiliary information in data privacy," in Proc. 14th ACM SIGKDD Int. Conf. Knowledge Discovery and Data Mining (KDD), Aug. 2008, pp. 265-273. DOI 10.1145/1401890.1401926. Confirmed on [Crossref](https://api.crossref.org/works/10.1145/1401890.1401926); abstract via [Semantic Scholar](https://api.semanticscholar.org/graph/v1/paper/DOI:10.1145/1401890.1401926?fields=title,abstract). Abstract-level.
*Found:* An adversary combines independent anonymized releases about overlapping populations; a simple composition attack breaches k-anonymity and several variants in practice; differential privacy provably resists composition attacks.
*Relation:* The project publishes several tables over the same edits; each may be k-anonymous alone and still leak when differenced, whereas the DP versions have a known total cost.
*Flags:* UNVERIFIED: city (Las Vegas).

## Corrections to the reference list in report_draft.md: all 23 entries exist, most lack pages and DOIs

The notes re-verified every entry in the References section of `docs/final/report_draft.md` (the list runs from line 334 to line 356, slightly past the 330-350 range). All 23 exist and are correctly attributed. No entry names a wrong paper. The corrections are additions, with four items the owner must decide. The draft list has no entries yet for the privacy sources, the Spark and Databricks documentation, the textbook, or the Wikimedia documentation pages listed in this guide.

| Draft entry | Status | Correction or addition the notes found | Guide ID |
|---|---|---|---|
| [10] Croushore and Stark, J. Econometrics 105(1), 2001 | Correct | Add pp. 111-130, Nov. 2001, DOI 10.1016/S0304-4076(01)00072-0. | D20 |
| [11] Aruoba, JMCB 40(2-3), 2008 | Correct | Add pp. 319-340, Mar. 2008, DOI 10.1111/j.1538-4616.2008.00115.x. | D21 |
| [12] Höhle and an der Heiden, Biometrics 70(4), 2014 | Correct | Add pp. 993-1002, Dec. 2014, DOI 10.1111/biom.12194. | D17 |
| [15] Priedhorsky et al., GROUP 2007 | Correct | Six authors (Priedhorsky, Chen, Lam, Panciera, Terveen, Riedl); pp. 259-268; DOI 10.1145/1316624.1316663. End page 268 is not on the Crossref record. | W9 |
| [16] Kumar, West, Leskovec, WWW 2016 | Correct, title truncated | Full title adds the subtitle "Impact, Characteristics, and Detection of Wikipedia Hoaxes"; pp. 591-602; DOI 10.1145/2872427.2883085. | W12 |
| [17] Geiger and Halfaker, "OpenSym 2013" | Correct, venue label to fix | Add the subtitle "without bots, what happens to Wikipedia's quality control processes?"; pp. 1-6; DOI 10.1145/2491055.2491061. The paper's own header says "WikiSym 2013, Aug 05-07, 2013, Hong Kong"; the ACM proceedings title is "Proceedings of the 9th International Symposium on Open Collaboration". Use "WikiSym '13" or the full proceedings title, not "OpenSym 2013". | W11 |
| [18] Flöck, Vrandečić, Simperl, HT 2012 | Correct, title truncated | Full title "Revisiting reverts: accurate revert detection in Wikipedia"; Proc. 23rd ACM Conf. Hypertext and Social Media (HT '12), pp. 3-12; DOI 10.1145/2309996.2310000 (not ...2310038). | W1 |
| [19] Trokhymovych et al., KDD 2023 | Correct | Five authors (Trokhymovych, Aslam, Chou, Baeza-Yates, Saez-Trumper); KDD '23, pp. 4981-4990; DOI 10.1145/3580305.3599823. | W19 |
| [20] Akidau et al., PVLDB 8(12), 2015 | Correct, title truncated | Add the full subtitle; pp. 1792-1803; DOI 10.14778/2824032.2824076; eleven authors. | S20 |
| [21] Golab and Johnson, CIDR 2011 | Correct | 5th Biennial Conference on Innovative Data Systems Research, Asilomar, CA, Jan. 9-12, 2011; no DOI. Page range UNVERIFIED (commonly cited as pp. 114-122); the PDF is 9 pages. | S26 |
| [22] Hellerstein, Haas, Wang, SIGMOD 1997 | Correct | Add pp. 171-182; DOI 10.1145/253260.253291. | S29 |
| [23] Kimball and Ross, 3rd ed., Wiley 2013 | Correct | Indianapolis, IN: Wiley, July 2013; ISBN 978-1-118-53080-1; 608 pp. | S28 |
| [24] Snodgrass, Morgan Kaufmann, "2000" | Correct, year to decide | The author's page gives the publication date as July 1999; 2000 is the usual citation year. Which year the title page prints is UNVERIFIED. ISBN 1-55860-436-7. | S27 |
| [25] Flajolet, Fusy, Gandouet, Meunier, AofA 2007 | Correct | Pages 127-146 (the paper's own running head), DMTCS Proceedings vol. AH; DOI 10.46298/dmtcs.3545. | S5 |
| Armbrust et al., Delta Lake, PVLDB 13(12), 2020 | Correct | Add pp. 3411-3424; DOI 10.14778/3415478.3415560; 21 authors. | S23 |
| Armbrust et al., Structured Streaming, SIGMOD 2018 | Correct | Add pp. 601-613; DOI 10.1145/3183713.3190664; 9 authors. | S16 |
| Flajolet and Martin, JCSS 31(2), 1985 | Correct | Add pp. 182-209; DOI 10.1016/0022-0000(85)90041-8. | S4 |
| Bloom, CACM 13(7), 1970 | Correct | Add pp. 422-426; DOI 10.1145/362686.362692. | S2 |
| Datar, Gionis, Indyk, Motwani, SIAM J. Computing 31(6), 2002 | Correct | Add pp. 1794-1813; DOI 10.1137/S0097539701398363. | S8 |
| Alon, Matias, Szegedy, STOC 1996 | Correct | Add pp. 20-29; DOI 10.1145/237814.237823. A journal version also exists (JCSS 58(1), 1999, pp. 137-147, DOI 10.1006/jcss.1997.1545); cite one consistently. | S7 |
| Vitter, ACM TOMS 11(1), 1985 | Correct | Add pp. 37-57; DOI 10.1145/3147.3165. | S1 |
| Broder, SEQUENCES 1997 | Correct | Proc. Compression and Complexity of SEQUENCES 1997, IEEE Computer Society, pp. 21-29; DOI 10.1109/SEQUEN.1997.666900. Cite as 1997; printed proceedings year UNVERIFIED. | L1 |
| Indyk and Motwani, STOC 1998 | Correct | Proc. 30th ACM STOC, pp. 604-613; DOI 10.1145/276698.276876. | L4 |

## Citation traps: where a plausible-looking citation is wrong or contested

These are the places where a correct-looking entry would be wrong, or where two records disagree. The team should settle each before the IEEE list is final.

**Wrong or misleading DOIs.** Flöck et al. 2012 is DOI 10.1145/2309996.2310000; the similar DOI 10.1145/2309996.2310038 is a different paper in the same proceedings ([Crossref](https://api.crossref.org/works/10.1145/2309996.2310000)). Lawless 1994 is registered as 10.2307/3315826.n1; the DOI 10.2307/3315826 without ".n1" is a different article in the same issue (R. D. Routledge, pp. 103-110), so use the ".n1" form or cite without a DOI ([Crossref](https://api.crossref.org/works/10.2307/3315826.n1)). Several sources have no DOI at all and should not be given one: Joulani et al. 2013 (PMLR), Kafka (NetDB 2011), RDDs (NSDI 2012), Flink (IEEE Data Engineering Bulletin), Lakehouse (CIDR 2021), Golab and Johnson (CIDR 2011), Gionis et al. (VLDB 1999), one permutation hashing (NIPS 2012), and the Samarati-Sweeney and Sweeney technical reports.

**Disputed or incomplete page ranges.** HyperLogLog's pages are 127-146 per the paper's own running head; some secondary citations give 137-156 ([PDF](https://algo.inria.fr/flajolet/Publications/FlFuGaMe07.pdf)). Dwork and Roth 2014: Crossref gives pages 211-487, the commonly cited range is 211-407; which is right is UNVERIFIED, so check the publisher page ([Crossref](https://api.crossref.org/works/10.1561/0400000042)). Golab and Johnson's proceedings range (commonly pp. 114-122) and Kafka's pages (commonly pp. 1-7) are UNVERIFIED. Priedhorsky et al.'s end page 268 is not on the Crossref record. Bawa et al. 2005 has only a start page (651) on Crossref and OpenAlex. Flink's end page 38 is UNVERIFIED. The notes give pp. 131-140 for both Xiao et al. 2008 and Bayardo et al. 2007; check both. Geiger and Halfaker 2013 (pp. 1-6), West et al.'s STiki demo (pp. 1-2) and Ekstrand and Riedl 2009 (pp. 1-10) are article-numbered ACM papers whose Crossref page field restarts at 1; the article numbers are UNVERIFIED.

**MD5 versus SHA-1.** The early revert papers (Priedhorsky et al., Yasseri et al., and the state of the art that Flöck et al. describe) detect identity reverts with MD5 checksums; the MediaWiki History dataset exposes a SHA-1 field (`revision_text_sha1`). Both are exact-content checksums, so the definitions are equivalent in practice, but "SHA-1" must not be attributed to those papers. The Research:Revert page itself says MD5 in its text while its sample code uses the SHA-1 field ([Research:Revert](https://meta.wikimedia.org/wiki/Research:Revert)).

**Spark MinHashLSH is OR-amplification, not bands and rows.** The Spark guide states that `numHashTables` gives OR-amplification, each table's vector has dimension 1, and AND-amplification is planned for future releases ([Spark guide](https://spark.apache.org/docs/latest/ml-features.html#locality-sensitive-hashing)). With one row per table, the candidate probability for a pair with Jaccard similarity s and L tables is 1 − (1 − s)^L, the Andoni-Indyk formula with k = 1. That curve is concave, not S-shaped: L = 5 gives 0.97 at s = 0.5 and also 0.41 at s = 0.1. Those two values were computed in the notes from the formula and are not from a source. The textbook's b = 20, r = 5 S-curve therefore does not describe what Spark does; selectivity comes from the exact-distance threshold in the join. The join's distance column is the exact Jaccard distance on the input vectors, so returned pairs have no false positives relative to the threshold on those vectors, but false negatives remain, and if the vectors come from HashingTF, hash collisions between shingles can distort the distance.

**Medallion architecture has no founding paper.** Neither the Delta Lake paper nor the Lakehouse paper contains "bronze", "medallion" or "gold"; "silver" appears in the Lakehouse paper only in a reference title ([Lakehouse PDF](https://www.cidrdb.org/cidr2021/papers/cidr2021_paper17.pdf)). The Databricks page calls it a data design pattern and gives no origin or academic citation ([Databricks](https://docs.databricks.com/aws/en/lakehouse/medallion)). Say plainly that it is a Databricks naming convention, cite S25 for the layer definitions and S23/S24 for the storage mechanisms. The notes searched no further than those two papers and the documentation page.

**Venue names, years and editions.** Geiger and Halfaker 2013 is WikiSym '13 or "Proc. 9th Int. Symp. Open Collaboration", not "OpenSym 2013". Geiger and Halfaker 2017: Crossref gives vol. 1, no. CSCW with issue date 6 Dec. 2017, while the paper's own reference format gives "1, 2, Article 49 (November 2017)". Snodgrass: published July 1999 per the author's page, usually cited as 2000. Broder's resemblance paper: the conference was held in 1997, Crossref has no issue date, OpenAlex lists 2002 (the IEEE Xplore load date), and it is often cited as 1998; cite as 1997. Metwally et al.: Crossref lists the online date as 2004, the volume is ICDT 2005. Potthast et al. 2008 (ECIR): the year is not in the Crossref record. AMS has a STOC 1996 version and a JCSS 1999 version; Broder et al.'s min-wise paper has a STOC 1998 extended abstract and a JCSS 2000 journal version; l-diversity has an ICDE 2006 version and a TKDD 2007 version. Pick one of each pair and cite it consistently.

**Author lists and orders.** l-diversity: the TKDD order is Machanavajjhala, Kifer, Gehrke, Venkitasubramaniam; the ICDE order is Machanavajjhala, Gehrke, Kifer, Venkitasubramaniam. Flink: the PDF's first page prints Carbone, Ewen, Haridi, Katsifodimos, Markl, Tzoumas in a three-column layout, while the commonly cited order is Carbone, Katsifodimos, Ewen, Markl, Haridi, Tzoumas; which the Bulletin's table of contents uses is UNVERIFIED. RDDs: the USENIX page spells the sixth author "McCauly", the paper "McCauley". Souza et al. 2018: OpenAlex spells the second author "Tiago Pinho da Silva".

**Crossref titles that are truncated or altered.** Do not copy these from Crossref without the subtitle: MillWheel (stored as "MillWheel"), Cypher ("Cypher"), RAPPOR ("RAPPOR"), Indyk-Motwani ("Approximate nearest neighbors"), Gomes et al. 2019 ("Machine learning for streaming data"). West et al.'s EUROSEC title carries a trailing "?" on Crossref, and Samarati 2001 is printed without its apostrophe. The MillWheel, Cypher and RAPPOR subtitles in this guide are from recall.

**The 1998 k-anonymity citation.** The Data Privacy Lab page lists a 1998 paper by Samarati and Sweeney as an IEEE S&P paper; SRI's own record gives the technical report SRI-CSL-98-04, and a second SRI listing attaches the same report number to the title "Generalizing Data to Provide Anonymity when Disclosing Information" (the PODS 1998 abstract). Cite the SRI record ([SRI](https://www.csl.sri.com/papers/sritr-98-04)). Any IEEE S&P 1998 version is UNVERIFIED.

**Figures that are easy to attribute to the wrong source.** The 87% uniqueness figure belongs to Sweeney's 2000 working paper (P4), not confirmed in the 2002 journal paper (P3). The 94% identity-revert share is reported by Priedhorsky et al. and Research:Revert as coming from Kittur et al.; it was not read in Kittur et al. The 12% "more full reverts" figure for Flöck et al. comes from the first author's dissertation and Research:Revert, not from the HT paper. The 6%, 9% and 11% figures for Kiesel et al. come from Research:Revert. The banding formula and the b = 20, r = 5 example come from the MMDS slide deck, not from Broder. Spark's guide cites Wikipedia, not Broder, Indyk-Motwani or Datar et al. The shingle-size advice k = 5 / k = 10 is for character shingles. Henzinger's precision figures are for web pages. The median time-to-revert figures of W8, W9 and W11 use different data, units and populations. Sumi et al. report about 24k controversial articles (November 2009 dump) and Yasseri et al. about 12k (January 2010 dump). Online aggregation's error is sampling error, not label-delay error. The English Wikipedia temporary-accounts date (4 November 2025) is on Phabricator and the English Wikipedia project page, not on the official MediaWiki.org pages. In the privacy notes, S17 (Adeleye et al.) and S17a (the New York Times article) are separate sources; this guide numbers them P17 and P17a.

## Everything the notes mark UNVERIFIED or [RECALL], by source

Nothing in these tables is confirmed. UNVERIFIED means the notes could not confirm the item on an opened page; [RECALL] means it is a standard result stated from memory without the text open. An item leaves this register only when a team member opens the source and checks it.

### Delayed labels

| ID | Status | Item |
|---|---|---|
| D3 Marrs et al. 2010 | UNVERIFIED | LNCS volume (believed 6291); conference name KSEM 2010; abstract and findings; whether it coined "verification latency". |
| (term) | UNVERIFIED | Origin of the term "verification latency". |
| D4 Plasse and Adams 2016 | UNVERIFIED | Category names of the taxonomy. |
| D7 Grzenda et al. 2020 | UNVERIFIED | Data sets and delay lengths used. |
| D8 Gomes et al. 2019 | UNVERIFIED | That the body has a dedicated discussion of delayed labels. |
| D9 Gomes et al. 2022 | UNVERIFIED | Article number within vol. 55 no. 4. |
| D10 Gama et al. 2014 | UNVERIFIED | Article number (commonly 44); what the body says about delayed feedback. |
| D12 Chapelle 2014 | UNVERIFIED | Share of conversions arriving within given waits; exponential form of the delay model. |
| D15a Mesterharm 2005 | UNVERIFIED | Host conference (believed ALT 2005); LNCS volume; findings. |
| D15b Weinberger and Ordentlich 2002 | UNVERIFIED | Findings. |
| D19 companion (Brookmeyer and Damiano 1989) | Not read | Findings. |
| D20 Croushore and Stark 2001 | UNVERIFIED | That the journal text matches the working-paper abstract. |
| Yoshikawa and Imai (arXiv:1802.00255) | UNVERIFIED | Title and authors; do not cite. |
| 2009 Signpost vandalism study | Not opened | 100 random articles; median time to correction about four minutes. |
| 2026 Phabricator "time-to-live" tasks | Not opened | Proposed median metric for reverted edits with a 7-day window. |
| Body-level facts | Not read | Bodies of D3, D4, D7, D8, D10, and full texts of D16-D19. |

### Wikipedia reverts

| ID | Status | Item |
|---|---|---|
| W1 Flöck et al. 2012 | UNVERIFIED | User-study sample size and exact accuracy figures in the HT paper. |
| W3 MediaWiki history | UNVERIFIED | Exact algorithm (window, SHA-1 comparison scope, self-reverts) behind the identity-revert fields. |
| W5 / W29 Kiesel et al. 2017 | Second-hand | 6% pseudo reverts, 9% self-reverts, 11% in edit wars; paper not opened; relevance to text similarity. |
| W6 mwreverts | UNVERIFIED | Version number and release year. |
| W9 Priedhorsky et al. 2007 | UNVERIFIED | Conference location; end page 268 not on Crossref. |
| W10 Geiger and Ribes 2010 | UNVERIFIED | Conference location. |
| W11 Geiger and Halfaker 2013 | UNVERIFIED | Article number; which tool class the "within one minute" statement belongs to (the two notes differ). |
| W12 Kumar et al. 2016 | UNVERIFIED | Conference location. |
| W13 Kittur et al. 2007 | UNVERIFIED | Conference location; any time-to-revert figure; "Revert Graph" clustering; data year; the 94% figure is second-hand. |
| W14 Potthast et al. 2008 | UNVERIFIED | LNCS volume (commonly 4956); year 2008. |
| W15 West et al. 2010 (EUROSEC) | UNVERIFIED | Workshop location. |
| W16 West et al. 2010 (STiki) | UNVERIFIED | Article number; symposium location. |
| W17 Adler et al. 2011 | UNVERIFIED | Exact AUC figures on the PAN 2010 corpus. |
| W19 Trokhymovych et al. 2023 | UNVERIFIED | Headline AUC and accuracy figures; conference location. |
| W21 Sumi et al. 2011 | UNVERIFIED | Conference location. |
| W22 Yasseri et al. 2012 | UNVERIFIED | Which of the sample sizes 223k and 233k is the typo. |
| W25 Temporary accounts | UNVERIFIED | Date the rollout finished on all wikis. |
| W26 English Wikipedia deployment | UNVERIFIED | 12 November 2025 for Spanish Wikipedia, Commons and Wikidata. |
| W27 Halfaker et al. 2013 | UNVERIFIED | Print month (May 2013). |
| W28 Halfaker et al. 2011 | UNVERIFIED | Symposium location. |
| All conference cities in this area | From memory | Marked UNVERIFIED wherever not seen on an opened page. |

### Streaming algorithms, stream processing and lakehouse systems

| ID | Status | Item |
|---|---|---|
| S1 Vitter 1985 | [RECALL] | Algorithm R description and its O(N) cost. |
| S2 Bloom 1970 | [RECALL] | Both content statements (false positives for space, no false negatives; the second method is the Bloom filter). |
| S3 Broder and Mitzenmacher 2004 | [RECALL] | False-positive formula, optimal k, 0.6185^(m/n); counting Bloom filters. |
| S4 Flajolet and Martin 1985 | [RECALL] | Standard error 0.78/sqrt(m); constant phi ≈ 0.77351. |
| S6 Heule et al. 2013 | UNVERIFIED | That Spark's `approx_count_distinct` implements HLL++. |
| S7 Alon et al. | [RECALL] | F_2 "tug-of-war" estimator and its counter bound. |
| S8 Datar et al. 2002 | [RECALL] | Error and space bounds, lower bound, extension to sums. |
| S9 Cormode and Muthukrishnan 2005 | [RECALL] | Dimensions, error guarantee, query types, linearity. |
| S10 Misra and Gries 1982 | [RECALL] | k − 1 counters, n/k threshold and undercount bound. |
| S11 Metwally et al. 2005 | [RECALL] / UNVERIFIED | Space-Saving description; LNCS volume 3363. |
| S12 Leskovec et al. 2020 | [RECALL] / UNVERIFIED | Chapter 4 section list; section numbers in chapters 3 and 4. |
| S13 Kreps et al. 2011 | UNVERIFIED | Page numbers (commonly 1-7); "6th" ordinal. |
| S14 Zaharia et al. 2012 | UNVERIFIED | Spelling of the sixth author. |
| S18 Carbone et al. 2015 | UNVERIFIED | Author order; end page 38; volume and issue. |
| S19 Akidau et al. 2013 | [RECALL] / UNVERIFIED | Low watermark and exactly-once statements; subtitle; that reference [2] in the Dataflow and Structured Streaming papers is MillWheel. |
| S20 Akidau et al. 2015 | UNVERIFIED | Whether the 2015 paper names "allowed lateness". |
| S22 Marz and Warren 2015 | [RECALL] / UNVERIFIED | The three layer names. |
| S24 Armbrust et al. 2021 | UNVERIFIED | "11th" ordinal. |
| S25 Databricks | Not established | First public use of the term "medallion". |
| S26 Golab and Johnson 2011 | UNVERIFIED | Proceedings page range (commonly 114-122). |
| S27 Snodgrass | [RECALL] / UNVERIFIED | Valid time and transaction time content; SQL patterns; the year on the title page; chapter pointers. |
| S28 Kimball and Ross 2013 | [RECALL] / UNVERIFIED | Slowly changing dimensions and late-arriving facts; chapter numbers. |
| S29 Hellerstein et al. 1997 | [RECALL] | Running estimate with confidence interval; random-order requirement. |
| S30 Begoli et al. 2019 | [RECALL] | Content. |
| S31 Angles et al. 2017 | [RECALL] / UNVERIFIED | Content; article number 68. |
| S32 Francis et al. 2018 | [RECALL] | Content; subtitle. |
| S34 Schultz et al. 2019 | [RECALL] | Content. |

### MinHash and LSH

| ID | Status | Item |
|---|---|---|
| L1 Broder 1997 | UNVERIFIED | Printed proceedings year; city; estimator unbiased with variance shrinking as 1/(sample size). |
| L2 Broder et al. 1997 | UNVERIFIED | About 30 million AltaVista pages; clustering threshold; "super-shingles". |
| L3 Broder et al. 2000 | UNVERIFIED | Exact and approximate families; lower bounds on family size. |
| L4 Indyk and Motwani 1998 | UNVERIFIED | Any specific theorem statement. |
| L5 Gionis et al. 1999 | UNVERIFIED | PDF URL; city (Edinburgh); publisher (Morgan Kaufmann); page range rests on OpenAlex only. |
| L10 Manku et al. 2007 | UNVERIFIED | 64-bit fingerprints, k = 3, 8 billion pages. |
| L11 MMDS chapter 3 | UNVERIFIED | Section numbers. |
| L13 Li et al. 2012 | UNVERIFIED | Page numbers. |
| L14 Bawa et al. 2005 | UNVERIFIED | End page (commonly 651-660). |
| L15 Das et al. 2007 | UNVERIFIED | MinHash clustering on MapReduce. |
| L20 Alshomary et al. 2019 | UNVERIFIED | LNCS volume (11437); whether the candidate stage uses MinHash or LSH. |
| L22 Ekstrand and Riedl 2009 | UNVERIFIED | Similarity measure used. |
| L24 / L25 | To check | Identical page range pp. 131-140 in the notes. |
| (formula) | UNVERIFIED | Variance s(1−s)/k of the MinHash estimator; omitted. |
| (paper) | Not verified | Densified one-permutation hashing (Shrivastava and Li, 2014); not listed. |

### Privacy

| ID | Status | Item |
|---|---|---|
| P1 Samarati and Sweeney 1998 | UNVERIFIED | Any IEEE S&P 1998 version. |
| P2 Samarati 2001 | UNVERIFIED | Issue month. |
| P3 Sweeney 2002 | UNVERIFIED | Whether the paper prints the 87% figure. |
| P5 Machanavajjhala et al. | UNVERIFIED | Variant names "distinct", "entropy", "recursive (c,l)". |
| P6 Li et al. 2007 | UNVERIFIED | "Skewness attack" and "similarity attack" names; city. |
| P7 LeFevre et al. 2006 | UNVERIFIED | City and month. |
| P8 Meyerson and Williams 2004 | UNVERIFIED | City. |
| P9 Bayardo and Agrawal 2005 | UNVERIFIED | City and month. |
| P10 Dwork et al. 2006 | UNVERIFIED | LNCS volume 3876; the paper's own wording ("epsilon-indistinguishability"). |
| P11 Dwork 2006 | UNVERIFIED | Content; LNCS volume 4052; "Part II". |
| P12 Dwork and Roth 2014 | UNVERIFIED | Page range (211-407 or 211-487); exact form of Theorem 3.8. |
| P13 Dwork et al. 2010 | UNVERIFIED | Error bound (order log^1.5 T / epsilon); city. |
| P14 Chan et al. 2011 | UNVERIFIED | Article number 26; the name "binary mechanism". |
| P15 Erlingsson et al. 2014 | UNVERIFIED | Content; full subtitle; city. |
| P16 Narayanan and Shmatikov 2008 | UNVERIFIED | "8 ratings within 14 days identify 99%"; city. |
| P17a Barbaro and Zeller 2006 | PARTLY VERIFIED | Article not opened; section and print page; count of about 650,000-658,000 users. |
| P19 Geoeditors | UNVERIFIED | Epsilon and release threshold actually used. |
| P21 Temporary accounts | UNVERIFIED | Date the rollout finished on all wikis. |
| P22 Rizoiu et al. 2016 | UNVERIFIED | City. |
| P23 Ganta et al. 2008 | UNVERIFIED | City. |
| (statement) | Not sourced | "Laplace noise with scale b has mean absolute value b and variance 2b^2" in those words; P12 Example 3.1 gives the count case only. |
| (surveys) | Not verified | Utility-cost surveys of k-anonymity (e.g. Aggarwal 2005; Brickell and Shmatikov 2008); not cited. |

## The gap statement, worded only as far as the notes support it

The notes support a narrow gap in three parts, and each part has a source behind it. First, stream-learning work asks for label delay to be considered but mostly supplies simulated or assumed delays: Žliobaitė 2010, Souza et al. 2018 and Grzenda et al. 2020 call immediate labels the usual and unrealistic assumption, and Plasse and Adams 2016 say delayed labels are not properly addressed in the literature ([D2](https://api.openalex.org/works/https://doi.org/10.1109/ICDMW.2010.49), [D4](https://api.openalex.org/works/https://doi.org/10.1109/BigData.2016.7840877), [D6](https://api.openalex.org/works/https://doi.org/10.1109/BRACIS.2018.00077), [D7](https://api.crossref.org/works/10.1007/s10618-019-00654-y)). Second, Wikipedia work measures time-to-revert but reports central tendency from complete history: a 2.8-minute median for mass deletions in 2003 data and a 12.4-minute median in 2011, 21.4 minutes with ClueBot NG down ([W8](http://hint.fm/papers/history_flow.pdf), [W11](https://www.stuartgeiger.com/wikisym13-cluebot.pdf)). Third, the statistics of reporting delay and data vintages give the right framework but, in the sources checked, have been applied to disease counts, insurance claims and macroeconomic series ([D17](https://api.crossref.org/works/10.1111/biom.12194), [D18](https://api.crossref.org/works/10.2307/3315826.n1), [D21](https://api.crossref.org/works/10.1111/j.1538-4616.2008.00115.x)). The systems literature adds a fourth leg: Dataflow, Spark's watermark and Golab and Johnson's consistency levels define when to stop waiting, and none measures the error of an open result as a function of the wait ([S20](https://www.vldb.org/pvldb/vol8/p1792-Akidau.pdf), [S26](https://www.cidrdb.org/cidr2011/Papers/CIDR11_Paper13.pdf)).

A sentence the notes can carry, for the team to reword in its own voice, has this content: to our knowledge, none of the sources we examined reports, for Wikipedia reverts, the share of eventual revert labels still missing as a function of the waiting time, measured by comparing a live edit stream with a later full-history snapshot. The draft's existing TODO wording ("prior work measures revert delay; it does not measure the error of a live count as a function of the wait") is consistent with W8, W9 and W11, provided "to our knowledge" is added. For the MinHash side analysis the equivalent supported wording is that the team found no prior work applying MinHash or LSH to edit comments, diffs or revert detection; the nearest are Potthast and Stein 2008 and Weissman et al. 2015.

Three findings in the notes strengthen the motivation without widening the claim. The delay distribution moved when one bot went down while the share eventually reverted did not, so a live count can change with no change in the final count (W11). Reporting-delay distributions also changed over time in epidemic surveillance (D17, D19b). The heavy tail (median in minutes, mean in days in W8; 62-day median for bot-bot reverts in W24) supports reporting E(L) at several waits instead of one summary number.

The claim must stay inside five limits. It is "not found in the sources checked", not a proof of absence. No systematic search of post-2020 Wikipedia research (Wikimedia Research reports, ORES and revert-risk evaluations) was done for an existing delay curve; if one exists, the statement must be narrowed. Two neighbours come close and should be acknowledged, not hidden: Kumar et al. 2016 report a detection share by elapsed time for hoax articles (a different label, deletion not revert), and Research:Revert states that nearly all English Wikipedia reverts happen within 48 hours and warns that observation cutoffs censor late reverts. The unopened 2026 Phabricator tasks proposing a median time-to-live metric with a 7-day window could bear directly on the claim and should be read first. No source checked uses a 4-day follow-up window, so the notes give no literature basis for that choice; the survey should present it as the project's own design decision and name its consequence (reverts after 4 days are outside both numerator and denominator). Finally, the notes found no peer-reviewed measurement of label latency in content moderation, but that search was shallow.

## Conclusion

The survey's strongest framing is not that label delay is new, but that four literatures each hold one piece and none holds the measurement: stream learning has the problem statement, statistics has the estimator and the vocabulary (reporting delay, right truncation, vintages), Wikipedia research has the retrospective medians and the evidence that the distribution shifts, and stream systems have the mechanisms that make a wait explicit. Read together, Golab and Johnson's Open, Closed and Complete levels and Lawless's occurred-but-not-reported events describe the same object from the warehouse side and the statistical side, and E(L) is the number that connects them. The MediaWiki History dataset already carries a seconds-to-revert field, so the retrospective delay distribution is cheap to compute (an inference from the field list in W2, not a statement in any source); what the checked sources lack is the live-versus-late comparison, which is where the survey should place the contribution.

Three practical consequences follow for the writing. The reference list needs no deletions, only completion and four decisions (the venue label for [17], the year for [24], which version of AMS to cite, and the Dwork and Roth page range if that source is added). Fourteen of the 35 systems entries have only [RECALL] content, so any bound or formula quoted from Bloom, DGIM, Count-Min, Misra-Gries, MillWheel, Snodgrass or Kimball needs the text opened first. And two items should be checked before the gap sentence is final: the post-2020 Wikimedia research output and the 2026 Phabricator time-to-live tasks, because either could turn "to our knowledge" into a citation.

## Appendix: BibTeX entries for the confirmed sources

Every field below comes from the notes. A `%` comment marks any field the notes could not confirm, and any title or name that differs between records. Classic BibTeX does not accept comments inside an entry, so resolve each comment and delete it before compiling. Author names are given as initials because that is what the notes hold. Non-ASCII letters are left as UTF-8. Sources that the notes did not confirm are left out: Yoshikawa and Imai (arXiv:1802.00255), the 2009 Signpost study, the 2026 Phabricator time-to-live tasks, densified one-permutation hashing, the k-anonymity utility surveys, and the New York Times article P17a (only partly verified). Access dates for web pages are 17 Nov. 2026.

```bibtex
% ---------- Area 1: delayed labels and reporting delay ----------

@inproceedings{D01_kuncheva2008,
  author    = {L. I. Kuncheva and J. S. S{\'a}nchez},
  title     = {Nearest Neighbour Classifiers for Streaming Data with Delayed Labelling},
  booktitle = {Proc. 2008 Eighth IEEE International Conference on Data Mining (ICDM)},
  month     = dec,
  year      = {2008},
  pages     = {869--874},
  doi       = {10.1109/ICDM.2008.33}
}

@inproceedings{D02_zliobaite2010,
  author    = {I. {\v Z}liobait{\.e}},
  title     = {Change with Delayed Labeling: When is it Detectable?},
  booktitle = {Proc. 2010 IEEE International Conference on Data Mining Workshops (ICDMW)},
  month     = dec,
  year      = {2010},
  pages     = {843--850},
  doi       = {10.1109/ICDMW.2010.49}
}

@incollection{D03_marrs2010,
  author    = {G. R. Marrs and R. J. Hickey and M. M. Black},
  title     = {The Impact of Latency on Online Classification Learning with Concept Drift},
  booktitle = {Knowledge Science, Engineering and Management (KSEM 2010)}, % UNVERIFIED: conference name; Crossref shows only "Lecture Notes in Computer Science"
  series    = {Lecture Notes in Computer Science},
  % volume  = {6291}, % UNVERIFIED: volume number
  publisher = {Springer},
  year      = {2010},
  pages     = {459--469},
  doi       = {10.1007/978-3-642-15280-1_42}
}

@inproceedings{D04_plasse2016,
  author    = {J. Plasse and N. Adams},
  title     = {Handling delayed labels in temporally evolving data streams},
  booktitle = {Proc. 2016 IEEE International Conference on Big Data (Big Data)},
  month     = dec,
  year      = {2016},
  pages     = {2416--2424},
  doi       = {10.1109/BigData.2016.7840877}
}

@inproceedings{D05_souza2015sdm,
  author    = {V. M. A. Souza and D. F. Silva and J. Gama and G. E. A. P. A. Batista},
  title     = {Data Stream Classification Guided by Clustering on Nonstationary Environments and Extreme Verification Latency},
  booktitle = {Proc. 2015 SIAM International Conference on Data Mining (SDM)},
  month     = jun,
  year      = {2015},
  pages     = {873--881},
  doi       = {10.1137/1.9781611974010.98}
}

@inproceedings{D05b_souza2015icmla,
  author    = {V. M. A. Souza and D. F. Silva and G. E. A. P. A. Batista and J. Gama},
  title     = {Classification of Evolving Data Streams with Infinitely Delayed Labels},
  booktitle = {Proc. 2015 IEEE 14th Int. Conf. Machine Learning and Applications (ICMLA)},
  month     = dec,
  year      = {2015},
  pages     = {214--219},
  doi       = {10.1109/ICMLA.2015.174}
}

@inproceedings{D06_souza2018,
  author    = {V. Souza and T. Pinho and G. Batista}, % OpenAlex spells the second author "Tiago Pinho da Silva"
  title     = {Evaluating Stream Classifiers with Delayed Labels Information},
  booktitle = {Proc. 2018 7th Brazilian Conference on Intelligent Systems (BRACIS)},
  month     = oct,
  year      = {2018},
  pages     = {408--413},
  doi       = {10.1109/BRACIS.2018.00077}
}

@article{D07_grzenda2020,
  author  = {M. Grzenda and H. M. Gomes and A. Bifet},
  title   = {Delayed labelling evaluation for data streams},
  journal = {Data Mining and Knowledge Discovery},
  volume  = {34},
  number  = {5},
  pages   = {1237--1266},
  year    = {2020}, % published online 16 Nov. 2019
  doi     = {10.1007/s10618-019-00654-y}
}

@article{D08_gomes2019,
  author  = {H. M. Gomes and J. Read and A. Bifet and J. P. Barddal and J. Gama},
  title   = {Machine learning for streaming data: state of the art, challenges, and opportunities}, % Crossref title stops at "Machine learning for streaming data"
  journal = {ACM SIGKDD Explorations Newsletter},
  volume  = {21},
  number  = {2},
  pages   = {6--22},
  month   = nov,
  year    = {2019},
  doi     = {10.1145/3373464.3373470}
}

@article{D09_gomes2022,
  author  = {H. M. Gomes and M. Grzenda and R. Mello and J. Read and M. H. Le Nguyen and A. Bifet},
  title   = {A Survey on Semi-supervised Learning for Delayed Partially Labelled Data Streams},
  journal = {ACM Computing Surveys},
  volume  = {55},
  number  = {4},
  pages   = {1--42}, % UNVERIFIED: article number within vol. 55 no. 4
  month   = nov,
  year    = {2022},
  doi     = {10.1145/3523055}
}

@article{D10_gama2014,
  author  = {J. Gama and I. {\v Z}liobait{\.e} and A. Bifet and M. Pechenizkiy and A. Bouchachia},
  title   = {A survey on concept drift adaptation},
  journal = {ACM Computing Surveys},
  volume  = {46},
  number  = {4},
  pages   = {1--37}, % UNVERIFIED: article number (commonly cited as Article 44)
  month   = mar,
  year    = {2014},
  doi     = {10.1145/2523813}
}

@article{D11_dyer2014,
  author  = {K. B. Dyer and R. Capo and R. Polikar},
  title   = {{COMPOSE}: A Semisupervised Learning Framework for Initially Labeled Nonstationary Streaming Data},
  journal = {IEEE Transactions on Neural Networks and Learning Systems},
  volume  = {25},
  number  = {1},
  pages   = {12--26},
  month   = jan,
  year    = {2014},
  doi     = {10.1109/TNNLS.2013.2277712}
}

@inproceedings{D12_chapelle2014,
  author    = {O. Chapelle},
  title     = {Modeling delayed feedback in display advertising},
  booktitle = {Proc. 20th ACM SIGKDD International Conference on Knowledge Discovery and Data Mining (KDD '14)},
  month     = aug,
  year      = {2014},
  pages     = {1097--1105},
  doi       = {10.1145/2623330.2623634}
}

@inproceedings{D13_ktena2019,
  author    = {S. I. Ktena and A. Tejani and L. Theis and P. K. Myana and D. Dilipkumar and F. Husz{\'a}r and S. Yoo and W. Shi},
  title     = {Addressing delayed feedback for continuous training with neural networks in {CTR} prediction},
  booktitle = {Proc. 13th ACM Conference on Recommender Systems (RecSys '19)},
  month     = sep,
  year      = {2019},
  pages     = {187--195},
  doi       = {10.1145/3298689.3347002},
  note      = {Preprint arXiv:1907.06558}
}

@inproceedings{D14_joulani2013,
  author    = {P. Joulani and A. Gy{\"o}rgy and C. Szepesv{\'a}ri},
  title     = {Online Learning under Delayed Feedback},
  booktitle = {Proc. 30th International Conference on Machine Learning (ICML)},
  series    = {Proceedings of Machine Learning Research},
  volume    = {28},
  number    = {3},
  pages     = {1453--1461},
  year      = {2013},
  url       = {https://proceedings.mlr.press/v28/joulani13.html} % no DOI
}

@incollection{D15a_mesterharm2005,
  author    = {C. Mesterharm},
  title     = {On-line Learning with Delayed Label Feedback},
  booktitle = {Lecture Notes in Computer Science}, % UNVERIFIED: host conference (believed Algorithmic Learning Theory, ALT 2005) and LNCS volume
  publisher = {Springer},
  year      = {2005},
  pages     = {399--413},
  doi       = {10.1007/11564089_31}
}

@article{D15b_weinberger2002,
  author  = {M. J. Weinberger and E. Ordentlich},
  title   = {On delayed prediction of individual sequences},
  journal = {IEEE Transactions on Information Theory},
  volume  = {48},
  number  = {7},
  pages   = {1959--1976},
  month   = jul,
  year    = {2002},
  doi     = {10.1109/TIT.2002.1013136}
}

@article{D16_kaplan1958,
  author  = {E. L. Kaplan and P. Meier},
  title   = {Nonparametric Estimation from Incomplete Observations},
  journal = {Journal of the American Statistical Association},
  volume  = {53},
  number  = {282},
  pages   = {457--481},
  month   = jun,
  year    = {1958},
  doi     = {10.1080/01621459.1958.10501452}
}

@article{D17_hohle2014,
  author  = {M. H{\"o}hle and M. an der Heiden},
  title   = {Bayesian nowcasting during the {STEC} {O104:H4} outbreak in {Germany}, 2011},
  journal = {Biometrics},
  volume  = {70},
  number  = {4},
  pages   = {993--1002},
  month   = dec,
  year    = {2014}, % online 13 Jun. 2014
  doi     = {10.1111/biom.12194}
}

@article{D18_lawless1994,
  author  = {J. F. Lawless},
  title   = {Adjustments for reporting delays and the prediction of occurred but not reported events},
  journal = {Canadian Journal of Statistics},
  volume  = {22},
  number  = {1},
  pages   = {15--31},
  month   = mar,
  year    = {1994},
  doi     = {10.2307/3315826.n1} % keep the ".n1"; 10.2307/3315826 without it is a different article (Routledge, pp. 103-110)
}

@article{D19_zeger1989,
  author  = {S. L. Zeger and L.-C. See and P. J. Diggle},
  title   = {Statistical methods for monitoring the {AIDS} epidemic},
  journal = {Statistics in Medicine},
  volume  = {8},
  number  = {1},
  pages   = {3--21},
  month   = jan,
  year    = {1989},
  doi     = {10.1002/sim.4780080104}
}

@article{D19c_brookmeyer1989,
  author  = {R. Brookmeyer and A. Damiano},
  title   = {Statistical methods for short-term projections of {AIDS} incidence},
  journal = {Statistics in Medicine},
  volume  = {8},
  number  = {1},
  pages   = {23--34},
  year    = {1989},
  doi     = {10.1002/sim.4780080105} % record only; findings not read
}

@article{D19b_mcgough2020,
  author  = {S. F. McGough and M. A. Johansson and M. Lipsitch and N. A. Menzies},
  title   = {Nowcasting by {Bayesian} Smoothing: A flexible, generalizable model for real-time epidemic tracking},
  journal = {PLOS Computational Biology},
  volume  = {16},
  number  = {4},
  pages   = {e1007735},
  month   = apr,
  year    = {2020},
  doi     = {10.1371/journal.pcbi.1007735}
}

@article{D20_croushore2001,
  author  = {D. Croushore and T. Stark},
  title   = {A real-time data set for macroeconomists},
  journal = {Journal of Econometrics},
  volume  = {105},
  number  = {1},
  pages   = {111--130},
  month   = nov,
  year    = {2001},
  doi     = {10.1016/S0304-4076(01)00072-0}
  % working-paper version: Federal Reserve Bank of Philadelphia Working Paper 99-4, 1999, DOI 10.21799/frbp.wp.1999.04
}

@article{D21_aruoba2008,
  author  = {S. B. Aruoba},
  title   = {Data Revisions Are Not Well Behaved},
  journal = {Journal of Money, Credit and Banking},
  volume  = {40},
  number  = {2-3},
  pages   = {319--340},
  month   = mar,
  year    = {2008},
  doi     = {10.1111/j.1538-4616.2008.00115.x}
}

@inproceedings{D22_dalpozzolo2015,
  author    = {A. Dal Pozzolo and G. Boracchi and O. Caelen and C. Alippi and G. Bontempi},
  title     = {Credit card fraud detection and concept-drift adaptation with delayed supervised information},
  booktitle = {Proc. 2015 International Joint Conference on Neural Networks (IJCNN)},
  month     = jul,
  year      = {2015},
  pages     = {1--8},
  doi       = {10.1109/IJCNN.2015.7280527}
}

@article{D23_dalpozzolo2018,
  author  = {A. Dal Pozzolo and G. Boracchi and O. Caelen and C. Alippi and G. Bontempi},
  title   = {Credit Card Fraud Detection: A Realistic Modeling and a Novel Learning Strategy},
  journal = {IEEE Transactions on Neural Networks and Learning Systems},
  volume  = {29},
  number  = {8},
  pages   = {3784--3797},
  month   = aug,
  year    = {2018},
  doi     = {10.1109/TNNLS.2017.2736643}
}

% ---------- Area 2: Wikipedia reverts, vandalism detection, quality control ----------

@inproceedings{W01_flock2012,
  author    = {F. Fl{\"o}ck and D. Vrande{\v c}i{\'c} and E. Simperl},
  title     = {Revisiting reverts: accurate revert detection in {Wikipedia}},
  booktitle = {Proc. 23rd ACM Conf. Hypertext and Social Media (HT '12)},
  address   = {Milwaukee, WI, USA},
  year      = {2012},
  pages     = {3--12},
  doi       = {10.1145/2309996.2310000} % not 10.1145/2309996.2310038, which is a different paper
}

@misc{W02_mwhistorydumps,
  author       = {{Wikimedia Foundation}},
  title        = {Data Platform/Data Lake/Edits/Mediawiki history dumps},
  howpublished = {Wikitech},
  note         = {Page last edited 5 July 2026},
  url          = {https://wikitech.wikimedia.org/wiki/Data_Platform/Data_Lake/Edits/Mediawiki_history_dumps}
}

@misc{W03_mwhistory,
  author       = {{Wikimedia Foundation}},
  title        = {Data Platform/Data Lake/Edits/MediaWiki history},
  howpublished = {Wikitech},
  note         = {Page last edited 5 July 2026},
  url          = {https://wikitech.wikimedia.org/wiki/Data_Platform/Data_Lake/Edits/MediaWiki_history}
}

@misc{W04_manualreverts,
  author       = {{MediaWiki contributors}},
  title        = {Manual:Reverts},
  howpublished = {MediaWiki.org},
  note         = {Page last edited 21 June 2026},
  url          = {https://www.mediawiki.org/wiki/Manual:Reverts}
}

@misc{W05_researchrevert,
  author       = {{Wikimedia Research}},
  title        = {Research:Revert},
  howpublished = {Meta-Wiki},
  url          = {https://meta.wikimedia.org/wiki/Research:Revert}
}

@misc{W06_mwreverts,
  author       = {A. Halfaker},
  title        = {mwreverts},
  howpublished = {Python library (MIT License), documentation},
  url          = {https://pythonhosted.org/mwreverts/} % UNVERIFIED: version number and release year
}

@misc{W07_liftwingstreams,
  author       = {{Wikimedia Foundation}},
  title        = {Machine Learning/LiftWing/Streams},
  howpublished = {Wikitech},
  note         = {Page last edited 13 May 2026},
  url          = {https://wikitech.wikimedia.org/wiki/Machine_Learning/LiftWing/Streams}
}

@inproceedings{W08_viegas2004,
  author    = {F. B. Vi{\'e}gas and M. Wattenberg and K. Dave},
  title     = {Studying cooperation and conflict between authors with history flow visualizations},
  booktitle = {Proc. SIGCHI Conf. Human Factors in Computing Systems (CHI '04)},
  address   = {Vienna, Austria},
  month     = apr,
  year      = {2004},
  pages     = {575--582},
  doi       = {10.1145/985692.985765}
}

@inproceedings{W09_priedhorsky2007,
  author    = {R. Priedhorsky and J. Chen and S. K. Lam and K. Panciera and L. Terveen and J. Riedl},
  title     = {Creating, destroying, and restoring value in {Wikipedia}},
  booktitle = {Proc. 2007 Int. ACM Conf. Supporting Group Work (GROUP '07)},
  address   = {Sanibel Island, FL, USA}, % UNVERIFIED: conference location
  year      = {2007},
  pages     = {259--268}, % Crossref gives first page 259 only; end page from another paper's reference list
  doi       = {10.1145/1316624.1316663}
}

@inproceedings{W10_geiger2010,
  author    = {R. S. Geiger and D. Ribes},
  title     = {The work of sustaining order in {Wikipedia}: the banning of a vandal},
  booktitle = {Proc. 2010 ACM Conf. Computer Supported Cooperative Work (CSCW '10)},
  address   = {Savannah, GA, USA}, % UNVERIFIED: conference location
  year      = {2010},
  pages     = {117--126},
  doi       = {10.1145/1718918.1718941}
}

@inproceedings{W11_geiger2013,
  author    = {R. S. Geiger and A. Halfaker},
  title     = {When the levee breaks: without bots, what happens to {Wikipedia}'s quality control processes?},
  booktitle = {Proc. 9th Int. Symp. Open Collaboration (WikiSym '13)}, % paper header says WikiSym 2013; do not write "OpenSym 2013"
  address   = {Hong Kong, China},
  month     = aug,
  year      = {2013},
  pages     = {1--6}, % Crossref page field; UNVERIFIED: article number
  doi       = {10.1145/2491055.2491061}
}

@inproceedings{W12_kumar2016,
  author    = {S. Kumar and R. West and J. Leskovec},
  title     = {Disinformation on the {Web}: impact, characteristics, and detection of {Wikipedia} hoaxes},
  booktitle = {Proc. 25th Int. Conf. World Wide Web (WWW '16)},
  address   = {Montr{\'e}al, Canada}, % UNVERIFIED: conference location
  year      = {2016},
  pages     = {591--602},
  doi       = {10.1145/2872427.2883085}
}

@inproceedings{W13_kittur2007,
  author    = {A. Kittur and B. Suh and B. A. Pendleton and E. H. Chi},
  title     = {He says, she says: conflict and coordination in {Wikipedia}},
  booktitle = {Proc. SIGCHI Conf. Human Factors in Computing Systems (CHI '07)},
  address   = {San Jose, CA, USA}, % UNVERIFIED: conference location
  month     = apr,
  year      = {2007},
  pages     = {453--462},
  doi       = {10.1145/1240624.1240698}
}

@incollection{W14_potthast2008ecir,
  author    = {M. Potthast and B. Stein and R. Gerling},
  title     = {Automatic vandalism detection in {Wikipedia}},
  booktitle = {Advances in Information Retrieval (ECIR 2008)},
  series    = {Lecture Notes in Computer Science},
  % volume  = {4956}, % UNVERIFIED: volume number
  publisher = {Springer},
  address   = {Berlin, Heidelberg},
  year      = {2008}, % UNVERIFIED: year is not in the Crossref record
  pages     = {663--668},
  doi       = {10.1007/978-3-540-78646-7_75}
}

@inproceedings{W15_west2010eurosec,
  author    = {A. G. West and S. Kannan and I. Lee},
  title     = {Detecting {Wikipedia} vandalism via spatio-temporal analysis of revision metadata}, % Crossref title carries a trailing "?"
  booktitle = {Proc. 3rd European Workshop on System Security (EUROSEC '10)},
  address   = {Paris, France}, % UNVERIFIED: workshop location
  year      = {2010},
  pages     = {22--28},
  doi       = {10.1145/1752046.1752050}
}

@inproceedings{W16_west2010stiki,
  author    = {A. G. West and S. Kannan and I. Lee},
  title     = {{STiki}: an anti-vandalism tool for {Wikipedia} using spatio-temporal analysis of revision metadata},
  booktitle = {Proc. 6th Int. Symp. Wikis and Open Collaboration (WikiSym '10)},
  address   = {Gda{\'n}sk, Poland}, % UNVERIFIED: symposium location
  year      = {2010},
  pages     = {1--2}, % demo; UNVERIFIED: article number
  doi       = {10.1145/1832772.1832814}
}

@incollection{W17_adler2011,
  author    = {B. T. Adler and L. de Alfaro and S. M. Mola-Velasco and P. Rosso and A. G. West},
  title     = {{Wikipedia} vandalism detection: combining natural language, metadata, and reputation features},
  booktitle = {Computational Linguistics and Intelligent Text Processing (CICLing 2011)},
  series    = {Lecture Notes in Computer Science},
  volume    = {6609},
  publisher = {Springer},
  address   = {Berlin, Heidelberg},
  year      = {2011},
  pages     = {277--288},
  doi       = {10.1007/978-3-642-19437-5_23}
}

@article{W18_halfaker2020ores,
  author  = {A. Halfaker and R. S. Geiger},
  title   = {{ORES}: lowering barriers with participatory machine learning in {Wikipedia}},
  journal = {Proc. ACM Hum.-Comput. Interact.},
  volume  = {4},
  number  = {CSCW2},
  pages   = {1--37},
  month   = oct,
  year    = {2020},
  doi     = {10.1145/3415219},
  note    = {Article 148. Preprint arXiv:1909.05189}
}

@inproceedings{W19_trokhymovych2023,
  author    = {M. Trokhymovych and M. Aslam and A.-J. Chou and R. Baeza-Yates and D. Saez-Trumper},
  title     = {Fair multilingual vandalism detection system for {Wikipedia}},
  booktitle = {Proc. 29th ACM SIGKDD Conf. Knowledge Discovery and Data Mining (KDD '23)},
  address   = {Long Beach, CA, USA}, % UNVERIFIED: conference location
  year      = {2023},
  pages     = {4981--4990},
  doi       = {10.1145/3580305.3599823},
  note      = {Preprint arXiv:2306.01650}
}

@misc{W20a_revertrisk_la,
  author       = {{Wikimedia Foundation}},
  title        = {Machine learning models/Production/Language-agnostic revert risk},
  howpublished = {Meta-Wiki (model card)},
  note         = {Page last edited 14 August 2026},
  url          = {https://meta.wikimedia.org/wiki/Machine_learning_models/Production/Language-agnostic_revert_risk}
}

@misc{W20b_revertrisk_ml,
  author       = {{Wikimedia Foundation}},
  title        = {Machine learning models/Production/Multilingual revert risk},
  howpublished = {Meta-Wiki (model card)},
  note         = {Page last edited 11 June 2026},
  url          = {https://meta.wikimedia.org/wiki/Machine_learning_models/Production/Multilingual_revert_risk}
}

@inproceedings{W21_sumi2011,
  author    = {R. Sumi and T. Yasseri and A. Rung and A. Kornai and J. Kert{\'e}sz},
  title     = {Edit wars in {Wikipedia}},
  booktitle = {Proc. 2011 IEEE 3rd Int. Conf. Privacy, Security, Risk and Trust and 2011 IEEE 3rd Int. Conf. Social Computing (PASSAT/SocialCom)},
  address   = {Boston, MA, USA}, % UNVERIFIED: conference location
  month     = oct,
  year      = {2011},
  pages     = {724--727},
  doi       = {10.1109/PASSAT/SocialCom.2011.47},
  note      = {Preprint arXiv:1107.3689}
}

@article{W22_yasseri2012,
  author  = {T. Yasseri and R. Sumi and A. Rung and A. Kornai and J. Kert{\'e}sz},
  title   = {Dynamics of conflicts in {Wikipedia}},
  journal = {PLoS ONE},
  volume  = {7},
  number  = {6},
  pages   = {e38869},
  month   = jun,
  year    = {2012},
  doi     = {10.1371/journal.pone.0038869}
}

@article{W23_tsvetkova2017,
  author  = {M. Tsvetkova and R. Garc{\'i}a-Gavilanes and L. Floridi and T. Yasseri},
  title   = {Even good bots fight: the case of {Wikipedia}},
  journal = {PLoS ONE},
  volume  = {12},
  number  = {2},
  pages   = {e0171774},
  month   = feb,
  year    = {2017},
  doi     = {10.1371/journal.pone.0171774}
}

@article{W24_geiger2017,
  author  = {R. S. Geiger and A. Halfaker},
  title   = {Operationalizing conflict and cooperation between automated software agents in {Wikipedia}: a replication and expansion of `{Even} Good Bots Fight'},
  journal = {Proc. ACM Hum.-Comput. Interact.},
  volume  = {1},
  number  = {CSCW}, % Crossref; the paper's own reference format gives "1, 2, Article 49 (November 2017)"
  pages   = {1--33},
  month   = nov,
  year    = {2017}, % Crossref issue date 6 Dec. 2017
  doi     = {10.1145/3134684},
  note    = {Article 49. Preprint arXiv:1810.07273}
}

@misc{W25_tempaccounts,
  author       = {{Wikimedia Foundation}},
  title        = {Trust and Safety Product/Temporary Accounts},
  howpublished = {MediaWiki.org},
  note         = {Main page last edited 6 February 2026; Updates subpage last edited 2 October 2026 (https://www.mediawiki.org/wiki/Trust_and_Safety_Product/Temporary_Accounts/Updates)},
  url          = {https://www.mediawiki.org/wiki/Trust_and_Safety_Product/Temporary_Accounts}
}

@misc{W26a_t409079,
  author       = {{Wikimedia Phabricator}},
  title        = {Deploy Temporary accounts to English Wikipedia},
  howpublished = {Task T409079},
  note         = {Deployed 4 November 2025; closed as resolved 5 November 2025},
  url          = {https://phabricator.wikimedia.org/T409079}
}

@misc{W26b_enwiki_tempaccounts,
  author       = {{English Wikipedia}},
  title        = {Wikipedia:Temporary accounts},
  howpublished = {Project page},
  note         = {Page last edited 19 October 2026},
  url          = {https://en.wikipedia.org/wiki/Wikipedia:Temporary_accounts}
}

@article{W27_halfaker2013,
  author  = {A. Halfaker and R. S. Geiger and J. T. Morgan and J. Riedl},
  title   = {The rise and decline of an open collaboration system: how {Wikipedia}'s reaction to popularity is causing its decline},
  journal = {American Behavioral Scientist},
  volume  = {57},
  number  = {5},
  pages   = {664--688},
  month   = may, % UNVERIFIED: print month; online 28 Dec. 2012
  year    = {2013},
  doi     = {10.1177/0002764212469365}
}

@inproceedings{W28_halfaker2011,
  author    = {A. Halfaker and A. Kittur and J. Riedl},
  title     = {Don't bite the newbies: how reverts affect the quantity and quality of {Wikipedia} work},
  booktitle = {Proc. 7th Int. Symp. Wikis and Open Collaboration (WikiSym '11)},
  address   = {Mountain View, CA, USA}, % UNVERIFIED: symposium location
  year      = {2011},
  pages     = {163--172},
  doi       = {10.1145/2038558.2038585}
}

@article{W29_kiesel2017,
  author  = {J. Kiesel and M. Potthast and M. Hagen and B. Stein},
  title   = {Spatio-temporal analysis of reverted {Wikipedia} edits},
  journal = {Proc. Int. AAAI Conf. Web and Social Media (ICWSM)},
  volume  = {11},
  number  = {1},
  pages   = {122--131},
  year    = {2017},
  doi     = {10.1609/icwsm.v11i1.14900} % record confirmed; paper not read
}

% ---------- Area 3: streaming algorithms, stream processing, lakehouse ----------

@article{S01_vitter1985,
  author  = {J. S. Vitter},
  title   = {Random sampling with a reservoir},
  journal = {ACM Transactions on Mathematical Software},
  volume  = {11},
  number  = {1},
  pages   = {37--57},
  month   = mar,
  year    = {1985},
  doi     = {10.1145/3147.3165}
}

@article{S02_bloom1970,
  author  = {B. H. Bloom},
  title   = {Space/time trade-offs in hash coding with allowable errors},
  journal = {Communications of the ACM},
  volume  = {13},
  number  = {7},
  pages   = {422--426},
  month   = jul,
  year    = {1970},
  doi     = {10.1145/362686.362692}
}

@article{S03_broder2004,
  author  = {A. Broder and M. Mitzenmacher},
  title   = {Network applications of {Bloom} filters: A survey},
  journal = {Internet Mathematics},
  volume  = {1},
  number  = {4},
  pages   = {485--509},
  year    = {2004},
  doi     = {10.1080/15427951.2004.10129096}
}

@article{S04_flajolet1985,
  author  = {P. Flajolet and G. N. Martin},
  title   = {Probabilistic counting algorithms for data base applications},
  journal = {Journal of Computer and System Sciences},
  volume  = {31},
  number  = {2},
  pages   = {182--209},
  month   = oct,
  year    = {1985},
  doi     = {10.1016/0022-0000(85)90041-8}
}

@inproceedings{S05_flajolet2007,
  author    = {P. Flajolet and {\'E}. Fusy and O. Gandouet and F. Meunier},
  title     = {{HyperLogLog}: the analysis of a near-optimal cardinality estimation algorithm},
  booktitle = {Proc. 2007 Conference on Analysis of Algorithms (AofA 07)},
  series    = {Discrete Mathematics and Theoretical Computer Science Proceedings},
  volume    = {AH},
  pages     = {127--146}, % per the paper's own running head; some secondary citations give 137-156
  year      = {2007},
  doi       = {10.46298/dmtcs.3545}
}

@inproceedings{S06_heule2013,
  author    = {S. Heule and M. Nunkesser and A. Hall},
  title     = {{HyperLogLog} in practice: Algorithmic engineering of a state of the art cardinality estimation algorithm},
  booktitle = {Proc. 16th International Conference on Extending Database Technology (EDBT '13)},
  pages     = {683--692},
  month     = mar,
  year      = {2013},
  doi       = {10.1145/2452376.2452456}
}

@inproceedings{S07a_alon1996,
  author    = {N. Alon and Y. Matias and M. Szegedy},
  title     = {The space complexity of approximating the frequency moments},
  booktitle = {Proc. 28th Annual ACM Symposium on Theory of Computing (STOC '96)},
  pages     = {20--29},
  year      = {1996},
  doi       = {10.1145/237814.237823}
}

@article{S07b_alon1999,
  author  = {N. Alon and Y. Matias and M. Szegedy},
  title   = {The space complexity of approximating the frequency moments},
  journal = {Journal of Computer and System Sciences},
  volume  = {58},
  number  = {1},
  pages   = {137--147},
  month   = feb,
  year    = {1999},
  doi     = {10.1006/jcss.1997.1545}
}

@article{S08_datar2002,
  author  = {M. Datar and A. Gionis and P. Indyk and R. Motwani},
  title   = {Maintaining stream statistics over sliding windows},
  journal = {SIAM Journal on Computing},
  volume  = {31},
  number  = {6},
  pages   = {1794--1813},
  year    = {2002},
  doi     = {10.1137/S0097539701398363}
}

@article{S09_cormode2005,
  author  = {G. Cormode and S. Muthukrishnan},
  title   = {An improved data stream summary: the count-min sketch and its applications},
  journal = {Journal of Algorithms},
  volume  = {55},
  number  = {1},
  pages   = {58--75},
  month   = apr,
  year    = {2005},
  doi     = {10.1016/j.jalgor.2003.12.001}
}

@article{S10_misra1982,
  author  = {J. Misra and D. Gries},
  title   = {Finding repeated elements},
  journal = {Science of Computer Programming},
  volume  = {2},
  number  = {2},
  pages   = {143--152},
  month   = nov,
  year    = {1982},
  doi     = {10.1016/0167-6423(82)90012-0}
}

@incollection{S11_metwally2005,
  author    = {A. Metwally and D. Agrawal and A. El Abbadi},
  title     = {Efficient computation of frequent and top-k elements in data streams},
  booktitle = {Database Theory - ICDT 2005},
  series    = {Lecture Notes in Computer Science},
  volume    = {3363}, % UNVERIFIED: volume number (from recall)
  publisher = {Springer},
  year      = {2005}, % Crossref lists the online date as 2004
  pages     = {398--412},
  doi       = {10.1007/978-3-540-30570-5_27}
}

@book{S12_leskovec2020,
  author    = {J. Leskovec and A. Rajaraman and J. D. Ullman},
  title     = {Mining of Massive Datasets},
  edition   = {3},
  publisher = {Cambridge University Press},
  address   = {Cambridge, U.K.},
  year      = {2020},
  isbn      = {9781108476348},
  doi       = {10.1017/9781108684163}
  % ch. 3 "Finding Similar Items", ch. 4 "Mining Data Streams"; UNVERIFIED: section numbers
}

@inproceedings{S13_kreps2011,
  author    = {J. Kreps and N. Narkhede and J. Rao},
  title     = {Kafka: a distributed messaging system for log processing},
  booktitle = {Proc. 6th International Workshop on Networking Meets Databases (NetDB '11)}, % UNVERIFIED: "6th" ordinal
  address   = {Athens, Greece},
  month     = jun,
  year      = {2011}
  % no DOI found; UNVERIFIED: page numbers (commonly cited as pp. 1-7)
}

@inproceedings{S14_zaharia2012,
  author    = {M. Zaharia and M. Chowdhury and T. Das and A. Dave and J. Ma and M. McCauley and M. J. Franklin and S. Shenker and I. Stoica}, % UNVERIFIED: "McCauley" (paper) vs "McCauly" (USENIX page)
  title     = {Resilient distributed datasets: A fault-tolerant abstraction for in-memory cluster computing},
  booktitle = {Proc. 9th USENIX Symposium on Networked Systems Design and Implementation (NSDI '12)},
  address   = {San Jose, CA},
  pages     = {15--28},
  month     = apr,
  year      = {2012},
  url       = {https://www.usenix.org/conference/nsdi12/technical-sessions/presentation/zaharia} % no DOI
}

@inproceedings{S15_zaharia2013,
  author    = {M. Zaharia and T. Das and H. Li and T. Hunter and S. Shenker and I. Stoica},
  title     = {Discretized streams: Fault-tolerant streaming computation at scale},
  booktitle = {Proc. 24th ACM Symposium on Operating Systems Principles (SOSP '13)},
  pages     = {423--438},
  month     = nov,
  year      = {2013},
  doi       = {10.1145/2517349.2522737}
}

@inproceedings{S16_armbrust2018,
  author    = {M. Armbrust and T. Das and J. Torres and B. Yavuz and S. Zhu and R. Xin and A. Ghodsi and I. Stoica and M. Zaharia},
  title     = {Structured Streaming: A declarative {API} for real-time applications in {Apache Spark}},
  booktitle = {Proc. 2018 International Conference on Management of Data (SIGMOD '18)},
  pages     = {601--613},
  month     = may,
  year      = {2018},
  doi       = {10.1145/3183713.3190664}
}

@misc{S17_sparkstreamingguide,
  author       = {{Apache Software Foundation}},
  title        = {Structured Streaming Programming Guide: {APIs} on {DataFrames} and {Datasets}},
  howpublished = {Apache Spark documentation},
  note         = {Version 4.3.0 on the access date. Accessed Nov. 17, 2026},
  url          = {https://spark.apache.org/docs/latest/streaming/apis-on-dataframes-and-datasets.html}
}

@article{S18_carbone2015,
  author  = {P. Carbone and A. Katsifodimos and S. Ewen and V. Markl and S. Haridi and K. Tzoumas}, % UNVERIFIED: author order; the PDF first page prints Carbone, Ewen, Haridi, Katsifodimos, Markl, Tzoumas
  title   = {{Apache Flink}: Stream and batch processing in a single engine},
  journal = {Bulletin of the IEEE Computer Society Technical Committee on Data Engineering},
  volume  = {38}, % from the issue path and recall
  number  = {4},
  pages   = {28--38}, % UNVERIFIED: end page 38
  month   = dec,
  year    = {2015},
  url     = {http://sites.computer.org/debull/A15dec/p28.pdf} % no DOI
}

@article{S19_akidau2013,
  author  = {T. Akidau and A. Balikov and K. Bekiro{\u g}lu and S. Chernyak and J. Haberman and R. Lax and S. McVeety and D. Mills and P. Nordstrom and S. Whittle},
  title   = {{MillWheel}: Fault-tolerant stream processing at {Internet} scale}, % Crossref holds only "MillWheel"; subtitle from recall
  journal = {Proceedings of the VLDB Endowment},
  volume  = {6},
  number  = {11},
  pages   = {1033--1044},
  month   = aug,
  year    = {2013},
  doi     = {10.14778/2536222.2536229}
}

@article{S20_akidau2015,
  author  = {T. Akidau and R. Bradshaw and C. Chambers and S. Chernyak and R. J. Fern{\'a}ndez-Moctezuma and R. Lax and S. McVeety and D. Mills and F. Perry and E. Schmidt and S. Whittle},
  title   = {The {Dataflow} model: A practical approach to balancing correctness, latency, and cost in massive-scale, unbounded, out-of-order data processing},
  journal = {Proceedings of the VLDB Endowment},
  volume  = {8},
  number  = {12},
  pages   = {1792--1803},
  month   = aug,
  year    = {2015},
  doi     = {10.14778/2824032.2824076}
}

@misc{S21_kreps2014,
  author       = {J. Kreps},
  title        = {Questioning the {Lambda} Architecture},
  howpublished = {O'Reilly Radar},
  month        = jul,
  year         = {2014},
  note         = {July 2, 2014. Blog post, not peer-reviewed},
  url          = {https://www.oreilly.com/radar/questioning-the-lambda-architecture/}
}

@book{S22_marz2015,
  author    = {N. Marz and J. Warren},
  title     = {Big Data: Principles and Best Practices of Scalable Realtime Data Systems},
  publisher = {Manning},
  address   = {Shelter Island, NY},
  month     = apr,
  year      = {2015},
  isbn      = {978-1-61729-034-3}
}

@article{S23_armbrust2020,
  author  = {M. Armbrust and T. Das and L. Sun and B. Yavuz and S. Zhu and M. Murthy and J. Torres and H. van Hovell and A. Ionescu and A. {\L}uszczak and M. {\'S}witakowski and M. Szafra{\'n}ski and X. Li and T. Ueshin and M. Mokhtar and P. Boncz and A. Ghodsi and S. Paranjpye and P. Senster and R. Xin and M. Zaharia},
  title   = {{Delta Lake}: High-performance {ACID} table storage over cloud object stores},
  journal = {Proceedings of the VLDB Endowment},
  volume  = {13},
  number  = {12},
  pages   = {3411--3424},
  month   = aug,
  year    = {2020},
  doi     = {10.14778/3415478.3415560}
}

@inproceedings{S24_armbrust2021,
  author    = {M. Armbrust and A. Ghodsi and R. Xin and M. Zaharia},
  title     = {Lakehouse: A new generation of open platforms that unify data warehousing and advanced analytics},
  booktitle = {Proc. 11th Conference on Innovative Data Systems Research (CIDR '21)}, % UNVERIFIED: "11th" ordinal
  month     = jan,
  year      = {2021},
  url       = {https://www.cidrdb.org/cidr2021/papers/cidr2021_paper17.pdf} % no DOI; CIDR papers have no page numbers in a bound volume
}

@misc{S25_databricksmedallion,
  author       = {{Databricks}},
  title        = {What is the medallion lakehouse architecture?},
  howpublished = {Databricks on AWS documentation},
  note         = {Last updated Oct. 29, 2026. Accessed Nov. 17, 2026. Vendor documentation; the pattern has no founding paper},
  url          = {https://docs.databricks.com/aws/en/lakehouse/medallion}
}

@inproceedings{S26_golab2011,
  author    = {L. Golab and T. Johnson},
  title     = {Consistency in a stream warehouse},
  booktitle = {Proc. 5th Biennial Conference on Innovative Data Systems Research (CIDR '11)},
  address   = {Asilomar, CA},
  month     = jan,
  year      = {2011},
  url       = {https://www.cidrdb.org/cidr2011/Papers/CIDR11_Paper13.pdf} % no DOI; UNVERIFIED: page range (commonly cited as pp. 114-122)
}

@book{S27_snodgrass,
  author    = {R. T. Snodgrass},
  title     = {Developing Time-Oriented Database Applications in {SQL}},
  publisher = {Morgan Kaufmann},
  address   = {San Francisco, CA},
  year      = {2000}, % UNVERIFIED: the author's page says published July 1999; 2000 is the usual citation year
  isbn      = {1-55860-436-7}
}

@book{S28_kimball2013,
  author    = {R. Kimball and M. Ross},
  title     = {The Data Warehouse Toolkit: The Definitive Guide to Dimensional Modeling},
  edition   = {3},
  publisher = {Wiley},
  address   = {Indianapolis, IN},
  month     = jul,
  year      = {2013},
  isbn      = {978-1-118-53080-1}
}

@inproceedings{S29_hellerstein1997,
  author    = {J. M. Hellerstein and P. J. Haas and H. J. Wang},
  title     = {Online aggregation},
  booktitle = {Proc. 1997 ACM SIGMOD International Conference on Management of Data (SIGMOD '97)},
  pages     = {171--182},
  year      = {1997},
  doi       = {10.1145/253260.253291}
}

@inproceedings{S30_begoli2019,
  author    = {E. Begoli and T. Akidau and F. Hueske and J. Hyde and K. Knight and K. Knowles},
  title     = {One {SQL} to rule them all: An efficient and syntactically idiomatic approach to management of streams and tables},
  booktitle = {Proc. 2019 International Conference on Management of Data (SIGMOD '19)},
  pages     = {1757--1772},
  month     = jun,
  year      = {2019},
  doi       = {10.1145/3299869.3314040}
}

@article{S31_angles2017,
  author  = {R. Angles and M. Arenas and P. Barcel{\'o} and A. Hogan and J. Reutter and D. Vrgo{\v c}},
  title   = {Foundations of modern query languages for graph databases},
  journal = {ACM Computing Surveys},
  volume  = {50},
  number  = {5},
  pages   = {1--40}, % UNVERIFIED: article number 68 (from recall)
  month   = sep,
  year    = {2017},
  doi     = {10.1145/3104031}
}

@inproceedings{S32_francis2018,
  author    = {N. Francis and A. Green and P. Guagliardo and L. Libkin and T. Lindaaker and V. Marsault and S. Plantikow and M. Rydberg and P. Selmer and A. Taylor},
  title     = {Cypher: An evolving query language for property graphs}, % Crossref holds only "Cypher"; subtitle from recall
  booktitle = {Proc. 2018 International Conference on Management of Data (SIGMOD '18)},
  pages     = {1433--1445},
  month     = may,
  year      = {2018},
  doi       = {10.1145/3183713.3190657}
}

@misc{S33_neo4jconcepts,
  author       = {{Neo4j, Inc.}},
  title        = {Graph database concepts},
  howpublished = {Neo4j Getting Started documentation},
  note         = {Accessed Nov. 17, 2026},
  url          = {https://neo4j.com/docs/getting-started/appendix/graphdb-concepts/}
}

@article{S34_schultz2019,
  author  = {W. Schultz and T. Avitabile and A. Cabral},
  title   = {Tunable consistency in {MongoDB}},
  journal = {Proceedings of the VLDB Endowment},
  volume  = {12},
  number  = {12},
  pages   = {2071--2081},
  month   = aug,
  year    = {2019},
  doi     = {10.14778/3352063.3352125}
}

@misc{S35_mongodbdocuments,
  author       = {{MongoDB, Inc.}},
  title        = {Documents},
  howpublished = {MongoDB Database Manual},
  note         = {Accessed Nov. 17, 2026},
  url          = {https://www.mongodb.com/docs/manual/core/document/}
}

% ---------- Area 4: MinHash and locality-sensitive hashing ----------

@inproceedings{L01_broder1997,
  author    = {A. Z. Broder},
  title     = {On the resemblance and containment of documents},
  booktitle = {Proc. Compression and Complexity of SEQUENCES 1997 (Cat. No.97TB100171)},
  publisher = {IEEE Computer Society},
  % address = {Salerno, Italy}, % UNVERIFIED: city
  year      = {1997}, % conference held 1997; UNVERIFIED: printed proceedings year (often cited as 1998; OpenAlex lists 2002)
  pages     = {21--29},
  doi       = {10.1109/SEQUEN.1997.666900}
}

@article{L02_broder1997web,
  author  = {A. Z. Broder and S. C. Glassman and M. S. Manasse and G. Zweig},
  title   = {Syntactic clustering of the {Web}},
  journal = {Computer Networks and ISDN Systems},
  volume  = {29},
  number  = {8-13},
  pages   = {1157--1166},
  month   = sep,
  year    = {1997},
  doi     = {10.1016/S0169-7552(97)00031-7},
  note    = {Proc. 6th Int. WWW Conf.}
}

@article{L03a_broder2000,
  author  = {A. Z. Broder and M. Charikar and A. M. Frieze and M. Mitzenmacher},
  title   = {Min-wise independent permutations},
  journal = {Journal of Computer and System Sciences},
  volume  = {60},
  number  = {3},
  pages   = {630--659},
  month   = jun,
  year    = {2000},
  doi     = {10.1006/jcss.1999.1690}
}

@inproceedings{L03b_broder1998,
  author    = {A. Z. Broder and M. Charikar and A. M. Frieze and M. Mitzenmacher},
  title     = {Min-wise independent permutations (extended abstract)},
  booktitle = {Proc. 30th ACM STOC},
  year      = {1998},
  pages     = {327--336},
  doi       = {10.1145/276698.276781}
}

@article{L03c_bohman2000,
  author  = {T. Bohman and C. Cooper and A. Frieze},
  title   = {Min-wise independent linear permutations},
  journal = {Electronic Journal of Combinatorics},
  volume  = {7},
  number  = {1},
  pages   = {R26},
  year    = {2000},
  doi     = {10.37236/1504}
}

@inproceedings{L04_indyk1998,
  author    = {P. Indyk and R. Motwani},
  title     = {Approximate nearest neighbors: towards removing the curse of dimensionality}, % Crossref title is truncated to "Approximate nearest neighbors"
  booktitle = {Proc. 30th ACM STOC},
  year      = {1998},
  pages     = {604--613},
  doi       = {10.1145/276698.276876}
}

@inproceedings{L05_gionis1999,
  author    = {A. Gionis and P. Indyk and R. Motwani},
  title     = {Similarity search in high dimensions via hashing},
  booktitle = {Proc. 25th Int. Conf. Very Large Data Bases (VLDB)},
  year      = {1999},
  pages     = {518--529} % page range rests on OpenAlex only; no DOI; UNVERIFIED: city (Edinburgh), publisher (Morgan Kaufmann), PDF URL
}

@inproceedings{L06_charikar2002,
  author    = {M. S. Charikar},
  title     = {Similarity estimation techniques from rounding algorithms},
  booktitle = {Proc. 34th ACM STOC},
  year      = {2002},
  pages     = {380--388},
  doi       = {10.1145/509907.509965}
}

@inproceedings{L07_datar2004,
  author    = {M. Datar and N. Immorlica and P. Indyk and V. S. Mirrokni},
  title     = {Locality-sensitive hashing scheme based on p-stable distributions},
  booktitle = {Proc. 20th Annual Symp. Computational Geometry (SoCG)},
  year      = {2004},
  pages     = {253--262},
  doi       = {10.1145/997817.997857}
}

@article{L08_andoni2008,
  author  = {A. Andoni and P. Indyk},
  title   = {Near-optimal hashing algorithms for approximate nearest neighbor in high dimensions},
  journal = {Communications of the ACM},
  volume  = {51},
  number  = {1},
  pages   = {117--122},
  month   = jan,
  year    = {2008},
  doi     = {10.1145/1327452.1327494}
}

@inproceedings{L09_henzinger2006,
  author    = {M. Henzinger},
  title     = {Finding near-duplicate web pages: a large-scale evaluation of algorithms},
  booktitle = {Proc. 29th Annual Int. ACM SIGIR Conf.},
  year      = {2006},
  pages     = {284--291},
  doi       = {10.1145/1148170.1148222}
}

@inproceedings{L10_manku2007,
  author    = {G. S. Manku and A. Jain and A. Das Sarma},
  title     = {Detecting near-duplicates for web crawling},
  booktitle = {Proc. 16th Int. Conf. World Wide Web (WWW)},
  year      = {2007},
  pages     = {141--150},
  doi       = {10.1145/1242572.1242592}
}

% L11 is chapter 3 of S12_leskovec2020 (same book).

@inproceedings{L12a_li2010,
  author    = {P. Li and A. C. K{\"o}nig},
  title     = {b-Bit minwise hashing},
  booktitle = {Proc. 19th Int. Conf. World Wide Web (WWW)},
  year      = {2010},
  pages     = {671--680},
  doi       = {10.1145/1772690.1772759},
  note      = {Preprint arXiv:0910.3349}
}

@article{L12b_li2011,
  author  = {P. Li and A. C. K{\"o}nig},
  title   = {Theory and applications of b-bit minwise hashing},
  journal = {Communications of the ACM},
  volume  = {54},
  number  = {8},
  pages   = {101--109},
  month   = aug,
  year    = {2011},
  doi     = {10.1145/1978542.1978566}
}

@inproceedings{L13_li2012,
  author    = {P. Li and A. Owen and C.-H. Zhang},
  title     = {One permutation hashing},
  booktitle = {Advances in Neural Information Processing Systems 25 (NIPS 2012)},
  year      = {2012},
  url       = {https://papers.nips.cc/paper/2012/hash/eaa32c96f620053cf442ad32258076b9-Abstract.html},
  note      = {Preprint arXiv:1208.1259} % no DOI; UNVERIFIED: page numbers
}

@inproceedings{L14_bawa2005,
  author    = {M. Bawa and T. Condie and P. Ganesan},
  title     = {{LSH} forest: self-tuning indexes for similarity search},
  booktitle = {Proc. 14th Int. Conf. World Wide Web (WWW)},
  year      = {2005},
  pages     = {651}, % UNVERIFIED: end page (commonly cited as 651-660)
  doi       = {10.1145/1060745.1060840}
}

@inproceedings{L15_das2007,
  author    = {A. S. Das and M. Datar and A. Garg and S. Rajaram},
  title     = {Google news personalization: scalable online collaborative filtering},
  booktitle = {Proc. 16th Int. Conf. World Wide Web (WWW)},
  year      = {2007},
  pages     = {271--280},
  doi       = {10.1145/1242572.1242610}
}

@inproceedings{L16_shrivastava2014,
  author    = {A. Shrivastava and P. Li},
  title     = {In defense of {MinHash} over {SimHash}},
  booktitle = {Proc. 17th Int. Conf. Artificial Intelligence and Statistics (AISTATS)},
  series    = {PMLR},
  volume    = {33},
  pages     = {886--894},
  year      = {2014},
  url       = {https://proceedings.mlr.press/v33/shrivastava14.html}
}

@misc{L17_sparklshguide,
  author       = {{Apache Software Foundation}},
  title        = {Extracting, transforming and selecting features --- Locality Sensitive Hashing},
  howpublished = {Apache Spark 4.3.0 MLlib Guide},
  note         = {Accessed 2026-11-17},
  url          = {https://spark.apache.org/docs/latest/ml-features.html#locality-sensitive-hashing}
}

@misc{L17b_wang2014,
  author       = {J. Wang and H. T. Shen and J. Song and J. Ji},
  title        = {Hashing for similarity search: A survey},
  howpublished = {arXiv:1408.2927},
  year         = {2014},
  url          = {https://arxiv.org/abs/1408.2927} % cited in the Spark BucketedRandomProjectionLSH source comment
}

@incollection{L18_potthast2008,
  author    = {M. Potthast and B. Stein},
  title     = {New issues in near-duplicate detection},
  booktitle = {Data Analysis, Machine Learning and Applications},
  series    = {Studies in Classification, Data Analysis, and Knowledge Organization},
  publisher = {Springer},
  address   = {Berlin, Heidelberg},
  year      = {2008},
  pages     = {601--609},
  doi       = {10.1007/978-3-540-78246-9_71}
}

@inproceedings{L19_weissman2015,
  author    = {S. Weissman and S. Ayhan and J. Bradley and J. Lin},
  title     = {Identifying duplicate and contradictory information in {Wikipedia}},
  booktitle = {Proc. 15th ACM/IEEE-CS Joint Conf. Digital Libraries (JCDL)},
  year      = {2015},
  pages     = {57--60},
  doi       = {10.1145/2756406.2756947},
  note      = {Preprint arXiv:1406.1143}
}

@incollection{L20_alshomary2019,
  author    = {M. Alshomary and M. V{\"o}lske and T. Licht and H. Wachsmuth and B. Stein and M. Hagen and M. Potthast},
  title     = {{Wikipedia} text reuse: within and without},
  booktitle = {Advances in Information Retrieval (ECIR 2019)},
  series    = {Lecture Notes in Computer Science},
  % volume  = {11437}, % UNVERIFIED: volume number (recalled)
  publisher = {Springer},
  year      = {2019},
  pages     = {747--754},
  doi       = {10.1007/978-3-030-15712-8_49},
  note      = {Preprint arXiv:1812.09221}
}

% L21 is W01_flock2012 (same paper).

@inproceedings{L22_ekstrand2009,
  author    = {M. D. Ekstrand and J. T. Riedl},
  title     = {rv you're dumb: identifying discarded work in {Wiki} article history},
  booktitle = {Proc. 5th Int. Symp. Wikis and Open Collaboration (WikiSym)},
  year      = {2009},
  pages     = {1--10}, % article-numbered
  doi       = {10.1145/1641309.1641317}
}

@inproceedings{L23_petrovic2010,
  author    = {S. Petrovi{\'c} and M. Osborne and V. Lavrenko},
  title     = {Streaming first story detection with application to {Twitter}},
  booktitle = {Proc. HLT-NAACL 2010},
  address   = {Los Angeles},
  publisher = {ACL},
  year      = {2010},
  pages     = {181--189},
  url       = {https://aclanthology.org/N10-1021/}
}

@inproceedings{L24_xiao2008,
  author    = {C. Xiao and W. Wang and X. Lin and J. X. Yu},
  title     = {Efficient similarity joins for near duplicate detection},
  booktitle = {Proc. 17th Int. Conf. World Wide Web (WWW)},
  year      = {2008},
  pages     = {131--140}, % the notes give the same range for L25; check both
  doi       = {10.1145/1367497.1367516}
}

@inproceedings{L25_bayardo2007,
  author    = {R. J. Bayardo and Y. Ma and R. Srikant},
  title     = {Scaling up all pairs similarity search},
  booktitle = {Proc. 16th Int. Conf. World Wide Web (WWW)},
  year      = {2007},
  pages     = {131--140}, % the notes give the same range for L24; check both
  doi       = {10.1145/1242572.1242591}
}

% ---------- Area 5: privacy techniques and Wikimedia privacy ----------

@techreport{P01_samarati1998,
  author      = {P. Samarati and L. Sweeney},
  title       = {Protecting privacy when disclosing information: k-anonymity and its enforcement through generalization and suppression},
  institution = {Computer Science Laboratory, SRI International},
  address     = {Menlo Park, CA},
  number      = {SRI-CSL-98-04},
  year        = {1998},
  url         = {https://www.csl.sri.com/papers/sritr-98-04} % cite the SRI record; UNVERIFIED: any IEEE S&P 1998 version
}

@article{P02_samarati2001,
  author  = {P. Samarati},
  title   = {Protecting respondents' identities in microdata release}, % Crossref prints the title without the apostrophe
  journal = {IEEE Trans. Knowl. Data Eng.},
  volume  = {13},
  number  = {6},
  pages   = {1010--1027},
  year    = {2001}, % UNVERIFIED: issue month (Nov./Dec.)
  doi     = {10.1109/69.971193}
}

@article{P03_sweeney2002,
  author  = {L. Sweeney},
  title   = {k-anonymity: A model for protecting privacy},
  journal = {Int. J. Uncertainty, Fuzziness and Knowledge-Based Systems},
  volume  = {10},
  number  = {5},
  pages   = {557--570},
  month   = oct,
  year    = {2002},
  doi     = {10.1142/S0218488502001648}
}

@techreport{P04_sweeney2000,
  author      = {L. Sweeney},
  title       = {Simple demographics often identify people uniquely},
  institution = {Carnegie Mellon University},
  address     = {Pittsburgh, PA},
  type        = {Data Privacy Working Paper},
  number      = {3},
  year        = {2000},
  url         = {https://dataprivacylab.org/projects/identifiability/}
}

@article{P05a_machanavajjhala2007,
  author  = {A. Machanavajjhala and D. Kifer and J. Gehrke and M. Venkitasubramaniam},
  title   = {l-diversity: Privacy beyond k-anonymity},
  journal = {ACM Trans. Knowl. Discov. Data},
  volume  = {1},
  number  = {1},
  month   = mar,
  year    = {2007},
  doi     = {10.1145/1217299.1217302},
  note    = {Art. 3}
}

@inproceedings{P05b_machanavajjhala2006,
  author    = {A. Machanavajjhala and J. Gehrke and D. Kifer and M. Venkitasubramaniam}, % author order differs from the journal version
  title     = {l-diversity: Privacy beyond k-anonymity},
  booktitle = {Proc. 22nd Int. Conf. Data Engineering (ICDE)},
  year      = {2006},
  pages     = {24},
  doi       = {10.1109/ICDE.2006.1}
}

@inproceedings{P06_li2007,
  author    = {N. Li and T. Li and S. Venkatasubramanian},
  title     = {t-closeness: Privacy beyond k-anonymity and l-diversity},
  booktitle = {Proc. IEEE 23rd Int. Conf. Data Engineering (ICDE)},
  % address = {Istanbul, Turkey}, % UNVERIFIED: conference city
  month     = apr,
  year      = {2007},
  pages     = {106--115},
  doi       = {10.1109/ICDE.2007.367856}
}

@inproceedings{P07_lefevre2006,
  author    = {K. LeFevre and D. J. DeWitt and R. Ramakrishnan},
  title     = {Mondrian multidimensional k-anonymity},
  booktitle = {Proc. 22nd Int. Conf. Data Engineering (ICDE)},
  % address = {Atlanta, GA}, month = apr, % UNVERIFIED: city and month
  year      = {2006},
  pages     = {25},
  doi       = {10.1109/ICDE.2006.101}
}

@inproceedings{P08_meyerson2004,
  author    = {A. Meyerson and R. Williams},
  title     = {On the complexity of optimal k-anonymity},
  booktitle = {Proc. 23rd ACM SIGMOD-SIGACT-SIGART Symp. Principles of Database Systems (PODS)},
  % address = {Paris, France}, % UNVERIFIED: city
  month     = jun,
  year      = {2004},
  pages     = {223--228},
  doi       = {10.1145/1055558.1055591}
}

@inproceedings{P09_bayardo2005,
  author    = {R. J. Bayardo and R. Agrawal},
  title     = {Data privacy through optimal k-anonymization},
  booktitle = {Proc. 21st Int. Conf. Data Engineering (ICDE)},
  % address = {Tokyo, Japan}, month = apr, % UNVERIFIED: city and month
  year      = {2005},
  pages     = {217--228},
  doi       = {10.1109/ICDE.2005.42}
}

@incollection{P10_dwork2006calibrating,
  author    = {C. Dwork and F. McSherry and K. Nissim and A. Smith},
  title     = {Calibrating noise to sensitivity in private data analysis},
  booktitle = {Theory of Cryptography (TCC 2006)},
  series    = {Lecture Notes in Computer Science},
  volume    = {3876}, % UNVERIFIED: volume number
  publisher = {Springer},
  address   = {Berlin, Germany},
  year      = {2006},
  pages     = {265--284},
  doi       = {10.1007/11681878_14}
}

@incollection{P11_dwork2006dp,
  author    = {C. Dwork},
  title     = {Differential privacy},
  booktitle = {Automata, Languages and Programming (ICALP 2006), Part II}, % UNVERIFIED: "Part II"
  series    = {Lecture Notes in Computer Science},
  volume    = {4052}, % UNVERIFIED: volume number
  publisher = {Springer},
  address   = {Berlin, Germany},
  year      = {2006},
  pages     = {1--12},
  doi       = {10.1007/11787006_1}
}

@article{P12_dwork2014,
  author  = {C. Dwork and A. Roth},
  title   = {The algorithmic foundations of differential privacy},
  journal = {Foundations and Trends in Theoretical Computer Science},
  volume  = {9},
  number  = {3-4},
  pages   = {211--407}, % UNVERIFIED: Crossref gives 211-487; the commonly cited range is 211-407; check the publisher page
  month   = aug,
  year    = {2014},
  doi     = {10.1561/0400000042}
}

@inproceedings{P13_dwork2010,
  author    = {C. Dwork and M. Naor and T. Pitassi and G. N. Rothblum},
  title     = {Differential privacy under continual observation},
  booktitle = {Proc. 42nd ACM Symp. Theory of Computing (STOC)},
  % address = {Cambridge, MA}, % UNVERIFIED: city
  month     = jun,
  year      = {2010},
  pages     = {715--724},
  doi       = {10.1145/1806689.1806787}
}

@article{P14_chan2011,
  author  = {T.-H. H. Chan and E. Shi and D. Song},
  title   = {Private and continual release of statistics},
  journal = {ACM Trans. Inf. Syst. Secur.},
  volume  = {14},
  number  = {3},
  pages   = {1--24}, % UNVERIFIED: article number 26
  month   = nov,
  year    = {2011},
  doi     = {10.1145/2043621.2043626}
}

@inproceedings{P15_erlingsson2014,
  author    = {{\'U}. Erlingsson and V. Pihur and A. Korolova},
  title     = {{RAPPOR}: Randomized aggregatable privacy-preserving ordinal response}, % UNVERIFIED: full subtitle (Crossref stores only "RAPPOR")
  booktitle = {Proc. 2014 ACM SIGSAC Conf. Computer and Communications Security (CCS)},
  % address = {Scottsdale, AZ}, % UNVERIFIED: city
  month     = nov,
  year      = {2014},
  pages     = {1054--1067},
  doi       = {10.1145/2660267.2660348}
}

@inproceedings{P16_narayanan2008,
  author    = {A. Narayanan and V. Shmatikov},
  title     = {Robust de-anonymization of large sparse datasets},
  booktitle = {Proc. 2008 IEEE Symp. Security and Privacy (S\&P)},
  % address = {Oakland, CA}, % UNVERIFIED: city
  month     = may,
  year      = {2008},
  pages     = {111--125},
  doi       = {10.1109/SP.2008.33},
  note      = {Preprint arXiv:cs/0610105}
}

@misc{P17_adeleye2023,
  author       = {T. Adeleye and S. Berghel and D. Desfontaines and M. Hay and I. Johnson and C. Lemoisson and A. Machanavajjhala and T. Magerlein and G. Modena and D. Pujol and D. Simmons-Marengo and H. Triedman},
  title        = {Publishing {Wikipedia} usage data with strong privacy guarantees},
  howpublished = {arXiv:2308.16298},
  month        = aug,
  year         = {2023},
  doi          = {10.48550/arXiv.2308.16298},
  note         = {v3, Jul. 2025. Presented at Theory and Practice of Differential Privacy (TPDP) 2023}
}

@article{P18_demontjoye2013,
  author  = {Y.-A. de Montjoye and C. A. Hidalgo and M. Verleysen and V. D. Blondel},
  title   = {Unique in the crowd: The privacy bounds of human mobility},
  journal = {Scientific Reports},
  volume  = {3},
  pages   = {1376},
  month   = mar,
  year    = {2013},
  doi     = {10.1038/srep01376}
}

@misc{P19a_wmfdp,
  author       = {{Wikimedia Foundation}},
  title        = {Differential privacy},
  howpublished = {Meta-Wiki},
  note         = {Last edited 29 Oct. 2024; accessed 17 Nov. 2026},
  url          = {https://meta.wikimedia.org/wiki/Differential_privacy}
}

@misc{P19b_wmfgeoeditors,
  author       = {{Wikimedia Foundation}},
  title        = {Differential privacy/Completed/Geoeditors/Feasibility report},
  howpublished = {Meta-Wiki},
  note         = {Last edited 29 Aug. 2023},
  url          = {https://meta.wikimedia.org/wiki/Differential_privacy/Completed/Geoeditors/Feasibility_report}
}

@misc{P20a_wmfprivacypolicy,
  author       = {{Wikimedia Foundation}},
  title        = {Privacy Policy},
  howpublished = {Wikimedia Foundation Governance Wiki},
  note         = {Version approved 3 Sep. 2025, effective 6 Oct. 2025; accessed 17 Nov. 2026},
  url          = {https://foundation.wikimedia.org/wiki/Policy:Privacy_policy}
}

@misc{P20b_wmfretention,
  author       = {{Wikimedia Foundation}},
  title        = {Data Retention Guidelines},
  howpublished = {Wikimedia Foundation Governance Wiki},
  note         = {Last edited 20 Feb. 2026},
  url          = {https://foundation.wikimedia.org/wiki/Legal:Data_retention_guidelines}
}

@misc{P21_wmfipaccess,
  author       = {{Wikimedia Foundation}},
  title        = {Wikimedia Access to Temporary Account {IP} Addresses Policy},
  howpublished = {Wikimedia Foundation Governance Wiki},
  note         = {Last edited 1 Apr. 2026},
  url          = {https://foundation.wikimedia.org/wiki/Policy:Wikimedia_Access_to_Temporary_Account_IP_Addresses_Policy}
}

@inproceedings{P22_rizoiu2016,
  author    = {M.-A. Rizoiu and L. Xie and T. Caetano and M. Cebrian},
  title     = {Evolution of privacy loss in {Wikipedia}},
  booktitle = {Proc. 9th ACM Int. Conf. Web Search and Data Mining (WSDM)},
  % address = {San Francisco, CA}, % UNVERIFIED: city
  month     = feb,
  year      = {2016},
  pages     = {215--224},
  doi       = {10.1145/2835776.2835798},
  note      = {Preprint arXiv:1512.03523}
}

@inproceedings{P23_ganta2008,
  author    = {S. R. Ganta and S. P. Kasiviswanathan and A. Smith},
  title     = {Composition attacks and auxiliary information in data privacy},
  booktitle = {Proc. 14th ACM SIGKDD Int. Conf. Knowledge Discovery and Data Mining (KDD)},
  % address = {Las Vegas, NV}, % UNVERIFIED: city
  month     = aug,
  year      = {2008},
  pages     = {265--273},
  doi       = {10.1145/1401890.1401926}
}
```
