<!-- Draft for team review. Numbering is local to Section II (order of first citation); LaTeX renumbers when merged into the full report. Generated from section_II.tex + refs.bib. -->

## II. Related Work

Truth Lag draws on five literatures: delayed labels and reporting delay, Wikipedia reverts, stream and lakehouse systems, MinHash and locality-sensitive hashing (LSH), and privacy for published aggregates.

### A. Delayed Labels, Reporting Delay and Data Vintages

Stream learning treats label delay as a condition the learner must tolerate. Žliobaitė [1] notes that most adaptive learners assume labels arrive immediately, which is often unrealistic, and asks which changes are detectable before labels arrive; the delay is an input to the experiment, not a quantity measured from a real labelling process. Closer in structure, Chapelle [2] models conversions that occur long after an impression, so that an unconverted user counts as negative only after enough time has passed. A not-yet-reverted edit is the same kind of right-censored positive, and our follow-up window plays the role of that waiting rule, but we report the delay curve instead of correcting a model for it.

Statistics supplies the vocabulary. Lawless [3] treats occurred-but-not-reported events such as insurance claims, and Höhle and an der Heiden [4] nowcast hospitalisations during the 2011 STEC outbreak under right truncation of the reporting delay, scoring estimates against counts known later and finding that the delay distribution shifted. Economics calls the same structure data vintages: Croushore and Stark [5] assembled macroeconomic series as they stood at each date, and Aruoba [6] showed that revisions have nonzero mean and are predictable at first release. In these terms the October EventStreams capture is an early vintage of the revert label and the MediaWiki History snapshot a later one, and E(L) is the survival function of a right-truncated reporting delay among eventual reverts.

### B. Wikipedia Reverts and Quality Control

The standard research definition is the identity revert: a revision whose content checksum equals an earlier revision's, marking the revisions between them as reverted [7]. Early studies used MD5 checksums [8], [9]; the MediaWiki History dataset, rebuilt monthly, exposes a SHA-1 field with identity-revert flags and a seconds-to-revert field [10]. Flöck et al. [11] showed that checksum matching misses some reverts, over-labels others and cannot separate full from partial reverts. Truth Lag waits for the checksum label, so its delay measurements cover identity reverts only.

Time-to-revert has been measured retrospectively from complete history. Viégas et al. [12] reported a 2.8-minute median survival for mass deletions in 2003 data against a 7.7-day mean. Priedhorsky et al. [8] measured damage in page views: 42% of about 2.1 million incidents were repaired within one estimated view and 11% persisted beyond 100. Geiger and Halfaker [13] found a 12.4-minute median time-to-revert on English Wikipedia in early 2011, rising to 21.4 minutes while ClueBot NG was offline, with no significant change in the share eventually reverted. This is the closest prior result: the delay moved while the final label did not, which is when a live count changes and a final count does not. These studies differ in data, units and population and are not directly comparable. Kumar et al. [14] give the nearest completeness-by-wait series, with 90% of eventually detected hoaxes flagged within an hour of patrol, but for article deletion, not reverts.

Trokhymovych et al. [15] train a multilingual vandalism model on the History identity-revert field, so a label still missing at snapshot time becomes a training negative. Yasseri et al. [9] measure edit-war controversy from mutual reverts between editor pairs, the approach our Neo4j analysis follows; on recent data such pair counts are lower bounds until late reverts are labelled.

### C. Stream Processing and Lakehouse Systems

Our streaming side analyses rest on founding papers for Flajolet–Martin counting [16], HyperLogLog [17], Bloom filters [18], the AMS frequency-moment estimators [19] (we cite the STOC 1996 version), DGIM sliding-window counts [20] and reservoir sampling [21], collected in the course textbook [22]. Each assumes one ordered pass with final values. Distinct-count sketches combine across partitions [16], [17], so a late event can be folded into its window, while a sliding-window count has no step for revising an item already counted.

