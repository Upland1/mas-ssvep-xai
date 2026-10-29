# P22 · 06 · Verification

Status: READY
Author: verifier
Reads: 00_assignment.md (acceptance), 02_plan.md (Acceptance checks, PR-1..PR-7, V1..V11), 05_run.md, the phase branch
Clean checkout: `mas/state/scratch/verify/P22` @ 461ef330d1ca145c8375e4b059b4bc529244c135 (detached worktree, removed after the commit)

Verdict: PASS

All numbers are verbatim from `reports/logs/P22/analysis.txt` (script `mas/state/scratch/verify/analysis_p22.py`, read-only) and the CSVs named. Data source of every table: built continuous folders `processed_continuous/w1_s0.25`, session OO, cohort S01-S05, LOSO (or within-subject for `within_lda`), 1.0 s windows, stride 0.25 s. Noise unit: SE = 100 sqrt(p(1-p)/n) pp, SE_D = sqrt(SE_a^2 + SE_b^2) (P21 C-3). "Strict" means beyond 2 SE_D.

## Tests on the clean checkout

`pytest tests/ -q -o addopts=""`, alone, `torch.get_num_threads()` = 12: `1433 passed, 8 skipped, 22 warnings in 800.46s (0:13:20)`, exit 0 (`reports/logs/P22/pytest_full.log`). Collected 1441 = the tester's 1441 passed (`07_review.md` round 2); the 8 skipped ran with `CUDA_VISIBLE_DEVICES=""`.

## Acceptance

| Criterion (verbatim) | Re-run command | Obtained | Reference (R-x) | Tolerance | Met? | Log |
|---|---|---|---|---|---|---|
| 1. Both scripts run (commands 1-3, 5 exit 0) | 05_run.md commands 1, 2, 3, 5 | exits 0, 0, 0, 0 (23.79 s, 29.47 s, 8.82 s, 5.79 s) | none | exit 0 | yes | `loso_cmd1_common.log`, `loso_cmd2_all.log`, `loso_cmd3_names.log`, `warmup_cmd5.log` |
| 2. A changed configuration on an existing out-dir is refused, nothing changes | command 1 with `--seed 43`; with `--within-repeats 3`; then command 1 unchanged | 4a exit 1: `configuration differs {'seed': (42, 43)} (saved, now); use a new --out-dir`. 4b exit 1: `configuration differs {'hyper': ({... 'within_repeats': 5}, {... 'within_repeats': 3})}; use a new --out-dir`. sha256 of the 26 files equal before / after 4a / after 4b (`cmp`, HASH_EQUAL). 4c exit 0, 20 `[skip]` lines, hashes of all 26 files identical to before (RERUN_IDENTICAL, so `summary.csv` byte-identical) | R-16 none | exact | yes | `loso_cmd4_*.log`, `v5_hash_*.txt` |
| 3. Warm-up table produced and recorded per subject and as a cohort with `warmup - full` | command 5 | `reports/loso_warmup/summary.csv` (20 subject rows + Mean/SD per K), `cohort.csv`, `recording_order.csv`, `warmup_config.json`; tables below | R-16 no numeric target | record | yes | `warmup_cmd5.log` |
| 4. `within_lda` channel list equals the LOSO list in every out-dir; LOSO vs within per subject with SE | `analysis.txt` V3, PR-1 | common: 5/5 files, channels of `within_lda` = `lda` = PO3, POz, PO4, PO8, O1, Oz, O2; all: 8-channel montage, 5/5; names: 8 names in the given order, 2/2; `train_subjects == [S]` everywhere; table below | none | exact | yes | `analysis.txt` |
| 5. Explicit-names run prints who is left out and what the gate dropped | command 3 | `[-] Leaving out S01: gate dropped PO7`, `... S03 ...`, `... S04 ...`; `[=] Keeping S02: gate accepted every named channel; gate dropped nothing`, same for S05; `Channels (names): PO7, PO3, POz, PO4, PO8, O1, Oz, O2 (explicit; gate accepted all in the kept subjects)` | none | exact | yes | `loso_cmd3_names.log` |
| 6. S01-S05 hash unchanged; suite passes alone; R11 log; privacy scan clean | sha256 before/after; pytest; log and scan below | both hashes `e7f55081705d9a0e9a528b93885925dd8cbfe354f44406c04fedc88e14bebab4` (65 files); suite passed alone; R11 and scan below | none | exact | yes | `hash_before.txt`, `hash_after.txt`, `pytest_full.log` |

## Binding items V1..V11

