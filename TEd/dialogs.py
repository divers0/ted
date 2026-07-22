from __future__ import annotations

import os
from enum import Enum
from pathlib import Path

from PyQt6.QtCore import QRegularExpression, Qt
from PyQt6.QtGui import (QAction, QIcon, QKeyEvent, QKeySequence, QPixmap,
                         QRegularExpressionValidator)
from PyQt6.QtWidgets import (QAbstractItemView, QApplication, QDialog,
                             QDialogButtonBox, QFileDialog, QLineEdit,
                             QListWidget, QListWidgetItem, QMenu, QPushButton,
                             QVBoxLayout, QWidget)

from .config import DISCARD_ICON_PATH
from .filename import FileNameLineEditFilter
from .image import ImageEditor, ImageViewer
from .song import Song
from .ui.AlbumCreationDialog import Ui_AlbumCreationDialog
from .ui.EditTagsDialog import Ui_EditTagsDialog
from .ui.SetAllDialog import Ui_SetAllDialog


class AlbumCreationDialog(QDialog):
    def __init__(self, table_songs: list[Song], parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.ui = Ui_AlbumCreationDialog()
        self.ui.setupUi(self)
        self.setFixedSize(self.size())

        self.__table_songs = table_songs

        self.ui.cover_button.clicked.connect(self.cover_browse_clicked)
        self.ui.cover_button.setAutoDefault(True)

        self.ui.clear_cover_button.clicked.connect(
            self.clear_cover_button_clicked)
        self.ui.clear_cover_button.setIcon(QIcon(str(DISCARD_ICON_PATH)))
        self.ui.clear_cover_button.setAutoDefault(True)

        if not self.__table_songs:
            self.ui.songs_button.clicked.connect(
                lambda: self.songs_browse_clicked(False))
            self.ui.songs_button.setAutoDefault(True)
        else:
            self.add_song_browse_button_menu()

        self.ui.button_box.accepted.connect(self.confirm_button_clicked)
        self.ui.button_box.rejected.connect(self.reject)
        for button in self.ui.button_box.buttons():
            if isinstance(button, QPushButton):
                button.setAutoDefault(True)

        self.ui.year_edit.setValidator(QRegularExpressionValidator(
            QRegularExpression("[1-9][0-9]{3}")))
        self.selected_cover_path: Path | None = None
        self.__songs: list[Song] = []

    def add_song_browse_button_menu(self) -> None:
        self.songs_menu = QMenu(self)
        self.ui.songs_button.setMenu(self.songs_menu)
        select_already_opened_songs_action = \
            QAction("Select already opened songs", self.songs_menu)
        select_already_opened_songs_action.triggered.connect(
            lambda: self.songs_browse_clicked(True))
        self.songs_menu.addAction(select_already_opened_songs_action)
        self.songs_menu.addAction(
            QIcon(), "Browse for files",
            lambda: self.songs_browse_clicked(False),
            Qt.ConnectionType.AutoConnection
        )

    def clear_cover_button_clicked(self) -> None:
        self.selected_cover_path = None
        self.ui.selected_cover_filename_label.setText("")

    def set_cover_path(self, path: Path) -> None:
        self.selected_cover_path = path
        self.ui.selected_cover_filename_label.setText(path.name)

    @property
    def songs(self) -> list[Song]:
        return self.__songs

    @songs.setter
    def songs(self, songs: list[Song]) -> None:
        self.__songs = songs
        self.ui.selected_song_filenames_label.setText(
            ", ".join([x.updated_file_path().name for x in songs]))

    def get_new_songs(self) -> list[Song]:
        assert hasattr(self, "_new_songs"), \
            "get_new_songs() was called before songs_browse_clicked()"
        if not self._new_songs:
            return []
        return self.songs

    def cover_browse_clicked(self) -> None:
        self.set_cover_path(Path(QFileDialog.getOpenFileName(
            self, "Select Cover Image", ".", "*.jpg")[0]))

    def songs_browse_clicked(self, already_opened: bool) -> None:
        if already_opened:
            self._new_songs = False
            self.dlg = SongsListDialog(
                "Choose songs", [x.file_name for x in self.__table_songs],
                True, self
            )
            if self.dlg.exec() != QDialog.DialogCode.Accepted:
                return
            selected_idxs = self.dlg.get_selected_indexes()
            if selected_idxs:
                self.songs = [self.__table_songs[i] for i in selected_idxs]
        else:
            self._new_songs = True
            raw_paths = QFileDialog.getOpenFileNames(
                self, "Select Songs", ".", "Mp3 Files (*.mp3)")[0]
            self.songs = [Song(path) for path in
                          [Path(x) for x in raw_paths]]

    def confirm_button_clicked(self) -> None:
        if self.ui.title_edit.displayText() == "":
            self.ui.status_bar.setText("Enter the album's title")
            return
        if self.ui.artist_edit.displayText() == "":
            self.ui.status_bar.setText("Enter the artist's name")
            return
        if self.ui.year_edit.displayText() == "":
            self.ui.status_bar.setText("Enter the album's release year")
            return
        if not self.ui.year_edit.hasAcceptableInput():
            self.ui.status_bar.setText("Enter a valid album release year " +
                                       "(a number between 1000 and 9999)")
            return
        if not self.songs:
            self.ui.status_bar.setText("Select songs for the album")
            return
        self.ui.status_bar.setText("")

        cover_bytes = None
        if self.selected_cover_path:
            with open(self.selected_cover_path, "rb") as f:
                cover_bytes = f.read()

        for song in self.songs:
            song.new_cover = cover_bytes
            song.album = self.ui.title_edit.text()
            song.artist = self.ui.artist_edit.text()
            song.year = int(self.ui.year_edit.text())
            song.update_crop_cover()
        self.accept()


class SetAllDialog(QDialog):
    Tags = Enum("Tags", ["TITLE", "ARTIST", "ALBUM",
                "ALBUM_ARTIST", "YEAR", "GENRE"])

    def __init__(self, year_validation_regex: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.ui = Ui_SetAllDialog()
        self.ui.setupUi(self)
        self.__tags: dict[str, SetAllDialog.Tags] = {
            "Title": self.Tags.TITLE,
            "Artist": self.Tags.ARTIST,
            "Album": self.Tags.ALBUM,
            "Album Artist": self.Tags.ALBUM_ARTIST,
            "Year": self.Tags.YEAR,
            "Genre": self.Tags.GENRE,
        }
        self.ui.button_box.accepted.connect(self.accept)
        self.ui.button_box.rejected.connect(self.reject)
        self.ui.tags_combobox.addItems(self.__tags.keys())
        self.ui.tags_combobox.currentTextChanged.connect(
            self.__combobox_changed)
        self.__year_validation_regex = year_validation_regex
        self.__validator_set = False

    def __combobox_changed(self, text: str) -> None:
        if text == "Year":
            self.ui.value_edit.setValidator(QRegularExpressionValidator(
                QRegularExpression(self.__year_validation_regex)))
            if not self.ui.value_edit.hasAcceptableInput():
                self.ui.value_edit.setText("")
            self.__validator_set = True
        elif self.__validator_set:
            self.ui.value_edit.setValidator(None)
            self.__validator_set = False

    def get_user_input(self) -> tuple[SetAllDialog.Tags, str]:
        return self.__tags[self.ui.tags_combobox.currentText()], self.ui.value_edit.text()


class SongsListDialog(QDialog):
    def __init__(self, title: str, items: list[str], allow_multiple: bool, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.resize(580, 440)
        self.setWindowTitle(title)

        self.allow_multiple = allow_multiple

        layout = QVBoxLayout()
        self.setLayout(layout)
        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText("Search...")
        self.search_bar.textChanged.connect(self.search)
        self.song_list = CheckableListWidget()
        self.song_list.itemDoubleClicked.connect(self.accept)
        self.button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok |
            QDialogButtonBox.StandardButton.Cancel
        )
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)

        layout.addWidget(self.search_bar)
        layout.addWidget(self.song_list)
        layout.addWidget(self.button_box)

        if self.allow_multiple:
            self.song_list.setSelectionMode(
                QAbstractItemView.SelectionMode.ExtendedSelection)
            for i in items:
                item = QListWidgetItem(i)
                item.setFlags(item.flags() |
                              Qt.ItemFlag.ItemIsUserCheckable |
                              Qt.ItemFlag.ItemIsSelectable)
                item.setCheckState(Qt.CheckState.Unchecked)
                self.song_list.addItem(item)
        else:
            self.song_list.addItems(items)

    def keyPressEvent(self, a0: QKeyEvent | None) -> None:
        if not a0:
            return
        key = a0.key()
        if key != Qt.Key.Key_Down:
            return super().keyPressEvent(a0)
        if not self.search_bar.hasFocus() or self.song_list.count() == 0:
            return
        self.song_list.setFocus()
        self.song_list.item(0).setSelected(True)  # type: ignore

    def search(self) -> None:
        search_query = self.search_bar.text()
        for i in range(self.song_list.count()):
            item = self.song_list.item(i)
            if not item:
                continue
            match = search_query in item.text().lower()
            item.setHidden(not match)

    def get_selected_index(self) -> int | None:
        assert not self.allow_multiple
        selected_items = self.song_list.selectedIndexes()
        if not selected_items:
            return
        return selected_items[0].row()

    def get_selected_indexes(self) -> list[int]:
        assert self.allow_multiple
        checked: list[int] = []
        for i in range(self.song_list.count()):
            item = self.song_list.item(i)
            if not item:
                continue
            if item.checkState() == Qt.CheckState.Checked:
                checked.append(i)
        return checked


class EditTagsDialog(QDialog):
    CoverImageStates = Enum("CoverImageStates", [
                            "SELECTED", "EMBEDDED", "NONE"])

    def __init__(self, songs: list[Song], index: int, year_validation_regex: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.ui = Ui_EditTagsDialog()
        self.ui.setupUi(self)
        self.setFixedSize(self.size())
        self.songs = songs
        self.index = index
        self.song: Song = self.songs[self.index]

        self.ui.year_edit.setValidator(QRegularExpressionValidator(
            QRegularExpression(year_validation_regex)))
        self.ui.button_box.accepted.connect(self.confirm)
        self.ui.button_box.rejected.connect(self.close)
        self.ui.tabs.setCurrentIndex(0)

        self.new_cover: bytes | None = self.song.new_cover
        self.__cover:   bytes | None = self.song.cover

        # Fill title and artist based on file name
        self.ui.fill_ta_button.clicked.connect(self.autofill_title_and_artist)

        self.fill_in_fields_from_song()
        self.filter = FileNameLineEditFilter(self.song.file_name)
        self.ui.file_name_edit.installEventFilter(self.filter)
        self.display_cover()

        # Change Cover Button
        self.cover_menu = QMenu(self)
        self.ui.change_cover_button.setMenu(self.cover_menu)

        self.show_cover_full_size_action = QAction(
            "Show full size", self.cover_menu)
        self.show_cover_full_size_action.triggered.connect(
            self.show_cover_full_size)
        self.cover_menu.addAction(self.show_cover_full_size_action)

        self.cover_menu.addSeparator()

        self.cover_menu.addAction(QIcon(), "Browse for cover image",
                                  self.browse_cover, Qt.ConnectionType.AutoConnection)

        self.cover_menu.addAction(QIcon(), "Browse for mp3 file to copy the cover from",
                                  self.copy_cover, Qt.ConnectionType.AutoConnection)

        self.cover_menu.addSeparator()

        # Unset Current Cover Action
        self.unset_current_cover_action = QAction("", self.cover_menu)
        self.cover_menu.addAction(self.unset_current_cover_action)
        self.unset_current_cover_action.triggered.connect(
            self.unset_current_cover)
        self.update_cover_related_controls()

        # Copy Tags From Another File
        self.copy_from_another_file_menu = QMenu(self)
        self.ui.copy_from_another_file_button.setMenu(
            self.copy_from_another_file_menu)

        self.copy_from_another_file_menu.addAction(
            QIcon(), "Copy from an already opened file", lambda: self.open_copy_tags_dialog(True),
            Qt.ConnectionType.AutoConnection)
        self.copy_from_another_file_menu.addAction(
            QIcon(), "Browse for file", lambda: self.open_copy_tags_dialog(False),
            Qt.ConnectionType.AutoConnection)

        self.ui.preserve_file_time_checkbox.setChecked(
            self.song.preserve_file_time)
        self.ui.remove_other_tags_checkbox.setChecked(
            self.song.remove_other_tags)
        self.ui.crop_cover_checkbox.setChecked(self.song.crop_cover_to_square)

        self.action_paste = QAction()
        self.action_paste.setShortcut(QKeySequence.StandardKey.Paste)
        self.addAction(self.action_paste)
        self.action_paste.triggered.connect(self.check_for_images_in_paste)

        self.ui.music_list.hide()

    def check_for_images_in_paste(self) -> None:
        cb = QApplication.clipboard()
        if not cb:
            return
        mime_data = cb.mimeData()
        if not mime_data:
            return
        supported_formats = (".jpg", ".png")
        if mime_data.hasUrls():
            if len(urls := mime_data.urls()) != 1:
                return
            path = Path(urls[0].toLocalFile())
            if path.suffix.lower() not in supported_formats or not path.is_file():
                return
        else:
            cb_contents = cb.text()
            if cb_contents == "":
                return
            paths = cb_contents.strip().split(os.linesep)
            if len(paths) != 1:
                return
            path = paths[0]
            if not os.path.isfile(path) or \
                    os.path.splitext(path.lower())[1] not in supported_formats:
                return
        with open(path, "rb") as f:
            image_data = f.read()
        self.new_cover = image_data
        self.update_cover_display()

    @property
    def cover(self) -> bytes | None:
        return self.__cover

    @cover.setter
    def cover(self, cover: None) -> None:
        self.__cover = cover

    def open_copy_tags_dialog(self, already_opened: bool) -> None:
        selected_song = None
        if already_opened:
            other_songs = [x for x in self.songs]
            other_songs.remove(self.song)
            self.dlg = SongsListDialog(
                "Choose a song", [x.file_name for x in other_songs],
                False, self
            )
            if self.dlg.exec() != QDialog.DialogCode.Accepted:
                return
            selected_idx = self.dlg.get_selected_index()
            if selected_idx is not None:
                selected_song = other_songs[selected_idx]
        else:
            selected_path = self.open_file_dialog("*.mp3")
            if selected_path:
                selected_song = Song(Path(selected_path))
        if not selected_song:
            return

        self.copy_tags_from_song(selected_song)

    def copy_tags_from_song(self, selected_song: Song) -> None:
        self.ui.title_edit.setText(selected_song.title)
        self.ui.artist_edit.setText(selected_song.artist)
        self.ui.album_edit.setText(selected_song.album)
        self.ui.album_artist_edit.setText(selected_song.album_artist)
        self.ui.genre_edit.setText(selected_song.genre)
        self.ui.lyrics_edit.setPlainText(selected_song.lyrics)
        self.ui.track_count_spinbox.setValue(selected_song.track_num[0])
        self.ui.track_total_spinbox.setValue(selected_song.track_num[1])
        self.ui.disc_count_spinbox.setValue(selected_song.disc_num[0])
        self.ui.disc_total_spinbox.setValue(selected_song.disc_num[1])
        year = str(selected_song.year)
        if year == "0":
            year = ""
        self.ui.year_edit.setText(year)

    def copy_cover(self) -> None:
        selected_path = self.open_file_dialog("*.mp3")
        if not selected_path:
            return
        selected_song = Song(Path(selected_path))
        if not selected_song.cover:
            return
        self.new_cover = selected_song.cover
        self.update_cover_display()

    def update_cover_display(self) -> None:
        self.ui.cover_label.clear()
        self.display_cover()
        self.update_cover_related_controls()

    def unset_current_cover(self) -> None:
        match self.which_cover_to_use():
            case self.CoverImageStates.NONE: return
            case self.CoverImageStates.SELECTED: self.new_cover = None
            case self.CoverImageStates.EMBEDDED: self.cover = None
        self.update_cover_display()

    def open_file_dialog(self, filter: str) -> str:
        return QFileDialog.getOpenFileName(
            self, "Select Cover Image", ".", filter)[0]

    def browse_cover(self) -> None:
        file_path = self.open_file_dialog("*.jpg")
        if file_path == "":
            return
        with open(file_path, "rb") as f:
            image_data = f.read()
        self.new_cover = image_data
        self.update_cover_display()

    def confirm(self) -> None:
        self.song.title = self.ui.title_edit.text()
        self.song.artist = self.ui.artist_edit.text()
        self.song.album = self.ui.album_edit.text()
        self.song.album_artist = self.ui.album_artist_edit.text()
        self.song.genre = self.ui.genre_edit.text()
        self.song.file_name = self.ui.file_name_edit.text()
        self.song.lyrics = self.ui.lyrics_edit.toPlainText()

        year_edit = self.ui.year_edit.text()
        self.song.year = int(year_edit) if year_edit != "" else 0

        self.song.track_num = (
            self.ui.track_count_spinbox.value(), self.ui.track_total_spinbox.value())
        self.song.disc_num = (self.ui.disc_count_spinbox.value(),
                              self.ui.disc_total_spinbox.value())

        self.song.new_cover = self.new_cover
        if not self.cover and self.song.cover:
            self.song.remove_covers()

        self.song.remove_other_tags = self.ui.remove_other_tags_checkbox.isChecked()
        self.song.preserve_file_time = self.ui.preserve_file_time_checkbox.isChecked()
        self.song.crop_cover_to_square = self.ui.crop_cover_checkbox.isChecked()

        self.close()

    def autofill_title_and_artist(self) -> None:
        res = self.song.get_title_and_artist_by_file_name(
            self.ui.file_name_edit.text())  # Better error
        if not res:
            return
        self.ui.artist_edit.setText(res[0])
        self.ui.title_edit.setText(res[1])

    def which_cover_to_use(self) -> EditTagsDialog.CoverImageStates:
        if self.new_cover:
            return self.CoverImageStates.SELECTED
        elif self.cover:
            return self.CoverImageStates.EMBEDDED
        return self.CoverImageStates.NONE

    def update_cover_related_controls(self) -> None:
        enabled = True
        text = ""
        image_data = None
        match self.which_cover_to_use():
            case self.CoverImageStates.SELECTED:
                text = "Unset selected cover image"
                image_data = self.new_cover
            case self.CoverImageStates.EMBEDDED:
                text = "Delete embedded cover image"
                image_data = self.cover
            case self.CoverImageStates.NONE:
                text = "Unset cover image"
                enabled = False
        self.unset_current_cover_action.setText(text)
        self.unset_current_cover_action.setEnabled(enabled)

        if not image_data:
            self.show_cover_full_size_action.setEnabled(False)
            self.ui.crop_cover_checkbox.setEnabled(False)
            self.ui.crop_cover_checkbox.setChecked(False)
            return
        if not self.show_cover_full_size_action.isEnabled():
            self.show_cover_full_size_action.setEnabled(True)

        image_editor = ImageEditor(image_data)
        if image_editor.image_is_square():
            self.ui.crop_cover_checkbox.setEnabled(False)
            self.ui.crop_cover_checkbox.setChecked(False)
        else:
            self.ui.crop_cover_checkbox.setEnabled(True)
            self.ui.crop_cover_checkbox.setChecked(True)

    def show_cover_full_size(self) -> None:
        which = self.which_cover_to_use()
        image_data = None
        if which == self.CoverImageStates.EMBEDDED:
            image_data = self.cover
        elif which == self.CoverImageStates.SELECTED:
            image_data = self.new_cover
        if not image_data:
            return
        self.image_viewer = ImageViewer(image_data, self)
        self.image_viewer.show()

    def display_cover(self) -> None:
        which = self.which_cover_to_use()
        if which == self.CoverImageStates.NONE:
            if not self.ui.cover_label.pixmap():
                return
            self.ui.cover_label.clear()
            return
        pixmap = QPixmap()
        if which == self.CoverImageStates.SELECTED:
            pixmap.loadFromData(self.new_cover)  # type: ignore
        elif which == self.CoverImageStates.EMBEDDED:
            pixmap.loadFromData(self.cover)  # type: ignore

        scaled_pixmap = pixmap.scaledToWidth(
            self.ui.cover_label.width(), Qt.TransformationMode.SmoothTransformation)
        self.ui.cover_label.setPixmap(scaled_pixmap)
        # self.cover_label.adjustSize()

    def fill_in_fields_from_song(self) -> None:
        self.ui.title_edit.setText(self.song.title)
        self.ui.artist_edit.setText(self.song.artist)
        self.ui.album_edit.setText(self.song.album)
        self.ui.album_artist_edit.setText(self.song.album_artist)
        self.ui.genre_edit.setText(self.song.genre)
        self.ui.track_count_spinbox.setValue(self.song.track_num[0])
        self.ui.disc_count_spinbox.setValue(self.song.disc_num[0])
        self.ui.track_total_spinbox.setValue(self.song.track_num[1])
        self.ui.disc_total_spinbox.setValue(self.song.disc_num[1])
        year = self.song.year
        if year:
            self.ui.year_edit.setText(str(year))
        self.ui.file_name_edit.setText(self.song.file_name)
        self.ui.lyrics_edit.setPlainText(self.song.lyrics)


class CheckableListWidget(QListWidget):
    def keyPressEvent(self, e: QKeyEvent | None) -> None:
        if not e:
            return
        key = e.key()
        if key not in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            return super().keyPressEvent(e)
        checked_states = [
            item.checkState() == Qt.CheckState.Checked for item in self.selectedItems()]
        if all(checked_states):
            for item in self.selectedItems():
                item.setCheckState(Qt.CheckState.Unchecked)
        elif not any(checked_states):
            for item in self.selectedItems():
                item.setCheckState(Qt.CheckState.Checked)
        else:
            for item in self.selectedItems():
                if item.checkState() == Qt.CheckState.Checked:
                    continue
                item.setCheckState(Qt.CheckState.Checked)
