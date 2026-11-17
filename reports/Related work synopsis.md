# Related work synopsis for the TruthLag paper

This is a point-by-point synopsis, not finished paragraphs. Each point is a claim the Related Work section can make, with the sources that back it. The team writes the sentences. IDs such as D12 or W11 point to the full entry and BibTeX in `TruthLag literature survey sources.md` (same folder).

Marks: **(full text)** = the finding was read in the paper; **(abstract)** = read from the abstract only; **(record)** = only the citation is confirmed, so open the paper before quoting a detail.

## The framing in one line

Four bodies of work each hold one piece of the problem, and none holds the measurement. Stream learning states the problem, statistics supplies the estimator, Wikipedia research supplies after-the-fact repair times, and stream systems supply the mechanisms for waiting. TruthLag's E(L) is the number that joins them.

## Proposed order of subsections

The current Section 2 has four subsections. The largest gap is that it never cites work on delayed labels, which is the paper's own topic. Suggested order: a new 2.1 below, then the existing four.

### 2.1 Delayed labels and reporting delay (new)

1. Stream learning has treated late labels as a known problem since 2008-2010, under two names: "delayed labelling" and "verification latency". Kuncheva and Sánchez 2008 (D1, abstract); Žliobaitė 2010 (D2, abstract); survey: Gomes et al. 2022 (D9, abstract).
2. In that work the delay is an input, fixed or simulated. It is not measured for a real labelling process. Plasse and Adams 2016 (D4, abstract); Grzenda, Gomes and Bifet 2020 (D7, abstract).
3. Online advertising is the closest match in structure: only the positive label arrives, and a negative is inferred by waiting long enough, so the follow-up window is part of the label's definition. Chapelle 2014 uses a window of up to a month (D12, abstract); Ktena et al. 2019 (D13, abstract). TruthLag's window is four days.
4. Fraud detection has the same two-speed labelling: a few fast labels from investigators and the rest after a delay. Dal Pozzolo et al. 2018 (D23, abstract).
5. Statistics already has the vocabulary. E(L) is a survival function (Kaplan and Meier 1958, D16) of a reporting delay, in the sense of "occurred but not yet reported" events (Lawless 1994, D18; Höhle and an der Heiden 2014, D17). Data that is revised after first release is studied as "vintages" in macroeconomics (Croushore and Stark 2001, D20; Aruoba 2008, D21).
6. Where those methods have been applied, in the sources checked: disease counts, insurance claims and economic series. Not Wikipedia reverts.

### 2.2 Wikipedia reverts and revision history (extend the current 2.1)

1. Three different "reverted" labels exist and need not agree: the checksum identity revert in MediaWiki History (W2, full text), the `mw-reverted` software tag (W4, full text), and diff-based reverts (Flöck et al. 2012, W1, abstract). The paper should say which one each number uses.
2. The `mw-reverted` tag is applied by a queued job, so that label lags by design (W4, full text). This supports the paper's premise directly.
3. Earlier studies measured how fast damage is repaired, always looking back from complete history:
   - Viégas et al. 2004: median survival 2.8 minutes for mass deletions, May 2003 data (W8, full text).
   - Priedhorsky et al. 2007: 42% of damage incidents repaired within one estimated view; 11% last beyond 100 views; 2002-2006 data (W9, full text).
   - Geiger and Halfaker 2013: median time-to-revert 12.4 minutes with ClueBot NG running and 21.4 minutes with it down, while the share eventually reverted did not change; early 2011 data (W11, full text).
4. Point 3's last finding is the strongest motivation: the delay moved while the final count stayed the same, so a live count can change with no change in the eventual truth.
5. The tail is long: about 1% of hoax articles survive over a year (Kumar, West and Leskovec 2016, W12, full text); median bot-to-bot time to revert is 62 days (Geiger and Halfaker 2017, W24, full text). This supports reporting E(L) at several waits instead of one average.
6. The revert-risk scores the stream carries come from a model trained on identity-revert labels from MediaWiki History (Trokhymovych et al. 2023, W19, full text). That model's training label is the same delayed label TruthLag measures.
7. Mutual reverts as a measure of conflict: Yasseri et al. 2012 (W22, full text). A raw pair count is not conflict when bots are involved: Tsvetkova et al. 2017 (W23) against Geiger and Halfaker 2017 (W24). This backs the paper's caution about the ClueBot NG community.
8. Keep Kiesel et al. 2017 as it is, but note it is (record) only: do not quote its figures without opening it.

