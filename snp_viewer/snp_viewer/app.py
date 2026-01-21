import sys
from PyQt5.QtWidgets import QApplication
from snp_viewer.gui_main import MainWindow

def run() -> None:
    app = QApplication(sys.argv)
    w = MainWindow()
    w.show()
    sys.exit(app.exec_())
