# P03 · 05 · Run

Status: READY
Author: runner
Reads: 02_plan.md (Amendment, Round 1 run commands), 07_review.md (pre-run audit Round 2 PASS)
Branch / commit: phase/P03-exploration @ 8adcb4d2f99cdafe8abe119d464cadc6e7b441fb (clean tree at start)
Machine: Linux 7.0.0-38-generic, Python 3.12.3 (.venv), CPU only, no GPU

## Commands executed

All from the repo root, in this order, once each, no re-runs. Data source: legacy, data/processed/<S>/ from P02.

| # | Command | Runtime | Exit | Log |
|---|---|---|---|---|
| 1 | .venv/bin/python -m scripts.exploration.diagnose_occipital_spectra --all | ~3 s | see note | `reports/logs/P03/diagnose_occipital_spectra_fs250_20261024T180123.log` |
| 2 | .venv/bin/python -m scripts.exploration.diagnose_occipital_spectra --all --fs 256 --out-suffix header | ~3 s | see note | `reports/logs/P03/diagnose_occipital_spectra_header_20261024T180126.log` |
| 3 | .venv/bin/python -m scripts.exploration.visualize_data --all | ~5 s | see note | `reports/logs/P03/visualize_data_fs250_20261024T180129.log` |
| 4 | .venv/bin/python -m scripts.exploration.visualize_data --all --fs 256 --out-suffix header | ~4 s | see note | `reports/logs/P03/visualize_data_header_20261024T180134.log` |

Exit-code note: the wrapper recorded the exit status of a brace group whose last
command was an echo, so the per-command python exit codes were not captured
individually (the wrapper reported 0 for all four and the chain continued). Evidence
that each command succeeded: no Traceback or error text in any of the four logs
(grep), and each log ends with its final "Cohort: 5 subjects plotted, 0 skipped"
line. Runtimes are wall-clock seconds measured by the wrapper (3, 3, 5, 4).

## Human run requests

None.

## Console output, occipital runs (per-subject blocks verbatim)

### Run 1 (fs 250, legacy)

