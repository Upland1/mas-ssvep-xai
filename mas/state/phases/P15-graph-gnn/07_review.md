# P15 · 07 · Scientific review

Status: READY (pre-run audit Round 2 PASS)
Author: scientific-reviewer
Reads: 00, 02, 03_changes_*, 04 and every changed file (pre-run); 05, 06 and the CSVs (results)

## Pre-run audit — Round 1

Audited commit: `e71797b` (branch `phase/P15-graph-gnn`). Read: 00_assignment.md, 02_plan.md, both
03_changes files, 04_tests.md, mas/state/decisions.md lines 102–111 and 127, mas/RULES.md, mas/03_ROADMAP.md P15
(lines 554–598) and Conventions (line 18), mas/02_REQUIREMENTS.md §5 (lines 160–175) and §6 (lines 212–213),
mas/04_REFERENCE_RESULTS.md tolerance table, R-1, R-8, R-14, R-15, mas/05_PITFALLS.md PF-01/02/03/04/15/28/30,
`git diff main..HEAD -- src scripts tests`.

Tests run here: `.venv/bin/python -m pytest tests/test_p15_graph_features.py tests/test_p15_gnn.py tests/test_p15_known_answer.py -o addopts="" -q`
→ `74 passed in 28.08s`. Parameter counts re-derived by instantiation (`ConnectivityGNN(7, 10, e, 5)`):
`0 5150`, `5 5534`. No real data was read.

