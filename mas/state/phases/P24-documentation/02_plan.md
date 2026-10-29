# P24 · 02 · Plan

Status: READY
Author: orchestrator
Approval: PLAN_APPROVAL auto

## Goal

Produce the project's written deliverables from the phase reports and CSVs, and a
single `make all` that regenerates every CSV from the raw recordings on a clean clone.

## Settled points (inferred; recorded in decisions.md)

1. **Language and format.**
   - Everything is in English (the repository language), in Markdown, plus one SVG for
     the infographic.
   - The academic report goes in `docs/report/v2/report.md`, about 5 pages. `docs/report/v1/`
     stays as the P06-era history.
   - The infographic is `docs/infographic/methodology_infographic.svg`, one page. The v1
     SVG in `docs/report/v1/` stays.
   - The progress report is `docs/progress_report/progress_report.md`.
   - No PDF build is required, since pandoc is not installed. Optional exports stay out
     of the repository.
2. **Numbers.**
   - Every number comes verbatim from a CSV or log under `reports/` (or a phase report
     that quotes one), with its path in a source note or footnote.
   - Reference targets (R-x) are labelled as the original project's numbers, never as
     results of this repository.
   - Per-subject tables carry the data source (R9).
   - Wording rulings from the phase reviews are binding:
     - "unsupervised per-subject normalization (test-time, offline upper bound)";
     - "direction not observed";
     - "GNN ≥ lda on S02/S05", never "beats";
     - P22 `within_lda` labelled within-subject;
     - PF-31 names (`compact_cnn` vs `compact_eegnet`);
     - the PF-30 readings;
     - the 3-channel wording for cohort-39 `common`.
3. **Citations (R10, mas/CITING.md).**
   - Each document has a `## Sources` section.
   - The paradigm paper is cited as given in `mas/01_DATA_SPEC.md` §3: Chailloux Peguero
     et al. (2023), Frontiers in Neuroscience 17:1142892. The scribe opened the spec, not
     the paper, so the entry says so.
   - Methods papers are cited only where a phase report already cites an opened source.
     Otherwise the scribe writes `[source not opened in this run]`; nothing is invented.
4. **README.**
   - It replaces the operator README.
   - The operator content (MAS workflow, `mas_status.py`) is reduced to a short
     "Development process" section that points to `mas/README.md`.
   - "Usage for every script" is a table: script, purpose, minimal command, outputs.
     It is generated from each script's argparse `description` where one exists.
5. **RESEARCH_LOG.md.**
   - It becomes one chronological narrative, P00 → P23, with a before/after line per fix.
   - Every existing entry's facts are kept, merged into the narrative, not deleted.
   - CHANGELOG.md stays as is.
6. **Progress report.**
   - One section per professor assignment, as listed in the roadmap task 5.
   - Each section covers: question, what was done (phase), result table, open questions.
   - The closing section lists every open carry-forward and blocker from
     `mas/state/decisions.md` and `mas/state/blockers/`.
7. **`make all` (data-signal).**
   - Per-phase targets `p00` … `p23` reproduce each phase's run commands as recorded in
     its `05_run.md`, with explicit `--subjects S01 S02 S03 S04 S05` wherever discovery
     would now find 39 subjects.
   - `all` = every phase target in order.
   - Optional targets, kept outside `all`:
     - `loso-all` (P21 39-subject classical LOSO and within reference);
     - `colab` (none).
   - Excluded entirely: the P21 39-subject ccnn, which took ≈ 1.5 h GPU (Sebastian
     limited networks to cohort 5).
   - `RAW_DIR ?= data/raw` is passed to every script that reads recordings. The verifier
     runs it on a clean clone with `RAW_DIR` pointing at the existing recordings.
     Recordings are read only by project scripts launched through `make`.
   - Targets are idempotent: they write to the same out-dirs as the phase runs, inside
     the clone.
   - A `make all-dry` (or `-n`) listing is tested. NEW `tests/test_p24_make_all.py`
     checks:
     - every target's commands parse against the real argparse parsers;
     - every out-dir in the reports appears in some target;
     - no target omits `--subjects` where the script discovers subjects.
   - The builder writes a runtime table per target from the phase logs' measured times.
8. **Budget for `make all`.**
   - The verifier runs `make all` once on a clean clone under `mas/state/scratch/`.
   - If the measured total from the phase logs is ≤ 4 h, it runs locally, detached and
     resumable, under Sebastian's standing preference that long local runs are done by
     the team (2026-10-28). The authorisation is recorded in decisions.md.
   - If it is > 4 h, the orchestrator stops and asks Sebastian first: he limited a long
     run on 2026-10-28 because of its duration.
   - Reproducibility check: every CSV regenerated in the clone is compared with the main
     tree:
     - exact (byte or value) for CPU paths;
     - for GPU paths, within the tolerance stated in that phase's report, with any
       difference listed.

## Work split (order: 1, then 2)

| # | Agent | Files | Tasks |
|---|---|---|---|
| 1 | data-signal | MODIFIED `Makefile`, NEW `tests/test_p24_make_all.py`, optionally NEW `scripts/run_all.sh` | task 6; settled 7, 8 (runtime table) |
| 2 | scribe | MODIFIED `README.md`, `RESEARCH_LOG.md`; NEW `docs/report/v2/report.md`, `docs/infographic/methodology_infographic.svg`, `docs/progress_report/progress_report.md` | tasks 1–5; settled 1–6 |

## Tests required

- `tests/test_p24_make_all.py` (above).
- A test that each document's `## Sources` section exists and that every `reports/...`
  path cited in the documents exists in the main tree. It may skip when `reports/` is
  absent, so CI stays data-free.

## Run commands (for the verifier)

```bash
# 0. clean clone of the phase branch under mas/state/scratch/clean_clone (git clone --no-hardlinks . <dir>; checkout HEAD)
# 1. make venv-free run with the main tree's .venv: make -C <clone> all PYTHON=<main>/.venv/bin/python RAW_DIR=<main raw folder>
# 2. compare every regenerated CSV with the main tree (exact for CPU; tolerance for GPU paths)
# 3. document-number cross-check (each number in README, report, progress report, infographic → CSV/log)
```

## Acceptance checks

1. The reviewer has checked every number in the documents against a CSV.
2. `make all` succeeds on a clean clone with only the raw recordings added.
3. The regenerated CSVs match: exactly for CPU paths, within the stated tolerance for
   GPU paths.
4. Every document has its Sources section, and the privacy scan of the staged diff with
   the guard's term list is clean (by reference only).

## Sources

- `mas/03_ROADMAP.md` P24.
- `mas/CITING.md`.
- `mas/01_DATA_SPEC.md` §3.
- `mas/state/reports/P00.md`–`P23.md`.
- `mas/state/decisions.md`.
- `Makefile`.

## Questions
<!-- receivers append: ACK <agent> <YYYY-MM-DD>, then questions; answers appended, never deleted -->