```
Data source: legacy, data/processed/<S>/ from P02 (OO.ebr) -> data/processed/<S>/
Occipital channels ['O1', 'Oz', 'O2'] by name from ['PO3', 'POz', 'PO4', 'PO8', 'O1', 'Oz', 'O2']; |rfft|^2 per window, mean over windows and channels; 5-35 Hz; classes [101, 102, 103, 104, 105]

[+] S01: 320 windows, X_time (320, 7, 256); fs=250 (legacy), header fs 256 Hz; bin spacing 0.976562 Hz; channels [4, 5, 6] = ['O1', 'Oz', 'O2']
  S01 101: n=40, target 24.00 Hz; max in band at 9.766 Hz (bin 10, P=1.556e+05); band median P=2.939e+04; 1f0 response bin 24 (23.438 Hz) P=2.667e+04 (x0.91 median), nearest-labelled bin 25 (24.414 Hz) P=1.411e+04 (x0.48 median); specificity x1.48 (1f0 response bin 24 vs median of 4 other classes)
  S01 102: n=40, target 20.00 Hz; max in band at 7.812 Hz (bin 8, P=1.171e+05); band median P=3.539e+04; 1f0 response bin 20 (19.531 Hz) P=5.063e+04 (x1.43 median); specificity x1.42 (1f0 response bin 20 vs median of 4 other classes)
  S01 103: n=40, target 15.00 Hz; max in band at 7.812 Hz (bin 8, P=1.237e+05); band median P=3.098e+04; 1f0 response bin 15 (14.648 Hz) P=7.25e+04 (x2.34 median); 2f0 response bin 30 (29.297 Hz) P=7615 (x0.25 median), nearest-labelled bin 31 (30.273 Hz) P=6473 (x0.21 median); specificity x0.99 (1f0 response bin 15 vs median of 4 other classes)
  S01 104: n=40, target 10.91 Hz; max in band at 10.742 Hz (bin 11, P=1.584e+05); band median P=3.471e+04; 1f0 response bin 11 (10.742 Hz) P=1.584e+05 (x4.56 median); 2f0 response bin 22 (21.484 Hz) P=3.24e+04 (x0.93 median); specificity x1.78 (1f0 response bin 11 vs median of 4 other classes)
  S01 105: n=40, target 8.57 Hz; max in band at 7.812 Hz (bin 8, P=1.09e+05); band median P=3.278e+04; 1f0 response bin 9 (8.789 Hz) P=6.778e+04 (x2.07 median); 2f0 response bin 17 (16.602 Hz) P=6.289e+04 (x1.92 median), nearest-labelled bin 18 (17.578 Hz) P=5.441e+04 (x1.66 median); specificity x0.87 (1f0 response bin 9 vs median of 4 other classes)
  Figure: outputs/figures/exploration/S01/occipital_spectra.png

[+] S02: 318 windows, X_time (318, 7, 256); fs=250 (legacy), header fs 256 Hz; bin spacing 0.976562 Hz; channels [4, 5, 6] = ['O1', 'Oz', 'O2']
  S02 101: n=40, target 24.00 Hz; max in band at 5.859 Hz (bin 6, P=3.256e+05); band median P=2.498e+04; 1f0 response bin 24 (23.438 Hz) P=2.649e+04 (x1.06 median), nearest-labelled bin 25 (24.414 Hz) P=1.398e+04 (x0.56 median); specificity x1.29 (1f0 response bin 24 vs median of 4 other classes)
  S02 102: n=40, target 20.00 Hz; max in band at 5.859 Hz (bin 6, P=3.031e+05); band median P=2.497e+04; 1f0 response bin 20 (19.531 Hz) P=2.57e+04 (x1.03 median); specificity x1.19 (1f0 response bin 20 vs median of 4 other classes)
  S02 103: n=39, target 15.00 Hz; max in band at 5.859 Hz (bin 6, P=3.893e+05); band median P=2.33e+04; 1f0 response bin 15 (14.648 Hz) P=8.619e+04 (x3.70 median); 2f0 response bin 30 (29.297 Hz) P=2.29e+04 (x0.98 median), nearest-labelled bin 31 (30.273 Hz) P=1.641e+04 (x0.70 median); specificity x1.49 (1f0 response bin 15 vs median of 4 other classes)
  S02 104: n=40, target 10.91 Hz; max in band at 5.859 Hz (bin 6, P=3.205e+05); band median P=2.189e+04; 1f0 response bin 11 (10.742 Hz) P=1.126e+05 (x5.14 median); 2f0 response bin 22 (21.484 Hz) P=1.945e+04 (x0.89 median); specificity x1.24 (1f0 response bin 11 vs median of 4 other classes)
  S02 105: n=40, target 8.57 Hz; max in band at 5.859 Hz (bin 6, P=3e+05); band median P=2.394e+04; 1f0 response bin 9 (8.789 Hz) P=2.215e+05 (x9.25 median); 2f0 response bin 17 (16.602 Hz) P=3.742e+04 (x1.56 median), nearest-labelled bin 18 (17.578 Hz) P=2.805e+04 (x1.17 median); specificity x1.01 (1f0 response bin 9 vs median of 4 other classes)
  Figure: outputs/figures/exploration/S02/occipital_spectra.png

[+] S03: 317 windows, X_time (317, 7, 256); fs=250 (legacy), header fs 256 Hz; bin spacing 0.976562 Hz; channels [4, 5, 6] = ['O1', 'Oz', 'O2']
  S03 101: n=40, target 24.00 Hz; max in band at 23.438 Hz (bin 24, P=1.471e+05); band median P=2.417e+04; 1f0 response bin 24 (23.438 Hz) P=1.471e+05 (x6.09 median), nearest-labelled bin 25 (24.414 Hz) P=1.267e+04 (x0.52 median); specificity x12.12 (1f0 response bin 24 vs median of 4 other classes)
  S03 102: n=40, target 20.00 Hz; max in band at 19.531 Hz (bin 20, P=2.92e+05); band median P=2.231e+04; 1f0 response bin 20 (19.531 Hz) P=2.92e+05 (x13.09 median); specificity x15.73 (1f0 response bin 20 vs median of 4 other classes)
  S03 103: n=40, target 15.00 Hz; max in band at 14.648 Hz (bin 15, P=2.389e+05); band median P=1.518e+04; 1f0 response bin 15 (14.648 Hz) P=2.389e+05 (x15.74 median); 2f0 response bin 30 (29.297 Hz) P=3.205e+04 (x2.11 median), nearest-labelled bin 31 (30.273 Hz) P=8384 (x0.55 median); specificity x9.33 (1f0 response bin 15 vs median of 4 other classes)
  S03 104: n=40, target 10.91 Hz; max in band at 10.742 Hz (bin 11, P=1.241e+05); band median P=1.732e+04; 1f0 response bin 11 (10.742 Hz) P=1.241e+05 (x7.16 median); 2f0 response bin 22 (21.484 Hz) P=2.855e+04 (x1.65 median); specificity x2.17 (1f0 response bin 11 vs median of 4 other classes)
  S03 105: n=40, target 8.57 Hz; max in band at 8.789 Hz (bin 9, P=9.398e+04); band median P=2.003e+04; 1f0 response bin 9 (8.789 Hz) P=9.398e+04 (x4.69 median); 2f0 response bin 17 (16.602 Hz) P=1.883e+04 (x0.94 median), nearest-labelled bin 18 (17.578 Hz) P=2.423e+04 (x1.21 median); specificity x2.43 (1f0 response bin 9 vs median of 4 other classes)
  Figure: outputs/figures/exploration/S03/occipital_spectra.png

[+] S04: 317 windows, X_time (317, 7, 256); fs=250 (legacy), header fs 256 Hz; bin spacing 0.976562 Hz; channels [4, 5, 6] = ['O1', 'Oz', 'O2']
  S04 101: n=38, target 24.00 Hz; max in band at 23.438 Hz (bin 24, P=3.02e+05); band median P=3.135e+04; 1f0 response bin 24 (23.438 Hz) P=3.02e+05 (x9.63 median), nearest-labelled bin 25 (24.414 Hz) P=2.623e+04 (x0.84 median); specificity x20.92 (1f0 response bin 24 vs median of 4 other classes)
  S04 102: n=40, target 20.00 Hz; max in band at 19.531 Hz (bin 20, P=4.329e+05); band median P=2.636e+04; 1f0 response bin 20 (19.531 Hz) P=4.329e+05 (x16.42 median); specificity x20.17 (1f0 response bin 20 vs median of 4 other classes)
  S04 103: n=40, target 15.00 Hz; max in band at 14.648 Hz (bin 15, P=5.75e+05); band median P=1.852e+04; 1f0 response bin 15 (14.648 Hz) P=5.75e+05 (x31.04 median); 2f0 response bin 30 (29.297 Hz) P=1.997e+04 (x1.08 median), nearest-labelled bin 31 (30.273 Hz) P=1.261e+04 (x0.68 median); specificity x14.55 (1f0 response bin 15 vs median of 4 other classes)
  S04 104: n=40, target 10.91 Hz; max in band at 10.742 Hz (bin 11, P=7.384e+05); band median P=2.327e+04; 1f0 response bin 11 (10.742 Hz) P=7.384e+05 (x31.74 median); 2f0 response bin 22 (21.484 Hz) P=3.93e+04 (x1.69 median); specificity x16.37 (1f0 response bin 11 vs median of 4 other classes)
  S04 105: n=40, target 8.57 Hz; max in band at 8.789 Hz (bin 9, P=2.153e+05); band median P=2.094e+04; 1f0 response bin 9 (8.789 Hz) P=2.153e+05 (x10.28 median); 2f0 response bin 17 (16.602 Hz) P=1.287e+05 (x6.15 median), nearest-labelled bin 18 (17.578 Hz) P=2.845e+04 (x1.36 median); specificity x4.73 (1f0 response bin 9 vs median of 4 other classes)
  Figure: outputs/figures/exploration/S04/occipital_spectra.png

[+] S05: 320 windows, X_time (320, 7, 256); fs=250 (legacy), header fs 256 Hz; bin spacing 0.976562 Hz; channels [4, 5, 6] = ['O1', 'Oz', 'O2']
  S05 101: n=40, target 24.00 Hz; max in band at 23.438 Hz (bin 24, P=1.209e+05); band median P=1.325e+04; 1f0 response bin 24 (23.438 Hz) P=1.209e+05 (x9.12 median), nearest-labelled bin 25 (24.414 Hz) P=1.266e+04 (x0.96 median); specificity x19.54 (1f0 response bin 24 vs median of 4 other classes)
  S05 102: n=40, target 20.00 Hz; max in band at 19.531 Hz (bin 20, P=6.786e+04); band median P=1.073e+04; 1f0 response bin 20 (19.531 Hz) P=6.786e+04 (x6.33 median); specificity x6.78 (1f0 response bin 20 vs median of 4 other classes)
  S05 103: n=40, target 15.00 Hz; max in band at 14.648 Hz (bin 15, P=1.07e+05); band median P=9355; 1f0 response bin 15 (14.648 Hz) P=1.07e+05 (x11.44 median); 2f0 response bin 30 (29.297 Hz) P=4.346e+04 (x4.65 median), nearest-labelled bin 31 (30.273 Hz) P=6607 (x0.71 median); specificity x6.59 (1f0 response bin 15 vs median of 4 other classes)
  S05 104: n=40, target 10.91 Hz; max in band at 21.484 Hz (bin 22, P=1.527e+05); band median P=1.351e+04; 1f0 response bin 11 (10.742 Hz) P=1.13e+05 (x8.36 median); 2f0 response bin 22 (21.484 Hz) P=1.527e+05 (x11.31 median); specificity x3.53 (1f0 response bin 11 vs median of 4 other classes)
  S05 105: n=40, target 8.57 Hz; max in band at 16.602 Hz (bin 17, P=1.71e+05); band median P=1.177e+04; 1f0 response bin 9 (8.789 Hz) P=6.341e+04 (x5.39 median); 2f0 response bin 17 (16.602 Hz) P=1.71e+05 (x14.53 median), nearest-labelled bin 18 (17.578 Hz) P=1.684e+04 (x1.43 median); specificity x2.48 (1f0 response bin 9 vs median of 4 other classes)
  Figure: outputs/figures/exploration/S05/occipital_spectra.png

Cohort: 5 subjects plotted, 0 skipped (none); frequency axis fs 250 Hz (legacy)
Figures: outputs/figures/exploration
```

