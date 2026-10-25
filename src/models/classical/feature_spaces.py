"""The six feature spaces of the P05 benchmark, built from one quality decision (PF-10).

`build_feature_blocks` gates the stimulus windows once (two-tier gate from P07) and hands that
decision to every extractor, so PSD, harmonic PSD, FBCCA and the FBCSP sub-band windows keep the same
rows and channels. Sub-band
filtering is per window (legacy R3/PF-14) and fits nothing; the CSP itself is fitted in each
training fold (`legacy_eval.fold_matrices`).
"""

from typing import Optional, Sequence

import numpy as np

from src.features.ssvep.fbcca_extraction import TARGET_FREQS, extract_fbcca_features
from src.features.ssvep.fbcsp_extraction import DEFAULT_SUBBANDS, filter_subbands
from src.features.ssvep.harmonic_psd import VISUAL_CLUSTER, visual_cluster_harmonic_psd
from src.features.ssvep.psd_extraction import continuous_psd_freqs, extract_continuous_psd_features
from src.features.ssvep.spectral_power import LEGACY_FS_HZ, select_channels_by_name
from src.features.ssvep.window_mask import (
  CHANNEL_FAIL_FRACTION, GATE_THRESHOLDS, channel_report, names_for, quality_gate)
from src.models.classical.legacy_eval import FeatureSpace

SPACE_NAMES = ("Continuous PSD", "Harmonic PSD", "FBCCA", "Harmonic PSD + FBCCA", "FBCSP (in-fold)",
               "FBCSP + FBCCA (in-fold)")


def build_feature_blocks(X_time: np.ndarray, y: np.ndarray, channel_names: Optional[Sequence[str]] = None,
                         fs: float = LEGACY_FS_HZ, thresholds: Optional[dict] = None,
                         fbcca_channels: Optional[Sequence[str]] = None,
                         channel_fail_fraction: float = CHANNEL_FAIL_FRACTION,
                         verbose: bool = False) -> dict:
  """Gate once (two-tier, P07), then every block on the accepted windows and kept channels.

  `channel_names` (None -> `resolve_channel_names(C)`) name the channels of `X_time`. The
  `channel_report` of one `quality_gate` call is handed to every extractor (`precomputed=`), so
  PSD, harmonic PSD, FBCCA and the FBCSP sub-band windows keep the same rows (PF-10).
  `fbcca_channels` (names, PF-06) restricts the FBCCA input to those channels that survive the tier-1
  drop (the harmonic+FBCCA script passes the visual cluster PO8, O1, Oz, O2, as the original); None =
  all kept channels. The harmonic PSD uses the visual cluster channels that survive.
  Returns `mask (n,)`, `y` (clean), `psd (n_clean, C'*F)`, `freqs`, `harmonic (n_clean, 8*|cluster|)`,
  `fbcca (n_clean, 5)`, `fbcca_channels` (names used), `subbands (n_clean, B, C', T)`, `thresholds`,
  `channel_report`, `channels_kept`, `channels_dropped`, `channel_fail_fraction`.
  """
  th = dict(GATE_THRESHOLDS if thresholds is None else thresholds)
  X_time = np.asarray(X_time)
  names = names_for(channel_names, X_time.shape[1])
  q = quality_gate(X_time, y, names, th, channel_fail_fraction, verbose=verbose)
  rep = channel_report(q)
  kept = rep["channels_kept"]
  mask = rep["valid_mask"]
  psd, y_c, _, _ = extract_continuous_psd_features(X_time, y, names, fs, precomputed=rep, thresholds=th)
  freqs = continuous_psd_freqs(X_time.shape[-1], fs)
  cluster = [c for c in VISUAL_CLUSTER if c in kept]
  if not cluster:
    raise ValueError(f"no visual-cluster channel {VISUAL_CLUSTER} survives the tier-1 drop (kept {kept})")
  harmonic = visual_cluster_harmonic_psd(psd, freqs, kept, cluster)
  if fbcca_channels is None:
    fb_names = list(kept)
  else:
    fb_names = [c for c in fbcca_channels if c in kept]
    if not fb_names:
      raise ValueError(f"none of the FBCCA channels {list(fbcca_channels)} survives the tier-1 drop (kept {kept})")
  X_fb = X_time[:, select_channels_by_name(names, fb_names, X_time.shape[1])]
  fbcca, y_f, _, _ = extract_fbcca_features(X_fb, y, fb_names, fs, TARGET_FREQS,
                                            precomputed=dict(rep, channels_kept=fb_names), thresholds=th)
  sub = filter_subbands(q["windows_clean"], fs, DEFAULT_SUBBANDS)
  if not (len(y_c) == len(y_f) == len(harmonic) == len(fbcca) == len(sub)):
    raise RuntimeError("feature blocks are misaligned (PF-10)")
  return {"mask": mask, "y": y_c, "psd": psd, "freqs": freqs, "harmonic": harmonic,
          "fbcca": fbcca, "fbcca_channels": fb_names, "subbands": sub, "thresholds": th,
          "channel_report": rep, "channels_kept": list(kept), "channels_dropped": list(rep["channels_dropped"]),
          "channel_fail_fraction": channel_fail_fraction}


def benchmark_spaces(blocks: dict, m: int = 1) -> list:
  """The six `FeatureSpace`s in `SPACE_NAMES` order."""
  return [FeatureSpace("Continuous PSD", [blocks["psd"]]),
          FeatureSpace("Harmonic PSD", [blocks["harmonic"]]),
          FeatureSpace("FBCCA", [blocks["fbcca"]]),
          FeatureSpace("Harmonic PSD + FBCCA", [blocks["harmonic"], blocks["fbcca"]]),
          FeatureSpace("FBCSP (in-fold)", [], fbcsp_m=m),
          FeatureSpace("FBCSP + FBCCA (in-fold)", [blocks["fbcca"]], fbcsp_m=m)]
