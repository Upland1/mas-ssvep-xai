# P24 · 06 · Verification

Status: READY
Author: verifier
Reads: 00_assignment.md (acceptance), 02_plan.md (acceptance, Run commands, Review additions V-1..V-8), 03_changes_data-signal.md, 03_changes_scribe.md, 05_run.md, the phase branch
Clean checkout: `mas/state/scratch/clean_clone` @ bb9c0913624238310b8b7f6d7b543c18e495b624 (`git clone --no-hardlinks`, committed files only, empty stamps, `RAW_DIR` = the main raw folder, `NN_DEVICES="cpu cuda"`)

Verdict: PASS

Round 1 verdict (cd708ac, superseded by the Round 2 rerun below): FAIL; its three reasons are kept unchanged below as the record.

One acceptance sub-criterion is not met: acceptance 3, "within the stated tolerance for GPU paths", fails for the 6-class pseudo-online summary (reason 1). Everything else compared is exact or differs only in the ways listed under V-3 and the label/timing columns below. Numbers come from `mas/state/scratch/p24_make/compare_reports.csv`, `compare_npz.txt`, `hash_data.txt`, `make_all.log` and the stamps; nothing was fixed or re-run.

## Tests on the clean checkout

```bash
.venv/bin/python -m pytest tests/ -q -o addopts="" -p no:cacheprovider    # inside the clone, after make all
```

`4 failed, 1561 passed, 22 warnings in 855.25s (0:14:15)` (`mas/state/scratch/p24_make/pytest_clone.log`; wall 14m20s, `pytest_time.txt`; `torch.get_num_threads()` 12). The 4 failures are all `tests/test_p24_docs.py::test_cited_reports_paths_exist[README.md | RESEARCH_LOG.md | docs/report/v2/report.md | docs/progress_report/progress_report.md]`: the test asserts that every `reports/...` path cited in the document exists, and in the regenerated clone some do not. Missing in the clone (from the assertion messages): README `reports/flagship_S01.csv`, `reports/flagship_S05.csv`, `reports/logs/P16/`, `reports/loso_w1/summary.csv`, `reports/loso_w1_all/summary.csv`, `reports/window_sweep_w1_all`; report `reports/logs/`, `reports/logs/P11/`, `reports/loso_w1/summary.csv`, `reports/loso_w1_all/summary.csv`; progress report `reports/loso_w1/summary.csv`, `reports/loso_w1_all/summary.csv`; RESEARCH_LOG `reports/compact_cnn_benchmark_cpu.csv`, `reports/diagnostics/p11_seed_spread_eegnet.csv`, `reports/eegnet_benchmark_cpu.csv`, `reports/eegnet_benchmark_cuda.csv`, `reports/feature_selection_sfs_audit_S03.csv`, `reports/feature_selection_sfs_diagnostics_S03.csv` and others (list in the log). Causes visible in the comparison: the `loso-all` outputs are outside `all` (V-6), logs are not produced by `all`, and the Era-A files that p05-p10 write under `reports/legacy_leaky/` in the clone sit at `reports/<f>` in the main tree (V-2). In the main tree `tests/test_p24_docs.py tests/test_p24_make_all.py` give `52 passed in 4.97s`.

## Acceptance

| Criterion (verbatim) | Re-run command | Obtained | Reference (R-x) | Tolerance | Met? | Log |
|---|---|---|---|---|---|---|
| 1. The reviewer has checked every number in the documents against a CSV. | (reviewer) plus the verifier's cross-check, step 3 | not mine to judge; my own cross-check is under "Document-number cross-check" | | | not assessed here | `xcheck*.py` |
| 2. `make all` succeeds on a clean clone with only the raw recordings added. | `make -C clean_clone all PYTHON=... RAW_DIR=... NN_DEVICES="cpu cuda"` | exit 0, 24 stamps p00-p23, one ignored non-zero exit (p07 demo, by design), `DONE rc=0 2026-10-29T17:41:42` | | exit 0 | yes | `make_all.log`, `DONE` |
| 3. The regenerated CSVs match: exactly for CPU paths, within the stated tolerance for GPU paths. | `compare.py`, `hash_data.py`, npz comparison | CPU paths exact (V-4 below). GPU paths: `eegnet_benchmark_cuda`, `nn_sweep`, `window_sweep` cnn rows, `dynamic_stopping`, `loso_w1_s01-s05*` network rows are exact in every non-time cell; `pseudo_online` is outside tolerance in 2 cells (reason 1) | `mas/04_REFERENCE_RESULTS.md` network rule | CPU: 0; GPU: per subject +-5 pp, cohort mean +-3 pp | no (GPU part) | `compare_reports.csv` |

