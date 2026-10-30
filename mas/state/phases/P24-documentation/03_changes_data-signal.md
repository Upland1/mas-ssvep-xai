# P24 · 03 · Changes — data-signal

Status: READY
Author: data-signal
Reads: 00_assignment.md, 02_plan.md (settled 7 and 8, work-split row 1, tests), Makefile (before), `mas/state/phases/P00..P23/05_run.md` and the "Run commands" of each `02_plan.md`, `mas/state/decisions.md` (cohort rules, P07+ preprocess warning), `mas/RULES.md`
Branch: phase/P24-documentation
Commit(s): see `git log` (feat: Makefile; test: test_p24_make_all; docs: this file)

## Files

| Path | NEW / MODIFIED | Summary | Roadmap task | Source |
|---|---|---|---|---|
| `Makefile` | MODIFIED | per-phase targets `p00` ... `p23`, `all`, `all-dry`, optional `loso-all`; variables `PYTHON`, `RAW_DIR`, `NN_DEVICES`, `STAMPS`, `FORCE`; old `venv`, `test`, `help`, `inventory`, `preprocess`, `explore` kept | P24.6 | settled 7, 8 |
| `tests/test_p24_make_all.py` | NEW | 13 tests, no pipeline command runs (`make -n`, and `parse_args` on the printed arguments; one real `make all PHASES=p09 PYTHON=true` for the stamp logic) | P24.6 | settled 7 |

No `scripts/run_all.sh`: the Makefile is enough.

## Targets

`make all` = `p00 ... p23` in order (`PHASES`), each run as its own `make pNN`. Targets do not depend on each other (later phases read the outputs of earlier ones; `all` orders them). `make -n all` lists everything without running (`all-dry` is the same).

Resumability. After a phase finishes, `make all` writes `$(STAMPS)/pNN.done` (default `mas/state/scratch/make_stamps/`, git-ignored; content = elapsed seconds) and skips stamped phases on the next call (`FORCE=1` reruns). Dry runs write no stamp. Inside a phase, `build_windows --resume`, `benchmark_loso` and `benchmark_gnn_loso` already skip finished folds, and `benchmark_window_sweep` merges per cell.

Variables: `PYTHON ?= .venv/bin/python`; `RAW_DIR ?= data/raw`, passed as `--raw-dir $(RAW_DIR)` to the six scripts whose parsers have that option (`inventory_raw`, `run_preprocessing`, `build_windows`, `demo_edge_effects`, `pseudo_online`, `batch_run_subjects`; the test checks that no other script opens a recording); `NN_DEVICES ?= cpu` (P08 EEGNet; `NN_DEVICES="cpu cuda"` adds the CUDA row).

