# Blocker B005: the delivered raw data holds 10 of the 23 recordings in 01_DATA_SPEC §4

- Opened: 2026-10-24 by orchestrator
- Phase: P00
- blocking: P00 (acceptance "inventory matches `01_DATA_SPEC.md` §4 row for row")
- Status: resolved 2026-10-24

## Question

The P00 run (`mas/state/phases/P00-bootstrap/05_run.md`, log
`reports/logs/P00/inventory_raw_20261024_141334.log`) ended with
`10 files, 5 subjects, 0 deviations`, exit 0. `reports/raw_inventory.csv` has one
row per subject for `OO` and `mOO` only. Every one of those 10 rows matches §4
(samples, duration, stim events, session start to the minute, 99th pct to 0.1 µV).

Absent (13 rows of §4): `C` and `mC` for S01–S05, S02 `online_C`, S03
`cb_mas_mcb`, S05 `online_OO`. B002 was resolved by copying the `.ebr` files from
`../SSVEPs_OO_mOO/`; the folder name suggests only the OO/mOO sessions were ever
in it.

No phase of `03_ROADMAP.md`, `04_REFERENCE_RESULTS.md` or `02_REQUIREMENTS.md`
names `C`, `mC`, the online runs or `cb_mas_mcb` as an input (grep, 2026-10-24).
The spec uses `OO` (main session) and `mOO` (P20 pseudo-online test run).

## Options and consequences

| Option | Consequence |
|---|---|
| A. Sebastian adds the 13 missing files to the raw-data folder | runner re-runs the inventory (≈1 s); acceptance as written; no deviation |
| B. Accept the 10-file inventory as the delivered dataset | acceptance read as "every delivered file matches its §4 row; the 13 absent rows are listed"; deviation recorded in `decisions.md` and signed by the scientific reviewer; the verifier joins on the 10 delivered rows and lists the 13 absent ones; no later phase is affected |

## Recommendation

B if the C/mC/online recordings are not available to you; A if they are (it costs
nothing and keeps the inventory complete for the cohort's record).

## Resolution (Sebastian)

2026-10-24: option B. The 10-file inventory (OO, mOO for S01–S05) is accepted as the delivered dataset. P00 acceptance is read as "every delivered file matches its §4 row; the 13 absent §4 rows are listed"; the scientific reviewer signs the deviation in the results review.