### 2.3 Real-time and historical data processing (extend the current 2.2)

1. The Dataflow model defines event time, watermarks and three ways to refine a result after late data arrives; it states that watermarks alone are not enough (Akidau et al. 2015, S20, full text).
2. Structured Streaming's watermark is the maximum event time seen minus a set delay (Armbrust et al. 2018, S16, full text).
3. Golab and Johnson 2011 give each partition of a stream warehouse a consistency level: Open, Closed or Complete (S26, full text). This is the warehouse-side name for "how long to wait before trusting a count".
4. What these sources do not give: the size of the error in an Open result as a function of the wait. They define mechanisms and levels, not the error curve. (This is a reading of the texts, not a claim that no such work exists.)
5. Cite the founding paper for each streaming algorithm the paper uses. The body currently cites none: reservoir sampling (Vitter 1985, S1), Bloom filter (Bloom 1970, S2, record), Flajolet-Martin (1985, S4), HyperLogLog (Flajolet et al. 2007, S5; pages 127-146), AMS (Alon, Matias and Szegedy 1996, S7), DGIM (Datar et al. 2002, S8, record).

### 2.4 Delta Lake and versioned data (the current 2.3)

1. Delta Lake: Armbrust et al. 2020 (S23, full text). Lakehouse: Armbrust et al. 2021 (S24, full text).
2. The Bronze/Silver/Gold pattern has no founding paper. Neither of the two papers above uses those words. Cite the Databricks documentation (S25).
3. Slowly changing dimensions: Kimball and Ross 2013 (S28, record).

### 2.5 Similarity search and privacy (the current 2.4)

1. MinHash chain: Broder 1997 defines resemblance over shingles (L1, abstract); Indyk and Motwani 1998 (L4, record) and Gionis et al. 1999 (L5, record) give LSH; Charikar 2002 defines LSH by collision probability equal to similarity (L6, abstract). Accurate wording: MinHash is an LSH family for Jaccard similarity; Broder's paper predates the term.
2. Spark's `MinHashLSH` uses OR-amplification only (L17, full text). Do not describe it as bands and rows.
3. Nearest prior uses on Wikipedia text: Potthast and Stein 2008 use the revision corpus as a near-duplicate benchmark (L18, full text); Weissman et al. 2015 run MinHash on Wikipedia sentences (L19, full text). No source was found that applies MinHash or LSH to edit summaries or revert detection.
4. k-anonymity (Sweeney 2002, P3) does not stop disclosure of a sensitive attribute, which is why l-diversity was proposed (Machanavajjhala et al. 2007, P5).
5. Differential privacy: Dwork 2006 (P11, record). For a count, Laplace noise gives expected error 1/epsilon whatever the data size (Dwork and Roth 2014, P12, full text). That is why small cohorts such as the 141-revert bot group show much larger relative error in the paper's own results.
6. Wikimedia itself publishes pageview counts under differential privacy, with threshold suppression on top of the noise (Adeleye et al. 2023, P17, full text). This is the closest real-world precedent for the paper's privacy section.

## The gap sentence

Content the sources support, for the team to word: to our knowledge, none of the sources examined reports, for Wikipedia reverts, the share of eventual revert labels still missing as a function of waiting time, measured by comparing a live edit stream with a later full-history snapshot.

Limits to respect:
- It is "not found in the sources checked". Post-2020 Wikimedia research was not searched systematically.
- Two near neighbours should be named: Kumar et al. 2016 report detection share by elapsed time for hoax articles (a different label), and Wikimedia's Research:Revert page says nearly all English Wikipedia reverts happen within 48 hours and warns that a cutoff hides late reverts (W5, full text).
- No source uses a four-day window. Present it as the project's own choice.

## If there is time for only five additions

1. Geiger and Halfaker 2013 (W11): delay moved, final count did not.
2. Priedhorsky et al. 2007 (W9): the classic repair-time study.
3. Trokhymovych et al. 2023 (W19): the revert-risk model the stream carries.
4. Grzenda, Gomes and Bifet 2020 (D7) or Gomes et al. 2022 (D9): delayed labels in stream learning.
5. Lawless 1994 (D18): reporting delay; note the DOI ends in `.n1`.
