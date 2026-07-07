from __future__ import annotations
import os
import sys
import eyed3
import eyed3.id3
from PIL import Image
from io import BytesIO

from typing import Any
from enum import Enum
from PyQt6.QtCore import (
    QAbstractItemModel,
    QEvent,
    QRegularExpression,
    Qt,
    QModelIndex,
    QObject,
    pyqtSignal,
    QAbstractTableModel,
    QSortFilterProxyModel,
)
from PyQt6.QtGui import (
    QCloseEvent,
    QAction,
    QKeySequence,
    QMouseEvent,
    QPainter,
    QPixmap,
    QRegularExpressionValidator,
    QIcon,
)

from PyQt6.QtWidgets import (
    QApplication,
    QMainWindow,
    QDialog,
    QLabel,
    QMenu,
    QPushButton,
    QFileDialog,
    QItemDelegate,
    QSpinBox,
    QStyle,
    QStyleOptionButton,
    QStyledItemDelegate,
    QVBoxLayout,
    QWidget,
    QLineEdit,
    QStyleOptionViewItem,
    QTableView,
    # uic
)

# For Debug purposes
from ui.TableWindow import Ui_TableWindow
from ui.AlbumCreationDialog import Ui_AlbumCreationDialog
from ui.EditTagsDialog import Ui_EditTagsDialog
from ui.ListDialog import Ui_ListDialog

DEBUG = 1

