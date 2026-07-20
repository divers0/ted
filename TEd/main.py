import os
import sys
from pathlib import Path

from PyQt6.QtCore import qInstallMessageHandler
from PyQt6.QtWidgets import QApplication

from TEd.config import DEBUG_ENV_VAR_NAME

from .table import TableWindow

DEBUG = False
if len(sys.argv) > 1:
    debug_place_idx = 1 if Path(
        sys.argv[0]).name != "bootstrap.py" or len(sys.argv) == 2 else 2
    if sys.argv[debug_place_idx] in ("debug", "--debug"):
        DEBUG = True


def main() -> int:
    os.environ[DEBUG_ENV_VAR_NAME] = str(int(DEBUG))
    if not DEBUG:
        def custom_message_handler(_, __, ___): return
        qInstallMessageHandler(custom_message_handler)
    app = QApplication(sys.argv)
    table_window = TableWindow()
    table_window.show()

    return app.exec()
