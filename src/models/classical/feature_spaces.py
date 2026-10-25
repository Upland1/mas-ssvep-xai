"""The six feature spaces of the P05 benchmark, built from one window mask (PF-10).

`build_feature_blocks` gates the stimulus windows once and hands that mask to every extractor,
so PSD, harmonic PSD, FBCCA and the FBCSP sub-band windows keep the same rows. Sub-band
filtering is per window (legacy R3/PF-14) and fits nothing; the CSP itself is fitted in each
training fold (`legacy_eval.fold_matrices`).
"""

from typing import Optional, Sequence

import numpy as np

from src.features.ssvep.fbcca_extraction import TARGET_FREQS, extract_fbcca_features
from src.features.ssvep.fbcsp_extraction import DEFAULT_SUBBANDS, filter_subbands
from src.features.ssvep.harmonic_psd import visual_cluster_harmonic_psd
from src.features.ssvep.psd_extraction import continuous_psd_freqs, extract_continuous_psd_features
from src.features.ssvep.spectral_power import LEGACY_FS_HZ, select_channels_by_name
from src.features.ssvep.window_mask import P05_MASK_THRESHOLDS, resolve_window_mask
from src.models.classical.legacy_eval import FeatureSpace

SPACE_NAMES = ("Continuous PSD", "Harmonic PSD", "FBCCA", "Harmonic PSD + FBCCA", "FBCSP (in-fold)",
               "FBCSP + FBCCA (in-fold)")


def build_feature_blocks(X_time: np.ndarray, y: np.ndarray, channel_names: Sequence[str],
                         fs: float = LEGACY_FS_HZ, thresholds: Optional[dict] = None,
                         fbcca_channels: Optional[Sequence[str]] = None) -> dict:
  """Mask once, then every block on the accepted windows.

  `fbcca_channels` (names, PF-06) restricts the FBCCA input to those channels (the harmonic+FBCCA
  script passes the visual cluster PO8, O1, Oz, O2, as the original); None = all channels. The
  mask is always computed on all channels, so every block keeps the same rows.
  Returns `mask (n,)`, `y` (clean), `psd (n_clean, C*F)`, `freqs`, `harmonic (n_clean, 32)`,
  `fbcca (n_clean, 5)`, `fbcca_channels` (names used), `subbands (n_clean, B, C, T)` and `thresholds`.
  """
  th = dict(P05_MASK_THRESHOLDS if thresholds is None else thresholds)
  mask = resolve_window_mask(X_time, None, th)
  if fbcca_channels is None:
    fb_names, X_fb = list(channel_names), X_time
  else:
    fb_names = list(fbcca_channels)
    X_fb = np.asarray(X_time)[:, select_channels_by_name(channel_names, fb_names, X_time.shape[1])]
  psd, y_c, _ = extract_continuous_psd_features(X_time, y, fs, valid_mask=mask)
  freqs = continuous_psd_freqs(X_time.shape[-1], fs)
  harmonic = visual_cluster_harmonic_psd(psd, freqs, channel_names)
  fbcca, y_f, _ = extract_fbcca_features(X_fb, y, fs, TARGET_FREQS, valid_mask=mask)
  sub = filter_subbands(X_time[mask == 1], fs, DEFAULT_SUBBANDS)
  if not (len(y_c) == len(y_f) == len(harmonic) == len(fbcca) == len(sub)):
    raise RuntimeError("feature blocks are misaligned (PF-10)")
  return {"mask": mask, "y": y_c, "psd": psd, "freqs": freqs, "harmonic": harmonic,
          "fbcca": fbcca, "fbcca_channels": fb_names, "subbands": sub, "thresholds": th}


def benchmark_spaces(blocks: dict, m: int = 1) -> list:
  """The six `FeatureSpace`s in `SPACE_NAMES` order."""
  return [FeatureSpace("Continuous PSD", [blocks["psd"]]),
          FeatureSpace("Harmonic PSD", [blocks["harmonic"]]),
          FeatureSpace("FBCCA", [blocks["fbcca"]]),
          FeatureSpace("Harmonic PSD + FBCCA", [blocks["harmonic"], blocks["fbcca"]]),
          FeatureSpace("FBCSP (in-fold)", [], fbcsp_m=m),
          FeatureSpace("FBCSP + FBCCA (in-fold)", [blocks["fbcca"]], fbcsp_m=m)]