| Rule | Result | Evidence (`path:line`) |
|---|---|---|
| R1 Trial-grouped CV | PASS | Gate: `make_splits("grouped", ds.y, ds.trial_ids, seed + r)` + `assert_no_shared_trials`, one split list per repeat shared by all sets and k (`scripts/connectivity/graph_modeling/benchmark_connectivity_gate.py:88-89`, passed to `oof_space` at `:95`). GNN: same splitter at `seed + repeat` (`benchmark_gnn.py:115-116`). Ids built on the PRE-gate labels (201/202 included in the walk) and masked with the gate mask (`src/models/classical/benchmark_runner.py:84-92`, PF-03). Tests: spies on `make_splits` with seeds 42/43/44 and no shared id (`test_gate_r1_…`, `test_gnn_r1_…`), PF-03 mid-trial rejection test, window-split mutants killed (04_tests.md). Ids approximate on S02/S04 (P11 D-2); must be stated in every write-up. |
| R2 Fit only in-fold | PASS | Gate: `Pipeline(StandardScaler, clone(model))` fitted on `Xtr` only (`src/models/classical/legacy_eval.py:143`); `SelectKBest` sits inside the cloned model (`benchmark_connectivity_gate.py:75-80`), so scaler → selector → Shrinkage-LDA are all fitted on the training fold. GNN: `standardize_fold` takes statistics from `train_idx` rows only (`src/features/connectivity/graph_inputs.py:86-92, 102-105`), called per fold (`benchmark_gnn.py:122`); no validation split, no early stopping, no augmentation. Tests: planted test-fold outliers leave other test predictions bit-identical (k = 0 and 30), spy on `fit_standardizer` indices = each fold's training set; full-data scaler and all-rows standardizer mutants killed. SelectKBest-on-all-rows is guarded only statistically (noted, non-blocking). |
| R3 Filter continuous, then window | LEGACY (by design) | Per-window features on raw gated legacy windows (task 1; era matrix R3 from P16), labelled in `connectivity_graph_features.py:13-15` and every script header. The phase part (enforced from P13) is met: `edge_phase` takes phase from the full-window FFT cross-spectrum summed over band bins (`connectivity_graph_features.py:96-112`), no Hilbert, no filtering. |
| R4 Estimator small-sample bias | N/A (note) | The 3-segment per-window MSC is a per-window *feature* prescribed by task 1, not a condition-level coherence estimate; its upward bias is labelled (`connectivity_graph_features.py:14-15`). The sanity report's `coh_diff` averages per-window coherence over windows (`build_graph_dataset.py:86`); it is a class difference in which a common bias largely cancels, but it is not an R4 estimate (note N3). |
| R5 Shared quality decision, explicit thresholds | LEGACY (by design) | Per-script P07 two-tier gate (R5 from P16), via the flagship `prepare_subject`; all four thresholds passed as one dict (`src/models/classical/feature_spaces.py:44`, `src/features/ssvep/window_mask.py:22-23`); R-1 counts in the builder smoke (200/196/197/197/200) show `vpp_min` 5 µV is in force (no PF-07 regression). |
| R6 Index layouts verified | PASS | Node harmonic-major `h*5 + k` (`connectivity_graph_features.py:69-73`), tested by a tone at every target and every 2nd harmonic (10 cases) and a log10-of-mean hand check; `upper_tri_flat` pair-major → band → cos/sin proven on an index-coded array (`:115-119`); `+phase` band-major flattening tested; edge gate direction `e[b, i, j]` gates j → i tested against a numpy forward. The gate's channel-major `N` reshape (`benchmark_connectivity_gate.py:65`) is not layout-tested, but scaler + f_classif + Ledoit–Wolf LDA are invariant to a column permutation, so the order cannot change any gate number. fs-250 bins of the 2nd harmonics are the prescribed legacy axis (PF-04). |
| R7 Honest statistics | N/A | No inferential test; the gate verdict is the roadmap's descriptive heuristic. |
| R8 Smoothing respects trials | PASS (legacy-folder clause) | Both benchmarks call `accuracies(..., "mod5")` on out-of-fold scores in clean-array order (`benchmark_connectivity_gate.py:98`, `benchmark_gnn.py:126-129`); the cache rows are the gate's clean order (`build_graph_dataset.py:55-61`). Spy test confirms both pass `"mod5"`; mod5 hand-smoothing test uses ids misaligned with `i % 5`. This is the P11 decision (decisions.md lines 103–104); the era-matrix reading stays an open question for Sebastian (P11 C1). |
| R9 Per-subject reporting with data source | PASS | Per-subject rows in both CSV schemas (§6); data source, fs 250 label, CV and smoothing lines in each header/meta (`benchmark_connectivity_gate.py:160-179`, `benchmark_gnn.py:205-215`). |
| R10 Every change and test cites a source that exists and says what is claimed | PASS | Handoffs cite the roadmap tasks, R-1/R-8/R-14/R-15 and PF ids; I opened them and they say what is claimed. |
| R10 Copied lines marked `# adapted from [n]`, license compatible | PASS (note) | No adapted code is declared. `src/models/graph/connectivity_gnn.py:46` is textually identical to the original's return line; it is the direct transcription of the task-5 formula `LayerNorm(h + Dropout(ELU(W_self h + agg)))` with the task's own names, so I do not treat it as copied, but the R11 row must say the forward pass was displayed (fix 1). |
| R11 Reference consulted only after an attempt, every consultation listed | FAIL | See the R11 audit below: the trigger is valid, the adopted change is only `bias=False`, but the listing understates what was opened. |
| Golden rule 3: legacy behaviour labelled and still reachable after fixes | PASS | `--fs` (default 250, labelled), `mod5` default with `"trial"` reachable in `accuracies`, per-window features labelled. |
| Tests cover every change; at least one fails on the historical bug | PASS | 74 P15 tests; PF-01 (window split), PF-03 (post-gate ids), bias=True (R-8), class-major layout, full-data scaler/standardizer, unnormalised phasor, self-messages, mean-only verdict are each killed (04_tests.md mutation table). Untested by mutation: SelectKBest on all rows, train accuracy measured in train mode (note N4). |
| Changes match 02_plan.md and the roadmap tasks | PASS | Tasks 1–6 implemented; plan deviations (new `graph_dataset.py`, extra cache keys, `gnn_benchmark_smoke.csv`, extra CLI flags) are declared and harmless. Hyperparameters match task 6 (`src/models/cnn/eegnet_cv.py:35-40`: epochs 150, batch 32, lr 1e-3, wd 1e-2, eta_min 1e-5, label smoothing 0.05); seeds 42 + r and `1000·r + fold` (`benchmark_gnn.py:115, 123`), `torch.manual_seed` before the model and a seeded DataLoader generator (`:87-96`, PF-28). |
| No data, `.ebr`, local tooling files or tool/vendor names in the diff | PASS | Fragment-built vendor/suffix scan over `git diff main..HEAD`: one hit, the template row of this file; 0 hits in branch commit messages; 0 changed paths under `data/` or the local tooling folder. |

### Specific checks requested

**Feature definitions (task 1).** Node power = log10 of the mean periodic-Hann power over bins within ±1 Hz
(nearest bin otherwise) on the mean-removed window; coherence = Welch MSC from 3 Hann segments at 0/64/128
(confirmed against `scipy.signal.coherence` to 1e-9 by the tester), band-averaged; phase = unit phasor of
`Σ_band X_i conj(X_j)`, `[j, i]` conjugate, diagonal (1, 0). These are natural readings of task 1, and the gate smoke reproduces
every R-14 k = 0 mean to ≤ 0.1 pp, which a different node or coherence definition would be unlikely to do.
PASS.

