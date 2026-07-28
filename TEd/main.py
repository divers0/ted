import os
import sys
from pathlib import Path

from PyQt6.QtCore import (QCommandLineOption, QCommandLineParser,
                          qInstallMessageHandler)
from PyQt6.QtWidgets import QApplication

from TEd.config import APP_NAME, DEBUG_ENV_VAR_NAME, VERSION

from .table import TableWindow


def set_app_metadata(app: QApplication) -> None:
    app.setApplicationDisplayName(APP_NAME)
    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(".".join(map(str, VERSION)))
    app.setOrganizationName("Diverso")


def setup_parser(app: QApplication) -> QCommandLineParser:
    parser = QCommandLineParser()
    parser.addHelpOption()
    parser.addVersionOption()
    parser.addPositionalArgument("file", "Files to open", "[file]...")
    parser.addOption(QCommandLineOption(
        "debug",
        "Enables debug mode."
    ))
    parser.process(app)
    return parser


def setup_debug(parser: QCommandLineParser) -> None:
    debug = parser.isSet("debug")
    os.environ[DEBUG_ENV_VAR_NAME] = str(int(debug))
    if not debug:
        def custom_message_handler(_, __, ___): return
        qInstallMessageHandler(custom_message_handler)


def validate_given_paths(positional_args: list[str]) -> list[Path]:
    paths: list[Path] = []
    for arg in set(positional_args):
        path = Path(arg)
        if path.is_file() and path.name.endswith(".mp3"):
            paths.append(path)
        else:
            print(f"{path} is not a MP3 file.")
    return paths


def main() -> int:
    app = QApplication(sys.argv)
    set_app_metadata(app)
    parser = setup_parser(app)
    setup_debug(parser)
    table_window = TableWindow(
        validate_given_paths(parser.positionalArguments()))
    table_window.show()

    return app.exec()
