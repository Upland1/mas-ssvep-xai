# P04 · 04 · Tests

Status: DRAFT
Author: synthetic-tester
Reads: 02_plan.md, 03_changes_*.md, mas/RULES.md, mas/05_PITFALLS.md

## Tests added

| Test id | Simulates | Expected | Tolerance | Source of the expected answer | Catches bug | Result |
|---|---|---|---|---|---|---|
| `tests/test_pxx_....py::test_...` | | | | [n] / analytic / [own] | PF-x / — | PASS / FAIL |

<!-- "Catches bug": the historical or plausible buggy variant this test
would fail on (cross-trial, unsorted, wrong axis, no-op, leaked fit).
Each was checked by running the test against that variant. -->

## Command

```bash
python -m pytest tests/ -q
```

## Output summary

<!-- Pass/fail counts and runtime. Failures pasted in full. -->

## Coverage gaps

<!-- Planned tests not written, and anything in 03_changes_*.md no test
covers. Any tolerance loosened from the plan is listed here with the reason. -->

## Reference consultations (R11)

## Sources

1.

## Questions
