import re

from PyQt6.QtCore import QEvent, QObject
from PyQt6.QtWidgets import QLineEdit

from .config import PLATFORM


class FileNameValidator:
    def __init__(self, file_name: str) -> None:
        self.__file_name = file_name

    def __is_file_name_valid_posix(self, file_name: str) -> bool:
        return bool(file_name) and "/" not in file_name and "\x00" not in file_name

    def __is_file_name_valid_windows(self, file_name: str) -> bool:
        illegal_chars = r'[<>:"/\\|?*\x00-\x1f]'
        reserved_names = {
            "CON", "PRN", "AUX", "NUL",
            *(f"COM{i}" for i in range(1, 10)),
            *(f"LPT{i}" for i in range(1, 10)),
        }
        if not file_name or file_name != file_name.strip(" ."):
            # can't be empty, or start/end with space or dot (Windows)
            return False
        if re.search(illegal_chars, file_name):
            return False
        if file_name.upper().split(".")[0] in reserved_names:
            return False
        if len(file_name) > 255:
            return False
        return True

    def is_valid(self) -> bool:
        func = self.__is_file_name_valid_posix
        if PLATFORM == "win32":
            func = self.__is_file_name_valid_windows
        return func(self.__file_name)


class FileNameLineEditFilter(QObject):
    def __init__(self, initial_text: str,
                 parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.__initial_text = initial_text

    def eventFilter(self, a0: QObject | None,
                    a1: QEvent | None) -> bool:
        res = super().eventFilter(a0, a1)
        obj: QLineEdit = a0  # type: ignore
        event: QEvent = a1  # type: ignore
        if event.type() not in (
                QEvent.Type.FocusOut, QEvent.Type.Close, QEvent.Type.KeyPress):
            return res

        text = obj.text()
        if not FileNameValidator(text).is_valid():
            obj.setText(self.__initial_text)
        return res
