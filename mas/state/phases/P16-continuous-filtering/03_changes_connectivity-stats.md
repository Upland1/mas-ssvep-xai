# P16 · 03 · Changes — connectivity-stats

Status: READY
Author: connectivity-stats
Reads: 00_assignment.md, 02_plan.md (row order 2, settled points 3, 4, 5, 10), 03_changes_data-signal.md, mas/RULES.md
Branch: phase/P16-continuous-filtering
Commit(s): 9c9148c (cohort + single-subject + loader), 0093234 (pairwise, comparison, power-confound), 74ccc1f (tests), plus the handoff commit

## Questions

ACK 02_plan.md connectivity-stats 2026-10-27

## Files

| Path | NEW / MODIFIED | Summary | Roadmap task | Source |
|---|---|---|---|---|
| `src/features/connectivity/connectivity_extraction.py` | MODIFIED | + `load_condition_windows` (101-105 and 201 through `load_subject`; clean windows, aligned true/legacy ids, kept channels, counts, fs and fs_source, identity `quality` dict for `extract_connectivity_by_condition`), `source_text`, `CONNECTIVITY_CONDITIONS`; `meta_lines` labels fs 256 as the true rate. The pre-P16 `load_legacy_selection`, `gate_selection`, `load_gated_conditions` are untouched (frozen reference of the regression test) | P16.7 | R3, R5, R8, PF-03 |
| `scripts/connectivity/analysis/analyze_connectivity_cohort.py` | MODIFIED | `load_condition_windows`; `--fs` default None (folder's fs), `--quality {shared,shared-no-guard,per-script}`; built roots accepted; real fs from meta, true ids in trial-level permutations, shared mask and kept channels; banner and `source` column say the build; legacy defaults print and write the same as before | P16.7 | R4, R5, R7 |
| `scripts/connectivity/analysis/analyze_connectivity.py` | MODIFIED | same loader and flags; `--out-suffix` (names get `_<suffix>`); meta text says the build for built folders, legacy text unchanged | P16.7 | R5 |
| `scripts/connectivity/comparison/test_connectivity_frequency_differences.py` | MODIFIED | `load_subject_groups` through the loader, per-subject fs into reliability and pair jobs, `--quality`, `--fs` default None | P16.7 | R4, R7 |
| `scripts/connectivity/comparison/compare_connectivity_frequencies.py` | MODIFIED | `--out-suffix` on every CSV/figure (reads any `--edges-dir`); responders still from the classifier benchmark only (PF-21) | P16.7 | R7 |
| `scripts/connectivity/diagnostics/check_power_alpha_confound.py` | MODIFIED | loader, `--quality`, `--fs` default None, `--out-suffix` (also reads `<m>_global_delta_<suffix>.csv`) | P16.7 | R5 |
| `tests/test_p16_connectivity_port.py` | NEW | 10 tests (below) | P16.7 | own |
| `tests/test_p14_known_answer.py` | MODIFIED | the power-confound row test patches `load_condition_windows` (new signature) | P16.7 | own |

## Legacy behaviour implemented

Era C requires none. The legacy root `data/processed` stays reachable and is the default: fs 250 (`legacy-assumed`), reconstructed ids (approximate flag from the full pre-gate labels, as before), per-script P07 gate (every `--quality` means it on a legacy folder). `--fs 250/256` overrides the axis (row a′). The frozen pre-P16 loaders remain in `connectivity_extraction.py` as the regression reference.

## Output names for the v1/v2 table (read by `compare_v1_v2.py`)

Cohort summary `reports/connectivity_cohort_summary_<suffix>.csv` (+ `_details.csv`, `connectivity_edges_<suffix>/`, `connectivity_alpha_diagnostic_<suffix>.csv`). Suffixes: `v1check` (legacy, regression), `v2pw` (per_window build, row b), `v2cont` (continuous, row c), `v2cont_noguard` (continuous, `--quality shared-no-guard`, row c').

Finding: the connectivity scripts read the broadband windows `X_time_windows`, which are filtered continuously (1-90 Hz + notch) in both build modes; the per_window / continuous difference is only in the saved sub-bands that connectivity does not use. On S03 the `v2pw` and `v2cont` summaries are identical in every printed count (below), so (c) - (b) = 0 for connectivity by construction; only the guard (c - c') and the fs / channels / filter step (a to b) can move it. The table should state this rather than present (c) - (b) as an effect.

## How to run / reproduce (verifier)

Builds come from the data-signal commands (`data/processed_per_window/`, `data/processed_continuous/`). Roots below use the default build location of `build_windows.py`; adjust if the verifier built elsewhere.

```bash
# regression (settled point 4): compare to the frozen v1 reports/connectivity_cohort_summary*.csv byte for byte
.venv/bin/python -m scripts.connectivity.analysis.analyze_connectivity_cohort --methods coherence plv wpli pdc --permutations 200 --permutation-unit trial --n-jobs -1 --out-suffix v1check
# rows b, c, c'
.venv/bin/python -m scripts.connectivity.analysis.analyze_connectivity_cohort --data-root data/processed_per_window --methods coherence plv wpli pdc --permutations 200 --permutation-unit trial --n-jobs -1 --out-suffix v2pw
.venv/bin/python -m scripts.connectivity.analysis.analyze_connectivity_cohort --data-root data/processed_continuous --methods coherence plv wpli pdc --permutations 200 --permutation-unit trial --n-jobs -1 --out-suffix v2cont
.venv/bin/python -m scripts.connectivity.analysis.analyze_connectivity_cohort --data-root data/processed_continuous --quality shared-no-guard --methods coherence plv wpli pdc --permutations 200 --permutation-unit trial --n-jobs -1 --out-suffix v2cont_noguard
# optional downstream on one build (frequency comparison, power confound, pairwise tests), e.g. v2cont
.venv/bin/python -m scripts.connectivity.comparison.compare_connectivity_frequencies --edges-dir reports/connectivity_edges_v2cont --out-suffix v2cont --no-figures
.venv/bin/python -m scripts.connectivity.diagnostics.check_power_alpha_confound --data-root data/processed_continuous --out-suffix v2cont --no-figures
.venv/bin/python -m scripts.connectivity.comparison.test_connectivity_frequency_differences --data-root data/processed_continuous --out-suffix v2cont
```
Row (a) is the frozen v1 `reports/connectivity_cohort_summary.csv`. Expected runtime on this machine, five subjects: about 82.6 s per subject for the four methods at 200 trial-level permutations (n_jobs -1), so about 7 min per cohort run and about 28 min for the four runs; the downstream scripts are short (comparison 4.5 s, power confound 1.8 s, pairwise at 100 permutations about 96 s for one subject; the default 1000 permutations is about 10x that per subject, optional). The verifier's `_v1check` comparison: `diff reports/connectivity_cohort_summary.csv reports/connectivity_cohort_summary_v1check.csv` (and `_details.csv`) must be empty.

## How I verified

Tests (`tests/test_p16_connectivity_port.py`, 10 tests, 134 s alone):
- `test_legacy_loader_equals_pre_port_loader` (2 cases, with and without a short block so the ids are approximate): windows (value and dtype), y, ids, channels, counts, approximate flag, fs 250 equal the frozen `load_gated_conditions` / `load_legacy_selection`.
- `test_legacy_cohort_equals_pre_port_flow` (trial and window unit): the ported `run_cohort` equals the frozen flow (`load_legacy_selection` + `gate_selection` + `extract_connectivity_by_condition` with fs 250) exactly on `obs_diff`, `p_one_tailed`, FDR counts, window counts, `source`, approximate flag and dropped channel.
- `test_legacy_single_subject_and_other_scripts_equal_pre_port`: `analyze_connectivity` CSV equals `summary_rows` of the old loader; power-confound SNR and the pairwise loader equal the old arrays; legacy meta text unchanged.
- `test_legacy_fs_override_changes_only_the_axis`.
- Known answer on a synthetic built folder (`p16_synth.write_built_subject`, 20 trials, a tone common to all channels in the stimulus window = coupled pair at f_c, independent noise at baseline; PO8 noisy, spike in trial 0): fs 256 reaches the estimator (`a[2] == 256`, details fs 256), `trial_ids` passed to the permutations equal the loader's true ids (4 distinct trials per class, none shared with 201), window counts per cell equal the shared mask of `load_subject`, PO8 dropped (7 channels), coherence `obs_diff > 0.5` and global p <= 0.1 in all five conditions; `shared-no-guard` keeps at least as many windows; `--fs 250` marks the source `override`; single-subject script on the built folder; downstream scripts with `--out-suffix` write only suffixed files and use the build's fs (256) and channels (O1;Oz;O2).
- Fails on the historical behaviour: the ids assertion fails if the permutations get reconstructed or unmasked ids instead of the loader's true ones (PF-03), the fs assertions fail with the 250 literal (PF-04), the per-cell window counts fail with the per-script gate instead of the shared mask (R5), and the legacy-equality tests fail if the port alters one v1 number (settled point 4).
- Existing suites touched: `pytest tests/test_p13_connectivity.py tests/test_p14_known_answer.py tests/test_p14_connectivity_comparison.py tests/test_p12_known_answer.py` 131 passed (59.6 s).
- Full suite: `pytest tests -q -o addopts=""` at 74ccc1f plus the ml-engineer's uncommitted working-tree edits: 3 failed, 1032 passed in 1144.49 s (log `mas/state/scratch/p16_suite_cs.txt`, machine shared with a second suite). The 3 failures are all in the ml-engineer's area and none touches connectivity: `tests/test_p05_feature_benchmark.py::test_qda_rank_failure_is_caught_and_other_models_survive`, `tests/test_p07_ml_engineer.py::test_n_subjects_schema_channels_and_parallel_equals_serial`, `tests/test_p11_cv.py::test_defaults_are_grouped_cv_and_mod5_smoothing_and_demo_delta_uses_reported_rule` (the first raises the new `oof_space needs explicit splits` error of P11 N1, so those tests still call `oof_space(splits=None)`). All connectivity tests (p12, p13, p14, p16 port) pass in that run.

Real-data smoke (project scripts, outputs in `mas/state/scratch/p16_cs/`, deleted afterwards; nothing written to `data/processed*`, `reports`, `outputs`, `baselines`; the one-subject builds went to scratch with `--out-root`):

| Run | Command (abridged) | Result |
|---|---|---|
| S01 legacy, `v1check`, 4 methods, 200 trial permutations | `analyze_connectivity_cohort --subjects S01 ... --out-suffix v1check --reports-dir mas/state/scratch/p16_cs/new` | 82.6 s (wall 1 m 24.7 s). `connectivity_cohort_summary_v1check.csv`, `_details.csv`, `connectivity_alpha_diagnostic_v1check.csv` and the four `connectivity_edges_v1check/S01_<m>.npz` are equal to the S01 rows of the P13 final `reports/connectivity_cohort_summary.csv`, `_details.csv`, `connectivity_alpha_diagnostic.csv`, `connectivity_edges/` (20 rows, `assert_frame_equal(check_exact=True)`, arrays `array_equal`): 0 differences |
| S03 per_window build, `v2pw` | `--data-root mas/state/scratch/p16_cs/built_per_window --subjects S03 --out-suffix v2pw` | 90.0 s; fs 256 (meta), PO7 dropped, clean 271/280; FDR edges coherence 62, plv 32, wpli 44, pdc 23 |
| S03 continuous build, `v2cont` | same with `built_continuous` | 99.2 s; clean 271/280; identical counts to `v2pw` (see Finding) |
| S03 continuous, `v2cont_noguard` | `--quality shared-no-guard` | 90.6 s; clean 274/280; wpli 43 (others unchanged); window counts 784 vs 776 summed over methods x conditions |
| S03 downstream on `v2cont` | `compare_connectivity_frequencies`, `check_power_alpha_confound`, `test_connectivity_frequency_differences --permutations 100` | 4.5 s, 1.8 s, 95.9 s; suffixed files only |

Numbers are the console output of those runs (the logs were in the deleted scratch folder; the verifier regenerates them).

## Deviations / notes

1. The pre-port `load_gated_conditions` was not rewritten: new callers use `load_condition_windows`; the old functions stay as the frozen reference (and are still used by P12/P13 tests). The one existing test that monkeypatched the loader (`test_p14_known_answer`) was updated for the new name.
2. `--out-suffix` was added to the comparison, power-confound and single-subject scripts (they had no suffix); with it empty the file names are unchanged.
3. `compare_connectivity_frequencies` needs no loader (edge files only); its edge-file source label is generic when a suffix is used. Responders still come from `reports/n_subjects_benchmark.csv` or `--responders` (classifier accuracy only).
4. A pre-port script was not executed side by side (the hook allows only `python -m scripts...` runs); the regression is against the frozen P13 CSVs/npz (settled point 4) and, in the tests, against the frozen pre-port loader flow.
5. `fs` of the details CSV: legacy default 250.0, built 256.0; `source` carries the build, fs origin and quality mode for built folders.

## Reference consultations (R11)

None. `reference/ssvep-eeg-xai/` was not opened.

| # | Trigger | Files and lines @ commit | What I learned | What changed in my code |
|---|---|---|---|---|
| - | - | - | - | - |

## Sources

1. `mas/state/phases/P16-continuous-filtering/02_plan.md`, `03_changes_data-signal.md`, `mas/RULES.md` (opened in this run).
2. Project code read in this run: `src/io/subject_data.py`, `src/features/connectivity/*`, `tests/p16_synth.py`, the five connectivity scripts.

## Round 1 fixes

- Fix 2 (R5): `load_condition_windows` now passes `thresholds` (vpp 5-120 uV, std 1-35 uV) and `channel_fail_fraction` (0.5) explicitly, taken from the P13 `GATE` constant, to `load_subject`; every connectivity script goes through it. Legacy outputs are unchanged (same values as before; the four-way equality tests of `tests/test_p16_connectivity_port.py` pass again).
- Fix 3: row a' is `analyze_connectivity_cohort ... --fs 256 --out-suffix v1fs256` on the legacy root. New test `test_legacy_cohort_fs256_flag_changes_only_the_axis`: windows, ids, gate and permutation counts equal the `v1check` run, details `fs` 256.0 and `source` marked override. No real smoke run.
- Tests: `test_p16_connectivity_port.py` + p12/p13/p14 known-answer: 108 passed (143.8 s). `tests/test_p16_*.py`: 109 passed, 4 failed outside my files (`test_p16_flagship_port.py::test_smoothing_trial_on_a_legacy_root_is_the_a_prime_t_row`, `test_p16_independent_known_answer.py` 3 tests), owned by the ml-engineer / synthetic-tester.
