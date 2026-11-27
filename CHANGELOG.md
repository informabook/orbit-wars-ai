# Changelog

## 0.3.0 — Reusable research framework

- Finalized the Phase 3 public scope under MIT for original contributions. Preserved third-party attribution, unresolved-source decisions and the experiment fingerprints.
- Added the authorized original 80-page V5 report, its publication assessment, the conceptual workflow diagram and a chart of recorded V14 training checkpoints.
- Added clean release verification, the public file manifest, release notes and private GitHub handoff instructions.

### Phase 3 research framework

- Added a separate, installable tournament, variant, hybrid, search and staged evaluation interface. Both match scoring paths require valid terminal statuses. The simulator seed is checked before and after play, with no retry that drops it.
- Recovered the V14 feature functions from the verified notebook and added explicit, deduplicated JSON replay ingestion. The new ranker splits by replay, scales from training data only, gives ties half credit in ROC AUC, and writes JSON for inference.
- Added project-owned demonstration agents, bounded configurations, experiment manifests and pytest coverage. A local registry pins source bytes without copying agent files.
- Added archived match-level projections, Beast parameters and evaluation rounds, replay-derived statistics, the V14 learning curve, and four data-backed notebooks.
- Kept archived results and the Phase 2 historical modules. New method behavior and fixture outcomes belong to Phase 3.

## Phase 2 — Archival publication draft

Selected authentic excerpts, results and source references. Recorded the historical Kaggle result, the zero ranker export coefficient and the limits of the recovered Holdout evidence. Preserved the exact historical candidate archive and V5 PDF in a separate private handoff.