### Run 2 (fs 256, header)

```
Data source: legacy, data/processed/<S>/ from P02 (OO.ebr) -> data/processed/<S>/
Occipital channels ['O1', 'Oz', 'O2'] by name from ['PO3', 'POz', 'PO4', 'PO8', 'O1', 'Oz', 'O2']; |rfft|^2 per window, mean over windows and channels; 5-35 Hz; classes [101, 102, 103, 104, 105]

[+] S01: 320 windows, X_time (320, 7, 256); fs=256 (header), header fs 256 Hz; bin spacing 1 Hz; channels [4, 5, 6] = ['O1', 'Oz', 'O2']
  S01 101: n=40, target 24.00 Hz; max in band at 10.000 Hz (bin 10, P=1.556e+05); band median P=3.031e+04; 1f0 response bin 24 (24.000 Hz) P=2.667e+04 (x0.88 median); specificity x1.48 (1f0 response bin 24 vs median of 4 other classes)
  S01 102: n=40, target 20.00 Hz; max in band at 8.000 Hz (bin 8, P=1.171e+05); band median P=3.579e+04; 1f0 response bin 20 (20.000 Hz) P=5.063e+04 (x1.41 median); specificity x1.42 (1f0 response bin 20 vs median of 4 other classes)
  S01 103: n=40, target 15.00 Hz; max in band at 8.000 Hz (bin 8, P=1.237e+05); band median P=3.452e+04; 1f0 response bin 15 (15.000 Hz) P=7.25e+04 (x2.10 median); 2f0 response bin 30 (30.000 Hz) P=7615 (x0.22 median); specificity x0.99 (1f0 response bin 15 vs median of 4 other classes)
  S01 104: n=40, target 10.91 Hz; max in band at 11.000 Hz (bin 11, P=1.584e+05); band median P=3.703e+04; 1f0 response bin 11 (11.000 Hz) P=1.584e+05 (x4.28 median); 2f0 response bin 22 (22.000 Hz) P=3.24e+04 (x0.88 median); specificity x1.78 (1f0 response bin 11 vs median of 4 other classes)
  S01 105: n=40, target 8.57 Hz; max in band at 8.000 Hz (bin 8, P=1.09e+05); band median P=3.311e+04; 1f0 response bin 9 (9.000 Hz) P=6.778e+04 (x2.05 median); 2f0 response bin 17 (17.000 Hz) P=6.289e+04 (x1.90 median); specificity x0.87 (1f0 response bin 9 vs median of 4 other classes)
  Figure: outputs/figures/exploration/S01/occipital_spectra_header.png

[+] S02: 318 windows, X_time (318, 7, 256); fs=256 (header), header fs 256 Hz; bin spacing 1 Hz; channels [4, 5, 6] = ['O1', 'Oz', 'O2']
  S02 101: n=40, target 24.00 Hz; max in band at 6.000 Hz (bin 6, P=3.256e+05); band median P=2.55e+04; 1f0 response bin 24 (24.000 Hz) P=2.649e+04 (x1.04 median); specificity x1.29 (1f0 response bin 24 vs median of 4 other classes)
  S02 102: n=40, target 20.00 Hz; max in band at 6.000 Hz (bin 6, P=3.031e+05); band median P=2.57e+04; 1f0 response bin 20 (20.000 Hz) P=2.57e+04 (x1.00 median); specificity x1.19 (1f0 response bin 20 vs median of 4 other classes)
  S02 103: n=39, target 15.00 Hz; max in band at 6.000 Hz (bin 6, P=3.893e+05); band median P=2.37e+04; 1f0 response bin 15 (15.000 Hz) P=8.619e+04 (x3.64 median); 2f0 response bin 30 (30.000 Hz) P=2.29e+04 (x0.97 median); specificity x1.49 (1f0 response bin 15 vs median of 4 other classes)
  S02 104: n=40, target 10.91 Hz; max in band at 6.000 Hz (bin 6, P=3.205e+05); band median P=2.302e+04; 1f0 response bin 11 (11.000 Hz) P=1.126e+05 (x4.89 median); 2f0 response bin 22 (22.000 Hz) P=1.945e+04 (x0.85 median); specificity x1.24 (1f0 response bin 11 vs median of 4 other classes)
  S02 105: n=40, target 8.57 Hz; max in band at 6.000 Hz (bin 6, P=3e+05); band median P=2.497e+04; 1f0 response bin 9 (9.000 Hz) P=2.215e+05 (x8.87 median); 2f0 response bin 17 (17.000 Hz) P=3.742e+04 (x1.50 median); specificity x1.01 (1f0 response bin 9 vs median of 4 other classes)
  Figure: outputs/figures/exploration/S02/occipital_spectra_header.png

[+] S03: 317 windows, X_time (317, 7, 256); fs=256 (header), header fs 256 Hz; bin spacing 1 Hz; channels [4, 5, 6] = ['O1', 'Oz', 'O2']
  S03 101: n=40, target 24.00 Hz; max in band at 24.000 Hz (bin 24, P=1.471e+05); band median P=2.465e+04; 1f0 response bin 24 (24.000 Hz) P=1.471e+05 (x5.97 median); specificity x12.12 (1f0 response bin 24 vs median of 4 other classes)
  S03 102: n=40, target 20.00 Hz; max in band at 20.000 Hz (bin 20, P=2.92e+05); band median P=2.259e+04; 1f0 response bin 20 (20.000 Hz) P=2.92e+05 (x12.93 median); specificity x15.73 (1f0 response bin 20 vs median of 4 other classes)
  S03 103: n=40, target 15.00 Hz; max in band at 15.000 Hz (bin 15, P=2.389e+05); band median P=1.668e+04; 1f0 response bin 15 (15.000 Hz) P=2.389e+05 (x14.32 median); 2f0 response bin 30 (30.000 Hz) P=3.205e+04 (x1.92 median); specificity x9.33 (1f0 response bin 15 vs median of 4 other classes)
  S03 104: n=40, target 10.91 Hz; max in band at 11.000 Hz (bin 11, P=1.241e+05); band median P=1.786e+04; 1f0 response bin 11 (11.000 Hz) P=1.241e+05 (x6.94 median); 2f0 response bin 22 (22.000 Hz) P=2.855e+04 (x1.60 median); specificity x2.17 (1f0 response bin 11 vs median of 4 other classes)
  S03 105: n=40, target 8.57 Hz; max in band at 9.000 Hz (bin 9, P=9.398e+04); band median P=2.028e+04; 1f0 response bin 9 (9.000 Hz) P=9.398e+04 (x4.63 median); 2f0 response bin 17 (17.000 Hz) P=1.883e+04 (x0.93 median); specificity x2.43 (1f0 response bin 9 vs median of 4 other classes)
  Figure: outputs/figures/exploration/S03/occipital_spectra_header.png

[+] S04: 317 windows, X_time (317, 7, 256); fs=256 (header), header fs 256 Hz; bin spacing 1 Hz; channels [4, 5, 6] = ['O1', 'Oz', 'O2']
  S04 101: n=38, target 24.00 Hz; max in band at 24.000 Hz (bin 24, P=3.02e+05); band median P=3.15e+04; 1f0 response bin 24 (24.000 Hz) P=3.02e+05 (x9.59 median); specificity x20.92 (1f0 response bin 24 vs median of 4 other classes)
  S04 102: n=40, target 20.00 Hz; max in band at 20.000 Hz (bin 20, P=4.329e+05); band median P=2.948e+04; 1f0 response bin 20 (20.000 Hz) P=4.329e+05 (x14.68 median); specificity x20.17 (1f0 response bin 20 vs median of 4 other classes)
  S04 103: n=40, target 15.00 Hz; max in band at 15.000 Hz (bin 15, P=5.75e+05); band median P=1.945e+04; 1f0 response bin 15 (15.000 Hz) P=5.75e+05 (x29.56 median); 2f0 response bin 30 (30.000 Hz) P=1.997e+04 (x1.03 median); specificity x14.55 (1f0 response bin 15 vs median of 4 other classes)
  S04 104: n=40, target 10.91 Hz; max in band at 11.000 Hz (bin 11, P=7.384e+05); band median P=2.346e+04; 1f0 response bin 11 (11.000 Hz) P=7.384e+05 (x31.47 median); 2f0 response bin 22 (22.000 Hz) P=3.93e+04 (x1.67 median); specificity x16.37 (1f0 response bin 11 vs median of 4 other classes)
  S04 105: n=40, target 8.57 Hz; max in band at 9.000 Hz (bin 9, P=2.153e+05); band median P=2.254e+04; 1f0 response bin 9 (9.000 Hz) P=2.153e+05 (x9.55 median); 2f0 response bin 17 (17.000 Hz) P=1.287e+05 (x5.71 median); specificity x4.73 (1f0 response bin 9 vs median of 4 other classes)
  Figure: outputs/figures/exploration/S04/occipital_spectra_header.png

[+] S05: 320 windows, X_time (320, 7, 256); fs=256 (header), header fs 256 Hz; bin spacing 1 Hz; channels [4, 5, 6] = ['O1', 'Oz', 'O2']
  S05 101: n=40, target 24.00 Hz; max in band at 24.000 Hz (bin 24, P=1.209e+05); band median P=1.384e+04; 1f0 response bin 24 (24.000 Hz) P=1.209e+05 (x8.74 median); specificity x19.54 (1f0 response bin 24 vs median of 4 other classes)
  S05 102: n=40, target 20.00 Hz; max in band at 20.000 Hz (bin 20, P=6.786e+04); band median P=1.243e+04; 1f0 response bin 20 (20.000 Hz) P=6.786e+04 (x5.46 median); specificity x6.78 (1f0 response bin 20 vs median of 4 other classes)
  S05 103: n=40, target 15.00 Hz; max in band at 15.000 Hz (bin 15, P=1.07e+05); band median P=9840; 1f0 response bin 15 (15.000 Hz) P=1.07e+05 (x10.87 median); 2f0 response bin 30 (30.000 Hz) P=4.346e+04 (x4.42 median); specificity x6.59 (1f0 response bin 15 vs median of 4 other classes)
  S05 104: n=40, target 10.91 Hz; max in band at 22.000 Hz (bin 22, P=1.527e+05); band median P=1.374e+04; 1f0 response bin 11 (11.000 Hz) P=1.13e+05 (x8.22 median); 2f0 response bin 22 (22.000 Hz) P=1.527e+05 (x11.11 median); specificity x3.53 (1f0 response bin 11 vs median of 4 other classes)
  S05 105: n=40, target 8.57 Hz; max in band at 17.000 Hz (bin 17, P=1.71e+05); band median P=1.266e+04; 1f0 response bin 9 (9.000 Hz) P=6.341e+04 (x5.01 median); 2f0 response bin 17 (17.000 Hz) P=1.71e+05 (x13.50 median); specificity x2.48 (1f0 response bin 9 vs median of 4 other classes)
  Figure: outputs/figures/exploration/S05/occipital_spectra_header.png

Cohort: 5 subjects plotted, 0 skipped (none); frequency axis fs 256 Hz
Figures: outputs/figures/exploration
```

