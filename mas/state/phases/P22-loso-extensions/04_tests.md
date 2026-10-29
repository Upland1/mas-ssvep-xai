# P22 · 04 · Tests — synthetic-tester

Status: READY
Author: synthetic-tester
Branch: phase/P22-loso-extensions

## Files

| Path | State |
|---|---|
| `tests/test_p22_independent_known_answer.py` | NEW (30 tests, ~6 s) |

No change to `src/`, `scripts/`, `configs/`. Expected values are computed inside the tests (numpy, bare sklearn, git), not with the functions under test.

## Tests and known answers

| Test | Known answer |
|---|---|
| `test_within_lda_matches_independent_grouped_cv_on_planted_subject` | probabilities of `within_lda_fold` equal a hand-built grouped CV (manual z-score + bare LDA lsqr/auto) per repeat, atol 1e-6; repeats use seeds 42+r (different partitions) |
| `test_within_folds_never_split_a_trial_...` | 5 seeds, 7 overlapping windows per trial: no trial id on both sides, each window tested once, test sets are whole trials; a window-level `StratifiedKFold` does share trials on the same data |
| `test_within_lda_uses_exactly_the_loso_channels_...` | CLI with names `Oz O1 POz` (non-montage order): `lda` and `within_lda` fold configs carry that list; stored `proba_rep` equals an independent recomputation on `load_subject(channels=names)`, and differs (log-probabilities) from one on `[O1, Oz]` |
| `test_explicit_names_leave_out_...` | planted gate drop of Oz in S01: printed `Leaving out S01: gate dropped Oz`, cohort S02-S04; unnamed channel keeps S01; unknown name `XX9` exits naming it, no output; Oz dropped in 3 of 4 subjects: exit "2 subjects"; parse_channels rejects mixing, duplicates, empty |
| `test_leave_out_pure_function_planted` | S02 lacks PO8, S03 lacks PO8+O2: names O2 PO8 Oz leave out exactly S02 {PO8} and S03 {O2, PO8} |
| `test_check_fold_refuses_each_key_but_not_data_root[key]` (13 keys) | each config key changed: SystemExit "use a new --out-dir" naming the key; identical and moved `data_root` accepted; `test_alt_covers_every_config_key` guards coverage |
| `test_check_fold_head_rules` | temp git repo: docs/reports-only head change accepted (both directions); scripts-only, src-only, and combined changes refused; unresolvable head (either side) refused; same head dirty vs clean refused |
| `test_fold_count_guard_cohort_rows_and_end_to_end` | one `lda` fold deleted: `[warn] ... 2 fold files for a cohort of 3`, `lda` Mean NaN, Folds 2, INCOMPLETE, per_subject Mean NaN; complete `fbcca` keeps its Mean; `partial_mean=True` gives the mean of the 2 present |
| `test_recording_order_planted_layout_differs_from_id_order` | order [4,1,7,0,5,2,6,3], rows shuffled: ids and first starts as planted; first-K sets for K = 1,3,5,8 |
| `test_warmup_stats_exact_values_and_std_guards` | mean/std (ddof 0) exact; 1 row: std 1, z = 0; 2 identical rows: all 5 features floored, finite output |
| `test_binomial_se_values` | 0.5/100 -> 5.0; 0.9/400 -> 1.5; 0.2/25 -> 8.0; 0 and 1 -> 0; n = 0 -> NaN |
| `test_first_k_stats_are_those_of_the_first_recorded_trials_...` | stats equal moments of the first K recorded trials (not id-order set); permuting held-out labels leaves stats and probabilities bit-identical; scaling every post-K window (features verified to move) leaves the K = 3 stats unchanged |
| `test_k_equal_all_trials_gives_warmup_equal_full_and_none_differs` | K = all: warmup == full (atol 1e-10); `none` differs on the gain-shifted subject |
| `test_warmup_recovers_toward_full_as_k_grows_...` | 4 recording orders, same scored windows: full > none by 0.15, warmup K=15 > K=1 by 0.10, K=15 > none by 0.10, K=15 within 0.08 of full |
| `test_k_row_scores_only_post_k_windows_with_counts` | warm-up + scored windows = all; accuracies recomputed independently on post-K windows; `warmup - full` column |

## Mutation checks (temporary copy under the session scratchpad; tree never modified)

17 of 18 mutants killed on the new file alone.

| Mutant | Result |
|---|---|
| id order instead of recording order (`np.arange`) | KILLED (recording order test) |
| warm-up stats from all held-out windows | KILLED (first-K / post-K test) |
| warm-up includes first post-K trial (`ids[:k+1]`) | KILLED |
| 1-window std guard returns 0 | KILLED |
| SE uses `acc*acc` | KILLED |
| within seeds not `+r` | KILLED (channels/independent test) |
| within splitter with window-level groups | KILLED (independent CV test) |
| within_lda config channels reversed | KILLED |
| `check_fold` ignores `seed` / `channels` | KILLED (both) |
| head check ignores src / ignores scripts | KILLED (both) |
| unresolvable head accepted | KILLED |
| names keep every subject | KILLED |
| names: no < 2 error | KILLED |
| fold-count guard off | KILLED |
| `k_row` scores warm-up windows too | KILLED |
| warm-up stats use labels | not testable as a mutant: `warmup_stats` and `warmup_probas` take no test labels. Covered by the signature (builder test) and by the label-permutation invariance test, which would fail if labels reached the stats. My attempted mutant was a no-op (equivalent), so it "survived"; it is not counted as a kill. |

## Gaps

- Label use in the warm-up statistics is only checked behaviourally (permutation invariance), as the mutant would need a new argument.
- Real S01-S05 folders are not touched (no raw data access); the recording order on real data relies on the builder's `recording_order.csv` and the verifier.
- Gain-recovery test is statistical (4 orders, margins 0.08-0.15), deterministic by seeds.
- `configs/` changes between heads are accepted by design (CODE_PATHS = src, scripts); not tested.

## Full suite (alone)

SUITE_PLACEHOLDER
