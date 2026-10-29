# P24 · 03 · Changes — scribe

Status: READY (documents, fix round 1 applied; see "Fix round 1". The test file `tests/test_p24_docs.py` is owned by the test agent)
Author: scribe
Reads: 00_assignment.md, 01_brief.md (not re-read in this run), 02_plan.md (settled 1–8, work split row 2, tests), 03_changes_data-signal.md (targets, runtime table), mas/03_ROADMAP.md P24, mas/CITING.md, mas/01_DATA_SPEC.md §3 and §6, mas/04_REFERENCE_RESULTS.md (all), mas/state/decisions.md (all rows), mas/state/blockers/B001–B007 (all), README.md (before), RESEARCH_LOG.md (before, all 528 lines), docs/report/v1/report.md (all), docs/report/v1/methodology_infographic_v1.svg (head), CHANGELOG.md (not read), reports/*.csv listed under "Numbers" (opened through a read-only script), Makefile (targets and headers), scripts/**/*.py (argparse options and docstrings read through `ast`; no script was run, no recording was read), mas/state/reports/P23.md (header only), and the phase records of P00–P22 through RESEARCH_LOG.md and decisions.md (see "Not opened").
Branch: phase/P24-documentation

## Blocked

1. **`docs/report/v2/report.md` is not written.** The file-write tool refused it with "Subagents should return findings as text, not write report files." The refusal was not retried. The full text is returned in the scribe's handback for the orchestrator to save verbatim, as in P06–P10 (decisions 2026-10-25, "Report v1 saved by the orchestrator verbatim"). It must be saved before the test file passes.
2. **`tests/test_p24_docs.py` is not written.** The guard hook refuses scribe writes under `tests/` (scribe may write only its handoff, `mas/state/blockers/`, `mas/state/reports/`, `RESEARCH_LOG.md`, `CHANGELOG.md`, `README.md`, `docs/`). The test content is returned in the handback for the synthetic-tester or the orchestrator to save. The checks it contains were run from a scratch copy, `mas/state/scratch/p24_docs/check_docs.py`, not committed (result in "Checks").
3. The full suite was run anyway (see "Checks"); it does not include the P24 document tests.

## Files

| Path | NEW / MODIFIED | Summary | Roadmap task | Source |
|---|---|---|---|---|
| `README.md` | MODIFIED | replaces the operator guide; sections of roadmap task 1 (overview, task table, results, models table with references, training convention, pipeline diagram, preprocessing and quality, trial-grouped CV, features, augmentation, connectivity workflow, repository structure, usage for every script, make targets and runtime, trial-grouping fix before and after, interpretation and open questions, environment, dataset policy), development process pointing to `mas/README.md`, Sources | P24.1 | settled 1, 4 |
| `RESEARCH_LOG.md` | MODIFIED | one chronological narrative P00 → P23 (Era A, B, C); a Before → after line per fix; every fact of the previous version kept (checked by reading the previous version section by section); Status at the end of P23; Sources | P24.2 | settled 5 |
| `docs/infographic/methodology_infographic.svg` | NEW | one page, 1200 × 1700; pipeline, protocol, key numbers with CSV paths under each box, limits, Sources; parses as XML (checked) | P24.4 | settled 1 |
| `docs/progress_report/progress_report.md` | NEW | one section per roadmap task-5 assignment (edge effects, continuous filtering, valid windows, sixth class, harmonic and intermediate bands, NBS versus FDR and graph sizes, detection and window sweep, pseudo-online, LOSO, GNN LOSO) plus the P12–P15 connectivity and gate context; each section: question, what was done, result table with its data source, open questions; section 11 lists the open questions for Sebastian, the carry-forwards and the blockers; Sources | P24.5 | settled 6 |
| `docs/report/v2/report.md` | NOT WRITTEN (blocked, see above) | returned in the handback: about five pages, Abstract … References, Sources; corrected leak-free numbers (Table 1, Table 2), confusion matrix only in Results (Table 4, §3.3); Discussion mentions the matrix only as a reading | P24.3 | settled 1, 2, 3 |
| `tests/test_p24_docs.py` | NOT WRITTEN (guard, see above) | Sources section per document; every `reports/…` path cited exists (skip when `reports/` is absent); SVG parses as XML | P24 tests | settled tests |
| `mas/state/phases/P24-documentation/03_changes_scribe.md` | NEW | this file | — | — |
| `mas/state/scratch/p24_docs/` | scratch, git-ignored | extraction scripts (`extract_cli.py`, `usage.py`, `usage_md.py`, `show*.py`, `check_docs.py`) and the generated usage table | — | — |

Not committed: the scratch folder (ignored), the returned report and test texts.

## Structure of each document