**Gate verdict rule.** `gate_verdict` (`benchmark_connectivity_gate.py:112-130`): best edge-augmented set
by cohort-mean 1.0 s accuracy, Δ = best − Base per subject, pass iff cohort-mean Δ ≥ 2 pp AND Δ ≥ 2 pp in
≥ ceil(2·3/3) = 2 of S03/S04/S05; k = 0 decides. This matches settled point 3 and the roadmap text. PASS.

**Cache and stale guard; legacy arrays.** The cache is a new file `graph_dataset.npz`; `save_graph_dataset`
refuses any other name (`src/features/connectivity/graph_dataset.py:78-90`); the build only reads legacy
arrays. The stale guard hashes the feature source file + fs + gate thresholds + channel-fail fraction
(`graph_dataset.py:38-44`), checked on every load (`:100-103`). It does NOT cover the FBCCA extractor, the gate
code, `build_trial_ids` or the input arrays, all of which shape the cached `X_fbcca`, `y` and `trial_ids`. The run
uses `--rebuild`, so the graded run is not exposed; CONCERN, carry-forward (note N1).

**GNN architecture (task 5).** Encoder Linear + ELU, channel embedding `randn · 0.1`, residual
`LayerNorm(h + Dropout(ELU(W_self h + agg)))`, `agg` = mean over j ≠ i of `sigmoid(Linear(e_ij)) ⊙ W_msg h_j`
(one gate per hidden unit), readout concat(mean, max) → dropout → concat FBCCA → Linear
(`connectivity_gnn.py:25-69`). Counts by instantiation: 5,150 / 5,534 = R-8 exactly. The per-hidden-unit gate was
fixed by the counts before the consultation (the coherence delta 5,662 − 5,278 = 384 = 2 × (5·32 + 32) already
matched). The remaining +128 has two count-equivalent explanations, bias-free `W_self`/`W_msg` or a non-affine
LayerNorm; I checked numerically that both give 5,150, so the ambiguity was real and R11 was the right tool. PASS.

**Standardizer.** Per (channel, feature) for nodes, per (i, j, feature) for edges, per feature for FBCCA,
training rows only; constant columns (std < 1e-8, the unit coherence diagonal) left unscaled
(`graph_inputs.py:80-99`). The diagonal maps to 0 and is masked from messages anyway. PASS.

**Train-accuracy diagnostic.** Mean over folds of the accuracy on the un-augmented, standardized training fold, after
the last epoch, in eval mode with `no_grad` (`benchmark_gnn.py:72-80, 128`); hints at gap > 15 pp / train < 70 %
(`:56-57, 134-140`). This matches PF-30 and settled point 2. PASS.

### R11 audit (deep-learning consultation, 2026-10-26T23:14)

- **Log.** `mas/state/scratch/reference_access.log` lines 32–33: 23:14:29 `git grep -n "class ConnectivityGNN\|class EdgeGatedLayer" HEAD`, 23:14:32 `git show HEAD:src/models/graph/connectivity_gnn.py | sed -n 1,95p`. The connectivity-stats builder made no access.
- **After-attempt condition: met, as far as the record can show.** The stated trigger (own implementation, count test failing at 5,278 / 5,662, +128 on both) is concrete and is preserved in `tests/test_p15_gnn.py:33-35`. The ambiguity was genuine (two count-equivalent choices, above). Timestamps cannot confirm the order independently: connectivity-stats committed at 23:07:29, the access was at 23:14, and all three deep-learning commits share 23:25:17. Edits are not logged, so this is stated, not a finding.
- **Listing: inaccurate.** I opened the same blob (`5d6d1c2`): the file has 73 lines, so `sed -n 1,95p` displayed all of it, including both `forward` methods (lines 23–33 and 61–73: mask formula, gated aggregation, readout). The handoff R11 row says "about lines 14-23 and 37-62". Its own "Differences" paragraph admits that "the gate module, readout and mask formula were read", and those are in the unlisted lines. By the verifier's rule ("unlisted accesses are a FAIL") this needs correcting before the run (fix 1).
- **Anything beyond the bias choice?** No adopted behaviour beyond `bias=False`. Everything else is fixed by task 5 or by the pre-consultation counts. The code is visibly our own: `agg` is divided after the sum, not folded into the mask; the gate is a separate `Linear` + `torch.sigmoid`, not a `Sequential`; the embedding has shape `(N, H)`, not `(1, N, H)`; a missing graph input raises instead of being skipped. Line 46 is identical in text to the original's return line, but it is the literal task-5 formula (R10 row). Nothing in the benchmark, inputs or features came from the original: the access log shows no other file opened by any builder.