## Console lines, visualize runs (mask and PSD consistency, verbatim)

### Run 3 (fs 250, legacy)

```
Quality mask (legacy per-script gate, R5): vpp [0.5, 200] uV, std [0.5, 60] uV; channels ['PO3', 'POz', 'PO4', 'PO8', 'O1', 'Oz', 'O2']
  S01 quality mask: kept 320/320, rejected 0 (vpp [0.5, 200] uV, std [0.5, 60] uV)
  saved X_psd_features (320, 217): not comparable at fs=250 (legacy)
  S02 quality mask: kept 318/318, rejected 0 (vpp [0.5, 200] uV, std [0.5, 60] uV)
  saved X_psd_features (318, 217): not comparable at fs=250 (legacy)
  S03 quality mask: kept 317/317, rejected 0 (vpp [0.5, 200] uV, std [0.5, 60] uV)
  saved X_psd_features (317, 217): not comparable at fs=250 (legacy)
  S04 quality mask: kept 317/317, rejected 0 (vpp [0.5, 200] uV, std [0.5, 60] uV)
  saved X_psd_features (317, 217): not comparable at fs=250 (legacy)
  S05 quality mask: kept 320/320, rejected 0 (vpp [0.5, 200] uV, std [0.5, 60] uV)
  saved X_psd_features (320, 217): not comparable at fs=250 (legacy)
Cohort: 5 subjects plotted, 0 skipped (none); mask kept 1592, rejected 0; PSD fs 250 Hz (legacy)
```

