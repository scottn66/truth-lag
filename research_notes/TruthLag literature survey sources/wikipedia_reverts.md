# Wikipedia reverts, vandalism detection and quality control: sources for the TruthLag literature survey

Research date: 2026-11-17. 28 entries (S1-S19, S20a, S20b, S21-S28). Every entry was opened on the "Confirmed on" URL. Bibliographic metadata for papers comes from the Crossref DOI record (api.crossref.org/works/<DOI>) unless stated; findings come from the paper text (author or arXiv PDF) where a PDF is listed, otherwise from the abstract only. "UNVERIFIED" marks any detail not confirmed on an opened page. No names of individual Wikipedia editors are recorded (bots and tools are named).

Corrections to the existing reference list in `docs/final/report_draft.md`:
- [15] Priedhorsky et al.: six authors (Priedhorsky, Chen, Lam, Panciera, Terveen, Riedl); pages 259-268; DOI 10.1145/1316624.1316663.
- [16] Kumar, West, Leskovec: full title has the subtitle "Impact, Characteristics, and Detection of Wikipedia Hoaxes"; pp. 591-602; DOI 10.1145/2872427.2883085.
- [17] Geiger and Halfaker: the paper's own header says "WikiSym 2013, Aug 05-07, 2013, Hong Kong"; the ACM proceedings title is "Proceedings of the 9th International Symposium on Open Collaboration" (the joint WikiSym + OpenSym 2013 volume). Either "WikiSym '13" or the full proceedings title is safer than "OpenSym 2013". DOI 10.1145/2491055.2491061.
- [18] Flöck, Vrandečić, Simperl: full title "Revisiting reverts: accurate revert detection in Wikipedia"; HT '12, pp. 3-12; DOI 10.1145/2309996.2310000.
- [19] Trokhymovych et al.: five authors (Trokhymovych, Aslam, Chou, Baeza-Yates, Saez-Trumper); KDD '23, pp. 4981-4990; DOI 10.1145/3580305.3599823.
- All five entries exist and are correctly attributed.

---

## 1. How are reverts defined and detected?

### Takeaway
The standard research definition is the identity revert: a revision whose content checksum equals an earlier revision's, which marks the revisions in between as reverted. Early papers used MD5; the MediaWiki History dataset exposes a SHA-1 field and identity-revert fields; MediaWiki itself (since 1.36) tags the reverted edits with `mw-reverted` through a deferred job, so the label arrives after the edit by design.

### Cited Findings

