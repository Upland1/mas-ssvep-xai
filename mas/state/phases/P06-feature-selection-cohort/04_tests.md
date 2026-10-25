# P06 · 04 · Tests

Status: READY
Author: synthetic-tester
Reads: 02_plan.md, 03_changes_ml-engineer.md, mas/RULES.md, mas/05_PITFALLS.md (PF-11), mas/04_REFERENCE_RESULTS.md R-4/R-5

## Tests added

File: NEW `tests/test_p06_known_answer.py` (16 tests, ~45 s). Synthetic only (`tests/p05_synth.py`), fs 250. Mutants are injected by monkeypatch inside the tests and the same assertions are shown to reject them.

| Test id | Simulates | Expected | Tolerance | Source | Catches bug | Result |
|---|---|---|---|---|---|---|
| `test_anova_ranking_matches_scipy_f_oneway` | 50 columns, 7 (strength 2) and 31 (1) planted | top-k = k largest `scipy.stats.f_oneway` F; k=1 -> [7] | exact | analytic | wrong score/order | PASS |
| `test_mi_ranks_strong_planted_first` | same | k=1 [7]; k=2 [7, 31] | exact | analytic | MI ranking | PASS |
| `test_mi_seed_passed_and_deterministic` | noise, 2 calls | identical; `mutual_info_classif` gets `random_state=42` (7 if asked); seed-dropping mutant fails the kwargs check | exact | plan (seeded MI) | unseeded MI (note: jitter ~1e-10 so selections rarely change, the seed itself is asserted) | PASS |
| `test_columns_returned_are_input_columns_...` (x2) | planted 0 and 49 | [0, 49] | exact | analytic | index offset | PASS |
| `test_sfs_infold_only` | column informative only in test rows | SFS(k=1) on train rows excludes it, on all rows picks [3] | exact | PF-11 | SFS fitted on all windows | PASS |
| `test_sfs_count_and_cca_tail_via_column_sets` | 55-col training matrix | p = 55, 45, 11, 11, 9; tail 50..54 last; selected < 50; ANOVA has 7, 31; SFS has 7 | exact | R-4 arithmetic | FBCCA not appended, selection touching tail | PASS |
| `test_ablation_rejects_selection_on_all_windows` | spy on ANOVA/MI/SFS inside `run_ablation` | 15 calls, each 80 rows; mutant (`legacy_cv` returns all rows as training) gives 100 rows | exact | PF-11 | ANOVA, MI and SFS fitted on all windows | PASS (mutant rejected) |
| `test_pruning_exact_columns_and_wrong_band_mutants` | `column_sets` on 55 cols | pruned = 0..39 + 50..54 (45); first-band / one-column-per-band sets differ | exact | R6 | wrong band, class-major | PASS |
| `test_band_major_layout_against_transformer` (x3: bands 0, 2, 4) | content of band b replaced by another band's before `FBCSPTransformer` | changed columns non-empty and within 10b..10b+9 | exact | R6, P05 layout | band-major vs other layout | PASS |
| `test_p_values_55_45_25_25_20_and_tail_mutant` | `run_ablation` k=20, sfs 15 (SFS selector stubbed for speed), and real SFS with k=4, sfs=2 | p = 55,45,25,25,20 and 55,45,9,9,7; ANOVA row without tail gives p != 25 | exact | R-4 | wrong p, FBCCA not appended | PASS |
| `test_full_row_equals_flagship_on_hard_tree_and_smoothing_is_mod5` | low-SNR tree (Full 1.0 s < 95 %) | Full row == `flagship_S03.csv` row (both accuracies); 2.0 s equals independent i % 5 smoothing of the captured scores; no-reset smoothing differs on this tree | exact | decisions.md P05, PF-02 | smoothing without reset, Full != flagship | PASS |
| `test_with_mean_row_known_numbers` | 3 rows (R-5 S01-S03 values) | Mean 67.97 / 73.2 | exact | hand arithmetic | wrong Mean | PASS |
| `test_cohort_csv_from_script_and_checker_rejects_mutants` | script on S10, S02, S03 | columns of 02_REQUIREMENTS §6, order S02, S03, S10, Mean = mean of rows, Mean counts blank, rows 100/0; checker rejects renamed column, median Mean, missing Mean, wrong order | exact | [1] §6 | wrong columns / Mean | PASS |

## Command

```bash
python -m pytest tests/ -o addopts="" -q
```

## Output summary

Full suite: `455 passed, 10 warnings in 274.37s (0:04:34)`. The new file alone: `16 passed in 45.21s`. No bug found in the builder's code.

## Coverage gaps

- The builder's `test_band_major_layout_matches_fbcsp_transformer` is vacuous: it scales band 5 by 10, but the CSP covariance is normalised, so no column changes and `changed <= set(range(40, 50))` holds for the empty set. My parametrised replacement test (content swap, non-empty `changed`) covers the layout. Not a code bug.
- The real 15-step SFS is not run inside the p-value test (about 90 s); its count 15 is covered by the builder's `test_sfs_selects_planted_columns_and_count` and the exact R-4 p by the stubbed run.
- MI seeding cannot be shown by behaviour (jitter too small); asserted through the kwarg.
- R-4 / R-5 numbers on real data are the verifier's job. Suite time (275 s) exceeds the nominal minute; P05 already recorded this.
