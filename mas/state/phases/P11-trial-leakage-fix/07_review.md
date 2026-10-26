# P11 · 07 · Scientific review

Status: READY (pre-run audit, Round 1: FAIL; Round 2: PASS)
Author: scientific-reviewer
Reads: 00, 02, 03_changes_ml-engineer.md (incl. "Round 1 orchestrator change"), 03_changes_deep-learning.md, 04, decisions.md P05/P10/P11 rows, mas/RULES.md, mas/03_ROADMAP.md P11 and "Conventions", mas/02_REQUIREMENTS.md §5.6, mas/01_DATA_SPEC.md §5.1, mas/04_REFERENCE_RESULTS.md (tolerances, R-3–R-9), mas/05_PITFALLS.md PF-01–04, PF-28–31, `git diff 829602c..HEAD -- src scripts tests` (branch head e86ae3f)

## Pre-run audit, Round 1

Verdict: FAIL (one code fix, small; everything else is ready to run)

Suite at e86ae3f (`.venv/bin/python -m pytest tests -o addopts="" -q -p no:cacheprovider`): `676 passed, 21 warnings in 349.48s (0:05:49)`. This equals the tester's 676/21. The runtime of nearly 6 min exceeds the "about a minute" target, as in P10 (noted, not blocking).

| Rule | Result | Evidence (`path:line`) |
|---|---|---|
| R1 Trial-grouped CV | PASS | Every split of the nine scripts goes through `cv_utils.make_splits` (`src/preprocessing/dataset/cv_utils.py:102`): classical through `legacy_eval.splits_for` into `oof_space(..., splits)` (`benchmark_n_subjects.py:111-112`, `benchmark_cross_validation.py:90`, `benchmark_feature_selection.py:149`, `benchmark_harmonic_fbcca.py:104-105`, `evaluate_confusion_matrix.py:159-160`); networks through `train_and_eval_cv` (`src/models/cnn/eegnet_cv.py:117-119`, which also asserts no shared id). Inner split: SFS inner CV is `StratifiedGroupKFold` over the training-fold ids (`benchmark_feature_selection.py:112-132,153`). No other inner split exists (networks: fixed 150 epochs, no validation split; P10 meta). Splitter scan over `src scripts` (StratifiedKFold, KFold, train_test_split, cross_val_*, cv=int): the remaining window-level splitters are the legacy path (`legacy_eval.py:67-69`), the labelled `--sfs-diagnostics` variants (`benchmark_feature_selection.py:211`), and the frozen scripts outside the nine (`train_models.py`, `spatial_spectral_cnn.py`, `benchmark_5_subjects.py`, `test_sklearn_models.py`), which the plan scopes out. The tester's class-level spies (04 table, M1 catches 13 tests) see every split of the nine. CONCERN N1 below: `oof_space(splits=None)` still defaults to the leaky splitter. |
| R2 Fit only in-fold | PASS | The code that builds the fold matrices is unchanged (`fold_matrices`, `oof_space` loop). Only the split indices passed in change. SFS/ANOVA/MI see `Xtr` only (`benchmark_feature_selection.py:149-153`). Networks: z-score is per window, augmentation is on the training fold only, N4 tested (`tests/test_p11_networks.py:112`). The P05/P06 spy tests still pass. |
| R3 Filter continuous, then window | LEGACY (by design) | Per-window sub-band filtering is unchanged and labelled in every header ("per-window sub-band filtering (R3/PF-14)"); enforced from P16. |
| R4 Estimator small-sample bias | N/A | No coherence/PLV estimator. |
| R5 Shared quality decision | LEGACY (by design) | P07 per-script two-tier gate, thresholds printed in each meta (vpp 5–120, std 1–35, > 50 %); decisions.md row 98. |
| R6 Index layouts verified | PASS | Ids are built on the full `y_labels.npy`, then the stimulus rows are selected, then the gate mask is applied (`benchmark_runner.py:84-92`, `benchmark_common.py:93-97`). Window content that encodes its trial id survives two gate drops (`test_window_content_encodes_its_trial_id_after_the_gate`). The chained-mask and whole-trial-gap cases are covered. 01_DATA_SPEC §5.1 ("each condition's windows in time order") makes consecutive chunks of 5 the true trial layout. Pre-gate vs post-gate ids are separated by M2 (11 failing tests). |
| R7 Honest statistics | N/A | No permutation statistics in P11. |
| R8 Smoothing respects trials | PASS, with the condition C1 | Reported rule on legacy folders = `i % 5` of the clean array (default `--smoothing mod5`, `benchmark_runner.py:46`). Trial reset is the PF-02 diagnostic (`smoothing.py:41`, exact by hand-checked tests, M3 caught). Assessment of the decision in "R8 decision audit" below: sound, incompletely cited, chronology not stated explicitly. |
| R9 Per-subject reporting with data source | PASS | Per-subject rows, mean row, data-source line, `trial_ids_approximate subjects:` and splitter/rule lines in every meta (verified on my grouped A/B smoke meta). Demo meta names the leaky, grouped and diagnostic rules. |
| R10 Every change and test cites a source that exists and says what is claimed | PASS | Handoffs cite the roadmap, R1/R8, PF-01–03, PF-28 and decisions.md rows. I opened them: they say what is claimed. Exception: the R8 decision row cites R8 text only, see C1. |
| R10 Copied lines marked, license compatible | N/A | No external code. |
| R11 Reference consulted only after an attempt, every consultation listed | PASS | Both builders and the tester declare none. `mas/state/scratch/reference_access.log` has no entry after my own P10 privacy scan (2026-10-26T00:25:42). No P11 consultation. |
| Golden rule 3: legacy labelled and reachable | PASS | `--cv legacy --smoothing mod5` writes under `legacy_leaky/` (`cv_utils.py:129`). I checked byte-identity myself against the **unmodified** 829602c (`git archive 829602c` into scratch, same synthetic tree as `tests/test_p11_cv.py:289-299`): 7 of 8 classical pins match exactly (n_subjects, flagship_S03, ablation, harmonic report, 3 confusion-matrix reports). The 8th, `feature_space_benchmark_S03.csv`, cannot match unmodified 829602c by construction (saga seeding, Deviation 1; the pin was made on a patched 829602c, as the handoff says). Compact-CNN A/B on a 2-subject synthetic tree, 2 epochs, CPU: unmodified 829602c and branch `--cv legacy --smoothing mod5` both give sha256 `8f16e9ee…e002`, which equals the DL handoff pin. The frozen P10 CSVs are unchanged. sha256 now: eegnet `0efbaaba…c367`, compact_cnn `ad98d5d6…4665`, shallow_conv_net `7a2407fb…5f74`. |
| Tests cover every change; at least one fails on the historical bug | PASS | PF-01: planted-fingerprint leak, every-script spies, M1. PF-03: pre-gate ids, M2. PF-02: trial-smoothing hand cases, M3. Inner CV: M4. Trial length: M5. N4: dataset length = fold, seeded generator both arms. Gap: the demo network section has no test of its input provenance (required fix 1). Gap: the network legacy pins live only in the handoff, not in a test (N3). |
| Changes match 02_plan.md and the roadmap tasks | PASS, except required fix 1 | P11.1–P11.4 implemented. Changed relative to the plan: settled point 1 (decision row 103), extra `cv_leakage_demo_networks.csv`, saga seeding, `--freeze-legacy` semantics. Each is assessed below. |
| No data, `.ebr`, local tooling files or tool/vendor names in the diff | PASS | `git diff --name-only 829602c..HEAD`: no data, tooling or answer-key paths. Vendor/trailer scan (word-bounded) over the diff, the branch commit messages and the P11 phase folder: 0 hits. The loose pattern's only hits are the word "clause". Legacy arrays: `sha256sum data/processed/S0*/*.npy data/processed/*.npy` prefixes are identical to P07 D0 (S01 45a9b033/241adcdc/1846c4e5 … S05 9400ebfd/d41793f3/1846c4e5; root = S03). |

