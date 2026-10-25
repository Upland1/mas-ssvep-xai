# P03 · 06 · Verification

Status: READY
Author: verifier
Reads: 00_assignment.md, 02_plan.md (Round 1 amendment), 03_changes_signal-processing.md, 04_tests.md, 05_run.md, 07_review.md, log.md, decisions.md P03 rows
Clean checkout: `mas/state/scratch/verify_P03` @ 1ccbac15e317cb5f353c6c28589fed19961ab1b9 (git worktree, detached HEAD; removed after the run)

Verdict: PASS

## 1. Tests on the clean checkout

```bash
cd mas/state/scratch/verify_P03 && <repo>/.venv/bin/python -m pytest tests/ -p no:cacheprovider -o addopts="" -q
```
Output (tail): `311 passed in 22.46s`

## 2. Re-run of the four commands from the clean checkout (exit codes captured)

A Python subprocess wrapper launched only the project scripts (cwd = clean checkout,
`--processed-dir <repo>/data/processed --figures-dir <repo>/mas/state/scratch/verify_P03_out/figures`)
and recorded `returncode`:

```
d250 returncode 0 stderr bytes 0     # diagnose_occipital_spectra --all
dhdr returncode 0 stderr bytes 0     # diagnose_occipital_spectra --all --fs 256 --out-suffix header
v250 returncode 0 stderr bytes 0     # visualize_data --all
vhdr returncode 0 stderr bytes 0     # visualize_data --all --fs 256 --out-suffix header
```

