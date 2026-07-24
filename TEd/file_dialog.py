from pathlib import Path
from typing import Any

from PyQt6.QtCore import QDir, QSettings
from PyQt6.QtWidgets import QFileDialog, QWidget


class _Settings:
    def __init__(self) -> None:
        self.__settings = QSettings()
        self.__image_key = "last_open_dir_image"
        self.__mp3_key = "last_open_dir_mp3"

    def get_last_open_dir_image(self) -> str:
        return self.__settings.value(self.__image_key, QDir.homePath())

    def get_last_open_dir_mp3(self) -> str:
        return self.__settings.value(self.__mp3_key, QDir.homePath())

    def set_last_open_dir_image(self, path: str) -> None:
        self.__settings.setValue(self.__image_key, path)

    def set_last_open_dir_mp3(self, path: str) -> None:
        self.__settings.setValue(self.__mp3_key, path)


class FileDialog:
    def __init__(self, parent: QWidget | None) -> None:
        self.__parent = parent
        self.__settings = _Settings()

    def __get_path(self, multiple: bool, text: str, path: str, filter: str) -> Any:
        dialog = QFileDialog.getOpenFileNames if multiple else QFileDialog.getOpenFileName
        return dialog(
            self.__parent, text, path, filter
        )[0]

    def get_cover_image(self) -> Path | None:
        path = self.__get_path(
            False,
            "Select Cover Image",
            self.__settings.get_last_open_dir_image(),
            "*.jpg"
        )
        if not path:
            return
        path = Path(path)
        self.__settings.set_last_open_dir_image(str(path.parent))
        return path

    def get_song(self) -> Path | None:
        path = self.__get_path(
            False,
            "Select Song",
            self.__settings.get_last_open_dir_mp3(),
            "Mp3 Files (*.mp3)"
        )
        if not path:
            return
        path = Path(path)
        self.__settings.set_last_open_dir_mp3(str(path.parent))
        return path

    def get_songs(self) -> list[Path]:
        paths = self.__get_path(
            True,
            "Select Songs",
            self.__settings.get_last_open_dir_mp3(),
            "Mp3 Files (*.mp3)"
        )
        if not paths:
            return []
        paths = list(map(Path, paths))
        self.__settings.set_last_open_dir_mp3(str(paths[0].parent))
        return list(paths)