### Required fixes

1. **Stale-result reuse in the demo's network section** (R9 and PF-01 interpretation; bug-history item "result caches reused under a different configuration"). Owner: **ml-engineer**. `scripts/diagnostics/demo_cv_leakage.py:113-130` pairs `reports/legacy_leaky/augmentation_ab_<model>.csv` with `reports/augmentation_ab_<model>.csv` by file name only. Today the second path holds the **leaky P10 files**: `cmp` shows that all three are byte-identical to the frozen copies, and their meta reads `StratifiedKFold(5, shuffle, 42) over windows`. The plan's run order runs the demo (step 1) **before** the A/B runs. That first run will therefore print, and write to `reports/cv_leakage_demo_networks.csv`, a table titled "frozen P10 leaky vs P11 grouped" in which every delta is 0.00. Reproduced in a smoke run on scratch copies: EEGNet Mean 63.93 → 63.93, Delta 0.0; Compact-CNN S04 53.30 → 53.30. Step 2 would overwrite the file, but the step-1 log stays wrong. Any demo run after a crashed or partial A/B run would silently report leaky numbers as grouped. Fix: before using a pair, read each CSV's `.meta.txt`. The "before" file must contain `CV_LABEL` (window-level) and the "after" file `GROUPED_CV_LABEL`; otherwise skip the pair with a printed reason. Add a test in which a leaky file sits in the P11 slot and the network section skips it. Do not change the run order. No change to any number-producing path.

