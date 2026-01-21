from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Tuple, List

import numpy as np


@dataclass
class TouchstoneData:
    freq_hz: np.ndarray            # shape: (N,)
    s: np.ndarray                  # shape: (N, P, P), complex
    nports: int
    fmt: str                       # "RI" / "MA" / "DB"
    z0: float                      # reference impedance (ohm)


def read_touchstone(path: Path) -> TouchstoneData:
    """
    Minimal Touchstone reader for .sNp (Touchstone 1.x style).
    Supports:
      - Frequency units: Hz/kHz/MHz/GHz
      - Data formats: RI / MA / DB
      - Reference: R <z0> (default 50)
    Notes:
      - This is intentionally lightweight. Future: robust parsing, comments, mixed-mode, touchstone 2.0.
    """
    text = Path(path).read_text(encoding="utf-8", errors="ignore").splitlines()
    nports = _infer_nports(path.name)

    unit_scale = 1.0
    fmt = "RI"
    z0 = 50.0

    data_rows: List[float] = []

    for line in text:
        line = line.strip()
        if not line:
            continue
        if line.startswith("!"):
            continue

        if line.startswith("#"):
            # Example: "# GHZ S RI R 50"
            parts = line.upper().split()
            unit_scale = _unit_scale(parts)
            fmt = _parse_format(parts)
            z0 = _parse_z0(parts)
            continue

        # Remove inline comment after !
        if "!" in line:
            line = line.split("!")[0].strip()
        if not line:
            continue

        # Touchstone sometimes breaks one frequency point into multiple lines.
        # We'll just collect floats and re-chunk later.
        for tok in line.replace("\t", " ").split():
            try:
                data_rows.append(float(tok))
            except ValueError:
                # ignore weird tokens
                pass

    if nports <= 0:
        raise ValueError(f"Unable to infer port count from filename: {path.name}")

    # Each frequency point contains:
    # 1 freq + (nports*nports)*2 numbers (pair per s-parameter)
    per_point = 1 + (nports * nports) * 2
    if len(data_rows) < per_point:
        raise ValueError("Not enough numeric data found. Is this a valid .sNp file?")

    # Chunk into points
    total_points = len(data_rows) // per_point
    rows = np.array(data_rows[: total_points * per_point], dtype=float).reshape(total_points, per_point)

    freq = rows[:, 0] * unit_scale
    vals = rows[:, 1:]  # shape (N, 2*nports*nports)

    s = np.zeros((total_points, nports, nports), dtype=np.complex128)

    idx = 0
    for i in range(nports):
        for j in range(nports):
            a = vals[:, idx]
            b = vals[:, idx + 1]
            idx += 2
            s[:, i, j] = _to_complex(a, b, fmt)

    return TouchstoneData(freq_hz=freq, s=s, nports=nports, fmt=fmt, z0=z0)


def _infer_nports(filename: str) -> int:
    # SNP naming: .s2p, .s4p, .s16p ...
    lower = filename.lower()
    if ".s" not in lower or not lower.endswith("p"):
        return 0
    # Extract between ".s" and "p"
    try:
        mid = lower.split(".s")[-1]
        n = int(mid[:-1])  # drop trailing 'p'
        return n
    except Exception:
        return 0


def _unit_scale(parts: List[str]) -> float:
    # parts contains tokens after splitting "# ..."
    if "HZ" in parts:
        return 1.0
    if "KHZ" in parts:
        return 1e3
    if "MHZ" in parts:
        return 1e6
    if "GHZ" in parts:
        return 1e9
    # default Hz
    return 1.0


def _parse_format(parts: List[str]) -> str:
    # RI / MA / DB
    for c in ("RI", "MA", "DB"):
        if c in parts:
            return c
    return "RI"


def _parse_z0(parts: List[str]) -> float:
    # header may contain "... R 50"
    if "R" in parts:
        idx = parts.index("R")
        if idx + 1 < len(parts):
            try:
                return float(parts[idx + 1])
            except Exception:
                pass
    return 50.0


def _to_complex(a: np.ndarray, b: np.ndarray, fmt: str) -> np.ndarray:
    fmt = fmt.upper()
    if fmt == "RI":
        return a + 1j * b
    if fmt == "MA":
        # magnitude, angle in degrees
        ang = np.deg2rad(b)
        return a * (np.cos(ang) + 1j * np.sin(ang))
    if fmt == "DB":
        # dB magnitude, angle in degrees
        mag = 10 ** (a / 20.0)
        ang = np.deg2rad(b)
        return mag * (np.cos(ang) + 1j * np.sin(ang))
    # default RI
    return a + 1j * b
