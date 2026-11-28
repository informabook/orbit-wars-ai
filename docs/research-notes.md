# Research notes

## What the archives establish

| Status | Evidence |
| --- | --- |
| Implemented | Seeded task scheduling and state snapshots in OrbitLab. Context-dependent parameter selection and policy combinations. Variant generation, mutation and staged validation in Beast Lab. Replay feature extraction and NumPy ranker training in V14. |
| Evaluated | The evolutionary log records 52 candidates across generations 0, 1 and 2 (16, 18 and 18), with 253 matches. Beast Lab records analysis of 312 historical replays, 16 Fast entries and four Full entries. V14 records historical training and a short self-play trial. |
| Positive observations | The research report records the competition placement. V14 produced learned weights and a recorded validation AUC of 0.886154. Several Beast Lab candidates had positive short-run signals. |
| Negative or inconclusive results | Twenty-two evolution records are errors or timeouts. Four Full results report negative combined deltas and the run promoted zero archives. There is no attested Holdout score. The V14 export chose coefficient 0.0 after recording only that coefficient in its short self-play comparison. |
| Unpromoted or superseded prototypes | The four Full candidates were unpromoted in the recovered Beast Lab run. Notebook v36b contains an unterminated replacement string and was superseded in the archive sequence by v36c. Neither source was run in Phase 2. The evidence shows this recorded outcome and leaves the status of other runs open. |
| External post-competition study | The V5 retrospective discusses action-space compression, the podium’s large-scale reinforcement learning, and the first-place Rust simulator. These are credited to their authors. [First-place write-up](https://www.kaggle.com/competitions/orbit-wars/writeups/1st-place-solution-scaling-reinforcement-learnin) |

The V14 validation split is sampled at example level by the retained trainer. Replay-level split independence and ranker transfer to the final ladder were not established. The archived self-play summary for coefficient 0.0 records one win and one loss. Its report gives 176 replays, 20,633 positive examples, 113,418 negative examples and 2,600 epochs. The validation metric is the historical implementation’s approximate AUC, with its own tie handling.

Beast Lab’s flags ending in `_ok` record whether the evaluation ran. Export gates additionally apply score, mode-floor and robustness thresholds. The archived run’s report formats missing Holdout values as zero. The exported table preserves the absence of those fields. The Phase 2 fixture demo exercises the Holdout gate with fresh test games and supplies no historical Holdout evidence.

## Additional OrbitLab match records identified in Phase 2

The Phase 1 inventory had indexed most of these files as replay JSON by name. Reading their schemas and statuses identifies them as local match outputs in the historical `orbit_lab/work/match_outputs` directory. The audit parsed 5,800 files with 5,800 unique content hashes and match IDs. Their file modification dates span 16–17 June 2026 UTC.

| Mode | Recorded OK | Recorded ERROR |
| --- | ---: | ---: |
| 2P | 1,535 | 2,635 |
| 3P | 0 | 11 |
| 4P | 427 | 1,192 |
| **Total** | **1,962** | **3,838** |

Every OK record carries the expected number of reward entries for its mode. Error records carry no rewards. There are no per-agent terminal statuses in this archive, and 340 OK records contain snapshots or actions. This establishes the number of attempts and the recorded outcomes. It leaves open the number of fully validated historical games, the number or length of overnight runs, and the completeness of the archive. The 253-row evolution log has a separate ID scheme. The audit found no shared IDs and reports the two sources separately without inferring a combined unique-game total.

The V5 report discusses overnight controllers and recovery on page 33. Four corresponding controller scripts are in the archive. All 36 generated candidate paths recorded by name in the evolution log resolve to files in the archived `generated_agents` directory. Those files were checked for presence only and remain outside the public tree. See the [aggregated OrbitLab records](../results/orbitlab_match_outputs.csv).

## Report identity

**Florent Schobyn, Orbit Wars Research Report, V5.1, 2026.** 90 pages. The report preserves the original date of 15 July 2026. See pages 45–46 for the rank and candidate archive name. Part III contains the retrospective.

```text
SHA-256
c8a70df4eada94f1b57e928ca8ed320c72cd75b54b3bf2fa7a135f18d0d1d7da
```

Read the [canonical research report](../Orbit_Wars_Research_Report.pdf) and the [retrospective and review](research_report/PUBLICATION_ASSESSMENT.md). The exact V5 source remains in the private archive and the historical tag.
