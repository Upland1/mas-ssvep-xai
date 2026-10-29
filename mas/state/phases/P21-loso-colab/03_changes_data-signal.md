# P21 · 03 · Changes — data-signal

Status: READY
Author: data-signal
Reads: 00_assignment.md, 02_plan.md, mas/RULES.md, 03_changes_ml-engineer.md, 03_changes_deep-learning.md
Branch: phase/P21-loso-colab
Commit(s): see `git log` (feat: Colab notebook; test: notebook structure tests; docs: this file)

## Files

| Path | NEW / MODIFIED | Summary | Roadmap task | Source |
|---|---|---|---|---|
| notebooks/loso_colab.ipynb | NEW | Colab notebook, 12 numbered steps, committed without outputs: GPU check, Drive mount, settings (`RAW_DIR`, `DRIVE_DIR`, `REPO_URL`, `BRANCH`, `LOSO_OUT`; lists subject folders, asserts `OO.ebr` per subject), fresh shallow clone, `pip install -q pyyaml joblib` only, symlinks to Drive, `build_windows --resume`, within reference, LOSO classical, LOSO networks (3 cells, one method each), within-vs-LOSO table, `runtime.unassign()` | P21.3 | PF-40, settled point 12 |
| tests/test_p21_notebook.py | NEW | 8 structure tests (below) | P21.3 | PF-40 |

No file under `src/`, `scripts/`, `reports/` or `baselines/` was touched.

## Legacy behaviour implemented

None.

## Notebook design

- Cell order is fixed by a test. Markdown cells are written for a first-time Colab user (what to click, what the expected output looks like, what to do after a disconnect). The first cell holds the expected-runtime table (40 subjects: build minutes to ~1 h, classical 30-35 min, ccnn 2.2 h, eegnet 4.9 h, compact_eegnet 12.5 h, from 03_changes_ml-engineer.md and 03_changes_deep-learning.md; stated as RTX 3050-class, a T4 "of similar order, within a factor of about two").
- Symlinks (Python cell, no recording content is read): the raw recordings folder (`RAW_DIR`), `reports`, `outputs/models`, and additionally `data/processed_continuous` (see Deviations).
- Commands (all verified by parser):
  - `scripts.build_windows --filter-mode continuous --session OO --quality-source both --banks fbcca fbcsp --window-sec 1 --stride-sec 0.25 --resume`
  - `scripts.benchmarks.benchmark_window_sweep --data-root data/processed_continuous --windows 1 --stride 0.25 --methods fbcca lda --cv-repeats 5 --out-dir {WITHIN_OUT}`
  - `scripts.benchmarks.benchmark_loso ... --methods fbcca lda lda_subjnorm --channels common --out-dir {LOSO_OUT}`
  - three network cells, `--methods ccnn | eegnet | compact`, `--device auto --save-models --models-dir {MODELS_DIR} --out-dir {LOSO_OUT}`.
- `LOSO_OUT` default `reports/loso_w1_colab`; the models dir is `outputs/models/<basename of LOSO_OUT>`, so a new `LOSO_OUT` also gets a new models folder. Classical and network cells share one `LOSO_OUT` (the harness rebuilds the summary from all folds, builder 1). A folder from another configuration is refused by the harness (builder 1, deviation 1).
- Comparison cell: pivots `summary.csv` of the within run and of the LOSO run (`Acc (%)` per Subject x Method), numeric subject order, Mean row over subjects, prints both Data source strings. It states in markdown that the channel sets can differ (builder 1, deviation 2). It prints only accuracies, never recording content.
- The settings cell prints subject folder names and `MISSING OO.ebr` lines only (allowed by settled point 12); it asserts on missing files.

## Tests (tests/test_p21_notebook.py, 8 passed in 2.4 s)