| Target | Commands (recorded in) | Main outputs |
|---|---|---|
| p00 | `inventory_raw` | `reports/raw_inventory.csv` |
| p01 | `inventory_raw --out reports/P01/...` x2 (default, `--strict`), `cmp` against p00 | `reports/P01/raw_inventory_parser*.csv` |
| p02 (= `preprocess`) | `run_preprocessing --legacy-p02` | `data/processed/<S>/`, `outputs/figures/spectra/` |
| p03 | `diagnose_occipital_spectra`, `visualize_data`, each plain and `--fs 256 --out-suffix header` | `outputs/figures/exploration/` |
| p04 | `train_models` per subject, `train_final_model` S01 and S04, `batch_run_subjects`, `run_xai` S04, `compare_subject_xai` | `outputs/` |
| p05 | `benchmark_cross_validation`, `benchmark_harmonic_fbcca`, `test_sklearn_models`, `evaluate_confusion_matrix` (S03, S03 `--m 2`, S01, S02, S04, S05), `visualize_data` S03 | `reports/flagship_S0x.csv`, `feature_space_benchmark_S03.csv`, figures |
| p06 | `benchmark_feature_selection` S03, `benchmark_5_subjects`, SFS diagnostic (`--sfs-diagnostics --n-jobs 8`) | `reports/feature_selection_*`, `five_subjects_benchmark.csv` |
| p07 | 3 `run_preprocessing` demos into `data/processed_p07_demo/` (the second exits 1 by design, prefixed `-`), `benchmark_n_subjects --data-root data/processed --n-jobs 5` | `reports/n_subjects_benchmark.csv` |
| p08 | `benchmark_eegnet` per `NN_DEVICES` | `reports/eegnet_benchmark_<device>.csv` |
| p09 | `count_parameters`, `benchmark_compact_cnn`, `benchmark_shallow_convnet` | `reports/network_parameter_counts.csv`, `*_benchmark_cpu.csv` |
| p10 | `benchmark_nn_augmentation --freeze-legacy` x3 | `reports/augmentation_ab_*.csv`, `reports/legacy_leaky/` |
| p11 | legacy snapshot (`--cv legacy --smoothing mod5` x3), `demo_cv_leakage`, leak-free reruns, A/B x3 without the flag, `demo_cv_leakage` again | `reports/n_subjects_benchmark.csv`, `augmentation_ab_*.csv` (overwrites p10) |
| p12 | `demo_coherence_bias --subjects S03 S04`, `analyze_connectivity` S03 and S04 | `reports/connectivity/` |
| p13 | two demos, `analyze_connectivity_cohort` (window200, trial100, final), two `--compare`, aligned S03, six-seed S05 wPLI diagnostic | `reports/connectivity_cohort_summary*.csv`, `connectivity_edges*/` |
| p14 | `compare_connectivity_frequencies`, `test_connectivity_frequency_differences` (p500, final 1000), `--compare p500 ""`, `check_power_alpha_confound` | `reports/connectivity_comparison/` |
| p15 | `build_graph_dataset --rebuild`, `benchmark_connectivity_gate`, `benchmark_gnn --smoke-test`, `benchmark_gnn` | `data/processed/S0x/graph_dataset.npz`, `reports/gnn_benchmark*.csv` |
| p16 | `freeze_baseline` (only if `baselines/v1_*` is absent), `demo_edge_effects`, two `build_windows`, 6 flagship and 4 connectivity rows, `compare_v1_v2 --check-regression` (stops make on failure), `compare_v1_v2` | `data/processed_per_window`, `data/processed_continuous`, `reports/*_v1*`, `*_v2*` |
| p17 | `build_windows` 4 banks into `data/processed_continuous_p17`, D0 regression, 6 benchmarks (bank x classes) | `reports/n_subjects_benchmark_p17_*.csv` |
| p18 | cohort 200 and 1000 with `--stats nbs`, `--compare`, pairwise 1000, `--summary-only` | `reports/connectivity_*_p18_nbs*`, `connectivity_comparison/` |
| p19 | 3 builds (filtered into `mas/state/scratch/p19_filtered`, raw, both), 4 benchmarks | `data/processed_continuous_p19_*`, `reports/n_subjects_benchmark_p19_*.csv` |
| p20 | 6 window builds, `benchmark_window_sweep` (fbcca lda), `benchmark_nn_sweep`, `simulate_dynamic_stopping` (lda), 2 `pseudo_online`, 6 CNN sweep invocations, `simulate_dynamic_stopping` | `reports/window_sweep`, `nn_sweep`, `dynamic_stopping_lda`, `dynamic_stopping`, `pseudo_online` |
| p21 | `build_windows --resume`, `benchmark_loso` classical common and all (CPU only), networks, classical rerun (skips), seeds 43 and 44 | `reports/loso_w1_s01-s05*` |
| p22 | `benchmark_loso` common, all, names (with `within_lda`), `benchmark_loso_warmup` | `reports/loso_w1_p22_*`, `loso_warmup` |
| p23 | smoke into `mas/state/scratch/p23_verify_smoke`, GNN within, GNN LOSO (CPU, 2 threads, 3 seeds) | `reports/within_gnn`, `reports/loso_gnn` |
| `loso-all` (outside `all`) | `build_windows --resume` on every raw subject, `benchmark_window_sweep` w1, `benchmark_loso` classical `fbcca` all channels, common, all (CPU) | `reports/window_sweep_w1_all`, `loso_w1_fbcca_all`, `loso_w1`, `loso_w1_all` |

Excluded: the P21 39-subject networks (`ccnn compact eegnet` on `reports/loso_w1`), the Colab notebook (no `colab` target), the pytest runs, and the verifiers' read-only hashes and checks.

## Cohort rule

