# P11 · 05 · Run

Status: READY
Author: verifier
Reads: 02_plan.md (Run commands), 03_changes_*.md (CLI confirmed), 07_review.md (pre-run audit PASS, Round 2)
Branch / commit: `phase/P11-trial-leakage-fix` @ `aedf8a81c581eebc4273181e71fd795df3e5a8bd`. Every log header shows this HEAD and an empty `git status --porcelain`. `git diff --stat e86ae3f HEAD -- src scripts tests configs`: `scripts/diagnostics/demo_cv_leakage.py`, `scripts/evaluation/evaluate_confusion_matrix.py`, `src/models/classical/legacy_eval.py`, `tests/test_p11_cv.py`, `tests/test_p11_known_answer.py` (the audit's fix 1 and the N1/N2 wording only; 84 insertions, 2 deletions).
Machine: Linux 7.0.0-38-generic, 16 cores, CPU only (`--device cpu`), Python 3.12.3, torch 2.14.1+cu130 (project `.venv`).

## Commands executed

Pytest ran in a clean detached worktree of HEAD (`mas/state/scratch/verify_P11`, removed afterwards). The 11 run commands ran once each, sequentially, from the repository root (HEAD, clean tree), so outputs landed in the main `reports/`. One driver script (`mas/state/scratch/run_p11.sh`) wrote each log header (command, HEAD, porcelain status, start), the output, `EXIT <code>` and the end time. No command was repeated. Total wall time 11:02:19 to 11:49:50 (about 47.5 min, of which pytest 6.6 min), inside `LOCAL_RUN_BUDGET_MIN` 120.

| # | Command (`.venv/bin/python ...`) | Start (-06:00) | Runtime | Exit | Log (`reports/logs/P11/`) |
|---|---|---|---|---|---|
| 0 | `-m pytest tests -o addopts="" -q` (worktree) | 11:02:19 | 393.19 s | 0 (`678 passed, 21 warnings`) | `pytest_20261026_110219.log` |
| 1 | `-m scripts.benchmarks.feature_based.benchmark_n_subjects --cv legacy --smoothing mod5` | 11:08:55 | 15 s | 0 | `n_subjects_legacy_20261026_110855.log` |
| 2 | `...benchmark_cross_validation --subject S03 --cv legacy --smoothing mod5` | 11:09:10 | 15 s | 0 | `cross_validation_legacy_20261026_110910.log` |
| 3 | `...benchmark_feature_selection --subject S03 --k-features 20 --cv legacy --smoothing mod5` | 11:09:25 | 97 s | 0 | `feature_selection_legacy_20261026_110925.log` |
| 4 | `-m scripts.diagnostics.demo_cv_leakage` (demo 1) | 11:11:02 | 17 s | 0 | `demo1_20261026_111102.log` |
| 5 | `...benchmark_n_subjects` | 11:11:19 | 16 s | 0 | `n_subjects_20261026_111119.log` |
| 6 | `...benchmark_cross_validation --subject S03` | 11:11:35 | 17 s | 0 | `cross_validation_20261026_111135.log` |
| 7 | `...benchmark_feature_selection --subject S03 --k-features 20` | 11:11:52 | 97 s | 0 | `feature_selection_20261026_111152.log` |
| 8 | `-m scripts.benchmarks.neural_networks.benchmark_nn_augmentation --model eegnet --epochs 150 --device cpu` | 11:13:29 | 833 s | 0 | `ab_eegnet_20261026_111329.log` |
| 9 | same, `--model compact_cnn` | 11:27:22 | 668 s | 0 | `ab_compact_cnn_20261026_112722.log` |
| 10 | same, `--model shallow_conv_net` | 11:38:30 | 661 s | 0 | `ab_shallow_conv_net_20261026_113830.log` |
| 11 | `-m scripts.diagnostics.demo_cv_leakage` (demo 2) | 11:49:31 | 19 s | 0 | `demo2_20261026_114931.log` |

Runtimes are end minus start of the log header, rounded to seconds (A/B total 2162 s).

## Human run requests

None.

## Produced files

- Logs: the 12 files above in `reports/logs/P11/`.
- Legacy snapshot (step 0): `reports/legacy_leaky/n_subjects_benchmark.csv`, `reports/legacy_leaky/feature_space_benchmark_S03.csv`, `reports/legacy_leaky/feature_selection_ablation_S03.csv` (each with `.meta.txt`).
- Leak-free: `reports/n_subjects_benchmark.csv`, `reports/feature_space_benchmark_S03.csv`, `reports/feature_selection_ablation_S03.csv` (+`.meta.txt`), `reports/augmentation_ab_{eegnet,compact_cnn,shallow_conv_net}.csv` (+`.meta.txt`), `reports/cv_leakage_demo.csv` (+`.meta.txt`), `reports/cv_leakage_demo_networks.csv`.
- Note: `reports/augmentation_ab_*.csv` and `reports/feature_*_S03.csv` / `n_subjects_benchmark.csv` held earlier-phase content before the run and were overwritten by the project scripts. The frozen P10 files in `reports/legacy_leaky/augmentation_ab_*.csv` were not written by any command (hashes in 06_verify.md, P7).

## Anomalies

- No warning lines in any benchmark or demo log (`grep -ci warn`: 0). All 12 exits 0. Pytest: 21 warnings, as in 04_tests.md.
- Demo 1 printed three "network section: ... skipped (splitter labels: legacy_leaky file leaky, reports file leaky; need leaky and grouped)" lines, as the audit expected (`reports/logs/P11/demo1_20261026_111102.log` lines 22-24). The network table is read from demo 2.
- Window counts 200/196/197/197/200 clean, 0/3/3/1/0 rejected, 7 channels kept and none dropped for every subject, in `reports/n_subjects_benchmark.csv`; A/B CSVs `Clean Windows` the same.
- Acceptance outcome (misses of R-9b, see 06_verify.md P4) is not a run anomaly; no command failed.

## Round 2b (seed-spread diagnostic)

Branch / commit: `phase/P11-trial-leakage-fix` @ `0b96524e6afe59fd70f6a3941d61b57bcf660fe6` (clean porcelain in every log header). `git diff --stat aedf8a8 HEAD -- src scripts`: `scripts/diagnostics/network_seed_spread.py` (NEW, 154 insertions) and `src/models/cnn/eegnet_cv.py` (9 lines changed); nothing else. Same machine and Python as above (CPU only).

| # | Command (`.venv/bin/python ...`) | Start (-06:00) | Runtime | Exit | Log (`reports/logs/P11/`) |
|---|---|---|---|---|---|
| 0 | `-m pytest tests -o addopts="" -q` (clean worktree, removed afterwards) | 12:42:31 | 549.27 s | 0 (`687 passed, 21 warnings`) | `pytest_2b_20261026_124231.log` |
| 1 | `-m scripts.diagnostics.network_seed_spread --model eegnet --seed-bases 1042 2042 --epochs 150 --device cpu` | 12:51:43 | 1920 s | 0 | `seed_spread_eegnet_20261026_125143.log` |
| 2 | `-m scripts.diagnostics.network_seed_spread --model compact_cnn --seed-bases 1042 2042 --epochs 150 --device cpu` | 13:23:43 | 1163 s | 0 | `seed_spread_compact_cnn_20261026_132343.log` |

Each command ran once. Total about 61 min wall, inside `LOCAL_RUN_BUDGET_MIN` 120 (the 50 min estimate was low for EEGNet). Human run requests: none.

Produced: `reports/diagnostics/p11_seed_spread_eegnet.csv`, `reports/diagnostics/p11_seed_spread_compact_cnn.csv` (+ `.meta.txt`). Byte check: `sha256sum -c mas/state/scratch/pre2b.txt` (taken before the run) reports OK for all 28 files: `reports/augmentation_ab_*.csv`, `reports/legacy_leaky/*.csv`, `reports/n_subjects_benchmark.csv`, the legacy arrays. Anomalies: none (no failed command; the run wrote only under `reports/diagnostics/` and `reports/logs/`).