| Item | Result | Evidence |
|---|---|---|
| V1 | One head, clean. Command: `analysis.txt` loops over the 48 fold configs, the 3 `loso_config.json` and `warmup_config.json`: `distinct heads {'461ef330d1ca145c8375e4b059b4bc529244c135'} dirty {False} n folds 48`. Equals the worktree HEAD. MET | `analysis.txt` |
| V2 | `ls -d` of `reports/loso_w1_p22_common`, `_all`, `_names`, `reports/loso_warmup` before command 1: "No such file or directory" x4. MET | `v2_ls_before.txt` |
| V3 | Channels and `train_subjects == [S]` checked per fold file in all three out-dirs: ok. `Runs` for `within_lda` = 5.0 for every subject in common, all and names (and 1.0 for the three LOSO methods). MET | `analysis.txt` |
| V4 | `[-] Leaving out` for exactly S01, S03, S04 (gate dropped PO7); `[=] Keeping` for S02, S05; `loso_config.json` cohort `['S02', 'S05']`. MET | `loso_cmd3_names.log`, `analysis.txt` |
| V5 | Refusals: see Acceptance 2. The seed message names `seed`; the repeats message names `hyper`; both contain "use a new --out-dir"; before hash taken after command 1, no later command wrote there. MET | `v5_hash_*.txt` |
| V6 | `Folds` = 5 for every method (cohort row) in common and all, = 2 in names (per-subject rows show 1 fold file each). `grep -ci "[warn]\|INCOMPLETE"` over all P22 logs and CSVs: 0 matches. MET | `analysis.txt` |
| V7 | `within_lda` `proba_rep` of S02, S05: `np.array_equal` True between `_all` and `_names`. `fbcca` S02, S05: labels, predictions and probabilities bitwise equal between `_all` and `_names`. `fbcca`, `lda`, `lda_subjnorm` for S01-S05: labels, predictions, 2-tap predictions and probabilities bitwise equal between `_common` and `reports/loso_w1_s01-s05`, and between `_all` and `reports/loso_w1_s01-s05_all` (every row of 30 comparisons printed `True`; zero mismatches; windows 680/644/661/665/679). MET | `analysis.txt` |
| V8 | Recomputed `lda_subjnorm` and `lda` accuracy on windows of trials with rank > K (from `recording_order.csv`) vs `full (%)` and `none (%)` for all 5 subjects x 4 K: max abs difference 0.0049495 pp (rounding of the 2-decimal CSV) <= 0.005; scored-window counts equal for all 20 rows. MET | `analysis.txt` |
| V9 | Trials per subject equal the common summary `Trials`: S01 40, S02 39, S03 40, S04 40, S05 40. Rank order differs from sorted-id order for all five (e.g. S01 recording ids 88, 89, 96, 104, 80, 112). Start monotone with rank. Minimum gap between consecutive first window starts: S01 14.968 s, S02 11.500 s, S03 14.500 s, S04 11.500 s, S05 14.968 s; overall minimum 11.5 s (>= 5 s). MET | `analysis.txt`, `recording_order.csv` |
| V10 | Numeric columns of `common`, `all`, `names` summaries and the warm-up summary equal the builder smokes (`mas/state/scratch/p22/{common,all2,names,warmup}/summary.csv`): max abs numeric difference 0.0 in all four (28, 28, 16 and 28 rows). Smoke heads: `common`, `names`, `warmup` at 046e45bc1b8f53842729d4ae4cd89c2ad0565b89 with dirty True; `all2` at e1d696cc27918bf4a503366d4ab01d16f5e63e1f, dirty False; verifier run at 461ef33, dirty False. Differences in head or dirty flag therefore do not change any number. MET | `analysis.txt` |
| V11 | Hash before and after equal the pin (65 files); suite alone passed; R11 log and privacy scan below. MET | see below |

## PR-1..PR-3 (LOSO vs within, subject normalization), per subject

Source: `reports/loso_w1_p22_common/summary.csv`, `reports/loso_w1_p22_all/summary.csv`. Columns: Acc in % (windows scored per subject = 680, 644, 661, 665, 679). `lda - within` is negative where within is higher.

Common channels (PO3, POz, PO4, PO8, O1, Oz, O2):

