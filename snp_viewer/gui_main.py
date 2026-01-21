from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional, List, Tuple

import numpy as np
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QFileDialog, QMessageBox, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QComboBox, QCheckBox, QSplitter, QTextEdit, QGroupBox
)

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

from snp_viewer.touchstone import TouchstoneData, read_touchstone
from snp_viewer.analysis import sparam_db


@dataclass
class LoadedFile:
    path: Path
    data: TouchstoneData


class MplCanvas(FigureCanvas):
    def __init__(self, parent: Optional[QWidget] = None):
        self.fig = Figure()
        super().__init__(self.fig)
        self.ax = self.fig.add_subplot(111)
        self.fig.tight_layout()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("SNP-Viewer (GUI Skeleton)")

        self.loaded_primary: Optional[LoadedFile] = None
        self.loaded_compare: Optional[LoadedFile] = None

        root = QWidget()
        self.setCentralWidget(root)

        # Left panel controls
        self.btn_open = QPushButton("Open .sNp")
        self.btn_open.clicked.connect(self.on_open_primary)

        self.btn_open_compare = QPushButton("Open Compare .sNp")
        self.btn_open_compare.clicked.connect(self.on_open_compare)

        self.btn_clear_compare = QPushButton("Clear Compare")
        self.btn_clear_compare.clicked.connect(self.on_clear_compare)

        self.btn_export_report = QPushButton("Export Report (stub)")
        self.btn_export_report.clicked.connect(self.on_export_report_stub)

        self.cmb_plot = QComboBox()
        self.cmb_plot.addItems([
            "S21 (Insertion Loss) [dB]",
            "S11 (Return Loss) [dB]",
            "S12 [dB]",
            "S22 [dB]",
        ])
        self.cmb_plot.currentIndexChanged.connect(self.refresh_plot)

        self.chk_smooth = QCheckBox("Light smoothing (moving avg)")
        self.chk_smooth.stateChanged.connect(self.refresh_plot)

        self.lbl_primary = QLabel("Primary: (none)")
        self.lbl_compare = QLabel("Compare: (none)")
        self.lbl_ports = QLabel("Ports: -")

        self.log = QTextEdit()
        self.log.setReadOnly(True)
        self.log.setPlaceholderText("Log / notes...")

        controls = QVBoxLayout()
        controls.addWidget(self.btn_open)
        controls.addWidget(self.lbl_primary)
        controls.addSpacing(8)
        controls.addWidget(self.btn_open_compare)
        controls.addWidget(self.lbl_compare)
        controls.addWidget(self.btn_clear_compare)
        controls.addSpacing(8)

        grp_plot = QGroupBox("Plot Options")
        grp_layout = QVBoxLayout()
        grp_layout.addWidget(QLabel("Metric"))
        grp_layout.addWidget(self.cmb_plot)
        grp_layout.addWidget(self.chk_smooth)
        grp_plot.setLayout(grp_layout)

        controls.addWidget(grp_plot)
        controls.addSpacing(8)
        controls.addWidget(self.lbl_ports)
        controls.addSpacing(8)
        controls.addWidget(self.btn_export_report)
        controls.addSpacing(8)
        controls.addWidget(QLabel("Notes / Log"))
        controls.addWidget(self.log, 1)

        left = QWidget()
        left.setLayout(controls)

        # Right panel plot
        self.canvas = MplCanvas()
        right_layout = QVBoxLayout()
        right_layout.addWidget(self.canvas)
        right = QWidget()
        right.setLayout(right_layout)

        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(left)
        splitter.addWidget(right)
        splitter.setSizes([320, 880])

        layout = QVBoxLayout()
        layout.addWidget(splitter)
        root.setLayout(layout)

        self._log("Ready. Open a Touchstone file (.s2p/.sNp) to begin.")

    # -------------------------
    # Actions
    # -------------------------
    def on_open_primary(self):
        path = self._pick_file()
        if not path:
            return
        self._load_primary(Path(path))

    def on_open_compare(self):
        path = self._pick_file()
        if not path:
            return
        self._load_compare(Path(path))

    def on_clear_compare(self):
        self.loaded_compare = None
        self.lbl_compare.setText("Compare: (none)")
        self._log("Compare file cleared.")
        self.refresh_plot()

    def on_export_report_stub(self):
        if not self.loaded_primary:
            QMessageBox.information(self, "Export Report", "Load a primary .sNp file first.")
            return
        save_path, _ = QFileDialog.getSaveFileName(
            self, "Export Report (stub)", "snp_report.txt", "Text (*.txt)"
        )
        if not save_path:
            return

        # Stub report: saves basic file info and last plotted series metadata
        lines = []
        lines.append("SNP-Viewer Report (stub)")
        lines.append("=======================")
        lines.append(f"Primary file: {self.loaded_primary.path}")
        if self.loaded_compare:
            lines.append(f"Compare file: {self.loaded_compare.path}")
        lines.append("")
        lines.append(f"Selected metric: {self.cmb_plot.currentText()}")
        lines.append(f"Smoothing: {'ON' if self.chk_smooth.isChecked() else 'OFF'}")
        lines.append("")
        lines.append("Note: This is a placeholder report generator.")
        lines.append("Future: PDF export, plot embedding, summary metrics, pass/fail checks.")

        Path(save_path).write_text("\n".join(lines), encoding="utf-8")
        self._log(f"Report exported (stub): {save_path}")

    # -------------------------
    # Loading
    # -------------------------
    def _load_primary(self, p: Path):
        try:
            data = read_touchstone(p)
        except Exception as e:
            QMessageBox.critical(self, "Load Error", f"Failed to read file:\n{p}\n\n{e}")
            return

        self.loaded_primary = LoadedFile(p, data)
        self.lbl_primary.setText(f"Primary: {p.name}")
        self.lbl_ports.setText(f"Ports: {data.nports}, Points: {len(data.freq_hz)}")
        self._log(f"Loaded primary: {p}  (ports={data.nports}, points={len(data.freq_hz)})")
        self.refresh_plot()

    def _load_compare(self, p: Path):
        try:
            data = read_touchstone(p)
        except Exception as e:
            QMessageBox.critical(self, "Load Error", f"Failed to read file:\n{p}\n\n{e}")
            return

        if self.loaded_primary and data.nports != self.loaded_primary.data.nports:
            QMessageBox.warning(
                self,
                "Port Mismatch",
                f"Compare file ports ({data.nports}) != primary ports ({self.loaded_primary.data.nports}).\n"
                "Overlay will still attempt to plot matching indices, but interpretation may be invalid."
            )

        self.loaded_compare = LoadedFile(p, data)
        self.lbl_compare.setText(f"Compare: {p.name}")
        self._log(f"Loaded compare: {p}  (ports={data.nports}, points={len(data.freq_hz)})")
        self.refresh_plot()

    # -------------------------
    # Plot
    # -------------------------
    def refresh_plot(self):
        self.canvas.ax.clear()

        if not self.loaded_primary:
            self.canvas.ax.set_title("Load a .sNp file to plot")
            self.canvas.draw()
            return

        metric = self.cmb_plot.currentText()
        ij = self._metric_to_ij(metric, self.loaded_primary.data.nports)
        if ij is None:
            self._log(f"Unsupported metric selection: {metric}")
            self.canvas.draw()
            return

        i, j = ij  # 0-based
        x_ghz, y_db = self._extract_db(self.loaded_primary.data, i, j)
        if self.chk_smooth.isChecked():
            y_db = self._smooth(y_db, win=7)

        self.canvas.ax.plot(x_ghz, y_db, label=f"Primary {metric}")
        self.canvas.ax.set_xlabel("Frequency (GHz)")
        self.canvas.ax.set_ylabel("Magnitude (dB)")
        self.canvas.ax.grid(True)

        # Compare overlay if present
        if self.loaded_compare:
            x2_ghz, y2_db = self._extract_db(self.loaded_compare.data, i, j)
            if self.chk_smooth.isChecked():
                y2_db = self._smooth(y2_db, win=7)
            self.canvas.ax.plot(x2_ghz, y2_db, label=f"Compare {metric}")

        self.canvas.ax.legend(loc="best")
        self.canvas.fig.tight_layout()
        self.canvas.draw()

    def _extract_db(self, data: TouchstoneData, i: int, j: int) -> Tuple[np.ndarray, np.ndarray]:
        f_ghz = data.freq_hz / 1e9
        s = data.s[:, i, j]  # complex
        return f_ghz, sparam_db(s)

    def _metric_to_ij(self, metric: str, nports: int) -> Optional[Tuple[int, int]]:
        # Minimal: map common 2-port use cases. For nports>2, still maps to first two ports.
        if "S21" in metric:
            return (1, 0) if nports >= 2 else None
        if "S11" in metric:
            return (0, 0) if nports >= 1 else None
        if "S12" in metric:
            return (0, 1) if nports >= 2 else None
        if "S22" in metric:
            return (1, 1) if nports >= 2 else None
        return None

    # -------------------------
    # Utils
    # -------------------------
    def _pick_file(self) -> Optional[str]:
        path, _ = QFileDialog.getOpenFileName(
            self, "Open Touchstone", "", "Touchstone (*.s*p *.S*p);;All Files (*)"
        )
        return path or None

    def _smooth(self, y: np.ndarray, win: int = 7) -> np.ndarray:
        win = max(3, int(win))
        if win % 2 == 0:
            win += 1
        if len(y) < win:
            return y
        kernel = np.ones(win) / win
        return np.convolve(y, kernel, mode="same")

    def _log(self, msg: str):
        self.log.append(msg)
