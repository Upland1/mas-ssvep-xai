"""Channel-name helpers shared by src and scripts (P07.3, PF-05, PF-06).

The recording montage has 8 scalp channels. The legacy arrays of `data/processed/`
were built with PO7 hard-excluded (7 channels); arrays built from P07 on carry all 8
(or fewer after a tier-1 channel drop). Channels are always selected by name (PF-06).
"""

import json
from pathlib import Path
from typing import Optional, Sequence

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


def subject_channel_names(processed_dir: Path, subject: str, n_channels: int,
                          scalp: Optional[Sequence[str]] = None) -> list:
  """Channel names of a subject's `X_time_windows` (PF-06): `channels.json` (`kept`) if the folder has one
  (built by P07 preprocessing), else `scalp` if given, else `resolve_channel_names(n_channels)`
  (8 -> montage, 7 -> legacy arrays without PO7). Raises ValueError when the count does not match."""
  f = Path(processed_dir) / subject / "channels.json"
  if f.is_file():
    names = list(json.loads(f.read_text())["kept"])
    src = "channels.json"
  elif scalp is not None:
    names, src = list(scalp), "the given scalp list"
  else:
    names, src = resolve_channel_names(n_channels), "resolve_channel_names"
  if names is None:
    raise ValueError(f"{n_channels} channels and no channels.json (layout unknown)")
  if len(names) != n_channels:
    raise ValueError(f"{len(names)} channel names {names} (from {src}) for an array with {n_channels} channels")
  return names
