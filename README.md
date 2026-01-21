# SNP-Viewer

SNP-Viewer is a lightweight GUI tool for loading and visualizing Touchstone **S-parameter (.sNp)** files.  
It aims to provide an intuitive, engineer-friendly front-end for quick frequency-domain inspection, early-stage debugging, and comparison workflows — without requiring heavy EDA environments.

> Status: **Active development (v0.1)** — GUI-first skeleton with progressive feature rollout.

---

## Highlights

- ✅ Simple GUI to load `.s2p/.sNp` Touchstone files
- ✅ Quick plotting of common metrics (S21 / S11 / S12 / S22 in dB)
- ✅ Compare overlay mode (Primary vs Compare)
- ✅ Clean modular code layout (GUI separated from parsing/analysis)
- 🧩 Built as a foundation for future SI workflows (reports, specs, automation)

---

## Screenshots

Drop your screenshots into `docs/screenshots/` and link them here.

Example:

- `docs/screenshots/main_window.png`
- `docs/screenshots/compare_overlay.png`

---

## Installation

### Option A: pip install dependencies

```bash
pip install -r requirements.txt
