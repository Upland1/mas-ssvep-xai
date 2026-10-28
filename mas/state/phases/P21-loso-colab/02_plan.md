# P21 · 02 · Plan

Status: READY
Author: orchestrator
Approval: PLAN_APPROVAL auto

## Goal

Leave-one-subject-out (LOSO) generalization at 1 s windows, stride 0.25 s:

- train on every subject but one and test on the held-out one;
- methods `fbcca`, `lda`, `lda_subjnorm`, `ccnn`, `compact_eegnet`, `eegnet`;
- folds are resumable;
- a Colab notebook runs the cohort that does not fit the local budget;
- record LOSO against the within-subject reference (R-16: direction only, no numeric target).

## Data source

- Built folders `data/processed_continuous/w1_s0.25/<S>/`, session OO, `--quality-source both`,
  `--banks fbcca fbcsp`. These are the same build parameters as P20, so the S01–S05 folders
  built in P20 are reused unchanged.
- **Cohort (B003 option B, Sebastian 2026-10-28).**
  - Cohort 5: S01–S05, comparable with P20.
  - Cohort all: every subject `build_windows` finds in the raw-data folder. Sebastian
    places S06–S40 there (40 subjects, the original's LOSO cohort plus S020). Agents never
    copy, list or read raw recordings.
  - Both cohorts are reported, each as its own data source (R9). Every summary row's
    `Data source` names the cohort and its subject count.

## Settled points (inferred; recorded in decisions.md)

1. **Subjects.**
   - `--subjects` (default: every built subject found by `discover_subjects`, numeric order).
   - The harness refuses two folder names with the same number (e.g. `S10` and `S010`),
     because numeric sorting would otherwise collide.
   - It prints the cohort and its size; the count is never hardcoded.
2. **Classes.** The 5 stimulus classes 101–105; 201/202 are excluded (as in the P20 sweep).
3. **Channels (`choose_channels`, PF-34).**
   - `common`: montage channels kept by the shared gate (`channels_kept_idx`) in **every**
     subject of the cohort. This is the default.
   - `all`: the full montage of the built folder for every subject, including channels the
     gate dropped. Window validity still comes from the shared `valid_mask` (R5). The summary
     states `Channels = all (gate channel drops ignored)`.
   - The harness refuses to run if the montages differ between subjects, or if `common` is empty.
   - `Channels` column: the names used.
4. **Grouping (R1, PF-33).**
   - The LOSO outer split is the subject.
   - Trial ids are offset per subject before pooling: `id + 10_000 × subject_index`, or any
     scheme proven collision-free by a test.
   - Nothing from the held-out subject reaches any `.fit()`: CSP, scaler, LDA, network
     normalization statistics, early stopping.
5. **Methods.**
   - `fbcca`: argmax of the normalized FBCCA scores already in the built folder; no training.
     Its LOSO value must equal its within-subject value per subject (R-16 check).
   - `lda`: CSP per band (m = 1 pair per class one-vs-rest, as the flagship) fitted on the
     pooled training subjects, plus FBCCA scores, then a StandardScaler (training subjects
     only), then Shrinkage-LDA (`solver="lsqr", shrinkage="auto"`). The existing in-fold
     feature code is reused; nothing is duplicated.
   - `lda_subjnorm`:
     - Each subject's feature matrix (after CSP, which is fitted on the training subjects) is
       z-scored with its **own** mean/std over all its clean windows. That covers the
       training subjects and the test subject, without labels.
     - Pooled scaler and LDA as for `lda`.
     - Its name and write-up say "unsupervised per-subject normalization (test-time, whole
       session = offline upper bound)". This is R2's exception (a)–(c), PF-35.
   - `ccnn`, `compact` (= `compact_eegnet`, PF-31), `eegnet`: `fit_network` from P20 on the
     pooled training subjects' filtered windows, with the same hyperparameters as P20
     (AdamW lr 1e-3, batch 16, wd 0.01, label smoothing 0.1, cosine, patience 25,
     max 150 epochs).
   - Validation (PF-32) is the first split of the inner grouped 5-fold over the **offset
     training trial ids**. It never contains the held-out subject.
   - Normalization statistics are computed on the training subjects only.
   - CLI name `compact`; tables print `compact_eegnet`.
6. **Resumable folds (PF-37 groundwork).**
   - Each (method, test subject) fold is saved to `<out-dir>/folds/<method>__test-<S>.npz`
     with predictions, probabilities, trial ids, offsets, train/val accuracy, best epoch,
     seconds, and a `config` JSON: channels, training subjects, window, stride, method
     hyperparameters, seed, git HEAD.
   - On rerun an existing fold is skipped (`[skip] <method> test-<S>`). The summary is always
     rebuilt from the fold files.
   - Folds are written atomically (temporary file, then rename), so an interrupt never
     leaves a half fold.
   - Refusing mixed configurations is P22. In P21 the harness only **warns** when a saved
     fold's config differs.