| Subject | lda | within_lda (SD over 5 repeats) | lda - within (pp) | SE_D | in SE_D | subjnorm - lda (pp) | SE_D | in SE_D | within - subjnorm (pp) | in SE_D |
|---|---|---|---|---|---|---|---|---|---|---|
| S01 | 69.26 | 75.88 (0.61) | -6.62 | 2.41 | -2.74 | +5.59 | 2.43 | +2.30 | +1.03 | +0.44 |
| S02 | 76.24 | 82.02 (0.89) | -5.78 | 2.26 | -2.56 | +6.83 | 2.24 | +3.06 | -1.05 | -0.50 |
| S03 | 96.07 | 97.31 (0.29) | -1.24 | 0.98 | -1.26 | -0.46 | 1.10 | -0.42 | +1.70 | +1.67 |
| S04 | 99.55 | 99.79 (0.08) | -0.24 | 0.31 | -0.76 | +0.15 | 0.34 | +0.45 | +0.09 | +0.33 |
| S05 | 96.91 | 98.97 (0.18) | -2.06 | 0.77 | -2.68 | +0.00 | 0.94 | +0.00 | +2.06 | +2.68 |
| Mean | fbcca 82.40, lda 87.61, lda_subjnorm 90.03, within_lda 90.79 | | | | | | | | | |

All channels (PO7 included where the gate kept it for the model; all 8 requested):

| Subject | lda | within_lda (SD) | lda - within (pp) | SE_D | in SE_D | subjnorm - lda (pp) | SE_D | in SE_D | within - subjnorm (pp) | in SE_D |
|---|---|---|---|---|---|---|---|---|---|---|
| S01 | 67.65 | 72.15 (1.00) | -4.50 | 2.48 | -1.81 | +5.59 | 2.47 | +2.26 | -1.09 | -0.45 |
| S02 | 70.03 | 77.36 (0.92) | -7.33 | 2.45 | -3.00 | +8.70 | 2.42 | +3.59 | -1.37 | -0.59 |
| S03 | 96.07 | 96.64 (0.79) | -0.57 | 1.03 | -0.55 | -0.61 | 1.11 | -0.55 | +1.18 | +1.10 |
| S04 | 99.70 | 99.70 (0.11) | +0.00 | 0.30 | +0.00 | +0.00 | 0.30 | +0.00 | +0.00 | +0.00 |
| S05 | 98.23 | 99.09 (0.22) | -0.86 | 0.62 | -1.38 | -1.62 | 0.86 | -1.89 | +2.48 | +3.16 |
| Mean | fbcca 81.16, lda 86.34, lda_subjnorm 88.75, within_lda 88.99 | | | | | | | | | |

Names run (all 8 names in the given order; cohort S02, S05 only; no prediction, N5): S02 lda 46.27, within 77.36 (SD 0.92), lda - within -31.09 (SE_D 2.57, -12.12 SE_D), subjnorm - lda +28.42 (+10.90 SE_D); S05 lda 91.90, within 99.09 (SD 0.22), -7.19 (SE_D 1.11, -6.49 SE_D), subjnorm - lda -6.33 (-3.71 SE_D). Mean over the two: fbcca 80.02, lda 69.09, lda_subjnorm 80.13, within_lda 88.22.

Predictions against the data:

- **PR-1.** Holds. No subject has `lda - within_lda > +2 SE_D` in common or all; cohort Mean within >= lda in both (90.79 vs 87.61; 88.99 vs 86.34). Strict gain of within over lda in common: S01 (-2.74), S02 (-2.56), S05 (-2.68), as expected; S03 (-1.26) and S04 (-0.76) tie, as expected. In all: S02 strict (-3.00); S01 (-1.81), S03, S04, S05 tie.
- **PR-2.** Holds, with a margin of 0.11 SE_D at the edge. No subject with `lda_subjnorm - lda < -2 SE_D` in common or all; the smallest value is all S05 = -1.89 SE_D (a tie, not refuted). Cohort Mean subjnorm >= lda in both (90.03 vs 87.61; 88.75 vs 86.34). Strict gain for S01 (+2.30, +2.26) and S02 (+3.06, +3.59); ties for S03-S05.
- **PR-3.** Reported, no direction predicted. `within_lda - lda_subjnorm` in common: S01 +0.44, S02 -0.50, S03 +1.67, S04 +0.33, S05 +2.68 SE_D. In all: -0.45, -0.59, +1.10, 0.00, +3.16 SE_D. Whole-session normalization closes the within-LOSO gap (|difference| <= 2 SE_D) for S01-S04 in both runs; for S05 within exceeds subjnorm strictly (+2.68 common, +3.16 all) and S05's `lda_subjnorm` is the subject where normalization does not help.

## Warm-up per subject and cohort (data source as above; record per R-16)

From `reports/loso_warmup/summary.csv` (accuracy % unsmoothed on windows after the warm-up trials; SE in pp; common channels).

