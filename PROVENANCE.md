# Source provenance

The selection draws on the Phase 1 archive audit and inventory. [SOURCE_PROVENANCE.csv](SOURCE_PROVENANCE.csv) records the source name, observed revision or SHA-256, attribution, scope, project changes and unresolved items. Historical file names and hashes identify the exact Phase 1 sources used to extract code and tables. The private handoff contains the exact exclusions register, including archive-member paths.

| Class | Meaning | Decision for this draft |
| --- | --- | --- |
| A | Project-owned material within the owner’s requested release scope | Include reviewed excerpts, selected experimental facts and Phase 2 tooling. The owner approved MIT for his original contributions, including the authorized original report. |
| B | Derivative material with verified source and redistribution rights | No material in this class is currently included. Each derivative requires a verified source revision and a license chain that covers the copied modules. |
| C | External material referenced by link or dependency | Link to the original publications or install versioned PyPI packages. |
| D | Unresolved provenance, privacy or redistribution rights | Keep the identified originals outside the publication tree. The register gives the next evidence needed. |

## Historical code retained

| Public module | Historical source | Contributions and extraction |
| --- | --- | --- |
| [OrbitLab](orbit_wars_research/orbitlab.py) | Main bundle's `orbit_lab.py` | Original task ordering, seat swaps, match worker, snapshots, actions and summaries. Phase 2 adapted the simulator registry name to `orbit_wars`. Notebook execution, agent discovery and archive extraction are outside this slice. |
| [Evolution](orbit_wars_research/evolution.py) | `orbit_evolution_intelligent_variants_v6_fixed.py` | Original single-parent mutation template and state-aware combination templates. Template output refers to separately supplied parent modules. Flattened baseline copies and full campaign orchestration were excluded. |
| [Beast Lab](orbit_wars_research/beast.py) | `orbit_wars_beast_lab_v18_base_adaptive.py` | Original parameter ranges, mutation, patching functions, contextual selection, match evaluator and validation gates. Phase 2 selected the imports and excluded the fetcher, submission commands, discovery and bulk run entry point. The recovered run is labeled V13. The V18 functions are preserved as an implementation example and their exact association with the run is unresolved. |
| [V14 ranker](orbit_wars_research/ranker_v14.py) | `orbit_wars_v14_fast_cpu_ranker_topk_selfplay_import.ipynb`, code cells 1 and 2 (zero-based) | Original feature order, training settings, linear trainer, and metric functions. Cell execution, feature extraction from the private corpus, the embedded game policy, serialized weights and executable outputs were outside the public slice. |

The code-body review found no reused baseline policy implementation within the retained definitions. The project attribution covers these research contributions. It does not establish the authorship of every historical file, or who first wrote common utilities. The original file fingerprints and definition ranges are recorded for independent review. The only code-body change from the source of the historical functions is any change expressly documented here. Import blocks were rebuilt for the extracted modules, literal V14 settings were copied as values, and source line endings were normalized.

## Final candidate and indirect dependencies

The historical `best_generated_submission.tar.gz` is a private exact copy. Its 84 regular members comprise 70 Python sources and 14 caches. Local SHA-256:

```text
b444dc65423bf5288fc0e5a463811ad02ec81123c54c1dab01a21273d3a7a5e4
```

| Layer | Confirmed evidence | Remaining question |
| --- | --- | --- |
| Outer wrapper | `main.py` declares a generation 2 `combo_situation`. It references parent 014 `submission_v38_exact_producer_direct` and a generation 1 combination with parent 016 `submission_v40_exact_producer_control`. The wrapping logic changes which policy is called and supplies a fallback. | Link the binary to a Kaggle submission ID and downloadable content or fingerprint. |
| Producer child modules | Nine top-level definitions match ASTs exactly between local Producer V2 notebook cell 2 and each of `combo0_main.py`, `combo1_combo0_main.py`, `combo1_combo1_main.py`. Matches include `ProducerLiteConfig`, `cheap_enemy_pressure`, `plan_lite_waves`, `run_turn`, `ProducerLiteRuntime` and `agent`. AST comparison ignores whitespace and source position. | Compare against the exact public V2 notebook revision. A matching function AST is local evidence and leaves module-level settings, imports and licensing open. |
| Indirect utilities | For each sampled family (`adapter`, `planner_core`, `movement`, `garrison_launch`, `obs`), all four `combo*` copies match the corresponding packaged `orbit_lite` file after removing import statements and normalizing line endings. This is evidence of flattening and import rewriting. | Retrieve the exact Slawek Biel utilities release, compare every packaged utility and verify dataset license and notices. |
| FlowDiff | A public candidate page displays Apache 2.0 and credits a private parent notebook. The local FlowDiff notebook lacks a verified match to that page or revision. | Find the upstream chain and compare the cells. There is no evidence establishing a FlowDiff dependency of this specific final archive. |
| Other external policies | The heuristic and exp34 URLs occur in local notebooks. The local notebooks labeled 1266 and 1335.5 have no verified original revision. | Resolve original authorship and inherited parts for each prospective opponent or baseline. |

