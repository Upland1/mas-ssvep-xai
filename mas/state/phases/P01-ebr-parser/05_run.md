# P01 · 05 · Run

Status: READY
Author: runner
Reads: 02_plan.md (Amendment, pre-run audit Round 1), 07_review.md (pre-run audit Round 2 PASS)
Branch / commit: phase/P01-ebr-parser, HEAD 477550967a7d04aab2ceb217d47c59735c992dd0 (clean tree at start)
Machine: Linux 7.0.0-38-generic, Python 3.12.3 (.venv), CPU only, no GPU

## Commands executed

All from the repo root, in this order. Budget: LOCAL_RUN_BUDGET_MIN 30; every run took under 1 s.

| # | Command | Runtime | Exit | Log | Outputs |
|---|---|---|---|---|---|
| 1 | `sha256sum reports/raw_inventory.csv` | <1 s | 0 | (console) | `e134a372b164bf42b4911c56ca98be47742f45442f0bad37f9923ed4d1b16c14  reports/raw_inventory.csv` |
| 2 | `.venv/bin/python scripts/exploration/inventory_raw.py --out reports/P01/raw_inventory_parser.csv` | 0 s (whole seconds) | 0 | `reports/logs/P01/inventory_raw_default_20261024T162513.log` | `reports/P01/raw_inventory_parser.csv` |
| 3 | `cmp reports/raw_inventory.csv reports/P01/raw_inventory_parser.csv` | <1 s | 0 | (console) | no output |
| 4 | `.venv/bin/python scripts/exploration/inventory_raw.py --strict --out reports/P01/raw_inventory_parser_strict.csv` | 0 s (whole seconds) | 0 | `reports/logs/P01/inventory_raw_strict_20261024T162517.log` | `reports/P01/raw_inventory_parser_strict.csv` |
| 5 | `cmp reports/raw_inventory.csv reports/P01/raw_inventory_parser_strict.csv` | <1 s | 0 | (console) | no output |
| 6 | `sha256sum reports/raw_inventory.csv` | <1 s | 0 | (console) | `e134a372b164bf42b4911c56ca98be47742f45442f0bad37f9923ed4d1b16c14  reports/raw_inventory.csv` |

Each python log starts with `# command:`, `# HEAD:`, `# start:` lines and ends with `# exit: 0 runtime_s: 0`
(exit code taken from PIPESTATUS of the python process).

Summary line printed by both runs (verbatim):

```
10 files, 5 subjects, 0 deviations
```

Followed by `Saved: reports/P01/raw_inventory_parser.csv` (run 2) and
`Saved: reports/P01/raw_inventory_parser_strict.csv` (run 4). The full 10-row table is in each log.

## Human run requests

None.

## Produced files

- `reports/P01/raw_inventory_parser.csv`
- `reports/P01/raw_inventory_parser_strict.csv`
- `reports/logs/P01/inventory_raw_default_20261024T162513.log`
- `reports/logs/P01/inventory_raw_strict_20261024T162517.log`

(All git-ignored; not committed.)

## Anomalies

None. Both runs exit 0, both cmp silent with exit 0, both sha256 lines identical.
`mas/state/phases/P01-ebr-parser/log.md` shows as modified in the working tree (not by the runner); left uncommitted.

## Questions

None.
