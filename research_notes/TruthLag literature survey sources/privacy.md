# Privacy techniques for published data, and privacy of Wikipedia editors and Wikimedia data releases

Research date: 2026-11-17. 22 sources (S1-S22). Every bibliographic record below was opened on the "Confirmed on" URL during this session. Items I could not confirm are marked `UNVERIFIED:`. Statements are paraphrased; nothing is copied at length. No individual Wikipedia editor is named.

How the checks were done: bibliographic fields (authors, title, venue, volume, pages) come from the Crossref record of each DOI (`https://api.crossref.org/works/<DOI>`); abstracts come from OpenAlex / Semantic Scholar records of the same DOI or from the paper PDF itself; Wikimedia facts come from the official pages. DBLP was rate-limited (HTTP 429) and was not used.

---

## Founding papers: k-anonymity, generalization and suppression, l-diversity, t-closeness, Mondrian, hardness

### Takeaway
k-anonymity (1998-2002) requires every quasi-identifier combination to match at least k people, achieved by generalization and suppression; l-diversity (2006/2007) and t-closeness (2007) were introduced because k-anonymity does not stop disclosure of a sensitive attribute; optimal k-anonymization is NP-hard (2004, 2005), so practical systems use greedy methods such as Mondrian (2006).

### Cited Findings

