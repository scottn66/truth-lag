# Founding literature: streaming algorithms, stream processing, lakehouse systems

Verification method (2026-11-17). "Crossref" = bibliographic record opened at `https://api.crossref.org/works/<DOI>` (authors, title, venue, volume, issue, pages, date read from the record). "PDF read" = the paper's own PDF was downloaded and its first page and relevant passages were read this session. DBLP was unreachable during this session (API timed out), so no entry rests on DBLP.

Confidence labels on the "what it introduced" bullets:
- [READ] = taken from the paper text or official page opened this session.
- [RECALL] = standard, widely reproduced result of that paper, stated from the researcher's prior knowledge; the full text was NOT opened this session (paywalled or mirror failed). Check against the paper or MMDS ch. 4 before quoting a number.

Corrections to the existing reference list in `docs/final/report_draft.md` are collected under "Re-verification of entries already in the report draft" at the end of Key Question 4.

---

## Key Question 1: Original papers for each streaming algorithm (sampling, membership, distinct count, moments, sliding windows, frequency) and the standard textbook

### Takeaway
Every algorithm the project uses has a single identifiable founding paper, all confirmed by DOI; the only bibliographic surprises are that HyperLogLog's pages are 127-146 (per the paper's own header) and that AMS has both a STOC 1996 version and a 1999 journal version.

### Cited Findings