**My own consultation (R11, verification of a finished, passing implementation).** For this audit and the
train-accuracy question I opened the original @5d6d1c2 (log entries 23:44:31–23:45:50, scientific-reviewer):
`src/models/graph/connectivity_gnn.py` (whole, 73 lines), `scripts/connectivity/graph_modeling/benchmark_gnn.py`
lines 30–105 and its argparse lines 130–143, and `src/features/connectivity/graph_inputs.py` lines 41–65. Learned:
see the next section. No code change follows from this, and I give the builders no code from it.

### Train-accuracy gap (S03 smoke 95.56 / 95.94 vs R-15 86.8 / 87.8)

The hypothesis that the original measured train accuracy in train mode with dropout on is **refuted**. The
original measures it after training, in `model.eval()` under `no_grad`, on the full (un-augmented) training fold,
and averages over the five folds. That is the same definition as ours. Its fold standardizer is per position on training rows with
`std + 1e-6`, which matches ours except for constant columns, and those are masked. Its CLI defaults equal task 6 (150 epochs,
batch 32, lr 1e-3, hidden 32, 2 layers, dropout 0.3). So the gap is **not definitional** and must not be
"fixed" by redefining the column (golden rule 5). Remaining candidates, none testable here: the device (the
original defaults to CUDA when available; this run is CPU by settled point 4), the RNG stream (the original
draws its batch order from the global torch RNG, which dropout also uses, while ours has a separate seeded loader
generator), and the variance of a single split (the smoke is one repeat; R-15 is a mean of 3). The smoke's
test accuracy (77.16 / 81.73) is inside R-15's S03 windows. Disclosure: these smoke values were seen before the windows below were set.

### Pre-committed acceptance windows (for the verifier and the results review)

Integer note: one window is 0.510 pp (S02, n 196), 0.508 pp (S03, 197) and 0.500 pp (S05, 200). Cells are means of
repeats, so they are not integers. Arithmetic: the python command in this audit's session, from the R-14/R-15
tables as printed in mas/04_REFERENCE_RESULTS.md.

**A1 — R-14 gate table** (`reports/connectivity_gate_benchmark.csv`, mean over the 5 repeats of `acc_1s`):
- k = 0: each of the 45 subject × set cells within ±1.5 pp of R-14, and each of the 9 cohort means (five subjects)
  within ±1.0 pp. Any cell outside must be explained (tolerance table).
- k = 30: the 8 cohort means R-14 lists (Base 74.0, Base+Ec 77.5, Base+Ec+Ep 77.5, Base+Ep 76.0, N 64.9, Ec 46.7,
  Ep 35.5, Ec+Ep 46.0) within ±1.0 pp. Per-subject k = 30 cells and F at k = 30 have no reference and are reported only
  (F has 5 columns, so k = 30 equals k = 0 for it).
- Best set: at k = 0 the best of all nine sets and the best edge-augmented set is Base+Ec, with mean in [76.6, 78.6].
  At k = 30 the best edge-augmented set may be Base+Ec or Base+Ec+Ep (R-14 ties them at 77.5).
- Verdict, reason included: at k = 0, "does NOT pass" *because of the responder criterion*. That means 0 or 1 of
  S03/S04/S05 with Δ ≥ 2 pp (R-14: 0/3, Δ +1.3 / +0.1 / −1.7), while the cohort-mean Δ is ≥ 2 pp (R-14-implied +3.82).
  S01 and S02 must have Δ ≥ 2 pp (R-14 +16.3 / +3.1). A "does not pass" reached for another reason (cohort-mean Δ < 2 pp)
  does not match R-14 and must be reported as a deviation. The k = 30 verdict is reported the same way.

**A2 — R-15 GNN cells** (`reports/gnn_benchmark.csv`, mean of the 3 repeats), graded on S02, S03, S05; S01 and S04 are
reported without reference. Graded cells are 1.0 s and 2.0 s, ±5 pp:

