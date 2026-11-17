# Delayed labels (verification latency) in data streams, and label completeness as a function of waiting time

Researched 2026-11-17. How to read this file:

- "Confirmed on" = the page I actually opened for the bibliographic record. Most records were checked against the Crossref DOI registry record (`https://api.crossref.org/works/<DOI>`); abstracts were read from the OpenAlex record of the same DOI (`https://api.openalex.org/works/https://doi.org/<DOI>`), which carries the publisher abstract. Three papers were read in full text (Geiger and Halfaker 2013; Viégas et al. 2004; Joulani et al. 2013 abstract page on PMLR).
- "Abstract-level" means the bullets come from the abstract only; I did not read the body. Anything I could not confirm is marked `UNVERIFIED:`.
- All bullets are paraphrases. S-numbers are local to this file, not IEEE reference numbers.
- Already in the report's reference list (report_draft.md lines 334-341) and re-verified here: [10] Croushore and Stark = S20, [11] Aruoba = S21, [12] Höhle and an der Heiden = S17, [15] Priedhorsky et al. = S25, [17] Geiger and Halfaker = S26. All five exist with the details the draft gives; corrections and added details are noted in each entry. [16], [18], [19] are outside this topic (Flöck et al. [18] was confirmed to exist in passing: Proc. 23rd ACM Conf. Hypertext and Social Media, 2012, pp. 3-12, DOI 10.1145/2309996.2310000).

## Key question 1: Founding and survey papers on delayed labels / verification latency in stream learning

### Takeaway
The stream-learning literature has treated delayed labels since 2008-2010 as a problem for the learner (what to do while the label is missing, how to evaluate a classifier fairly), and all named papers exist. In the abstracts checked, none of them measures the empirical distribution of the label delay itself in a real system; the delay is an input (fixed, simulated, or "never arrives").

### Cited Findings