The Dataflow model [23] separates event time from processing time, rejects the idea that unbounded data eventually becomes complete, and defines discarding, accumulating, and accumulating-and-retracting refinements. Structured Streaming [24] sets the watermark to the maximum event time seen minus a user-set delay, so a revert later than the delay falls outside the streaming aggregate and must be recovered by batch reconciliation, which is how our stream and History cohorts relate. Golab and Johnson [25] label stream-warehouse partitions Open, Closed or Complete; a day of edits in our lake is Open while reverts can arrive, Closed after the chosen wait, and Complete once a History snapshot covers it. Online aggregation [26] shows an early answer with its error, but that error comes from sampling, whereas ours comes from labels not yet arrived, which are not missing at random. Bitemporal tables [27] and slowly changing dimensions [28] separate when a fact held from when it was recorded, the pattern behind our SCD2 page dimension and time travel.

Delta Lake [29] provides ACID tables over object stores through a transaction log, with time travel and MERGE. The bronze/silver/gold medallion layering has no founding paper; Delta Lake does not use the terms, and the Databricks documentation [30] calls it a data design pattern without an academic origin, so we treat it as a Databricks naming convention. Keeping bronze unchanged lets silver be re-derived when labels arrive late. None of these sources measures how wrong an Open result is as a function of the wait.

### D. MinHash and Locality-Sensitive Hashing

Broder [31] defined document resemblance and containment and estimated them by per-document random sampling, and Indyk and Motwani [32] introduced LSH for approximate nearest neighbours. Andoni and Indyk [33] give the amplification bound: with *k* functions per table and *L* tables, a near pair collides in some table with probability at least 1−(1−P₁^k)^L, the banding S-curve of [22]. Spark's MinHashLSH [34] implements only OR-amplification: each table has dimension one and AND-amplification is listed as future work, so for Jaccard similarity *s* the candidate probability is 1−(1−s)^L, a concave curve rather than an S-curve. In our edit-war analysis, selectivity therefore comes from the exact Jaccard-distance threshold in the join. On Wikipedia text, Potthast and Stein [35] used revision history as a near-duplicate benchmark, and Weissman et al. [36] applied MinHash to sentences, dropping very short ones. We found no prior work applying MinHash or LSH to edit comments, diffs or revert detection.

### E. Privacy for Published Aggregates

*k*-anonymity requires each person's record to be indistinguishable from at least *k*−1 others [37] and was originally enforced by generalization and suppression [38]. ℓ-diversity [39] answers the case where a *k*-anonymous group shares a sensitive value; a group in which every edit was reverted would reveal each member's outcome. The Laplace mechanism [40] instead adds noise scaled to a query's sensitivity. The Wikimedia Foundation publishes pageview counts under differential privacy with threshold suppression after noise and reports drop and spurious rates [41], the combination our privacy analysis evaluates. Since edit metadata is already public, the question is what Truth Lag's aggregates add, so we publish counts over groups of editors, never per-editor rows.

### F. Gap Addressed by Truth Lag

To our knowledge, none of the sources we examined reports, for Wikipedia reverts, the share of eventual revert labels still missing as a function of the waiting time, measured by comparing a live edit stream with a later full-history snapshot. Stream learning treats the delay as given [1]; Wikipedia studies report medians from complete history [12], [13]; reporting-delay and vintage methods have been applied to disease counts, insurance claims and macroeconomic series [3], [4], [6]; and stream systems define when to stop waiting without measuring the error of an open result [23], [25]. Two results come close: Kumar et al. [14] report detection shares by elapsed time for hoaxes, a deletion label, and Research:Revert [7] notes that nearly all reverts happen within 48 hours and that observation cutoffs censor late reverts. Truth Lag measures the curve directly: about 42% of eventual reverts are not yet labelled after 1 hour and 6.3% after 48 hours. The 4-day follow-up window for the October cohort is our own design choice, not a convention from the literature; reverts arriving after it fall outside both the numerator and the denominator of E(L).

### References

[1] I. Žliobaitė, “Change with delayed labeling: When is it detectable?” in *Proc. 2010 IEEE International Conference on Data Mining Workshops (ICDMW)*, Dec. 2010, pp. 843–850. doi: 10.1109/ICDMW.2010.49.

