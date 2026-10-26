# P12 · 05 · Run

Status: READY
Author: verifier
Reads: 02_plan.md (Run commands), 03_changes_connectivity-stats.md (CLI confirmed, Round 1 audit fixes), 07_review.md (pre-run audit PASS, Round 2)
Branch / commit: `phase/P12-coherence` @ `cb446b0b7a9ad50f7d4482eeb67619043dc5df0f`. Every log header shows this HEAD and an empty `git status --porcelain`.
Machine: Linux 7.0.0-38-generic, CPU only, Python 3.12.3 (project `.venv`).

## Commands executed

Pytest ran in a clean detached worktree of HEAD (`mas/state/scratch/verify_P12`). The three run commands ran once each, in order, from the repository root (HEAD, porcelain empty), so outputs landed in the main `reports/connectivity/` and `outputs/figures/connectivity/`. Driver: `mas/state/scratch/run_p12.sh` (log header, `tee`, `EXIT` line). No command was repeated. Total wall time under 12 min (pytest 6.0 min), inside `LOCAL_RUN_BUDGET_MIN`.

| # | Command (`.venv/bin/python ...`) | Start (-06:00) | Runtime | Exit | Log (`reports/logs/P12/`) |
|---|---|---|---|---|---|
| 0 | `-m pytest tests -o addopts="" -q` (worktree) | 15:11:09 | 362.42 s | 0 (`723 passed, 21 warnings`) | `pytest_20261026_151109.log` |
| 1 | `-m scripts.connectivity.diagnostics.demo_coherence_bias --subjects S03 S04` | 15:17:20 | 14 s | 0 | `demo_20261026_151720.log` |
| 2 | `-m scripts.connectivity.analysis.analyze_connectivity --subject S03 --method coherence` | 15:17:34 | 9 s | 0 | `analyze_S03_20261026_151734.log` |
| 3 | `-m scripts.connectivity.analysis.analyze_connectivity --subject S04 --method coherence` | 15:17:43 | 10 s | 0 | `analyze_S04_20261026_151743.log` |

## Human run requests

None.

## Produced files

- `reports/connectivity/coherence_bias_demo.csv`, `coherence_bias_demo_S03.csv`, `coherence_bias_demo_S04.csv` (+ `.meta.txt` each).
- `reports/connectivity/coherence_S03_matrices.npz`, `coherence_S03_summary.csv`, `coherence_S03_summary.meta.txt`; same for S04.
- `outputs/figures/connectivity/coherence_{S03,S04}_{raw,difference}_panel.png`.
- Logs: the 4 files above.
- Legacy arrays `data/processed/S0{3,4}/{X_time_windows,y_labels}.npy`: sha256 before and after in 06_verify.md (identical).

## Anomalies

None. All four exits 0; no warning lines in the three run logs; no channel dropped for either subject; the 'synthetic part in range: True' line is printed by the demo. Pytest: 21 warnings (same count as the handoffs).

## Questions
