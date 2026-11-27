# Test report

## v0.3.1 recovery and V5.1 verification

Local verification used Windows x64, CPython 3.13.9, Kaggle Environments 1.30.2 and Matplotlib 3.10.8. The report builder used PyMuPDF 2.2. **28 tests passed** (22 existing and six focused recovery tests). The new tests cover replay failure and guidance, bracket lineage and original template binding, resume and terminal evidence, local diagnostics and non-executing archive creation.

~~~text
python -m pip install -e ".[simulator,analysis,test]"
python -m pytest -q -p no:cacheprovider
orbit-history beast-guided configs/beast_replay_fixture.json --base configs/beast_fixture_agent.py --config configs/beast_validation_fixture.json --evaluate-all --out local-runs/guided
orbit-history intelligent-v6 hold nearest --workers 2 --out local-runs/v6
orbit-history orbitlab hold nearest --workers 2 --out local-runs/orbitlab
orbit-history orbitlab-diagnose configs/beast_replay_fixture.json --out local-runs/diagnostics
orbit-history package-agent configs/beast_fixture_agent.py --out local-runs/orbitlab/fixture.tar.gz
python docs/research_report/build_v51.py --out local-runs/orbit-wars-v5.1.pdf
~~~

The guided run completed ten attempts across four stages using synthetic inputs. Forced evaluation exercised the gates, independently of whether the candidate passed them. The V6 example completed seven matches from its eight-game limit. OrbitLab completed two seat-swapped matches and reused both completed records on a second run. The synthetic replay yielded four OrbitLab snapshot rows. These runs verify the interfaces and provide no historical campaign evidence.

The PDF audit compared text and pixel digests for all 79 unchanged body pages. It checked the first-page text difference, 10 appendix figures, retained outline and link counts, and exact original V5 SHA-256. The appendix charts read the same fingerprinted evidence files as the original candidate. The dated [edition assessment](docs/research_report/PUBLICATION_ASSESSMENT.md) records the changes and final PDF fingerprint.

