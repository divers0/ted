from pathlib import Path

from PyQt6.QtCore import QDir, QSettings

RECENTS_MAX_LENGTH = 10


class Settings:
    def __init__(self) -> None:
        self._settings = QSettings()
        self._image_key = "last_open_dir_image"
        self._mp3_key = "last_open_dir_mp3"
        self._recents_key = "recents"
        self.__home_path = QDir.homePath()

    def get_last_open_dir_image(self) -> str:
        return self._settings.value(self._image_key, self.__home_path)

    def get_last_open_dir_mp3(self) -> str:
        return self._settings.value(self._mp3_key, self.__home_path)

    def set_last_open_dir_image(self, path: str) -> None:
        self._settings.setValue(self._image_key, path)

    def set_last_open_dir_mp3(self, path: str) -> None:
        self._settings.setValue(self._mp3_key, path)

    def get_recents(self) -> list[Path]:
        return self._settings.value(self._recents_key, [])

    def append_recents(self, path: Path) -> None:
        recents = self.get_recents()
        if recents:
            if path == recents[0]:
                return
            elif path in recents:
                # if the item to be added is in recents already
                # but not the most recen twe move it up
                recents.remove(path)
        if len(recents) == RECENTS_MAX_LENGTH:
            recents.pop(-1)
        recents.insert(0, path)
        self._settings.setValue(self._recents_key, recents)

    def clear_recents(self) -> None:
        self._settings.remove(self._recents_key)
