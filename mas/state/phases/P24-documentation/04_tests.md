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