### Run 4 (fs 256, header)

```
Quality mask (legacy per-script gate, R5): vpp [0.5, 200] uV, std [0.5, 60] uV; channels ['PO3', 'POz', 'PO4', 'PO8', 'O1', 'Oz', 'O2']
  S01 quality mask: kept 320/320, rejected 0 (vpp [0.5, 200] uV, std [0.5, 60] uV)
  saved X_psd_features (320, 217): max |computed - saved| = 0
  S02 quality mask: kept 318/318, rejected 0 (vpp [0.5, 200] uV, std [0.5, 60] uV)
  saved X_psd_features (318, 217): max |computed - saved| = 0
  S03 quality mask: kept 317/317, rejected 0 (vpp [0.5, 200] uV, std [0.5, 60] uV)
  saved X_psd_features (317, 217): max |computed - saved| = 0
  S04 quality mask: kept 317/317, rejected 0 (vpp [0.5, 200] uV, std [0.5, 60] uV)
  saved X_psd_features (317, 217): max |computed - saved| = 0
  S05 quality mask: kept 320/320, rejected 0 (vpp [0.5, 200] uV, std [0.5, 60] uV)
  saved X_psd_features (320, 217): max |computed - saved| = 0
Cohort: 5 subjects plotted, 0 skipped (none); mask kept 1592, rejected 0; PSD fs 256 Hz
```

## Produced files

Under `outputs/figures/exploration/<S>/` for S in S01..S05 (git-ignored):
- occipital_spectra.png (run 1)
- occipital_spectra_header.png (run 2)
- psd_features_by_class.png (run 3)
- psd_features_by_class_header.png (run 4)

Logs: the four files in `reports/logs/P03/` listed above (git-ignored, not committed).

## Anomalies

None observed: no warnings or errors in the logs; window counts match P02 (320, 318, 317, 317, 320); mask rejected 0 in both visualize runs.