| Subject | K | Warm-up windows | classes | span (s) | scored | full | warmup | none | warmup - full | z_wf (SE_D) | warmup - none | z_wn (SE_D) | full - none | z_fn (SE_D) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| S01 | 1 | 17 | 1 | 5.0 | 663 | 74.96 | 28.81 | 70.14 | -46.15 | -18.97 | -41.33 | -16.51 | +4.82 | +1.97 |
| S01 | 2 | 34 | 1 | 20.03 | 646 | 74.92 | 57.43 | 70.43 | -17.49 | -6.74 | -13.00 | -4.90 | +4.49 | +1.81 |
| S01 | 5 | 85 | 4 | 65.03 | 595 | 73.11 | 71.60 | 68.91 | -1.51 | -0.58 | +2.69 | +1.01 | +4.20 | +1.60 |
| S01 | 10 | 170 | 5 | 140.03 | 510 | 73.33 | 72.75 | 69.22 | -0.58 | -0.21 | +3.53 | +1.24 | +4.11 | +1.45 |
| S02 | 1 | 17 | 1 | 5.0 | 627 | 83.25 | 74.80 | 76.24 | -8.45 | -3.70 | -1.44 | -0.59 | +7.01 | +3.10 |
| S02 | 2 | 34 | 2 | 19.97 | 610 | 82.95 | 65.90 | 75.90 | -17.05 | -6.96 | -10.00 | -3.87 | +7.05 | +3.06 |
| S02 | 5 | 85 | 3 | 80.0 | 559 | 85.87 | 79.43 | 77.82 | -6.44 | -2.86 | +1.61 | +0.66 | +8.05 | +3.51 |
| S02 | 10 | 156 | 5 | 155.0 | 488 | 87.09 | 87.09 | 78.89 | 0.00 | 0.00 | +8.20 | +3.42 | +8.20 | +3.42 |
| S03 | 1 | 9 | 1 | 4.5 | 652 | 95.55 | 63.04 | 96.01 | -32.51 | -15.81 | -32.97 | -16.16 | -0.46 | -0.41 |
| S03 | 2 | 26 | 2 | 19.5 | 635 | 95.43 | 64.41 | 95.91 | -31.02 | -14.96 | -31.50 | -15.31 | -0.48 | -0.42 |
| S03 | 5 | 77 | 5 | 64.53 | 584 | 95.55 | 96.06 | 96.06 | +0.51 | +0.44 | 0.00 | 0.00 | -0.51 | -0.44 |
| S03 | 10 | 162 | 5 | 139.53 | 499 | 95.39 | 93.79 | 95.99 | -1.60 | -1.12 | -2.20 | -1.58 | -0.60 | -0.47 |
| S04 | 1 | 3 | 1 | 1.5 | 662 | 99.70 | 63.44 | 99.55 | -36.26 | -19.27 | -36.11 | -19.13 | +0.15 | +0.45 |
| S04 | 2 | 20 | 2 | 16.5 | 645 | 99.69 | 79.53 | 99.53 | -20.16 | -12.56 | -20.00 | -12.40 | +0.16 | +0.46 |
| S04 | 5 | 71 | 4 | 61.5 | 594 | 99.66 | 90.74 | 99.49 | -8.92 | -7.35 | -8.75 | -7.14 | +0.17 | +0.45 |
| S04 | 10 | 156 | 5 | 136.53 | 509 | 99.61 | 99.61 | 99.41 | 0.00 | 0.00 | +0.20 | +0.45 | +0.20 | +0.45 |
| S05 | 1 | 17 | 1 | 5.0 | 662 | 97.43 | 84.44 | 97.73 | -12.99 | -8.46 | -13.29 | -8.72 | -0.30 | -0.36 |
| S05 | 2 | 34 | 1 | 20.0 | 645 | 97.67 | 87.60 | 97.83 | -10.07 | -7.05 | -10.23 | -7.21 | -0.16 | -0.20 |
| S05 | 5 | 85 | 2 | 65.0 | 594 | 97.64 | 86.70 | 97.81 | -10.94 | -7.19 | -11.11 | -7.34 | -0.17 | -0.20 |
| S05 | 10 | 170 | 5 | 140.03 | 509 | 98.04 | 95.68 | 97.45 | -2.36 | -2.16 | -1.77 | -1.55 | +0.59 | +0.63 |

Cohort (`reports/loso_warmup/cohort.csv`, 5 subjects; values are across-subject means and SDs):