**S1. Vitter 1985 (reservoir sampling)**
- J. S. Vitter, "Random sampling with a reservoir," ACM Transactions on Mathematical Software, vol. 11, no. 1, pp. 37-57, Mar. 1985. DOI 10.1145/3147.3165 — [Crossref](https://api.crossref.org/works/10.1145/3147.3165); [PDF read](https://www.cs.umd.edu/~samir/498/vitter.pdf)
- [READ] Problem: draw a uniform sample of n records without replacement from a pool of N records when N is not known in advance, in one pass — [PDF](https://www.cs.umd.edu/~samir/498/vitter.pdf)
- [READ] Main result is Algorithm Z: one pass, constant space, expected time O(n(1 + log(N/n))), stated as optimal up to a constant factor — [PDF](https://www.cs.umd.edu/~samir/498/vitter.pdf)
- [RECALL] Algorithm R (attributed in the paper to Alan Waterman) is the simple baseline: keep the first n, then replace a random slot with probability n/t for the t-th record; it costs O(N) time because it draws a random number per record. Algorithm Z instead draws how many records to skip — [DOI page](https://doi.org/10.1145/3147.3165)
- Applies to an edit stream: a fixed-size uniform sample of edits can be held while the stream length is unknown; labels that arrive later (reverts) can be joined to the sampled revision ids afterwards without changing the inclusion probabilities, because inclusion does not depend on the label.

**S2. Bloom 1970 (Bloom filter)**
- B. H. Bloom, "Space/time trade-offs in hash coding with allowable errors," Communications of the ACM, vol. 13, no. 7, pp. 422-426, July 1970. DOI 10.1145/362686.362692 — [Crossref](https://api.crossref.org/works/10.1145/362686.362692)
- [RECALL] Introduces hash-coded set membership that tolerates a small fraction of false positives in exchange for much less space; no false negatives — [DOI page](https://doi.org/10.1145/362686.362692)
- [RECALL] Two methods are given; the second (a bit array with several hash-selected bit positions per key) is what is now called a Bloom filter — [DOI page](https://doi.org/10.1145/362686.362692)
- Applies to an edit stream: membership test of "have I seen this revision id / is this user in the bot set" in fixed memory; a standard Bloom filter cannot delete, so a label that later changes (e.g. a revert that is itself reverted) cannot be removed from the filter.

**S3. Broder and Mitzenmacher 2004 (Bloom filter survey)**
- A. Broder and M. Mitzenmacher, "Network applications of Bloom filters: A survey," Internet Mathematics, vol. 1, no. 4, pp. 485-509, 2004. DOI 10.1080/15427951.2004.10129096 — [Crossref](https://api.crossref.org/works/10.1080/15427951.2004.10129096); [PDF read](https://www.eecs.harvard.edu/~michaelm/postscripts/im2005b.pdf)
- [READ] Defines a Bloom filter as a space-efficient randomized structure for membership queries that allows false positives; surveys variants and four families of network uses (overlay/P2P, resource routing, packet routing, measurement) — [PDF](https://www.eecs.harvard.edu/~michaelm/postscripts/im2005b.pdf)
- [RECALL] Gives the standard analysis: with m bits, n keys and k hash functions the false-positive rate is about (1 - e^(-kn/m))^k, minimized at k = (m/n) ln 2, giving about 0.6185^(m/n); also describes counting Bloom filters, which support deletion — [DOI page](https://doi.org/10.1080/15427951.2004.10129096)
- Applies to an edit stream: the source to cite for the false-positive formula when comparing a measured false-positive rate against theory; counting filters are the cited remedy when set members must be removed after a late correction.

**S4. Flajolet and Martin 1985 (probabilistic counting)**
- P. Flajolet and G. N. Martin, "Probabilistic counting algorithms for data base applications," Journal of Computer and System Sciences, vol. 31, no. 2, pp. 182-209, Oct. 1985. DOI 10.1016/0022-0000(85)90041-8 — [Crossref](https://api.crossref.org/works/10.1016/0022-0000(85)90041-8); [PDF read](https://algo.inria.fr/flajolet/Publications/FlMa85.pdf)
- [READ] Estimates the number of distinct elements in one pass using small extra storage ("typically less than a hundred binary words") and a few operations per element, from bit patterns of hashed values — [PDF](https://algo.inria.fr/flajolet/Publications/FlMa85.pdf)
- [READ] The estimate is insensitive to how often each element repeats, and the sketches can be used across distributed sites without loss — [PDF](https://algo.inria.fr/flajolet/Publications/FlMa85.pdf)
- [RECALL] The PCSA variant with m bitmaps has standard error about 0.78/sqrt(m); the correction constant is phi ≈ 0.77351 — [DOI page](https://doi.org/10.1016/0022-0000(85)90041-8)
- Applies to an edit stream: distinct editors or distinct pages per window; duplicates caused by replays or at-least-once delivery do not change the estimate, and sketches from separate partitions or days merge by bitwise OR.

**S5. Flajolet, Fusy, Gandouet, Meunier 2007 (HyperLogLog)**
- P. Flajolet, É. Fusy, O. Gandouet, and F. Meunier, "HyperLogLog: the analysis of a near-optimal cardinality estimation algorithm," in Proc. 2007 Conference on Analysis of Algorithms (AofA 07), Discrete Mathematics and Theoretical Computer Science Proceedings, vol. AH, pp. 127-146, 2007. DOI 10.46298/dmtcs.3545 — [Crossref](https://api.crossref.org/works/10.46298/dmtcs.3545); [PDF read](https://algo.inria.fr/flajolet/Publications/FlFuGaMe07.pdf)
- [READ] The page range printed in the paper's own running head is "DMTCS proc. AH, 2007, 127–146". (Some secondary citations give 137-156; the paper header says 127-146.) — [PDF](https://algo.inria.fr/flajolet/Publications/FlFuGaMe07.pdf)
- [READ] With m registers the relative standard error is about 1.04/sqrt(m); matches LogLog accuracy with 64% of the memory — [PDF](https://algo.inria.fr/flajolet/Publications/FlFuGaMe07.pdf)
- [READ] Example given: cardinalities well beyond 10^9 at about 2% typical accuracy using 1.5 kilobytes; the algorithm parallelizes and adapts to sliding windows — [PDF](https://algo.inria.fr/flajolet/Publications/FlFuGaMe07.pdf)
- Applies to an edit stream: mergeable distinct-count sketches per window can be re-merged when late events are assigned to an old window, so a corrected distinct count does not need the raw rows.

**S6. Heule, Nunkesser, Hall 2013 (HyperLogLog++)**
- S. Heule, M. Nunkesser, and A. Hall, "HyperLogLog in practice: Algorithmic engineering of a state of the art cardinality estimation algorithm," in Proc. 16th International Conference on Extending Database Technology (EDBT '13), pp. 683-692, Mar. 2013. DOI 10.1145/2452376.2452456 — [Crossref](https://api.crossref.org/works/10.1145/2452376.2452456); [PDF read](https://static.googleusercontent.com/media/research.google.com/en//pubs/archive/40671.pdf)
- [READ] Uses a 64-bit hash so cardinalities beyond 1 billion can be estimated; register memory becomes 6·2^p bits instead of 5·2^p for precision p — [PDF](https://static.googleusercontent.com/media/research.google.com/en//pubs/archive/40671.pdf)
- [READ] Adds an empirical bias correction for small cardinalities and a sparse representation to cut memory at low counts — [PDF](https://static.googleusercontent.com/media/research.google.com/en//pubs/archive/40671.pdf)
- Applies to an edit stream: this is the variant behind Spark's `approx_count_distinct` (UNVERIFIED: Spark's source cites this paper; not opened this session), so it is the right citation when the report compares Spark's built-in estimate with a hand-written HLL.

**S7. Alon, Matias, Szegedy 1996 / 1999 (AMS frequency moments)**
- Conference: N. Alon, Y. Matias, and M. Szegedy, "The space complexity of approximating the frequency moments," in Proc. 28th Annual ACM Symposium on Theory of Computing (STOC '96), pp. 20-29, 1996. DOI 10.1145/237814.237823 — [Crossref](https://api.crossref.org/works/10.1145/237814.237823)
- Journal: same authors and title, Journal of Computer and System Sciences, vol. 58, no. 1, pp. 137-147, Feb. 1999. DOI 10.1006/jcss.1997.1545 — [Crossref](https://api.crossref.org/works/10.1006/jcss.1997.1545); [author PDF read](https://www.tau.ac.il/~nogaa/PDFS/amsz4.pdf)
- [READ] Defines the k-th frequency moment F_k = sum over items of (count)^k; F_0 is the number of distinct elements, F_1 the stream length, F_2 the repeat rate — [PDF](https://www.tau.ac.il/~nogaa/PDFS/amsz4.pdf)
- [READ] F_0, F_1 and F_2 can be approximated in logarithmic space; approximating F_k for k ≥ 6 needs n^Ω(1) space — [PDF](https://www.tau.ac.il/~nogaa/PDFS/amsz4.pdf)
- [RECALL] The F_2 estimator uses four-wise independent ±1 hashes ("tug-of-war" sketch); averaging groups and taking the median of group means gives a (1 ± ε) estimate with probability 1 − δ using O((1/ε²) log(1/δ)) counters — [DOI page](https://doi.org/10.1006/jcss.1997.1545)
- Applies to an edit stream: F_2 of the edits-per-page (or reverts-per-user) distribution measures skew; the sketch is linear, so late-arriving edits can simply be added to the sketch of their window.

**S8. Datar, Gionis, Indyk, Motwani 2002 (DGIM)**
- M. Datar, A. Gionis, P. Indyk, and R. Motwani, "Maintaining stream statistics over sliding windows," SIAM Journal on Computing, vol. 31, no. 6, pp. 1794-1813, 2002. DOI 10.1137/S0097539701398363 — [Crossref](https://api.crossref.org/works/10.1137/S0097539701398363)
- [RECALL] Counts the 1s among the last N bits of a stream with relative error at most ε using O((1/ε) log² N) bits (exponential histogram), and proves a matching lower bound — [DOI page](https://doi.org/10.1137/S0097539701398363)
- [RECALL] Extends the technique to sums of bounded integers and other statistics over a sliding window — [DOI page](https://doi.org/10.1137/S0097539701398363)
- Applies to an edit stream: "how many of the last N edits were reverted" in small memory. The structure assumes bits arrive in order with their final value; a revert label that arrives after the edit's bit was recorded is outside the model (see Gaps).

**S9. Cormode and Muthukrishnan 2005 (Count-Min sketch)**
- G. Cormode and S. Muthukrishnan, "An improved data stream summary: the count-min sketch and its applications," Journal of Algorithms, vol. 55, no. 1, pp. 58-75, Apr. 2005. DOI 10.1016/j.jalgor.2003.12.001 — [Crossref](https://api.crossref.org/works/10.1016/j.jalgor.2003.12.001)
- [RECALL] A d × w array of counters with d = ceil(ln(1/δ)) pairwise-independent hash rows and w = ceil(e/ε) columns; a point query overestimates the true count by at most ε·(total count) with probability at least 1 − δ, and never underestimates for non-negative updates — [DOI page](https://doi.org/10.1016/j.jalgor.2003.12.001)
- [RECALL] Supports point, range and inner-product queries and is linear, so it accepts decrements (turnstile updates) — [DOI page](https://doi.org/10.1016/j.jalgor.2003.12.001)
- Applies to an edit stream: per-page or per-user edit and revert counts; because decrements are allowed, a retracted label can be subtracted, which a Bloom filter or Misra-Gries summary cannot do. Not used in the project; cite as a related alternative only.

**S10. Misra and Gries 1982 (frequent elements)**
- J. Misra and D. Gries, "Finding repeated elements," Science of Computer Programming, vol. 2, no. 2, pp. 143-152, Nov. 1982. DOI 10.1016/0167-6423(82)90012-0 — [Crossref](https://api.crossref.org/works/10.1016/0167-6423(82)90012-0)
- [RECALL] Finds every value that occurs more than n/k times in a sequence of length n using k − 1 counters in one pass; a second pass confirms the candidates — [DOI page](https://doi.org/10.1016/0167-6423(82)90012-0)
- [RECALL] Each reported count undercounts the truth by at most n/k — [DOI page](https://doi.org/10.1016/0167-6423(82)90012-0)
- Applies to an edit stream: most-edited or most-reverted pages in fixed memory; deterministic, insert-only.

**S11. Metwally, Agrawal, El Abbadi 2005 (Space-Saving; optional companion to S10)**
- A. Metwally, D. Agrawal, and A. El Abbadi, "Efficient computation of frequent and top-k elements in data streams," in Database Theory - ICDT 2005, Lecture Notes in Computer Science vol. 3363, pp. 398-412, Springer, 2005. DOI 10.1007/978-3-540-30570-5_27 — [Crossref](https://api.crossref.org/works/10.1007/978-3-540-30570-5_27) (Crossref lists the online date as 2004; the volume is ICDT 2005. UNVERIFIED: LNCS volume number 3363, from recall.)
- [RECALL] Space-Saving keeps m counters; when a new item arrives and all are in use it replaces the minimum counter and inherits its count, giving overestimates bounded by n/m — [DOI page](https://doi.org/10.1007/978-3-540-30570-5_27)
- Applies to an edit stream: top-k pages by revert count; same insert-only limitation as S10.

**S12. Leskovec, Rajaraman, Ullman 2020 (textbook)**
- J. Leskovec, A. Rajaraman, and J. D. Ullman, Mining of Massive Datasets, 3rd ed. Cambridge, U.K.: Cambridge University Press, 2020. DOI 10.1017/9781108684163 — [Crossref (edition-number 3, issued 2020-01-09)](https://api.crossref.org/works/10.1017/9781108684163); [authors' book page](http://infolab.stanford.edu/~ullman/mmds.html)
- [READ] The authors' page lists a third edition, free to download by agreement with the publisher, and names Chapter 4 "Mining Data Streams" — [book page](http://infolab.stanford.edu/~ullman/mmds.html)
- [RECALL] Chapter 4 sections: stream model, sampling, Bloom filters (4.3), Flajolet-Martin distinct counting (4.4), AMS moments (4.5), DGIM (4.6), decaying windows (4.7). UNVERIFIED: section numbers; the chapter PDF link on the authors' page returned 404 this session (`http://infolab.stanford.edu/~ullman/mmds/ch4.pdf`) and `www.mmds.org` has a certificate mismatch over HTTPS — [book page](http://infolab.stanford.edu/~ullman/mmds.html)
- Applies to an edit stream: the course-level reference that ties all six project techniques together; cite it once for the stream model and cite the original papers for the bounds.

### Inferences
- The sketches split into mergeable/linear ones (FM, HLL, AMS, Count-Min) that can absorb a late event by updating the sketch of the window the event belongs to, and order- or insert-dependent ones (DGIM, Bloom, Misra-Gries, reservoir by arrival order) that cannot undo or reorder. This split is the researcher's synthesis; none of the papers frames it in terms of late labels.
- None of the founding sketch papers (S1-S10) discusses out-of-order arrival or labels that change after the fact; the stream model in each is a single ordered pass.

### Gaps
- Bloom 1970, DGIM 2002, Count-Min 2005, Misra-Gries 1982 and Space-Saving 2005 full texts were not opened (paywall or mirror failure); their bibliographic data is confirmed by Crossref but the stated bounds are [RECALL].
- MMDS Chapter 4 PDF could not be opened, so section numbers are unverified.
- The claim that Spark's `approx_count_distinct` implements HLL++ was not checked against Spark source or docs this session.

---

## Key Question 2: Stream processing systems (Kafka, Spark RDDs, D-Streams, Structured Streaming, Flink, MillWheel, Dataflow, Lambda/Kappa)

### Takeaway
The systems lineage is fully citable: Kafka (NetDB 2011) for the replayable log, RDDs (NSDI 2012) and D-Streams (SOSP 2013) for micro-batch recovery by lineage, MillWheel (PVLDB 2013) and the Dataflow model (PVLDB 2015) for event time, low watermarks and triggers, and Structured Streaming (SIGMOD 2018), which adopts the watermark idea as max(event time) minus a user-set delay.

### Cited Findings

**S13. Kreps, Narkhede, Rao 2011 (Kafka)**
- J. Kreps, N. Narkhede, and J. Rao, "Kafka: a distributed messaging system for log processing," in Proc. 6th International Workshop on Networking Meets Databases (NetDB '11), Athens, Greece, June 12, 2011. No DOI found. — [PDF read (mirror)](https://notes.stephenholiday.com/Kafka.pdf); the PDF footer reads "NetDB'11, Jun. 12, 2011, Athens, Greece". UNVERIFIED: page numbers (commonly cited as pp. 1-7) and "6th" ordinal; no publisher page was opened.
- [READ] Presents Kafka as a distributed messaging system for collecting and delivering high volumes of log data with low latency, for both offline and online consumers — [PDF](https://notes.stephenholiday.com/Kafka.pdf)
- [READ] Messages are addressed by logical offset in a partition log; the broker is stateless about consumers, and a consumer can deliberately rewind to an old offset and re-consume — [PDF](https://notes.stephenholiday.com/Kafka.pdf)
- Applies to an edit stream: a retained, offset-addressed log is what makes reprocessing after late labels possible; the project's captured SSE files play the same role as a replayable log.

**S14. Zaharia et al. 2012 (RDDs / Spark)**
- M. Zaharia, M. Chowdhury, T. Das, A. Dave, J. Ma, M. McCauley, M. J. Franklin, S. Shenker, and I. Stoica, "Resilient distributed datasets: A fault-tolerant abstraction for in-memory cluster computing," in Proc. 9th USENIX Symposium on Networked Systems Design and Implementation (NSDI '12), San Jose, CA, pp. 15-28, Apr. 2012. No DOI (USENIX). — [USENIX page](https://www.usenix.org/conference/nsdi12/technical-sessions/presentation/zaharia) (the page spells the sixth author "McCauly"; the paper spells it "McCauley" — UNVERIFIED which the IEEE entry should use; the paper PDF was not opened)
- [READ] RDDs are a distributed memory abstraction for fault-tolerant in-memory computation, built on coarse-grained transformations rather than fine-grained updates — [USENIX page](https://www.usenix.org/conference/nsdi12/technical-sessions/presentation/zaharia)
- [READ] Keeping data in memory is reported to improve iterative and interactive workloads by about an order of magnitude; implemented as Spark — [USENIX page](https://www.usenix.org/conference/nsdi12/technical-sessions/presentation/zaharia)
- Applies to an edit stream: the batch side of the project (monthly dump processing) runs on this engine; lineage-based recomputation is what allows deterministic rebuilds of silver and gold tables.

**S15. Zaharia et al. 2013 (Discretized Streams)**
- M. Zaharia, T. Das, H. Li, T. Hunter, S. Shenker, and I. Stoica, "Discretized streams: Fault-tolerant streaming computation at scale," in Proc. 24th ACM Symposium on Operating Systems Principles (SOSP '13), pp. 423-438, Nov. 2013. DOI 10.1145/2517349.2522737 — [Crossref](https://api.crossref.org/works/10.1145/2517349.2522737); [PDF read](https://people.csail.mit.edu/matei/papers/2013/sosp_spark_streaming.pdf)
- [READ] Treats a stream as a series of small deterministic batch computations and recovers lost state from the lineage graph without replication — [PDF](https://people.csail.mit.edu/matei/papers/2013/sosp_spark_streaming.pdf)
- [READ] Reports over 60 million records per second on 100 nodes at sub-second latency, with sub-second recovery from faults and stragglers — [PDF](https://people.csail.mit.edu/matei/papers/2013/sosp_spark_streaming.pdf)
- Applies to an edit stream: the micro-batch model the project's streaming job still runs under; D-Streams window by arrival (processing) time, which is the limitation Structured Streaming's event-time watermarks address.

**S16. Armbrust et al. 2018 (Structured Streaming)** — already in the report draft; re-verified
- M. Armbrust, T. Das, J. Torres, B. Yavuz, S. Zhu, R. Xin, A. Ghodsi, I. Stoica, and M. Zaharia, "Structured Streaming: A declarative API for real-time applications in Apache Spark," in Proc. 2018 International Conference on Management of Data (SIGMOD '18), pp. 601-613, May 2018. DOI 10.1145/3183713.3190664 — [Crossref](https://api.crossref.org/works/10.1145/3183713.3190664); [PDF read](https://people.eecs.berkeley.edu/~matei/papers/2018/sigmod_structured_streaming.pdf)
- [READ] A high-level streaming API on Spark SQL in which a query over a stream is written like a query over a table and incrementalized by the engine — [PDF](https://people.eecs.berkeley.edu/~matei/papers/2018/sigmod_structured_streaming.pdf)
- [READ] Watermark for an event-time column C with delay t_C is max(C) − t_C; the paper notes this is robust to backlogged data, and that watermarks decide when stateful operators can emit and forget state — [PDF, section 4.3.1](https://people.eecs.berkeley.edu/~matei/papers/2018/sigmod_structured_streaming.pdf)
- [READ] The paper justifies bounding lateness because arbitrarily late data would require storing arbitrarily old state — [PDF, section 4.3.1](https://people.eecs.berkeley.edu/~matei/papers/2018/sigmod_structured_streaming.pdf)
- Applies to an edit stream: the project's `withWatermark` call is exactly this definition; a revert that arrives later than the delay falls outside the streaming aggregate and must be picked up by a later batch reconciliation.

**S17. Apache Spark documentation (watermark semantics; official, not peer-reviewed)**
- Apache Software Foundation, "Structured Streaming Programming Guide: APIs on DataFrames and Datasets," Apache Spark documentation (latest; the top-level guide page reported version 4.3.0 on the access date). Accessed Nov. 17, 2026. — [page read](https://spark.apache.org/docs/latest/streaming/apis-on-dataframes-and-datasets.html)
- [READ] Watermarking was introduced in Spark 2.1; state for a window ending at T is kept until (max event time seen − late threshold) > T — [docs, "Handling Late Data and Watermarking"](https://spark.apache.org/docs/latest/streaming/apis-on-dataframes-and-datasets.html)
- [READ] The guarantee is one-directional: data delayed by less than the threshold is never dropped; data delayed by more is "not guaranteed to be dropped" and may or may not be aggregated — [docs, "Semantic Guarantees of Aggregation with Watermarking"](https://spark.apache.org/docs/latest/streaming/apis-on-dataframes-and-datasets.html)
- [READ] In append mode a windowed aggregate is written to the result table only after the watermark passes the window end — [docs](https://spark.apache.org/docs/latest/streaming/apis-on-dataframes-and-datasets.html)
- Applies to an edit stream: the precise statement to cite when the report explains why a streamed revert count is final only after the watermark and why very late reverts are not counted by the stream.

**S18. Carbone et al. 2015 (Flink)**
- P. Carbone, A. Katsifodimos, S. Ewen, V. Markl, S. Haridi, and K. Tzoumas, "Apache Flink: Stream and batch processing in a single engine," Bulletin of the IEEE Computer Society Technical Committee on Data Engineering, vol. 38, no. 4, pp. 28-38, Dec. 2015. No DOI. — [PDF read](http://sites.computer.org/debull/A15dec/p28.pdf). Notes: the PDF's first page prints the authors in the order Carbone, Ewen, Haridi, Katsifodimos, Markl, Tzoumas (a three-column layout); the order above is the commonly cited one. UNVERIFIED: which author order the Bulletin's table of contents uses, and the end page 38 (start page 28 is in the file name; volume/issue from the "A15dec" issue path and recall).
- [READ] Batch programs are treated as a special case of streaming dataflows executed by one pipelined, fault-tolerant engine — [PDF](http://sites.computer.org/debull/A15dec/p28.pdf)
- [READ] A watermark carries a time t stating that all events with time lower than t have entered the operator; watermarks start at sources, and an operator with several inputs forwards the minimum of the incoming watermarks; event-time windows fire when the watermark passes the window end — [PDF, section 4.1](http://sites.computer.org/debull/A15dec/p28.pdf)
- Applies to an edit stream: the alternative record-at-a-time engine to name when justifying Spark; its watermark definition is the same concept the project uses.

**S19. Akidau et al. 2013 (MillWheel)**
- T. Akidau, A. Balikov, K. Bekiroğlu, S. Chernyak, J. Haberman, R. Lax, S. McVeety, D. Mills, P. Nordstrom, and S. Whittle, "MillWheel: Fault-tolerant stream processing at Internet scale," Proceedings of the VLDB Endowment, vol. 6, no. 11, pp. 1033-1044, Aug. 2013. DOI 10.14778/2536222.2536229 — [Crossref](https://api.crossref.org/works/10.14778/2536222.2536229) (Crossref holds the short title "MillWheel"; the subtitle is from recall and is the standard citation form)
- [RECALL] Introduces the low watermark as a system-maintained bound on the event time of work still pending, used to decide when a time window can be considered complete — [DOI page](https://doi.org/10.14778/2536222.2536229)
- [RECALL] Provides exactly-once record delivery through per-key persistent state and checkpointing with deduplication — [DOI page](https://doi.org/10.14778/2536222.2536229)
- Applies to an edit stream: the origin of the watermark concept that both the Dataflow model and Spark cite; reference [2] in both the Dataflow paper and the Structured Streaming paper points to watermarks in this lineage (UNVERIFIED that both "[2]" entries are MillWheel; the reference lists were not read).

**S20. Akidau et al. 2015 (Dataflow model)** — already in the report draft as [20]; re-verified
- T. Akidau, R. Bradshaw, C. Chambers, S. Chernyak, R. J. Fernández-Moctezuma, R. Lax, S. McVeety, D. Mills, F. Perry, E. Schmidt, and S. Whittle, "The Dataflow model: A practical approach to balancing correctness, latency, and cost in massive-scale, unbounded, out-of-order data processing," Proceedings of the VLDB Endowment, vol. 8, no. 12, pp. 1792-1803, Aug. 2015. DOI 10.14778/2824032.2824076 — [Crossref](https://api.crossref.org/works/10.14778/2824032.2824076); [PDF read](https://www.vldb.org/pvldb/vol8/p1792-Akidau.pdf)
- [READ] Position: stop treating unbounded data as something that eventually becomes complete; assume new data will arrive and "old data may be retracted", and let the user trade off correctness, latency and cost — [PDF, section 1](https://www.vldb.org/pvldb/vol8/p1792-Akidau.pdf)
- [READ] Separates event time from processing time; windowing (fixed, sliding, session) is by event time; triggers decide when a pane is emitted — [PDF](https://www.vldb.org/pvldb/vol8/p1792-Akidau.pdf)
- [READ] Watermarks alone are judged insufficient: they can be too fast (late data arrives behind them) or too slow (one slow datum holds back the pipeline) — [PDF, section 2.3](https://www.vldb.org/pvldb/vol8/p1792-Akidau.pdf)
- Applies to an edit stream: gives the vocabulary (event time, watermark, late datum, pane, refinement) for describing a live revert count that is revised as labels arrive.

**S21. Kreps 2014 (Kappa architecture; blog, not peer-reviewed)**
- J. Kreps, "Questioning the Lambda Architecture," O'Reilly Radar, July 2, 2014. — [page read](https://www.oreilly.com/radar/questioning-the-lambda-architecture/)
- [READ] Describes Lambda as an immutable input log feeding a batch pipeline and a stream pipeline in parallel, with results merged at query time, and attributes it to Nathan Marz's post "How to beat the CAP theorem" — [page](https://www.oreilly.com/radar/questioning-the-lambda-architecture/)
- [READ] Proposes a single stream system instead: retain the input log (e.g. in Kafka), and to reprocess, start a second job from the beginning of the log writing to a new output table, then switch readers and delete the old table — [page](https://www.oreilly.com/radar/questioning-the-lambda-architecture/)
- Applies to an edit stream: the project is closer to Lambda (a live stream path plus a monthly-dump batch path that later overrides it); this is the citable source for the trade-off.

**S22. Marz and Warren 2015 (Lambda architecture; book)**
- N. Marz and J. Warren, Big Data: Principles and Best Practices of Scalable Realtime Data Systems. Shelter Island, NY: Manning, Apr. 2015. ISBN 978-1-61729-034-3. 328 pp. — [publisher page](https://www.manning.com/books/big-data)
- [READ] The publisher page states the book presents the Lambda Architecture — [publisher page](https://www.manning.com/books/big-data)
- [RECALL] Three layers: batch layer (immutable master dataset, recomputed views), serving layer (indexes batch views), speed layer (covers only recent data until the batch view catches up) — [publisher page](https://www.manning.com/books/big-data) (layer names not on the page read; UNVERIFIED from this session)
- Applies to an edit stream: the speed layer's results being "overwritten" by the batch layer is the direct analogue of stream labels being replaced by the later History snapshot.

### Inferences
- Structured Streaming's watermark (S16, S17) is a heuristic watermark in the Dataflow paper's sense (S20): it is derived from observed event times, so it can be "too fast" and late data behind it can exist. The Spark docs' one-directional guarantee is consistent with this.
- The project's design (stream first, reconcile against the monthly dump later) is a Lambda-style arrangement in Kreps's description (S21), with the reconciliation step doing what the Dataflow paper calls refinement of earlier results.

### Gaps
- No publisher or DBLP page was opened for the Kafka NetDB paper; venue and date come from the PDF footer only, page numbers unverified.
- MillWheel full text not opened; its bullets are [RECALL].
- Flink paper: author order and page range need a check against the Bulletin issue table of contents (`http://sites.computer.org/debull/A15dec/issue1.htm`, not opened).

---

## Key Question 3: Lakehouse sources (Delta Lake, Lakehouse, medallion architecture)

### Takeaway
Delta Lake (PVLDB 2020) and Lakehouse (CIDR 2021) are both confirmed; the medallion (bronze/silver/gold) pattern has no founding paper, and neither of those two papers contains the words bronze, silver (as a layer), gold or medallion, so it must be cited to Databricks documentation.

### Cited Findings

**S23. Armbrust et al. 2020 (Delta Lake)** — already in the report draft; re-verified
- M. Armbrust, T. Das, L. Sun, B. Yavuz, S. Zhu, M. Murthy, J. Torres, H. van Hovell, A. Ionescu, A. Łuszczak, M. Świtakowski, M. Szafrański, X. Li, T. Ueshin, M. Mokhtar, P. Boncz, A. Ghodsi, S. Paranjpye, P. Senster, R. Xin, and M. Zaharia, "Delta Lake: High-performance ACID table storage over cloud object stores," Proceedings of the VLDB Endowment, vol. 13, no. 12, pp. 3411-3424, Aug. 2020. DOI 10.14778/3415478.3415560 — [Crossref](https://api.crossref.org/works/10.14778/3415478.3415560); [PDF read](https://www.vldb.org/pvldb/vol13/p3411-armbrust.pdf)
- [READ] An ACID table layer over cloud object stores: a transaction log, itself stored in the object store, determines the content of each table version; writes use optimistic concurrency control and are serializable — [PDF](https://www.vldb.org/pvldb/vol13/p3411-armbrust.pdf)
- [READ] Listed features include time travel (query point-in-time snapshots or roll back), UPSERT, DELETE and MERGE, and streaming ingest with exactly-once semantics — [PDF](https://www.vldb.org/pvldb/vol13/p3411-armbrust.pdf)
- Applies to an edit stream: MERGE is how a late label updates an already-written row; time travel by table version gives the "what did the table say at time X" axis of the project's two-axis time travel.

**S24. Armbrust, Ghodsi, Xin, Zaharia 2021 (Lakehouse)**
- M. Armbrust, A. Ghodsi, R. Xin, and M. Zaharia, "Lakehouse: A new generation of open platforms that unify data warehousing and advanced analytics," in Proc. 11th Conference on Innovative Data Systems Research (CIDR '21), Jan. 2021. No DOI. — [PDF read](https://www.cidrdb.org/cidr2021/papers/cidr2021_paper17.pdf). UNVERIFIED: "11th" ordinal (from recall). CIDR papers have no page numbers in a bound volume.
- [READ] Argues the warehouse architecture will be replaced by a lakehouse that (i) uses open direct-access formats such as Parquet, (ii) has first-class support for machine learning and data science, and (iii) offers state-of-the-art performance — [PDF, abstract](https://www.cidrdb.org/cidr2021/papers/cidr2021_paper17.pdf)
- [READ] Defines a lakehouse as a data management system on low-cost, directly accessible storage that also provides ACID transactions, data versioning, auditing, indexing, caching and query optimization — [PDF, section 1](https://www.cidrdb.org/cidr2021/papers/cidr2021_paper17.pdf)
- [READ] A text search of the paper finds no occurrence of "bronze", "medallion" or "gold"; "silver" appears only in a reference title — [PDF](https://www.cidrdb.org/cidr2021/papers/cidr2021_paper17.pdf)
- Applies to an edit stream: justifies keeping raw captures, cleaned tables and aggregates in one open-format store with versioning, instead of a separate lake and warehouse.

**S25. Databricks documentation (medallion architecture; vendor documentation, no founding paper)**
- Databricks, "What is the medallion lakehouse architecture?," Databricks on AWS documentation. Page shows last-updated Oct. 29, 2026. Accessed Nov. 17, 2026. — [page read](https://docs.databricks.com/aws/en/lakehouse/medallion)
- [READ] Bronze holds raw, unvalidated source data kept mostly unchanged for reprocessing and auditing; silver holds validated, cleaned, deduplicated and enriched data; gold holds refined, usually aggregated data modeled for analytics and applications — [page](https://docs.databricks.com/aws/en/lakehouse/medallion)
- [READ] The page calls it a data design pattern, also known as multi-hop architecture, and a recommended practice rather than a requirement; it gives no origin or academic citation — [page](https://docs.databricks.com/aws/en/lakehouse/medallion)
- Applies to an edit stream: bronze = raw SSE events and dump rows, silver = cleaned edits joined to revert labels, gold = lag and error aggregates; keeping bronze unchanged is what permits re-deriving silver when labels arrive late.

### Inferences
- Because the pattern is vendor terminology, the report should say plainly that "medallion architecture" is a Databricks naming convention with no founding paper, and cite S25 for the layer definitions and S23/S24 for the storage mechanisms underneath.

### Gaps
- No peer-reviewed source defining bronze/silver/gold was found; none was searched for beyond the two Databricks-authored papers and the documentation page.
- The first public use of the term "medallion" (date, author) was not established.

---

## Key Question 4: What the sources say about late or out-of-order data and correcting results after the fact

### Takeaway
Four distinct, citable mechanisms exist for correcting results after the fact: Dataflow's refinement modes (discarding, accumulating, accumulating and retracting), Spark's bounded-lateness watermark with a one-directional guarantee, Golab and Johnson's per-partition consistency levels (Open, Closed, Complete) for a continuously loaded warehouse, and bitemporal tables (valid time plus transaction time) that keep both the fact and when the database learned it.

### Cited Findings

**Dataflow refinement modes (S20)**
- [READ] Three modes govern how successive panes of the same window relate: Discarding (each pane holds only new data), Accumulating (each pane holds the full result so far, so a later pane overwrites an earlier one), and Accumulating and Retracting (the new pane is emitted together with a retraction of the previous pane) — [Akidau et al. 2015, section 2.3](https://www.vldb.org/pvldb/vol8/p1792-Akidau.pdf)
- [READ] Retractions are needed when downstream consumers regroup the data by a different key, so the earlier output's effect can be reversed — [Akidau et al. 2015, section 2.3](https://www.vldb.org/pvldb/vol8/p1792-Akidau.pdf)
- [READ] The paper describes the Lambda Architecture as low-latency streaming results later overwritten by batch results — [Akidau et al. 2015, section 2.3](https://www.vldb.org/pvldb/vol8/p1792-Akidau.pdf)
- [READ] In the worked examples, a single late datum appears behind the heuristic watermark; whether it is incorporated depends on the trigger and allowed lateness chosen — [Akidau et al. 2015, section 2.4 figures](https://www.vldb.org/pvldb/vol8/p1792-Akidau.pdf)

**Spark Structured Streaming (S16, S17)**
- [READ] Late events within the watermark delay update the old window's aggregate; events beyond it start to be dropped; the engine never drops data delayed by less than the threshold but does not promise to drop data delayed by more — [Spark docs](https://spark.apache.org/docs/latest/streaming/apis-on-dataframes-and-datasets.html)
- [READ] Watermark = max(C) − t_C on event-time column C — [Armbrust et al. 2018, section 4.3.1](https://people.eecs.berkeley.edu/~matei/papers/2018/sigmod_structured_streaming.pdf)

**S26. Golab and Johnson 2011 (stream warehouse consistency)** — already in the report draft as [21]; re-verified
- L. Golab and T. Johnson, "Consistency in a stream warehouse," in Proc. 5th Biennial Conference on Innovative Data Systems Research (CIDR '11), Asilomar, CA, Jan. 9-12, 2011. No DOI. — [PDF read](https://www.cidrdb.org/cidr2011/Papers/CIDR11_Paper13.pdf). The PDF is 9 pages. UNVERIFIED: proceedings page range (commonly cited as pp. 114-122; not confirmed this session).
- [READ] Defines a stream warehouse as a stream system that stores a very long history, or equivalently a continuously loaded warehouse; states the tension that users want timely results but stable results need long synchronization delays — [PDF, abstract](https://www.cidrdb.org/cidr2011/Papers/CIDR11_Paper13.pdf)
- [READ] Develops a theory of temporal consistency with multiple levels per temporal partition: Open (data may exist, more may come), Closed (no more updates expected), Complete (Closed and all expected data arrived); a derived view's partition is Closed/Complete only if all source partitions it depends on are — [PDF, sections 3-4](https://www.cidrdb.org/cidr2011/Papers/CIDR11_Paper13.pdf)
- [READ] Queries can be restricted to a required consistency level, and view maintenance can be scheduled using the levels; consistency markers are described as a generalization of punctuations — [PDF](https://www.cidrdb.org/cidr2011/Papers/CIDR11_Paper13.pdf)
- [READ] The paper notes one can no longer assume data arrive in time order or that feeds are synchronized — [PDF, section 1](https://www.cidrdb.org/cidr2011/Papers/CIDR11_Paper13.pdf)
- Applies to an edit stream: a day's revert-rate partition is Open while reverts can still arrive, Closed after a chosen wait, and Complete once the monthly History snapshot covering it is loaded; this gives formal names to "how long to wait before trusting a count".

**S27. Snodgrass (bitemporal tables)** — already in the report draft as [24]; re-verified with a date note
- R. T. Snodgrass, Developing Time-Oriented Database Applications in SQL. San Francisco, CA: Morgan Kaufmann, 504+xxiii pp., ISBN 1-55860-436-7. — [author's publications page](https://www2.cs.arizona.edu/~rts/publications.html) (the author's page gives the publication date as July 1999 and links a free PDF; the book is almost always cited with year 2000, its copyright year. UNVERIFIED: which year the title page prints; the PDF was not opened.)
- [RECALL] Distinguishes valid time (when a fact was true in the world) from transaction time (when the database recorded it); a bitemporal table carries both, so past database states can be reconstructed and corrections are recorded without overwriting — [author's page](https://www2.cs.arizona.edu/~rts/publications.html)
- [RECALL] Gives SQL patterns for current, sequenced and nonsequenced queries and modifications over such tables — [author's page](https://www2.cs.arizona.edu/~rts/publications.html)
- Applies to an edit stream: edit timestamp = valid time; time the pipeline learned of the revert = transaction time. The project's "time travel on both knowledge axes" is a bitemporal query.

**S28. Kimball and Ross 2013 (dimensional modeling)** — already in the report draft as [23]; re-verified
- R. Kimball and M. Ross, The Data Warehouse Toolkit: The Definitive Guide to Dimensional Modeling, 3rd ed. Indianapolis, IN: Wiley, July 2013. ISBN 978-1-118-53080-1. 608 pp. — [publisher page](https://www.wiley.com/en-us/The+Data+Warehouse+Toolkit%3A+The+Definitive+Guide+to+Dimensional+Modeling%2C+3rd+Edition-p-9781118530801)
- [READ] Title, authors, edition, date, ISBN and page count confirmed on the publisher page; the page description mentions star schemas and ETL chapters but does not name slowly changing dimensions or late-arriving facts — [publisher page](https://www.wiley.com/en-us/The+Data+Warehouse+Toolkit%3A+The+Definitive+Guide+to+Dimensional+Modeling%2C+3rd+Edition-p-9781118530801)
- [RECALL] The book defines slowly changing dimension types (type 1 overwrite, type 2 add a new row with effective dates, and others) and treats late-arriving facts and late-arriving dimensions. UNVERIFIED this session: chapter numbers — [publisher page](https://www.wiley.com/en-us/The+Data+Warehouse+Toolkit%3A+The+Definitive+Guide+to+Dimensional+Modeling%2C+3rd+Edition-p-9781118530801)
- Applies to an edit stream: a revert label that arrives after the edit fact row was loaded is a late-arriving attribute; type 2 history on the label is the dimensional-modeling counterpart of a bitemporal row.

**S29. Hellerstein, Haas, Wang 1997 (online aggregation)** — already in the report draft as [22]; re-verified
- J. M. Hellerstein, P. J. Haas, and H. J. Wang, "Online aggregation," in Proc. 1997 ACM SIGMOD International Conference on Management of Data (SIGMOD '97), pp. 171-182, 1997. DOI 10.1145/253260.253291 — [Crossref](https://api.crossref.org/works/10.1145/253260.253291)
- [RECALL] Proposes showing a running estimate of an aggregate with a confidence interval that tightens as more tuples are processed, letting the user stop early — [DOI page](https://doi.org/10.1145/253260.253291)
- [RECALL] Requires processing tuples in random order for the interval to be statistically valid — [DOI page](https://doi.org/10.1145/253260.253291)
- Applies to an edit stream: precedent for reporting an early answer with a stated error; the difference to note is that online aggregation's error comes from sampling, while a live revert rate's error comes from labels that have not yet arrived, which is not random.

**S30. Begoli et al. 2019 (streams and tables in SQL; optional)**
- E. Begoli, T. Akidau, F. Hueske, J. Hyde, K. Knight, and K. Knowles, "One SQL to rule them all: An efficient and syntactically idiomatic approach to management of streams and tables," in Proc. 2019 International Conference on Management of Data (SIGMOD '19), pp. 1757-1772, June 2019. DOI 10.1145/3299869.3314040 — [Crossref](https://api.crossref.org/works/10.1145/3299869.3314040)
- [RECALL] Proposes SQL extensions built on time-varying relations, event-time semantics with watermarks, and materialization controls, including emitting changes as a stream with retractions — [DOI page](https://doi.org/10.1145/3299869.3314040)
- Applies to an edit stream: supports describing the revert-labelled edit table as a time-varying relation whose earlier answers are revised.

**Re-verification of entries already in the report draft (lines 330-350)**
- Akidau et al. 2015: PVLDB 8(12), pp. 1792-1803 — correct; add pages and full subtitle — [Crossref](https://api.crossref.org/works/10.14778/2824032.2824076)
- Golab and Johnson, CIDR 2011 — correct; paper is `CIDR11_Paper13.pdf`; page range unverified — [PDF](https://www.cidrdb.org/cidr2011/Papers/CIDR11_Paper13.pdf)
- Hellerstein, Haas, Wang, SIGMOD 1997 — correct; pp. 171-182 — [Crossref](https://api.crossref.org/works/10.1145/253260.253291)
- Kimball and Ross, 3rd ed., Wiley 2013 — correct — [Wiley](https://www.wiley.com/en-us/The+Data+Warehouse+Toolkit%3A+The+Definitive+Guide+to+Dimensional+Modeling%2C+3rd+Edition-p-9781118530801)
- Snodgrass, Morgan Kaufmann, "2000" — author's page says published July 1999; 2000 is the usual citation year; flag for the owner — [author page](https://www2.cs.arizona.edu/~rts/publications.html)
- Flajolet, Fusy, Gandouet, Meunier, AofA 2007 — correct; pages 127-146, DMTCS Proceedings vol. AH — [PDF](https://algo.inria.fr/flajolet/Publications/FlFuGaMe07.pdf)
- Armbrust et al., Delta Lake, PVLDB 13(12), 2020 — correct; pp. 3411-3424; 21 authors — [Crossref](https://api.crossref.org/works/10.14778/3415478.3415560)
- Armbrust et al., Structured Streaming, SIGMOD 2018 — correct; pp. 601-613; 9 authors — [Crossref](https://api.crossref.org/works/10.1145/3183713.3190664)
- Flajolet and Martin, JCSS 31(2), 1985 — correct; pp. 182-209 — [Crossref](https://api.crossref.org/works/10.1016/0022-0000(85)90041-8)
- Bloom, CACM 13(7), 1970 — correct; pp. 422-426 — [Crossref](https://api.crossref.org/works/10.1145/362686.362692)
- Datar, Gionis, Indyk, Motwani, SIAM J. Computing 31(6), 2002 — correct; pp. 1794-1813 — [Crossref](https://api.crossref.org/works/10.1137/S0097539701398363)
- Alon, Matias, Szegedy, STOC 1996 — correct; pp. 20-29; a journal version (JCSS 58(1), 1999, pp. 137-147) also exists — [Crossref STOC](https://api.crossref.org/works/10.1145/237814.237823); [Crossref JCSS](https://api.crossref.org/works/10.1006/jcss.1997.1545)
- Vitter, ACM TOMS 11(1), 1985 — correct; pp. 37-57 — [Crossref](https://api.crossref.org/works/10.1145/3147.3165)
- Broder 1997 (SEQUENCES) and the privacy/LSH entries are outside this topic and were not checked.

### Inferences
- The project's reconciliation (stream label replaced by the History snapshot label) corresponds to Dataflow's Accumulating mode when the gold row is overwritten, and to Accumulating and Retracting if the old value is also kept as a reversed row; a bitemporal silver table keeps both without choosing.
- Golab and Johnson's Closed level and Spark's watermark answer the same question (when to stop waiting) at different layers: the watermark bounds operator state inside the stream job, while Closed/Complete are warehouse-level statements that can be set from outside knowledge such as "the monthly dump has been loaded".
- None of these sources measures the size of the error in an Open result as a function of how long one waits; they define mechanisms and levels, not the error curve. This supports the gap statement the report draft asks the owner to write (inference from the texts read, not a claim that no such work exists anywhere).

### Gaps
- Snodgrass and Kimball/Ross book contents were not opened; the content bullets are [RECALL]. Chapter and page pointers for bitemporal tables and for late-arriving facts are missing.
- Dataflow's "allowed lateness" parameter is part of the later Beam model; whether the 2015 paper itself names it was not confirmed in the text search.
- Golab and Johnson page range in the CIDR 2011 proceedings is unverified.

---

## Key Question 5: Citable sources for Neo4j / property graphs and for document stores (MongoDB)

### Takeaway
Peer-reviewed sources exist for both: Angles et al. 2017 (ACM Computing Surveys) and Francis et al. 2018 (SIGMOD) for the property graph model and Cypher, and Schultz et al. 2019 (PVLDB) for MongoDB; official documentation pages cover the basic data-model definitions.

### Cited Findings

**S31. Angles et al. 2017 (graph query language foundations)**
- R. Angles, M. Arenas, P. Barceló, A. Hogan, J. Reutter, and D. Vrgoč, "Foundations of modern query languages for graph databases," ACM Computing Surveys, vol. 50, no. 5, Article 68, pp. 1-40, Sept. 2017. DOI 10.1145/3104031 — [Crossref](https://api.crossref.org/works/10.1145/3104031) (UNVERIFIED: article number 68, from recall; Crossref gives pp. 1-40)
- [RECALL] Surveys the two main graph data models (edge-labelled graphs and property graphs) and the core query features: graph patterns and navigational (path) expressions, with their semantics and complexity — [DOI page](https://doi.org/10.1145/3104031)
- [RECALL] Compares SPARQL, Cypher and Gremlin against those core features — [DOI page](https://doi.org/10.1145/3104031)
- Applies to an edit stream: formal definition of the property graph used to store revert links (revision or user nodes, REVERTED edges with timestamp properties).

**S32. Francis et al. 2018 (Cypher)**
- N. Francis, A. Green, P. Guagliardo, L. Libkin, T. Lindaaker, V. Marsault, S. Plantikow, M. Rydberg, P. Selmer, and A. Taylor, "Cypher: An evolving query language for property graphs," in Proc. 2018 International Conference on Management of Data (SIGMOD '18), pp. 1433-1445, May 2018. DOI 10.1145/3183713.3190657 — [Crossref](https://api.crossref.org/works/10.1145/3183713.3190657) (Crossref holds the short title "Cypher"; subtitle from recall, standard citation form)
- [RECALL] Describes Cypher's design and gives a formal semantics for its core read fragment, including pattern matching over property graphs — [DOI page](https://doi.org/10.1145/3183713.3190657)
- [RECALL] Describes the language's evolution through the openCypher effort — [DOI page](https://doi.org/10.1145/3183713.3190657)
- Applies to an edit stream: the citation for the query language used on the revert graph (e.g. mutual-revert pairs as a two-edge pattern).

**S33. Neo4j documentation (official)**
- Neo4j, Inc., "Graph database concepts," Neo4j Getting Started documentation. Accessed Nov. 17, 2026. — [page read](https://neo4j.com/docs/getting-started/appendix/graphdb-concepts/)
- [READ] Nodes represent entities and can carry zero or more labels; a relationship connects a source node to a target node, has a direction and exactly one type; nodes and relationships can both hold key-value properties — [page](https://neo4j.com/docs/getting-started/appendix/graphdb-concepts/)
- Applies to an edit stream: direction matters for reverts (who reverted whom), and late-arriving revert links are added as new relationships without changing existing nodes.

**S34. Schultz, Avitabile, Cabral 2019 (MongoDB; peer-reviewed)**
- W. Schultz, T. Avitabile, and A. Cabral, "Tunable consistency in MongoDB," Proceedings of the VLDB Endowment, vol. 12, no. 12, pp. 2071-2081, Aug. 2019. DOI 10.14778/3352063.3352125 — [Crossref](https://api.crossref.org/works/10.14778/3352063.3352125)
- [RECALL] Describes MongoDB's replication and its per-operation consistency controls (write concern and read concern), and how users trade latency against durability and consistency — [DOI page](https://doi.org/10.14778/3352063.3352125)
- Applies to an edit stream: the peer-reviewed citation for MongoDB as the serving store for gold results; relevant when results are re-loaded after reconciliation and readers may briefly see the older value.

**S35. MongoDB documentation (official)**
- MongoDB, Inc., "Documents," MongoDB Database Manual. Accessed Nov. 17, 2026. — [page read](https://www.mongodb.com/docs/manual/core/document/)
- [READ] Records are stored as BSON documents made of field-and-value pairs; values may be embedded documents and arrays; maximum BSON document size is 16 mebibytes — [page](https://www.mongodb.com/docs/manual/core/document/)
- [READ] `_id` is the primary key, unique within the collection and immutable; an ObjectId is generated if it is omitted — [page](https://www.mongodb.com/docs/manual/core/document/)
- Applies to an edit stream: a deterministic `_id` (e.g. window plus as-of date) makes re-loading corrected results an idempotent upsert rather than a duplicate insert.

### Inferences
- For an IEEE reference list, S31 and S32 suffice for the graph side and S34 for the document side; S33 and S35 are only needed if the report states specific data-model facts (direction, 16 MiB limit, `_id`).

### Gaps
- Angles et al., Francis et al. and Schultz et al. full texts were not opened; bibliographic data is from Crossref and content bullets are [RECALL].
- No source specific to MongoDB Atlas (the hosted service) was sought; Atlas has only vendor documentation as far as this session established (nothing opened).