## V-1 to V-8

| Item | Result | Evidence |
|---|---|---|
| V-1 clone | met | fresh clone at bb9c091, empty stamps, `RAW_DIR` = main raw folder, `NN_DEVICES="cpu cuda"` (`reports/eegnet_benchmark_cuda.csv` produced), `torch.get_num_threads()` = 12 recorded before the run (`torch_threads.txt`); p23 sets `--threads 2` itself |
| V-2 path mapping | applied | clone `reports/legacy_leaky/<f>` against main `reports/<f>` for `flagship_S01..S05`, `eegnet_benchmark_{cpu,cuda}`, `compact_cnn_benchmark_cpu`, `shallow_convnet_benchmark_cpu`, `classification_report_*.txt`, `feature_selection_sfs_{audit,diagnostics}_S03`; the others against main `reports/legacy_leaky/` (`compare.py`). All the CSVs of this group are EXACT (maxabs 0.0): flagship x5, eegnet cpu and cuda, compact, shallow, sfs audit and diagnostics, `n_subjects_benchmark`, `feature_selection_ablation_S03`, `feature_space_benchmark_S03`, `augmentation_ab_*` x3 |
| V-3 columns | partly as listed | see "Column-set differences" |
| V-4 exact (CPU) | met | see "Exact comparisons" |
| V-5 tolerance (GPU) | one failure | see "GPU paths" and reason 1 |
| V-6 not compared | not compared | `loso_w1`, `loso_w1_all`, `loso_w1_fbcca_all`, `window_sweep_w1_all` (not produced by `all`: 158+117+39 fold files and their summaries are main-only); S06-S040 built folders (main `processed_continuous` has 828 `.npy`, the clone 420, all 420 identical); `baselines/v1_*` bytes; logs, `.meta.txt`, `*_config.json`, `windows_meta.json` |
| V-7 exits | met | one non-zero exit, the p07 demo (`make[1]: [Makefile:153: p07] Error 1 (ignored)`, log line 1673); `compare_v1_v2 --check-regression` at log line 6094 did not stop `make` (not prefixed), so exit 0; `make` exit 0 |
| V-8 runtime | recorded | per-phase table in `05_run.md`; stamp sum 34055 s = 567.6 min, 9.46 h wall 9 h 27 min 36 s; p18 = 12967 s includes the suspend (216.1 min against 79.4 recorded); without the 136.7 min excess 430.9 min against 436.1 recorded. Stamp minutes above the recorded ones outside p18: p03 0.7/0.3, p13 16.4/15.3, p15 7.3/5.5, p16 34.5/32.5, p17 7.6/5.5, p19 10.2/2.5, p21 34.1/32.6, p22 1.6/1.1, p23 21.9/20.5; below: p04 4.6/9.1, p11 25.9/40.9, p14 63.0/67.5, p10 22.5/24.9 |

## Exact comparisons (V-4)

`compare.py` over the 319 CSV and TXT files of clone `reports/` (logs, `.meta.txt`, `*_config.json`, `windows_meta.json` excluded; `compare_reports.csv`, 319 rows):

| Status | Files |
|---|---|
| EXACT (all shared columns equal, |diff| = 0, same row count) | 245 |
| BYTES_EQ (txt) | 13 |
| DIFF | 22 (all listed below) |
| BYTES_DIFF (txt) | 6 |
| ROWS (different row count) | 3 |
| NO_MAIN (clone-only file) | 30 |