### Non-blocking notes

- N1 (R1, CONCERN): `legacy_eval.oof_space(..., splits=None)` still falls back to the window-level splitter (`src/models/classical/legacy_eval.py:128-129`). The nine scripts always pass `splits`, and the frozen scripts rely on the fallback. Deviation 2 ("a new caller is leak-free by default") therefore does not hold for this function. Next touch: make `splits` required, or default to raising, with the frozen scripts passing `splits_for("legacy", ...)` explicitly.
- N2 (labels): in grouped runs `evaluate_confusion_matrix.py:112` names the trial rule "trial-aware smoothing, R8" and the mod5 rule "R8 legacy, PF-02". The meta lines elsewhere say the reverse (mod5 = R8 legacy-folder clause, trial = PF-02 diagnostic). The REPORTED/DIAGNOSTIC tags are correct. Align the wording at the next touch.
- N3 (regression coverage): the network legacy sha256 pins (03_changes_deep-learning.md table) are not asserted by any test. Only the P09 EEGNet pins are. Carry forward: put the five pins in `tests/test_p11_networks.py` (deep-learning).
- N4 (PF-03 residual leak): on S02 (blocks 39 + 40) and S04 (38 + 40), the chunks after a lost window straddle two true trials. One window of true trial t+1 can sit in a different reconstructed id from its four siblings, so a small residual leak remains on those two subjects. This is inherent to legacy ids (PF-03) and goes away with true ids in P16. The write-up must say so next to their rows.
- N5 (saga seeding, Deviation 1): accepted. It touches no R-3, R-4, R-5 or R-6 number (all LDA). It can only move the LogReg L1/ElasticNet rows of `feature_space_benchmark_S03.csv`, which have no reference values. Check P5 below covers R-3's qualitative ranking. Frozen scripts that share `get_sklearn_model_suite` (`test_sklearn_models.py`) inherit it. The write-up states that.
- N6 (`--freeze-legacy`): accepted. With `--cv grouped` it is now a parser error, so a grouped file can never be frozen as legacy (`benchmark_nn_augmentation.py:106`). With `--cv legacy` it is redundant. A `--cv legacy` A/B re-run would rewrite the frozen P10 "before" files in place. The plan does not run it. If anyone does, the frozen hashes above must still match afterwards.
- N7 (library defaults): `cv="grouped"`, `smoothing="mod5"`, and `train_and_eval_cv` raising without ids are the right defaults (`tests/test_p11_networks.py:78`).

### R8 decision audit (settled point 1 → decision row 103)

- **Sound.** Three spec texts prescribe `i % 5` of the clean array as the 2.0 s rule on legacy folders:
  - the R8 rule text ("`i % 5` on legacy", `mas/RULES.md:74-77`);
  - `mas/02_REQUIREMENTS.md:179-183` §5.6 ("Legacy folders define 'first window of a trial' as `j % 5 == 0` on the clean array (a known approximation); built folders use true trial ids");
  - the roadmap "Conventions" line, which defines every phase's "smoothing" as §5.6 (`mas/03_ROADMAP.md:18-19`).

  PF-02's fix ("reset at the first window of each true trial, windows ordered by offset") is written for built folders. The text that conflicts is the era-matrix row (`mas/RULES.md:28`): it lists that same rule as the P05–P10 legacy behaviour, which suggests the rule ends at P11. The conflict was recorded **before any P11 number existed** (decisions.md row 58, P05, 2026-10-25). On legacy folders the trial-reset rule also rests on approximate ids (S02, S04), so it is not "true trial" smoothing either. Splitter and smoothing stay independent flags, and the demo prints both 2.0 s columns, so nothing is hidden.
