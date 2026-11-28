# Orbit Wars Research Report publication assessment

The [Orbit Wars Research Report](../../Orbit_Wars_Research_Report.pdf) is the primary scientific document of this repository. The canonical PDF is the exact 90-page V5.1 report. It contains the complete historical report and two owner-approved changes.

1. Page 1 reads “Étudiant en bac 2 informatique, École polytechnique de Louvain (EPL), UCLouvain”. The note identifies November 2026 as the date of that status. The report’s historical date remains 15 July 2026.
2. Ten illustrated appendix pages follow the original 80. Captions distinguish archived measurements, documented chronology and conceptual methods. The [builder](build_v51.py) uses the preserved V5 PDF and released tables.

Pages 2–80 match the archived PDF in extracted text and rendered pixels. Page 1 matches in text except for the authorized academic update. The original bookmarks and link annotations were retained. No existing body text, chapter, equation, table, figure, appendix or reference was removed.

V5.1 PDF SHA-256: `c8a70df4eada94f1b57e928ca8ed320c72cd75b54b3bf2fa7a135f18d0d1d7da`.

## Exact archived V5

The owner’s private archive and the v0.3.0 tag preserve the exact 80-page French V5 report, dated 15 July 2026. Both sources share this SHA-256.

~~~text
fdf0fc33690978d97d288c4afd49c70e6635f56dec9919ba11176a355db14207
~~~

Pages 45–46 give the historical placement and score. Page 47 links to the leading teams’ primary write-ups. For reconstruction use the [historical v0.3.0 source](https://github.com/informabook/orbit-wars-ai/blob/v0.3.0/docs/research_report/rapport_orbit_wars_v5_post_cloture.pdf) and follow the [build instructions](../reproduce.md#regenerate-the-research-report).

## Review and modification log

| Review item | Finding and decision |
| --- | --- |
| Figures 1–15 and 16–20 | All 20 image placements were visually reviewed. They appear to be project-rendered plots, tables or schematic boxes, including redrawn diagrams for the top solutions. No embedded Kaggle interface captures, third-party document scans or photographic illustrations were identified. Figures 16–20 use publicly attributed quantities and describe external designs. The source works and models retain their own terms. |
| Sources and quotations | The embedded links point to Kaggle write-ups or linked authors’ code. Inspected quotation-like passages on pages 42 and 63 are the author’s rules or paraphrases. No substantial third-party quotation was found requiring replacement. |
| Personal and confidential information | The title page attributes the author and includes academic context. The public report contains that author-approved attribution. Automated checks found no email addresses, personal filesystem paths or credential patterns. No forms or embedded attachments were found. PDF metadata contains TeX tooling and creation dates. |
| Historical and potentially outdated claims | The original narrative describes qualitative trends, historical approximations and proposed future validation. Read it with the retrospective below. The dedicated report and the release tables serve different evidentiary roles. |
| LaTeX sources | The Phase 1 search and targeted follow-up did not identify the matching TeX source. The release contains the canonical PDF. |

**Archived V5 modifications: none.** The release adds this companion assessment and a retrospective outside the report, preserving the original bytes and pagination. The interface screenshots are separate from the report. See the [asset evidence index](../../assets/README.md).

## Retrospective note

- **Match validity and seeds.** Phase 2 recovered 5,800 local outputs. The 1,962 OK labels lack per-agent terminal proof. Phase 3 rejects invalid simulator outcomes and requires the requested seed to be applied. These checks cannot retroactively validate the archived matches.
- **Replay learning.** V14’s reported validation AUC of 0.886154 comes from its historical example-level split and approximate metric. Phase 3 groups rows by replay and handles tied scores. V14’s export coefficient was zero. The project’s historical leaderboard performance cannot be assigned to the learned ranker.
- **Validation scope.** The archived Beast Lab run contains four negative Full-stage candidates and zero validated exports. Holdout appears in the design, but the historical evidence establishes no Holdout score.
- **Leaderboard and score.** V5 states 611 / 4,729 and a public score around 958.5. The November 26 Kaggle submissions capture shows a completed record with the same archive name and a displayed score of 1068.9. The score snapshots may reflect different times or views. The separate leaderboard capture corroborates rank 611 and the displayed 1068.9. Neither capture establishes comparability between snapshots or the SHA-256 of the uploaded bytes. The release cites the rank as documented in V5 and omits a headline score.
- **External RL systems.** The report analyzes the winning implementations retrospectively. Its diagrams and published-data comparisons are explanatory, and they do not attribute those systems or reported computations to this project. The [first-place write-up](https://www.kaggle.com/competitions/orbit-wars/writeups/1st-place-solution-scaling-reinforcement-learnin) and [second-place write-up](https://www.kaggle.com/competitions/orbit-wars/writeups/2nd-place-solution-for-orbit-wars) substantiate their authors’ model and training descriptions. Quantitative release graphics read the fingerprinted tables rather than reusing qualitative charts in the archival PDF.