| Variant | S02 1.0 / 2.0 s | S03 1.0 / 2.0 s | S05 1.0 / 2.0 s |
|---|---|---|---|
| nodes+F | [33.6, 43.6] / [41.1, 51.1] | [72.8, 82.8] / [77.2, 87.2] | [85.0, 95.0] / [90.0, 100] |
| nodes+coh+F | [32.2, 42.2] / [35.1, 45.1] | [72.5, 82.5] / [77.9, 87.9] | [85.5, 95.5] / [90.3, 100] |

Cohort (mean of S02/S03/S05, ±3 pp): nodes+F 1.0 s 68.80 [65.80, 71.80], 2.0 s 74.43 [71.43, 77.43]; nodes+coh+F
1.0 s 68.40 [65.40, 71.40], 2.0 s 72.77 [69.77, 75.77].

**A3 — seed/fold spread rule (decisions P11, row 110; the 3 repeats are the seed bases).** The repeats vary both the
split (42 + r) and the init (1000·r + fold), as the original did, so their range is the right noise scale for R-15. For each cell
outside its A2 window:
(a) it is *explained by seed/fold variance* if the R-15 value lies within [min, max] of the three repeats;
(b) if all three repeats lie on the same side of R-15 it is *systematic*: "not reproduced within tolerance, cause not
established". Report the 3-repeat SD, and if the gap is more than 3 × SD say that seed variance is not the cause (P11 D-8
lesson). A systematic graded cell goes to Sebastian as a deviation (B006 precedent);
(c) a cohort cell outside ±3 pp is explained only if every driving cell (setting it to R-15 brings the cohort back
inside) is explained under (a).
Also tally the signs of all 12 graded differences (obtained − R-15). If 11 or 12 share a sign, report it as one-sided, not as noise.

**A4 — "nodes+F ≈ nodes+coh+F" and "coherence edges do not help".** Δ = (nodes+coh+F) − (nodes+F), on
3-repeat means at 1.0 s.
- ≈: |Δ| ≤ 5 pp on each of S02/S03/S05 and |cohort Δ| ≤ 3 pp (NN tolerance). The 2.0 s Δ is reported, not
  graded per subject, because R-15's own S02 2.0 s Δ is −6.0 pp and would fail a per-subject 2.0 s reading
  (R-15 1.0 s Δ: −1.4 / −0.3 / +0.5, cohort −0.40; 2.0 s Δ: −6.0 / +0.7 / +0.3, cohort −1.67).
- Do not help: cohort Δ1.0 s < +2.0 pp AND fewer than 2 of the 3 subjects with Δ1.0 s ≥ +2.0 pp (the gate's own
  threshold mirrored). The five-subject version is reported beside it. If the two readings disagree, say so; the
  three-subject reading is graded.
- Sign-flip clause (tolerance table): a positive cohort Δ1.0 s is a flip of R-15's −0.40. It is explained as noise
  if 0 lies within the range of the three per-repeat cohort Δ (same split per repeat for both variants);
  otherwise it must be explained.

**A5 — train column (PF-30 diagnostic).** Reported for every subject next to R-15 with the same ±5 pp windows
(S02 [51.4, 61.4] / [52.7, 62.7]; S03 [81.8, 91.8] / [82.8, 92.8]; S05 [91.1, 100] / [91.6, 100]). It does not
decide the phase: the roadmap acceptance names test-level claims, and the definition was verified identical above.
A train cell outside its window is recorded in decisions.md as "not reproduced within tolerance, cause not
established (candidates: device, RNG stream, split variance)". No code or definition changes (golden rule 5). If
the excess is on all three subjects and both variants, it is stated in the report as a systematic difference that is
open for Sebastian (non-blocking question).

**A6 — exact.** R-8: the meta line `params: nodes+F=5150, nodes+coh+F=5534`. R-1: the build log shows clean
windows S01 200, S02 196, S03 197, S04 197, S05 200, 7 channels kept for all, `trial_ids_approximate` True only for
S02 and S04, and every subject built fresh (`[+]` lines, no `[=] cache valid` line).

