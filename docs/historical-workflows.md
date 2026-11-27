# Recovered historical workflows

The `orbit-history` command exposes the reviewed historical methods with explicit, bounded inputs. The original Phase 3 `orbit-research` commands remain available. Install with `python -m pip install ".[simulator,analysis,test]"` from the repository root.

## Replay failures to guided candidates

~~~text
orbit-history beast-guided configs/beast_replay_fixture.json --base configs/beast_fixture_agent.py --config configs/beast_validation_fixture.json --evaluate-all --out local-runs/guided
~~~

The supplied JSON is synthetic. The original Beast Lab code computes seat-zero snapshots and deltas, classifies failures and writes situation and timeline tables. The guidance functions load those tables, weight search families, build a small population and mutate the first candidate. The command applies one selected spec to a **local copy** of the base agent, checks that it changes source, loads the two trusted modules and passes the candidate to strict seeded Phase 3 validation. Population indices start at zero. Index `--population` selects the child.

Provide explicit unpacked Orbit Wars JSON files to analyze your own episodes. A terminal result with consistent rewards is required. The parser deduplicates identical playable content. The historical metric uses seat zero and the original checkpoint definitions. For charts, pass `--charts` and install the analysis extra.

The baseline must be a reviewed single Python file with typed parameters and, for contextual patching, `CONFIG_4P = dataclasses.replace(` on a multiline block. Run local code only if you trust its effects. If the selected variant changes no recognized parameter, the command stops. The supplied example plays ten games across Fast, Anti-Mirage, Full and Holdout using the same opponent. Neither its decisions nor its match scores are historical results.

Use `orbit-research import-agent` to register additional local opponents and pass that `--registry` to `orbit-history beast-guided`. Set stages’ opponent IDs and independent seed blocks in the configuration. Leave off `--evaluate-all` to gate later stages on earlier results. Recovered historical gates are preserved. A strong design freezes a separate Holdout pool before tuning.

## Intelligent Evolution V6

~~~text
orbit-history intelligent-v6 hold nearest --workers 2 --max-games 16 --out local-runs/v6
~~~

The schedule seeds and shuffles a bracket, selects two finalists, creates situation-aware challengers and both two-parent combinations, and carries the next finalists forward. The final bracket compares the original population with the last four ranked candidates, deduplicating repeated names. Wins, rewards and exposure break ties in the original final ranking. Template adapters bind parents explicitly and isolate state per seat. For the original random mutation mode, the public adapter derives a stable seed from candidate identity instead of Python’s process-dependent string hash.

Choose `--variants` from `expand`, `defense`, `comeback`, `anti_leader`, `sniper`, `timing_wave`, `random_alpha` and `random_beta`. Roster IDs are `hold`, `nearest` or keys in a supplied local registry. `--generations`, `--best-of` and `--max-games` control the budget. The schedule checks a conservative upper limit before starting. The documented example attempts at most eight matches and illustrates the archived search structure on modern policies. The V6 brackets use 2P as in the inspected V6 source.

## OrbitLab scheduling, resumption and diagnostics

~~~text
orbit-history orbitlab hold nearest --workers 2 --out local-runs/orbitlab
orbit-history orbitlab-diagnose configs/beast_replay_fixture.json --every 20 --out local-runs/diagnostics
orbit-history package-agent configs/beast_fixture_agent.py --out local-runs/orbitlab/fixture.tar.gz
~~~

The 2P tournament uses the historical order and seat swaps. For 4P supply at least four distinct IDs and `--modes 4p` or `--modes 2p 4p`. Advance both advanced tournament commands by repeating the same command and output directory after an interruption, with the same seed, policy bytes and settings. Finished match attempts are loaded from atomic JSON records. Change the output directory for a new schedule. A recorded failed attempt remains visible. Use a fresh run to retry failures. Use one process per output directory. Process workers parallelize matches, and simulator limits do not sandbox or forcibly time-limit arbitrary Python imports.

Diagnostics use the historical OrbitLab snapshot and action parsers on validated local JSON. Output rows use seat aliases and a playable-content fingerprint. The packaging command copies one explicit Python source into a deterministic `main.py` tarball through static parsing, suitable for local research exchange when you hold the relevant rights. It performs neither dependency vendoring nor Kaggle submission.

[Coverage and source fingerprints](../HISTORICAL_COVERAGE.md) · [Recovered code](../orbit_wars_research/historical/workflows.py) · [Test record](../TEST_REPORT.md)