Data arrays (`hash_data.txt`, sha256 of every `.npy`, clone against main): `data/processed` 18/18 identical, `processed_per_window` 60/60, `processed_continuous` 420/420 (the clone holds S01-S05 and the `w<L>_s0.25` sweep folders; the 408 remaining main files belong to S06-S040), `processed_continuous_p17` 70/70, `processed_continuous_p19_raw` 70/70, `processed_continuous_p19_both` 70/70, `processed_p07_demo` 12/12. Different: 0. Clone-only: 0.

NPZ files (`compare_npz.txt`, 392 pairs): 42 identical, 167 identical on the common keys with extra `nbs_*` keys in the clone (V-3 expected), 183 differ only in the keys `config` (a JSON string with the git head and the run's path) and `seconds` (wall time); all other keys (predictions, probabilities, labels) are equal, GPU folds included. The 183 are the fold files of `loso_gnn` 20, `loso_w1_p22_{all,common}` 20+20, `loso_w1_p22_names` 8, `loso_w1_s01-s05` 30, `_all` 15, `_seed43` 10, `_seed44` 10 and `within_gnn` 50.

The 22 DIFF CSVs:

| Group | Files | What differs |
|---|---|---|
| Timing only | `folds.csv` of `loso_gnn`, `loso_w1_p22_{all,common,names}`, `loso_w1_s01-s05`, `_all`, `_seed43`, `_seed44`, `within_gnn` (9), `nn_sweep/folds.csv`, `window_sweep/timing.csv` | column `Seconds` only (largest |diff| 13.9 s in `window_sweep/timing.csv`, 12.2 s in `loso_w1_s01-s05/folds.csv`) |
| Label text only | `summary.csv` of `loso_w1_p22_{all,common,names}`, `loso_w1_s01-s05`, `_all`, `_seed43`, `_seed44` (7) | column `Data source` (strings; e.g. clone "cohort 5 subjects (S01, S02, S03, S04, S05), LOSO, channels common" against main "(S01-S05)"; for the P22 `within_lda` rows the clone says "within-subject" where the main P22 file says "LOSO"); every numeric column equal |
| GPU network, pseudo-online | `pseudo_online/decisions_ccnn_5class.csv`, `decisions_ccnn_6class.csv`, `summary_ccnn_5class.csv`, `summary_ccnn_6class.csv` (4) | prediction and accuracy cells, see "GPU paths" |

BYTES_DIFF (6): `legacy_leaky/classification_report_evaluate_confusion_matrix_S01..S05.txt` and `_S03_m2.txt` differ only in the last parenthetical of line 1: clone "(two-tier gate (P07))", main "(original extractor limits)"; after removing that parenthetical the six files are identical (`sed` and `diff`, run for S01-S05 and S03_m2). The commands of p05 run after the P07 gate became the default.

ROWS (3): `connectivity_cohort_flips.csv` 14 against 11 rows, `connectivity_cohort_flips_window200_vs_final.csv` 18 against 14, `connectivity_comparison/pairwise_flips.csv` 11 against 8. The extra rows (3, 4, 3) are the rows flagged by the new `flip_NBS`/`flip_nbs` columns; on the shared rows (merge on subject, method, condition or frequencies) every shared column is equal (cell-by-cell comparison printed no difference).

NO_MAIN (30): `connectivity_graph_size{,_<suffix>}.csv` (15) and `connectivity_nbs_sweep{,_<suffix>}.csv` (15) for suffixes none, aligned_S03, diagA2_rs1..5 and rs42, trial100, v1check, v1fs256, v2cont, v2cont_noguard, v2pw, window200. They are outputs of the NBS pass; the main tree has none of them.

## Column-set differences (V-3)

Expected NBS extras present: 15 cohort-summary files (`connectivity_cohort_summary.csv`, `_aligned_S03`, `_diagA2_rs{1,2,3,4,5,42}`, `_trial100`, `_v1check`, `_v1fs256`, `_v2cont`, `_v2cont_noguard`, `_v2pw`, `_window200`) with the 18 clone-only columns (`nbs_threshold`, `nbs_max_size`, `nbs_size_fraction`, `nbs_p`, `nbs_n_sig_edges`, `nbs_significant`, `nbs_size_z1.5/2/2.5/3`, `nbs_p_z1.5/2/2.5/3`, `n_stim_windows`, `n_baseline_windows`, `fs`, `source`) and six `connectivity_comparison/{coherence,plv,wpli}_pairwise_tests{,_p500}.csv` with 4 (`nbs_max_size`, `nbs_p`, `n_edges_nbs`, `fs`); NPZ keys `nbs_101..105` in the `connectivity_edges*` files (167). On these files every column present in both is equal.

Not on the expected list (anomaly to explain): `loso_warmup/cohort.csv` and `loso_warmup/summary.csv` have an extra clone column `Normalization`. The code at HEAD writes it (`scripts/benchmarks/benchmark_loso_warmup.py` line 56, commit 06cd42d "Normalization label column in the warm-up CSVs (P22 C-3)"); the main files lack it. The other 20 and 21 columns are equal.

## GPU paths (V-5)

Exact in every non-time cell although produced on CUDA: `eegnet_benchmark_cuda.csv`, `nn_sweep/` (folds, summary), `window_sweep/` (including the `cnn (compact_eegnet)` rows), `dynamic_stopping/`, `loso_w1_s01-s05{,_seed43,_seed44}/` network rows, `loso_gnn/`, `within_gnn/` (CPU). Outside exact:

`pseudo_online/summary_ccnn_5class.csv` (clone against main, accuracy in %): S01 60.0 / 60.0, S02 87.5 / 90.0, S03 97.5 / 97.5, S04 100.0 / 100.0, S05 97.5 / 97.5, Mean 88.5 / 89.0. Largest |diff| 2.5 pp per subject, 0.5 pp on the cohort mean: inside tolerance. Other columns differ (`Time (s)` up to 0.0813 s, `ITR (bits/min)` up to 1.77, `False act. (%)` up to 2.5 pp, `Forced (%)` up to 2.5 pp, `Val acc (%)` up to 1.32 pp).

`pseudo_online/summary_ccnn_6class.csv` (clone against main, accuracy in %):

| Subject | Clone | Main | |diff| (pp) | Within +-5 pp? |
|---|---|---|---|---|
| S01 | 45.0 | 35.0 | 10.0 | no |
| S02 | 50.0 | 47.5 | 2.5 | yes |
| S03 | 97.5 | 92.5 | 5.0 | at the limit (not above 5) |
| S04 | 100.0 | 100.0 | 0.0 | yes |
| S05 | 97.5 | 95.0 | 2.5 | yes |
| Mean | 78.0 | 74.0 | 4.0 | no (limit 3 pp) |

Cells outside tolerance: S01 6-class accuracy (10.0 pp), 6-class cohort mean (4.0 pp). Other 6-class columns that differ: `Missed (%)` up to 7.5 pp, `ITR (bits/min)` up to 7.66 (S01 6.91218 against 2.67128), `False act. (%)` up to 7.5 pp, `Time (s)` up to 0.178, `Val acc (%)` up to 1.03 pp. `decisions_ccnn_5class.csv` differs in 12 `pred` cells and `decisions_ccnn_6class.csv` in 17. No cell was fixed. Sign flips of the stated directions were not assessed (outside the comparison task).

## Document-number cross-check (step 3)

`xcheck.py` extracts every decimal token (digits, point, digits) from the four documents and looks for it in the CSV cells under main `reports/`; `xcheck2.py` repeats the lookup against the CSVs each document cites only. Tolerance half a unit in the last printed digit, also tried as a fraction times 100.

| Document | Decimal tokens (distinct) | Found in any main-tree CSV | Found in cited CSVs only | Not in cited CSVs |
|---|---|---|---|---|
| `README.md` | 577 (387) | 387 | 384 | 3 |
| `docs/report/v2/report.md` | 639 (400) | 400 | 380 | 20 |
| `docs/progress_report/progress_report.md` | 339 (252) | 252 | 226 | 26 |
| `docs/infographic/methodology_infographic.svg` | 46 (31) | 31 | 25 | 6 |

The first lookup is weak (2.1 million distinct cell values: any two-decimal token is likely to hit one), so the second is the one I rely on. The not-in-cited-CSV tokens are listed in `xcheck2_unmatched.txt`. I recomputed from the CSVs the groups that dominate it, with these results: the 6 x 3 window-sweep table (cohort means of `reports/window_sweep/summary.csv`, Acc and ITR at 0.5, 1, 2 and 4 s: lda 81.80/84.37, 89.89/70.03, 95.63/48.82, 98.03/28.93; fbcca 69.16/57.50, 81.72/56.56, 92.11/44.60, 96.86/28.15; cnn 80.75/87.25, 92.08/74.53, 95.51/48.43, 83.10/21.56) match; the cohort-39 means (`reports/loso_w1_all/summary.csv`, 39 subject rows: fbcca 75.80, lda 83.42, lda_subjnorm 86.13) match; the connectivity gate k = 0 means (`reports/connectivity_gate_benchmark.csv`: Base 73.75, Base+Ec 77.57, Ec 48.59) match; the three-seed GNN cohort means (`loso_gnn/seeds.csv`: nodes+F 87.69, 88.66, 89.06; subjnorm 89.89, 90.49, 90.01; `within_gnn/seeds.csv` nodes+F 85.42, 85.21, 86.01) and the network ranges (`loso_w1_s01-s05*/summary.csv` Mean rows: ccnn 85.36 to 86.58, eegnet 78.58 to 79.76) match. The README tokens 110.5, 110.1 and 325.6 are the runtime-table sums (arithmetic in `03_changes_data-signal.md`), the infographic tokens 16.7 (chance, 100/6), 84.37, 87.65, 89.85, 95.94 and 98.03 are quoted from CSV rows of the cited tables. No document token is without a source in the files I checked; I did not check each token's meaning in its sentence (the reviewer's step 1).

