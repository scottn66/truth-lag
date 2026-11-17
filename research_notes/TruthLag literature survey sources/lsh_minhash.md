# MinHash and Locality-Sensitive Hashing (LSH) for near-duplicate and similarity search, incl. Wikipedia edit text

How each entry was checked (read this first):
- "CR" = bibliographic record opened in the Crossref DOI registry API (`https://api.crossref.org/works/<DOI>`); "OA" = OpenAlex record (`https://api.openalex.org/works/doi:<DOI>`), which also supplied the abstract text. The DOI link given is the stable URL.
- DBLP could not be used (it served a bot check to scripted access); vldb.org returned 403; infolab.stanford.edu (host of the MMDS book chapter PDFs) refused connections on 2026-11-17.
- Content bullets come from the abstract or from the full text only where "full text read" is stated. Anything recalled but not seen in an opened source is marked UNVERIFIED.
- 22 numbered sources (S1-S22) plus 3 unnumbered ones in section 5 (Petrović et al. 2010; Xiao et al. 2008; Bayardo et al. 2007) and 2 cited inside entries (Bohman et al. 2000; Wang et al. 2014). Suggested core 16 for the report: S1-S9, S11, S12, S16-S19, S21. No deep-learning methods are included.

## 1. Founding papers (MinHash, min-wise independence, LSH, SimHash, p-stable LSH, survey)

### Takeaway
All eight founding sources named in the brief exist and their details are confirmed below; the chain is Broder 1997 (resemblance by shingles + min sampling) -> Broder et al. 1998/2000 (min-wise independent permutations) -> Indyk-Motwani 1998 and Gionis et al. 1999 (LSH, hash-table amplification) -> Charikar 2002 (LSH defined as collision probability = similarity; SimHash) -> Datar et al. 2004 (Euclidean LSH) -> Andoni-Indyk 2008 (survey with the amplification formula).

### Cited Findings