Every command of `all` names `--subjects S01 S02 S03 S04 S05` (or `--subject Sxx`) wherever the script would otherwise discover subjects; the test enforces it from each parser. Exemptions: `--compare`, `--summary-only` and `--smoke-test` commands (no subject selection), and `loso-all`, which discovers on purpose (39 subjects, B003 as amended). The only recorded commands that had no subject option are the `--all` ones (`train_models --all`, `run_preprocessing --all`, the P03 `--all`); they are rewritten, see deviations.

## Runtime table (measured, minutes; seconds in the sources)

Sources: the "Commands executed" tables of `mas/state/phases/Pxx/05_run.md` (verifier runs on the 16-core workstation with the GPU of P20/P21; sums are mine, arithmetic in the Python command below). Pytest runs are excluded. CPU = classical and CPU-only network jobs; GPU = jobs that ran on CUDA in the recorded run (CPU time for these is not measured; P21 states about 16 h for the 40-subject networks on a 3050-class GPU, so a CPU run of the cohort-5 networks is not expected to be shorter than the GPU one).

| Target | CPU min | GPU min | Total min | Recorded breakdown |
|---|---|---|---|---|
| p00 | 0.0 | | 0.0 | 1 s |
| p01 | 0.0 | | 0.0 | below 3 s |
| p02 | 0.1 | | 0.1 | 5 s |
| p03 | 0.3 | | 0.3 | 3+3+5+4 s |
| p04 | 9.1 | | 9.1 | 28+27+36+438+7+5 s (+3 s param count, not run) |
| p05 | 1.2 | | 1.2 | 74 s (Round 1) |
| p06 | 12.8 | | 12.8 | 80+13 s, SFS diagnostic 674 s |
| p07 | 0.2 | | 0.2 | 1+1+1+6 s |
| p08 | 0.6 | (0.4) | 0.6 | cpu 35 s; cuda 22 s only with `NN_DEVICES="cpu cuda"` |
| p09 | 1.8 | | 1.8 | 1+45+60 s |
| p10 | 24.9 | | 24.9 | 389+497+609 s (CPU nets) |
| p11 | 40.9 | | 40.9 | classical 15+15+97+17+16+17+97+19 s, A/B 833+668+661 s |
| p12 | 0.6 | | 0.6 | 14+9+10 s |
| p13 | 15.3 | | 15.3 | 905 s (window200 335, trial100 181, final 346) + about 10 s diagnostic |
| p14 | 67.5 | | 67.5 | 6+1343+2702+1+1 s |
| p15 | 5.5 | | 5.5 | 11+75+1+241 s |
| p16 | 32.5 | | 32.5 | builds 8 s, flagship rows about 150 s, connectivity 340+328+385+388+393 s (rows v1check, v1fs256, v2pw, v2cont, v2cont_noguard) |
| p17 | 5.5 | | 5.5 | 4+15+19+28+50+72+57+83 s |
| p18 | 79.4 | | 79.4 | 370+1853+1+2537+1 s |
| p19 | 2.5 | | 2.5 | 15+20+19+49+49 s |
| p20 | 2.9 | 78.1 | 81.0 | GPU: nn_sweep 944, pseudo_online 33+63, CNN sweep 3645 s; CPU rest |
| p21 | 0.6 | 32.0 | 32.6 | GPU networks about 1074 s (300 s interrupted + 774 s resumed in the record) + seeds 412+438 s |
| p22 | 1.1 | | 1.1 | 24+29+9+6 s |
| p23 | 20.5 | | 20.5 | smoke 37, within 472, LOSO 721 s |
| **Total `make all`** | **325.6 (5.43 h)** | **110.5 (1.84 h)** (110.1 without the p08 CUDA row, which is outside `all` by default) | **436.1 (7.27 h)** | |