Comparison with `reports/logs/P03/*.log` (`diff`, after mapping the figures-dir prefix): the only
differences are the runner's wrapper lines (CMD/HEAD/START/EXIT_PIPE_DONE), the absolute
vs relative data path on line 1, and the `figures/` path prefix of the Figure lines (I
passed `--figures-dir <...>/figures`, hence `figures/exploration/...`). All numeric lines
are identical in all four logs. Figure files produced per subject: `occipital_spectra.png`,
`occipital_spectra_header.png`, `psd_features_by_class.png`, `psd_features_by_class_header.png`
(same names as the runner's outputs).

## 3. Acceptance

| Criterion | Obtained | Met? |
|---|---|---|
| figures exist (4 PNG per subject, non-empty) | `find ... -name '*.png' -size +0 | wc -l` = 20 (5 subjects x 4); zero-size files: none | yes |
| Mask rejected 0 | vhdr and v250 logs: "rejected 0" for S01-S05 and every label; `grep -c "rejected [1-9]"` = 0 / 0 | yes |
| PSD consistency 0 at fs 256 | `saved X_psd_features (n, 217): max |computed - saved| = 0` for S01 (320), S02 (318), S03 (317), S04 (317), S05 (320) | yes |
| Legacy identity: band-max bin identical fs 250 vs fs 256 | True for 25/25 subject-class rows | yes |
| Legacy label = k*250/256 | 25/25 rows within 5e-4 Hz (printed to 3 decimals) | yes |
| Reviewer visual confirmation of fundamental peaks (S01/S02 recorded) | not a verifier criterion; table below supplies the printed numbers | deferred to results review |

Table from the fs-256 occipital run (`dhdr.log`), parsed with `mas/state/scratch/verify_P03_out/tab.py`
(regex over the printed lines; legacy label and bin from `d250.log`). Columns: subject, class,
target Hz | band-max Hz (fs 256) and bin | 1f0 response bin, power, xmedian | specificity |
band-max bin equal in fs 250 and 256 runs | legacy label Hz | label = bin*250/256 (expected value).

```
S01 101 24.00 | 10.000 10 | 24 2.667e+04 x0.88 | x1.48 | True | 9.766 | True 9.766
S01 102 20.00 | 8.000 8 | 20 5.063e+04 x1.41 | x1.42 | True | 7.812 | True 7.812
S01 103 15.00 | 8.000 8 | 15 7.25e+04 x2.10 | x0.99 | True | 7.812 | True 7.812
S01 104 10.91 | 11.000 11 | 11 1.584e+05 x4.28 | x1.78 | True | 10.742 | True 10.742
S01 105 8.57 | 8.000 8 | 9 6.778e+04 x2.05 | x0.87 | True | 7.812 | True 7.812
S02 101 24.00 | 6.000 6 | 24 2.649e+04 x1.04 | x1.29 | True | 5.859 | True 5.859
S02 102 20.00 | 6.000 6 | 20 2.57e+04 x1.00 | x1.19 | True | 5.859 | True 5.859
S02 103 15.00 | 6.000 6 | 15 8.619e+04 x3.64 | x1.49 | True | 5.859 | True 5.859
S02 104 10.91 | 6.000 6 | 11 1.126e+05 x4.89 | x1.24 | True | 5.859 | True 5.859
S02 105 8.57 | 6.000 6 | 9 2.215e+05 x8.87 | x1.01 | True | 5.859 | True 5.859
S03 101 24.00 | 24.000 24 | 24 1.471e+05 x5.97 | x12.12 | True | 23.438 | True 23.438
S03 102 20.00 | 20.000 20 | 20 2.92e+05 x12.93 | x15.73 | True | 19.531 | True 19.531
S03 103 15.00 | 15.000 15 | 15 2.389e+05 x14.32 | x9.33 | True | 14.648 | True 14.648
S03 104 10.91 | 11.000 11 | 11 1.241e+05 x6.94 | x2.17 | True | 10.742 | True 10.742
S03 105 8.57 | 9.000 9 | 9 9.398e+04 x4.63 | x2.43 | True | 8.789 | True 8.789
S04 101 24.00 | 24.000 24 | 24 3.02e+05 x9.59 | x20.92 | True | 23.438 | True 23.438
S04 102 20.00 | 20.000 20 | 20 4.329e+05 x14.68 | x20.17 | True | 19.531 | True 19.531
S04 103 15.00 | 15.000 15 | 15 5.75e+05 x29.56 | x14.55 | True | 14.648 | True 14.648
S04 104 10.91 | 11.000 11 | 11 7.384e+05 x31.47 | x16.37 | True | 10.742 | True 10.742
S04 105 8.57 | 9.000 9 | 9 2.153e+05 x9.55 | x4.73 | True | 8.789 | True 8.789
S05 101 24.00 | 24.000 24 | 24 1.209e+05 x8.74 | x19.54 | True | 23.438 | True 23.438
S05 102 20.00 | 20.000 20 | 20 6.786e+04 x5.46 | x6.78 | True | 19.531 | True 19.531
S05 103 15.00 | 15.000 15 | 15 1.07e+05 x10.87 | x6.59 | True | 14.648 | True 14.648
S05 104 10.91 | 22.000 22 | 11 1.13e+05 x8.22 | x3.53 | True | 21.484 | True 21.484
S05 105 8.57 | 17.000 17 | 9 6.341e+04 x5.01 | x2.48 | True | 16.602 | True 16.602
```

Observations (no tuning): S03-S05 show the 1f0 as band maximum for classes 101-103 (and 104/105 for S03, S04);
S05 104 and 105 peak at 2f0 (bin 22 and bin 17, x11.3 and x14.5 median at the 2f0 bin per the run log) with the 1f0 still
x8.22/x5.01 median; S01/S02 band maxima sit at 10, 8 and 6 Hz (non-stimulus, alpha/low band) with 1f0 x0.88-x4.89
median, consistent with the P02 carry-forward (no clear SSVEP peaks, S01 101 peaks at 10 Hz).

## 4. Privacy / git

- Tracked files matching data-like extensions or `data/`, `reports/`, `outputs/`, `baselines/`, `.venv`, the answer-key
  folder, or local tooling paths: none (grep output empty).
- Pattern built from fragments (vendor/assistant names and co-author trailer) over all tracked file contents: no match.
- `main..HEAD` (23 commits) messages and author/committer fields: no match; sole identity
  `Sebastian Oliva <soulthunder5200@gmail.com>`.

## 5. R11

`mas/state/scratch/reference_access.log` has 2 lines, timestamped 15:07 and 16:27, role verifier, tool Bash. Both are
before the first P03 commit (17:31) and are P02 verification greps whose command text contained the folder name in a
pattern (not an open of the answer key). P03 lines: 0. No R11 violation by P03 agents.

## 6. Notes

- The runner's missing exit codes are now covered: all four python exit codes are 0 in the independent re-run.
- Runtime of each command about 3-5 s (CPU), within budget.