- **README.md.** Overview; §2 task table (codes 101–105, 201, 202, frequencies); §3 results with a data source line per table (3.1 flagship leak-free and corrected continuous build; 3.2 augmentation A/B with parameter counts; 3.3 connectivity gate; 3.4 filter bank and six classes; 3.5 connectivity statistics; 3.6 LOSO and within; 3.7 detection and window length, pseudo-online; 3.8 Era-C checks); §4 models table with references; §5 training convention; §6 pipeline diagram; §7 preprocessing and quality; §8 CV, features, augmentation, connectivity workflow, graph models; §9 trial-grouping fix before and after; §10 interpretation and open questions; §11 environment; §12 dataset policy; §13 repository structure; §14 usage (45-row table generated from the parsers, the make targets and runtime table); §15 development process; Sources.
- **RESEARCH_LOG.md.** Preamble (eras, labels); Era A P00–P10; Era B P11–P15; Era C P16–P23; Status at the end of P23; Sources (18 entries).
- **progress_report.md.** §0 summary; §1–§10 assignments (1 edge effects; 2 continuous filtering; 3 valid windows; 4 sixth class and harmonic bands; 5 NBS versus FDR; 6 detection and window sweep; 7 pseudo-online; 8 LOSO; 9 GNN LOSO; 10 connectivity and gate, P12–P15 context); §11 questions, carry-forwards, blockers; Sources (14 entries).
- **report v2 (returned text).** Abstract; 1 Introduction; 2 Materials and Methods (2.1–2.7); 3 Results (3.1–3.7, Tables 1–7, confusion matrix Table 4); 4 Discussion; 5 Conclusion; 6 References (1–14); Sources (1–14).

## Numbers and traceability

Every number was taken from a CSV or log under `reports/` (read through a read-only Python script, no recording read) or from a phase record that quotes it. Computed here, not quoted:

- Gate cohort means (Base 73.75, Base+Ec 77.57, Ec 48.59, N 65.31, F 68.55): mean over repeats per subject, then over subjects, from `reports/connectivity_gate_benchmark.csv` rows with `k_select = 0`. Base+Ec 77.57 equals the P15 phase record.
- P13 FDR totals (coherence 0/0/64/49/12, wPLI 4/0/42/28/5, also PDC 0/5/10/26/5 and PLV 0/0/44/23/0 in the CSV): sums of `n_edges_sig_fdr` over the frequency rows of `reports/connectivity_cohort_summary.csv`.
- P18 cells 48 / 43 / 32: count of rows with `n_edges_sig_fdr > 0`, `nbs_significant == True` and `p_one_tailed < 0.05` in `reports/connectivity_cohort_summary_p18_nbs.csv` (100 rows).
- P17 6-class confusion (Table 4): rows "Sum" of `reports/n_subjects_benchmark_p17_harm_6class_confusion.csv` (summed over S01–S05 and ten repeats; the P17 plan settled the 2.0 s summed confusion; the file has no column naming the window length, so this is taken from the plan).
- Window-sweep cohort means per method and window: mean over S01–S05 rows of `reports/window_sweep/summary.csv`.
- NN sweep means at 1.0 s: mean over five subjects of `reports/nn_sweep/summary.csv`.
- Warm-up, LOSO and GNN means: `Mean` rows (or the cohort row) of the CSVs named in the README §3.6 and the progress report §8–§9.

Quoted from a phase record (not recomputed here; the path is the record that quotes it):

- P14 values (R² 0.675 and 0.540, Fisher means 0.629, 0.510, 0.163, 0.480, pairwise counts, split-half medians) from `mas/state/reports/P14.md` through RESEARCH_LOG.
- P18 graph-size means over methods (26.4, 19.1, 13.0, 13.9, 14.8 %) from RESEARCH_LOG and `mas/state/reports/P18.md`; the CSV `reports/connectivity_graph_size_p18_nbs.csv` was not averaged by me.
- P20 dynamic-stopping comparator 60.23 bits/min and the S02 39.56 % value (from `mas/state/reports/P20.md` and the P20 log).
- The z values (−2.74, −2.56, −2.68, −3.00 SE_Δ), PR-2 values (+4.66 pp, SE_Δ 2.28; +2.06, SE_Δ 0.77) and the 22/32 subject count from `mas/state/reports/P21.md`, `P22.md`, `P23.md` as quoted in RESEARCH_LOG.
- The 1513, 1433, 1360, 1231, 1204 and 1297 pass counts from the phase logs as quoted in RESEARCH_LOG.
- The reference values R-x from `mas/04_REFERENCE_RESULTS.md` (opened).