- **Incompletely cited.** Row 103 cites only the R8 text. It omits §5.6 and the Conventions line (the stronger texts) and P05 row 58 (the pre-numbers record of the ambiguity). It also leaves the era-matrix row unreconciled.
- **Chronology not stated plainly.** 18a6792 (09:51:46) put the smoke numbers in the handoff: mod5 matches R-6 to 0.01 pp on all five subjects; trial gives S02 −2.55, S03 −3.56, mean 81.39. The correction followed in 31d6f8e (09:59:36) and 816afc3 (10:00:05). Row 103 calls those numbers "consistent but not the basis". It does not say that the plan's earlier choice (trial) was reversed **after** they were seen. Golden rule 5 requires that order to be explicit.

### Conditions for the results review (binding, not run blockers)

- **C1 (orchestrator, before the scribe writes the report):** append a decisions.md row, without editing row 103.
  - It states that settled point 1 was reversed after the ml-engineer's smoke numbers were known (commits and times above).
  - It cites §5.6, the Conventions line and P05 row 58 as the basis.
  - It records the era-matrix R8 wording as an open question for Sebastian: does "enforced from P11" mean "no cross-trial smoothing without reset (P04 rule)" on legacy folders, with the i%5 misalignment fixed only by true ids in P16?

  The P11 report must say, next to the R-6 table, that R-6's 2.0 s column is reproduced with the legacy-folder i%5 rule, and give the trial-reset diagnostic beside it. If C1 is missing at the results review, the verdict is REJECT.

### Results-review checks, committed before the run (they cannot be moved afterwards)

Window counts: S01 200, S02 196, S03 197, S04 197, S05 200 clean; rejected 0/3/3/1/0; 7 channels kept, none dropped (R-6). Any difference: REJECT.

**P1. Flagship = R-6** (`reports/n_subjects_benchmark.csv`, default flags; its meta must name `StratifiedGroupKFold` and the `2.0 s rule = legacy i%5` label). Tolerance: ±1.5 pp per subject, ±1.0 pp on the mean. Windows computed with `python3 -c` (k = round(v·n/100), interval [ceil((v−1.5)n/100), floor((v+1.5)n/100)]):

| Subject | 1.0 s target (k/n) | accepted k | 2.0 s target (k/n) | accepted k |
|---|---|---|---|---|
| S01 | 61.00 (122/200) | 119–125 | 67.50 (135/200) | 132–138 |
| S02 | 56.12 (110/196) | 108–112 | 61.73 (121/196) | 119–123 |
| S03 | 86.80 (171/197) | 169–173 | 90.36 (178/197) | 176–180 |
| S04 | 97.46 (192/197) | 190–194 | 97.97 (193/197) | 191–195 |
| S05 | 95.00 (190/200) | 187–193 | 95.50 (191/200) | 188–194 |
| Mean | 79.28 | 78.28–80.28 | 82.61 | 81.61–83.61 |

The trial-reset diagnostic (demo column) is reported next to the table and is never substituted for it. The builder's smoke run gave 81.39 for it, outside the range. That is expected and is not a FAIL. A deterministic pipeline that misses a window range is a FAIL. It is not explained by tolerance, and the results are not re-run with other flags.

**P2. Leak size (classical)**, from `reports/cv_leakage_demo.csv`. Its leaky columns must equal R-5 exactly (64.50/66.33/90.36/98.98/96.50; 75.50/71.94/95.43/98.48/96.50; means 83.33/87.57), because the code is deterministic and the pins match. Its grouped columns must equal `n_subjects_benchmark.csv` exactly. Mean Δ1.0 is checked against R-6's −4.05 and Δ2.0 against −4.96, ±1.0 pp each. Rounding: the demo subtracts rounded values, so differences of 0.01 are allowed.

**P3. Legacy reachable**, step 0. The table and rows below must be exact. Any difference is a regression, and the verdict is REJECT.

- `reports/legacy_leaky/n_subjects_benchmark.csv` = R-5 exactly.
- `reports/legacy_leaky/feature_selection_ablation_S03.csv`: Full 90.36/95.43, pruning 87.31/94.92, ANOVA 86.29/94.42, MI 87.82/93.40 (R-4), SFS 89.85/95.94 (D-1).
- `reports/legacy_leaky/feature_space_benchmark_S03.csv`: hybrid Shrinkage-LDA lsqr = 90.36/95.43 (R-3).

The saga rows (LogReg L1, ElasticNet) may differ from the P05 CSV. Report each difference. If a seeded saga row beats Shrinkage-LDA on the hybrid, record it as a seed-sensitivity note against R-3's qualitative ranking, not as a regression.

**P4. Augmentation A/B = R-9b** (`reports/augmentation_ab_<model>.csv`; each meta must name `StratifiedGroupKFold`, otherwise the file is not P11 output). Accepted ranges: per subject ±5 pp on 1.0 s OFF, 1.0 s ON, 2.0 s OFF and 2.0 s ON; cohort Mean ±3 pp on each column.