The actual Kaggle result and the local binary have separate evidence. The V5 report documents the finish and archive name. The public competition page gives the team count. Submission metadata and binary identity still need confirmation.

## Data and visuals

The evolution outputs retain all candidate and match records and omit absolute archive paths and raw error text. Error statuses remain intact. The Phase 2 schema audit additionally projects the 5,800 raw OrbitLab match JSONs into counts by mode and recorded status. The Beast tables preserve aggregate mode totals and evaluation values. Local IDs, file paths, raw replays, free-form errors, model arrays and embedded notebook outputs are outside the selection. A new chart renders the selected historical values. The exact V5 PDF is included under the owner’s authorization. The [report assessment](docs/research_report/PUBLICATION_ASSESSMENT.md) describes the figures, citations and retained private copy.

## Phase 3 recovery and new code

The [V14 feature excerpt](orbit_wars_research/replay_features_v14.py) comes from notebook code cell 2 (zero-based), lines 2–8, 119–571 and 623–715. The notebook SHA-256 is `2a3d3e49b3759605990841e57779d5a19098470c7845be43ac1c757e763cb91d`. Function bodies retain the notebook source. The module adds explicit imports, obtains the existing feature order from `ranker_v14.py`, and carries the necessary literal settings `SEED=13` and `MAX_NEG_PAR_POS=6` from cell 1. The reviewed excerpt parses shot geometry and builds features and labels. It does not contain the embedded agent, automated archive discovery, file access or a model payload. Phase 3 supplies separate ingestion and group-aware training around it.

The two demo policies `hold` and `nearest` are new project material created for this release candidate. They have no external policy parent. The other framework files, package configuration, tests and notebooks are Phase 3 additions. The current publication scope includes these original materials at the owner's request. The owner approved MIT for original project-owned contributions.

The [experiment manifest](results/phase3/EXPERIMENT_MANIFEST.json) documents the Phase 3 evidence projections and their verified source fingerprints. It includes a source-set digest for the individual OrbitLab archives. The expanded Beast and V14 tables contain project-computed values with source aliases or raw fields removed. The data dictionary explains join boundaries and flags. All outputs generated by the new CLI belong to new experiments and are kept separate.


## v0.3.0 licensing and attribution audit

The root [MIT license](LICENSE) applies to Florent Schobyn’s original code, documentation and project-created materials to the extent he owns the underlying rights. Third-party software, independently licensed dependencies, external policy bodies, data, screenshots and scholarly works keep their applicable terms. Metrics and factual comparisons in the report are attributed to their sources. The software citation metadata records MIT for the project software.

| Scope | Release decision |
| --- | --- |
| Original research tools, excerpts and reproducibility code | Included with MIT and the source records below. Historical Phase 3 code and evidence were retained byte-for-byte from the independently reviewed candidate. |
| V5 report | Included as the exact 80-page original with owner approval, confirmed SHA-256 and visual review. The [assessment](docs/research_report/PUBLICATION_ASSESSMENT.md) records the release decision and separate retrospective. |
| Public references, Kaggle Environments, NumPy and Matplotlib | Linked or installed under their own terms. No third-party policy body or dependency is vendored. |
| Producer V2, `orbit_lite`, FlowDiff and other derivative packages | Original lineages and public references are preserved. The exact applicable revision and full rights chain remain unresolved. Supply authorized agents through the [local registry](docs/reproduce.md#register-a-local-agent). |
| Replay corpus, archived weights and the final candidate archive | Excluded from the release. Reported metrics, permitted historical table projections and SHA-256 evidence are retained. |
| Kaggle UI and game captures | Reviewed privately, with contents and scope documented in the [asset index](assets/README.md). The audit did not verify reusable permission for the service artwork. |

The public file inventory is at [docs/release/PUBLIC_FILES.csv](docs/release/PUBLIC_FILES.csv). The [source register](SOURCE_PROVENANCE.csv) describes source identity, license scope, retained portions and evidence gaps.