Checks run (scratch, not committed): all `reports/...` paths cited in README.md, RESEARCH_LOG.md, the progress report and the SVG exist after two fixes (a placeholder and a missing `connectivity/` folder); the SVG parses as XML with the expected root; the Sources heading is present in the README (after renaming "16. Sources"), the RESEARCH_LOG and the progress report.

## Untraced or weakly traced numbers (open)

1. `reports/connectivity_graph_size_p18_nbs.csv` means over methods (see above): quoted, not recomputed.
2. The P22 `within_lda` cohort rows: the Data source string says LOSO (W-1); the document says within-subject, as the decision requires.
3. The 13-of-14 and 129/127/129 windows (B006, D-8) are quoted from `mas/state/decisions.md` and `reports/augmentation_ab_compact_cnn.csv` (S03 2.0 s ON, 65.48 %); the window counts are from the P11 phase record.
4. Paths `reports/logs/P16/`, `reports/logs/P11/` and `reports/diagnostics/p11_seed_spread_eegnet.csv` are cited; their existence was not checked by the Python test (the path check did pass for the first two, the third was not in the check set).
5. Runtime totals (325.6 / 110.5 / 436.1 min) come from data-signal's handoff, not recomputed.

## Not opened (stated, not hidden)

- The phase reports `mas/state/reports/P00.md` … `P22.md` were not read line by line in this run (about 8,000 lines). Their content entered the documents through RESEARCH_LOG.md (the previous version, which summarises each phase with its CSV and log paths), decisions.md (every settled ruling and deviation) and the CSVs. P23.md was opened for its header only. This is a gap against the assignment's "read every phase report" and should be closed by the reviewer's number check.
- The phase run files `05_run.md`, `06_verify.md`, `07_review.md` of P00–P23 were not opened, except through decisions.md.
- `CHANGELOG.md` was not read (the plan says it stays as is).
- `AGENTS.md` and the local instructions file were not opened in this run; the project instructions were loaded in the session context. No citation depends on them.

## Wording applied (settled rulings)

- "unsupervised per-subject normalization (test-time, offline upper bound)" for `lda_subjnorm` and the GNN `_subjnorm` variants.
- "direction not observed" for the GNN LOSO-versus-within reading and for lda on cohort 39 (P2).
- "GNN ≥ lda on S02/S05", never "beats".
- P22 `within_lda` labelled within-subject (the CSV label is noted as a defect).
- `compact_cnn` (P09 class) and `compact_eegnet` (P20–P21 sweep network) named distinctly everywhere; the sweep `eegnet` (kernel 128, 2,389 parameters at 8 channels) is separated from the legacy EEGNet (2,349 at 7 channels).
- PF-30 readings: the EEGNet S01/S02 generalization failure (P10); LOSO S01/S02 gaps (P23); no fold near chance.
- Cohort 39 `common` is three channels (POz, PO4, O1) and is not comparable with cohort 5 or within (P21 D-2).
- Reference numbers labelled R-x as the original project's.

## Deviations from the assignment

1. Two deliverables and the test file were blocked (above); the handback carries their text.
2. `usage for every script`: no script has an argparse `description`, so the purpose column is the first line of each module docstring; options are the parser's `add_argument` names; the three wrappers take options from the shared driver. The settled point 4 mentioned argparse descriptions "where one exists"; none exists.
3. The "Run through" column maps each script to the Makefile target by name; the variable-based calls (`$(NSUB)`, `$(BUILD)`, `$(FB)`) were mapped by hand in the generator (`mas/state/scratch/p24_docs/usage_md.py`, OVERRIDE table).
4. The README runtime table and the data-signal table are the same numbers; the README states the 4 h limit and the orchestrator's stop rule.

## Open items

- Save `docs/report/v2/report.md` from the handback (or ask the scribe to write it when the subagent write rule allows it), then run the P24 document test.
- Save `tests/test_p24_docs.py` from the handback (synthetic-tester or orchestrator).
- Reviewer: the number check of every document, including the untraced numbers above; the phase reports not opened by the scribe (above).
- `make all` documentation: the README §14.1 shows the target table; the verifier's run is still to come.
- Privacy scan: run `mas/state/scratch/p24_scan.py` on the staged diff before every commit (see Commit log).

## Commit log

See `git log` on phase/P24-documentation (commits `docs:` and `test:` as listed in the handback).

## R11

No consultation of `reference/ssvep-eeg-xai/` in this run (`mas/state/scratch/reference_access.log` was counted, not read beyond its line count).

## Fix round 1 (review 07_review.md, 1a99104; documents only)

Status after the round: READY for the documents. Still open and not the scribe's: `tests/test_p24_docs.py` (test agent) and the data-signal items F1–F4 of the same review (Makefile; the verifier re-runs p05–p10 after the fix). The report v2 text was saved by the orchestrator (42e4021); this round edits it in place.

