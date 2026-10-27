"""DIAGNOSTIC (kept, P13.2): reproduce the MVAR coefficient-slicing bug (PF-17, R6) before the fix.

Synthetic identifiable VAR(10) on 7 channels (a fixed random stable system, seed 0), 200 windows of 256
samples simulated with a burn-in. `fit_mvar_ols` builds channel-major columns (`c * p + lag`); the
coefficients of lag l are the STRIDED rows `weights[lag::p].T` (fix). Reading contiguous blocks
`weights[lag*C:(lag+1)*C].T` (BUG) mixes channels and lags. Error = ||A_hat - A||_F / ||A||_F.

Output: <reports-dir>/connectivity/mvar_slicing_demo.csv (+ .meta.txt). Exit code 0 when the strided error is
<= 15 % and the contiguous error is >= 100 %.
"""

import argparse
import sys
from pathlib import Path
from typing import Optional, Sequence

import numpy as np
import pandas as pd


def _find_root() -> Path:
  here = Path(__file__).resolve()
  for parent in here.parents:
    if (parent / "configs" / "pipeline_config.yaml").is_file():
      return parent
  return here.parents[3]


ROOT = _find_root()
if str(ROOT) not in sys.path:
  sys.path.insert(0, str(ROOT))

from src.features.connectivity.mvar_pdc import fit_mvar_ols, mvar_coefficients  # noqa: E402

N_CH, ORDER, N_WIN, T = 7, 10, 200, 256


def random_var(seed: int = 0, c: int = N_CH, p: int = ORDER, radius: float = 0.85, decay: float = 0.6) -> np.ndarray:
  """`(p, C, C)` stable VAR coefficients: random, geometrically decaying over lags, spectral radius `radius`."""
  rng = np.random.default_rng(seed)
  a = np.stack([rng.standard_normal((c, c)) * decay ** l for l in range(p)])
  comp = np.zeros((c * p, c * p))
  comp[:c] = np.concatenate(list(a), axis=1)
  comp[c:, :-c] = np.eye(c * (p - 1))
  s = radius / max(abs(np.linalg.eigvals(comp)))
  return a * (s ** np.arange(1, p + 1))[:, None, None]  # lag-l scaling s^l scales the companion eigenvalues by s


def simulate_var(coefs: np.ndarray, n: int = N_WIN, t: int = T, seed: int = 1, burn: int = 100) -> np.ndarray:
  """`(n, C, t)` windows of the VAR with unit-variance Gaussian innovations (independent windows)."""
  p, c, _ = coefs.shape
  rng = np.random.default_rng(seed)
  out = np.zeros((n, c, t))
  for k in range(n):
    x = np.zeros((c, t + burn))
    e = rng.standard_normal((c, t + burn))
    for s in range(p, t + burn):
      x[:, s] = e[:, s] + sum(coefs[l] @ x[:, s - 1 - l] for l in range(p))
    out[k] = x[:, burn:]
  return out


def contiguous_coefficients(weights: np.ndarray, p: int) -> np.ndarray:
  """BUG (PF-17): contiguous lag blocks `weights[lag*C:(lag+1)*C].T` of a channel-major design."""
  c = weights.shape[1]
  return np.stack([weights[lag * c:(lag + 1) * c, :].T for lag in range(p)])


def rel_error(est: np.ndarray, true: np.ndarray) -> float:
  return float(np.linalg.norm(est - true) / np.linalg.norm(true))


def run(seed: int = 0) -> dict:
  true = random_var(seed)
  w = simulate_var(true, seed=seed + 1)
  wts = fit_mvar_ols(w, ORDER)
  return dict(strided_error=rel_error(mvar_coefficients(wts, ORDER), true),
              contiguous_error=rel_error(contiguous_coefficients(wts, ORDER), true), order=ORDER, n_channels=N_CH,
              n_windows=N_WIN, window_length=T)


def main(argv: Optional[Sequence[str]] = None) -> int:
  p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
  p.add_argument("--reports-dir", type=Path, default=ROOT / "reports")
  args = p.parse_args(argv)
  r = run()
  print(f"synthetic VAR({ORDER}), {N_CH} channels, {N_WIN} windows x {T} samples, seed 0 (DIAGNOSTIC, PF-17)")
  print(f"  strided   weights[lag::p].T          (fix, REPORTED path): relative error {100 * r['strided_error']:.1f} %")
  print(f"  contiguous weights[lag*C:(lag+1)*C].T (BUG, PF-17)        : relative error {100 * r['contiguous_error']:.1f} %")
  out = Path(args.reports_dir) / "connectivity"
  out.mkdir(parents=True, exist_ok=True)
  csv = out / "mvar_slicing_demo.csv"
  pd.DataFrame([r]).to_csv(csv, index=False)
  csv.with_suffix(".meta.txt").write_text("synthetic VAR(10), seed 0; strided = fix, contiguous = PF-17 bug; DIAGNOSTIC\n")
  ok = r["strided_error"] <= 0.15 and r["contiguous_error"] >= 1.0
  print(f"in range (strided <= 15 %, contiguous >= 100 %): {ok}")
  print(f"saved {csv}")
  return 0 if ok else 1


if __name__ == "__main__":
  sys.exit(main())
