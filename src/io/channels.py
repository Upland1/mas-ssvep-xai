"""Channel-name helpers shared by src and scripts (P07.3, PF-05, PF-06).

The recording montage has 8 scalp channels. The legacy arrays of `data/processed/`
were built with PO7 hard-excluded (7 channels); arrays built from P07 on carry all 8
(or fewer after a tier-1 channel drop). Channels are always selected by name (PF-06).
"""

from typing import Optional

# Montage order of mas/01_DATA_SPEC.md (and channels.scalp of config v2).
FULL_MONTAGE = ("PO7", "PO3", "POz", "PO4", "PO8", "O1", "Oz", "O2")
# legacy (P01-P06): the 7-channel arrays of data/processed/.
LEGACY_EXCLUDED = ("PO7",)


def resolve_channel_names(n_channels: int) -> Optional[list]:
  """Channel names of an array with `n_channels` channels: 8 -> full montage, 7 -> montage
  without PO7 (legacy arrays), anything else -> None (unknown layout; the caller must
  carry the names, e.g. after a tier-1 drop)."""
  n = int(n_channels)
  if n == len(FULL_MONTAGE):
    return list(FULL_MONTAGE)
  if n == len(FULL_MONTAGE) - len(LEGACY_EXCLUDED):
    return [c for c in FULL_MONTAGE if c not in LEGACY_EXCLUDED]
  return None


def legacy_scalp(scalp_names) -> list:
  """The config scalp list reduced to the channels of the legacy 7-channel arrays (PO7 removed).

  For consumers of `data/processed/` (legacy, P02-P06) that read `channels.scalp` from config
  v2 (8 channels); consumers of newer arrays use `resolve_channel_names(n)` or the saved
  `channels.json` instead.
  """
  return [c for c in scalp_names if c not in LEGACY_EXCLUDED]