**S1. Kuncheva and Sánchez 2008**
- L. I. Kuncheva and J. S. Sánchez, "Nearest Neighbour Classifiers for Streaming Data with Delayed Labelling," in Proc. 2008 Eighth IEEE International Conference on Data Mining (ICDM), Dec. 2008, pp. 869-874. DOI: 10.1109/ICDM.2008.33. Confirmed on: [Crossref](https://api.crossref.org/works/10.1109/ICDM.2008.33); abstract via [OpenAlex](https://api.openalex.org/works/https://doi.org/10.1109/ICDM.2008.33).
- Studies streams where the true label arrives after a delay, and asks whether an online nearest-neighbour classifier (IB2, IB3) should use the still-unlabelled points. (Abstract-level.)
- Compares three strategies for the unlabelled points: do nothing, replace, forget.
- Experiments on 28 data sets: IB2 gains from using unlabelled data, IB3 does not.
- Relation to revert-label delay: an early statement of the setting TruthLag measures (label arrives later than the item); the delay here is an assumed condition, not a measured quantity.

**S2. Žliobaitė 2010**
- I. Žliobaitė, "Change with Delayed Labeling: When is it Detectable?," in Proc. 2010 IEEE International Conference on Data Mining Workshops (ICDMW), Dec. 2010, pp. 843-850. DOI: 10.1109/ICDMW.2010.49. Confirmed on: [Crossref](https://api.crossref.org/works/10.1109/ICDMW.2010.49); abstract via [OpenAlex](https://api.openalex.org/works/https://doi.org/10.1109/ICDMW.2010.49).
- States that most adaptive learners assume new labels are available immediately, and that this is often unrealistic because of task-specific labelling delay or labelling cost. (Abstract-level.)
- Analyses, from a probabilistic view, which kinds of change can be detected without the labels and which cannot.
- Proposes a low-cost detector that monitors the stream of classifier outputs; tested on real data with simulated and natural changes.
- Relation to revert-label delay: explains why the period before labels arrive matters (some changes are invisible until labels come); gives no measurement of how long that period is.

**S3. Marrs, Hickey and Black 2010**
- G. R. Marrs, R. J. Hickey, and M. M. Black, "The Impact of Latency on Online Classification Learning with Concept Drift," in Knowledge Science, Engineering and Management (KSEM 2010), Lecture Notes in Computer Science, Springer, 2010, pp. 459-469. DOI: 10.1007/978-3-642-15280-1_42. Confirmed on: [Crossref](https://api.crossref.org/works/10.1007/978-3-642-15280-1_42) (authors, title, LNCS, pages, year).
- UNVERIFIED: LNCS volume number (I believe 6291) and the conference name KSEM 2010; Crossref shows only "Lecture Notes in Computer Science".
- UNVERIFIED: abstract and findings. No abstract was available on Crossref or OpenAlex and the Springer page required login. It is commonly cited as an early source for "latency" between classification and label arrival; check the paper before stating that it coined "verification latency".
- Relation to revert-label delay: title-level relevance only (effect of label latency on online learning under drift).

**S4. Plasse and Adams 2016**
- J. Plasse and N. Adams, "Handling delayed labels in temporally evolving data streams," in Proc. 2016 IEEE International Conference on Big Data (Big Data), Dec. 2016, pp. 2416-2424. DOI: 10.1109/BigData.2016.7840877. Confirmed on: [Crossref search record](https://api.crossref.org/works/10.1109/bigdata.2016.7840877); abstract via [OpenAlex](https://api.openalex.org/works/https://doi.org/10.1109/BigData.2016.7840877).
- Says that in real applications labels for earlier feature vectors may arrive only after an appreciable lag, and that this is not properly addressed in the literature. (Abstract-level.)
- Contributes a taxonomy of delayed labelling and a framework for folding late labels into a streaming classifier.
- Real-data demonstration with a temporally adaptive linear classifier: handling delayed labels correctly raised performance. No numbers in the abstract.
- Relation to revert-label delay: its taxonomy of delay types is the natural place to position revert labels (delay is random, per-item, and only the positive class "arrives"). UNVERIFIED: the taxonomy's category names; I did not read the body.

**S5. Souza, Silva, Gama and Batista 2015**
- V. M. A. Souza, D. F. Silva, J. Gama, and G. E. A. P. A. Batista, "Data Stream Classification Guided by Clustering on Nonstationary Environments and Extreme Verification Latency," in Proc. 2015 SIAM International Conference on Data Mining (SDM), Jun. 2015, pp. 873-881. DOI: 10.1137/1.9781611974010.98. Confirmed on: [Crossref](https://api.crossref.org/works/10.1137/1.9781611974010.98); abstract via [OpenAlex](https://api.openalex.org/works/https://doi.org/10.1137/1.9781611974010.98).
- Defines extreme verification latency as the case where the true labels of processed data never become available. (Abstract-level.)
- Proposes SCARGC, a repeated clustering-then-classification loop that adapts without external supervision.
- Reports it is faster and more accurate than the prior state of the art on synthetic and real data. No numbers in the abstract.
- Relation to revert-label delay: marks the far end of the delay scale (infinite delay). Revert labels sit in between: finite but heavy-tailed delay.
- Companion paper by the same group (confirmed on [Crossref search](https://api.crossref.org/works/10.1109/icmla.2015.174)): V. M. A. Souza, D. F. Silva, G. E. A. P. A. Batista, and J. Gama, "Classification of Evolving Data Streams with Infinitely Delayed Labels," in Proc. 2015 IEEE 14th Int. Conf. Machine Learning and Applications (ICMLA), Dec. 2015, pp. 214-219, DOI 10.1109/ICMLA.2015.174.

**S6. Souza, Pinho and Batista 2018**
- V. Souza, T. Pinho, and G. Batista, "Evaluating Stream Classifiers with Delayed Labels Information," in Proc. 2018 7th Brazilian Conference on Intelligent Systems (BRACIS), Oct. 2018, pp. 408-413. DOI: 10.1109/BRACIS.2018.00077. Confirmed on: [Crossref](https://api.crossref.org/works/10.1109/BRACIS.2018.00077); abstract via [OpenAlex](https://api.openalex.org/works/https://doi.org/10.1109/BRACIS.2018.00077). (OpenAlex spells the second author "Tiago Pinho da Silva".)
- Calls the assumption of immediate labels very optimistic for most applications. (Abstract-level.)
- Measures experimentally how latency changes stream-classifier performance and warns that ignoring it biases conclusions.
- Proposes an evaluation measure, Kappa-Latency, that accounts for the arrival delay of true labels.
- Relation to revert-label delay: argues that the delay must be a reported variable in evaluation; TruthLag reports that variable for one real label.

**S7. Grzenda, Gomes and Bifet 2020**
- M. Grzenda, H. M. Gomes, and A. Bifet, "Delayed labelling evaluation for data streams," Data Mining and Knowledge Discovery, vol. 34, no. 5, pp. 1237-1266, 2020 (published online 16 Nov. 2019). DOI: 10.1007/s10618-019-00654-y. Confirmed on: [Crossref](https://api.crossref.org/works/10.1007/s10618-019-00654-y) (includes abstract). Open-access copy listed by OpenAlex at link.springer.com and hal.science/hal-04468430 (both blocked automated reading).
- Notes that test-then-train evaluation assumes the true label arrives right after the prediction, while in many real cases labels arrive with non-negligible latency. (Abstract-level.)
- Proposes "continuous re-evaluation": evaluate how a model's prediction for an instance changes between the instance's arrival and the arrival of its true label.
- Uses it to separate stream methods by their ability to refine predictions as new instances arrive.
- UNVERIFIED: data sets and delay lengths used (full text not read).
- Relation to revert-label delay: closest methodological relative. It evaluates predictions during the waiting period; TruthLag measures how incomplete the label itself is during the same period.

**S8. Gomes, Read, Bifet, Barddal and Gama 2019**
- H. M. Gomes, J. Read, A. Bifet, J. P. Barddal, and J. Gama, "Machine learning for streaming data: state of the art, challenges, and opportunities," ACM SIGKDD Explorations Newsletter, vol. 21, no. 2, pp. 6-22, Nov. 2019. DOI: 10.1145/3373464.3373470. Confirmed on: [Crossref](https://api.crossref.org/works/10.1145/3373464.3373470) (includes abstract; Crossref title stops at "Machine learning for streaming data").
- Position/survey paper on open challenges in stream learning in academia and industry, covering topics earlier surveys treated lightly. (Abstract-level.)
- UNVERIFIED: that the body has a dedicated discussion of delayed labels / label availability. I believe it does, but the abstract does not say so; check before citing it for that point.
- Relation to revert-label delay: general survey to cite for "immediate labels are a common but unrealistic assumption" only after the body is checked.

**S9. Gomes, Grzenda, Mello, Read, Le Nguyen and Bifet 2022**
- H. M. Gomes, M. Grzenda, R. Mello, J. Read, M. H. Le Nguyen, and A. Bifet, "A Survey on Semi-supervised Learning for Delayed Partially Labelled Data Streams," ACM Computing Surveys, vol. 55, no. 4, pp. 1-42, Nov. 2022. DOI: 10.1145/3523055. Confirmed on: [Crossref search record](https://api.crossref.org/works/10.1145/3523055) and [arXiv:2106.09170](https://arxiv.org/abs/2106.09170).
- UNVERIFIED: article number within vol. 55 no. 4 (Crossref gives only pp. 1-42).
- Surveys methods that use unlabelled stream data; treats delayed labelling as an issue affecting both fully supervised and semi-supervised methods. (Abstract-level.)
- Proposes a unified problem setting and reviews benchmarking practice, with proposed changes.
- Relation to revert-label delay: the most recent survey that names delayed labelling as a core stream problem; suitable as the survey citation for the setting.

**S10. Gama, Žliobaitė, Bifet, Pechenizkiy and Bouchachia 2014**
- J. Gama, I. Žliobaitė, A. Bifet, M. Pechenizkiy, and A. Bouchachia, "A survey on concept drift adaptation," ACM Computing Surveys, vol. 46, no. 4, pp. 1-37, Mar. 2014. DOI: 10.1145/2523813. Confirmed on: [Crossref](https://api.crossref.org/works/10.1145/2523813) (includes abstract).
- UNVERIFIED: article number (commonly cited as Article 44).
- Defines concept drift as a change over time in the relation between input data and target; categorises adaptation strategies and discusses evaluation methodology. (Abstract-level.)
- UNVERIFIED: what the body says about delayed feedback; the abstract does not mention it.
- Relation to revert-label delay: background citation for stream learning and evaluation; not a delayed-label source on the evidence of its abstract.

**S11. Dyer, Capo and Polikar 2014**
- K. B. Dyer, R. Capo, and R. Polikar, "COMPOSE: A Semisupervised Learning Framework for Initially Labeled Nonstationary Streaming Data," IEEE Transactions on Neural Networks and Learning Systems, vol. 25, no. 1, pp. 12-26, Jan. 2014. DOI: 10.1109/TNNLS.2013.2277712. Confirmed on: [Crossref](https://api.crossref.org/works/10.1109/TNNLS.2013.2277712); abstract via [OpenAlex](https://api.openalex.org/works/https://doi.org/10.1109/TNNLS.2013.2277712).
- Learns from streams where labels are unavailable (or very sporadic) after an initial labelled set. (Abstract-level.)
- The abstract refers to this setting as "extreme verification latency" and compares against the arbitrary subpopulation tracker algorithm.
- On NOAA weather data it is reported as competitive with a fully supervised learner that gets labels in every batch.
- Relation to revert-label delay: second source for the term "extreme verification latency"; optional.

### Inferences
- The stream-learning papers S1-S11 take the delay as given and ask what a learner or evaluator should do; on abstract evidence none reports an empirical delay distribution or a completeness-versus-wait curve for a real labelling process.
- "Verification latency" (S5, S11, S22) and "delayed labels/labelling" (S1, S2, S4, S6, S7, S9) are used for the same thing; the report should pick one and note the synonym.

### Gaps
- Origin of the term "verification latency": not confirmed. Marrs et al. (S3) could not be read.
- Body-level facts for S3, S4, S7, S8, S10 were not read (paywall or bot blocks).
- DBLP was not reachable from this session (its API returned a non-JSON response), so DBLP was not used as a check.

## Key question 2: Delayed-feedback literature in online advertising and online learning

### Takeaway
Advertising work models the delay between an impression/click and its conversion explicitly, because a not-yet-converted item looks like a negative; this is the same one-sided label problem as "not yet reverted". Online-learning theory gives regret bounds under delay.

### Cited Findings

**S12. Chapelle 2014**
- O. Chapelle, "Modeling delayed feedback in display advertising," in Proc. 20th ACM SIGKDD International Conference on Knowledge Discovery and Data Mining (KDD '14), Aug. 2014, pp. 1097-1105. DOI: 10.1145/2623330.2623634. Confirmed on: [Crossref](https://api.crossref.org/works/10.1145/2623330.2623634); abstract via [OpenAlex](https://api.openalex.org/works/https://doi.org/10.1145/2623330.2623634).
- Conversions can occur long after the impression, "up to a month", which hinders conversion modelling. (Abstract-level.)
- Adds a second model for the conversion delay; an unconverted user is treated as a negative only when the elapsed time exceeds the predicted delay, and is otherwise left out as too early to tell.
- Evaluated on real traffic logs. UNVERIFIED: the share of conversions arriving within given waits, and the exponential form of the delay model (the latter is reported only second-hand in search-result summaries of later papers; I could not open the full text).
- Relation to revert-label delay: direct analogue. "Not converted yet" = "not reverted yet"; both are right-censored positives. Chapelle models the delay to fix training; TruthLag reports the delay curve itself.

**S13. Ktena et al. 2019**
- S. I. Ktena, A. Tejani, L. Theis, P. K. Myana, D. Dilipkumar, F. Huszár, S. Yoo, and W. Shi, "Addressing delayed feedback for continuous training with neural networks in CTR prediction," in Proc. 13th ACM Conference on Recommender Systems (RecSys '19), Sep. 2019, pp. 187-195. DOI: 10.1145/3298689.3347002. Confirmed on: [Crossref](https://api.crossref.org/works/10.1145/3298689.3347002) and [arXiv:1907.06558](https://arxiv.org/abs/1907.06558).
- In continuous training, fresh data may lack complete labels when ingested; treating every item as negative until a positive arrives underestimates click-through rate. (Abstract-level.)
- Compares 5 loss functions, 3 of them new to this problem.
- Offline, on 668 million in-house data points, the proposed methods beat the earlier state of the art by 3% relative cross entropy; online, a 55% gain in revenue per thousand requests against naive log loss.
- Relation to revert-label delay: documents the cost of the "count it as negative until told otherwise" rule, which is what a live revert count does at short waits. (Neural-network paper, included because it is specifically about delayed labels.)

**S14. Joulani, György and Szepesvári 2013**
- P. Joulani, A. György, and C. Szepesvári, "Online Learning under Delayed Feedback," in Proc. 30th International Conference on Machine Learning (ICML), Proceedings of Machine Learning Research, vol. 28, no. 3, pp. 1453-1461, 2013. Stable URL and confirmed on: [PMLR](https://proceedings.mlr.press/v28/joulani13.html). No DOI.
- Shows that delay raises regret multiplicatively in adversarial problems and additively in stochastic problems.
- Gives black-box meta-algorithms that turn a non-delayed algorithm into one that handles delayed feedback.
- Gives modified UCB bandit algorithms for delayed feedback with lower complexity than the meta-algorithms.
- Relation to revert-label delay: theory for how much delay costs a learner; needs the delay distribution as input, which is what TruthLag measures for one label.

**S15 (optional, earlier theory). Mesterharm 2005; Weinberger and Ordentlich 2002**
- C. Mesterharm, "On-line Learning with Delayed Label Feedback," in Lecture Notes in Computer Science, Springer, 2005, pp. 399-413. DOI: 10.1007/11564089_31. Confirmed on: [Crossref search record](https://api.crossref.org/works/10.1007/11564089_31). UNVERIFIED: host conference (I believe Algorithmic Learning Theory, ALT 2005) and LNCS volume; abstract not available.
- M. J. Weinberger and E. Ordentlich, "On delayed prediction of individual sequences," IEEE Transactions on Information Theory, vol. 48, no. 7, pp. 1959-1976, Jul. 2002. DOI: 10.1109/TIT.2002.1013136. Confirmed on: [Crossref search record](https://api.crossref.org/works/10.1109/tit.2002.1013136). UNVERIFIED: findings (abstract not read).
- Relation to revert-label delay: show the delayed-feedback question predates the stream-mining papers; cite only if the survey needs the earlier theory.

### Inferences
- Advertising papers and the revert label share a structure the generic stream papers lack: only the positive label "arrives"; a negative is never confirmed, it is only inferred from enough waiting. A follow-up window (30 days in advertising attribution per S12's "up to a month"; 4 days in TruthLag) is therefore part of the label's definition.

### Gaps
- Chapelle's delay statistics (share of conversions by wait) could not be read; no open copy was reachable.
- Not verified here: Yoshikawa and Imai, "A Nonparametric Delayed Feedback Model for Conversion Rate Prediction" (arXiv:1802.00255 exists as an identifier; title and authors were not confirmed on a page I could read). Do not cite without checking.

## Key question 3: The same problem in statistics: right-censoring, reporting delay, nowcasting, data vintages

### Takeaway
Statistics has three established framings that match E(L): the survival function with censored observations (Kaplan-Meier), occurred-but-not-yet-reported events with a reporting-delay distribution (Zeger et al., Lawless, Höhle and an der Heiden, McGough et al.), and real-time data vintages with revisions (Croushore and Stark, Aruoba).

### Cited Findings

**S16. Kaplan and Meier 1958**
- E. L. Kaplan and P. Meier, "Nonparametric Estimation from Incomplete Observations," Journal of the American Statistical Association, vol. 53, no. 282, pp. 457-481, Jun. 1958. DOI: 10.1080/01621459.1958.10501452. Confirmed on: [Crossref](https://api.crossref.org/works/10.1080/01621459.1958.10501452); abstract via [OpenAlex](https://api.openalex.org/works/https://doi.org/10.1080/01621459.1958.10501452).
- Estimates P(t), the proportion of items whose lifetime exceeds t, when some lifetimes are cut short by a loss (censoring), with no assumption on the form of P(t).
- Defines the product-limit estimate and shows it is the distribution that maximises the likelihood of the observations.
- Assumes lifetime is independent of the potential loss time, and says this assumption needs scrutiny in practice.
- With no losses before t, the estimate reduces to the observed proportion of survivors.
- Relation to revert-label delay: E(L) is a survival function of time-to-revert among eventual reverts. With a fixed 4-day follow-up for every edit (no losses before the horizon) the plain observed proportion is the Kaplan-Meier estimate, per the last bullet.

**S17. Höhle and an der Heiden 2014** (report ref [12]; re-verified)
- M. Höhle and M. an der Heiden, "Bayesian nowcasting during the STEC O104:H4 outbreak in Germany, 2011," Biometrics, vol. 70, no. 4, pp. 993-1002, Dec. 2014 (online 13 Jun. 2014). DOI: 10.1111/biom.12194. Confirmed on: [Crossref](https://api.crossref.org/works/10.1111/biom.12194) (includes abstract).
- Predicts occurred-but-not-yet-reported daily hospitalisations during the May-July 2011 outbreak.
- Handles right-truncation of the reporting-delay distribution in a conjugate Bayesian framework (generalized Dirichlet), with negative binomial counts.
- Scored against the retrospectively known true counts; finds the delay distribution changed during the outbreak because of interventions, and extends to a hierarchical model with a discrete-time survival regression for the delay.
- Relation to revert-label delay: same two-source design as TruthLag (real-time partial count versus later complete count), and evidence that a delay distribution is not stable over time. Draft entry is correct; add pages 993-1002 and the DOI.

**S18. Lawless 1994**
- J. F. Lawless, "Adjustments for reporting delays and the prediction of occurred but not reported events," Canadian Journal of Statistics, vol. 22, no. 1, pp. 15-31, Mar. 1994. DOI as registered: 10.2307/3315826.n1 (resolves to Wiley). Confirmed on: [Crossref](https://api.crossref.org/works/10.2307/3315826.n1); abstract via [OpenAlex search record](https://api.openalex.org/works?search=Adjustments%20for%20reporting%20delays%20and%20the%20prediction%20of%20occurred%20but%20not%20reported%20events).
- Caution: the DOI 10.2307/3315826 without ".n1" is a different article in the same issue (R. D. Routledge, pp. 103-110). Use the ".n1" form or cite without DOI.
- Treats delays in reporting events such as disease cases or insurance claims, and the estimation of events that have occurred but are not yet reported.
- States that earlier methods ignore random fluctuation over time in reporting delays, which makes prediction limits too narrow.
- Proposes an approach using recent reporting data with random effects to give more robust predictions.
- Relation to revert-label delay: the standard statistical name for "eventual reverts not yet known at wait L" is occurred-but-not-reported events; E(L) is one minus the cumulative reporting-delay distribution.

**S19. Zeger, See and Diggle 1989**
- S. L. Zeger, L.-C. See, and P. J. Diggle, "Statistical methods for monitoring the AIDS epidemic," Statistics in Medicine, vol. 8, no. 1, pp. 3-21, Jan. 1989. DOI: 10.1002/sim.4780080104. Confirmed on: [Crossref search record](https://api.crossref.org/works/10.1002/sim.4780080104); abstract via [OpenAlex](https://api.openalex.org/works/https://doi.org/10.1002/sim.4780080104).
- Proposes a log-linear model to estimate incidence and growth rate while accounting for delays in case reporting.
- Applied to US Centers for Disease Control registry data as of September 1987, seven risk groups in six regions.
- Finds incidence doubling about once every two years at that time.
- Relation to revert-label delay: early worked example of correcting a recent count for reports that have not arrived yet. Same-issue companion, confirmed on Crossref search: R. Brookmeyer and A. Damiano, "Statistical methods for short-term projections of AIDS incidence," Statistics in Medicine, vol. 8, no. 1, pp. 23-34, 1989, DOI 10.1002/sim.4780080105 (findings not read).

**S19b (optional). McGough, Johansson, Lipsitch and Menzies 2020**
- S. F. McGough, M. A. Johansson, M. Lipsitch, and N. A. Menzies, "Nowcasting by Bayesian Smoothing: A flexible, generalizable model for real-time epidemic tracking," PLOS Computational Biology, vol. 16, no. 4, e1007735, Apr. 2020. DOI: 10.1371/journal.pcbi.1007735. Confirmed on: [Crossref](https://api.crossref.org/works/10.1371/journal.pcbi.1007735); abstract via [OpenAlex](https://api.openalex.org/works/https://doi.org/10.1371/journal.pcbi.1007735).
- Nowcasting estimates complete case counts from reports known to be incomplete because of reporting delay; modelling the delay distribution is the common core.
- Tested on dengue in Puerto Rico and influenza-like illness in the United States, covering stable and time-varying delays.
- Linking cases across time improves accuracy when the delay distribution varies over time.
- Relation to revert-label delay: recent, open-access statement of the nowcasting problem; the possible next step after measuring E(L) (scale a live count up by the known delay curve).

**S20. Croushore and Stark 2001** (report ref [10]; re-verified)
- D. Croushore and T. Stark, "A real-time data set for macroeconomists," Journal of Econometrics, vol. 105, no. 1, pp. 111-130, Nov. 2001. DOI: 10.1016/S0304-4076(01)00072-0. Confirmed on: [Crossref](https://api.crossref.org/works/10.1016/S0304-4076(01)00072-0).
- No abstract on Crossref/OpenAlex for the journal version. The working-paper version (Federal Reserve Bank of Philadelphia Working Paper 99-4, 1999, DOI 10.21799/frbp.wp.1999.04, [OpenAlex search record](https://api.openalex.org/works?search=A%20real-time%20data%20set%20for%20macroeconomists)) describes a data set of vintages, i.e. snapshots of the major macroeconomic data as available at quarterly intervals in real time.
- The working paper says the data set is for testing the robustness of published results, policy analysis and forecasting, and shows that forecasts and policy analysis can change with the data vintage.
- UNVERIFIED: that the journal text matches the working-paper abstract word for word.
- Relation to revert-label delay: source for the "vintage" idea, i.e. keeping what was known at each time. TruthLag's stream-versus-dump comparison is a two-vintage data set for one label. Draft entry is correct; add pages 111-130 and the DOI.

**S21. Aruoba 2008** (report ref [11]; re-verified)
- S. B. Aruoba, "Data Revisions Are Not Well Behaved," Journal of Money, Credit and Banking, vol. 40, no. 2-3, pp. 319-340, Mar. 2008. DOI: 10.1111/j.1538-4616.2008.00115.x. Confirmed on: [Crossref](https://api.crossref.org/works/10.1111/j.1538-4616.2008.00115.x) (includes abstract).
- Documents revisions to major US macroeconomic variables.
- Revisions do not have zero mean, so initial announcements are biased.
- Revisions are large relative to the original variables and predictable from information available at the first announcement, so first announcements are not rational forecasts.
- Relation to revert-label delay: precedent for the finding that an early figure is biased in a known direction. An early revert count is biased low by construction, and E(L) gives the size of that bias. Draft entry is correct; add pages 319-340 and the DOI.

### Inferences
- E(L) as defined by the project (share of eventual reverts not yet known after wait L, within a 4-day window) is, in statistical terms, the survival function of the reporting delay conditional on the event being reported within the window (a right-truncated delay distribution, the term used in S17).
- Because the 4-day window truncates the delay, reverts that arrive after 4 days are outside both numerator and denominator; S17 and S18 are the sources for naming that limitation.

### Gaps
- Journal-version abstract of Croushore and Stark not available on an open page.
- Full texts of S16-S19 were not read; bullets are abstract-level.

## Key question 4: Measured label delay or time-to-revert on Wikipedia, and label latency in fraud / content moderation

### Takeaway
Time-to-revert on Wikipedia has been measured since 2004, as summary statistics (median, mean) computed after the fact from complete history; fraud detection is the applied area that treats delayed labels most explicitly. I found no peer-reviewed source on label latency in content moderation.

### Cited Findings

**S22. Dal Pozzolo, Boracchi, Caelen, Alippi and Bontempi 2015**
- A. Dal Pozzolo, G. Boracchi, O. Caelen, C. Alippi, and G. Bontempi, "Credit card fraud detection and concept-drift adaptation with delayed supervised information," in Proc. 2015 International Joint Conference on Neural Networks (IJCNN), Jul. 2015, pp. 1-8. DOI: 10.1109/IJCNN.2015.7280527. Confirmed on: [Crossref](https://api.crossref.org/works/10.1109/IJCNN.2015.7280527); abstract via [OpenAlex](https://api.openalex.org/works/https://doi.org/10.1109/IJCNN.2015.7280527).
- Only a small set of alerted transactions gets fast labels from human investigators; labels for the vast majority arrive only several days later, when customers report unauthorised transactions. (Abstract-level.)
- Shows that fast investigator feedback and delayed labels should be handled separately: train one classifier on each and aggregate.
- On a large real transaction data set this improves alert precision. No numbers in the abstract.
- Relation to revert-label delay: same two-speed labelling as Wikipedia (fast bot/tool reverts versus slow human reverts, see S26). The delay is described ("several days") but not measured as a curve.

**S23. Dal Pozzolo, Boracchi, Caelen, Alippi and Bontempi 2018**
- A. Dal Pozzolo, G. Boracchi, O. Caelen, C. Alippi, and G. Bontempi, "Credit Card Fraud Detection: A Realistic Modeling and a Novel Learning Strategy," IEEE Transactions on Neural Networks and Learning Systems, vol. 29, no. 8, pp. 3784-3797, Aug. 2018. DOI: 10.1109/TNNLS.2017.2736643. Confirmed on: [Crossref](https://api.crossref.org/works/10.1109/TNNLS.2017.2736643); abstract via [OpenAlex](https://api.openalex.org/works/https://doi.org/10.1109/TNNLS.2017.2736643).
- Names three challenges: concept drift, class imbalance, and verification latency (only a small set of transactions is checked promptly). (Abstract-level.)
- Says most proposed fraud learners assume unrealistic timing of supervised information and unrealistic performance measures.
- Formalises the real operating conditions with an industrial partner; experiments on a real stream of more than 75 million transactions authorised over three years.
- Relation to revert-label delay: journal-level source that label timing must be modelled as it actually occurs; uses the term "verification latency" in an applied setting.

**S24. Viégas, Wattenberg and Dave 2004**
- F. B. Viégas, M. Wattenberg, and K. Dave, "Studying cooperation and conflict between authors with history flow visualizations," in Proc. SIGCHI Conference on Human Factors in Computing Systems (CHI '04), Apr. 2004, pp. 575-582. DOI: 10.1145/985692.985765. Confirmed on: [Crossref](https://api.crossref.org/works/10.1145/985692.985765); full text read at [hint.fm](http://hint.fm/papers/history_flow.pdf).
- Uses a May 2003 Wikipedia database snapshot; "survival time" is how long a revision stays before being modified.
- Table 1: all content, 618,502 revisions, mean 22.3 days, median 90.4 minutes; mass deletions, 3,574, mean 7.7 days, median 2.8 minutes; obscene mass deletions, 47, mean 1.8 days, median 1.7 minutes.
- Mean far above median in every row (days versus minutes).
- Relation to revert-label delay: earliest measured repair-time figures for Wikipedia, and direct evidence of a heavy tail (median in minutes, mean in days), which is why a curve over L says more than one number.

**S25. Priedhorsky et al. 2007** (report ref [15]; re-verified)
- R. Priedhorsky, J. Chen, S. K. Lam, K. Panciera, L. Terveen, and J. Riedl, "Creating, destroying, and restoring value in Wikipedia," in Proc. 2007 International ACM Conference on Supporting Group Work (GROUP '07), 2007, pp. 259-268. DOI: 10.1145/1316624.1316663. Confirmed on: [Crossref](https://api.crossref.org/works/10.1145/1316624.1316663) (first page 259 only); abstract via [OpenAlex](https://api.openalex.org/works/https://doi.org/10.1145/1316624.1316663). End page 268 comes from a University of Minnesota Experts listing seen in search results, not opened.
- Measures the impact of an edit by the number of times the edited version is viewed, using logs of article views. (Abstract-level.)
- The probability that a typical article view shows damage is small but increasing; gives empirically grounded classes of damage.
- UNVERIFIED: the often-quoted figure that 42% of damage incidents are repaired almost immediately (within one estimated view). I could not open the full text; check before quoting.
- Relation to revert-label delay: measures damage lifetime in views instead of clock time, from complete history. Draft entry is correct; add the full author list, pages and DOI.

**S26. Geiger and Halfaker 2013** (report ref [17]; re-verified)
- R. S. Geiger and A. Halfaker, "When the levee breaks: without bots, what happens to Wikipedia's quality control processes?," in Proc. 9th International Symposium on Open Collaboration (WikiSym/OpenSym '13), Aug. 2013, pp. 1-6. DOI: 10.1145/2491055.2491061. Confirmed on: [Crossref](https://api.crossref.org/works/10.1145/2491055.2491061); full text read at [stuartgeiger.com](https://www.stuartgeiger.com/wikisym13-cluebot.pdf).
- Defines time-to-revert as the time between an edit and the later edit that removes it entirely by returning the article to a previous state; says researchers have long used its median or mean as the quality-control metric.
- English Wikipedia, Wednesdays and Thursdays from 1 January to 30 June 2011. Median time-to-revert 744 s (12.4 min) with ClueBot NG up and 1,286 s (21.4 min) with it down; geometric mean 941 s (15.7 min) versus 1,674 s (27.9 min).
- While the bot was down, the share of edits that were reverts was significantly lower (p < 0.001), but the share of revisions eventually reverted was not significantly different (p = 0.43): the same edits were reverted, later.
- Most reverts made with the Huggle tool came within 1 minute of the offending edit; different reviewer classes act at staggered times.
- Relation to revert-label delay: closest prior work. It shows the delay distribution shifts when the reviewing system changes while the eventual label stays the same, which is exactly the situation where E(L) changes and the final count does not. It reports medians and histograms from complete history, not the error of a live count at wait L. Draft entry is correct; add the subtitle, pages 1-6 and the DOI.

**S27 (optional). Kittur, Suh, Pendleton and Chi 2007**
- A. Kittur, B. Suh, B. A. Pendleton, and E. H. Chi, "He says, she says: conflict and coordination in Wikipedia," in Proc. SIGCHI Conference on Human Factors in Computing Systems (CHI '07), Apr. 2007, pp. 453-462. DOI: 10.1145/1240624.1240698. Confirmed on: [Crossref search record](https://api.crossref.org/works/10.1145/1240624.1240698); abstract via [OpenAlex](https://api.openalex.org/works/https://doi.org/10.1145/1240624.1240698).
- Examines growth of non-direct work (conflict, coordination) in Wikipedia and builds tools to characterise conflict. (Abstract-level; no delay numbers in the abstract.)
- Relation to revert-label delay: background on reverts as a conflict signal only; not a delay measurement. Probably better placed in the reverts section of the survey.

### Inferences
- Wikipedia studies (S24, S25, S26) measure repair time retrospectively from full history and summarise it with medians, means or histograms. None of the three frames it as a label-completeness curve for a consumer of a live stream.
- The fraud papers (S22, S23) are the nearest applied analogue: a fast partial label channel and a slow complete one.

### Gaps
- Content moderation: I found no peer-reviewed paper measuring moderation-label latency. Not searched in depth; report as "not found", not as "does not exist".
- Non-peer-reviewed leads seen only in search-result summaries, not opened and not suitable as citations without checking: a 2009 Wikipedia Signpost vandalism study (100 random articles, median time to correction reported as about four minutes), and 2026 Wikimedia Phabricator tasks proposing a median "time-to-live" metric for reverted edits with a 7-day window.
- The current Wikimedia revert-risk work (report ref [19]) and other revert-specific papers were not examined here; they belong to the Wikipedia-reverts topic.
- Priedhorsky full text not read (certificate error and paywall).

## Key question 5: What gap remains for a study of revert-label delay in a live Wikipedia stream

### Takeaway
Supported only this far: the sources checked either assume a label delay (stream learning), model it to fix training (advertising, fraud), correct counts for it (nowcasting), or summarise Wikipedia time-to-revert after the fact with medians. None of the sources checked here reports, for Wikipedia reverts, the share of eventual labels still missing as a function of wait, measured by comparing a live stream with a later snapshot.

### Cited Findings
- Stream-learning papers state that immediate labels are the usual assumption and are unrealistic — [S2 Žliobaitė 2010](https://api.openalex.org/works/https://doi.org/10.1109/ICDMW.2010.49); [S6 Souza et al. 2018](https://api.openalex.org/works/https://doi.org/10.1109/BRACIS.2018.00077); [S7 Grzenda et al. 2020](https://api.crossref.org/works/10.1007/s10618-019-00654-y).
- Plasse and Adams say delayed labels are "not properly appreciated or addressed in the literature" (2016) — [S4](https://api.openalex.org/works/https://doi.org/10.1109/BigData.2016.7840877).
- Souza et al. say few studies consider label delay when proposing new algorithms (2018) — [S6](https://api.openalex.org/works/https://doi.org/10.1109/BRACIS.2018.00077).
- Wikipedia time-to-revert has been reported as medians/means: 2.8 min median for mass deletions (2003 data) — [S24](http://hint.fm/papers/history_flow.pdf); 12.4 min median, 21.4 min with ClueBot NG down (2011 data) — [S26](https://www.stuartgeiger.com/wikisym13-cluebot.pdf).
- The delay distribution on Wikipedia moved when one bot went down, while the share eventually reverted did not — [S26](https://www.stuartgeiger.com/wikisym13-cluebot.pdf).
- Reporting-delay distributions also changed over time in epidemic surveillance — [S17](https://api.crossref.org/works/10.1111/biom.12194); [S19b](https://api.openalex.org/works/https://doi.org/10.1371/journal.pcbi.1007735).
- Early published figures are biased and their revisions predictable in macroeconomic data — [S21](https://api.crossref.org/works/10.1111/j.1538-4616.2008.00115.x).

### Inferences
- Gap statement the sources support: (a) stream-learning work asks for delay to be considered but mostly supplies simulated or assumed delays; (b) Wikipedia work measures time-to-revert but reports central tendency from complete history; (c) the statistics of reporting delay and data vintages give the right framework but have been applied to disease counts, insurance claims and macroeconomic series in the sources checked. A measured completeness-versus-wait curve E(L) for the revert label, from a live stream checked against a later dump, combines (a)-(c) and was not found in any source checked here.
- This is a "not found in the sources checked" claim, not a proof of absence. The draft's TODO wording ("prior work measures revert delay; it does not measure the error of a live count as a function of the wait") is consistent with S24-S26 but should be phrased as "to our knowledge".
- Heavy tail (S24: median minutes, mean days) supports reporting E(L) at several waits instead of one summary number.

### Gaps
- No systematic search of post-2020 Wikipedia research (e.g. Wikimedia Research reports, ORES/revert-risk evaluations) was done for an existing delay curve; another researcher's topic may cover it. If one exists, the gap statement must be narrowed.
- No source checked here uses a 4-day follow-up window; no literature basis for that specific choice was found.
- Citation counts and Google Scholar / DBLP cross-checks were not done.