Over the 4 h limit of settled point 8: the recorded runs add up to 7.3 h (about 7.3 h also without p08's CUDA row). The orchestrator therefore asks Sebastian first (settled point 8). Eras: p00-p15 = 180.8 min (3.0 h), p16-p23 = 255.3 min (4.3 h). The largest items are p18 (79.4), p20 (81.0, of which the six CNN sweep invocations 60.8), p14 (67.5), p11 (40.9), p16 (32.5), p21 (32.6), p10 (24.9), p23 (20.5). Intermediate runs that only support a flip/sensitivity table and could be skipped to save time if Sebastian accepts it (they are in the targets because the reports quote their CSVs): p14 `p500` 22.4 min, p18 `p200` 6.2 min, p13 `window200` + `trial100` 8.6 min, p06 SFS diagnostic 11.2 min; together 48.4 min, giving 6.5 h; this is still above 4 h. A run of `make all` therefore needs a detached, resumable session (stamps), not the 4 h budget; I did not remove anything from the targets.

Arithmetic: `.venv/bin/python` snippet over the seconds above (printed `cpu 19534 s 325.6 min`, `gpu 6631 s 110.5 min`, `total 436.1 min 7.27 h`; minus the intermediates 6.46 h).

## Deviations from the recorded commands

1. P02 runs `run_preprocessing --subjects S01..S05 --legacy-p02` instead of `--all`: since P07 the default is the two-tier 8-channel gate, and `--legacy-p02` is the documented switch that reproduces the P02 arrays (decisions.md 2026-10-24 P07, `make preprocess`). `--subjects` replaces `--all` because the raw folder holds 39 subjects. `preprocess` is its own target (an existing test requires the recipe text); `p02` depends on it.
2. P03, P04: `--all` becomes `--subjects S01 ... S05` (P03) or one `train_models --subject Sxx` per subject (P04; `train_models` has no `--subjects`); outputs are per subject, so they are the same files.
3. P04: `batch_run_subjects` runs with the default paradigm, as recorded (the verifier omitted `--paradigm` because of the guard; the default is the same session).
4. P08: only the CPU row by default; the CUDA row is `NN_DEVICES="cpu cuda"` (the recorded run also ran each device twice for the determinism check; only one run per device is in the target).
5. P11: `demo_cv_leakage` gets `--subjects S01..S05` (no other flags were recorded).
6. P13: the six-seed DIAG-A2 (S05 wPLI) from the verifier's report is in `p13` because the P13 report quotes `reports/connectivity_cohort_summary_diagA2_rs<B>.csv`.
7. P16: `freeze_baseline` runs only when `baselines/v1_*` is absent (a repeated tag refuses by design); in a clean clone it snapshots the Era A/B outputs that p00-p15 just produced, with `configs/` taken from git at 97a29be (the clone must contain that commit). `compare_v1_v2 --check-regression` is NOT silenced (corrected in Fix round 1: the final P16 run exits 0; exit 1 was round 1).
8. P19: the filtered regression build goes to `mas/state/scratch/p19_filtered` as recorded; the hash/identity checks A-F of the pre-run audit are not targets (read-only checks).
9. P20: the three `pseudo_online` and sweep commands get `--subjects S01..S05`; `--quality-source both` was already in the pre-run additions. Recorded order kept (2b after 5-6). The stop rule S was a budget guard and is not in the Makefile.
10. P21: `build_windows --resume` gets `--subjects S01..S05` (recorded: all raw subjects, 39 here); the SIGINT interrupt test (B7), the hashes and the checks are not targets; the rerun of the classical command (command 4) is a target. The 39-subject classical runs are `loso-all`; the 39-subject networks are excluded.
11. P22: the three refusal checks (4a, 4b, 4c) are not targets (4a and 4b exit 1 by design).
12. P23: the smoke test is a target (37 s, writes only to scratch); the resume/refusal reruns are not.
13. P05: Round 1 command list (Round 2 repeated it with `_r2` logs). P06: the SFS diagnostic is the last line of `p06` and rewrites `feature_selection_ablation_S03.csv` identically (cmp identical in 05_run.md).

Phases whose commands could not be reproduced exactly: P05-P10 (flags added, see Fix round 1) and the rows above. Not reproduced by design: pytest runs, hash and identity checks, interrupt tests, refusal checks, Colab. Commands that need a GPU: p20 (nn_sweep, pseudo_online, CNN sweep) and p21 (networks) run on CUDA when available (`--device` default), as recorded.

## Verification

- `make -n all PYTHON=fakepython RAW_DIR=FAKE` and `make -n pNN` for every target print the commands (tested, 13 tests, 2.5 s).
- Every printed `-m scripts...` command (149 in the 24 phase targets, plus those of `loso-all`) parses against the real parser; the six recording readers receive `--raw-dir`; no command of `all` discovers subjects; every `--out-dir/--out-root/--processed-dir/--data-root/--out-suffix` value quoted in `mas/state/phases/P*/05_run.md` and `mas/state/reports/P*.md` is in some target (the test skips the last check when `mas/state/` is absent). `loso-all` outputs are absent from `all`.
- Mutants shown by the last-but-one test: omitting `--subjects` is detected (`build_windows`, `run_preprocessing --all`), an unknown flag is rejected, a missing `--raw-dir` shows as `None`.
- Existing tests that read the Makefile (`test_p07_round1_known_answer`, `test_p07_quality_signal`) pass.
- Full suite alone, `.venv/bin/python -m pytest tests/ -q -o addopts=""` (log `mas/state/scratch/pytest_p24_data_signal.txt`): `1526 passed, 22 warnings in 848.38s (0:14:08)` (1513 at P23 plus the 13 new tests).

## R11

No consultation of `reference/ssvep-eeg-xai/`.

## Questions
<!-- receivers append: ACK <agent> <YYYY-MM-DD>, then questions; answers appended, never deleted -->


## Fix round 1 (review 07_review.md, pre-run audit F1-F4)

Status: READY

**F1.** p10 now passes `--cv legacy --smoothing mod5 --freeze-legacy` (since P11 `--freeze-legacy` without `--cv legacy` is `parser.error`, exit 2).

**F2.** Every P05-P10 command of a script with a `--cv` option now passes `--cv legacy --smoothing mod5` (17 commands: p05 `benchmark_cross_validation`, `benchmark_harmonic_fbcca`, `evaluate_confusion_matrix` x6; p06 `benchmark_feature_selection` x2 including the SFS diagnostic; p07 `benchmark_n_subjects`; p08 `benchmark_eegnet`; p09 `benchmark_compact_cnn`, `benchmark_shallow_convnet`; p10 x3). `mod5` is the script default and the `i % 5` reset of the final P05 round; it is passed explicitly. `test_sklearn_models`, `benchmark_5_subjects` and `visualize_data` have no `--cv` option, so they are unchanged. The p11 legacy snapshot lines already carried the flags.

Deviation (path mapping). With `--cv legacy` the scripts write under `reports/legacy_leaky/` (`src/preprocessing/dataset/cv_utils.py` `LEGACY_DIR`; figures and classification reports in the matching `legacy_leaky` subfolders), while the main tree still holds the Era-A files that P11 did not rerun at `reports/<f>`. The comparison for the clone must therefore map:

| Clone path (after p05-p10 and p11) | Main-tree path holding the same Era-A numbers |
|---|---|
| `reports/legacy_leaky/n_subjects_benchmark.csv`, `feature_selection_ablation_S03.csv`, `feature_space_benchmark_S03.csv`, `augmentation_ab_{eegnet,compact_cnn,shallow_conv_net}.csv` | the same name under `reports/legacy_leaky/` (P11 snapshot / P10 freeze) |
| `reports/legacy_leaky/flagship_S0x.csv`, `eegnet_benchmark_cpu.csv`, `compact_cnn_benchmark_cpu.csv`, `shallow_convnet_benchmark_cpu.csv`, `classification_report_*` | `reports/<same name>` (Era-A files P11 did not rerun; verify per file that the main-tree one is not a grouped rerun by reading its `.meta.txt` splitter line) |
| `reports/n_subjects_benchmark.csv`, `feature_selection_ablation_S03.csv`, `feature_space_benchmark_S03.csv`, `augmentation_ab_*.csv` (grouped, written by p11) | the same paths (P11 grouped numbers) |
| `reports/five_subjects_benchmark.csv`, `sklearn_suite_S03.csv` (scripts without `--cv`, legacy by construction) | the same paths |

p07's `n_subjects_benchmark.csv` is now written to `reports/legacy_leaky/` and p11 then rewrites `reports/n_subjects_benchmark.csv` with the grouped run, so the final state matches the main tree. Confusion-matrix figures of p05 go to the `legacy_leaky` figure folder; the main tree holds the Era-A ones at the P05 paths. Items that are rerun later by p11 (grouped) end identical to the main tree; the verifier compares the legacy files by the table above.

**F3.** Four new tests (18 in the file now): every Era-A command of a `--cv` script has `cv == legacy` and `smoothing == mod5` (17 commands); every `--freeze-legacy` command has `--cv legacy`; the three p10 commands are run through `main()` with empty folders so `parser.error` would show as SystemExit 2 (the old p10 line fails here); the p16/p17 builds pin `--quality-source filtered` and `--banks`. Run against the previous Makefile, 5 tests fail (`test_era_a_commands_...`, `test_freeze_legacy_implies_cv_legacy_...`, `test_p10_commands_pass_the_scripts_own_post_parse_validation`, `test_builds_of_p16_and_p17_...`, `test_final_regression_check_is_not_silenced`); 13 pass. The vacuous bash `[ -f ]` half of the dry-run test was removed.

**F4.** `compare_v1_v2 --check-regression` has no `-` prefix any more (the final P16 run exits 0, `05_run.md` command 17 after 9b297c0). Deviation 7 corrected above.

**Other defaults changed after the recording phase (audit).** Scanned decisions.md, the parsers' defaults and `configs/pipeline_config.yaml`:
- `quality.source` is `both` since P19 (config default; commit e090d20). The P16 builds and the P17 build were recorded on the filtered gate and the default banks of that time, so p16 (both builds) and p17 now pass `--quality-source filtered`; the p16 builds also pass `--banks fbcca fbcsp` (config `filter_bank` enables harmonic and intermediate since P17, which would add files to the P16 root whose hash P17 checks). p19, p20, p21 already pass the source explicitly or are `--resume` over p20 builds.
- `analyze_connectivity_cohort --stats` default became `nbs` (P18) but only changes which criterion is printed; FDR, NBS and global p are always saved: no change needed.
- `--quality` default `shared`, `--fs` default None on `benchmark_n_subjects` and the connectivity scripts: P16's `_v1check` regression reproduced R-6 and the P13 final summary exactly with these defaults, so they stay.
- `--cv` default `grouped` and `--smoothing` default `mod5`: handled above. `build_windows --filter-mode` default `continuous` is passed explicitly in p16.

Not changed: runtimes (same work), the 149-command count (unchanged), targets and outputs of p11-p23.

Full suite alone after this round (`mas/state/scratch/pytest_p24_fix1.txt`): `1565 passed, 22 warnings in 984.01s (0:16:24)`.


## Round 2 (fix)

Status: READY

Reads: 06_verify.md (reason 1), 02_plan.md (V-4, V-5), `mas/state/decisions.md` (row "Verify FAIL (cd708ac)"), `reports/logs/P20/pseudo_online_{5,6}class.log`, `mas/state/scratch/p24_make/make_all.log` lines 8277-8321, `src/models/cnn/training.py`, `src/models/cnn/benchmark_common.py`, `src/preprocessing/dataset/augmentation.py`.
Commits: e2bd25d (`fix:` script), 35bd278 (`test:`), this file (`docs:`).

### Files

- MODIFIED `scripts/benchmarks/pseudo_online.py`: in `main`, right after `resolve_device`, `if device == "cuda": torch.backends.cudnn.deterministic = True; torch.backends.cudnn.benchmark = False` (3 added lines, same idiom as `src/models/cnn/benchmark_common.py` line 144 and `scripts/benchmarks/benchmark_window_sweep.py` line 260). Nothing else changed; CPU runs untouched.
- MODIFIED `tests/test_p20_online.py`: 3 tests appended (P24 fix round 2 block).

### Diagnosis (confirmed)

1. Same code, seed 42 and device cuda in both runs (header line of both logs: "device cuda, seed 42"), but different trajectories: 6-class best epoch S01 104/129 (P20 log) vs 109/134 (make all), S02 77/102 vs 43/68, S03 30/55 vs 32/57, S05 25/50 vs 27/52; S04 24/49 both.
2. `pseudo_online.py` was the only network script without the cudnn flags (`grep -rn cudnn scripts src`: benchmark_loso, benchmark_window_sweep, benchmark_nn_sweep, benchmark_nn_augmentation, network_seed_spread, benchmark_gnn, benchmark_gnn_loso, benchmark_common set them; pseudo_online did not). Every CUDA output of those scripts was exact in the clone (06_verify.md "GPU paths"), `dynamic_stopping/` included, which trains the same ccnn on CUDA through the window sweep.
3. Other nondeterminism sources checked in the pseudo-online path, none found: `fit_network` calls `torch.manual_seed(seed)` before the model, the DataLoader uses `shuffle=True` with `generator=torch.Generator().manual_seed(seed)` and `num_workers=0`; augmentation draws from its own `numpy.random.default_rng(seed)` (`SSVEPAugmentedDataset`); the inner validation split is `StratifiedGroupKFold(shuffle, random_state=seed)`; the two `set`s in the script (`channel_tier`, `check_channels`) only feed membership tests, `kept` is built in montage order and the reported lists are `sorted`. Torch default `cudnn.deterministic` is False here (`torch 2.14.1+cu130`, printed by `.venv/bin/python -c ...`).
4. Synthetic reproduction on this GPU (`fit_network` ccnn, 60 synthetic trials x 8 windows, seed 42, 40 epochs, scratch script `det.py`): flags off, two runs give the same best epoch but `max |d val loss| 0.0004615858197212219`; flags on, `0.0`. Small per-epoch differences of this kind change the early-stopping epoch over 100+ epochs, which is what the logs show.

### Tests

- `test_pseudo_online_same_seed_gives_identical_probabilities_and_decisions_cpu`: two `main` runs on fake recordings, seed 42, CPU: stream probabilities `np.array_equal`, decisions and summary (minus `Seconds`) frame-equal. Honest note: it passes on the old code too (CPU kernels deterministic).
- `test_pseudo_online_sets_cudnn_determinism_when_device_is_cuda`: device resolution and `run_subject` stubbed (no GPU needed); flags preset to deterministic False / benchmark True; asserts they are untouched for cpu and (True, False) at training time for cuda. Fails on the old code.
- `test_pseudo_online_same_seed_gives_identical_probabilities_cuda` (skipped without CUDA): two real CUDA runs, 15 epochs, flags reset to False beforehand; probabilities and decisions identical. Fails on the old code on this machine (`assert np.array_equal(p1, p2, equal_nan=True)` False).
- Against the old script (HEAD version restored temporarily): `2 failed, 1 passed, 8 deselected in 4.43s`. With the fix: `tests/test_p20_online.py` `11 passed in 5.53s`.
- Full suite (`.venv/bin/python -m pytest tests/ -q -o addopts="" -p no:cacheprovider`, working tree = e2bd25d + 35bd278, CUDA available so the CUDA case ran): `1569 passed, 22 warnings in 944.75s (0:15:44)`.

### Run commands for the verifier (not run by me)

From the Makefile `p20` target (`P := $(PYTHON) -m`, `S := --subjects $(SUBJ)`, `RAW := --raw-dir $(RAW_DIR)`), with `SUBJ = S01 S02 S03 S04 S05`:

```bash
.venv/bin/python -m scripts.benchmarks.pseudo_online --subjects S01 S02 S03 S04 S05 --train-session OO --test-session mOO --model ccnn --window-sec 0.5 --stride-sec 0.25 --skip-sec 0.5 --threshold 0.6 --tag ccnn_5class --quality-source both --raw-dir <RAW_DIR>
.venv/bin/python -m scripts.benchmarks.pseudo_online --subjects S01 S02 S03 S04 S05 --train-session OO --test-session mOO --model ccnn --window-sec 0.5 --stride-sec 0.25 --skip-sec 0.5 --threshold 0.6 --rest-class --tag ccnn_6class --quality-source both --raw-dir <RAW_DIR>
```

Expected runtime on cuda: per-subject `Seconds` in `reports/logs/P20/pseudo_online_5class.log` sum to 30 s and in `pseudo_online_6class.log` to 60.7 s (`python -c "print(10.5+8.4+5.7+2.7+2.7, 21.1+15.6+8.2+7.5+8.3)"`), so about 1 to 1.5 min per tag with start-up; deterministic cudnn may be slightly slower. Device: `auto` resolves to cuda here; both runs of a comparison must use the same device. Expected outcome: two main-tree runs and the clone run give identical `summary_ccnn_{5,6}class.csv` and `decisions_ccnn_{5,6}class.csv` apart from `Seconds`.

Consequence for the documents: the new main-tree numbers will in general differ from the P20 ones (the P20 run was one draw of a nondeterministic trajectory), so the pseudo-online figures quoted in `README.md` (line 242), `RESEARCH_LOG.md` (line 510, "89.00 % (5 classes) and 74.00 % (6 classes)"), `docs/report/v2/report.md` (line 215), `docs/progress_report/progress_report.md` (line 131) and `docs/infographic/methodology_infographic.svg` must be re-copied from the regenerated CSVs (scribe), and the P20 log/report should record that the earlier numbers came from a run without the flags.

### R11

No consultation of `reference/ssvep-eeg-xai/`.