The earlier private v0.3.0 GitHub Actions runs passed on both Windows and Linux with 22 tests and four 2P/4P tournament matches on each platform and ref. The v0.3.1 workflow exercises the new tests and advanced commands in both jobs. [v0.3.0 main run](https://github.com/informabook/orbit-wars-ai/actions/runs/45991758201) · [v0.3.0 tag run](https://github.com/informabook/orbit-wars-ai/actions/runs/45992245556) · [Release CI](https://github.com/informabook/orbit-wars-ai/actions)

## v0.3.0 clean release verification

Verified on 27 November 2026 using Windows x64 (build 26300), CPython 3.13.9 and pip 25.2. The fresh environment used Kaggle Environments 1.30.2, NumPy 2.2.6, Matplotlib 3.10.8, pytest 8.4.2, nbclient 0.10.2, ipykernel 7.1.0, setuptools 80.9.0 and wheel 0.45.1. Imports and tests outside the checkout used the non-editable install from the built wheel. The wheel metadata reports version 0.3.0 and license expression MIT.

### Environment and wheel commands

The following commands use paths relative to the workspace. The release source is under `outputs/orbit-wars-ai`. The test environments, local inputs and run outputs stay under the scratch directory `work`.

~~~powershell
python -m venv work/release-v030-venv
$py = "work/release-v030-venv/Scripts/python.exe"
& $py -m pip --isolated install --no-input --no-compile --index-url https://pypi.org/simple -r outputs/orbit-wars-ai/requirements-win-py313.lock pytest==8.4.2 setuptools==80.9.0 wheel==0.45.1 nbclient==0.10.2 ipykernel==7.1.0
& $py -m pip wheel --no-deps --no-build-isolation outputs/orbit-wars-ai --wheel-dir work/final-wheels
& $py -m pip install --no-deps --no-compile work/final-wheels/orbit_wars_research-0.3.0-py3-none-any.whl
& $py -m pip check
$env:PYTHONDONTWRITEBYTECODE = "1"
$env:LITELLM_LOCAL_MODEL_COST_MAP = "True"
$env:HF_HUB_OFFLINE = "1"
$env:TRANSFORMERS_OFFLINE = "1"
Push-Location work
.\release-v030-venv\Scripts\python.exe -m pytest -q -p no:cacheprovider --import-mode=importlib ../outputs/orbit-wars-ai/tests
Pop-Location
~~~

Package installation and dependency checks succeeded. **22 pytest tests passed in 135.76 seconds**, including the simulator test for two- and four-seat runs and applied-seed checks. The earlier independent Phase 3 review reported 21 passes and one simulator skip. The two reports used different environments.

### CLI and notebook commands

`orbit-research` below refers to the console script installed next to the verified Python executable. The three replay JSON files were tiny synthetic inputs made for the audit. They follow the replay schema in `test_historical_replay_features_are_grouped_by_playable_content`, with one duplicate and one distinct set of planet ships. The temporary local agent provides `agent(observation)` returning an empty list. Its registration was exercised by the CLI, and invocation and fingerprint enforcement were exercised by pytest.

~~~text
orbit-research --help
orbit-research import-agent work/final-smoke/owned_agent.py --id fixture-agent --registry work/final-smoke/agents.json
orbit-research extract-replays work/final-smoke/replay-1.json work/final-smoke/replay-2.json work/final-smoke/replay-3.json --out work/final-smoke/features.csv
orbit-research generate --agent nearest --seed 42 --count 2 --out work/final-smoke/variants
orbit-research hybridize --two nearest --four hold --out work/final-smoke/hybrid.json
orbit-research train-ranker outputs/orbit-wars-ai/configs/ranker_fixture.csv --epochs 3 --seed 42 --out work/final-smoke/ranker.json
orbit-research predict work/final-smoke/ranker.json outputs/orbit-wars-ai/configs/ranker_fixture.csv --out work/final-smoke/scores.csv
orbit-research plot-history --root work/final-plot
python outputs/orbit-wars-ai/assets/render_figures.py --out work/final-plot/assets
orbit-research tournament --config outputs/orbit-wars-ai/configs/tournament.json --out work/final-smoke/tournament
orbit-research validate --config outputs/orbit-wars-ai/configs/quickstart.json --spec work/final-smoke/hybrid.json --evaluate-all --out work/final-smoke/validation
orbit-research search --config outputs/orbit-wars-ai/configs/quickstart.json --agent nearest --out work/final-smoke/search
python -m ipykernel install --prefix work/release-v030-venv --name orbit-release
~~~

| Check | Observed result |
| --- | --- |
| Registration, extraction and generation | Registered the project-owned fixture by hash, extracted four feature rows in two replay groups after deduplicating one input, generated two variants and wrote the 2P/4P router. |
| Ranker and predictions | Trained the JSON model for three epochs using the bundled synthetic feature fixture and generated eight predictions. The historic V14 training corpus was not used. |
| 2P and 4P tournament | Four attempts with valid terminal results, two in each mode. |
| Staged validation | Ten attempts with valid terminal results. The fixture gates reported Fast REJECT, Anti-Mirage REJECT, Full PASS and Holdout REJECT. Running all stages after rejection exercises the CLI under a fixed budget. The fixture shares an opponent pool and is unrelated to historical Holdout evidence. |
| Evolutionary search | Eight attempts with valid terminal results across two Fast generations. |
| Notebooks | All four passed validation and executed in-memory via `nbclient.NotebookClient(notebook, timeout=120, kernel_name="orbit-release").execute(cwd=notebooks_folder)`. Five PNG outputs were rendered across the notebooks, distributed 1, 2, 1 and 1. The published notebooks retain empty outputs. |
| Figure regeneration | The archived evaluation figure regenerated byte-for-byte from a scratch copy of `evolution_matches.csv` and `beast_full.csv`. Both diagram formats and the V14 plot also reproduced byte-for-byte with Matplotlib 3.10.8 on this host. |
| Release files | Eight manifest entries matched row counts and SHA-256. Phase 3 research code, fixtures, tests, notebooks and table bytes matched the prior ZIP. Python and notebook cell syntax, internal file links, configuration and artifact metadata were checked. The final ZIP was extracted into a temporary Git repository and the staged contents were compared byte-for-byte to the intended release files. |
| GitHub Actions | The workflow YAML parsed with the expected push, pull request and manual triggers, repository read permission and Windows/Linux matrix. GitHub Actions, Linux and macOS were not run in this audit. |

Kaggle Environments logged OpenSpiel warnings for unavailable poker games and LiteLLM pricing notices during import. Jupyter logged a Windows ZMQ selector fallback warning. Orbit Wars tests and notebooks completed with those diagnostics. Only bundled code, original release graphics and scratch fixtures were run. The original candidate archive and historical serialized models were excluded from execution.



## Phase 3 tested environment

Windows x64, CPython 3.13.9. Kaggle Environments 1.30.2, NumPy 2.2.6 and Matplotlib 3.10.8. Installed the Phase 3 extras in the existing isolated Phase 2 environment. Pytest 8.4.2, nbclient 0.10.2 and ipykernel 7.1.0 were used. Linux and macOS have no observed Phase 3 result here. The Windows/Linux GitHub Actions matrix is prepared for use after publication.

### Commands executed locally

With the isolated interpreter active, from the repository root. The relative output locations below are the local scratch directories used in the checks.

~~~text
python -m pip --isolated install --index-url https://pypi.org/simple pytest==8.4.2 setuptools==80.9.0 wheel==0.45.1 nbclient==0.10.2 ipykernel==7.1.0
python -m pip install --no-build-isolation --no-deps -e .
python -m pip check
python -m pytest -q -p no:cacheprovider -m "not simulator"
python -m pytest -q -p no:cacheprovider
orbit-research tournament --config configs/tournament.json --out ../../work/p3-tournament
orbit-research generate --agent nearest --seed 42 --count 2 --out ../../work/p3-variants
orbit-research hybridize --two nearest --four hold --out ../../work/p3-hybrid.json
orbit-research validate --config configs/quickstart.json --spec ../../work/p3-hybrid.json --evaluate-all --out ../../work/p3-validation
orbit-research search --config configs/quickstart.json --agent nearest --out ../../work/p3-search
orbit-research train-ranker configs/ranker_fixture.csv --epochs 3 --seed 42 --out ../../work/p3-ranker.json
orbit-research predict ../../work/p3-ranker.json configs/ranker_fixture.csv --out ../../work/p3-scores.csv
orbit-research plot-history --root ../../work/p3-plot
python -m ipykernel install --prefix ../../work/orbit-wars-venv --name orbit-phase3
~~~

From the workspace root, `python -m pip wheel --no-deps --no-build-isolation outputs/orbit-wars-ai --wheel-dir work/phase3-wheels` built the version 0.3.0 wheel.

Each notebook passed nbformat validation and execution via `nbclient.NotebookClient` in the installed `orbit-phase3` kernel, with its working directory set to `notebooks/`. The check required at least one rendered PNG and no error outputs in each executed copy. The bundled notebooks remain output-free. The plot command used a scratch copy of the two required CSVs.

### Results

| Check | Observed result |
| --- | --- |
| Dependency and installation checks | Editable install worked, exposed the console script, and passed pip check. |
| Pytest | 22 passed with the simulator enabled. Coverage includes strict terminal states and rewards, rejection without an applied seed, no unseeded retry, seed repeatability and board invariants for 2P/4P, stage seed independence, stopped gates, local source registration and hash pinning, deterministic variants, context selection, tie-aware AUC, grouped splits and replay fixtures. |
| Tournament | Four games finished OK, two in each mode, under seeds 42–45. |
| Validation | Ten games finished OK. The demo hybrid was rejected by Fast, Anti-Mirage and Holdout thresholds and passed the Full threshold in an explicit evaluate-all run. The small fixture shares an opponent pool across stages and is a functional check. |
| Search | Two generations, two variants each, eight Fast-stage games finished OK. Each generation recorded a next parent and retained candidate decisions. |
| Replay features | The pytest fixture generated two rows in the 106-feature V14 order. Repeated playable content produced one group despite changed metadata. No raw competition corpus was used. |
| Ranker CLI | Three training epochs with four synthetic replay groups, three for training and one for validation. Prediction wrote eight row-aligned scores. |
| Four notebooks and historical figure | All notebooks executed and rendered in the local kernel. The regenerated figure had the same SHA-256 as the existing figure. |
| Historical evidence | Phase 2 code and result hashes preserved. Phase 3 projections reconcile with their manifest, including all 5,800 OrbitLab outputs, 312 replay summaries and 131 V14 checkpoints. |

The initial feature-only extraction check found a missing `FEATURES` import. Reusing the retained V14 feature order fixed it before the test runs. The simulator emitted package-level LiteLLM and optional OpenSpiel warnings during startup. The full test and CLI runs still reached their recorded outcomes. Windows Jupyter emitted a selector-loop compatibility warning and all notebooks completed.

These are Phase 3 workflow tests. The historical Kaggle submission, exact original V14 training inputs and original Holdout performance remain outside the verified runtime scope.

## Phase 2 verification record


**Platform** Windows x64, CPython 3.13.9. The smoke test is separate from the archived competition runs. Historical measurements are checked by reading the selected tables and retain their original scope.

### Commands

From the repository root, with the isolated environment activated:

```text
python -m pip install -r requirements-win-py313.lock
python -m pip check
python -B -m orbit_wars_research.smoke
python -B -m orbit_wars_research.plot_results
```

The initial resolver used the binary-only option. Gymnax requires Gym 0.26 and the Windows resolver found no published Gym wheel. The retry allowed the Gym source distribution and used pinned top-level packages. A smoke invocation made before the Kaggle package had finished installing returned `ModuleNotFoundError`. The full run uses the resolved environment after installation. The historical source excerpts initially omitted the module import for `@dataclasses.dataclass`. The import was restored and the experiment functions were left intact.

The primary setup pins `kaggle-environments==1.30.2`, `numpy==2.2.6` and `matplotlib==3.10.8`. The Windows lock records the complete isolated environment, including the compatible historical utilities pandas 2.3.3, nbformat 5.10.4 and requests 2.32.5. Other Python platforms and the original Kaggle image remain unverified.

### Boundaries and verified inputs

The fixture harness uses Kaggle’s built-in random agent and generated local test fixtures for the small runtime checks. The generated historical templates are compiled from their sources. Historical candidate archives, output cells, submitted agent bundles, replay data and serialized policy weights stay outside the runtime. The NumPy trainer uses a 128-row synthetic fixture and a two-epoch cap instead of the original training budget. The Holdout gate fixture only checks code behavior.

The retained result files reconcile 52 candidates, 253 matches with 22 errors or timeouts, 312 replay analyses, 16 Fast and four Full rows, and the reported V14 sample count and AUC with an export coefficient of 0.0. The historical evidence supports zero validated exports and leaves the historical Holdout outcome unobserved.


### Observed results

The full command exited with code 0. The environment passed `pip check` and the resolved Windows lock pins 151 packages. The test used Kaggle Environments 1.30.2 and NumPy 2.2.6. The simulator’s package initialization logged optional OpenSpiel poker registration errors and LiteLLM pricing warnings. The Orbit Wars registry entry initialized and both game modes completed.

| Check | Observed result |
| --- | --- |
| Imports and engine | The four historical modules loaded. Kaggle registered `orbit_wars`. |
| 2P simulator | Seed 42, 32 recorded steps and both agents `DONE`. |
| 4P simulator | Seed 42, 32 recorded steps and all four agents `DONE`. |
| OrbitLab tournament | Two 2P fixture games with swapped seats, seeds 1716087199 and 542730242. Both produced action summaries, reward arrays and 42 snapshot rows. |
| Generation and mode selection | One Beast Lab mutation with a parent and child ID. Global and 4P patch functions updated fixture parameter text. Three historical wrapper templates compiled. Independent fixture rows were selected for 2P and 4P. |
| Beast Lab import and package shape | A controlled agent imported. An incomplete submission directory was rejected for missing `orbit_lite`. |
| Fast, Full and Holdout | Each stage evaluated one 2P and one 4P fixture game. They returned correctly shaped metrics and rejected the unfavorable candidate. Error states were also rejected. |
| Anti-Mirage | Two rounds, twelve fixture games in total, with a recorded rejection. An empty set of rounds was rejected by the gate. |
| V14 trainer | 128 synthetic examples with 106 features, two-epoch budget and finite weights. |
| Historical evidence | All summary counts reconciled. Independent Phase 2 audit found 5,800 additional OrbitLab match outputs, 1,962 marked OK and 3,838 marked ERROR. |
| Figure | Matplotlib regenerated the chart from the two historical data tables. |
| Public selection | Syntax, internal documentation links, CSV structure and path/secret-pattern checks passed. The exclusions register reconciled with all 21,499 file and archive-member entries from Phase 1. |

The 22 fixture games comprise two simulator checks, two tournament games and 18 Beast Lab evaluation games. The historical templates were compiled without importing the original opponents. The historical 2P/4P hybrid, candidate submission archive, replay-feature construction over the private corpus, full V14 retraining and Kaggle leaderboard reproduction remain outside the verified scope.