[2] O. Chapelle, “Modeling delayed feedback in display advertising,” in *Proc. 20th ACM SIGKDD International Conference on Knowledge Discovery and Data Mining (KDD '14)*, Aug. 2014, pp. 1097–1105. doi: 10.1145/2623330.2623634.

[3] J. F. Lawless, “Adjustments for reporting delays and the prediction of occurred but not reported events,” *Canadian Journal of Statistics*, vol. 22, no. 1, pp. 15–31, Mar. 1994. doi: 10.2307/3315826.n1.

[4] M. Höhle and M. an der Heiden, “Bayesian nowcasting during the STEC O104:H4 outbreak in Germany, 2011,” *Biometrics*, vol. 70, no. 4, pp. 993–1002, Dec. 2014. doi: 10.1111/biom.12194.

[5] D. Croushore and T. Stark, “A real-time data set for macroeconomists,” *Journal of Econometrics*, vol. 105, no. 1, pp. 111–130, Nov. 2001. doi: 10.1016/S0304-4076(01)00072-0.

[6] S. B. Aruoba, “Data revisions are not well behaved,” *Journal of Money, Credit and Banking*, vol. 40, no. 2-3, pp. 319–340, Mar. 2008. doi: 10.1111/j.1538-4616.2008.00115.x.

[7] Wikimedia Research, “Research:Revert,” Meta-Wiki, accessed Nov. 17, 2026. [Online]. Available: <https://meta.wikimedia.org/wiki/Research:Revert>

[8] R. Priedhorsky, J. Chen, S. K. Lam, K. Panciera, L. Terveen, and J. Riedl, “Creating, destroying, and restoring value in Wikipedia,” in *Proc. 2007 Int. ACM Conf. Supporting Group Work (GROUP '07)*, 2007, pp. 259–268. doi: 10.1145/1316624.1316663.

[9] T. Yasseri, R. Sumi, A. Rung, A. Kornai, and J. Kertész, “Dynamics of conflicts in Wikipedia,” *PLoS ONE*, vol. 7, no. 6, p. e38869, Jun. 2012. doi: 10.1371/journal.pone.0038869.

[10] Wikimedia Foundation, “Data Platform/Data Lake/Edits/Mediawiki history dumps,” Wikitech, page last edited 5 July 2026. Accessed Nov. 17, 2026. [Online]. Available: <https://wikitech.wikimedia.org/wiki/Data_Platform/Data_Lake/Edits/Mediawiki_history_dumps>

[11] F. Flöck, D. Vrandečić, and E. Simperl, “Revisiting reverts: accurate revert detection in Wikipedia,” in *Proc. 23rd ACM Conf. Hypertext and Social Media (HT '12)*, 2012, pp. 3–12. doi: 10.1145/2309996.2310000.

[12] F. B. Viégas, M. Wattenberg, and K. Dave, “Studying cooperation and conflict between authors with history flow visualizations,” in *Proc. SIGCHI Conf. Human Factors in Computing Systems (CHI '04)*, Apr. 2004, pp. 575–582. doi: 10.1145/985692.985765.

[13] R. S. Geiger and A. Halfaker, “When the levee breaks: without bots, what happens to Wikipedia's quality control processes?” in *Proc. 9th Int. Symp. Open Collaboration (WikiSym '13)*, Hong Kong, China, Aug. 2013, pp. 1–6. doi: 10.1145/2491055.2491061.

[14] S. Kumar, R. West, and J. Leskovec, “Disinformation on the Web: impact, characteristics, and detection of Wikipedia hoaxes,” in *Proc. 25th Int. Conf. World Wide Web (WWW '16)*, 2016, pp. 591–602. doi: 10.1145/2872427.2883085.

[15] M. Trokhymovych, M. Aslam, A.-J. Chou, R. Baeza-Yates, and D. Saez-Trumper, “Fair multilingual vandalism detection system for Wikipedia,” in *Proc. 29th ACM SIGKDD Conf. Knowledge Discovery and Data Mining (KDD '23)*, 2023, pp. 4981–4990, preprint arXiv:2306.01650. doi: 10.1145/3580305.3599823.

[16] P. Flajolet and G. N. Martin, “Probabilistic counting algorithms for data base applications,” *Journal of Computer and System Sciences*, vol. 31, no. 2, pp. 182–209, Oct. 1985. doi: 10.1016/0022-0000(85)90041-8.

[17] P. Flajolet, É. Fusy, O. Gandouet, and F. Meunier, “HyperLogLog: the analysis of a near-optimal cardinality estimation algorithm,” in *Proc. 2007 Conference on Analysis of Algorithms (AofA 07)*, ser. Discrete Mathematics and Theoretical Computer Science Proceedings, vol. AH, 2007, pp. 127–146. doi: 10.46298/dmtcs.3545.

[18] B. H. Bloom, “Space/time trade-offs in hash coding with allowable errors,” *Communications of the ACM*, vol. 13, no. 7, pp. 422–426, Jul. 1970. doi: 10.1145/362686.362692.

[19] N. Alon, Y. Matias, and M. Szegedy, “The space complexity of approximating the frequency moments,” in *Proc. 28th Annual ACM Symposium on Theory of Computing (STOC '96)*, 1996, pp. 20–29. doi: 10.1145/237814.237823.

[20] M. Datar, A. Gionis, P. Indyk, and R. Motwani, “Maintaining stream statistics over sliding windows,” *SIAM Journal on Computing*, vol. 31, no. 6, pp. 1794–1813, 2002. doi: 10.1137/S0097539701398363.

[21] J. S. Vitter, “Random sampling with a reservoir,” *ACM Transactions on Mathematical Software*, vol. 11, no. 1, pp. 37–57, Mar. 1985. doi: 10.1145/3147.3165.

[22] J. Leskovec, A. Rajaraman, and J. D. Ullman, *Mining of Massive Datasets*, 3rd ed. Cambridge, U.K.: Cambridge University Press, 2020. doi: 10.1017/9781108684163.

[23] T. Akidau, R. Bradshaw, C. Chambers, S. Chernyak, R. J. Fernández-Moctezuma, R. Lax, S. McVeety, D. Mills, F. Perry, E. Schmidt, and S. Whittle, “The Dataflow model: A practical approach to balancing correctness, latency, and cost in massive-scale, unbounded, out-of-order data processing,” *Proceedings of the VLDB Endowment*, vol. 8, no. 12, pp. 1792–1803, Aug. 2015. doi: 10.14778/2824032.2824076.

[24] M. Armbrust, T. Das, J. Torres, B. Yavuz, S. Zhu, R. Xin, A. Ghodsi, I. Stoica, and M. Zaharia, “Structured Streaming: A declarative API for real-time applications in Apache Spark,” in *Proc. 2018 International Conference on Management of Data (SIGMOD '18)*, May 2018, pp. 601–613. doi: 10.1145/3183713.3190664.

[25] L. Golab and T. Johnson, “Consistency in a stream warehouse,” in *Proc. 5th Biennial Conference on Innovative Data Systems Research (CIDR '11)*, Asilomar, CA, Jan. 2011. [Online]. Available: <https://www.cidrdb.org/cidr2011/Papers/CIDR11_Paper13.pdf>

[26] J. M. Hellerstein, P. J. Haas, and H. J. Wang, “Online aggregation,” in *Proc. 1997 ACM SIGMOD International Conference on Management of Data (SIGMOD '97)*, 1997, pp. 171–182. doi: 10.1145/253260.253291.

[27] R. T. Snodgrass, *Developing Time-Oriented Database Applications in SQL*. San Francisco, CA: Morgan Kaufmann, 2000.

[28] R. Kimball and M. Ross, *The Data Warehouse Toolkit: The Definitive Guide to Dimensional Modeling*, 3rd ed. Indianapolis, IN: Wiley, Jul. 2013.

[29] M. Armbrust, T. Das, L. Sun, B. Yavuz, S. Zhu, M. Murthy, J. Torres, H. van Hovell, A. Ionescu, A. Łuszczak, M. Świtakowski, M. Szafrański, X. Li, T. Ueshin, M. Mokhtar, P. Boncz, A. Ghodsi, S. Paranjpye, P. Senster, R. Xin, and M. Zaharia, “Delta Lake: High-performance ACID table storage over cloud object stores,” *Proceedings of the VLDB Endowment*, vol. 13, no. 12, pp. 3411–3424, Aug. 2020. doi: 10.14778/3415478.3415560.

[30] Databricks, “What is the medallion lakehouse architecture?” Databricks on AWS documentation, last updated Oct. 29, 2026. Accessed Nov. 17, 2026. Vendor documentation; the pattern has no founding paper. [Online]. Available: <https://docs.databricks.com/aws/en/lakehouse/medallion>

[31] A. Z. Broder, “On the resemblance and containment of documents,” in *Proc. Compression and Complexity of SEQUENCES 1997 (Cat. No.97TB100171)*. IEEE Computer Society, 1997, pp. 21–29. doi: 10.1109/SEQUEN.1997.666900.

[32] P. Indyk and R. Motwani, “Approximate nearest neighbors: towards removing the curse of dimensionality,” in *Proc. 30th ACM STOC*, 1998, pp. 604–613. doi: 10.1145/276698.276876.

[33] A. Andoni and P. Indyk, “Near-optimal hashing algorithms for approximate nearest neighbor in high dimensions,” *Communications of the ACM*, vol. 51, no. 1, pp. 117–122, Jan. 2008. doi: 10.1145/1327452.1327494.

[34] Apache Software Foundation, “Extracting, transforming and selecting features — Locality Sensitive Hashing,” Apache Spark 4.3.0 MLlib Guide, accessed 2026-11-17. [Online]. Available: <https://spark.apache.org/docs/latest/ml-features.html#locality-sensitive-hashing>

[35] M. Potthast and B. Stein, “New issues in near-duplicate detection,” in *Data Analysis, Machine Learning and Applications*, ser. Studies in Classification, Data Analysis, and Knowledge Organization. Berlin, Heidelberg: Springer, 2008, pp. 601–609. doi: 10.1007/978-3-540-78246-9_71.

[36] S. Weissman, S. Ayhan, J. Bradley, and J. Lin, “Identifying duplicate and contradictory information in Wikipedia,” in *Proc. 15th ACM/IEEE-CS Joint Conf. Digital Libraries (JCDL)*, 2015, pp. 57–60, preprint arXiv:1406.1143. doi: 10.1145/2756406.2756947.

[37] L. Sweeney, “k-anonymity: A model for protecting privacy,” *Int. J. Uncertainty, Fuzziness and Knowledge-Based Systems*, vol. 10, no. 5, pp. 557–570, Oct. 2002. doi: 10.1142/S0218488502001648.

[38] P. Samarati and L. Sweeney, “Protecting privacy when disclosing information: k-anonymity and its enforcement through generalization and suppression,” Computer Science Laboratory, SRI International, Menlo Park, CA, Tech. Rep. SRI-CSL-98-04, 1998. [Online]. Available: <https://www.csl.sri.com/papers/sritr-98-04>

[39] A. Machanavajjhala, D. Kifer, J. Gehrke, and M. Venkitasubramaniam, “ℓ-diversity: Privacy beyond k-anonymity,” *ACM Trans. Knowl. Discov. Data*, vol. 1, no. 1, Mar. 2007, art. 3. doi: 10.1145/1217299.1217302.

[40] C. Dwork, F. McSherry, K. Nissim, and A. Smith, “Calibrating noise to sensitivity in private data analysis,” in *Theory of Cryptography (TCC 2006)*, ser. Lecture Notes in Computer Science. Berlin, Germany: Springer, 2006, pp. 265–284. doi: 10.1007/11681878_14.

[41] T. Adeleye, S. Berghel, D. Desfontaines, M. Hay, I. Johnson, C. Lemoisson, A. Machanavajjhala, T. Magerlein, G. Modena, D. Pujol, D. Simmons-Marengo, and H. Triedman, “Publishing Wikipedia usage data with strong privacy guarantees,” arXiv:2308.16298, Aug. 2023, v3, Jul. 2025. Presented at Theory and Practice of Differential Privacy (TPDP) 2023. doi: 10.48550/arXiv.2308.16298.
