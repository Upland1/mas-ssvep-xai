# P07 · 04 · Tests

Status: READY
Author: synthetic-tester
Reads: 02_plan.md, 03_changes_data-signal.md, 03_changes_ml-engineer.md, mas/RULES.md, mas/05_PITFALLS.md PF-05..PF-10

## Tests added

File: NEW `tests/test_p07_known_answer.py` (8 tests, about 3 s). Extends, does not replace, the builders' `tests/test_p07_quality_signal.py` (13) and `tests/test_p07_ml_engineer.py` (14), which already cover: 5/10 vs 6/10 tier-1 boundary, analytic channel stats, return dict and `channels_kept_idx`, `precomputed` reuse, `resolve_channel_names` 8/7/6/9, PF-07 pinned default, chronic-noise drop end to end, extractor arity and shared decision, PSD columns by name after a drop, benchmark schema/parallel equality, consumer scripts on trees.

| Test id | Simulates | Expected | Tolerance | Source | Catches bug | Result |
|---|---|---|---|---|---|---|
| `test_tier1_boundary_at_100_windows` | 100 windows; PO4 fails in 50, O1 in 51, PO3 in 49 | only O1 dropped; fail fractions 0.50 / 0.51 | exact | roadmap P07.1 | `>=` instead of `>` (mutant) | PASS |
| `test_tier2_ignores_bad_samples_on_dropped_channel_only` | PO8 bad in all windows (dropped); one bad window on kept Oz | mask all 1 except window 4 | exact | roadmap P07.1 | tier 2 judging a dropped channel (mutant) | PASS |
| `test_config_restores_po7_in_montage_order` | `configs/pipeline_config.yaml`, `resolve_channel_names` 8/7/0/1 | scalp = 8-name montage, excluded `[]`; 7 = without PO7 in order; else None | exact | roadmap P07.3, PF-05 | wrong mapping (mutant: 7 drops O2) | PASS |
| `test_every_extractor_call_unpacks_four_values` | AST scan of `src/`, `scripts/` for the three extractors | every assignment has exactly 4 targets (at least 3 sites seen) | exact | roadmap P07.2, PF-08 | consumer unpacking 3 values (mutant in visualize_data) | PASS |
| `test_blocks_share_one_gate_decision` | `prepare_subject` on a tree with POz noisy, spy on the pipeline | exactly 1 call without `precomputed`, later calls reuse | exact | PF-10 | blocks gated separately (mutant: `quality_gate` drops `precomputed`) | PASS |
| `test_summarize_window_quality_sees_rejected_windows` | tiny recording with a 400 uV spike trial, `--no-channel-drop` | log summary Vpp max >= 400, rejected > 0; saved windows Vpp < 200 | exact bounds | P02 carry-forward | summary fed gated windows (mutant) | PASS |
| `test_visualize_runs_on_8_channel_tree` | 8-channel legacy-layout folder | exit 0 | exact | PF-08, PF-05 | 3-value unpack (mutant) | PASS |
| `test_n_subjects_csv_rows_and_mean_blank_cells` | 8-channel subject (PO7, PO8 noisy) + 7-channel subject | rows S01, S02, Mean; kept 6 / 7; dropped `PO7 PO8` / `none`; clean + rejected = 50; Mean has blank non-accuracy cells; accuracies in [0, 100] | exact | roadmap P07.6, 02_REQUIREMENTS section 6 | blank dropped column (mutant) | PASS |

Mutants were run on throw-away copies of the repository (scratchpad, not committed), applying one edit each to a copy of `src/` / `scripts/` and running the P07 test files; every mutant fails at least one test:

| Mutant | First failing test |
|---|---|
| tier 1 `>=` | `test_tier1_boundary_at_100_windows` |
| tier 2 on all channels | `test_tier2_ignores_bad_samples_on_dropped_channel_only` |
| positional kept channels (`[:, :len(kept)]`) | builders' `test_tier2_judges_only_surviving_channels_and_dict_layout` |
| `precomputed` ignored in the pipeline | builders' `test_precomputed_decision_is_reused_for_another_block` |
| `quality_gate` drops `precomputed` (extractors gated separately) | `test_blocks_share_one_gate_decision` |
| `LEGACY_VPP_MIN_UV = 5.0` in `run_preprocessing` | builders' `test_pf07_pinned_default_and_regression_flag` |
| 7-channel mapping removes O2 instead of PO7 | `test_config_restores_po7_in_montage_order` |
| summary fed the gated array | `test_summarize_window_quality_sees_rejected_windows` |
| `visualize_data` unpacks 3 values | `test_every_extractor_call_unpacks_four_values`, `test_visualize_runs_on_8_channel_tree` |
| CSV `Channels Dropped` left empty | `test_n_subjects_csv_rows_and_mean_blank_cells` |

## Command

```bash
.venv/bin/python -m pytest tests -o addopts="" -q -p no:cacheprovider
```

## Output summary

Summary line verbatim: `493 passed, 10 warnings in 223.90s (0:03:43)`. Before my file: 485 passed in 227 s (ml-engineer); my 8 tests add about 3 s. No bugs found.

## Coverage gaps

- `benchmark_cross_validation` and `test_sklearn_models` (full model suites) are exercised by the existing P05 tests on clean 7-channel trees only; not re-run on a tree with a dropped channel because each takes tens of seconds (runtime budget). Their extractor calls go through `build_feature_blocks`, covered with drops by the builders' tests and by the AST arity scan.
- Real-data effect of the gate on S01-S05 (R-6 counts) is unmeasured here; verifier.
- The PF-07 "all 320 windows of S03" reproduction needs real data; synthetic proxy only (low-amplitude recording, builders' test).

## Reference consultations (R11)

None.

## Sources

1. `mas/state/phases/P07-two-tier-quality/02_plan.md` Tests required; `mas/03_ROADMAP.md` P07 tasks 1-6; `mas/02_REQUIREMENTS.md` section 6; `mas/05_PITFALLS.md` PF-05..PF-10 (opened in this run).

## Questions
