# P06 · 03 · Changes — scribe

Status: READY
Author: scribe
Reads: 00_assignment.md, 02_plan.md, 06_verify.md, 07_review.md (pre-run audit and results review part 1, commit 637dad6), 03_changes_ml-engineer.md (incl. Round 1 R11), mas/RULES.md, mas/CITING.md, mas/01_DATA_SPEC.md §1, §3, §5.1, mas/04_REFERENCE_RESULTS.md R-4/R-5/R-6, mas/05_PITFALLS.md PF-01/02/04/10/11/14, mas/02_REQUIREMENTS.md §6, configs/pipeline_config.yaml, scripts/preprocessing/run_preprocessing.py, src/features/ssvep/window_mask.py, src/features/ssvep/fbcsp_extraction.py, src/features/selection/feature_selection.py, scripts/benchmarks/feature_based/benchmark_feature_selection.py, scikit-learn 1.9.1 installed source (cited lines in report.md)
Branch: phase/P06-feature-selection-cohort
Commit(s): see the `docs: P06 technical report v1 and methodology infographic` commit (SHA reported by the scribe in its run summary)

Note: `docs/report/v1/report.md` was written by the orchestrator on Sebastian's authorisation (the scribe's Write attempt on that path was refused by the tool). Its text is the scribe's Part A, then updated with the scientific reviewer's decision D-1 (07_review.md, commit 637dad6): the status line, §2.5, §3.1, §4 SFS paragraph and §5 sentence.

## Files

| Path | NEW / MODIFIED | Summary | Roadmap task | Source |
|---|---|---|---|---|
| `docs/report/v1/report.md` | NEW (orchestrator-saved, scribe-edited) | Technical report v1, academic structure (Abstract, Introduction, Materials and Methods, Results, Discussion, Conclusion, References), historical title with correction note, ablation and cohort tables copied from the CSVs, SFS row as deviation D-1 with R-4 beside it | P06.4 | [1]–[16], R9, R10 |
| `docs/report/v1/methodology_infographic_v1.svg` | NEW | Hand-written SVG of the legacy pipeline flow (OO recording → 1–60 Hz filter → 1.0 s windows → quality mask → FBCSP + FBCCA → scaler → Shrinkage-LDA → i%5 smoothing), labelled "v1 — historical", explicit white background; valid XML, render checked | P06.4 | [2], [16] |
| `mas/state/phases/P06-feature-selection-cohort/03_changes_scribe.md` | NEW | this handoff | P06.4 | — |

## Legacy behaviour implemented

None added. The report states the inherited legacy protocol: window-level `StratifiedKFold(5, shuffle, 42)` (R1, PF-01), `i % 5` trial smoothing for the 2.0 s column (R8, PF-02), fs 250 Hz on 256 Hz recordings (PF-04), per-window sub-band filtering (R3, PF-14), extractor mask vpp 0.5–120 µV / std 0.1–35 µV (R5), 7 channels (PO7 excluded), OO session, S01–S05 from the legacy folders `data/processed/<S>/`.

## Differences from the cited examples

None (no code examples used; the scikit-learn behaviour cited is read from the installed 1.9.1 source).

## Deviations from the plan