7. **Outputs** (`mas/02_REQUIREMENTS.md` §6) in `<out-dir>/`:
   - `summary.csv`: `Subject, Window (s), Method, Windows, Trials, Acc (%), Acc SD,
     BalAcc (%), ITR (bits/min), Train Acc (%), Runs, Val Acc (%), Best Epoch,
     2-tap Smoothed (%), Channels, Data source`, plus cohort rows `Mean` and `SD`.
   - `per_subject.csv` (pivot Subject × Method on Acc and 2-tap), `predictions.csv`,
     `confusion.csv`.
   - `--save-models` saves to `outputs/models/loso_w1/<method>__test-<S>.*`.
   - 2-tap smoothing within trial, sorted by (trial, offset) (R8).
   - ITR: Wolpaw, N = 5, T = 1 + 0.5 s.
   - `Runs` = 1 for every method. FBCCA has no training; for the others one fit per held-out
     subject is the protocol.
8. **Early-stopping diagnostics (P20 C-2).**
   - `fit_network`'s callers mark a fold `degenerate` when its restored best epoch is ≤ 5
     or its train accuracy is below chance + 10 pp (30 % for 5 classes).
   - The flag is a column in `folds.csv` and is printed. The rule itself is unchanged; any
     change must be pre-registered.
9. **Seeds.** Seed 42 for every fold. A single CNN fit per held-out subject; P20 C-3 applies
   to interpretation.