**S1. P. Samarati and L. Sweeney, "Protecting privacy when disclosing information: k-anonymity and its enforcement through generalization and suppression," Computer Science Laboratory, SRI International, Menlo Park, CA, Tech. Rep. SRI-CSL-98-04, 1998.**
- Confirmed on: [SRI CSL report page](https://www.csl.sri.com/papers/sritr-98-04) (title, authors, report number, year); full text opened at [EPIC copy of the PDF](https://epic.org/wp-content/uploads/privacy/reidentification/Samarati_Sweeney_paper.pdf). No DOI.
- Defines the k-anonymity requirement (Definition 2.2): every combination of quasi-identifier values in a release must match at least k individuals — [PDF](https://epic.org/wp-content/uploads/privacy/reidentification/Samarati_Sweeney_paper.pdf)
- Introduces the term quasi-identifier for attributes that are not names but can be linked to public data, and enforces k-anonymity with generalization (coarser values) and suppression (removing values or rows); defines "minimal generalization" (no more distortion than needed) — [PDF](https://epic.org/wp-content/uploads/privacy/reidentification/Samarati_Sweeney_paper.pdf)
- Reports experiments on real medical data, measuring precision and completeness of the release for different k — [PDF](https://epic.org/wp-content/uploads/privacy/reidentification/Samarati_Sweeney_paper.pdf)
- Note on a citation conflict: the Data Privacy Lab page lists a 1998 paper by the same authors as an IEEE S&P paper; SRI's own record gives the tech report above, and a second SRI listing attaches the same report number to the title "Generalizing Data to Provide Anonymity when Disclosing Information" (the PODS 1998 abstract) — [Data Privacy Lab](https://dataprivacylab.org/dataprivacy/projects/kanonymity/index3.html); [SRI](https://www.csl.sri.com/papers/sritr-98-04). Cite the SRI record. UNVERIFIED: any IEEE S&P 1998 version.
- Applies to TruthLag: the group keys of the aggregate tables (hour, editor kind, wiki, etc.) are the quasi-identifiers; a cell with fewer than k contributing editors is the case k-anonymity with suppression removes.

**S2. P. Samarati, "Protecting respondents' identities in microdata release," IEEE Trans. Knowl. Data Eng., vol. 13, no. 6, pp. 1010-1027, Nov./Dec. 2001, doi: 10.1109/69.971193.**
- Confirmed on: [Crossref](https://api.crossref.org/works/10.1109/69.971193) (author, title, journal, vol. 13, no. 6, pp. 1010-1027, 2001). Crossref prints the title without the apostrophe ("respondents identities"). UNVERIFIED: issue month.
- Journal version of the k-anonymity model: a table is k-anonymous if linking attempts map its content to at least k entities — [OpenAlex abstract](https://api.openalex.org/works/https://doi.org/10.1109/69.971193)
- States that generalization and suppression keep the released data truthful (no false values), and gives an algorithm for computing a minimal generalization plus preference policies among minimal generalizations — [OpenAlex abstract](https://api.openalex.org/works/https://doi.org/10.1109/69.971193)
- Names race, birth date, sex and ZIP code as examples of data that can be linked to public sources — [OpenAlex abstract](https://api.openalex.org/works/https://doi.org/10.1109/69.971193)
- Applies to TruthLag: suppression of small cells is the truthful-data option (published counts stay exact; some cells disappear), in contrast to noise addition.

**S3. L. Sweeney, "k-anonymity: A model for protecting privacy," Int. J. Uncertainty, Fuzziness and Knowledge-Based Systems, vol. 10, no. 5, pp. 557-570, Oct. 2002, doi: 10.1142/S0218488502001648.**
- Confirmed on: [Crossref](https://api.crossref.org/works/10.1142/S0218488502001648) (author, title, journal, vol. 10, no. 05, pp. 557-570, Oct. 2002).
- Definition: a release is k-anonymous if each person's information cannot be told apart from that of at least k-1 other people in the release — [Semantic Scholar abstract](https://api.semanticscholar.org/graph/v1/paper/DOI:10.1142/S0218488502001648?fields=title,abstract)
- Examines re-identification attacks that still work on k-anonymous releases unless accompanying policies are followed — [Semantic Scholar abstract](https://api.semanticscholar.org/graph/v1/paper/DOI:10.1142/S0218488502001648?fields=title,abstract)
- States that the model underlies the systems Datafly, mu-Argus and k-Similar — [Semantic Scholar abstract](https://api.semanticscholar.org/graph/v1/paper/DOI:10.1142/S0218488502001648?fields=title,abstract)
- UNVERIFIED: whether this paper itself prints the 87% figure (full text not opened); cite S4 for the number.
- Applies to TruthLag: gives the standard definition to quote for "k editors per published cell".

**S4. L. Sweeney, "Simple demographics often identify people uniquely," Carnegie Mellon University, Pittsburgh, PA, Data Privacy Working Paper 3, 2000.**
- Confirmed on: [Data Privacy Lab project page](https://dataprivacylab.org/projects/identifiability/) (author, title, working paper number, place, year). No DOI.
- Exact source of the 87% finding: using 1990 U.S. Census summary data, 87% of the U.S. population (216 million of 248 million) was likely unique on 5-digit ZIP, gender and date of birth — [Data Privacy Lab](https://dataprivacylab.org/projects/identifiability/)
- About 53% (132 million of 248 million) were likely unique on place (city/town/municipality), gender and date of birth; about 18% on county, gender and date of birth — [Data Privacy Lab](https://dataprivacylab.org/projects/identifiability/)
- Applies to TruthLag: shows that a few coarse attributes combined can single out a person; the analogue is hour x editor kind x wiki x page-level keys producing cells with one editor.

**S5. A. Machanavajjhala, D. Kifer, J. Gehrke, and M. Venkitasubramaniam, "l-diversity: Privacy beyond k-anonymity," ACM Trans. Knowl. Discov. Data, vol. 1, no. 1, Art. 3, Mar. 2007, doi: 10.1145/1217299.1217302.** Conference version: A. Machanavajjhala, J. Gehrke, D. Kifer, and M. Venkitasubramaniam, same title, in Proc. 22nd Int. Conf. Data Engineering (ICDE), 2006, p. 24, doi: 10.1109/ICDE.2006.1.
- Confirmed on: [Crossref, TKDD](https://api.crossref.org/works/10.1145/1217299.1217302) (four authors in the order above, vol. 1, no. 1, article 3, Mar. 2007); [Crossref, ICDE](https://api.crossref.org/works/10.1109/ICDE.2006.1) (author order differs: Machanavajjhala, Gehrke, Kifer, Venkitasubramaniam; p. 24; 2006).
- Shows two attacks on k-anonymous data: (1) the homogeneity case, where a group has little diversity in the sensitive attribute so its value is revealed, and (2) the background-knowledge attack, where outside knowledge rules out values — [OpenAlex abstract](https://api.openalex.org/works/https://doi.org/10.1145/1217299.1217302)
- Proposes l-diversity as the criterion that defends against both, and reports experiments showing it can be implemented efficiently — [OpenAlex abstract](https://api.openalex.org/works/https://doi.org/10.1145/1217299.1217302)
- Definition in words (as restated by S6): each equivalence class must contain at least l "well-represented" values of each sensitive attribute — [OpenAlex abstract of S6](https://api.openalex.org/works/https://doi.org/10.1109/ICDE.2007.367856)
- UNVERIFIED: the names "distinct", "entropy" and "recursive (c,l)" l-diversity for the variants (from memory; full text not opened).
- Applies to TruthLag: if "reverted or not" is treated as the sensitive attribute, a k-anonymous group in which every edit was reverted reveals each member's outcome; l-diversity requires at least l distinct outcomes per group.

**S6. N. Li, T. Li, and S. Venkatasubramanian, "t-closeness: Privacy beyond k-anonymity and l-diversity," in Proc. IEEE 23rd Int. Conf. Data Engineering (ICDE), Istanbul, Turkey, Apr. 2007, pp. 106-115, doi: 10.1109/ICDE.2007.367856.**
- Confirmed on: [Crossref](https://api.crossref.org/works/10.1109/ICDE.2007.367856) (authors, title, proceedings, pp. 106-115, Apr. 2007). UNVERIFIED: conference city.
- Argues l-diversity is "neither necessary nor sufficient" to prevent attribute disclosure — [OpenAlex abstract](https://api.openalex.org/works/https://doi.org/10.1109/ICDE.2007.367856)
- Definition: the distribution of the sensitive attribute inside every equivalence class must be within distance t of its distribution in the whole table; distance is measured with the Earth Mover's Distance — [OpenAlex abstract](https://api.openalex.org/works/https://doi.org/10.1109/ICDE.2007.367856)
- UNVERIFIED: the names "skewness attack" and "similarity attack" for the two l-diversity failures (from memory; full text not opened).
- Applies to TruthLag: a group whose revert rate is far from the overall revert rate leaks information about its members even when it is l-diverse; t-closeness is the measure of that gap.

**S7. K. LeFevre, D. J. DeWitt, and R. Ramakrishnan, "Mondrian multidimensional k-anonymity," in Proc. 22nd Int. Conf. Data Engineering (ICDE), Atlanta, GA, Apr. 2006, p. 25, doi: 10.1109/ICDE.2006.101.**
- Confirmed on: [Crossref](https://api.crossref.org/works/10.1109/ICDE.2006.101) (authors, title, proceedings, page 25, 2006). UNVERIFIED: city and month.
- Proposes a multidimensional recoding model, more flexible than earlier single-dimensional recoding — [OpenAlex abstract](https://api.openalex.org/works/https://doi.org/10.1109/ICDE.2006.101)
- States optimal multidimensional anonymization is NP-hard and gives a simple greedy approximation algorithm — [OpenAlex abstract](https://api.openalex.org/works/https://doi.org/10.1109/ICDE.2006.101)
- Experiments: the greedy algorithm often gives better anonymizations than exhaustive optimal algorithms for two single-dimensional models, by general metrics and by query answerability — [OpenAlex abstract](https://api.openalex.org/works/https://doi.org/10.1109/ICDE.2006.101)
- Applies to TruthLag: the alternative to suppressing small cells is to merge neighbouring cells (e.g. adjacent hours) until each holds k editors; Mondrian is the standard greedy way to do that.

**S8. A. Meyerson and R. Williams, "On the complexity of optimal k-anonymity," in Proc. 23rd ACM SIGMOD-SIGACT-SIGART Symp. Principles of Database Systems (PODS), Paris, France, Jun. 2004, pp. 223-228, doi: 10.1145/1055558.1055591.**
- Confirmed on: [Crossref](https://api.crossref.org/works/10.1145/1055558.1055591) (authors, title, proceedings, pp. 223-228, 14 Jun. 2004). UNVERIFIED: city.
- Proves two general versions of optimal k-anonymization are NP-hard, including the suppression version (delete the fewest entries) — [OpenAlex abstract](https://api.openalex.org/works/https://doi.org/10.1145/1055558.1055591)
- Gives an O(k log k)-approximation (constant at most 4) whose running time is exponential in k, and an O(k log m)-approximation without that condition, m being the number of attributes — [OpenAlex abstract](https://api.openalex.org/works/https://doi.org/10.1145/1055558.1055591)
- Applies to TruthLag: justifies a simple rule (drop every cell below k) instead of a search for the minimum-loss suppression.

**S9. R. J. Bayardo and R. Agrawal, "Data privacy through optimal k-anonymization," in Proc. 21st Int. Conf. Data Engineering (ICDE), Tokyo, Japan, Apr. 2005, pp. 217-228, doi: 10.1109/ICDE.2005.42.**
- Confirmed on: [Crossref](https://api.crossref.org/works/10.1109/ICDE.2005.42) (authors, title, proceedings ICDE'05, pp. 217-228; Crossref gives no date). UNVERIFIED: city and month.
- States that even simple restrictions of optimized k-anonymity are NP-hard — [OpenAlex abstract](https://api.openalex.org/works/https://doi.org/10.1109/ICDE.2005.42)
- Presents a search algorithm that finds optimal k-anonymizations of real census data under two cost measures over a wide range of k; claims the first optimal result on a non-trivial dataset under a general model — [OpenAlex abstract](https://api.openalex.org/works/https://doi.org/10.1109/ICDE.2005.42)
- Applies to TruthLag: source for the idea of scoring an anonymization by a cost measure (information lost), which is what "rows and edits suppressed at each k" reports.

### Inferences
- The founding papers all address microdata (one row per person). TruthLag publishes only grouped counts, so k-anonymity there means "each published cell covers at least k distinct editors" and suppression is the only operation needed.
- Generalization in this setting = coarser group keys (day instead of hour, merged editor kinds).

### Gaps
- Full texts of S3, S5, S6, S7 were not opened; only publisher metadata and abstracts were. Variant names and attack names not in the abstracts are flagged UNVERIFIED above.
- DBLP records were not reachable (rate limit); conference cities and months are from memory and flagged.

---

## Differential privacy: definition, Laplace mechanism, error, composition, streams

### Takeaway
Differential privacy (2006) bounds how much any one person's data can change the output distribution; for a count the Laplace mechanism adds noise of scale sensitivity/epsilon, giving expected absolute error 1/epsilon for a sensitivity-1 count regardless of data size, and privacy losses add up across releases. Continual release of a running count needs the tree-based counters of 2010/2011 to keep error polylogarithmic in the number of time steps.

### Cited Findings

**S10. C. Dwork, F. McSherry, K. Nissim, and A. Smith, "Calibrating noise to sensitivity in private data analysis," in Theory of Cryptography (TCC 2006), Lecture Notes in Computer Science, vol. 3876. Berlin, Germany: Springer, 2006, pp. 265-284, doi: 10.1007/11681878_14.**
- Confirmed on: [Crossref](https://api.crossref.org/works/10.1007/11681878_14) (four authors, title, LNCS / Theory of Cryptography, pp. 265-284, 2006). UNVERIFIED: LNCS volume number 3876.
- Source of the Laplace mechanism, per the bibliographic notes of S12 (Section 3.7) — [Dwork and Roth PDF](https://www.cis.upenn.edu/~aaroth/Papers/privacybook.pdf)
- Cited by the Wikimedia pageview paper (S17) as the basis for its epsilon-DP guarantee with Laplace noise — [arXiv 2308.16298](https://arxiv.org/abs/2308.16298)
- UNVERIFIED: this paper's own wording of the definition ("epsilon-indistinguishability") — full text not opened.
- Applies to TruthLag: the primary citation for "add Laplace noise scaled to sensitivity/epsilon to each grouped count".

**S11. C. Dwork, "Differential privacy," in Automata, Languages and Programming (ICALP 2006), Part II, Lecture Notes in Computer Science, vol. 4052. Berlin, Germany: Springer, 2006, pp. 1-12, doi: 10.1007/11787006_1.**
- Confirmed on: [Crossref](https://api.crossref.org/works/10.1007/11787006_1) (author, title, LNCS / Automata, Languages and Programming, pp. 1-12, 2006). UNVERIFIED: LNCS volume 4052 and "Part II".
- UNVERIFIED: content (the paper that names "differential privacy" and argues that absolute disclosure prevention is impossible when the adversary has auxiliary information) — from memory; full text not opened. Use only as the naming citation.
- Applies to TruthLag: citation for the term itself.

**S12. C. Dwork and A. Roth, "The algorithmic foundations of differential privacy," Foundations and Trends in Theoretical Computer Science, vol. 9, nos. 3-4, pp. 211-407, Aug. 2014, doi: 10.1561/0400000042.**
- Confirmed on: [Crossref](https://api.crossref.org/works/10.1561/0400000042) (authors, title, journal, vol. 9, no. 3-4, 2014). Conflict: Crossref gives pages 211-487; the commonly cited range is 211-407. UNVERIFIED: which page range is right — check the publisher page before finalizing. Full text opened at [author PDF](https://www.cis.upenn.edu/~aaroth/Papers/privacybook.pdf).
- Definition 2.4: a randomized algorithm M is (epsilon, delta)-differentially private if, for any two databases differing in one record and any set S of outputs, Pr[M(x) in S] <= exp(epsilon) * Pr[M(y) in S] + delta — [PDF](https://www.cis.upenn.edu/~aaroth/Papers/privacybook.pdf)
- Definition 3.1 and 3.3, Theorem 3.6: the l1-sensitivity of f is the largest change in f when one record changes; the Laplace mechanism adds independent Lap(sensitivity/epsilon) noise to each output coordinate and is (epsilon, 0)-differentially private — [PDF](https://www.cis.upenn.edu/~aaroth/Papers/privacybook.pdf)
- Example 3.1: a counting query has sensitivity 1, so Lap(1/epsilon) noise suffices, and the expected error is 1/epsilon "independent of the size of the database" — [PDF](https://www.cis.upenn.edu/~aaroth/Papers/privacybook.pdf). Worked values of 1/epsilon: epsilon 0.1 -> 10; 0.5 -> 2; 1 -> 1; 2 -> 0.5 (arithmetic, not from the source).
- Example 3.2: a histogram (disjoint cells) has sensitivity 1 as a whole, so every cell gets Lap(1/epsilon) noise without splitting the budget across cells — [PDF](https://www.cis.upenn.edu/~aaroth/Papers/privacybook.pdf)
- Theorem 3.16 (basic composition): running k mechanisms that are (epsilon_i, delta_i)-private gives a combined mechanism that is (sum of epsilon_i, sum of delta_i)-private; Theorem 3.20 is the advanced composition bound — [PDF](https://www.cis.upenn.edu/~aaroth/Papers/privacybook.pdf)
- Theorem 3.8 gives a tail bound on the Laplace mechanism's maximum error over k outputs involving ln(k/delta) * (sensitivity/epsilon). UNVERIFIED: exact form of the inequality (the PDF text extraction garbled the formula) — [PDF](https://www.cis.upenn.edu/~aaroth/Papers/privacybook.pdf)
- Applies to TruthLag: the grouped edit/revert tables are histograms, so the reported mean absolute error at each epsilon should be near 1/epsilon per cell if one editor changes one cell by one; publishing several tables from the same data spends the sum of their epsilons.

**S13. C. Dwork, M. Naor, T. Pitassi, and G. N. Rothblum, "Differential privacy under continual observation," in Proc. 42nd ACM Symp. Theory of Computing (STOC), Cambridge, MA, Jun. 2010, pp. 715-724, doi: 10.1145/1806689.1806787.**
- Confirmed on: [Crossref](https://api.crossref.org/works/10.1145/1806689.1806787) (authors, title, proceedings, pp. 715-724, 5 Jun. 2010). UNVERIFIED: city.
- Notes that earlier differential-privacy work assumed a static dataset and a one-shot computation, while monitoring tasks (traffic, search trends, flu incidence) need repeated outputs — [OpenAlex abstract](https://api.openalex.org/works/https://doi.org/10.1145/1806689.1806787)
- Starts the study of privacy under continual observation and identifies the private counter (running count) as the core problem with wide applicability — [OpenAlex abstract](https://api.openalex.org/works/https://doi.org/10.1145/1806689.1806787)
- UNVERIFIED: the error bound (order log^1.5 T / epsilon for T steps, event-level privacy) — from memory.
- Applies to TruthLag: a live count of edits or reverts republished every window is a continual-observation release; naive fresh Laplace noise per release makes the privacy loss grow with the number of releases (S12 Theorem 3.16).

**S14. T.-H. H. Chan, E. Shi, and D. Song, "Private and continual release of statistics," ACM Trans. Inf. Syst. Secur., vol. 14, no. 3, Art. 26, pp. 1-24, Nov. 2011, doi: 10.1145/2043621.2043626.**
- Confirmed on: [Crossref](https://api.crossref.org/works/10.1145/2043621.2043626) (authors, title, journal, vol. 14, no. 3, pp. 1-24, Nov. 2011). UNVERIFIED: article number 26.
- Setting: a stream of 0s and 1s; the mechanism outputs at every time step an approximate count of 1s so far, under differential privacy — [OpenAlex abstract](https://api.openalex.org/works/https://doi.org/10.1145/2043621.2043626)
- Result: the counter's error is only polylogarithmic in the number of time steps; extends to continually releasing top-k and hot items — [OpenAlex abstract](https://api.openalex.org/works/https://doi.org/10.1145/2043621.2043626)
- UNVERIFIED: the name "binary mechanism" for the construction — from memory.
- Applies to TruthLag: the direct reference for a private running revert count on a stream; the project's per-table Laplace noise is the one-shot case.

**S15. Ú. Erlingsson, V. Pihur, and A. Korolova, "RAPPOR: Randomized aggregatable privacy-preserving ordinal response," in Proc. 2014 ACM SIGSAC Conf. Computer and Communications Security (CCS), Scottsdale, AZ, Nov. 2014, pp. 1054-1067, doi: 10.1145/2660267.2660348.** (optional)
- Confirmed on: [Crossref](https://api.crossref.org/works/10.1145/2660267.2660348) (authors, short title "RAPPOR", proceedings, pp. 1054-1067, 3 Nov. 2014). UNVERIFIED: full subtitle and city (Crossref stores only "RAPPOR").
- UNVERIFIED: content (local differential privacy by randomized response on the client, deployed in Chrome) — from memory; abstract not opened.
- Applies to TruthLag: contrast case only. TruthLag adds noise centrally after aggregation; RAPPOR adds it before collection.

### Inferences
- Sensitivity 1 holds only if the protected unit is one edit (event-level). If the unit is one editor, sensitivity equals the largest number of edits one editor can add to a cell, unless contributions are capped; S17 caps contributions for exactly this reason.
- Because Laplace error is about 1/epsilon in absolute terms whatever the count, relative error is large on small cells and negligible on large ones (follows from S12 Example 3.1).

### Gaps
- No source opened states "Laplace noise with scale b has mean absolute value b and variance 2b^2" in those words; S12 Example 3.1 gives the expected error 1/epsilon for counts, which is the same fact for b = 1/epsilon.
- S10, S11 and S15 full texts were not opened.

---

## Re-identification failures that motivate these methods

### Takeaway
Three well-documented cases show that removing names is not anonymization: search logs (AOL, 2006), movie ratings (Netflix Prize, 2008) and location traces (2013) were each re-identified from a handful of data points plus outside information.

### Cited Findings

**S16. A. Narayanan and V. Shmatikov, "Robust de-anonymization of large sparse datasets," in Proc. 2008 IEEE Symp. Security and Privacy (S&P), Oakland, CA, May 2008, pp. 111-125, doi: 10.1109/SP.2008.33.**
- Confirmed on: [Crossref](https://api.crossref.org/works/10.1109/SP.2008.33) (authors, title, proceedings, pp. 111-125, May 2008); preprint "How To Break Anonymity of the Netflix Prize Dataset" at [arXiv cs/0610105](https://arxiv.org/abs/cs/0610105). UNVERIFIED: city.
- Presents statistical de-anonymization attacks on high-dimensional sparse microdata that tolerate perturbed data and errors in the attacker's background knowledge — [OpenAlex abstract](https://api.openalex.org/works/https://doi.org/10.1109/SP.2008.33)
- Applied to the Netflix Prize dataset (ratings of about 500,000 subscribers): an attacker who knows a little about one subscriber can find that subscriber's record; using the Internet Movie Database as background, the authors identified known users' records and inferred apparent political preferences — [arXiv abstract](https://arxiv.org/abs/cs/0610105)
- UNVERIFIED: the specific figure that 8 ratings with dates within 14 days identify 99% of records — from memory; full text not opened.
- Applies to TruthLag: an editor's row-level history (pages, times) is the same kind of sparse high-dimensional record; this is the argument for publishing aggregates only.

**S17a. M. Barbaro and T. Zeller Jr., "A face is exposed for AOL searcher no. 4417749," The New York Times, Aug. 9, 2006. URL: https://www.nytimes.com/2006/08/09/technology/09aol.html**
- PARTLY VERIFIED: the nytimes.com page could not be opened (fetch blocked). Headline, byline and date were confirmed only through search-result excerpts of the article — [search hit: John Battelle's Searchblog](https://battellemedia.com/archives/2006/08/nyt_finds_an_aol_searcher); [search hit: Search Engine Watch](https://searchenginewatch.com/?p=9181). UNVERIFIED: section and print page (commonly given as p. A1).
- From the search excerpt of the article's opening: AOL released about 20 million search queries with users replaced by numbers; reporters identified the person behind one number from the content of that user's queries over three months — [Searchblog](https://battellemedia.com/archives/2006/08/nyt_finds_an_aol_searcher)
- UNVERIFIED: the count of about 650,000-658,000 users in the release — from memory.
- Applies to TruthLag: a pseudonymous id (like a temporary-account name) attached to a detailed activity log does not prevent identification; aggregate counts carry no per-user log.

**S18. Y.-A. de Montjoye, C. A. Hidalgo, M. Verleysen, and V. D. Blondel, "Unique in the crowd: The privacy bounds of human mobility," Scientific Reports, vol. 3, Art. no. 1376, Mar. 2013, doi: 10.1038/srep01376.**
- Confirmed on: [Crossref](https://api.crossref.org/works/10.1038/srep01376) and [PubMed Central PMC3607247](https://pmc.ncbi.nlm.nih.gov/articles/PMC3607247/) (authors, title, journal, vol. 3, article 1376, 25 Mar. 2013).
- Data: 15 months of mobility records for about 1.5 million mobile-phone users — [PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC3607247/)
- Four spatio-temporal points (hourly, antenna-level) uniquely identify about 95% of individuals — [PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC3607247/)
- Coarsening helps little: uniqueness falls roughly as the 1/10 power of the resolution — [PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC3607247/)
- Applies to TruthLag: coarsening hour to day does not by itself make small cells safe; the count of people per cell (k) must be checked.

### Inferences
- Edit timestamps are public and exact on Wikipedia, so any released table that can be joined back to the public edit history by (hour, wiki, editor kind) inherits the linkage risk these papers describe.

### Gaps
- The NYT article itself was not opened (S17a); treat its details as secondary until someone opens the page.

---

## Wikimedia-specific: differential privacy releases, policies, temporary accounts, editor profiling

### Takeaway
The Wikimedia Foundation publishes per-country pageview counts under differential privacy (Tumult Analytics; rho = 0.0151 zCDP for current data, epsilon = 1 for historical data, with suppression thresholds), while edit metadata (account name, timestamp) is a permanent public record; since 2024-2025 logged-out editors appear under temporary account names and their IP addresses are visible only to vetted users for 90 days. One peer-reviewed study shows private traits of editors can be predicted from coarse edit counts.

### Cited Findings

**S17. T. Adeleye, S. Berghel, D. Desfontaines, M. Hay, I. Johnson, C. Lemoisson, A. Machanavajjhala, T. Magerlein, G. Modena, D. Pujol, D. Simmons-Marengo, and H. Triedman, "Publishing Wikipedia usage data with strong privacy guarantees," arXiv:2308.16298, Aug. 2023 (v3, Jul. 2025); presented at Theory and Practice of Differential Privacy (TPDP) 2023. doi: 10.48550/arXiv.2308.16298.**
- Confirmed on: [arXiv abstract page](https://arxiv.org/abs/2308.16298) (title, 12 authors in this order, dates, TPDP 2023 note); full text read from [arXiv PDF v3](https://arxiv.org/pdf/2308.16298). The arXiv page gives authors' full first names: Temilola, Skye, Damien, Michael, Isaac, Cléo, Ashwin, Tom, Gabriele, David, Daniel, Hal.
- Release: daily pageview counts per page, project and country, started June 2023, built with Tumult Analytics (chosen after a comparison of open-source tools) — [PDF, Sec. 1 and 4.3](https://arxiv.org/pdf/2308.16298)
- Privacy parameters: zero-concentrated DP with rho = 0.0151 for current data (stated as stronger than (epsilon = 1, delta = 1e-7)-DP), and pure epsilon = 1 DP for historical data — [PDF, Sec. 3](https://arxiv.org/pdf/2308.16298)
- Privacy unit (Table 5): one user-day from 6 Feb 2023; 30 daily pageviews for 9 Feb 2017 - 5 Feb 2023; 300 daily pageviews for 1 Jul 2015 - 8 Feb 2017 — [PDF, Sec. 3](https://arxiv.org/pdf/2308.16298)
- Mechanism: current data caps each device at k = 10 pageviews per day (client-side), adds Gaussian noise, keeps pages above an ingestion threshold t = 150 and suppresses noisy counts below tau = 90; historical data uses Laplace noise with tau = 450 (2017-2023) and tau = 3500 (2015-2017) — [PDF, Sec. 4](https://arxiv.org/pdf/2308.16298)
- Utility metrics defined: relative error, drop rate (true non-zero counts missing from the output) and spurious rate (output counts whose true value is zero) — [PDF, Sec. 3](https://arxiv.org/pdf/2308.16298)
- Reported utility: current data, over 95% of counts have relative error below 50%, drop rate above 150 is under 0.1%, global spurious rate under 0.01%; 2017-2023 data, drop rate above 450 under 3%, spurious rate under 0.1%; 2015-2017 data, spurious rate under 20% — [PDF, Sec. 5](https://arxiv.org/pdf/2308.16298)
- Scale: more than 135 million statistics covering 325 billion pageviews released for previously unpublished days; median data points per day rose from 9,000 to 360,000 (Table 6, as of 29 Jun 2023) — [PDF, Sec. 5](https://arxiv.org/pdf/2308.16298)
- Notes that before 9 Feb 2017, editors previewing a page were logged as pageviews, so heavy editors could contribute many views; this is why the older data protects 300 views — [PDF, Sec. 3](https://arxiv.org/pdf/2308.16298)
- Applies to TruthLag: the closest published precedent. It combines the same two tools TruthLag uses (noise plus threshold suppression of small noisy counts), reports error with drop/spurious rates, and uses epsilon = 1 as a reference value for count data.

**S19. Wikimedia Foundation, "Differential privacy," Meta-Wiki. [Online]. Available: https://meta.wikimedia.org/wiki/Differential_privacy (last edited 29 Oct. 2024; accessed 17 Nov. 2026).** With subpage: "Differential privacy/Completed/Geoeditors/Feasibility report," https://meta.wikimedia.org/wiki/Differential_privacy/Completed/Geoeditors/Feasibility_report (last edited 29 Aug. 2023).
- Confirmed on: both URLs above (opened).
- Lists the Foundation's differentially private releases: pageviews historical (pre-2017), historical (9 Feb 2017 - 5 Feb 2023), current (6 Feb 2023 onward), and Geoeditors weekly and monthly — [Meta-Wiki](https://meta.wikimedia.org/wiki/Differential_privacy)
- Geoeditors data = number of active editors by project, country and month, in activity buckets 1-4, 5-99 and 100+ edits; the earlier non-DP release used rounded upper bounds and ranges, and left out countries judged risky — [Feasibility report](https://meta.wikimedia.org/wiki/Differential_privacy/Completed/Geoeditors/Feasibility_report)
- The report frames the release as a histogram query with Laplace noise of scale 1/epsilon (sensitivity 1 when the unit is one editor per country-project-month), and names a linkage risk: joining the release with public edit history could reveal an editor's country, e.g. for a page edited once in a month — [Feasibility report](https://meta.wikimedia.org/wiki/Differential_privacy/Completed/Geoeditors/Feasibility_report)
- The report notes logged-out (IP) editors are hard to bound because one person can appear under several IP addresses — [Feasibility report](https://meta.wikimedia.org/wiki/Differential_privacy/Completed/Geoeditors/Feasibility_report)
- UNVERIFIED: the epsilon and release threshold actually used for Geoeditors (the landing page and feasibility report give none; the dataset README was not found).
- Applies to TruthLag: an official Wikimedia example of DP applied to editor counts (not reader counts), with the same structure as TruthLag's grouped counts and an explicit statement of the join-with-public-history risk.

**S20. Wikimedia Foundation, "Privacy Policy," Wikimedia Foundation Governance Wiki. [Online]. Available: https://foundation.wikimedia.org/wiki/Policy:Privacy_policy (version approved 3 Sep. 2025, effective 6 Oct. 2025; accessed 17 Nov. 2026).** With: "Data Retention Guidelines," https://foundation.wikimedia.org/wiki/Legal:Data_retention_guidelines (last edited 20 Feb. 2026).
- Confirmed on: both URLs above (opened).
- Edits are a permanent public record that shows the account or temporary-account name and the timestamp; content can remain visible in history after removal — [Privacy Policy](https://foundation.wikimedia.org/wiki/Policy:Privacy_policy)
- Logged-out edits are attributed to a temporary account tied to the browser; the IP address is recorded temporarily and is not public — [Privacy Policy](https://foundation.wikimedia.org/wiki/Policy:Privacy_policy)
- Non-public personal data (IP address, user agent) is deleted, aggregated or de-identified after at most 90 days; non-personal account activity and public contributions are kept indefinitely — [Data Retention Guidelines](https://foundation.wikimedia.org/wiki/Legal:Data_retention_guidelines)
- The guidelines define "aggregated" with the example of reporting "between 1 and 10 editors" instead of an exact small number; the policy warns that aggregated data can still allow inferences such as country or gender — [Data Retention Guidelines](https://foundation.wikimedia.org/wiki/Legal:Data_retention_guidelines); [Privacy Policy](https://foundation.wikimedia.org/wiki/Policy:Privacy_policy)
- Applies to TruthLag: the input stream (who edited what, when) is public by policy, so TruthLag's privacy analysis concerns what its own derived tables add or make easier, not the secrecy of the edits; the Foundation's own "1 to 10 editors" range is a small-count suppression rule of the same kind.

**S21. Wikimedia Foundation, "Trust and Safety Product/Temporary Accounts," MediaWiki.org. [Online]. Available: https://www.mediawiki.org/wiki/Trust_and_Safety_Product/Temporary_Accounts (last edited 6 Feb. 2026; accessed 17 Nov. 2026).** With: "Temporary Accounts/Updates," https://www.mediawiki.org/wiki/Trust_and_Safety_Product/Temporary_Accounts/Updates (last edited 2 Oct. 2026); "Wikimedia Access to Temporary Account IP Addresses Policy," https://foundation.wikimedia.org/wiki/Policy:Wikimedia_Access_to_Temporary_Account_IP_Addresses_Policy (last edited 1 Apr. 2026); deployment task T409079, https://phabricator.wikimedia.org/T409079.
- Confirmed on: all four URLs above (opened).
- What is hidden: on wikis with the feature, unregistered editors are shown under a temporary account name of the form ~YYYY-nnnnn-nnn instead of their IP address; a temporary account lasts 90 days — [project page](https://www.mediawiki.org/wiki/Trust_and_Safety_Product/Temporary_Accounts); [Updates](https://www.mediawiki.org/wiki/Trust_and_Safety_Product/Temporary_Accounts/Updates)
- Who can see the IP address: stewards, ombuds, U4C members, staff, and local CheckUsers and oversighters automatically; administrators and some global groups by opting in; other users only on request with an account at least 6 months old and at least 300 local edits; every reveal is logged; IP data is kept 90 days — [access policy](https://foundation.wikimedia.org/wiki/Policy:Wikimedia_Access_to_Temporary_Account_IP_Addresses_Policy)
- Rollout: test wiki July 2024; first pilots 29 Oct. 2024 (5 wikis) and 5 Nov. 2024 (7 wikis); 18 large and medium Wikipedias plus MediaWiki.org in late June 2025; English Wikipedia 4 Nov. 2025 — [Updates](https://www.mediawiki.org/wiki/Trust_and_Safety_Product/Temporary_Accounts/Updates); [T409079](https://phabricator.wikimedia.org/T409079)
- By December 2025 about 96% of unregistered editing across Wikimedia wikis came from temporary accounts — [project page](https://www.mediawiki.org/wiki/Trust_and_Safety_Product/Temporary_Accounts)
- UNVERIFIED: the date the rollout finished on all wikis (the Updates page states only a plan for September 2025 and a December 2025 "last deployments" heading). The Signpost of 10 Nov. 2025 says more than one thousand other wikis had the feature before English Wikipedia — [Signpost](https://signpost.news/2025-11-10/News_and_notes) (community newspaper, secondary).
- Applies to TruthLag: explains the "temporary account" editor kind in the stream and why its definition changes by wiki and date; a temporary account is a pseudonym, so cells with few temporary accounts still need the k check.

**S22. M.-A. Rizoiu, L. Xie, T. Caetano, and M. Cebrian, "Evolution of privacy loss in Wikipedia," in Proc. 9th ACM Int. Conf. Web Search and Data Mining (WSDM), San Francisco, CA, Feb. 2016, pp. 215-224, doi: 10.1145/2835776.2835798.**
- Confirmed on: [Crossref](https://api.crossref.org/works/10.1145/2835776.2835798) (authors, title, proceedings, pp. 215-224, 8 Feb. 2016); abstract at [arXiv 1512.03523](https://arxiv.org/abs/1512.03523). UNVERIFIED: city.
- Data: 13 years of Wikipedia edit history, 188,805,088 edits by more than 117,523 users — [arXiv abstract](https://arxiv.org/abs/1512.03523)
- Features were only the number of edits per broad topic category per time period; standard classifiers predicted undisclosed gender, religion and education from them — [arXiv abstract](https://arxiv.org/abs/1512.03523)
- Prediction accuracy for almost all traits rose over time, including for users who had stopped editing; new users' activity contributed more to the rise than extra activity by existing users — [arXiv abstract](https://arxiv.org/abs/1512.03523)
- Applies to TruthLag: evidence that per-editor aggregate edit counts are themselves sensitive, which supports publishing only cells that cover many editors and never per-editor rows.

### Inferences
- Wikimedia's practice sets a concrete benchmark for the report: epsilon = 1 (or the stronger rho = 0.0151) per release for count data, with contribution capping and threshold suppression on top of the noise.
- TruthLag's editor-kind key changed meaning during the capture window on wikis where temporary accounts were switched on (IP editors became temporary accounts), by wiki and date per S21.

### Gaps
- No Wikimedia page opened states an epsilon for the Geoeditors release.
- Only one peer-reviewed study of profiling Wikipedia editors from edit metadata was found and verified (S22). I found no verified study that de-anonymizes editors (links accounts to real identities) from edit timestamps; none is cited.
- The Tumult Analytics software itself is cited inside S17 (reference "Tumult Labs. Tumult Analytics. https://tmlt.dev, December 2022"); that page was not opened.

---

## Known trade-offs: utility loss, and why k-anonymity alone is not enough

### Takeaway
Suppression loses whole cells (worst for rare groups), noise loses accuracy on small counts (error is about 1/epsilon whatever the count), and k-anonymity gives no protection for the sensitive attribute and no guarantee when several releases are combined; differential privacy composes with an additive, stated cost.

### Cited Findings

**S23. S. R. Ganta, S. P. Kasiviswanathan, and A. Smith, "Composition attacks and auxiliary information in data privacy," in Proc. 14th ACM SIGKDD Int. Conf. Knowledge Discovery and Data Mining (KDD), Las Vegas, NV, Aug. 2008, pp. 265-273, doi: 10.1145/1401890.1401926.**
- Confirmed on: [Crossref](https://api.crossref.org/works/10.1145/1401890.1401926) (authors, title, proceedings, pp. 265-273, 24 Aug. 2008). UNVERIFIED: city.
- Defines composition attacks: an adversary combines independent anonymized releases about overlapping populations to breach privacy — [Semantic Scholar abstract](https://api.semanticscholar.org/graph/v1/paper/DOI:10.1145/1401890.1401926?fields=title,abstract)
- Experiments show a simple composition attack breaches privacy in practice for a class of methods that includes k-anonymity and several of its variants — [Semantic Scholar abstract](https://api.semanticscholar.org/graph/v1/paper/DOI:10.1145/1401890.1401926?fields=title,abstract)
- Shows that differential privacy and a class of its relaxations provably resist composition attacks and arbitrary side information — [Semantic Scholar abstract](https://api.semanticscholar.org/graph/v1/paper/DOI:10.1145/1401890.1401926?fields=title,abstract)
- Applies to TruthLag: the project publishes several tables over the same edits (by hour, by editor kind, live vs reconciled); each may be k-anonymous alone and still leak when differenced, whereas the DP versions have a known total cost (sum of epsilons).

Other trade-off facts already sourced above:
- k-anonymity does not prevent attribute disclosure (homogeneity and background-knowledge attacks) — [S5 abstract](https://api.openalex.org/works/https://doi.org/10.1145/1217299.1217302); l-diversity is in turn neither necessary nor sufficient — [S6 abstract](https://api.openalex.org/works/https://doi.org/10.1109/ICDE.2007.367856)
- Minimum-loss suppression is NP-hard — [S8 abstract](https://api.openalex.org/works/https://doi.org/10.1145/1055558.1055591)
- Laplace error on a count is 1/epsilon in expectation, independent of the count's size — [S12, Example 3.1](https://www.cis.upenn.edu/~aaroth/Papers/privacybook.pdf)
- Privacy loss adds across releases — [S12, Theorem 3.16](https://www.cis.upenn.edu/~aaroth/Papers/privacybook.pdf)
- In practice noise on zero or tiny counts creates spurious rows and high relative error, so Wikimedia suppresses noisy counts below a threshold and accepts a non-zero drop rate (e.g. up to 20% spurious rate on its oldest data) — [S17, Sec. 3-5](https://arxiv.org/pdf/2308.16298)
- Coarsening the data reduces uniqueness only slowly (about the 1/10 power of resolution) — [S18](https://pmc.ncbi.nlm.nih.gov/articles/PMC3607247/)

### Inferences
- For a cell with true count c, relative error from Laplace noise is about 1/(epsilon * c): with epsilon = 1 about 10% at c = 10 and 1% at c = 100; with epsilon = 0.1 about 100% at c = 10. (Arithmetic from S12 Example 3.1.)
- Revert rates are ratios of two noisy counts, so their error is larger than either count's error in small cells.
- k-anonymity with suppression and DP noise are complementary in the Wikimedia design (S17): noise gives the guarantee, the threshold removes cells the noise has made useless.

### Gaps
- No survey paper on the utility cost of k-anonymity (e.g. Aggarwal 2005 on high dimensionality, Brickell and Shmatikov 2008) was opened or verified; none is cited.

---

## Source index (IEEE-style short list)

| # | Short reference | Stable link | Verification |
|---|---|---|---|
| S1 | Samarati and Sweeney, SRI-CSL-98-04, 1998 | https://www.csl.sri.com/papers/sritr-98-04 | record + full text |
| S2 | Samarati, IEEE TKDE 13(6), 2001 | https://doi.org/10.1109/69.971193 | record + abstract |
| S3 | Sweeney, IJUFKS 10(5), 2002 | https://doi.org/10.1142/S0218488502001648 | record + abstract |
| S4 | Sweeney, CMU Data Privacy WP 3, 2000 | https://dataprivacylab.org/projects/identifiability/ | official page |
| S5 | Machanavajjhala et al., ACM TKDD 1(1), 2007 (ICDE 2006) | https://doi.org/10.1145/1217299.1217302 | record + abstract |
| S6 | Li, Li, Venkatasubramanian, ICDE 2007 | https://doi.org/10.1109/ICDE.2007.367856 | record + abstract |
| S7 | LeFevre, DeWitt, Ramakrishnan, ICDE 2006 | https://doi.org/10.1109/ICDE.2006.101 | record + abstract |
| S8 | Meyerson and Williams, PODS 2004 | https://doi.org/10.1145/1055558.1055591 | record + abstract |
| S9 | Bayardo and Agrawal, ICDE 2005 | https://doi.org/10.1109/ICDE.2005.42 | record + abstract |
| S10 | Dwork, McSherry, Nissim, Smith, TCC 2006 | https://doi.org/10.1007/11681878_14 | record only |
| S11 | Dwork, ICALP 2006 | https://doi.org/10.1007/11787006_1 | record only |
| S12 | Dwork and Roth, FnT TCS 9(3-4), 2014 | https://doi.org/10.1561/0400000042 | record + full text |
| S13 | Dwork, Naor, Pitassi, Rothblum, STOC 2010 | https://doi.org/10.1145/1806689.1806787 | record + abstract |
| S14 | Chan, Shi, Song, ACM TISSEC 14(3), 2011 | https://doi.org/10.1145/2043621.2043626 | record + abstract |
| S15 | Erlingsson, Pihur, Korolova, CCS 2014 | https://doi.org/10.1145/2660267.2660348 | record only |
| S16 | Narayanan and Shmatikov, IEEE S&P 2008 | https://doi.org/10.1109/SP.2008.33 | record + abstract |
| S17a | Barbaro and Zeller, NYT, 9 Aug. 2006 | https://www.nytimes.com/2006/08/09/technology/09aol.html | search excerpts only |
| S18 | de Montjoye et al., Sci. Rep. 3:1376, 2013 | https://doi.org/10.1038/srep01376 | record + abstract |
| S17 | Adeleye et al., arXiv:2308.16298, 2023 | https://arxiv.org/abs/2308.16298 | record + full text |
| S19 | WMF, Differential privacy (Meta-Wiki) | https://meta.wikimedia.org/wiki/Differential_privacy | official pages |
| S20 | WMF, Privacy Policy; Data Retention Guidelines | https://foundation.wikimedia.org/wiki/Policy:Privacy_policy | official pages |
| S21 | WMF, Temporary Accounts; IP access policy | https://www.mediawiki.org/wiki/Trust_and_Safety_Product/Temporary_Accounts | official pages |
| S22 | Rizoiu et al., WSDM 2016 | https://doi.org/10.1145/2835776.2835798 | record + abstract |
| S23 | Ganta, Kasiviswanathan, Smith, KDD 2008 | https://doi.org/10.1145/1401890.1401926 | record + abstract |

Numbering note: S17 (Adeleye et al.) and S17a (NYT) are separate sources; 24 entries in total, of which S17a is only partly verified and S10, S11, S15 are verified as bibliographic records only.