1. valid nbformat 4 JSON; every code cell has `outputs == []` and `execution_count is None`.
2. required cells present and strictly ordered (GPU check, mount, settings, clone, pip, symlink, build, within, classical, ccnn, eegnet, compact, comparison, release).
3. settings names `RAW_DIR`, `DRIVE_DIR`, `REPO_URL` (exact URL), `BRANCH`, `LOSO_OUT` assigned at line start; `OO.ebr` check and `os.listdir` present.
4. the only `pip install` is `!pip install -q pyyaml joblib`; no `-r` form, no `requirements.txt` anywhere in code.
5. symlink cell covers reports, outputs/models, the raw folder and the built windows.
6. every `!python -m scripts...` line (with `{VAR}` substituted) parses with the real `build_parser()` of its script (unknown option or bad choice raises SystemExit) and the build/sweep arguments are the plan's (`--resume`, continuous, both, banks, 1 s / 0.25 s, `--windows 1 --methods fbcca lda --cv-repeats 5`).
7. three network cells, exactly one method each, writing to `{LOSO_OUT}`.
8. the comparison cell is executed on synthetic within/LOSO summary CSVs: columns `within lda`, `LOSO lda`, `Mean (subjects)` appear, S10 sorts after S02, the cohort Mean/SD rows are not treated as subjects.

A variant with `pip install -r requirements.txt` fails test 4 (the regexes match it); a misspelled option (e.g. `--stride-secs`) fails test 6 through argparse. Not run on Colab: the notebook has never executed on a real Colab runtime (no access); the Colab-only cells (`google.colab`, `!` and `%cd` magics) are not exercised by tests.

## Manual steps that cannot be automated (for the human run)

1. Upload the recordings to Drive, one folder per subject (`S01/OO.ebr`, ..., S06-S40 included), e.g. `MyDrive/ssvep/raw/`. Agents never touch these files.
2. Open `notebooks/loso_colab.ipynb` in Colab (File > Upload notebook, or open from GitHub once the branch is pushed by Sebastian; the notebook clones `BRANCH` from `REPO_URL`, so the branch must exist on that remote; the repository must be public or the clone needs a token, which this notebook does not handle).
3. Runtime > Change runtime type > GPU (T4). Credits / compute units are bought or granted on the Colab account by Sebastian; nothing here can verify them.
4. Authorise the Drive pop-up when step 2 runs.
5. Edit the settings cell if the Drive paths differ.
6. After a disconnect: run steps 1-6 again, then the interrupted cell. Run networks one cell at a time; `compact_eegnet` (~12.5 h) needs several sessions.
7. Download `summary.csv`, `per_subject.csv`, `folds.csv` from `DRIVE_DIR/reports/<LOSO_OUT>` and drop them into `reports/` of the repository for the verifier/scribe.
8. Run the last cell (or Runtime > Disconnect and delete runtime) to stop credit use.

## Deviations from the plan

1. **Extra symlink `data/processed_continuous` -> Drive.** Settled point 12 lists raw, `reports`, `outputs/models`. Without persisting the built windows, `--resume` would rebuild 40 subjects at every session. Windows are derived data in an ignored folder; no raw content moves.
2. **Within reference out-dir `reports/window_sweep_colab`** (a new folder, not `reports/window_sweep`, so the P20 S01-S05 reference is never overwritten).
3. `--save-models` and `--models-dir` are used in the network cells so the `outputs/models` symlink has a purpose (state dicts moved to CPU, builder 2).
4. `nbformat` is not listed in `requirements.txt`; it is installed transitively by `jupyter` (already listed) and is present in `.venv`. Not changed.
5. The comparison table uses the `summary.csv` accuracy column (`Acc (%)`, unsmoothed); smoothed values are in `LOSO_OUT/per_subject.csv`.

## Full suite

`.venv/bin/python -m pytest tests/ -q -o addopts=""` alone (includes the 8 notebook tests): `1337 passed, 22 warnings in 788.91s (0:13:08)`, log mas/state/scratch/p21_notebook_full.log.

## Reference consultations (R11)

None. `reference/ssvep-eeg-xai/` was not opened.

## Sources

mas/05_PITFALLS.md PF-40; 02_plan.md settled point 12; CLIs of scripts/build_windows.py, scripts/benchmarks/benchmark_window_sweep.py, scripts/benchmarks/benchmark_loso.py (`build_parser`); runtimes from 03_changes_ml-engineer.md and 03_changes_deep-learning.md.

## Questions

ACK 02_plan.md data-signal 2026-10-28