**S1. F. Flöck, D. Vrandečić, and E. Simperl, "Revisiting reverts: accurate revert detection in Wikipedia," in Proc. 23rd ACM Conf. Hypertext and Social Media (HT '12), Milwaukee, WI, USA, 2012, pp. 3-12. DOI 10.1145/2309996.2310000.**
Confirmed on: https://api.crossref.org/works/10.1145/2309996.2310000 ; abstract on https://api.openalex.org/works/doi:10.1145/2309996.2310000
- States that the then state of the art detects reverts by finding duplicate revisions through MD5 hash values, and calls this efficient but imprecise (abstract) — [OpenAlex abstract](https://api.openalex.org/works/doi:10.1145/2309996.2310000)
- Claims three drawbacks of the MD5 identity method: it misses some reverts, labels too many edits as reverts, and cannot separate full from partial reverts (abstract) — [OpenAlex abstract](https://api.openalex.org/works/doi:10.1145/2309996.2310000)
- Proposes a detector based on word tokens added or deleted, evaluated with a user study; trade-off is longer run time (abstract) — [OpenAlex abstract](https://api.openalex.org/works/doi:10.1145/2309996.2310000)
- The first author's dissertation summarises the result as finding 12% more full reverts than the earlier method, plus partial reverts — [Flöck dissertation, KIT](https://publikationen.bibliothek.kit.edu/1000058165/3879557); the same 12% figure is repeated on [Research:Revert](https://meta.wikimedia.org/wiki/Research:Revert). UNVERIFIED: the user-study sample size and exact accuracy figures in the HT paper itself (paper PDF not opened).
- Relation to revert-label delay: the label TruthLag waits for (identity revert, `mw-reverted`) is the checksum definition this paper criticises, so the measured delay is for identity reverts only; partial reverts never get the label.

**S2. Wikimedia Foundation, "Data Platform/Data Lake/Edits/Mediawiki history dumps," Wikitech. Page last edited 5 July 2026.**
Confirmed on: https://wikitech.wikimedia.org/wiki/Data_Platform/Data_Lake/Edits/Mediawiki_history_dumps
- Field definitions: `revision_is_identity_reverted` (boolean, revision was reverted by a later one), `revision_first_identity_reverting_revision_id` (bigint), `revision_seconds_to_identity_revert` (bigint, seconds between the revision and its revert), `revision_is_identity_revert` (boolean, this revision reverts others), `revision_text_sha1` (string), `revision_tags` (array of strings) — [Wikitech](https://wikitech.wikimedia.org/wiki/Data_Platform/Data_Lake/Edits/Mediawiki_history_dumps)
- Released monthly, around the end of the first week of the month; each release holds the full history since 2001; a snapshot is named YYYY-MM after the last month it covers; only the last two versions are kept — [Wikitech](https://wikitech.wikimedia.org/wiki/Data_Platform/Data_Lake/Edits/Mediawiki_history_dumps)
- Format: bzip2-compressed TSV under https://dumps.wikimedia.org/other/mediawiki_history/ with path `/<version>/<wiki>/<version>.<wiki>.<time range>.tsv.bz2` — [Wikitech](https://wikitech.wikimedia.org/wiki/Data_Platform/Data_Lake/Edits/Mediawiki_history_dumps)
- Relation to revert-label delay: this is the "late truth" source; its monthly cadence means an identity-revert flag can be up to about five weeks behind the edit regardless of how fast the revert happened.

**S3. Wikimedia Foundation, "Data Platform/Data Lake/Edits/MediaWiki history," Wikitech. Page last edited 5 July 2026.**
Confirmed on: https://wikitech.wikimedia.org/wiki/Data_Platform/Data_Lake/Edits/MediaWiki_history
- States that a new snapshot covering all of history is generated from source data each month; snapshots partitioned since 2017-03 — [Wikitech](https://wikitech.wikimedia.org/wiki/Data_Platform/Data_Lake/Edits/MediaWiki_history)
- Change log: `revision_tags` added in 2019-04; known quality notes include null or zero page ids and apparent duplicates (2020-06) and incomplete handling of complex delete/restore histories (2017 note, possibly outdated) — [Wikitech](https://wikitech.wikimedia.org/wiki/Data_Platform/Data_Lake/Edits/MediaWiki_history)
- This page does not define "identity revert" itself; it points to the schema catalog. UNVERIFIED: the exact algorithm (window, SHA-1 comparison scope) used to compute the identity-revert fields.
- Relation to revert-label delay: documents that the History dataset is rebuilt in full each month, so a revert label can change between snapshots.

**S4. MediaWiki contributors, "Manual:Reverts," MediaWiki.org. Page last edited 21 June 2026.**
Confirmed on: https://www.mediawiki.org/wiki/Manual:Reverts
- Software tags: `mw-undo` (edit made with the undo link or API), `mw-rollback` (rollback of the last editor's consecutive edits), `mw-manual-revert` (edit restoring an exact earlier version; since MediaWiki 1.36), `mw-reverted` (placed on the edits that were reverted, not on the reverting edit; since 1.36) — [Manual:Reverts](https://www.mediawiki.org/wiki/Manual:Reverts)
- `mw-reverted` is applied by a queued `revertedTagUpdate` job after the reverting edit is saved, so on busy wikis the tag can be delayed — [Manual:Reverts](https://www.mediawiki.org/wiki/Manual:Reverts)
- Conditions: the revert must be recognised, the number of reverted edits must not exceed `$wgRevertedTagMaxDepth`, the reverting revision must not itself be reverted or deleted, and the reverting edit must be auto-approved (with patrolling, the reverter has the autopatrol right); otherwise the update waits until the edit is approved — [Manual:Reverts](https://www.mediawiki.org/wiki/Manual:Reverts)
- Manual reverts are found by checking up to `$wgManualRevertSearchRadius` (default 15) most recent revisions for matching content — [Manual:Reverts](https://www.mediawiki.org/wiki/Manual:Reverts)
- Relation to revert-label delay: gives the mechanical reasons the stream-side label lags the revert (job queue, patrol approval) and why some reverted edits never receive it (depth limit, 15-revision radius).

**S5. Wikimedia Research, "Research:Revert," Meta-Wiki.**
Confirmed on: https://meta.wikimedia.org/wiki/Research:Revert
- Defines reverting, reverted and reverted-to revisions, and three revert types: identity revert, full revert plus changes, partial revert — [Research:Revert](https://meta.wikimedia.org/wiki/Research:Revert)
- Says nearly all reverts on English Wikipedia happen within 48 hours, which is why 48 hours is a common cutoff; mwreverts defaults to a radius of 15 subsequent edits — [Research:Revert](https://meta.wikimedia.org/wiki/Research:Revert)
- Reports from Kiesel et al. that about 6% of identity reverts are pseudo reverts, 9% self-reverts and 11% in edit wars; and warns that observation cutoffs censor late reverts — [Research:Revert](https://meta.wikimedia.org/wiki/Research:Revert). UNVERIFIED: the Kiesel et al. paper itself was not opened.
- The page text says MD5 while its sample code uses the SHA-1 field — [Research:Revert](https://meta.wikimedia.org/wiki/Research:Revert)
- Relation to revert-label delay: names the censoring problem TruthLag measures (a revert can arrive after the observation window closes) and gives the 48-hour convention to compare against.

**S6. A. Halfaker, "mwreverts" (Python library, MIT License), documentation.**
Confirmed on: https://pythonhosted.org/mwreverts/
- Library for detecting reverts and checking the reverted status of edits on a MediaWiki wiki; offers `mwreverts.Detector`, `mwreverts.detect()`, and status checks against the API (`mwreverts.api.check()`) and database (`mwreverts.db.check()`) — [mwreverts docs](https://pythonhosted.org/mwreverts/)
- Default radius of 15 revisions is stated on [Research:Revert](https://meta.wikimedia.org/wiki/Research:Revert), not on the library's front page. UNVERIFIED: version number and release year.
- Relation to revert-label delay: the reference implementation of the identity-revert definition; a radius of 15 means a revert more than 15 revisions later is not counted.

**S7. Wikimedia Foundation, "Machine Learning/LiftWing/Streams," Wikitech. Page last edited 13 May 2026.**
Confirmed on: https://wikitech.wikimedia.org/wiki/Machine_Learning/LiftWing/Streams
- The language-agnostic revert-risk model server consumes `mediawiki.page_change.v1` and emits `mediawiki.page_revert_risk_prediction_change.v1` — [Wikitech](https://wikitech.wikimedia.org/wiki/Machine_Learning/LiftWing/Streams)
- The page does not say which wikis are covered or whether the stream is in public EventStreams — [Wikitech](https://wikitech.wikimedia.org/wiki/Machine_Learning/LiftWing/Streams)
- Relation to revert-label delay: documents where the at-edit-time revert-risk score in the stream comes from, the early signal TruthLag compares with the late label.

### Inferences
- Three "revert" labels coexist and need not agree: checksum identity revert in MediaWiki History (SHA-1 field), `mw-reverted` in the software (content match within 15 revisions, plus approval and depth conditions), and diff-based reverts (Flöck et al.). The report should state which one each number uses.
- Yasseri et al. and Priedhorsky et al. used MD5; MediaWiki History exposes SHA-1. Both are exact-content checksums, so the definitions are equivalent in practice, but "SHA-1" should not be attributed to those papers.

### Gaps
- No opened Wikimedia page states the exact algorithm that fills `revision_is_identity_reverted` (window size, whether self-reverts are included).
- Kiesel et al. 2017 (ICWSM, reverted-edit analysis) is cited only second-hand through Research:Revert; not confirmed directly.
- No documentation page was found that states a typical delay of the `revertedTagUpdate` job.

---

## 2. How fast is damage reverted?

### Takeaway
Published medians run from about 2-3 minutes for blatant mass deletions (2003 data) to about 12 minutes for all reverted edits on English Wikipedia in early 2011, rising to about 21 minutes when ClueBot NG was offline; fully automated reverts mostly land within one minute. Every study also reports a long tail (11% of damage incidents lasting beyond 100 views; 1% of hoaxes lasting over a year).

### Cited Findings

**S8. F. B. Viégas, M. Wattenberg, and K. Dave, "Studying cooperation and conflict between authors with history flow visualizations," in Proc. SIGCHI Conf. Human Factors in Computing Systems (CHI '04), Vienna, Austria, 2004, pp. 575-582. DOI 10.1145/985692.985765.**
Confirmed on: https://api.crossref.org/works/10.1145/985692.985765 ; text read at https://politics.media.mit.edu/papers/history_flowviegas.pdf
- Data: English Wikipedia history as of May 2003 — [paper PDF](https://politics.media.mit.edu/papers/history_flowviegas.pdf)
- Table 1 survival times: all content, n = 618,502, mean 22.3 days, median 90.4 minutes; mass deletions, n = 3,574, mean 7.7 days, median 2.8 minutes; obscene mass deletions, n = 47, mean 1.8 days, median 1.7 minutes — [paper PDF](https://politics.media.mit.edu/papers/history_flowviegas.pdf)
- Mass deletion defined as a version at least 90% smaller than the page's previous maximum size, not a redirect, not made by an administrator — [paper PDF](https://politics.media.mit.edu/papers/history_flowviegas.pdf)
- Describes edit wars as alternation between two versions, some lasting 20 consecutive versions — [paper PDF](https://politics.media.mit.edu/papers/history_flowviegas.pdf)
- Relation to revert-label delay: earliest published time-to-repair figures; note the large gap between median (minutes) and mean (days), the same skew a label-delay distribution shows.

**S9. R. Priedhorsky, J. Chen, S. K. Lam, K. Panciera, L. Terveen, and J. Riedl, "Creating, destroying, and restoring value in Wikipedia," in Proc. 2007 Int. ACM Conf. Supporting Group Work (GROUP '07), Sanibel Island, FL, USA, 2007, pp. 259-268. DOI 10.1145/1316624.1316663.**
Confirmed on: https://api.crossref.org/works/10.1145/1316624.1316663 (first page 259; range 259-268 as cited in the reference list of S11); text read from the Internet Archive copy of the authors' PDF (http://www-users.cs.umn.edu/~reid/papers/group282-priedhorsky.pdf via web.archive.org). UNVERIFIED: conference location.
- Study period 1 September 2002 to 31 October 2006, English Wikipedia; 4.2 million editors and 58 million edits analysed — [archived author PDF](https://web.archive.org/web/2015/http://www-users.cs.umn.edu/~reid/papers/group282-priedhorsky.pdf)
- Reverts detected by comparing MD5 checksums of revision text; only identity reverts are considered; damage is a will-be-reverted revision whose reverting edit comment signals damage repair — [archived author PDF](https://web.archive.org/web/2015/http://www-users.cs.umn.edu/~reid/papers/group282-priedhorsky.pdf)
- 2,100,828 damage incidents covering 2,955,698 damaged revisions (1.4 revisions per incident); 42% repaired within one estimated view; 11% persist beyond 100 views; 0.75% (15,756) beyond 1,000 views; 0.06% (1,260) beyond 10,000 views — [archived author PDF](https://web.archive.org/web/2015/http://www-users.cs.umn.edu/~reid/papers/group282-priedhorsky.pdf)
- Of an estimated 51 billion views, 188 million were of damaged revisions: probability 0.0037 overall, 0.0067 in October 2006, growing roughly exponentially through June 2006 — [archived author PDF](https://web.archive.org/web/2015/http://www-users.cs.umn.edu/~reid/papers/group282-priedhorsky.pdf)
- Relation to revert-label delay: measures the delay in views rather than seconds, and shows the heavy tail; cites Kittur et al. for 94% of comment-identifiable reverts being identity reverts.

**S10. R. S. Geiger and D. Ribes, "The work of sustaining order in Wikipedia: the banning of a vandal," in Proc. 2010 ACM Conf. Computer Supported Cooperative Work (CSCW '10), Savannah, GA, USA, 2010, pp. 117-126. DOI 10.1145/1718918.1718941.**
Confirmed on: https://api.crossref.org/works/10.1145/1718918.1718941 ; text read at https://stuartgeiger.com/papers/cscw-sustaining-order-wikipedia.pdf . UNVERIFIED: conference location.
- Trace ethnography of one anonymous vandal blocked after about twenty edits in one hour, reverted by several bots and tool-assisted editors — [author PDF](https://stuartgeiger.com/papers/cscw-sustaining-order-wikipedia.pdf)
- As of 2009, over 12 percent of all edits were made with assisted tools; on the vandalism-intervention noticeboard the share was as high as 75 percent — [author PDF](https://stuartgeiger.com/papers/cscw-sustaining-order-wikipedia.pdf)
- Tools leave markers in edit summaries (for example "(HG)" for Huggle, "(TW)" for Twinkle), which is how tool-made reverts are identified — [author PDF](https://stuartgeiger.com/papers/cscw-sustaining-order-wikipedia.pdf)
- Relation to revert-label delay: explains who produces fast reverts (bots, then tool users, then manual editors), the mechanism behind a multi-modal delay distribution.

**S11. R. S. Geiger and A. Halfaker, "When the levee breaks: without bots, what happens to Wikipedia's quality control processes?," in Proc. 9th Int. Symp. Open Collaboration (WikiSym '13), Hong Kong, China, 2013, pp. 1-6 (Crossref page field; article number UNVERIFIED). DOI 10.1145/2491055.2491061.**
Confirmed on: https://api.crossref.org/works/10.1145/2491055.2491061 ; text read at https://stuartgeiger.com/wikisym13-cluebot.pdf
- Data: English Wikipedia, 1 January to 30 June 2011. ClueBot NG outages: 15-18 February, 13-17 March, 29 March-7 April, 15 April-1 May 2011 — [author PDF](https://stuartgeiger.com/wikisym13-cluebot.pdf)
- Time-to-revert, Wednesdays and Thursdays only: bot up, geometric mean 941 s (15.7 min), median 744 s (12.4 min); bot down, geometric mean 1,674 s (27.9 min), median 1,286 s (21.4 min) — [author PDF](https://stuartgeiger.com/wikisym13-cluebot.pdf)
- In a normal month (January 2011): most fully automated reverts occur within one minute; manual in-browser reverts fall mostly between one minute and 24 hours; tool-assisted reverts lie in between — [author PDF](https://stuartgeiger.com/wikisym13-cluebot.pdf)
- A smaller share of edits made during downtime was reverted at first, but those edits were eventually reverted later — [author PDF](https://stuartgeiger.com/wikisym13-cluebot.pdf)
- ClueBot NG first edited in November 2010, made about 5,000 edits per weekday and 2,500 per weekend day, and had over 2 million edits by March 2013 — [author PDF](https://stuartgeiger.com/wikisym13-cluebot.pdf)
- Relation to revert-label delay: direct precedent for measuring the time-to-revert distribution and for the finding that a revert label that is missing early can still arrive later.

**S12. S. Kumar, R. West, and J. Leskovec, "Disinformation on the Web: impact, characteristics, and detection of Wikipedia hoaxes," in Proc. 25th Int. Conf. World Wide Web (WWW '16), Montréal, Canada, 2016, pp. 591-602. DOI 10.1145/2872427.2883085.**
Confirmed on: https://api.crossref.org/works/10.1145/2872427.2883085 ; text read at https://cs.stanford.edu/people/jure/pubs/hoax-www16.pdf . UNVERIFIED: conference location.
- 21,218 English Wikipedia hoax articles that went through creation, patrol, flagging and deletion — [author PDF](https://cs.stanford.edu/people/jure/pubs/hoax-www16.pdf)
- Of hoaxes eventually detected, 90% are flagged within one hour of patrol, 92% within a day, 94% within a week, 96% within a month; about 1 in 100 survives more than a year — [author PDF](https://cs.stanford.edu/people/jure/pubs/hoax-www16.pdf)
- New-article patrol (since November 2007): 80% of new articles patrolled within an hour, 95% within a day — [author PDF](https://cs.stanford.edu/people/jure/pubs/hoax-www16.pdf)
- 1% of hoaxes get over 100 views per day before discovery; human accuracy in a hoax vs non-hoax pair task 66%, classifier 86% — [author PDF](https://cs.stanford.edu/people/jure/pubs/hoax-www16.pdf)
- Relation to revert-label delay: a detection-delay curve for article-level falsehoods (deletion, not revert) with the same shape: most caught fast, a small share very late.

**S13. A. Kittur, B. Suh, B. A. Pendleton, and E. H. Chi, "He says, she says: conflict and coordination in Wikipedia," in Proc. SIGCHI Conf. Human Factors in Computing Systems (CHI '07), San Jose, CA, USA, 2007, pp. 453-462. DOI 10.1145/1240624.1240698.**
Confirmed on: https://api.crossref.org/works/10.1145/1240624.1240698 ; abstract on https://api.openalex.org/works/doi:10.1145/1240624.1240698 . UNVERIFIED: conference location; paper PDF not opened.
- Abstract: studies the growth of non-direct work (conflict and coordination) in Wikipedia and builds tools to characterise conflict and coordination costs — [OpenAlex abstract](https://api.openalex.org/works/doi:10.1145/1240624.1240698)
- As reported by Priedhorsky et al. (S9): among identity reverts plus effective reverts identifiable from edit comments, 94% are identity reverts — [S9 archived PDF](https://web.archive.org/web/2015/http://www-users.cs.umn.edu/~reid/papers/group282-priedhorsky.pdf); restated on [Research:Revert](https://meta.wikimedia.org/wiki/Research:Revert)
- As reported by Sumi et al. (S20): computed article controversy from page metrics, using dispute tags as ground truth — [arXiv 1107.3689](https://arxiv.org/abs/1107.3689)
- UNVERIFIED: any time-to-revert figure, the "Revert Graph" user clustering, and the data year in this paper (not read first-hand).
- Relation to revert-label delay: source of the 94% coverage figure that justifies using identity reverts as the label.

### Inferences
- Median time-to-revert figures are not comparable across papers without care: Viégas (2003 data, mass deletions only), Priedhorsky (2002-2006, counted in views), Geiger and Halfaker (2011, all reverted edits, seconds).
- A "Signpost" summary and other secondary pages quote these numbers; the figures above were taken from the papers' own text.

### Gaps
- No peer-reviewed paper on ClueBot NG's own detection accuracy or latency was confirmed; the bot is described here only through S11.
- West et al.'s STiki papers (S15, S16) give no time-to-revert figure in their abstracts.
- No opened source gives a time-to-revert distribution for data later than 2011 other than the bot-only figures in S23.

---

## 3. Vandalism-detection systems and their papers

### Takeaway
The line runs from feature-based classifiers on a labelled corpus (Potthast 2008), through metadata-only and combined systems (West 2010; Adler 2011), to Wikimedia's production services: ORES (2015 onward, paper 2020) and the Revert Risk models on Lift Wing (2023), which are trained directly on the MediaWiki History revert label.

### Cited Findings

**S14. M. Potthast, B. Stein, and R. Gerling, "Automatic vandalism detection in Wikipedia," in Advances in Information Retrieval (ECIR 2008), Lecture Notes in Computer Science. Berlin, Heidelberg: Springer, 2008, pp. 663-668. DOI 10.1007/978-3-540-78646-7_75.**
Confirmed on: https://api.crossref.org/works/10.1007/978-3-540-78646-7_75 (authors, title, book title, pages); text read at https://webis.de/downloads/publications/papers/potthast_2008b.pdf . UNVERIFIED: LNCS volume number (commonly given as 4956) and the year 2008 (not in the Crossref record; taken from the conference name and file name).
- Frames vandalism detection as a classification task and releases a machine-readable corpus of vandalism edits — [paper PDF](https://webis.de/downloads/publications/papers/potthast_2008b.pdf)
- Logistic regression reaches 83% precision at 77% recall; F-measure 49% higher than the rule-based bots then used on Wikipedia — [paper PDF](https://webis.de/downloads/publications/papers/potthast_2008b.pdf)
- Features derived from manual analysis of 301 vandalism cases — [paper PDF](https://webis.de/downloads/publications/papers/potthast_2008b.pdf)
- Relation to revert-label delay: uses human-annotated labels rather than reverts, the alternative to waiting for a revert label.

**S15. A. G. West, S. Kannan, and I. Lee, "Detecting Wikipedia vandalism via spatio-temporal analysis of revision metadata," in Proc. 3rd European Workshop on System Security (EUROSEC '10), Paris, France, 2010, pp. 22-28. DOI 10.1145/1752046.1752050.**
Confirmed on: https://api.crossref.org/works/10.1145/1752046.1752050 (the Crossref title carries a trailing "?"); abstract on https://api.openalex.org/works/doi:10.1145/1752046.1752050 . UNVERIFIED: workshop location.
- Uses only revision metadata (no article or diff text); labels come from administrative rollback, which tags malicious edits — [OpenAlex abstract](https://api.openalex.org/works/doi:10.1145/1752046.1752050)
- Reports 85% accuracy at 50% recall, throughput over 100 edits per second, and over 5,000 manually confirmed vandalism incidents found outside the labelled set — [OpenAlex abstract](https://api.openalex.org/works/doi:10.1145/1752046.1752050)
- Relation to revert-label delay: an early case of using a revert action (rollback) as the training label, so label quality depends on when rollback happens.

**S16. A. G. West, S. Kannan, and I. Lee, "STiki: an anti-vandalism tool for Wikipedia using spatio-temporal analysis of revision metadata," in Proc. 6th Int. Symp. Wikis and Open Collaboration (WikiSym '10), Gdańsk, Poland, 2010, pp. 1-2 (demo; article number UNVERIFIED). DOI 10.1145/1832772.1832814.**
Confirmed on: https://api.crossref.org/works/10.1145/1832772.1832814 ; abstract on https://api.openalex.org/works/doi:10.1145/1832772.1832814 . UNVERIFIED: symposium location.
- STiki is a real-time tool: a server scores each revision's likelihood of vandalism; a client GUI shows likely vandalism to human users who classify and revert — [OpenAlex abstract](https://api.openalex.org/works/doi:10.1145/1832772.1832814)
- Relation to revert-label delay: one of the "assisted" tools whose queues put human reverts minutes, not seconds, after the edit (see S11).

**S17. B. T. Adler, L. de Alfaro, S. M. Mola-Velasco, P. Rosso, and A. G. West, "Wikipedia vandalism detection: combining natural language, metadata, and reputation features," in Computational Linguistics and Intelligent Text Processing (CICLing 2011), Lecture Notes in Computer Science, vol. 6609. Berlin, Heidelberg: Springer, 2011, pp. 277-288. DOI 10.1007/978-3-642-19437-5_23.**
Confirmed on: https://api.crossref.org/works/10.1007/978-3-642-19437-5_23 ; abstract on https://api.semanticscholar.org/graph/v1/paper/DOI:10.1007/978-3-642-19437-5_23 ; LNCS 6609 and Tokyo venue from the authors' repository copy (archived https://users.soe.ucsc.edu/~luca/papers/11/cicling2011.pdf cover sheet).
- States that about 7% of edits are vandalism — [Semantic Scholar abstract](https://api.semanticscholar.org/graph/v1/paper/DOI:10.1007/978-3-642-19437-5_23?fields=title,abstract,year,venue)
- Combines three approaches: STiki metadata, WikiTrust reputation, and natural-language features; the joint system beats each prior method — [Semantic Scholar abstract](https://api.semanticscholar.org/graph/v1/paper/DOI:10.1007/978-3-642-19437-5_23?fields=title,abstract,year,venue)
- Separates two tasks: catching fresh vandalism at edit time and finding vandalism in the full revision history — [Semantic Scholar abstract](https://api.semanticscholar.org/graph/v1/paper/DOI:10.1007/978-3-642-19437-5_23?fields=title,abstract,year,venue)
- UNVERIFIED: exact AUC figures on the PAN 2010 corpus.
- Relation to revert-label delay: the "fresh vs historical" split is the same distinction as scoring before the label exists vs after it has settled.

**S18. A. Halfaker and R. S. Geiger, "ORES: lowering barriers with participatory machine learning in Wikipedia," Proc. ACM Hum.-Comput. Interact., vol. 4, no. CSCW2, Article 148, pp. 1-37, Oct. 2020. DOI 10.1145/3415219. Preprint arXiv:1909.05189.**
Confirmed on: https://api.crossref.org/works/10.1145/3415219 ; https://arxiv.org/abs/1909.05189 (article number 148 from the PDF footer)
- ORES is a scoring service giving real-time scores for edits from several independent classifiers; it separates training-data curation, model building, auditing and tool building — [arXiv abstract](https://arxiv.org/abs/1909.05189)
- Example English Wikipedia "damaging" model (gradient boosting): 19,445 labelled edits, 743 damaging (3.8%); ROC AUC 0.923; precision 0.34 and recall 0.555 on the damaging class — [arXiv PDF](https://arxiv.org/pdf/1909.05189)
- Labels come either from manual community labelling campaigns (Wiki Labels) or from trace data found on the wiki, which the authors say needs care — [arXiv PDF](https://arxiv.org/pdf/1909.05189)
- Single-score response times quoted by S19: median 1.1 s, 75th percentile 1.2 s, 95th percentile 1.9 s — [arXiv 2306.01650 PDF](https://arxiv.org/pdf/2306.01650)
- Relation to revert-label delay: ORES "damaging" labels are human judgements, not reverts; the contrast with revert-trained models (S19) is a design choice about label timing.

**S19. M. Trokhymovych, M. Aslam, A.-J. Chou, R. Baeza-Yates, and D. Saez-Trumper, "Fair multilingual vandalism detection system for Wikipedia," in Proc. 29th ACM SIGKDD Conf. Knowledge Discovery and Data Mining (KDD '23), Long Beach, CA, USA, 2023, pp. 4981-4990. DOI 10.1145/3580305.3599823. Preprint arXiv:2306.01650.**
Confirmed on: https://api.crossref.org/works/10.1145/3580305.3599823 ; https://arxiv.org/abs/2306.01650 . UNVERIFIED: conference location.
- Covers 47 languages; target is whether a revision will be reverted; the training record shown in the paper uses the MediaWiki History field `revision_is_identity_reverted` — [arXiv PDF](https://arxiv.org/pdf/2306.01650)
- Training data: six months of revisions, test set the following week (time-based split); bot edits removed; "revision wars" filtered out; one training set uses anonymous edits only to reduce bias — [arXiv PDF](https://arxiv.org/pdf/2306.01650)
- Claims better accuracy than ORES and over 60% more languages covered; inference median 1.0 s, 75th percentile 1.7 s, 95th percentile 4.0 s on CPU — [arXiv PDF](https://arxiv.org/pdf/2306.01650)
- Notes about 16 pages edited per second on Wikipedia — [arXiv PDF](https://arxiv.org/pdf/2306.01650)
- UNVERIFIED: headline AUC and accuracy figures (not extracted).
- Relation to revert-label delay: the model whose scores ride in the stream is trained on the late identity-revert label from a monthly snapshot; any label still missing at snapshot time is a training negative.

**S20a. Wikimedia Foundation, "Machine learning models/Production/Language-agnostic revert risk" (model card), Meta-Wiki. Page last edited 14 August 2026.**
Confirmed on: https://meta.wikimedia.org/wiki/Machine_learning_models/Production/Language-agnostic_revert_risk
- Predicts the probability that a revision will be reverted; Wikipedia article namespace only; XGBoost; hosted on Lift Wing — [model card](https://meta.wikimedia.org/wiki/Machine_learning_models/Production/Language-agnostic_revert_risk)
- Training data from MediaWiki History and Wikitext History, snapshot 2023-05, observation period 2022-01-01 to 2023-01-01; bots removed; random 70/30 split — [model card](https://meta.wikimedia.org/wiki/Machine_learning_models/Production/Language-agnostic_revert_risk)
- Features: article-quality features for current and parent revision and their differences; user account age, prior revision count, number of user groups — [model card](https://meta.wikimedia.org/wiki/Machine_learning_models/Production/Language-agnostic_revert_risk)
- Guidance: probability above 0.9 for precision, 0.5 for recall; may be biased against new users, temporary accounts and IP editors; not for a page's first revision. Performance section is empty — [model card](https://meta.wikimedia.org/wiki/Machine_learning_models/Production/Language-agnostic_revert_risk)
- Relation to revert-label delay: the score in the stream; trained on data whose snapshot (2023-05) is four months after the observation window ends, so labels had time to settle.

**S20b. Wikimedia Foundation, "Machine learning models/Production/Multilingual revert risk" (model card), Meta-Wiki. Page last edited 11 June 2026.**
Confirmed on: https://meta.wikimedia.org/wiki/Machine_learning_models/Production/Multilingual_revert_risk
- Fine-tuned multilingual BERT text features plus a CatBoost classifier; 47 languages — [model card](https://meta.wikimedia.org/wiki/Machine_learning_models/Production/Multilingual_revert_risk)
- Training: snapshot 2022-07, observation 2022-01-01 to 2022-07-01, test the following week; 8,586,362 training and 1,079,265 test revisions; at most 300,000 per language — [model card](https://meta.wikimedia.org/wiki/Machine_learning_models/Production/Multilingual_revert_risk)
- Revert rate 0.08 in training and 0.07 in test; IP-edit rate 0.17 and 0.19; edit-war and bot revisions filtered out — [model card](https://meta.wikimedia.org/wiki/Machine_learning_models/Production/Multilingual_revert_risk)
- Relation to revert-label delay: here the snapshot month (2022-07) equals the end of the observation window, so the most recent training edits had little time to be reverted; the lower revert rate in the test week (0.07 vs 0.08) is consistent with that, though the card does not say so.

### Inferences
- Label source shifted over time: human annotation (Potthast, ORES) to rollback (West) to identity reverts from MediaWiki History (Revert Risk). Only the last depends on revert-label delay.
- Neither model card defines the revert label in words; the KDD paper's data example is the only place the field name appears.

### Gaps
- PAN 2010/2011 shared-task overview papers were not opened; only mentioned inside S17.
- Performance sections of both model cards are empty; headline metrics must come from the KDD paper and were not extracted.
- The multilingual model card's count of "47 languages" and the abstract agree; the language-agnostic card gives no wiki count.

---

## 4. Edit wars and mutual reverts

### Takeaway
Yasseri et al. define conflict through mutual reverts (two editors each reverting the other), weighted by the less experienced editor's edit count, and find under 1% of English Wikipedia articles controversial. The bot-conflict debate (Tsvetkova et al. vs Geiger and Halfaker) shows that a raw revert pair count is not conflict: median bot-bot time to revert is months.

### Cited Findings

**S21. R. Sumi, T. Yasseri, A. Rung, A. Kornai, and J. Kertész, "Edit wars in Wikipedia," in Proc. 2011 IEEE 3rd Int. Conf. Privacy, Security, Risk and Trust and 2011 IEEE 3rd Int. Conf. Social Computing (PASSAT/SocialCom), Boston, MA, USA, Oct. 2011, pp. 724-727. DOI 10.1109/PASSAT/SocialCom.2011.47. Preprint arXiv:1107.3689.**
Confirmed on: https://api.crossref.org/works/10.1109/PASSAT/SocialCom.2011.47 ; text read at https://arxiv.org/pdf/1107.3689 . UNVERIFIED: conference location.
- Proposes an automatic edit-war detector and tests it on six language editions — [arXiv PDF](https://arxiv.org/pdf/1107.3689)
- Defines mutual reverts as cases where two editors revert each other; restricting to these changes disputed articles little and removes most reverts on peaceful ones — [arXiv PDF](https://arxiv.org/pdf/1107.3689)
- About 24k articles, under 1% of the 3 million in the November 2009 English dump, are called controversial — [arXiv PDF](https://arxiv.org/pdf/1107.3689)
- Top-30 precision averaged over languages: 85% using revert count, 92% using mutual-revert count, 95% using the final measure M — [arXiv PDF](https://arxiv.org/pdf/1107.3689)
- Relation to revert-label delay: mutual-revert pairs are revert-of-revert chains, the case where an edit's reverted status and the reverting edit's own status both change after the fact.

**S22. T. Yasseri, R. Sumi, A. Rung, A. Kornai, and J. Kertész, "Dynamics of conflicts in Wikipedia," PLoS ONE, vol. 7, no. 6, Art. no. e38869, Jun. 2012. DOI 10.1371/journal.pone.0038869.**
Confirmed on: https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0038869 ; https://api.crossref.org/works/10.1371/journal.pone.0038869
- Reverts found by MD5 hash of each revision's text; a mutual revert is a pair of editors who each reverted the other; self-reverts excluded — [PLoS ONE](https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0038869)
- Controversy measure M weights each mutually reverting pair by the smaller of the two editors' edit counts (so vandal-fighting reverts count little), multiplies by the number of editors involved in mutual reverts, and discounts the top pair — [PLoS ONE](https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0038869)
- Data: January 2010 English Wikipedia dump, 3.2 million articles; about 84k have M above zero, about 12k are controversial, fewer than 100 "super-controversial"; controversial articles are under 1% — [PLoS ONE](https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0038869)
- Three conflict patterns: consensus reached, repeated temporary consensus, never-ending war; edit timing is bursty, more so for mutual reverts — [PLoS ONE](https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0038869)
- Note: S21 reports a November 2009 dump and about 24k controversial articles; S22 reports a January 2010 dump and about 12k. The two differ in threshold and filtering; the fetched summary also shows the paper giving both 223k and 233k for the filtered sample size. UNVERIFIED: which of the two sample sizes is the typo.
- Relation to revert-label delay: the method the side analysis follows; it uses MD5 (not SHA-1) and counts pairs, so pair counts on fresh data are lower bounds until late reverts are labelled.

**S23. M. Tsvetkova, R. García-Gavilanes, L. Floridi, and T. Yasseri, "Even good bots fight: the case of Wikipedia," PLoS ONE, vol. 12, no. 2, Art. no. e0171774, Feb. 2017. DOI 10.1371/journal.pone.0171774.**
Confirmed on: https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0171774 ; https://api.crossref.org/works/10.1371/journal.pone.0171774
- Data: 13 language editions, 2001-2010; reverts detected by matching hashes of full article text — [PLoS ONE](https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0171774)
- Average number of times a bot reverted another bot over the decade: about 105 on English, 24 on German, 185 on Portuguese Wikipedia — [PLoS ONE](https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0171774)
- Timing: human revert gaps cluster near 2 minutes, 24 hours and 1 year; bots' characteristic response time is about 1 month — [PLoS ONE](https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0171774)
- Relation to revert-label delay: gives three characteristic human revert time scales; a label wait shorter than a day misses the second mode.

**S24. R. S. Geiger and A. Halfaker, "Operationalizing conflict and cooperation between automated software agents in Wikipedia: a replication and expansion of 'Even Good Bots Fight'," Proc. ACM Hum.-Comput. Interact., vol. 1, no. CSCW, Article 49, pp. 1-33, Nov. 2017 (Crossref issue date 6 Dec. 2017; the paper's own reference format gives "1, 2, Article 49 (November 2017)"). DOI 10.1145/3134684. Preprint arXiv:1810.07273.**
Confirmed on: https://api.crossref.org/works/10.1145/3134684 ; text read at https://arxiv.org/pdf/1810.07273
- Replicates S23 and concludes most bot-bot reverts are routine or collaborative work, not conflict — [arXiv PDF](https://arxiv.org/pdf/1810.07273)
- Bot-bot reverts are 0.5% to 1% of bot edits to articles in every language studied; about 39% of bot-bot reverts are outside the article namespace — [arXiv PDF](https://arxiv.org/pdf/1810.07273)
- Median bot-bot time to revert across languages and years: 62 days; English mean 355 days, median 138 days; Japanese mean 107 days, median 13 days; English median rose from 26 days (2008) to 299 days (2016) — [arXiv PDF](https://arxiv.org/pdf/1810.07273)
- Uses two metrics to separate conflict from non-conflict: time to revert and reverts per bot pair per page — [arXiv PDF](https://arxiv.org/pdf/1810.07273)
- Relation to revert-label delay: shows that identity reverts can arrive months or years after the edit and that long-delay reverts mean something different from fast ones; a warning for interpreting mutual-revert pair counts.

### Inferences
- A mutual-revert pair count from a live stream will under-count relative to the same count on a settled snapshot, because the second half of a pair may not yet be labelled.
- Bot edits should be excluded or reported separately in any pair count; S24 shows they dominate very long delays.

### Gaps
- The formula for M is rendered as an image on the PLoS page and was read only in words.
- Kittur et al.'s own conflict model details were not read first-hand (see S13).

---

## 5. Temporary accounts / IP masking

### Takeaway
Temporary accounts replace public IP addresses for logged-out editors. They reached 12 pilot wikis in late October and early November 2024, 18 larger Wikipedias in late June 2025, and English Wikipedia on 4 November 2025. Any analysis of "anonymous" editors or editor pairs after that date sees `~YYYY-…` names instead of IPs.

### Cited Findings

**S25. Wikimedia Foundation, "Trust and Safety Product/Temporary Accounts" and its "Updates" subpage, MediaWiki.org. Main page last edited 6 February 2026; Updates page last edited 2 October 2026.**
Confirmed on: https://www.mediawiki.org/wiki/Trust_and_Safety_Product/Temporary_Accounts ; https://www.mediawiki.org/wiki/Trust_and_Safety_Product/Temporary_Accounts/Updates
- Temporary accounts are a new account type for unregistered editors; where enabled, editors' IP addresses are no longer public; IP access is limited to users with the temporary-account IP viewer right and administrators under a Foundation access policy — [project page](https://www.mediawiki.org/wiki/Trust_and_Safety_Product/Temporary_Accounts)
- Rollout dates: testwiki July 2024; 29 October 2024 (five pilot wikis, including Igbo, Swahili and Serbo-Croatian Wikipedia); 5 November 2024 (seven more, including Danish, Romanian, Serbian, Norwegian Bokmål and Cantonese Wikipedia); latter half of June 2025 (MediaWiki.org and 18 large and medium Wikipedias, including French, German, Chinese, Japanese); remaining wikis planned for September 2025 — [Updates page](https://www.mediawiki.org/wiki/Trust_and_Safety_Product/Temporary_Accounts/Updates)
- December 2025 update: about 96% of unregistered editing across Wikimedia wikis came from temporary accounts, up from about one-third six months earlier — [project page](https://www.mediawiki.org/wiki/Trust_and_Safety_Product/Temporary_Accounts)
- Name format `~YYYY-nnnnn-nnn` (example `~2023-27459-041`); accounts last 90 days (an April 2023 plan had said tentatively one year) — [Updates page](https://www.mediawiki.org/wiki/Trust_and_Safety_Product/Temporary_Accounts/Updates)
- Relation to revert-label delay: changes the editor-identity field in the stream and in MediaWiki History; an IP-based "anonymous" flag or an IP-keyed editor pair is not comparable before and after rollout.

**S26. Wikimedia Phabricator, task T409079, "Deploy Temporary accounts to English Wikipedia"; and English Wikipedia, "Wikipedia:Temporary accounts" (project page, last edited 19 October 2026).**
Confirmed on: https://phabricator.wikimedia.org/T409079 ; https://en.wikipedia.org/wiki/Wikipedia:Temporary_accounts
- English Wikipedia deployment: 4 November 2025 (config change synced from about 08:02 UTC); task closed as resolved on 5 November 2025 — [Phabricator T409079](https://phabricator.wikimedia.org/T409079)
- The English Wikipedia project page gives the same date, 4 November 2025 — [Wikipedia:Temporary accounts](https://en.wikipedia.org/wiki/Wikipedia:Temporary_accounts)
- On English Wikipedia: accounts expire 90 days after creation; IP records are kept 90 days after each edit; names are a tilde, the creation year and hyphen-separated digit groups — [Wikipedia:Temporary accounts](https://en.wikipedia.org/wiki/Wikipedia:Temporary_accounts)
- A search-result summary (not opened) gives 12 November 2025 for Spanish Wikipedia, Commons and Wikidata. UNVERIFIED.
- Relation to revert-label delay: fixes the date after which English Wikipedia stream events carry temporary-account names; the Revert Risk model cards (S20a) warn of possible bias against temporary accounts.

### Inferences
- A temporary account is tied to a browser session and expires after 90 days, so one person can appear as several "editors" and several people behind one IP appear as separate editors; mutual-revert pair counts involving unregistered editors are affected in both directions.
- The Revert Risk training windows (2022) predate temporary accounts on all wikis.

### Gaps
- The official MediaWiki.org pages opened do not state the English Wikipedia date; it is documented on Phabricator and the English Wikipedia project page. No Wikimedia Foundation blog post or press statement was opened.
- No opened page confirms the date on which rollout to all remaining wikis completed.
- No source was found on whether temporary accounts changed revert rates or time-to-revert.

---

## 6. Reverts of newcomers

### Takeaway
Halfaker et al. (2013) show that the share of good-faith newcomers whose first-session edits were reverted roughly tripled between 2006 and 2007, that tool-based reverts of newcomers rose from 0% to 40% between 2006 and 2010, and that being reverted predicts lower retention.

### Cited Findings

**S27. A. Halfaker, R. S. Geiger, J. T. Morgan, and J. Riedl, "The rise and decline of an open collaboration system: how Wikipedia's reaction to popularity is causing its decline," American Behavioral Scientist, vol. 57, no. 5, pp. 664-688, May 2013 (online 28 Dec. 2012). DOI 10.1177/0002764212469365.**
Confirmed on: https://api.crossref.org/works/10.1177/0002764212469365 ; text read at https://stuartgeiger.com/papers/abs-rise-and-decline-wikipedia.pdf . UNVERIFIED: print month (May 2013).
- Share of newcomers judged desirable (good-faith) fell from 92.2% (first half of 2005) to 79.8% (first half of 2006) and stayed roughly constant after — [author PDF](https://stuartgeiger.com/papers/abs-rise-and-decline-wikipedia.pdf)
- Share of desirable newcomers with at least one reverted first-session edit rose from 6.1% to 18.2% between the first half of 2006 and the first half of 2007 — [author PDF](https://stuartgeiger.com/papers/abs-rise-and-decline-wikipedia.pdf)
- Tool-based rejection of newcomer edits rose from 0% in 2006 to 40% in 2010; by mid-2008, 75% of new users got their first message from an automated tool — [author PDF](https://stuartgeiger.com/papers/abs-rise-and-decline-wikipedia.pdf)
- Rejection of a desirable newcomer's contribution is a significant negative predictor of retention; desirable-newcomer survival fell to 11.7% and did not recover — [author PDF](https://stuartgeiger.com/papers/abs-rise-and-decline-wikipedia.pdf)
- Relation to revert-label delay: shows reverts are not a pure "damage" label (good-faith edits are reverted too), and that faster, tool-driven reverts carry a social cost.

**S28. A. Halfaker, A. Kittur, and J. Riedl, "Don't bite the newbies: how reverts affect the quantity and quality of Wikipedia work," in Proc. 7th Int. Symp. Wikis and Open Collaboration (WikiSym '11), Mountain View, CA, USA, 2011, pp. 163-172. DOI 10.1145/2038558.2038585.**
Confirmed on: https://api.crossref.org/works/10.1145/2038558.2038585 ; abstract on https://api.openalex.org/works/doi:10.1145/2038558.2038585 . UNVERIFIED: symposium location; paper PDF not opened.
- Analyses 400,000 revisions to measure the effect of being reverted on editors — [OpenAlex abstract](https://api.openalex.org/works/doi:10.1145/2038558.2038585)
- Reverts are strongly demotivating, but on net more quality work results than is lost — [OpenAlex abstract](https://api.openalex.org/works/doi:10.1145/2038558.2038585)
- Most harmful case: new editors reverted by much more experienced editors — [OpenAlex abstract](https://api.openalex.org/works/doi:10.1145/2038558.2038585)
- Relation to revert-label delay: background for S27; supports reading the revert label as "rejected", not "vandalism".

### Inferences
- "Reverted" in the stream and in MediaWiki History includes good-faith rejections; the model cards (S20a, S20b) say the same about what Revert Risk predicts.

### Gaps
- No time-to-revert figure specific to newcomers was found in the text read.

---

## Source count and verification summary
- 28 entries (S1-S19, S20a, S20b, S21-S28): 19 peer-reviewed papers, 9 Wikimedia or MediaWiki documentation pages.
- Full text read: S8, S9, S10, S11, S12, S14, S18, S19, S21, S22 (publisher HTML), S23 (publisher HTML), S24, S27. Abstract only: S1, S13, S15, S16, S17, S28.
- DBLP and ACM Digital Library pages blocked automated access; Crossref DOI records were used instead for bibliographic data. Conference cities are from memory and marked UNVERIFIED where not seen on an opened page.