## Numbers in the handoffs vs logs

Per-phase minutes in `05_run.md` are the stamp seconds divided by 60, shown in the table; the 9 h 27 min 36 s is the difference of two logged timestamps. Test counts are copied from `pytest_clone.log`.

## Sources spot-check

Not part of this verification (no new sources are cited in the Makefile or the run). The documents' `## Sources` sections are covered by the test in `tests/` (existence of sections and of the cited `reports/` paths), run in the suite above.

## Reference consultations check

`03_changes_data-signal.md` states "No consultation of `reference/ssvep-eeg-xai/`". `mas/state/scratch/reference_access.log` holds 42 lines, none dated 2026-10-29. Privacy scan: no match for the forbidden terms in `README.md`, `docs/`, `RESEARCH_LOG.md`, `Makefile`, `tests/test_p24_make_all.py` (`git grep`), and no tracked local-only instruction files (`git ls-files` check).

## Reasons (if FAIL)

1. Acceptance 3, GPU part: `reports/pseudo_online/summary_ccnn_6class.csv` of the clone is outside the network tolerance of `mas/04_REFERENCE_RESULTS.md` (per subject +-5 pp, cohort mean +-3 pp) in two cells: S01 accuracy 45.0 against 35.0 (10.0 pp) and the cohort mean 78.0 against 74.0 (4.0 pp); S03 is at 5.0 pp (limit). The 5-class summary is inside tolerance (largest 2.5 pp per subject, 0.5 pp mean). All other GPU outputs agree exactly outside their time columns. I report the cells and do not interpret them.
2. V-3: the extra `Normalization` column in the clone's `loso_warmup/{cohort,summary}.csv` is not on the expected NBS list. Its cause is stated above (commit 06cd42d, main files older); the shared columns are equal. This alone would not change the verdict.
3. Tests in the clone: 4 failures of `test_cited_reports_paths_exist` (above). The test is written for the main tree, so on a regenerated tree it fails on paths that `make all` does not produce or places elsewhere. Not a defect of a document in the main tree; reported because the suite is not green on the clone.