class AlbumCreationDialog(QDialog, Ui_AlbumCreationDialog):
    def __init__(self: AlbumCreationDialog, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setupUi(self)
        self.setFixedSize(self.size())

        self.cover_button.clicked.connect(self.cover_browse_clicked)
        self.cover_button.setAutoDefault(True)

        self.clear_cover_button.clicked.connect(self.clear_cover_button_clicked)
        self.clear_cover_button.setIcon(QIcon("./icons/delete.png")) # TODO
        self.clear_cover_button.setAutoDefault(True)

        self.songs_button.clicked.connect(self.songs_browse_clicked)
        self.songs_button.setAutoDefault(True)

        self.status_bar = QLabel()
        self.status_bar_layout.addWidget(self.status_bar)

        self.button_box.accepted.connect(self.confirm_button_clicked)
        self.button_box.rejected.connect(self.reject)
        for button in self.button_box.buttons():
            if isinstance(button, QPushButton):
                button.setAutoDefault(True)

        self.year_edit.setValidator(QRegularExpressionValidator(
                                    QRegularExpression("[1-9][0-9]{3}")))
        self.selected_cover = ""
        self.selected_songs = []

        if DEBUG: pass

    def clear_cover_button_clicked(self: AlbumCreationDialog) -> None:
        self.selected_cover = ""
        self.selected_cover_filename_label.setText("")

    def set_cover_path(self: AlbumCreationDialog, path: str) -> None:
        self.selected_cover = path
        self.selected_cover_filename_label.setText(os.path.basename(path))

    def set_song_paths(self: AlbumCreationDialog, song_paths: list[str]) -> None:
        self.selected_songs = song_paths
        self.selected_songs_filenames_label.setText(
            ", ".join([os.path.basename(x) for x in song_paths]))

    def cover_browse_clicked(self: AlbumCreationDialog) -> None:
        self.set_cover_path(QFileDialog.getOpenFileName(
                self, "Select Cover Image", ".", "*.jpg")[0])

    def songs_browse_clicked(self: AlbumCreationDialog) -> None:
        self.set_song_paths(QFileDialog.getOpenFileNames(
                self, "Select Songs", ".", "Mp3 Files (*.mp3)")[0])

    def confirm_button_clicked(self: AlbumCreationDialog) -> None:
        if self.title_edit.displayText() == "":
            self.status_bar.setText("Enter the album's title")
            return
        if self.artist_edit.displayText() == "":
            self.status_bar.setText("Enter the artist's name")
            return
        if self.year_edit.displayText() == "":
            self.status_bar.setText("Enter the album's release year")
            return
        if not self.year_edit.hasAcceptableInput():
            self.status_bar.setText("Enter a valid album release year "+
                                    "(a number between 1000 and 9999)")
            return
        if len(self.selected_songs) == 0:
            self.status_bar.setText("Select songs for the album")
            return
        self.status_bar.setText("")

        cover_bytes = None
        needs_cropping = False
        if self.selected_cover:
            with open(self.selected_cover, "rb") as f:
                cover_bytes = f.read()
            needs_cropping = not ImageEditor(cover_bytes).image_is_square()

        self.songs = []
        for path in self.selected_songs:
            song = Song(path)
            song.new_cover = cover_bytes
            song.album = self.title_edit.text()
            song.artist = self.artist_edit.text()
            song.year = int(self.year_edit.text())
            song.crop_cover_to_square = needs_cropping
            self.songs.append(song)
        self.accept()

class YearLineEditDelegate(QItemDelegate):
    def createEditor(
        self: YearLineEditDelegate,
        parent: QWidget | None,
        option: QStyleOptionViewItem,
        index: QModelIndex) -> QLineEdit:
        editor = QLineEdit(parent)
        editor.setValidator(QRegularExpressionValidator(
                            QRegularExpression("[1-9][0-9]{3}")))
        return editor

class EditTagsButtonDelegate(QStyledItemDelegate):
    clicked = pyqtSignal(object)

    def paint(
        self: EditTagsButtonDelegate,
        painter: QPainter | None,
        option: QStyleOptionViewItem,
        index: QModelIndex) -> None:
        opt = QStyleOptionButton()
        opt.rect = option.rect
        opt.text = "Edit"
        style = QApplication.style()
        if not style: return
        style.drawControl(QStyle.ControlElement.CE_PushButton, opt, painter)

    def editorEvent(
        self: EditTagsButtonDelegate,
        event: QEvent | None,
        model: QAbstractItemModel | None,
        option: QStyleOptionViewItem,
        index: QModelIndex) -> bool:
        if not event: return False
        if event.type() != QEvent.Type.MouseButtonRelease: return False
        assert(isinstance(event, QMouseEvent))
        if not option.rect.contains(event.position().toPoint()): return False

        self.clicked.emit(index)
        return True

class TrackSpinBoxDelegate(QStyledItemDelegate):
    # def paint(self, painter: QPainter | None, option: QStyleOptionViewItem, index: QModelIndex) -> None:
    #     opt = QStyleOptionSpinBox()
    #     opt.rect = option.rect
    #     opt.state = option.state
    #     # opt.frame = True
    #     opt.stepEnabled = QAbstractSpinBox.StepEnabledFlag.StepUpEnabled | \
    #                         QAbstractSpinBox.StepEnabledFlag.StepDownEnabled

    #     style = QApplication.style()
    #     if not style: return
    #     style.drawComplexControl(QStyle.ComplexControl.CC_SpinBox, opt, painter)

    def createEditor(
        self: TrackSpinBoxDelegate,
        parent: QWidget | None,
        option: QStyleOptionViewItem,
        index: QModelIndex) -> QWidget | None:
        editor = QSpinBox(parent)
        editor.setFrame(False)
        editor.setMinimum(0)
        editor.setMaximum(100)
        return editor

    # def setEditorData(self, editor: QWidget | None, index: QModelIndex) -> None:
    #     model = index.model()
    #     if not model: return
    #     value = model.data(index, Qt.ItemDataRole.EditRole)
    #     if not isinstance(editor, QSpinBox): return
    #     editor.setValue(value)
    # def setModelData(self, editor: QWidget | None, model: QAbstractItemModel | None, index: QModelIndex) -> None:
    #     if not isinstance(editor, QSpinBox): return
    #     editor.interpretText()
    #     value = editor.value()
    #     if not model: return
    #     model.setData(index, value, Qt.ItemDataRole.EditRole)
    # def updateEditorGeometry(self, editor: QWidget | None, option: QStyleOptionViewItem, index: QModelIndex) -> None:
    #     if not editor: return
    #     editor.setGeometry(option.rect)

class Song(QObject):
    #                           proerty_name, new_value
    propertyChanged = pyqtSignal(str, object)

    def __init__(self: Song, file_path: str) -> None:
        super().__init__()
        self.__new_cover = None
        self.__file_path = os.path.abspath(file_path)
        self.__file_name = os.path.basename(self.__file_path)
        self.__audio_file = eyed3.load(self.__file_path) # TODO: add a check
        self.__remove_other_tags = True
        self.__preserve_file_time = True
        self.__crop_cover_to_square = False
        self.__original_file_has_tags = True
        self.__edited = False

        if not self.__audio_file: assert(False)
        if not self.__audio_file.tag:
            self.__original_file_has_tags = False
            self.__audio_file.initTag(version=eyed3.id3.ID3_V2_4)

    @property
    def crop_cover_to_square(self: Song) -> bool:
        return self.__crop_cover_to_square

    @crop_cover_to_square.setter
    def crop_cover_to_square(self: Song, value: bool) -> None:
        self.__crop_cover_to_square = value
        if not self.__edited: self.__edited = True

    @property
    def preserve_file_time(self: Song) -> bool:
        return self.__preserve_file_time

    @preserve_file_time.setter
    def preserve_file_time(self: Song, value: bool) -> None:
        self.__preserve_file_time = value
        if not self.__edited: self.__edited = True

    @property
    def remove_other_tags(self: Song) -> bool:
        return self.__remove_other_tags

    @remove_other_tags.setter
    def remove_other_tags(self: Song, value: bool) -> None:
        self.__remove_other_tags = value
        if not self.__edited: self.__edited = True

    def __repr__(self) -> str:
        return f"Song(track=\"{self.track_num}\" title={self.title.__repr__()} "+ \
               f"artist={self.artist.__repr__()} album={self.album.__repr__()} "+ \
               f"year={self.year.__repr__()} file_path={self.file_path.__repr__()}"+ \
               ")"
               # f" orig_file_path={self.orig_file_path.__repr__()})"

    @property
    def new_cover(self: Song) -> bytes | None:
        return self.__new_cover

    @new_cover.setter
    def new_cover(self: Song, new_cover: bytes | None) -> None:
        if new_cover == self.__new_cover: return
        self.__new_cover = new_cover
        if not self.__edited: self.__edited = True

    def __remove_all_tags(self: Song, preserve_file_time: bool) -> bool:
        if not self.__original_file_has_tags: return True
        ret = eyed3.id3.Tag.remove(self.__audio_file.path, eyed3.id3.ID3_ANY_VERSION, # type: ignore
                                    preserve_file_time=preserve_file_time)
        if ret: self.__audio_file.initTag(version=eyed3.id3.ID3_V2_4) # type: ignore
        return ret

    def _get_relevant_tags(self: Song) -> dict[str, Any]:
        return {
            "title": self.title,
            "artist": self.artist,
            "album": self.album,
            "year": self.year,
            "album_artist": self.album_artist,
            "lyrics": self.lyrics,
            "genre": self.genre,
            "track_num": self.track_num,
            "disc_num": self.disc_num,
            "cover": self.new_cover if self.new_cover else self.cover
        }

    def save(self: Song) -> bool:
        if not self.__edited: return False
        if self.__remove_other_tags:
            tags = self._get_relevant_tags()
            if not self.__remove_all_tags(self.__preserve_file_time): return False
            self.title = tags["title"]
            self.artist = tags["artist"]
            self.album = tags["album"]
            self.year = tags["year"]
            self.album_artist = tags["album_artist"]
            self.lyrics = tags["lyrics"]
            self.genre = tags["genre"]
            self.track_num = tags["track_num"]
            self.disc_num = tags["disc_num"]
            if tags["cover"]:
                self.cover = tags["cover"]
        if self.__crop_cover_to_square:
            assert(self.cover)
            image_editor = ImageEditor(self.cover)
            self.cover = image_editor.crop_to_center_square()

        self.__audio_file.tag.save(preserve_file_time=self.__preserve_file_time) # type: ignore
        if self.__file_name != os.path.basename(self.__file_path):
            return self.__rename()
        return True

    def __rename(self: Song) -> bool:
        if not self.__file_name.endswith(".mp3"):
            print(f"Error: {self.__file_name} is not a valid mp3 file name")
        new_path = os.path.join(os.path.dirname(self.__file_path), self.__file_name)
        if os.path.exists(new_path):
            print(f"Error {self.__file_name}: path already exists") # TODO: BETTER ERROR
            return False
        try:
            self.__audio_file.rename(self.__file_name, preserve_file_time=self.__preserve_file_time) # type: ignore
        except Exception as e:
            print(f"Error {self.__file_name}: {e}")
            return False
        return True

    def remove_images(self: Song) -> None:
        self._remove_frame_by_fid(eyed3.id3.frames.IMAGE_FID)

    def _remove_frame_by_fid(self: Song, fid: bytes) -> None:
        del self.__audio_file.tag.frame_set[fid] # type: ignore

    def remove_unknown_tags(self: Song) -> None:
        raise NotImplementedError()
        for fid in self.__audio_file.tag.unknown_frame_ids: # type: ignore
            del self.__audio_file.tag.frame_set[fid] # type: ignore

    def remove_comments(self: Song) -> None:
        raise NotImplementedError()
        del self.__audio_file.tag.frame_set[eyed3.id3.frames.COMMENT_FID] # type: ignore

    def get_title_and_artist_by_file_name(self: Song) -> tuple[str, str] | None:
        file_name = os.path.splitext(
                os.path.basename(self.file_name))[0]
        # TODO: might want to add regex validation
        splitted_file_name = file_name.split(' - ')
        parts_n = len(splitted_file_name)
        if parts_n == 2: return (splitted_file_name[0], splitted_file_name[1])
        
    def _has_cover(self: Song) -> bool:
        return len(self.__audio_file.tag.images) > 0 # type: ignore

    @property
    def cover(self: Song) -> bytes | None:
        if not self._has_cover(): return
        return self.__audio_file.tag.images[0].image_data # type: ignore

    @cover.setter
    def cover(self: Song, image_data: bytes) -> None:
        self.__audio_file.tag.images.set(3, image_data, "image/jpeg") # type: ignore
        if not self.__edited: self.__edited = True

    @property
    def file_path(self: Song) -> str:
        return self.__file_path

    @property
    def file_name(self: Song) -> str:
        return self.__file_name

    @file_name.setter
    def file_name(self: Song, new_file_name: str) -> None:
        if new_file_name == self.__file_name: return

        self.__file_name = new_file_name
        self.propertyChanged.emit("file_name", new_file_name)
        if not self.__edited: self.__edited = True

    @property
    def title(self: Song) -> str:
        title = self.__audio_file.tag.title # type: ignore
        if not title: return ""
        return title

    @title.setter
    def title(self: Song, new_title: str | None) -> None:
        if new_title == self.__audio_file.tag.title: return # type: ignore

        self.__audio_file.tag.title = new_title # type: ignore
        self.propertyChanged.emit("title", new_title)
        if not self.__edited: self.__edited = True

    @property
    def artist(self: Song) -> str:
        artist = self.__audio_file.tag.artist # type: ignore
        if not artist: return ""
        return artist

    @artist.setter
    def artist(self: Song, new_artist: str) -> None:
        if new_artist == self.__audio_file.tag.artist: return # type: ignore

        self.__audio_file.tag.artist = new_artist # type: ignore
        self.propertyChanged.emit("artist", new_artist)
        if not self.__edited: self.__edited = True

    @property
    def track_num(self: Song) -> tuple[int, int]: # TODO
        track_num = self.__audio_file.tag.track_num # type: ignore
        if not track_num: return (0, 0)
        count = total = 0
        if track_num.count: count = track_num.count
        if track_num.total: total = track_num.total
        return (count, total)

    @track_num.setter
    def track_num(self: Song, new_track_num: tuple[int, int]) -> None:
        if new_track_num == self.__audio_file.tag.track_num: return # type: ignore

        self.__audio_file.tag.track_num = new_track_num # type: ignore
        self.propertyChanged.emit("track_num", new_track_num)
        if not self.__edited: self.__edited = True

    @property
    def disc_num(self: Song) -> tuple[int, int]: # TODO
        disc_num = self.__audio_file.tag.disc_num # type: ignore
        if not disc_num: return (0, 0)
        count = total = 0
        if disc_num.count: count = disc_num.count
        if disc_num.total: total = disc_num.total
        return (count, total)

    @disc_num.setter
    def disc_num(self: Song, new_disc_num: tuple[int, int]) -> None:
        if new_disc_num == self.__audio_file.tag.disc_num: return # type: ignore

        self.__audio_file.tag.disc_num = new_disc_num # type: ignore
        self.propertyChanged.emit("disc_num", new_disc_num)
        if not self.__edited: self.__edited = True

    @property
    def album(self: Song) -> str:
        album = self.__audio_file.tag.album # type: ignore
        if not album: return ""
        return album

    @album.setter
    def album(self: Song, new_album: str) -> None:
        if new_album == self.__audio_file.tag.album: return # type: ignore

        self.__audio_file.tag.album = new_album # type: ignore
        self.propertyChanged.emit("album", new_album)
        if not self.__edited: self.__edited = True

    @property
    def album_artist(self: Song) -> str:
        album_artist = self.__audio_file.tag.album_artist # type: ignore
        if not album_artist: return ""
        return album_artist

    @album_artist.setter
    def album_artist(self: Song, new_album_artist: str) -> None:
        if new_album_artist == self.__audio_file.tag.album_artist: return # type: ignore

        self.__audio_file.tag.album_artist = new_album_artist # type: ignore
        if not self.__edited: self.__edited = True

    @property
    def genre(self: Song) -> str:
        genre = self.__audio_file.tag.genre # type: ignore
        if not genre: return ""
        return genre.name

    @genre.setter
    def genre(self: Song, new_genre: str) -> None:
        if new_genre == self.__audio_file.tag.genre: return # type: ignore

        self.__audio_file.tag.genre = new_genre # type: ignore
        if not self.__edited: self.__edited = True

    @property
    def lyrics(self: Song) -> str:
        if len(self.__audio_file.tag.lyrics) == 0: return "" # type: ignore
        return self.__audio_file.tag.lyrics[0].text # type: ignore

    @lyrics.setter
    def lyrics(self: Song, new_lyrics: str) -> None:
        if new_lyrics == self.lyrics: return
        if new_lyrics == "":
            self._remove_frame_by_fid(eyed3.id3.frames.LYRICS_FID)
            if not self.__edited: self.__edited = True
            return
        self.__audio_file.tag.lyrics.set(new_lyrics) # type: ignore
        if not self.__edited: self.__edited = True

    def fix_date(self: Song) -> int:
        self.__audio_file.tag.recording_date = self.__audio_file.tag.getBestDate() # type: ignore
        self.__audio_file.tag.original_release_date = None # type: ignore
        self.__audio_file.tag.release_date = None # type: ignore
        return self.__audio_file.tag.recording_date.year # type: ignore

    @property
    def year(self: Song) -> int | None:
        best_date = self.__audio_file.tag.getBestDate(prefer_recording_date=True) # type: ignore
        if not best_date: return
        if best_date != self.__audio_file.tag.recording_date: # type: ignore
            return self.fix_date()
        return best_date.year

    @year.setter
    def year(self: Song, new_year: int | None) -> None:
        if new_year == self.year: return
        self.__audio_file.tag.recording_date = str(new_year) # type: ignore
        if not self.__edited: self.__edited = True
        self.propertyChanged.emit("year", new_year)


class SongsTableModel(QAbstractTableModel):
    tableChanged = pyqtSignal()

    def __init__(self: SongsTableModel) -> None:
        super().__init__()
        self.__songs: list[Song] = []
        self.__columns = [
            "Track #",
            "Title",
            "Artist",
            "Album",
            "Year",
            "All Tags",
            "File Name",
        ]

    @property
    def columns(self: SongsTableModel) -> list[str]:
        return self.__columns

    @property
    def songs(self: SongsTableModel) -> list[Song]:
        return self.__songs

    def add_songs(self: SongsTableModel, songs: list[Song]) -> None:
        songs_n = len(self.__songs)
        self.beginInsertRows(QModelIndex(), songs_n, songs_n+len(songs)-1)
        for row, song in enumerate(songs):
            song.propertyChanged.connect(
                lambda name, _, row=row: self._on_song_prop_change(name, row))
            self.__songs.append(song)
        self.endInsertRows()

    def _on_song_prop_change(self: SongsTableModel, name: str, row: int) -> None:
        col = None
        match name:
            case "file_name":
                col = self.__columns.index("File Name")
            case "title":
                col = self.__columns.index("Title")
            case "artist":
                col = self.__columns.index("Artist")
            case "track_num":
                col = self.__columns.index("Track #")
            case "album":
                col = self.__columns.index("Album")
            case "year":
                col = self.__columns.index("Year")
        if not col: return

        # they're the same because we're only trying to specify one cell
        top_left = bottom_right = self.index(row, col)
        self.dataChanged.emit(top_left, bottom_right, [Qt.ItemDataRole.DisplayRole])
        self.tableChanged.emit() # for resizing the columns on update

    def data(self: SongsTableModel, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        if not index.isValid(): return
        song = self.__songs[index.row()]
        col = self.__columns[index.column()]
        if role not in (Qt.ItemDataRole.DisplayRole, Qt.ItemDataRole.EditRole): return
        match col:
            case 'Track #':
                return song.track_num[0]
            case 'Title':
                return song.title
            case 'Artist':
                return song.artist
            case 'Album':
                return song.album
            case 'Year':
                return song.year
            case 'File Name':
                return song.file_name

    def setData(
        self: SongsTableModel,
        index: QModelIndex,
        value: str,
        role: int = Qt.ItemDataRole.EditRole) -> bool:
        if not index.isValid() or role != Qt.ItemDataRole.EditRole: return False
        song = self.__songs[index.row()]
        col = self.__columns[index.column()]
        match col:
            case 'Track #':
                if not value.isdigit(): return False
                song.track_num = (int(value), song.track_num[1])
            case 'Title':
                song.title = value
            case 'Artist':
                song.artist = value
            case 'Album':
                song.album = value
            case 'Year':
                if not value.isdigit(): return False
                song.year = int(value)
            case 'File Name':
                song.file_name = value
            case _:
                return False
        self.tableChanged.emit() # for resizing the columns on update
        return True


    def flags(self:SongsTableModel, index: QModelIndex) -> Qt.ItemFlag:
        if not index.isValid(): return Qt.ItemFlag.NoItemFlags
        flags = Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable
        if index.column() == self.__columns.index("All Tags"): return flags
        return flags | Qt.ItemFlag.ItemIsEditable

    def headerData(
        self,
        section: int,
        orientation: Qt.Orientation,
        role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        if role != Qt.ItemDataRole.DisplayRole: return
        if orientation != Qt.Orientation.Horizontal: return
        return self.__columns[section]

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return len(self.__songs)

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return len(self.__columns)

class TableWindow(QMainWindow, Ui_TableWindow):
    def __init__(self: TableWindow) -> None:
        super().__init__()
        self.setupUi(self)
        self.centralwidget.destroy()

        self.action_new.triggered.connect(self.new_album_window)
        self.action_save_all.triggered.connect(self.save_all)
        self.action_autofill_ta.triggered.connect(self.autofill_titles_and_artists)
        self.action_save_all.setShortcut(QKeySequence("Ctrl+Shift+S"))
        self.toggle_menu_bar_actions(False)

        if DEBUG:
            self.action_debug = QAction("Debug", self)
            self.menuFile.addAction(self.action_debug)
            self.action_debug.triggered.connect(self.debug)
            self.action_debug.setShortcut(QKeySequence("Ctrl+D"))

    def toggle_menu_bar_actions(self: TableWindow, enabled: bool) -> None:
        self.action_new.setEnabled(enabled)
        self.action_save_all.setEnabled(enabled)
        self.action_autofill_ta.setEnabled(enabled)

    def save_all(self: TableWindow) -> None:
        for i in range(len(self.model.songs)):
            self.model.songs[i].save()

    def closeEvent(self: TableWindow, a0: QCloseEvent | None) -> None:
        if not a0: return
        a0.accept()
        QApplication.quit()

    def autofill_titles_and_artists(self: TableWindow) -> None:
        for i in range(len(self.model.songs)):
            res = self.model.songs[i].get_title_and_artist_by_file_name()
            if not res: return # TODO: Better error
            self.model.songs[i].artist = res[0]
            self.model.songs[i].title = res[1]

    def debug(self: TableWindow) -> None:
        print(" ---- debug ----")
        print(" ---- end debug ----")

    def new_album_window(self: TableWindow) -> None:
        self.album_creation_dialog = AlbumCreationDialog(self)
        res = self.album_creation_dialog.exec()
        if res == QDialog.DialogCode.Accepted:
            self.add_songs(self.album_creation_dialog.songs)
        else:
            self.action_new.setEnabled(True)

        # self.album_creation_dialog.show()

    def all_tags_button_clicked(self: TableWindow, index: QModelIndex) -> None:
        if index.model() is self.proxy: index = self.proxy.mapToSource(index)
        row = index.row()
        self.dialog = EditTagsDialog(self.model.songs, row, self)
        self.dialog.exec()
    
    def add_songs(self: TableWindow, songs: list[Song]) -> None:
        self.model = SongsTableModel()

        self.proxy = QSortFilterProxyModel()
        self.proxy.setSourceModel(self.model)

        self.view = QTableView()
        self.view.setModel(self.proxy)
        self.view.setSortingEnabled(True)
        self.setCentralWidget(self.view)

        self.year_line_edit_delegate = YearLineEditDelegate()
        self.view.setItemDelegateForColumn(self.model.columns.index("Year"), self.year_line_edit_delegate)

        self.edit_tags_button_delegate = EditTagsButtonDelegate()
        self.edit_tags_button_delegate.clicked.connect(self.all_tags_button_clicked)
        self.view.setItemDelegateForColumn(self.model.columns.index("All Tags"), self.edit_tags_button_delegate)

        self.track_item_delegate = TrackSpinBoxDelegate()
        self.view.setItemDelegateForColumn(self.model.columns.index("Track #"), self.track_item_delegate)

        vertical_header = self.view.verticalHeader()
        if vertical_header is not None:
            vertical_header.hide()

        self.model.add_songs(songs)
        self.view.resizeColumnsToContents()
        self.model.tableChanged.connect(self.view.resizeColumnsToContents)
        self.toggle_menu_bar_actions(True)

class SongsListDialog(QDialog, Ui_ListDialog):
    def __init__(self: SongsListDialog, items: list[str], parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setupUi(self)
        self.songs_list.addItems(items)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        self.songs_list.itemDoubleClicked.connect(self.accept)

    def get_selected(self: SongsListDialog) -> int | None:
        selected_items = self.songs_list.selectedIndexes()
        if len(selected_items) == 0: return
        return selected_items[0].row()

class ImageViewer(QWidget):
    def __init__(self: ImageViewer, image_data: bytes, parent: QWidget | None = None):
        super().__init__(parent, Qt.WindowType.Window)
        self.setWindowTitle("Image Viewer")

        layout = QVBoxLayout()
        label = QLabel()
        layout.addWidget(label)
        pixmap = QPixmap()
        pixmap.loadFromData(image_data)
        label.setPixmap(pixmap)
        self.setLayout(layout)
        self.setFixedSize(pixmap.width(), pixmap.height())
        # self.setWindowModality(Qt.WindowModality.WindowModal)

class ImageEditor:
    def __init__(self: ImageEditor, data: bytes) -> None:
        self.__data = data
        self.__image = Image.open(BytesIO(data))
        print('ImageEditor format:', self.__image.format)
        if self.__image.format != "JPEG":
            raise ValueError(f"Expected JPEG format, got {self.__image.format}")

    def image_is_square(self: ImageEditor) -> bool:
        return self.__image.width == self.__image.height

    @property
    def data(self: ImageEditor) -> bytes:
        return self.__data

    def crop_to_center_square(self: ImageEditor) -> bytes:
        width, height = self.__image.size
        x = (width-height)/2
        self.__image = self.__image.crop((x, 0, x+height, height))
        output_bytes = BytesIO()
        self.__image.save(output_bytes, format="JPEG", quality=95)
        return output_bytes.getvalue()

class EditTagsDialog(QDialog, Ui_EditTagsDialog):
    CoverImageStates = Enum("CoverImageStates", ["SELECTED", "EMBEDDED", "NONE"])

    def __init__(self: EditTagsDialog, songs: list[Song], index: int, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setupUi(self)
        self.setFixedSize(self.size())
        self.songs = songs
        self.index = index
        self.song = self.songs[self.index]

        self.year_edit.setValidator(QRegularExpressionValidator(
                                    QRegularExpression("[1-9][0-9]{3}")))
        self.button_box.accepted.connect(self.confirm)
        self.button_box.rejected.connect(self.close)
        self.tabs.setCurrentIndex(0)
        self.new_cover = self.song.new_cover
        self.__cover = self.song.cover

        # Fill title and artist based on file name
        self.fill_ta_button.clicked.connect(self.autofill_title_and_artist)

        self.fill_in_fields_from_song()
        self.display_cover()


        self.file_name_edit.setText(os.path.basename(self.song.file_name))


        # Change Cover Button
        self.cover_menu = QMenu(self)
        self.change_cover_button.setMenu(self.cover_menu)

        self.show_cover_full_size_action = QAction("Show full size", self.cover_menu)
        self.show_cover_full_size_action.triggered.connect(self.show_cover_full_size)
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
        self.unset_current_cover_action.triggered.connect(self.unset_current_cover)
        self.update_cover_related_controls()

        # Copy Tags From Another File
        self.copy_from_another_file_menu = QMenu(self)
        self.copy_from_another_file_button.setMenu(self.copy_from_another_file_menu)


        self.copy_from_another_file_menu.addAction(
                QIcon(), "Copy from an already opened file", lambda: self.open_copy_tags_dialog(True),
                Qt.ConnectionType.AutoConnection)
        self.copy_from_another_file_menu.addAction(
                QIcon(), "Browse for file", lambda: self.open_copy_tags_dialog(False),
                Qt.ConnectionType.AutoConnection)

        self.preserve_file_time_checkbox.setChecked(self.song.preserve_file_time)
        self.remove_other_tags_checkbox.setChecked(self.song.remove_other_tags)
        self.crop_cover_checkbox.setChecked(self.song.crop_cover_to_square)

        self.music_list.hide()
        # if self.song.crop_cover_to_square:
        #     self.crop_cover_checkbox.setChecked(True)
        #     self.crop_cover_checkbox.setEnabled(True)
        # else:
        #     self.crop_cover_checkbox.setChecked(False)

    @property
    def cover(self: EditTagsDialog) -> bytes | None:
        return self.__cover

    @cover.setter
    def cover(self: EditTagsDialog, cover: None) -> None:
        self.__cover = cover

    def open_copy_tags_dialog(self: EditTagsDialog, already_opened: bool) -> None:
        selected_song = None
        if already_opened:
            self.dlg = SongsListDialog([x.file_name for x in self.songs], self)
            if self.dlg.exec() != QDialog.DialogCode.Accepted: return
            selected_idx = self.dlg.get_selected()
            if selected_idx is not None: selected_song = self.songs[selected_idx]
        else:
            selected_path = self.open_file_dialog("*.mp3")
            if selected_path: selected_song = Song(selected_path)
        if not selected_song: return

        self.copy_tags_from_song(selected_song)

    def copy_tags_from_song(self: EditTagsDialog, selected_song: Song) -> None:
        self.title_edit.setText(selected_song.title)
        self.artist_edit.setText(selected_song.artist)
        self.album_edit.setText(selected_song.album)
        self.album_artist_edit.setText(selected_song.album_artist)
        self.genre_edit.setText(selected_song.genre)
        self.lyrics_edit.setPlainText(selected_song.lyrics)
        self.track_count_spinbox.setValue(selected_song.track_num[0])
        self.track_total_spinbox.setValue(selected_song.track_num[1])
        self.disc_count_spinbox.setValue(selected_song.disc_num[0])
        self.disc_total_spinbox.setValue(selected_song.disc_num[1])
        self.year_edit.setText(str(selected_song.year))

    def copy_cover(self: EditTagsDialog) -> None:
        selected_path = self.open_file_dialog("*.mp3")
        if not selected_path: return
        selected_song = Song(selected_path)
        if not selected_song.cover: return
        self.new_cover = selected_song.cover
        self.update_cover_display()

    def update_cover_display(self: EditTagsDialog) -> None:
        self.cover_label.clear()
        self.display_cover()
        self.update_cover_related_controls()

    def unset_current_cover(self: EditTagsDialog) -> None:
        match self.which_cover_to_use():
            case self.CoverImageStates.NONE: return
            case self.CoverImageStates.SELECTED: self.new_cover = None
            case self.CoverImageStates.EMBEDDED: self.cover = None
        self.update_cover_display()

    def open_file_dialog(self: EditTagsDialog, filter: str) -> str:
        return QFileDialog.getOpenFileName(
                self, "Select Cover Image", ".", filter)[0]

    def browse_cover(self: EditTagsDialog) -> None:
        file_path = self.open_file_dialog("*.jpg")
        if file_path == "": return
        with open(file_path, "rb") as f:
            image_data = f.read()
        self.new_cover = image_data
        self.update_cover_display()

    # def clean_out_tags(self: EditTagsDialog) -> None:
    #     self.song.remove_unknown_tags()
    #     self.song.remove_comments()

    def confirm(self: EditTagsDialog) -> None:
        self.song.title = self.title_edit.text()
        self.song.artist = self.artist_edit.text()
        self.song.album = self.album_edit.text()
        self.song.album_artist = self.album_artist_edit.text()
        self.song.genre = self.genre_edit.text()
        self.song.file_name = self.file_name_edit.text()
        self.song.lyrics = self.lyrics_edit.toPlainText()

        year_edit = self.year_edit.text()
        if year_edit != "": self.song.year = int(year_edit)

        self.song.track_num = (self.track_count_spinbox.value(), self.track_total_spinbox.value())
        self.song.disc_num = (self.disc_count_spinbox.value(), self.disc_total_spinbox.value())

        self.song.new_cover = self.new_cover
        if not self.cover and self.song.cover: self.song.remove_images()

        self.song.remove_other_tags = self.remove_other_tags_checkbox.isChecked()
        self.song.preserve_file_time = self.preserve_file_time_checkbox.isChecked()
        self.song.crop_cover_to_square = self.crop_cover_checkbox.isChecked()

        self.close()

    def autofill_title_and_artist(self: EditTagsDialog):
        res = self.song.get_title_and_artist_by_file_name() # Better error
        if not res: return
        self.artist_edit.setText(res[0])
        self.title_edit.setText(res[1])

    def which_cover_to_use(self: EditTagsDialog) -> EditTagsDialog.CoverImageStates:
        if self.new_cover: return self.CoverImageStates.SELECTED
        elif self.cover: return self.CoverImageStates.EMBEDDED
        return self.CoverImageStates.NONE

    def update_cover_related_controls(self: EditTagsDialog) -> None:
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
            self.crop_cover_checkbox.setEnabled(False)
            self.crop_cover_checkbox.setChecked(False)
            return
        if not self.show_cover_full_size_action.isEnabled():
            self.show_cover_full_size_action.setEnabled(True)

        image_editor = ImageEditor(image_data)
        if image_editor.image_is_square():
            self.crop_cover_checkbox.setEnabled(False)
            self.crop_cover_checkbox.setChecked(False)
        else:
            self.crop_cover_checkbox.setEnabled(True)
            self.crop_cover_checkbox.setChecked(True)


    def show_cover_full_size(self: EditTagsDialog) -> None:
        which = self.which_cover_to_use()
        image_data = None
        if which == self.CoverImageStates.EMBEDDED:
            image_data = self.cover
        elif which == self.CoverImageStates.SELECTED:
            image_data = self.new_cover
        if not image_data: return
        self.image_viewer = ImageViewer(image_data, self)
        self.image_viewer.show()

    def display_cover(self: EditTagsDialog) -> None:
        which = self.which_cover_to_use()
        if which == self.CoverImageStates.NONE:
            if not self.cover_label.pixmap(): return
            self.cover_label.clear()
            return
        pixmap = QPixmap()
        if which == self.CoverImageStates.SELECTED:
            pixmap.loadFromData(self.new_cover) # type: ignore
        elif which == self.CoverImageStates.EMBEDDED:
            pixmap.loadFromData(self.cover) # type: ignore

        scaled_pixmap = pixmap.scaledToWidth(
                self.cover_label.width(), Qt.TransformationMode.SmoothTransformation)
        self.cover_label.setPixmap(scaled_pixmap)
        # self.cover_label.adjustSize()

    def fill_in_fields_from_song(self: EditTagsDialog):
        self.title_edit.setText(self.song.title)
        self.artist_edit.setText(self.song.artist)
        self.album_edit.setText(self.song.album)
        self.album_artist_edit.setText(self.song.album_artist)
        self.genre_edit.setText(self.song.genre)
        self.track_count_spinbox.setValue(self.song.track_num[0])
        self.disc_count_spinbox.setValue(self.song.disc_num[0])
        year = self.song.year
        if year: self.year_edit.setText(str(year))
        self.lyrics_edit.setPlainText(self.song.lyrics)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    table_window = TableWindow()
    table_window.show()
    table_window.new_album_window()

    sys.exit(app.exec())
