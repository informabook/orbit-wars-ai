# Visual assets and competition evidence

| Asset | Source and scope |
| --- | --- |
| [Architecture PNG](research-architecture.png) and [SVG](research-architecture.svg) | Original conceptual diagram of the research workflow. Dashed connections signal an experimental overlay or an evidence gap. The diagram gives no proof that a particular feature was deployed. |
| [V14 training curve](v14-training-curve.png) | Rendered from 131 archived checkpoints in [the V14 table](../results/phase3/v14_training_curve.csv). Original archived metrics with their original split. |
| [Historical evaluation chart](../docs/figures/historical-results.png) | Existing project figure drawn from the recorded evolution attempts and Beast Lab Full-stage deltas. |

Regenerate the new assets with `python assets/render_figures.py` from the repository root after installing the analysis extra. The historical chart uses `orbit-research plot-history`. The [Orbit Wars Research Report](../Orbit_Wars_Research_Report.pdf) provides the scientific context for the figures.

## Authentic capture review

Three 26 November 2026 captures and the later owner-supplied leaderboard row were checked in the private handoff. The [Kaggle terms](https://www.kaggle.com/terms) govern site content. A reusable permission for the captured site interface and game visuals was not established during the audit. The release therefore provides source links and factual descriptions. The captures stay in the private evidence folder with their source fingerprints.

| Capture | What it establishes | Source |
| --- | --- | --- |
| Competition overview | Orbit Wars 2P and 4P description and a participation total of 4,729 teams. | [Kaggle overview](https://www.kaggle.com/competitions/orbit-wars/) |
| Historical submissions | A completed entry named `best_generated_submission.tar.gz` and a second guided candidate entry. The displayed 1068.9 is a capture value. | [Kaggle submissions](https://www.kaggle.com/competitions/orbit-wars/submissions) may depend on the account. |
| Authentic replay | The captured UI displays a two-player win for InformaBook2 at step 53 of the shown episode. One replay does not establish an aggregate performance result or final archive identity. | [Kaggle competition](https://www.kaggle.com/competitions/orbit-wars/) |
| Final leaderboard row | The owner supplied a capture showing InformaBook2 at rank 611 and displayed score 1068.9. It corroborates V5’s placement and contains no uploaded-file fingerprint. | [Kaggle leaderboard](https://www.kaggle.com/competitions/orbit-wars/leaderboard) |

The release includes no official animation. Original source links and captures must retain their attribution if permission is later obtained.

The research report’s illustrated appendix contains schematics of Beast Lab, failure-guided candidate generation and 2P/4P routing, plus the documented chronology and quantitative views. Each archival plot reads the released evidence tables. [Research report](../Orbit_Wars_Research_Report.pdf)