## Round 2 rerun (pseudo-online tags, fix round 2)

Reads: `07_review.md` "Round 3 audit (fix round 2)" (8e333c6, PASS; binding items F-1..F-6), `03_changes_data-signal.md` and `04_tests.md` "Round 2 (fix)", decisions.md row afcd417.

Head (F-2): `git rev-parse HEAD` = afcd417538dc311eda8118951d720d2073ed14ef on `phase/P24-documentation`. `git diff e2bd25d HEAD --stat -- scripts/benchmarks/pseudo_online.py src/` is empty (both in the main tree and in the clean checkout). Files changed between e2bd25d and HEAD outside `mas/`: `tests/test_p20_online.py` only (35bd278, tests); the rest are `mas/state/` documents (35bd278..afcd417: 32bd825, 7b17c52, 8e333c6, afcd417).

Preserved first (F-1), `mas/state/scratch/p24_fix2/`: `p20_original/` (4 CSVs of the main-tree `reports/pseudo_online/` and `logs/pseudo_online_{5,6}class.log` copied from `reports/logs/P20/`), `clone_bb9c091/` (4 CSVs of the make-all clone), sha256 of the 10 files in `manifest.txt` (re-checked after the runs: `sha256sum -c` all OK). `reports/logs/P20/` was only read. After the runs: `manifest_after.txt` (sha256 of A, B and C outputs and logs).