10. **Hash-pinned tests (P20 C-1).** The P09/P10 hash-pinned tests set
    `torch.set_num_threads(1)` inside the test. Their hash is re-derived on `main`'s code
    (the test file's model code is unchanged), and they add a probability-tolerance check,
    so a thread change can no longer flip them silently.
11. **Within-subject reference.** `benchmark_window_sweep.py --windows 1 --methods fbcca lda
    --cv-repeats 5` on the same folders and cohort. The P20 window-sweep CSV is the
    S01–S05 reference, and the run for all subjects goes into a new out-dir. LOSO and within
    are compared per subject on the same channels where possible; the report states where
    the channel sets differ. P22 adds `within_lda` on exactly the LOSO channels.
12. **Colab notebook (PF-40).**
    - Cells, in order:
      1. GPU check;
      2. mount Drive;
      3. settings (`RAW_DIR`, `DRIVE_DIR`, `REPO_URL = "https://github.com/Upland1/mas-ssvep-xai.git"`,
         `BRANCH`, `LOSO_OUT`), which lists the subjects and checks that `OO.ebr` exists;
      4. fresh clone;
      5. `pip install pyyaml joblib` only;
      6. symlinks for the raw-data folder, `reports`, and `outputs/models` to Drive;
      7. build windows (`--resume`);
      8. within reference;
      9. LOSO classical;
      10. LOSO networks, one method per cell, resumable;
      11. a comparison table (within vs LOSO, per subject and mean);
      12. release the runtime.
    - Markdown cells are written for a first-time Colab user.
    - The notebook is committed **without outputs**.
    - It never prints recording content; listing subject folder names in the user's own
      Colab session is allowed.

## Work split (order: 1, then 2 and 3 in parallel on disjoint files)

| # | Agent | Files | Tasks |
|---|---|---|---|
| 1 | ml-engineer | NEW `scripts/benchmarks/benchmark_loso.py` (CLI, `choose_channels`, cohort loading via `load_subject`, trial-id offset, classical methods, resumable fold store, summary/pivot/predictions/confusion, smoothing, ITR), NEW `tests/test_p21_loso.py`; `tests/test_no_leakage.py` registration if needed | P21.1; settled 1–7, 11. Leaves a `NETWORK_METHODS` hook that calls `cnn_fold`-style code from `src/models/cnn/training.py`, so builder 2 adds no structure. Measures classical runtime on S01–S05 and extrapolates to 40 subjects. |
| 2 | deep-learning | MODIFIED `src/models/cnn/training.py` (if a pooled-subject entry point or the degenerate flag is needed), MODIFIED `scripts/benchmarks/benchmark_loso.py` (network methods only), MODIFIED P09/P10 hash-pinned tests, NEW `tests/test_p21_loso_networks.py` | P21.2; settled 5 (networks), 8, 9, 10. Measures one network fold per model on S01–S05 (≤ 5 min smoke) and gives per-window-epoch costs for the runtime table. |
| 3 | data-signal | NEW `notebooks/loso_colab.ipynb`, NEW `tests/test_p21_notebook.py` (valid JSON, no outputs, required cells and settings names, no `pip install -r`, every CLI line matches a real argparse option) | P21.3; settled 12. Documents the manual steps it cannot automate. |

Each builder runs the full suite (`.venv/bin/python -m pytest tests/ -q -o addopts=""`, about 14 min, nothing else running) and gives measured smoke times.

## Methodological risks

| Rule / PF | Risk | Guard |
|---|---|---|
| R1, PF-33 | trial-id collisions pool two subjects' trials into one group; held-out subject leaks into validation | offset ids; test: two subjects with equal ids, assert disjoint groups and no test subject in any fit |
| R2 | CSP/scaler/LDA/network stats fitted with test-subject data | planted-leak test: test subject's windows replaced by NaN or a sentinel; every fit must succeed and give the same model |
| R2 exc., PF-35 | `lda_subjnorm` uses test labels, or is unlabeled in output | test: permuting the test subject's labels leaves its normalized features unchanged; method name and data source carry the label |
| PF-34 | channel sets differ across subjects | `choose_channels` test with a planted per-subject drop |
| PF-32 | early stopping on the held-out subject | test: `fit_network` receives no window of the test subject (ids checked) |
| PF-37 | resumed fold from another configuration | config stored; mismatch warns (refusal is P22) |
| R8 | smoothing across trials or across subjects | sort by (subject, trial, offset); test with a planted boundary |
| R9 | cohort mean only, or cohort unstated | per-subject rows plus Mean/SD; `Data source` names the cohort |
| R-16 | implausible direction (LOSO ≥ within, fbcca LOSO ≠ within) | reviewer checks; fbcca equality is a test with a known answer |

## Tests required (known answers)

1. Planted SSVEP: synthetic subjects with planted target frequencies and different gains. LOSO `fbcca` equals the per-subject within accuracy exactly; `lda` is above chance.
2. Subject gain shift: subjects scaled by very different gains. `lda_subjnorm` ≥ `lda` on the held-out subject (known: normalization removes the gain).
3. Trial-id offset: pooled groups are unique per (subject, trial) and the test subject's ids never appear in training or validation groups.
4. Leakage sentinel (R2): the test subject's windows are replaced by a sentinel. Training-side fitted parameters are identical, so nothing from the test subject was fitted.
5. `choose_channels`: planted drops give the expected `common` list; `all` returns the full montage; differing montages raise.
6. Resume: a run is interrupted after k folds (simulated). The rerun skips exactly those k, the summary is identical to an uninterrupted run, and an atomic write leaves no partial file.
7. 2-tap smoothing within trial and subject on a known prediction sequence.
8. Networks: a pooled CCNN learns planted classes on synthetic subjects (CPU, small). The validation groups exclude the test subject. The degenerate flag fires on a planted best-epoch-1 history.
9. Notebook: the structural tests listed in the work split.
10. Each test of a fix fails on the bug it guards (e.g. no offset leads to collisions; normalization with labels makes the permutation test fail).

## Run commands (for the verifier, in order; runtimes to be replaced by the builders' measurements)

```bash
P=".venv/bin/python -m"
# 0. hash data/processed_continuous/w1_s0.25/S0[1-5] (before); count subjects with an OO recording via build_windows' own discovery (dry listing printed by the script, not by the agent)
# 1. build the extra subjects at w1_s0.25 (S01–S05 skipped by --resume; ≈ 1–5 min if S06–S40 are present)
$P scripts.build_windows --filter-mode continuous --session OO --banks fbcca fbcsp --quality-source both --window-sec 1 --stride-sec 0.25 --resume
# 2. LOSO classical, cohort 5
$P scripts.benchmarks.benchmark_loso --data-root data/processed_continuous --window 1 --stride-sec 0.25 --subjects S01 S02 S03 S04 S05 --methods fbcca lda lda_subjnorm --channels common --out-dir reports/loso_w1_s01-s05
# 3. LOSO networks, cohort 5 (≈ 13 min GPU, estimate from P20 nn_sweep/folds.csv)
$P scripts.benchmarks.benchmark_loso --data-root data/processed_continuous --window 1 --stride-sec 0.25 --subjects S01 S02 S03 S04 S05 --methods ccnn compact eegnet --channels common --out-dir reports/loso_w1_s01-s05
# 4. resume check: rerun 2; every fold must print [skip]; summary hash unchanged
# 5. within reference, all subjects (new out-dir; S01–S05 reference = reports/window_sweep from P20)
$P scripts.benchmarks.benchmark_window_sweep --data-root data/processed_continuous --windows 1 --stride 0.25 --methods fbcca lda --cv-repeats 5 --out-dir reports/window_sweep_w1_all
# 6. LOSO classical, all subjects
$P scripts.benchmarks.benchmark_loso --data-root data/processed_continuous --window 1 --stride-sec 0.25 --methods fbcca lda lda_subjnorm --channels common --out-dir reports/loso_w1
# 7. LOSO networks, all subjects — HUMAN RUN (Colab notebook or local), ≈ 16 h on an RTX 3050-class GPU
$P scripts.benchmarks.benchmark_loso --data-root data/processed_continuous --window 1 --stride-sec 0.25 --methods ccnn compact eegnet --channels common --out-dir reports/loso_w1
# 8. hash S01–S05 folders (after) — must equal 0
```

**Measured (builders' handoffs, 2026-10-28).**
- Classical LOSO, S01–S05, CPU: 11.7 s; rerun 2.8 s with 15 `[skip]`.
- Classical LOSO, 40 subjects (from a 20-subject replica): ≈ 30–35 min, ≈ 4.5 GB peak.
- Networks, GPU:
  - ms per training-window-epoch: 0.137 (ccnn), 0.456 (compact_eegnet), 0.247 (eegnet).
  - Cohort 5: ≈ 1.7 + 9.6 + 3.8 min, ≈ 15 min.
  - 40 subjects: ≈ 2.2 + 12.5 + 4.9 h, ≈ 19.6 h, so command 7 is a human run.
- Resume check (command 4): compare `summary.csv`, `per_subject.csv`, `predictions.csv` and
  `confusion.csv`. Do not compare `folds.csv`, whose `Seconds` is wall clock (04_tests.md).
- Suite ≈ 13–15 min, run alone.
- Colab: the notebook clones `BRANCH` from `REPO_URL`, so the branch must be on GitHub, and
  pushing is Sebastian's step. The notebook's within reference goes to
  `reports/window_sweep_colab`.

**Budget.** `LOCAL_RUN_BUDGET_MIN` 120 and `MAX_GPU_HOURS_PER_PHASE` 2.
- Estimate from P20 `reports/nn_sweep/folds.csv`: 0.115, 0.458 and 0.218 ms per
  training-window-epoch (ccnn, compact_eegnet, eegnet); mean epochs 66, 86, 107; ~660
  windows per subject.
- LOSO networks on 40 subjects: ≈ 106 + 548 + 323 min, about 16 h. That is far over the
  budget, so command 7 is the human-run request: the Colab notebook, or the same command
  locally, resumable.
- Cohort 5 networks: ≈ 1.4 + 7.0 + 4.1 min, so they run locally.
- If S06–S40 are not in the raw-data folder when the verifier starts, commands 1, 5, 6
  and 7 join the human-run request. The phase then reports cohort 5 only and is
  `PASS (partial; human run pending)`.

## Acceptance checks (for the verifier)

1. Classical LOSO runs end-to-end on CPU (command 2 and 6 with `CUDA_VISIBLE_DEVICES=""` or the script's CPU path for classical methods).
2. The interrupt-and-rerun check skips the finished folds (command 4; the verifier may also kill command 6 after a few folds and rerun it).
3. The notebook's structure tests pass. Manual Colab steps are documented in `03_changes_data-signal.md`; running it top to bottom on a T4 is part of the human run.
4. Within vs LOSO recorded per subject and as a cohort mean, for each cohort, with data source.
5. R-16 directions reported:
   - `fbcca` LOSO equals within, exactly per subject;
   - LOSO below within for trained methods;
   - `lda_subjnorm` ≥ `lda`.
6. The S01–S05 built folders are unchanged (hashes); suite passes run alone, with `torch.get_num_threads()` recorded (P20 C-1).
7. R11 log and privacy scan clean.

## Sources

- `mas/03_ROADMAP.md` P21.
- `mas/05_PITFALLS.md` PF-31..PF-37, PF-40.
- `mas/04_REFERENCE_RESULTS.md` R-16.
- `mas/02_REQUIREMENTS.md` §2, §5, §6.
- `mas/state/blockers/B003-cohort-beyond-S05.md`.
- `mas/state/decisions.md` P20 rows (C-1..C-3).
- `reports/nn_sweep/folds.csv` for the timing estimate.

## Questions
<!-- receivers append: ACK <agent> <YYYY-MM-DD>, then questions; answers appended, never deleted -->
