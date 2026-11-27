# Reproduce and extend the research

## Install

Use Python 3.13 for the tested setup. From the repository root, create and activate a new virtual environment. On Windows PowerShell, run:

~~~powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements-win-py313.lock
python -m pip install -e ".[simulator,analysis,test]"
python -m pip check
~~~

On Linux or macOS use `source .venv/bin/activate` and install the extras without the Windows lock. The lock preserves the Phase 2 simulator environment and was used for the clean release run. Phase 3 pinned extras are specified by `pyproject.toml`. Python 3.13 Windows x64 was tested in a fresh local environment. The CI matrix proposes Windows and Linux checks. See [TEST_REPORT.md](../TEST_REPORT.md) for actual execution.

The core with just NumPy can run the ranker, manipulate variant specifications and parse replays. Install the simulator extra to run matches and the analysis extra to render figures and run notebooks.

## Bounded quickstart

Run from the repository root. Use fresh output paths for repeat runs.

~~~text
orbit-research tournament --config configs/tournament.json --out local-runs/tournament
orbit-research generate --agent nearest --seed 42 --count 2 --out local-runs/variants
orbit-research hybridize --two nearest --four hold --out local-runs/hybrid.json
orbit-research validate --config configs/quickstart.json --spec local-runs/hybrid.json --evaluate-all --out local-runs/validation
orbit-research search --config configs/quickstart.json --agent nearest --out local-runs/search
orbit-research train-ranker configs/ranker_fixture.csv --epochs 3 --seed 42 --out local-runs/ranker.json
orbit-research predict local-runs/ranker.json configs/ranker_fixture.csv --out local-runs/scores.csv
orbit-research plot-history
~~~

The tournament schedules four games with seat rotation across repeats. Validation schedules ten games across four stages. `--evaluate-all` exercises every stage even when the earlier candidate was rejected. The default stops at rejection and logs skipped stages. Use `--stage fast`, `--stage anti-mirage`, `--stage full`, or `--stage holdout` to run a specific stage. Search schedules eight Fast games across two generations and chooses among candidates with valid metrics. In search an eligible winner can become the next parent even when its Fast gate rejects it. That is an exploratory next-parent decision. It does not validate the candidate.

The quickstart uses shortened games and a shared opponent pool. A held-out seed block alone is insufficient to claim generalization. For a serious prospective evaluation, set distinct stage seed blocks and a separately selected Holdout opponent list under `stages.holdout.opponents`, then freeze them before selection. The manifest records shared pool detection at the reference level. Equivalent policies under different IDs still share behavior. Session budgets and results are recorded in the experiment directory. The example uses one game per mode per round, so seats are deliberately not balanced in these stage fixtures. Increase each mode to a multiple of its player count for balanced candidate-seat exposure, within the explicit budget.

~~~text
python -m pytest -q -p no:cacheprovider
~~~

The test fixture CSV contains synthetic feature rows. Its output illustrates the interface and is unrelated to the archival AUC.

## Register a local agent

~~~text
orbit-research import-agent ../my_local_agent.py --id local-policy --registry local-runs/agents.json
orbit-research validate --config configs/quickstart.json --agent local-policy --registry local-runs/agents.json --stage fast --out local-runs/local-fast
~~~

The registry references a local Python file providing `agent(observation)` or `agent(observation, configuration)`. Registration checks syntax and records SHA-256. When selected, match execution loads the pinned file contents and invokes the callable. It executes as your user inside the local Python process. Use sources you have reviewed and trust. Third-party dependency installation and package setup are the user's responsibility. This adapter targets single-file entry points with imports available in the environment. It writes no copy of the source, and manifests record hashes instead of paths. The registry itself contains private file paths. Keep it under an ignored output directory.