| Model | Mean 1.0 OFF / ON | Mean 2.0 OFF / ON | Mean Δ1.0 | Mean Δ2.0 |
|---|---|---|---|---|
| EEGNet | 61.22–67.22 / 63.24–69.24 | 64.56–70.56 / 65.77–71.77 | −0.99–5.01 | −1.78–4.22 |
| Compact-CNN | 33.80–39.80 / 50.96–56.96 | 38.23–44.23 / 54.69–60.69 | 14.16–20.16 | 13.46–19.46 |
| ShallowConvNet | 70.18–76.18 / 72.70–78.70 | 73.52–79.52 / 75.92–81.92 | −0.47–5.53 | −0.60–5.40 |

Per-subject ranges are R-9b's values ±5 (clipped to [0, 100]). Examples: Compact-CNN OFF S04 49.82–59.82, ON S04 92.97–100; EEGNet OFF S03 68.60–78.60.

- **Sign rule:** every Mean Δ (1.0 s and 2.0 s, three models) must be > 0, as in R-9b. A Mean Δ ≤ 0 is a sign flip and needs an explanation even if it is inside ±3. Without one, the verdict is REJECT.
- **Per-subject Δ:** these have no tolerance of their own. A per-subject Δ more than 5 pp from R-9b is listed and read against the P08 device and fold noise (about 5 pp), not gated.
- **R-7 cross-check:** ON 1.0 s against R-7, same ±5 per subject.

**P5. Roadmap's qualitative claims** (diagnostic. The gates are P1 and P4). Before = frozen P10 CSVs (CPU, our rebuild; their hashes are above and must be unchanged after the run). After = P11 grouped CSVs.

- Classical: "drops ~4–5 pp" is met if the mean Δ1.0 lies in [−5.5, −3.0] and Δ2.0 in [−6.0, −3.5].
- CNNs, "drop much more (Compact-CNN up to ~20 pp on single subjects)":
  - **reproduced** if the cohort-mean 1.0 s drop of each network arm (OFF and ON) exceeds the classical mean drop, and the largest per-subject Compact-CNN drop (either arm) is ≥ 15 pp;
  - **partial** if only the first part holds;
  - **not reproduced** otherwise.

  If R-9b is met (P4) but this claim is partial or not reproduced, the gap is on the "before" side. Our P10 leaky CNN numbers are not the original's leaky run, which 04_REFERENCE does not preserve per subject. P08 already found the CNN inflation undetectable. That explains the deviation; it does not fail the phase. If R-9b is missed as well, P4 decides. From the frozen P10 numbers and R-9b I expect at most about 12 pp (Compact OFF S03 54.31 vs R-9b 42.64). I state this now so that a "partial" is not read later as a surprise.
- EEGNet gain "+7.34 → +2.01": judged on the P11 Mean Δ1.0 alone (P4 range, > 0). The +7.34 is the original's last leaky run. Ours, P10, is +3.11. The report compares them only descriptively and never presents +3.11 → x as the roadmap's shrinkage. Compact-CNN "keeps +17.16" and ShallowConvNet "keeps +2.53" are judged by the P4 ranges and the sign rule.
- Any coincidence between a P11 network number and an R-x number of a different quantity is flagged as a coincidence, never called a reproduction (memory P09/P10).

**P6. Task 2:** the logs print block lengths per subject and condition. Expected approximate ids: S02 (39 + 40) and S04 (38 + 40), listed in every meta. Any other subject flagged must be explained from its block lengths.

**P7. Provenance:** before reading any CSV, the verifier states the commit that ran (`git diff --stat e86ae3f <run commit> -- src scripts tests configs` shows only fix 1) and the D0 hashes after the run.

### Run commands (02_plan.md, confirmed by both builders)

The commands produce everything P1–P7 need: step 0 for P3; step 1 for P1, P2, P4 and P6; step 2 for P5. Once fix 1 is in, the network section of the step-1 demo run will print "skipped" lines for the three models, which is the intended outcome. The verifier keeps both demo logs and reads the network table from step 2 only.

## Results review

Verdict: APPROVE / REJECT

### Deviations from references

| Ref | Expected | Obtained (log) | Δ | Within tolerance? | Explanation | Accepted? |
|---|---|---|---|---|---|---|
| | | | | | | |

### Interpretation check

### Decisions for decisions.md

## Sources spot-check

