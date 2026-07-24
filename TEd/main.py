import os
import sys
from pathlib import Path

from PyQt6.QtCore import (QCommandLineOption, QCommandLineParser,
                          qInstallMessageHandler)
from PyQt6.QtWidgets import QApplication

from TEd.config import APP_NAME, DEBUG_ENV_VAR_NAME

from .table import TableWindow


def setup_parser(app: QApplication) -> QCommandLineParser:
    parser = QCommandLineParser()
    parser.addHelpOption()
    parser.addPositionalArgument("file", "Files to open", "[file]...")
    parser.addOption(QCommandLineOption(
        "debug",
        "Enables debug mode."
    ))
    parser.process(app)
    return parser


def main() -> int:
    app = QApplication(sys.argv)
    parser = setup_parser(app)

    debug = parser.isSet("debug")
    os.environ[DEBUG_ENV_VAR_NAME] = str(int(debug))
    if not debug:
        def custom_message_handler(_, __, ___): return
        qInstallMessageHandler(custom_message_handler)

    positional_args = parser.positionalArguments()
    paths = []
    for arg in set(positional_args):
        path = Path(arg)
        if path.is_file() and path.name.endswith(".mp3"):
            paths.append(path)
        else:
            print(f"{path} is not a MP3 file.")

    app.setApplicationDisplayName(APP_NAME)
    app.setApplicationName(APP_NAME)
    app.setOrganizationName("Diverso")
    table_window = TableWindow(paths)
    table_window.show()

    return app.exec()