The supplied `hold` and `nearest` agents are original Phase 3 demonstration policies written here for this project. `hold` issues no launch. `nearest` selects a stocked planet and sends half its ships toward the closest non-owned planet. See the [provenance record](../PROVENANCE.md). Variant and router files contain settings and parent references only. The router binds once using the scheduled number of seats. It keeps its initial mode when players are eliminated.

The engine sets per-action and run time limits. The framework stays in-process and does not sandbox local Python. Deterministic built-ins provide seed regression checks. External agents can still introduce stochasticity or nonportable dependencies.

## Replay features and ranking

1. Acquire replay JSON you are authorized to use from the [competition](https://www.kaggle.com/competitions/orbit-wars/) or a clearly licensed release such as the [publisher's episodes collection](https://www.kaggle.com/competitions/orbit-wars/discussion/697413). Check the release terms and version before using downloaded data. These sources are examples of acquisition routes. The exact original V14 replay batch is unresolved.
2. Place unpacked JSON outside the tracked tree. The adapter expects `name=orbit_wars`, consistently sized `steps` with observations and actions, terminal DONE states and matching rewards. Incompatible versions will fail the format check.
3. Pass the selected JSON files explicitly. The V14 extractor uses identifiable launches by a unique winner as positives and plausible alternatives as negatives. Tied episodes may provide no rows.

~~~text
orbit-research extract-replays ../local-replays/match-a.json ../local-replays/match-b.json --out local-runs/replay_features.csv
orbit-research train-ranker local-runs/replay_features.csv --epochs 30 --seed 42 --out local-runs/local-ranker.json
orbit-research predict local-runs/local-ranker.json local-runs/replay_features.csv --out local-runs/replay-scores.csv
~~~

Training needs both classes in each split, enough replay groups, and finite numeric features. The trainer allocates complete replay groups, computes scaling from training rows, and reports tie-aware validation ROC AUC. Extraction uses a content fingerprint of playable steps and rewards as the group ID and deduplicates exact playable-content copies even if filenames or top-level metadata differ. Near-duplicate replays are a separate issue. For third-party feature CSVs the investigator must provide trustworthy group identifiers. The default split requires at least two usable replay groups. Real research should use separately obtained held-out episodes. Models are plain JSON, and scores are sigmoid-transformed linear scores in input row order. Validation performance is diagnostic and is not a strategic win-rate estimate.

## Analyze the archive

Open the four notebooks from the repository or its notebook directory using a Python kernel with the analysis extra. Start with [notebook 1](../notebooks/01_competition_and_historical_results.ipynb), then [lineage](../notebooks/02_agent_evolution_and_lineage.ipynb), [validation](../notebooks/03_multistage_validation_and_failures.ipynb), and [replay learning](../notebooks/04_replay_learning_and_ranker_limits.ipynb). Each figure reads a bundled historical table. Use the [data dictionary](../DATA_DICTIONARY.md) for joins and missing values.

Regenerate the release architecture and V14 plot with `python assets/render_figures.py` after installing the analysis extra. The architecture is conceptual, and the V14 curve reads recorded checkpoints. Open the [asset index](../assets/README.md) for the sources.

## Use the recovered historical workflows

The installation provides a separate `orbit-history` command. Follow the [advanced guide](historical-workflows.md) for failure-guided Beast Lab, V6 finalist brackets, OrbitLab scheduling, resumption and local diagnostics, and deterministic packaging. These workflows use bundled fixtures or explicitly supplied authorized inputs. The [coverage matrix](../HISTORICAL_COVERAGE.md) describes their origin and adaptations.

## Regenerate the V5.1 report

The optional report builder uses the exact V5 and fingerprinted tables. Create `local-runs` before running the commands.

~~~text
python -m pip install "matplotlib==3.10.8" "PyMuPDF==2.2"
python docs/research_report/build_v51.py --out local-runs/orbit-wars-v5.1.pdf
~~~

See the [edition assessment](research_report/PUBLICATION_ASSESSMENT.md) for the precise changes and figure sources.