Commands (F-3), the Makefile p20 commands with the explicit subjects, run by `p24_fix2/run_fix2.sh` (no `--resume`; same `--raw-dir`; the recordings read only by the script): `python -m scripts.benchmarks.pseudo_online --subjects S01 S02 S03 S04 S05 --train-session OO --test-session mOO --model ccnn --window-sec 0.5 --stride-sec 0.25 --skip-sec 0.5 --threshold 0.6 --quality-source both --raw-dir <raw> --tag ccnn_5class` and the same with `--rest-class --tag ccnn_6class`. A: main tree, default out-dir `reports/pseudo_online/`, log `reports/logs/P24/pseudo_online_{5,6}class_A.log`. B: main tree, `--out-dir mas/state/scratch/p24_fix2/main_B`, log `..._B.log`. C: a separate clean `git clone --no-hardlinks` checkout at the same head (`p24_fix2/clone_C_checkout`), `--out-dir mas/state/scratch/p24_fix2/clone_C`, logs `p24_fix2/clone_C_{5,6}class.log` (outside any `reports/`; the make-all clone `clean_clone` was not touched).

| Run | Exit | Elapsed |
|---|---|---|
| A 5-class | 0 | 35 s |
| B 5-class | 0 | 34 s |
| C 5-class | 0 | 34 s |
| A 6-class | 0 | 69 s |
| B 6-class | 0 | 73 s |
| C 6-class | 0 | 71 s |

(`p24_fix2/exits.txt`.) All six logs contain `device cuda, seed 42`.

F-4 identity (`p24_fix2/f4.py`): for both tags and the pairs A-B, A-C, B-C: `summary_*.csv` equal on every column except `Seconds`; `decisions_*.csv` equal on every cell; the per-subject `val acc` / `best epoch` log lines equal (6 lines per log). Output: `F-4 ALL EQUAL`. No retry was made; each run was done once.

F-5 per-subject values, read from `p24_fix2/p20_original/summary_ccnn_*.csv` (run 1) and `reports/pseudo_online/summary_ccnn_*.csv` (run 2). These are two runs of one seed (42) on the same code path, the first without cuDNN determinism flags; they are not a comparison of methods. The make-all clone values (bb9c091, also without flags) are in `clone_bb9c091/` and differ from both.

5-class (`ccnn_5class`), accuracy %, false activations %, forced %, ITR bits/min; run 1 = P20 original (2026-10-28, no cuDNN determinism flags), run 2 = P24 rerun (deterministic cuDNN, same seed 42):

