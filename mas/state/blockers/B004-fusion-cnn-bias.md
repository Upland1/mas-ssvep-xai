# Blocker B004: R-8 parameter counts imply bias-free convolutions the roadmap does not state

- Opened: 2026-10-24 by orchestrator (setup)
- Phase: P04, P09
- blocking: none (spec note for P04 and P09)
- Status: resolved 2026-10-24

## Question

Checked by instantiating the layers in PyTorch (2026-10-24):

| Model (R-8) | Target | Biases as default | Both convolutions `bias=False` |
|---|---|---|---|
| DualBranchFusionCNN (P04), branch-1 convs | 10,005 | 10,053 | 10,005 |
| ShallowConvNet (P09), temporal + spatial conv | 14,485 | 14,565 | 14,485 |

The roadmap says "no bias" for EEGNet and Compact-CNN (their counts, 2,349
and 56,021, follow from the text), but not for these two models.

## Options and consequences

| Option | Consequence |
|---|---|
| A. Confirm `bias=False` on those convolutions (maybe already in `02_REQUIREMENTS.md` or `05_PITFALLS.md`) | counts match R-8 |
| B. Keep biases | R-8 not met; must be explained in the P04/P09 reports |

## Recommendation

A, if `05_PITFALLS.md` or `02_REQUIREMENTS.md` confirms it.

## Resolution (Sebastian)

Option A. `mas/04_REFERENCE_RESULTS.md` R-8 now states it: every convolution
followed by BatchNorm has `bias=False` (EEGNet, Compact-CNN, ShallowConvNet
temporal and spatial convs, both DualBranchFusionCNN convs); Linear layers keep
their bias; conv biases are a spec deviation, not a pass.