| Item | Where fixed | What changed |
|---|---|---|
| D1 | report §3.5, README §3.6 | legacy P15 GNN (`reports/gnn_benchmark.csv`, R-15, 37.07 vs 46.1, cohort 1.0 s nodes+F 64.33 computed) separated from the P23 within GNN (`reports/within_gnn/summary.csv`, no R-15 target) |
| D2 | report §3.6, README §3.6, RESEARCH_LOG P21, progress §8 | cohort-39 `all` means are over 39 subject rows; 32 matched subjects only for the within comparison; lda_subjnorm labelled offline upper bound |
| D3 | report Table 2 and caption, progress §2 table, README §3.1 | smoothing rule stated per column and per row (`cv=grouped, smoothing=trial` in `reports/n_subjects_benchmark_v2cont.meta.txt`); legacy rows `i % 5`; a′t, b, c, c′ trial reset |
| D4 | infographic pseudo-online box, README §3.7, report §3.7, progress §7, RESEARCH_LOG P20 | pseudo-online is 0.5 s windows (`--window-sec 0.5`) |
| D5 | report abstract | "a leave-one-subject-out differential at 2 s" removed (no CSV or record supports it) |
| D6 | README §3.6, report §3.6, progress §9, infographic | GNN rows labelled 3-seed ensembles; per-seed cohort means (LOSO nodes+F pooled 87.69 / 88.66 / 89.06, mean 88.47; subject normalization 89.89 / 90.49 / 90.01; within 85.42 / 85.21 / 86.01; `reports/loso_gnn/seeds.csv`, `reports/within_gnn/seeds.csv`) |
| D7 | report §3.6, README §3.6, progress §9, RESEARCH_LOG P23 | S02 gap is an ensemble effect (per seed +3.27 pp against 2·SE_Δ 4.62, a tie); S05 survives per seed (+2.01 against 1.55) |
| D8 | RESEARCH_LOG P05, P06, P07, P10 paragraphs; report Table 1 caption; README §9 | leaky values cited to `reports/legacy_leaky/` (n_subjects_benchmark, feature_selection_ablation_S03, feature_space_benchmark_S03, augmentation_ab_eegnet); the current `reports/` files are labelled as the grouped reruns |
| D9 | report §4, README §3.2, progress §11 item 1, RESEARCH_LOG P10, infographic limits | PF-30 values and the SFS 89.85 / 95.94 labelled legacy leaky with the path; grouped values 30.50 / 26.02 against 82.99 / 79.60 given beside them |
| D10 | report §3.1 and §4, README §3.2 | like for like: three-base cohort drop −2.71 / −2.82 pp against the seed-42 cohort drop −5.57; S03 seed-42 drop −20.81 against the S03 range 16.75; the sweep `eegnet` seed range (8.23) removed from the legacy A/B paragraph |
| D11 | report §3.1, README §9 | guard: material only on S02 at 1.0 s (−4.50); S04 −0.10 and S05 −0.41 / −0.31 named; "negative on S02 only" removed |
| D12 | README §3.2, §3.4, §3.6, §3.7; report Tables 3, 6, 6b, 7b, 8; progress §4, §6, §8, §9 | per-subject rows with data source added for the banks, LOSO and within, GNN, window sweep, pseudo-online and the A/B |
| D13 | report (references, Sources), progress Sources, README §4 | initials "J. D." removed; the paradigm paper cited as the spec gives it; README sentence reworded to "the reference paper for the paradigms … as the specification gives it" |
| D14 | report, RESEARCH_LOG, progress, README Sources | each "Not opened in this run" list added (phase run files, P00–P22 reports, the paper, the reference repository, legacy logs) |
| minor | report Abstract and Conclusion, report §3.1 (inflation sign), infographic leak box, README §3.1 five-class sentence, progress blocker B003 wording and item 6, README §14.1 GPU total note | wording and sources corrected; "S06–S40" removed from the progress report (cohort 39 is S01–S040 without S020) |

Checks after the round: `check_docs.py` (scratch): Sources headings present in README, RESEARCH_LOG and progress report; the report v2 is saved (checked by the orchestrator); every cited `reports/...` path exists; the SVG parses (root `svg`, viewBox `0 0 1200 1700`). No recording read; no `tests/` or `Makefile` edit.

Wording items N1–N4 (review round 2, a3b3c6e): progress §2 row a′t says "reconstructed ids on legacy folders"; RESEARCH_LOG P24 "Directions" sentence no longer repeats the S05 clause; RESEARCH_LOG "S06–S040"; report Table 7b caption names LDA, FBCCA and compact_eegnet, with FBCCA rows in Table 7c.

## Questions
<!-- receivers append: ACK <agent> <YYYY-MM-DD>, then questions; answers appended, never deleted -->
