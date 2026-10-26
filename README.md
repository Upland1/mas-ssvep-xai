# mas-ssvep-eeg-xai

A from-zero, multi-agent rebuild of an SSVEP brain-computer-interface research
pipeline (5-class decoding from 8-channel parieto-occipital EEG). The rebuild
replays the original project's history in 26 gated phases, P00–P25: legacy
pipeline, the trial-leakage discovery and fix, connectivity statistics and
graph models, continuous filtering at the true 256 Hz, detection and
pseudo-online decoding, and leave-one-subject-out evaluation. Every result is
backed by a logged run, and every fix ships with a before/after table.

This README is the operator's guide; phase P24 replaces it with the full
project documentation.

## Where to start

| Read | For |
|---|---|
| `AGENTS.md` | mission and golden rules |
| `mas/README.md` | team, phase workflow, hand-off contract, human gates |
| `mas/RULES.md` | methodological rules R1–R11 and when each is enforced |
| `mas/03_ROADMAP.md` | the 26 phases, their tasks and acceptance criteria |
| `mas/state/` | live state: phase status, hand-offs, reports, decisions, blockers |

## Status

```bash
python mas/tools/mas_status.py check   # preflight
python mas/tools/mas_status.py show    # phase table (after P00 init)
```

Open blockers are in `mas/state/blockers/`.

## Results status (P11, trial-leakage fix)

Legacy folders (7 channels, CPU, one training seed 42 for the networks). Full record: `mas/state/reports/P11.md`; numbers from `reports/n_subjects_benchmark.csv`, `reports/cv_leakage_demo.csv`, `reports/cv_leakage_demo_networks.csv`, `reports/augmentation_ab_<model>.csv`.

- **Flagship, trial-grouped CV (R-6 reproduced exactly):** 79.28 % at 1.0 s and 82.61 % at 2.0 s (legacy `i % 5` smoothing; mean over S01–S05).
- **Size of the classical inflation:** −4.06 pp (1.0 s) and −4.96 pp (2.0 s) on the cohort mean (leaky 83.33 / 87.57 %); S02 −10.21 pp at 1.0 s. S02 and S04 have approximate trial ids, so a small residual leak can remain there until P16.
- **Networks, seed 42 against the single-seed leaky run:** EEGNet OFF −5.57 pp, Compact-CNN OFF −5.56 pp, ShallowConvNet OFF −3.04 pp at 1.0 s. The training-seed range on EEGNet S03 (16.75 pp) is of the same order as its seed-42 drop (−20.81 pp), so per-subject network differences are not leak sizes; the three-seed EEGNet cohort drop (OFF, 1.0 s) is −2.71 pp.
- **Augmentation A/B vs R-9b:** 13 of 14 out-of-band cells are explained by training-seed variance. Compact-CNN S03 2.0 s ON is not reproduced within tolerance (accepted as a documented deviation by Sebastian, D-8, B006).
- The CNN-specific inflation of the original project was not reproduced here; the classical inflation was.

## Data policy

The recordings are private human-subject data and are never committed.
`data/`, generated arrays, models, reports and outputs are git-ignored; see
`.gitignore`.