| K | full | warmup | none | warmup - full (mean, SD) | warmup - none (mean, SD) | warm-up windows (mean) | span s (mean) |
|---|---|---|---|---|---|---|---|
| 1 | 90.18 | 62.91 | 87.93 | -27.27 (15.99) | -25.03 (16.92) | 12.6 | 4.2 |
| 2 | 90.13 | 70.97 | 87.92 | -19.16 (7.61) | -16.95 (9.08) | 29.6 | 19.2 |
| 5 | 90.37 | 84.91 | 88.02 | -5.46 (4.85) | -3.11 (6.35) | 80.6 | 67.2 |
| 10 | 90.69 | 89.78 | 88.19 | -0.91 (1.04) | +1.59 (4.33) | 162.8 | 142.2 |

The `Std guard` column reads `none` in all 20 subject rows (every warm-up has at least 2 windows, minimum 3 for S04 K=1; no feature std below the floor).

Predictions against the data:

- **PR-4.** Holds. Cohort Mean |warmup - full| over K = 1, 2, 5, 10: 27.27, 19.16, 5.66, 0.91 (non-increasing; computed from the per-subject rows, `analysis.txt`). At K = 10 the means satisfy none 88.19 <= warmup 89.78 <= full 90.69.
- **PR-5.** Holds. At K = 10, |warmup - full| <= 2 SE_D for 4 of 5 subjects (S01 -0.21, S02 0.00, S03 -1.12, S04 0.00); the exception is S05 (-2.16 SE_D), as predicted (5 classes in its first 10 trials, 2 in its first 5; the K = 10 value in the summary is 5). No per-subject monotonicity in K is claimed: S02 warmup - full is -3.70, -6.96, -2.86, 0.00 SE_D for K = 1, 2, 5, 10, and S05 is -8.46, -7.05, -7.19, -2.16.
- **PR-6.** Holds. At K = 1, warmup < none by more than 2 SE_D in 4 of 5 subjects (S02 tie, -0.59); at K = 2 in 5 of 5 (needed 3). Mechanism to state (reviewer): a 1-2 class warm-up mean shifts every feature toward those classes; classes seen at K = 1 is 1 in all subjects and at K = 2 is 1-2.
- **PR-7.** Holds. `full - none` on the post-K windows has the sign of `lda_subjnorm - lda` on all windows where |Delta| > 2 SE_D: S01 all-window +5.59 pp vs post-K +4.82, +4.49, +4.20, +4.11; S02 +6.83 pp vs +7.01, +7.05, +8.05, +8.20 (both positive for every K). S03-S05 are ties in both (|z_fn| < 1).

## Numbers in the handoffs vs logs

Every number in `05_run.md` is from `reports/logs/P22/*` (pytest log and time file, hash files, command logs, `ls -l --time-style` mtimes for start times). Every number above is from `analysis.txt`, the summary CSVs or `cohort.csv` of the out-dirs. Mean `|warmup - full|` per K (27.27, 19.16, 5.66, 0.91) is the `absd` column of `analysis.txt`; the cohort Mean of `warmup - full` per K in the CSV (-27.27, -19.16, -5.46, -0.91) differs at K = 5 only because the mean of absolute values includes S03's +0.51.

## Sources spot-check

Opened: `mas/state/phases/P22-loso-extensions/02_plan.md` (run commands, additions) and `07_review.md` (round 2 PASS, PR/V list): the V1..V11 and PR-1..PR-7 above are applied as written there. `03_changes_ml-engineer.md` claims the recording order comes from `window_starts` and differs from id order on the real folders (S01 recording ids 88, 89, 96, 104, 80, 112): `recording_order.csv` and `warmup_cmd5.log` show exactly that sequence. The builder's smoke times (31.4 s, 36.2 s, 10.7 s, 6.7 s) and the verifier's (23.79 s, 29.47 s, 8.82 s, 5.79 s) are of the same order. The builder's smoke head and dirty flag differ from the verifier's (V10) with identical numbers.

## Reference consultations check

`03_changes_ml-engineer.md` lists no R11 consultation, `04_tests.md` none. `mas/state/scratch/reference_access.log` has 42 lines, the same count as at the reviewer's round 2 and the last entry dated 2026-10-28T07:41:21 (scribe, P19); no line is dated after the P22 branch work (`awk` on the timestamp field: 0 lines at or after 2026-10-28T08). The verifier did not open the answer-key folder (a guard block on a command that merely mentioned the symlink, and the worktree link was not read). No unlisted access: OK.

## Privacy scan

Scanned with the term pattern of the repository guard hook (loaded by import from the hook script, terms not printed), on `05_run.md`, `06_verify.md` and the commit messages. Result: 0 matches in each. Clean.


## Reasons (if FAIL)

None.