**S1. A. Z. Broder, "On the resemblance and containment of documents," in Proc. Compression and Complexity of SEQUENCES 1997 (Cat. No.97TB100171), Salerno, Italy, IEEE Computer Society, pp. 21-29. DOI 10.1109/SEQUEN.1997.666900.**
- Confirmed: CR + OA — [doi](https://doi.org/10.1109/SEQUEN.1997.666900), [Crossref record](https://api.crossref.org/works/10.1109/SEQUEN.1997.666900). Year note: conference held 1997; Crossref has no issue date and OpenAlex lists 2002 (IEEE Xplore load date). Cite as 1997. UNVERIFIED: the printed proceedings year (often cited as 1998) and the city.
- Defines two measures between documents, resemblance r(A,B) and containment c(A,B), for "roughly the same" and "roughly contained" — [OA abstract](https://api.openalex.org/works/doi:10.1109/SEQUEN.1997.666900)
- Reduces both to set-intersection problems estimated by random sampling done independently per document; resemblance needs only a fixed-size sample per document — same source
- Implements the sampling with Rabin fingerprints — same source
- Applies to edits: this is the Jaccard-over-shingles definition that the project's MinHash stage estimates; "containment" is the relevant notion when one edit comment or diff is a subset of another.
- UNVERIFIED (not in abstract; recalled): estimator is unbiased with variance shrinking as 1/(sample size).

**S2. A. Z. Broder, S. C. Glassman, M. S. Manasse, G. Zweig, "Syntactic clustering of the Web," Computer Networks and ISDN Systems, vol. 29, no. 8-13, pp. 1157-1166, Sept. 1997 (Proc. 6th Int. WWW Conf.). DOI 10.1016/S0169-7552(97)00031-7.**
- Confirmed: CR + OA — [doi](https://doi.org/10.1016/S0169-7552(97)00031-7), [Crossref record](https://api.crossref.org/works/10.1016/S0169-7552(97)00031-7)
- No abstract was available in CR/OA and the full text was not opened. UNVERIFIED (recalled): applied shingle sketches to about 30 million AltaVista pages, clustering at a resemblance threshold; introduced "super-shingles". Do not put numbers from this paper in the report without opening it.
- Henzinger 2006 (S9) and Potthast-Stein 2008 (S18) both treat this "shingling" method as the baseline near-duplicate algorithm — [S9 abstract](https://api.openalex.org/works/doi:10.1145/1148170.1148222)
- Applies to edits: first large-scale use of shingle sketches to group similar documents, the same pipeline shape as shingle -> MinHash -> candidate pairs.

**S3. A. Z. Broder, M. Charikar, A. M. Frieze, M. Mitzenmacher, "Min-wise independent permutations," J. Computer and System Sciences, vol. 60, no. 3, pp. 630-659, June 2000. DOI 10.1006/jcss.1999.1690. Conference version: "Min-wise independent permutations (extended abstract)," Proc. 30th ACM STOC, 1998, pp. 327-336. DOI 10.1145/276698.276781.**
- Confirmed: CR for both — [journal doi](https://doi.org/10.1006/jcss.1999.1690), [STOC doi](https://doi.org/10.1145/276698.276781)
- Charikar 2002 states that min-wise independent permutations give a hashing scheme whose collision probability equals |A∩B|/|A∪B| — [S5 abstract](https://api.openalex.org/works/doi:10.1145/509907.509965)
- UNVERIFIED (no abstract retrievable; recalled): defines exact and approximate min-wise independent families and gives lower bounds on family size.
- Related, verified: Spark's MinHashLSH uses linear hashes h(x) = ((x·a + b) mod prime) and its source comment cites T. Bohman, C. Cooper, A. Frieze, "Min-wise independent linear permutations," Electronic J. Combinatorics, vol. 7, no. 1, R26, 2000, DOI 10.37236/1504, as the reason this family is approximately min-wise independent — [Spark source](https://github.com/apache/spark/blob/master/mllib/src/main/scala/org/apache/spark/ml/feature/MinHashLSH.scala), [Crossref](https://api.crossref.org/works/10.37236/1504)
- Applies to edits: justifies using cheap random hash functions in place of true random permutations of the shingle vocabulary.

**S4. P. Indyk, R. Motwani, "Approximate nearest neighbors: towards removing the curse of dimensionality," Proc. 30th ACM STOC, 1998, pp. 604-613. DOI 10.1145/276698.276876.**
- Confirmed: CR + OA — [doi](https://doi.org/10.1145/276698.276876), [Crossref record](https://api.crossref.org/works/10.1145/276698.276876) (Crossref title is truncated to "Approximate nearest neighbors"; OpenAlex gives the full subtitle)
- Origin of LSH: Andoni-Indyk attribute the (R, cR, P1, P2)-sensitive definition and the n^ρ query bound to this line of work — [S8 full text](https://people.csail.mit.edu/indyk/p117-andoni.pdf)
- UNVERIFIED: any specific theorem statement from this paper (abstract not retrievable).
- Applies to edits: source of the formal guarantee that near pairs collide with probability ≥ p1 and far pairs with probability ≤ p2.

**S5. A. Gionis, P. Indyk, R. Motwani, "Similarity search in high dimensions via hashing," Proc. 25th Int. Conf. Very Large Data Bases (VLDB), 1999, pp. 518-529. No DOI.**
- Confirmed: OpenAlex record (authors, year 1999, venue Very Large Data Bases, pp. 518-529) — [OpenAlex search](https://api.openalex.org/works?search=Similarity%20Search%20in%20High%20Dimensions%20via%20Hashing). Publisher PDF https://www.vldb.org/conf/1999/P49.pdf returned HTTP 403, so UNVERIFIED: that this is the correct PDF URL, the city (Edinburgh) and publisher (Morgan Kaufmann).
- Abstract: tree indexes degrade to near linear scan beyond roughly 10-20 dimensions; proposes hashing so that close points collide more often than distant ones — same OpenAlex record
- Applies to edits: the multi-table (OR) scheme Spark exposes as `numHashTables` descends from this design.

**S6. M. S. Charikar, "Similarity estimation techniques from rounding algorithms," Proc. 34th ACM STOC, 2002, pp. 380-388. DOI 10.1145/509907.509965.**
- Confirmed: CR + OA — [doi](https://doi.org/10.1145/509907.509965)
- Defines an LSH scheme as a hash family with Pr[h(x)=h(y)] = sim(x,y) — [OA abstract](https://api.openalex.org/works/doi:10.1145/509907.509965)
- Gives a random-hyperplane scheme where distance is θ(u,v)/π, usable to estimate cosine similarity (later called SimHash), and a scheme for Earth Mover Distance — same source
- Applies to edits: the alternative to MinHash if edits were represented as weighted token vectors (cosine) rather than shingle sets (Jaccard).

**S7. M. Datar, N. Immorlica, P. Indyk, V. S. Mirrokni, "Locality-sensitive hashing scheme based on p-stable distributions," Proc. 20th Annual Symp. Computational Geometry (SoCG), 2004, pp. 253-262. DOI 10.1145/997817.997857.**
- Confirmed: CR + OA — [doi](https://doi.org/10.1145/997817.997857)
- LSH for l_p norms that works directly on Euclidean points without embedding; first provably efficient scheme for p<1 — [OA abstract](https://api.openalex.org/works/doi:10.1145/997817.997857)
- Reports up to 40x speed-up over kd-trees on synthetic data — same source
- Applies to edits: this is the family behind Spark's BucketedRandomProjectionLSH (floor(x·v / r)); not the family the project uses, but the reason the Spark API has two LSH classes.

**S8. A. Andoni, P. Indyk, "Near-optimal hashing algorithms for approximate nearest neighbor in high dimensions," Communications of the ACM, vol. 51, no. 1, pp. 117-122, Jan. 2008. DOI 10.1145/1327452.1327494.** (full text read)
- Confirmed: CR + OA + author PDF — [doi](https://doi.org/10.1145/1327452.1327494), [PDF](https://people.csail.mit.edu/indyk/p117-andoni.pdf)
- Definition 2.3: a family is (R, cR, P1, P2)-sensitive if points within R collide with probability ≥ P1 and points beyond cR with probability ≤ P2, with P1 > P2 — [PDF](https://people.csail.mit.edu/indyk/p117-andoni.pdf)
- Amplification: concatenate k functions per table and use L tables; an R-near pair collides in at least one table with probability ≥ 1 − (1 − P1^k)^L; L = Θ(n^ρ) with ρ = ln(1/P1)/ln(1/P2); for Hamming distance ρ = 1/c — same PDF
- States worst-case query time can reach Θ(n) but is sublinear for many natural datasets with tuned k and L; lists Jaccard/min-hash as one LSH family — same PDF
- Applies to edits: gives the citable form of the S-curve (k = rows, L = bands) used to predict recall of candidate generation.

### Inferences
- Report wording should say "MinHash (Broder 1997) is an LSH family for Jaccard similarity in the sense of Charikar 2002"; Broder's papers predate the term LSH.
- The correct citation for the banding/S-curve formula is S8 (primary) or S11 (textbook), not Broder.

### Gaps
- Full texts of S2, S3, S4 were not opened; only bibliographic data is verified for them.
- S5 has no DOI and the VLDB site blocked access; page range rests on OpenAlex only.

## 2. Practical variants, evaluations and the textbook

### Takeaway
The evaluations give concrete, citable numbers: Henzinger measured precision 0.38 (shingling) vs 0.50 (SimHash) on 1.6B pages; b-bit MinHash cuts storage by a proven factor of at least 21.3 at resemblance ≥ 0.5; the MMDS course material gives the worked b=20, r=5 S-curve.

### Cited Findings

**S9. M. Henzinger, "Finding near-duplicate web pages: a large-scale evaluation of algorithms," Proc. 29th Annual Int. ACM SIGIR Conf., 2006, pp. 284-291. DOI 10.1145/1148170.1148222.**
- Confirmed: CR + OA — [doi](https://doi.org/10.1145/1148170.1148222)
- Compares Broder et al. shingling with Charikar's random-projection method on 1.6 billion distinct web pages — [OA abstract](https://api.openalex.org/works/doi:10.1145/1148170.1148222)
- Precision 0.38 (shingling) vs 0.50 (Charikar); both weak for same-site pairs; a combined algorithm reached precision 0.79 at 79% of the recall — same source
- Applies to edits: precedent for the project's design of judging LSH candidate pairs by hand labels, and evidence that hash candidates need a second check.

**S10. G. S. Manku, A. Jain, A. Das Sarma, "Detecting near-duplicates for web crawling," Proc. 16th Int. Conf. World Wide Web (WWW), 2007, pp. 141-150. DOI 10.1145/1242572.1242592.**
- Confirmed: CR + OA — [doi](https://doi.org/10.1145/1242572.1242592)
- Shows Charikar's fingerprint is suitable for near-duplicate detection in a multi-billion-page repository — [OA abstract](https://api.openalex.org/works/doi:10.1145/1242572.1242592)
- Gives a method to find stored f-bit fingerprints within Hamming distance k of a query, for online and batch use — same source
- UNVERIFIED (recalled, not in abstract): 64-bit fingerprints, k = 3, 8 billion pages.
- Applies to edits: the streaming/online counterpart (one new item against a stored set), relevant if similar-edit lookup were done per incoming edit rather than as a batch self-join.

**S11. J. Leskovec, A. Rajaraman, J. D. Ullman, Mining of Massive Datasets, 3rd ed. Cambridge, U.K.: Cambridge University Press, 2020, ch. 3 "Finding Similar Items". DOI 10.1017/9781108684163. ISBN 9781108476348 (print).**
- Confirmed: CR (monograph, issued 2020-01-09, CUP) and the authors' site, which states the posted book is the third edition and that Chapter 3 is titled "Finding Similar Items" — [doi](https://doi.org/10.1017/9781108684163), [mmds.org](http://www.mmds.org/)
- UNVERIFIED: section numbers inside ch. 3 (chapter PDF host infolab.stanford.edu was down). The facts below are from the authors' official chapter-3 slide deck, full text read — [slides PDF](http://www.mmds.org/mmds/v2.1/ch03-lsh.pdf)
- Banding: with b bands of r rows, a pair with similarity t becomes a candidate with probability 1 − (1 − t^r)^b; the threshold is about (1/b)^(1/r) — slides PDF
- Worked example b=20, r=5: at similarity 0.8, miss probability (1 − 0.8^5)^20 = 0.00035 (99.965% found); at similarity 0.3, 4.74% become candidates (false positives). Table for r=5, b=10: s=0.2→0.006, 0.3→0.047, 0.4→0.186, 0.5→0.470, 0.6→0.802, 0.7→0.975, 0.8→0.9996 — slides PDF
- Shingle size: k must be large enough or most documents share most shingles; k=5 for short documents, k=10 for long ones (slides); notes candidates can be false positives unless the optional exact check is made — slides PDF
- Applies to edits: the standard teaching reference for the exact pipeline the project runs (shingle, MinHash signature, band, verify).

**S12. P. Li, A. C. König, "b-Bit minwise hashing," Proc. 19th Int. Conf. World Wide Web (WWW), 2010, pp. 671-680. DOI 10.1145/1772690.1772759.** (full text read via arXiv:0910.3349)
- Confirmed: CR + OA + arXiv PDF — [doi](https://doi.org/10.1145/1772690.1772759), [arXiv](https://arxiv.org/abs/0910.3349). Journal follow-up: P. Li, A. C. König, "Theory and applications of b-bit minwise hashing," Commun. ACM, vol. 54, no. 8, pp. 101-109, Aug. 2011, DOI 10.1145/1978542.1978566 (CR).
- Stores only the lowest b bits of each min-hash (e.g. b = 1 or 2) instead of e.g. 64 bits, with an unbiased resemblance estimator — [arXiv PDF](https://arxiv.org/pdf/0910.3349)
- Proves that b = 1 reduces storage by at least a factor of 21.3 (10.7 in a second stated case) at resemblance ≥ 0.5, in the least favourable scenario — same PDF
- Notes the common web setting of shingles of w = 5 contiguous words — same PDF
- Applies to edits: a way to shrink signatures if the number of edits grows; not available in Spark's MinHashLSH.

**S13. P. Li, A. Owen, C.-H. Zhang, "One permutation hashing," Advances in Neural Information Processing Systems 25 (NIPS 2012). No DOI.** (abstract page + arXiv:1208.1259 read)
- Confirmed: official proceedings page — [NeurIPS proceedings](https://papers.nips.cc/paper/2012/hash/eaa32c96f620053cf442ad32258076b9-Abstract.html). UNVERIFIED: page numbers (not shown on the page).
- Motivation: standard minwise hashing needs e.g. k = 500 permutations per item, a high preprocessing cost — proceedings page
- Method: one permutation, split the space into k bins, keep the smallest non-zero location per bin; empty bins are rare unless a set has few non-zeros relative to k — [arXiv PDF](https://arxiv.org/pdf/1208.1259)
- Applies to edits: the empty-bin caveat is exactly the short-text case (edit comments with few shingles), so this speed-up is risky for short items.

**S14. M. Bawa, T. Condie, P. Ganesan, "LSH forest: self-tuning indexes for similarity search," Proc. 14th Int. Conf. World Wide Web (WWW), 2005, p. 651 ff. DOI 10.1145/1060745.1060840.**
- Confirmed: CR + OA — [doi](https://doi.org/10.1145/1060745.1060840). UNVERIFIED: end page (Crossref and OpenAlex give only 651; commonly cited as 651-660).
- Removes the data-dependent parameters that standard LSH needs hand-tuned, and improves guarantees for skewed data at the same storage and query cost — [OA abstract](https://api.openalex.org/works/doi:10.1145/1060745.1060840)
- Evaluated on multiple text corpora — same source
- Applies to edits: documents that fixed (bands, rows) settings are a known weakness; the project's fixed-parameter Spark join inherits it.

**S15. A. S. Das, M. Datar, A. Garg, S. Rajaram, "Google news personalization: scalable online collaborative filtering," Proc. 16th Int. Conf. World Wide Web (WWW), 2007, pp. 271-280. DOI 10.1145/1242572.1242610.**
- Confirmed: CR + OA — [doi](https://doi.org/10.1145/1242572.1242610)
- Production recommender for Google News combining MinHash clustering, PLSI and covisitation counts in a linear model — [OA abstract](https://api.openalex.org/works/doi:10.1145/1242572.1242610)
- Setting is large (several million users/items) and dynamic (item set changes continually) — same source
- UNVERIFIED (recalled): MinHash clustering was implemented on MapReduce.
- Applies to edits: evidence that MinHash scales on a cluster framework over a continually changing item set, like an edit stream.

**S16. A. Shrivastava, P. Li, "In defense of MinHash over SimHash," Proc. 17th Int. Conf. Artificial Intelligence and Statistics (AISTATS), PMLR vol. 33, pp. 886-894, 2014.**
- Confirmed: official proceedings page — [PMLR](https://proceedings.mlr.press/v33/shrivastava14.html)
- For binary data, MinHash "virtually always outperforms SimHash" (theory, checked by experiments) — PMLR abstract
- Uses the inequality S² ≤ R ≤ S/(2 − S) linking resemblance R and cosine S to compare the two on one scale — PMLR abstract
- Applies to edits: supports choosing MinHash over SimHash when edits are binary shingle sets.

### Inferences
- Henzinger's precision figures (0.38 / 0.50) are for web pages with boilerplate; they are not a prediction for edit text, only a reason to report precision from hand labels.
- The MMDS slide advice (k=5 short, k=10 long) is for character shingles; the project uses token shingles, so the rule does not transfer directly.

### Gaps
- MMDS book chapter 3 itself could not be opened; quote section numbers only after checking the PDF at http://infolab.stanford.edu/~ullman/mmds/ch3n.pdf.
- Densified one-permutation hashing (Shrivastava and Li, 2014) was not verified and is not listed.

## 3. Implementation reference: Apache Spark MLlib

### Takeaway
Spark's guide defines LSH by the (r1, r2, p1, p2) property, implements MinHash for Jaccard distance and bucketed random projection for Euclidean distance, supports OR-amplification only, and cites Wikipedia rather than the founding papers; the only papers named are in the source comments.

### Cited Findings

**S17. Apache Software Foundation, "Extracting, transforming and selecting features — Locality Sensitive Hashing," Apache Spark 4.3.0 MLlib Guide. https://spark.apache.org/docs/latest/ml-features.html#locality-sensitive-hashing (accessed 2026-11-17).** (full section read)
- An LSH family is (r1, r2, p1, p2)-sensitive: d(p,q) ≤ r1 ⇒ Pr[h(p)=h(q)] ≥ p1; d(p,q) ≥ r2 ⇒ Pr ≤ p2. False positive = distant pair in the same bucket; false negative = near pair in different buckets — [Spark guide](https://spark.apache.org/docs/latest/ml-features.html#locality-sensitive-hashing)
- MinHash: Jaccard distance d(A,B) = 1 − |A∩B|/|A∪B|; h(A) = min over a in A of g(a); input is a binary vector; all non-zero values count as 1; a vector with no non-zero entry cannot be transformed — same guide
- `numHashTables` gives OR-amplification; more tables raise accuracy and also communication cost and running time. Each table's vector has dimension 1; the guide says AND-amplification will come in future releases — same guide
- `approxSimilarityJoin` returns pairs under a user threshold and adds a column with the true distance of each returned pair; self-join yields some duplicate pairs. `approxNearestNeighbors` can return fewer than k rows — same guide
- BucketedRandomProjectionLSH: h(x) = floor(x·v / r) with user bucket length r; larger r raises true and false positives — same guide
- Citations: the guide links only to Wikipedia (LSH, Amplification, Stable distributions, MinHash). Source comments: MinHashLSH cites Wikipedia on MinHash and Bohman-Cooper-Frieze 2000 for the hash family h(x) = ((x·a + b) mod prime); BucketedRandomProjectionLSH cites Wikipedia and J. Wang, H. T. Shen, J. Song, J. Ji, "Hashing for similarity search: A survey," arXiv:1408.2927, 2014. Both classes are marked Since 2.1.0 — [MinHashLSH.scala](https://github.com/apache/spark/blob/master/mllib/src/main/scala/org/apache/spark/ml/feature/MinHashLSH.scala), [BucketedRandomProjectionLSH.scala](https://github.com/apache/spark/blob/master/mllib/src/main/scala/org/apache/spark/ml/feature/BucketedRandomProjectionLSH.scala), [arXiv](https://arxiv.org/abs/1408.2927)
- Applies to edits: this is the code the project runs; empty-shingle edits must be dropped before hashing.

### Inferences
- Because Spark has r = 1 row per table, the candidate probability for a pair with Jaccard s and L = numHashTables is 1 − (1 − s)^L (S8 formula with k = 1). This curve is concave, not S-shaped: e.g. L = 5 gives 0.97 at s = 0.5 but also 0.41 at s = 0.1 (computed here from the formula, not from a source). Selectivity therefore comes from the exact-distance threshold in the join, not from banding.
- The join's distance column is the exact Jaccard distance on the input vectors, so returned pairs have no false positives relative to the threshold on those vectors; false negatives remain. If the vectors come from HashingTF, hash collisions between shingles can still distort the distance (collision behaviour of HashingTF is described in the same guide).
- Spark does not cite Broder, Indyk-Motwani or Datar et al.; the report should cite the papers itself and cite the Spark guide only for implementation behaviour.

### Gaps
- No Spark document states the default-parameter recall of MinHashLSH; none was found.
- The Spark version the project runs was not checked against the 4.3.0 guide text.

## 4. Applications close to the project: Wikipedia revisions, edit text, reverts

### Takeaway
Little exists: two confirmed studies apply near-duplicate hashing to Wikipedia text (revisions as an evaluation corpus; sentences via MapReduce MinHash), and revert research uses checksums or word-level diffs, not LSH. No source was found that applies MinHash/LSH to edit comments or to revert detection.

### Cited Findings

**S18. M. Potthast, B. Stein, "New issues in near-duplicate detection," in Data Analysis, Machine Learning and Applications (Studies in Classification, Data Analysis, and Knowledge Organization), Berlin, Heidelberg: Springer, 2008, pp. 601-609. DOI 10.1007/978-3-540-78246-9_71.** (full text read)
- Confirmed: CR + author-group PDF — [doi](https://doi.org/10.1007/978-3-540-78246-9_71), [PDF](https://webis.de/downloads/publications/papers/potthast_2008c.pdf)
- Proposes the Wikipedia Revision Corpus (order of 6 million articles, 80 million revisions) as a near-duplicate benchmark because it permits recall as well as precision measurement; an article's revisions have expected similarity of about 0.5 to its first revision — PDF
- Evaluates fingerprint methods (shingling, super-/megashingling, fuzzy-fingerprinting, locality-sensitive hashing and others) on 7 million document pairs; chunking-based methods beat similarity hashing, and among fixed-size fingerprints shingling was best — PDF
- Applies to edits: the closest prior use of Wikipedia revision text to evaluate shingling/LSH with precision and recall against a similarity threshold. It compares whole revisions, not edit diffs or comments.

**S19. S. Weissman, S. Ayhan, J. Bradley, J. Lin, "Identifying duplicate and contradictory information in Wikipedia," Proc. 15th ACM/IEEE-CS Joint Conf. Digital Libraries (JCDL), 2015, pp. 57-60. DOI 10.1145/2756406.2756947.** (full text read via arXiv:1406.1143)
- Confirmed: CR + OA + arXiv — [doi](https://doi.org/10.1145/2756406.2756947), [arXiv](https://arxiv.org/abs/1406.1143)
- MapReduce MinHash over Wikipedia sentences to find high-Jaccard pairs, then cluster; manual inspection sorted clusters into six types (templates, identical sentences, copyediting, factual drift, references, other) — [OA abstract](https://api.openalex.org/works/doi:10.1145/2756406.2756947)
- Parameters: hash family N = 20, K = 10 min-hashes per signature, M = 10 signatures per sentence, character shingles of length 12; stated 99% chance of a match at Jaccard 0.9; sentences with fewer than 75 or more than 600 shingles discarded — [arXiv PDF](https://arxiv.org/pdf/1406.1143)
- States a second verification pass would remove false positives cheaply but was not implemented — same PDF
- Applies to edits: nearest methodological match (MinHash on short Wikipedia text + manual categorisation); note they dropped very short texts, and the project's exact-Jaccard check is the step they left for future work.

**S20. M. Alshomary, M. Völske, T. Licht, H. Wachsmuth, B. Stein, M. Hagen, M. Potthast, "Wikipedia text reuse: within and without," in Advances in Information Retrieval (ECIR 2019), LNCS, Springer, 2019, pp. 747-754. DOI 10.1007/978-3-030-15712-8_49.**
- Confirmed: CR + arXiv — [doi](https://doi.org/10.1007/978-3-030-15712-8_49), [arXiv](https://arxiv.org/abs/1812.09221). UNVERIFIED: LNCS volume number (11437 recalled).
- Runs text-reuse detection over all of Wikipedia in a distributed pipeline; reports about 100 million reuse cases inside Wikipedia and 1.6 million outside (Common Crawl sample) — [arXiv abstract](https://arxiv.org/abs/1812.09221)
- UNVERIFIED: whether the candidate stage uses MinHash/LSH specifically (abstract does not say).
- Applies to edits: shows near-copy text is common inside Wikipedia, so similar-edit pairs are expected, not anomalies.

**S21. F. Flöck, D. Vrandečić, E. Simperl, "Revisiting reverts: accurate revert detection in Wikipedia," Proc. 23rd ACM Conf. Hypertext and Social Media (HT), 2012, pp. 3-12. DOI 10.1145/2309996.2310000.** (already proposal ref [18])
- Confirmed: CR + OA — [doi](https://doi.org/10.1145/2309996.2310000). Note: the DOI 10.1145/2309996.2310038 is a different paper in the same proceedings.
- States the usual revert detection matches identical revisions by MD5 hash, which misses reverts, misclassifies others and cannot separate full from partial reverts — [OA abstract](https://api.openalex.org/works/doi:10.1145/2309996.2310000)
- Proposes detection from word tokens added or deleted, validated by a user study, at higher runtime — same source
- Applies to edits: the argument for going beyond exact checksums; the method is word-level diffing, not LSH.

**S22. M. D. Ekstrand, J. T. Riedl, "rv you're dumb: identifying discarded work in Wiki article history," Proc. 5th Int. Symp. Wikis and Open Collaboration (WikiSym), 2009, pp. 1-10 (article-numbered). DOI 10.1145/1641309.1641317.**
- Confirmed: CR + OA — [doi](https://doi.org/10.1145/1641309.1641317)
- Detects when a revision discards the work of earlier revisions and which earlier revision supplied most of a later one's content — [OA abstract](https://api.openalex.org/works/doi:10.1145/1641309.1641317)
- UNVERIFIED: the similarity measure used (not in abstract).
- Applies to edits: revision-to-revision similarity used to find reverts that are not exact copies; again not hashing-based.

Also confirmed to exist, not read: J. Kiesel, M. Potthast, M. Hagen, B. Stein, "Spatio-temporal analysis of reverted Wikipedia edits," Proc. Int. AAAI Conf. Web and Social Media (ICWSM), vol. 11, no. 1, pp. 122-131, 2017, DOI 10.1609/icwsm.v11i1.14900 — [doi](https://doi.org/10.1609/icwsm.v11i1.14900). Relevance to text similarity UNVERIFIED.

### Inferences
- The project's use of MinHash LSH on edit/revert text with exact-Jaccard and hand-label checks appears not to have a direct published precedent among the sources found; S18 and S19 are the nearest. State this as "we found no prior work", not "none exists".

### Gaps
- No reliable source found for MinHash/LSH on edit comments (summaries), on diffs, or for vandalism detection by near-duplicate hashing. Searches were limited to Crossref/OpenAlex title queries; ACM DL and DBLP full-text search were not available.

## 5. Known limits: short texts and shingle size, bands/rows trade-off, verification cost

### Takeaway
The limits are documented: short items give few shingles and unstable hashing; fewer bands or more rows trade false positives for false negatives; and candidate verification is a separate cost that exact set-similarity joins try to cut.

### Cited Findings
- Shingle size: k too small makes most documents share most shingles; k=5 short / k=10 long documents — [MMDS slides](http://www.mmds.org/mmds/v2.1/ch03-lsh.pdf) (S11)
- Short texts: Weissman et al. discarded sentences under 75 character-shingles — [arXiv PDF](https://arxiv.org/pdf/1406.1143) (S19); one-permutation hashing has empty bins when a set has few non-zeros — [arXiv PDF](https://arxiv.org/pdf/1208.1259) (S13); Spark MinHash rejects empty vectors — [Spark guide](https://spark.apache.org/docs/latest/ml-features.html#locality-sensitive-hashing) (S17)
- Short-text streams: **S. Petrović, M. Osborne, V. Lavrenko, "Streaming first story detection with application to Twitter," Proc. HLT-NAACL 2010, Los Angeles, ACL, pp. 181-189** — confirmed on [ACL Anthology](https://aclanthology.org/N10-1021/) (full text read). Pure LSH gave poor performance and high variance on the task; adding an exact comparison against a fixed number (2000) of most recent documents fixed it; matched a state-of-the-art system on TDT5 with an order-of-magnitude speed-up; run on 160 million tweets — [PDF](https://aclanthology.org/N10-1021.pdf). (Uses cosine/random-hyperplane LSH, not MinHash.)
- Bands/rows: b=20, r=5 misses 0.035% of pairs at s=0.8 and admits 4.74% at s=0.3; going to 15 bands lowers false positives and raises false negatives — [MMDS slides](http://www.mmds.org/mmds/v2.1/ch03-lsh.pdf)
- Tables: more hash tables raise accuracy and also communication cost and running time — [Spark guide](https://spark.apache.org/docs/latest/ml-features.html#locality-sensitive-hashing)
- Worst case: LSH query time can be Θ(n) — [Andoni-Indyk PDF](https://people.csail.mit.edu/indyk/p117-andoni.pdf) (S8)
- Verification cost / exact alternatives: **C. Xiao, W. Wang, X. Lin, J. X. Yu, "Efficient similarity joins for near duplicate detection," Proc. 17th Int. Conf. World Wide Web (WWW), 2008, pp. 131-140, DOI 10.1145/1367497.1367516** — exact threshold joins by prefix filtering plus ordering-based filters cut candidate sets, 2.6x-5x faster than prior algorithms — [OA abstract](https://api.openalex.org/works/doi:10.1145/1367497.1367516). **R. J. Bayardo, Y. Ma, R. Srikant, "Scaling up all pairs similarity search," Proc. 16th WWW, 2007, pp. 131-140, DOI 10.1145/1242572.1242591** — exact all-pairs above a threshold without approximation or heavy parameter tuning — [OA abstract](https://api.openalex.org/works/doi:10.1145/1242572.1242591)
- Precision of unverified hash candidates on real data: 0.38-0.50 — [Henzinger abstract](https://api.openalex.org/works/doi:10.1145/1148170.1148222) (S9)

### Inferences
- For token shingles on short edit comments, many items have only a handful of shingles, so Jaccard moves in large steps (one shared shingle out of three is 0.33); a fixed threshold behaves differently for short and long items. This follows from the definition; no source measured it for edit comments.
- With Spark's OR-only scheme the candidate set at low similarity is large (section 3), so the dominant cost is the exact-distance filter inside the join, consistent with Spark's own warning about running time.

### Gaps
- No source found that measures MinHash error specifically as a function of text length for texts under ~20 tokens.
- UNVERIFIED and omitted: variance formula s(1−s)/k for the MinHash estimator (standard, but not seen in an opened source this session).
