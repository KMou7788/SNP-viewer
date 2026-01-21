from __future__ import annotations
import numpy as np

def sparam_db(s: np.ndarray) -> np.ndarray:
    """Return magnitude in dB, safe for zeros."""
    mag = np.abs(s)
    mag = np.maximum(mag, 1e-20)
    return 20.0 * np.log10(mag)