1. The report was written by the orchestrator (Sebastian's authorisation), not by the scribe, after the scribe's Write attempt was refused. Its text is the scribe's Part A plus the D-1 edits below.
2. D-1 edits to `report.md` follow the reviewer's decision (07_review.md, results review part 1, commit 637dad6, conditions (a) and (b)): the SFS row is reported as ours (89.85 / 95.94) with R-4's 84.77 / 93.40 beside it and the reason; never "reproduced"; the SFS definition is named where it appears; SFS vs Full is a ±1-window tie (0.51 pp, one window = 0.5076 pp); no conclusion is drawn from the SFS row. Condition (c) (open question to Sebastian on the original .docx or his memory of the run) is stated in §4.

## How to run / reproduce

The tables and arithmetic of `report.md` were printed from the CSVs with the script in Part C, run from stdin with an isolated interpreter (`python3 -I -`), reading only `reports/` CSVs. The arithmetic was run as `python3 -I -c` (outputs in the run summary):

```bash
python3 -I -c "print(round(90.36-87.31,2), round((90.36-87.31)/(100/197),2), round(90.36-89.85,2), round(95.94-95.43,2), round(89.85-84.77,2), round(95.94-93.40,2), round(89.85-87.82,2), round(100/197,4))"
```

Output: `3.05 6.01 0.51 0.51 5.08 2.54 2.03 0.5076`.

Cohort gains and means (`python3 -I -c` on the rounded CSV rows): gains 11.0, 5.61, 5.07, -0.5, 0.0 pp; means 83.334 (1.0 s) and 87.57 (2.0 s), as in the CSV Mean row 83.33 / 87.57.

## How I verified

- Table generation (Part C, stdin, `python3 -I`): the ablation table, the cohort table, the diagnostic table and the audit table in `report.md` equal the CSV cells (`93.4`, `64.5` kept as written; cohort Mean row blank counts as in the CSV).
- Infographic: `python3 -I` ElementTree parse OK (root 1200×720, one explicit white background rect, label "v1 — historical" present); rendered with ImageMagick `convert` to a scratch PNG and viewed; arrowheads drawn as explicit polygons because the marker did not render.
- No product or service names in `report.md` or the SVG; no data read; no reference repository opened by the scribe.

## Left to do / known limitations

- Open question to Sebastian (reviewer condition (c), not a blocker): the original .docx report or his memory of the SFS run may give the original configuration; if so, the row is revisited as a labelled re-run.
- The verifier's numeric verdict for P06 is FAIL on the SFS row in 06_verify.md; the reviewer's D-1 acceptance and the verifier's restatement are recorded by the orchestrator (`mas/state/decisions.md`), not by the scribe.
- All P06 numbers are legacy and leaky (window-level CV); they are not comparable with R-6.

## Reference consultations (R11)

None by the scribe. The original repository was not opened in this run. The consultations of the builder (Round 1, read-only) are listed in 03_changes_ml-engineer.md.

| # | Trigger (failed test / deviation / verification) | Files and lines @ commit | What I learned | What changed in my code |
|---|---|---|---|---|
| | | | | |

## Sources

1. RULE — mas/RULES.md, R1, R2, R3, R5, R6, R8, R9, R10, R11 and the era matrix.
2. DATA — mas/01_DATA_SPEC.md §1, §3, §5.1 and the sampling-rate line (256 Hz).
3. DATA — mas/05_PITFALLS.md PF-01, PF-02, PF-04, PF-10, PF-11, PF-14.
4. REQUEST — mas/03_ROADMAP.md P06 tasks 1–4 and acceptance line.
5. DATA — mas/04_REFERENCE_RESULTS.md R-4 and R-5 tables (lines 53–74), R-6 header.
6. REQUEST — mas/02_REQUIREMENTS.md §6 (line 199).
7. HANDOFF — 06_verify.md (verdict FAIL, R-4/R-5 tables, diagnostic run); 05_run.md (commit 7575405, runtimes).
8. HANDOFF — 07_review.md, pre-run audit (PASS) and results review part 1 (D-1 decision, commit 637dad6).
9. HANDOFF — 03_changes_ml-engineer.md (implementation, Round 1 investigation, R11 consultation).
10. HANDOFF — mas/state/decisions.md, P05 and P06 rows.
11. HANDOFF — mas/state/reports/P05.md §2 and §4.
12. DATA — reports/feature_selection_ablation_S03.csv and .meta.txt; reports/logs/P06/benchmark_feature_selection_20261025_035546.log.
13. DATA — reports/five_subjects_benchmark.csv and .meta.txt; reports/logs/P06/benchmark_5_subjects_20261025_035706.log.
14. DATA — reports/feature_selection_sfs_diagnostics_S03.csv, reports/feature_selection_sfs_audit_S03.csv; reports/logs/P06/benchmark_feature_selection_diag_20261025_043543.log.
15. DOCS — scikit-learn 1.9.1 installed package: feature_selection/_sequential.py:189–191; discriminant_analysis.py:48.
16. DATA — configs/pipeline_config.yaml (preprocessing block); scripts/preprocessing/run_preprocessing.py:1–7, 60–61, 116–118; src/features/ssvep/window_mask.py:17; src/features/ssvep/fbcsp_extraction.py:31, 46–47; src/features/selection/feature_selection.py:1–9.

## Questions

ACK 00_assignment.md scribe 2026-10-25

## Part C: table-generation script (run with python3 -I from stdin)

```python
import csv, sys
from pathlib import Path
ROOT = Path(sys.argv[1])
ABL = "reports/feature_selection_ablation_S03.csv"
COH = "reports/five_subjects_benchmark.csv"
DIAG = "reports/feature_selection_sfs_diagnostics_S03.csv"
AUD = "reports/feature_selection_sfs_audit_S03.csv"
R4 = {  # from mas/04_REFERENCE_RESULTS.md, R-4 table (typed)
    "Full baseline": ("55", "90.36", "95.43"),
    "Sub-band pruning (drop 38-52 Hz)": ("45", "87.31", "94.92"),
    "ANOVA F-score": ("25", "86.29", "94.42"),
    "Mutual information": ("25", "87.82", "93.40"),
    "Sequential forward selection": ("20", "84.77", "93.40"),
}
def rows(rel):
    with open(ROOT / rel, newline="", encoding="utf-8") as fh:
        return list(csv.reader(fh))
def md(table):
    head, body = table[0], table[1:]
    out = ["| " + " | ".join(head) + " |", "|" + "---|" * len(head)]
    out += ["| " + " | ".join(r) + " |" for r in body]
    return "\n".join(out)
abl = rows(ABL)
print(md(abl))
for r in abl[1:]:                       # R-4 comparison, deltas computed
    name, p, a1, a2 = r[1], r[2], float(r[3]), float(r[4])
    rp, r1, r2 = R4[name]
    print(f"| {name} | {p} / {rp} | {r[3]} / {r1} | {a1 - float(r1):+.2f} | {r[4]} / {r2} | {a2 - float(r2):+.2f} |")
coh = rows(COH)
print(md(coh))
for r in coh[1:-1]:                     # per-subject gain
    print(f"| {r[0]} | {r[3]} | {r[4]} | {float(r[4]) - float(r[3]):+.2f} |")
n = len(coh) - 2
print(sum(float(r[3]) for r in coh[1:-1]) / n, sum(float(r[4]) for r in coh[1:-1]) / n)
diag = rows(DIAG); hdr = diag[0]
for r in diag[1:]:                      # diagnostics, window counts
    d = dict(zip(hdr, r))
    print(d["Variant"], d["p"], d["1.0s Acc (%)"], d["2.0s Smoothed (%)"],
          round(float(d["1.0s Acc (%)"]) * int(d["Clean Windows"]) / 100),
          round(float(d["2.0s Smoothed (%)"]) * int(d["Clean Windows"]) / 100))
aud = rows(AUD); ah = aud[0]
for r in aud[1:]:
    d = dict(zip(ah, r))
    print(d["Fold"], d["Train rows"], d["Test rows"], d["Disjoint indices"], d["Test rows found in SFS input"])
```

Run as: `python3 -I - <repo root> < script` (reads only the CSVs under reports/).
