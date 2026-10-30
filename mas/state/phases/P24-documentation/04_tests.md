# P24 · 04 · Tests

Status: READY
Author: synthetic-tester
Reads: 02_plan.md, 03_changes_scribe.md, mas/RULES.md, the five deliverables

## Tests added

`tests/test_p24_docs.py` (NEW; 34 test cases, data-free; the `reports/` check skips when `reports/` is absent). Own design, adopting the scribe's proposal (Sources section, `reports/` paths, SVG parse) and extending it. The expected answers are structural (a path exists, a heading exists), not numerical.

| Test | Simulates | Expected | Catches | Result |
|---|---|---|---|---|
| `test_document_exists` (5) | the five deliverables | files exist | a deliverable not saved (the v2 report was blocked in the scribe run) | PASS |
| `test_markdown_has_sources_section` (4) | README, RESEARCH_LOG, report v2, progress report | exactly one `## Sources` heading, non-empty body | missing or empty Sources (R10) | PASS |
| `test_svg_parses_and_has_sources_note` | the infographic | XML parses, root is the svg-namespace `svg`, a text element contains "Sources" | malformed SVG, wrong namespace | PASS |
| `test_cited_reports_paths_exist` (5) | every `reports/...` path cited | exists; globs match at least one file; placeholders (`<S>`, `{a,b}`, `...`) skipped; `mas/state/reports/` excluded by construction | a citation of a CSV or log that was never produced | PASS |
| `test_cited_mas_and_docs_paths_exist` (5) | every `mas/...` and `docs/...` path | exists; `B00x` blocker ids matched by prefix; `Pxx` placeholders and git-ignored `mas/state/scratch/` run-time paths skipped | stale paths | PASS |
| `test_no_nonexistent_phase_report_cited` (5) | `mas/state/reports/Pnn.md` citations | each file exists | a citation of a phase report that does not exist | PASS |
| `test_no_bare_compact_model_name_in_tables` (4) | table cells of the four Markdown files | no cell equal to "compact" (case-insensitive, markup stripped) | PF-31 naming (compact_cnn vs compact_eegnet) | PASS |
| `test_privacy_no_vendor_terms` (5) | all five deliverables | no line matches the guard's vendor pattern, built from string fragments | a vendor or tool mention in a public file | PASS |

Non-vacuity check: `_exists` returns False for a non-existent `reports/` file and for `mas/state/blockers/B999`. Extracted citations per document (reports paths / mas-docs paths): README 55/20, RESEARCH_LOG 62/14, report v2 37/13, progress report 34/11, SVG 10/5.

## Command

```bash
.venv/bin/python -m pytest tests/test_p24_docs.py -q -o addopts=""
.venv/bin/python -m pytest tests/ -q -o addopts=""
```

## Output summary

- `tests/test_p24_docs.py`: 34 passed (0.07 s).
- Full suite: 1560 passed, 22 warnings in 1042.02 s (slow because the `make all` job ran concurrently).

## Findings

No cited path is missing and no document fails a check; no xfail marks. The first version of the test produced false positives that were fixed in the test, not in the documents: a trailing `*` of a glob was being stripped; blocker ids are cited by prefix (`B003` for `B003-cohort-beyond-S05.md`); `Pxx` is a placeholder; `mas/state/scratch/make_stamps/` (README section 14) is a git-ignored directory created by `make`. Nothing is left for the scribe from these checks.

## Coverage gaps

- Numbers in the documents against CSVs are not tested here (reviewer's acceptance check 1).
- The PF-31 check is conservative: it flags only table cells equal to a bare "compact", not prose.
- Existence of a path is checked, not that it holds the quoted value. The `reports/` check depends on the local main tree and skips on a data-free CI.

## Reference consultations (R11)

None.

## Sources

1. `mas/state/phases/P24-documentation/02_plan.md`, "Tests required".
2. `mas/RULES.md` (R10), `mas/05_PITFALLS.md` (PF-31, named in the assignment).
3. The guard hook's vendor pattern (reproduced from fragments only).

## Questions

## Round 2 (fix)

Status: READY

Trigger: `06_verify.md`, reason 3. In the clean clone after `make all`, `test_cited_reports_paths_exist` failed for four documents (`mas/state/scratch/p24_make/pytest_clone.log`) on paths a clone does not have.

MODIFIED `tests/test_p24_docs.py`:

- The checked tree is the repository or the one named in `P24_DOCS_ROOT`.
- A cited `reports/` path passes if it exists. If it does not, it can pass only when the tree is a make-all clone, meaning `reports/` exists, `reports/logs/` does not, and `reports/legacy_leaky/` does. In that case one of two conditions must hold:
  - V-6 (`02_plan.md`): the path is, or lies under, one of the outputs `all` does not produce. These are `reports/loso_w1`, `loso_w1_all`, `loso_w1_fbcca_all`, `window_sweep_w1_all` (`make loso-all`), `reports/logs` (V-6 "logs") and `reports/diagnostics`. Matching is exact or by prefix plus `/`, so `reports/loso_w1_s01/...` is not covered. `reports/diagnostics` is not named in V-6. It is listed because its only cited file, `p11_seed_spread_eegnet.csv`, comes from `scripts/diagnostics/network_seed_spread.py`, which no Makefile target runs (`grep seed_spread Makefile` finds nothing). The reviewer should confirm this class.
  - V-2: the path is one of the Era-A files (`flagship_S*.csv`, `eegnet_benchmark_{cpu,cuda}.csv`, `compact_cnn_benchmark_cpu.csv`, `shallow_convnet_benchmark_cpu.csv`, `classification_report_*.txt`, `feature_selection_sfs_{audit,diagnostics}_S03.csv`), and `reports/legacy_leaky/<f>` exists in that tree.
- In the main tree, which has `reports/logs/`, every cited path must still exist as written.
- NEW `test_reports_path_rule_synthetic` builds temporary trees with known answers:
  - In both the main-like and clone-like trees, a missing ordinary path fails, a non-V-6 neighbour (`reports/loso_w1_s01/summary.csv`) fails, and a V-2 file whose `legacy_leaky` copy is missing fails.
  - The V-6 and V-2-mapped paths fail in the main-like tree and pass in the clone-like tree.
  - A tree without `legacy_leaky/` is not treated as a clone.

Commands and output:

```bash
.venv/bin/python -m pytest tests/test_p24_docs.py tests/test_p24_make_all.py -q -o addopts=""
# 53 passed in 2.71s
P24_DOCS_ROOT=$PWD/mas/state/scratch/clean_clone .venv/bin/python -m pytest tests/test_p24_docs.py -q -o addopts=""
# 35 passed in 0.25s
```

Non-vacuity check on the clone root: `_is_make_all_clone` is True. 32 cited paths do not exist as written, and the rule accepts every one: README 6, RESEARCH_LOG 20, report v2 4, progress report 2. These are the same paths as in the verifier's log. They break down as 8 V-2 files with their `legacy_leaky` copies present, 9 `loso_w1`/`loso_w1_all` citations, 14 `reports/logs` citations and 1 `reports/diagnostics` file. I ran no `make` target and no real-data script.