| Subject | Acc run 1 | Acc run 2 | False act. run 1 | False act. run 2 | Forced run 1 | Forced run 2 | ITR run 1 | ITR run 2 |
|---|---|---|---|---|---|---|---|---|
| S01 | 60 | 60 | 52.5 | 57.5 | 32.5 | 32.5 | 10.923 | 10.968 |
| S02 | 90 | 87.5 | 45 | 45 | 17.5 | 22.5 | 40.364 | 34.841 |
| S03 | 97.5 | 97.5 | 20 | 20 | 0 | 0 | 71.632 | 71.632 |
| S04 | 100 | 100 | 0 | 0 | 0 | 0 | 84.957 | 84.957 |
| S05 | 97.5 | 97.5 | 20 | 20 | 0 | 0 | 73.091 | 73.091 |
| Mean | 89 | 88.5 | 27.5 | 28.5 | 10 | 11 | 56.193 | 55.098 |

6-class (`ccnn_6class`), accuracy %, false activations %, missed %, ITR bits/min; run 1 = P20 original (2026-10-28, no cuDNN determinism flags), run 2 = P24 rerun (deterministic cuDNN, same seed 42):

| Subject | Acc run 1 | Acc run 2 | False act. run 1 | False act. run 2 | Missed run 1 | Missed run 2 | ITR run 1 | ITR run 2 |
|---|---|---|---|---|---|---|---|---|
| S01 | 35 | 40 | 17.5 | 17.5 | 50 | 45 | 2.6713 | 4.5101 |
| S02 | 47.5 | 45 | 7.5 | 10 | 52.5 | 52.5 | 8.6382 | 6.9547 |
| S03 | 92.5 | 95 | 0 | 0 | 7.5 | 5 | 59.705 | 61.801 |
| S04 | 100 | 100 | 0 | 0 | 0 | 0 | 84.957 | 84.957 |
| S05 | 95 | 97.5 | 0 | 0 | 5 | 2.5 | 66.832 | 68.445 |
| Mean | 74 | 75.5 | 5 | 5.5 | 23 | 21 | 44.561 | 45.334 |

Cohort means, run 2: 5-class Acc 88.5, ITR 55.0978, false act. 28.5; 6-class Acc 75.5, ITR 45.3336, false act. 5.5.

F-6 tests. Full suite in the main tree at afcd417 (`p24_fix2/pytest_main_full.log`): `1569 passed, 22 warnings in 895.87s (0:14:55)` (CUDA available, so the CUDA identity test ran). `P24_DOCS_ROOT=<clean_clone> pytest tests/test_p24_docs.py` (`p24_fix2/pytest_docs_clone.log`): `35 passed in 0.07s` (the 4 failures of round 1 are gone).

Human run requests: none. Anomalies: none.

## Round 2 verdict

Resolution of the round 1 reasons:

1. Reason 1 (pseudo-online outside GPU tolerance): the cause is a missing cuDNN determinism flag in `pseudo_online.py` (fixed in e2bd25d, audited PASS in round 3). With the fix, three independent runs (A, B, C) are identical on every compared cell (F-4), so the script is deterministic for seed 42 on this GPU; the P20 values and the make-all clone values were non-reproducible draws and are replaced by run 2 per the round 3 ruling (item 1d). Resolved. The tolerance comparison against the P20 files is no longer the criterion; the identity A = B = C is.
2. Reason 2 (`Normalization` column in `loso_warmup`): accepted as expected by the round 3 audit (item 3) and by decisions row afcd417 (V-3 list). Settled.
3. Reason 3 (4 failures of `test_cited_reports_paths_exist` in the clone): settled by the round 3 audit (item 2: narrow rule for a make-all tree; `reports/diagnostics/` added to V-6) and by the afcd417 decisions row; the suite in the main tree passes (1569) and the docs test on the clone passes (35).

Scope note: this rerun covers the two pseudo-online tags only. The other 22 phases of `make all` were run once at bb9c091 (above) and are not repeated; `src/` is unchanged since then (`git diff` empty for `src/`), and the fix touches `scripts/benchmarks/pseudo_online.py` and `tests/test_p20_online.py` only. The documents' pseudo-online numbers still hold the P20 values until the scribe re-copies them (S-1); that re-check is the final review's (S-6).

Verdict: PASS