**A7 — smoke.** `benchmark_gnn --smoke-test` exits 0 and writes `reports/gnn_benchmark_smoke.csv` with exactly
the columns `variant, repeat, acc_1s, acc_2s, train_acc, subject`, 2 rows (2 variants × 1 repeat), and a `SMOKE TEST` header.
It does not create or modify `reports/gnn_benchmark.csv` (step 3 runs before step 4; check that the file is absent or
older than step 3's start).

**A8 — run hygiene (verifier).**
- Legacy arrays unchanged. Run before step 1 and after step 4, with the output identical:
  `find data/processed -type f ! -name graph_dataset.npz | sort | xargs sha256sum | sha256sum`.
- Run commit = audited code: `git diff --stat <audited commit> <run commit> -- src scripts tests configs` is empty
  (Round-2 fixes are documentation only).
- The gate runs before the GNN, so the gate rows are printed in the GNN log.

### Required fixes

1. **R11 / deep-learning** (`mas/state/phases/P15-graph-gnn/03_changes_deep-learning.md`, the R11 table row and its
   footnote). Correct the "Files and lines" cell to the full extent displayed: the `git grep` class lookup
   (23:14:29) and `git show HEAD:src/models/graph/connectivity_gnn.py | sed -n 1,95p` (23:14:32) displayed the whole
   73-line file @5d6d1c2, including both `forward` methods. In "What changed" state that only `bias=False` on
   `W_self`/`W_msg` was adopted, and that the forward pass, gate and readout were already implemented from task 5
   and were not changed after the reading. Also note that `connectivity_gnn.py:46` coincides in text with the
   original's return line because both transcribe the task-5 formula. Documentation only; no code change.

### Non-blocking notes

- N1 (cache, carry-forward to any phase that reuses `graph_dataset.npz`; connectivity-stats). Extend
  `code_fingerprint` to the FBCCA extractor, gate and trial-id sources, and to the sha256 of each subject's input
  arrays (`y_labels.npy`, window arrays). Today a cache stays "valid" after any of them changes. The P15 run is
  not affected (`--rebuild`).
- N2 (R8). The open era-matrix question on i%5 under R8 (P11 C1) still applies to the P15 2.0 s columns; the
  report should cite decisions rows 103–104.
- N3 (R4 wording). The sanity CSV's `coh_diff` is a difference of per-window-averaged 3-segment MSC; the report
  should call it a descriptive class difference of biased per-window values, not a coherence estimate.
- N4 (test strength). Two variants are not mutation-tested: SelectKBest fitted on all rows (statistical guard
  only), and train accuracy measured without `model.eval()` (no test asserts dropout off for the train column).
  Both are correct by inspection (`legacy_eval.py:143`, `benchmark_gnn.py:73`).
- N5 (R9). Every write-up states the data source (legacy 7-channel OO folders, stimulus windows, two-tier gate,
  fs 250 label, per-window features) and the approximate ids on S02/S04 (D-2).

Verdict: FAIL

## Pre-run audit — Round 2

Checked commit: `73a7e9e`. The fix is `0d10722`, which edits the R11 row of `03_changes_deep-learning.md`.

- **Code unchanged.** `git diff --stat e71797b HEAD -- src scripts tests configs` gives empty output. The Round 1 test result (74 passed) and the counts 5,150 / 5,534 therefore still hold. No tester round was needed.
- **Fix 1 against `mas/state/scratch/reference_access.log`.** Lines 32–33 are the only deep-learning entries in P15. Lines 34–39 are my own Round 1 verification, which is listed in Round 1.
  - (a) The `git grep` at 23:14:29 is listed.
  - (b) The `git show … | sed -n 1,95p` at 23:14:32 is listed. The row correctly says it displayed the whole 73-line file, including both `forward` methods.
  - "What changed" now says only `bias=False` was adopted, and that the forward pass, gate and readout came from task 5.
  - The coincidence of line 46 is stated. The blocked recursive `grep` is labelled as not an access.
  - Fix 1 is met.
- **Wording note (non-blocking).** The row calls the `git grep` output a "file list only". That command (`-n`, run against `HEAD`) prints matching lines. I re-ran it, and the access is logged: it printed the two class-declaration lines with their line numbers, `connectivity_gnn.py:12` and `:36`. It showed no body code, so nothing material is understated. The scribe may write "file and line of the two class declarations".
- A1–A8 and notes N1–N5 of Round 1 stand unchanged.

Verdict: PASS

## Results review

Verdict: APPROVE / REJECT

### Deviations from references

| Ref | Expected | Obtained (log) | Δ | Within tolerance? | Explanation | Accepted? |
|---|---|---|---|---|---|---|
| | | | | | | |

### Interpretation check

<!-- Per-subject reading; inconclusive results stated as such; leakage in
fitted objects, normalization, validation sets; statistics unit and
multiple comparisons. -->

### Decisions for decisions.md

<!-- Accepted deviations, one line each; the orchestrator copies them. -->

## Sources spot-check

<!-- Fix rounds: append "## Pre-run audit — Round N". After two failed rounds,
set Status: BLOCKED. -->

## Questions
