# Section II draft: notes for Scott and Tingyu

Files: `section_II.md` (Markdown, local [n] numbering), `section_II.tex` (`\section{Related Work}` with `\cite{key}`), `refs.bib` (41 entries, only the cited ones, no `%` comments), `build/main.tex` (test wrapper), `build/main.pdf` (test build), `build/make_md.py` (regenerates the .md from the .tex and .bib).

Size: about 1,300 words of prose in six subsections (A to E plus the gap), 41 references. The test build is 3 IEEE pages including the reference list.

## Decisions made

- Only sources labelled Confirmed, abstract-level or full-text in the guide are cited. No figure the guide marks UNVERIFIED or [RECALL] is quoted.
- **AMS:** cites the STOC 1996 conference version (`S07a_alon1996`), which matches the existing draft list. The JCSS 1999 version is not cited.
- **l-diversity:** cites the TKDD 2007 version (`P05a`) with the TKDD author order (Machanavajjhala, Kifer, Gehrke, Venkitasubramaniam).
- **k-anonymity:** cites the SRI tech report SRI-CSL-98-04 (`P01`) for generalization and suppression, not an IEEE S&P version, and Sweeney 2002 (`P03`) for the definition. The 87% uniqueness figure is not used.
- **Geiger and Halfaker 2013** is labelled "WikiSym '13" (Proc. 9th Int. Symp. Open Collaboration), not "OpenSym 2013". Pages are 1-6, the Crossref page field.
- **Flöck et al.** uses DOI 10.1145/2309996.2310000, not ...2310038. The "12% more full reverts" figure comes from the dissertation, so it is not used.
- **MD5 vs SHA-1:** MD5 is attributed to Priedhorsky et al. and Yasseri et al. SHA-1 is attributed only to the MediaWiki History field.
- **Lawless 1994** keeps the `.n1` DOI.
- **Medallion** is called a Databricks naming convention and cited to the Databricks documentation. Delta Lake is cited only for storage mechanisms.
- **Spark MinHashLSH** is described as OR-amplification only, so its candidate curve is 1-(1-s)^L and not an S-curve. The S-curve is cited to Andoni and Indyk and to the MMDS textbook, not to Broder.
- **Gap paragraph** uses the guide's wording, including "to our knowledge". It acknowledges Kumar et al. 2016 and the 48-hour note in Research:Revert, and calls the 4-day window the project's own design choice.
- **BibTeX comments resolved:**
  - Unverified conference cities removed (Priedhorsky, Kumar, Trokhymovych, Flöck, Viégas, Broder).
  - Hong Kong kept, because it is in the WikiSym paper's own header. Asilomar kept, because it was confirmed for CIDR '11.
  - The unverified "11th" ordinal is gone: Lakehouse (CIDR '21) was dropped, to keep the list near 40.
  - LNCS volume 3876 removed from Dwork et al. 2006 (UNVERIFIED).
  - Golab and Johnson has no page range (UNVERIFIED).
  - Snodgrass is kept as 2000.
  - HyperLogLog pages are 127-146.
- **Dwork and Roth 2014 not cited**, because its page range is disputed (211-407 vs 211-487). The 1/epsilon error statement is therefore left out.
- **All 23 existing draft references are kept** under these keys:
  - [10] D20, [11] D21, [12] D17, [15] W09, [16] W12, [17] W11, [18] W01, [19] W19
  - [20] S20, [21] S26, [22] S29, [23] S28, [24] S27, [25] S05
  - Delta Lake S23, Structured Streaming S16, Flajolet-Martin S04, Bloom S02, DGIM S08, AMS S07a, Vitter S01, Broder L01, Indyk-Motwani L04
  - The draft has no [13] or [14] in the guide's corrections table. Check whether those numbers exist in the report.
- **Compile:** built with Tectonic 0.15 (XeTeX engine, TeX Live bundle) using `IEEEtran.cls` and `IEEEtran.bst` 1.14. BibTeX ran with no warnings and there are no undefined citations. `pdflatex` could not be installed on the box (the Debian mirror returned 500). Both `refs.bib` and `section_II.tex` are pure ASCII, so they should also build under pdflatex and Overleaf.

## Check before submission

1. **The gap sentence.** The guide says to read two things before this is final:
   - the 2026 Wikimedia Phabricator "time-to-live" tasks (a median metric for reverted edits with a 7-day window);
   - post-2020 Wikimedia research output.
   Neither was opened. If either has a delay curve, narrow or cite it.
2. **Project numbers in the gap paragraph** ("about 42% at 1 h, 6.3% at 48 h") must match `docs/final/results.json` (57.95% known at 1 h). Run `check_numbers.py --text` on the merged report.
3. **Claims about teammates' methods.** Confirm with Wanru and Zhenni that these describe their work:
   - Wanru: the Neo4j edit-war analysis follows Yasseri et al.'s mutual-revert approach, and her LSH join filters on an exact Jaccard-distance threshold.
   - Zhenni: her analysis combines noise with threshold suppression, and the project publishes group counts only, never per-editor rows.
4. **Open items that touch cited references:**
   - Priedhorsky et al.: the 42% figure was confirmed in only one of two research sessions, and the end page 268 is not on Crossref.
   - Geiger and Halfaker: the article number is UNVERIFIED.
   - Snodgrass: the title-page year is UNVERIFIED (1999 vs 2000).
   - Kimball and Ross, and Snodgrass: the bitemporal and SCD content is [RECALL]. The text only names the concepts, so open either book before adding any detail.
   - Bloom and DGIM are cited by title only, because their content is [RECALL].
   - The Spark LSH guide text is from 4.3.0, which may not match the Spark version the project runs.
   - Croushore and Stark: the description comes from the working-paper abstract.
5. **The sliding-window remark** ("no step for revising an item already counted") and the mergeability remark are our synthesis, not claims from the founding papers.
6. **Numbering:** the Markdown uses local [1]-[41]. In the full report, LaTeX renumbers everything when Section II is merged with the other sections' `\cite`s. Merge `refs.bib` into the report's `.bib` and drop any duplicate keys.

## GenAI disclosure line

Section II drafted with AI assistance from a human-curated, citation-verified source guide; reviewed by the team.