Opened in this audit: `mas/RULES.md` (R8 text lines 74-77, era row 28), `mas/02_REQUIREMENTS.md:179-183`, `mas/03_ROADMAP.md:18-19` and P11, `mas/05_PITFALLS.md` PF-01–04, PF-28–31, `mas/01_DATA_SPEC.md` §5.1, `mas/04_REFERENCE_RESULTS.md` R-3–R-9, `mas/state/decisions.md` rows 58, 98, 102, 103. Each says what the handoffs claim, with the exception noted in C1.

## Questions

Verdict: FAIL

1. ml-engineer: required fix 1 (demo network section must check the splitter label in each CSV's meta before pairing, plus a test with a leaky file in the P11 slot).

## Pre-run audit, Round 2

Head audited: c414aeb. Changes since Round 1 (32461e2):
- 40a6d57: C1 decision row.
- bb4d2ea: fix 1, plus N1/N2 wording.
- 567a98a: tester test, mutant M6.

| Item | Result | Evidence |
|---|---|---|
| Fix 1 (R9, stale-result reuse) | PASS | `scripts/diagnostics/demo_cv_leakage.py` `meta_splitter` reads the `cv=` line of each `.meta.txt`. It checks `StratifiedGroupKFold` first; that name does not contain the substring `StratifiedKFold`, so no false match. `network_section` uses a pair only if the labels are exactly (leaky, grouped), otherwise it prints the reason. I re-ran my Round 1 smoke on scratch copies of the real P10 CSVs and their metas: the leaky files in the P11 slot give 3 "skipped (… legacy_leaky file leaky, reports file leaky …)" lines and `None` (Round 1: an all-zero delta table). With a grouped synthetic A/B meta in the compact slot, only `compact_cnn` is paired. On the real files, `meta_splitter` returns `leaky` for `reports/augmentation_ab_eegnet.csv` and `grouped` for a grouped smoke output. Tests: `test_network_section_skips_pairs_whose_splitter_labels_do_not_match` (builder: leaky/leaky, leaky/no-meta, leaky/grouped) and `test_demo_network_section_skips_leaky_vs_leaky_and_computes_hand_deltas` (tester: hand deltas −20/−15, −10/−18, gains 10/15, 10/2). M6 caught. No number-producing path changed (`git diff 32461e2..c414aeb -- src scripts`: the demo pairing, one label string, one docstring). |
| N1 | Resolved as documentation | The `oof_space` docstring now marks `splits=None` as a legacy-only fallback. The behaviour is unchanged, which is acceptable: all nine scripts pass `splits` (Round 1 R1 row). A future caller is still not protected by an error. The note stays open for the P16 refactor. |
| N2 | Resolved | The trial rule is now named "trial-reset smoothing, PF-02 diagnostic", consistent with the meta labels. |
| N3, N4 | Open, carried | Network legacy pins are not in a test (deep-learning, next touch). The S02/S04 residual leak from approximate ids must be stated in the report. |
| C1 (decision row, 40a6d57) | Satisfied | The row is appended and row 103 is left as it was. It states the order plainly: plan chose trial → smoke numbers at 18a6792 → reversal at 31d6f8e, "the numbers were therefore seen before the decision". It cites the R8 text, §5.6, the Conventions line and the P05 record, all of which predate P11. It names the era-matrix R8 row as unreconciled, gives a reading (P11 fixes the window-level CV; true resets need true ids, P16; PF-02 phases P04/P11/P16), and leaves it to Sebastian as a non-blocking question. It fixes the reporting rule: R-6's 2.0 s is reproduced with i%5, with the trial-reset diagnostic beside it, never in place of it. One imprecision, not blocking: item (d) calls the P05 row one "that corrected the era-matrix R8 row"; the row I cited (decisions.md row 58) records the conflict as a carry-forward. Either way the record predates P11, which is what C1 needed. The reporting part of C1 is checked at the results review. |
| Suite | PASS | `.venv/bin/python -m pytest tests -o addopts="" -q -p no:cacheprovider` at c414aeb: `678 passed, 21 warnings in 372.28s (0:06:12)`. This equals the reported 678. Runtime above target, as noted in Round 1. |
| R11 / privacy | PASS | No new reference consultation is declared. The word-bounded vendor/trailer scan of the Round 2 diff and commit messages is clean. |

The pre-committed checks P1–P7 of Round 1 stand unchanged. With fix 1, the step-1 demo run will print three "skipped" lines for the network section; the verifier reads the network table from step 2 only.

Verdict: PASS
