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
    qInstallMessageHandler,
)
from PyQt6.QtGui import (
    QCloseEvent,
    QAction,
    QContextMenuEvent,
    QDragEnterEvent,
    QDropEvent,
    QKeyEvent,
    QKeySequence,
    QMouseEvent,
    QPainter,
    QPixmap,
    QRegularExpressionValidator,
    QIcon,
)

from PyQt6.QtWidgets import (
    QApplication,
    QDialogButtonBox,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QDialog,
    QLabel,
    QMenu,
    QPushButton,
    QFileDialog,
    QSpinBox,
    QStyle,
    QStyleFactory,
    QStyleOptionButton,
    QStyledItemDelegate,
    QVBoxLayout,
    QWidget,
    QLineEdit,
    QStyleOptionViewItem,
    QTableView,
    QAbstractItemView,
)

UI_DIR_NAME = "ui"
UI_FILE_NAMES = [
    "table_window.ui",
    "album_creation_dialog.ui",
    "edit_tags_dialog.ui",
    "set_all_dialog.ui",
]

DEBUG = False
if len(sys.argv) > 1:
    if sys.argv[1] == "--debug":
        DEBUG = True

if DEBUG:
    from ui.TableWindow import Ui_TableWindow
    from ui.AlbumCreationDialog import Ui_AlbumCreationDialog
    from ui.EditTagsDialog import Ui_EditTagsDialog
    from ui.SetAllDialog import Ui_SetAllDialog
else:
    from PyQt6 import uic
    Ui_TableWindow, _ = uic.loadUiType(os.path.join(UI_DIR_NAME, UI_FILE_NAMES[0]))
    Ui_AlbumCreationDialog, _ = uic.loadUiType(os.path.join(UI_DIR_NAME, UI_FILE_NAMES[1]))
    Ui_EditTagsDialog, _ = uic.loadUiType(os.path.join(UI_DIR_NAME, UI_FILE_NAMES[2]))
    Ui_SetAllDialog, _ = uic.loadUiType(os.path.join(UI_DIR_NAME, UI_FILE_NAMES[3]))


class AlbumCreationDialog(QDialog, Ui_AlbumCreationDialog):
    def __init__(self: AlbumCreationDialog, table_songs: list[Song], parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setupUi(self)
        self.setFixedSize(self.size())

        self.__table_songs = table_songs

        self.cover_button.clicked.connect(self.cover_browse_clicked)
        self.cover_button.setAutoDefault(True)

        self.clear_cover_button.clicked.connect(self.clear_cover_button_clicked)
        self.clear_cover_button.setIcon(QIcon("./icons/delete.png")) # TODO
        self.clear_cover_button.setAutoDefault(True)

        if not self.__table_songs:
            self.songs_button.clicked.connect(
                    lambda: self.songs_browse_clicked(False))
            self.songs_button.setAutoDefault(True)
        else:
            self.add_song_browse_button_menu()

        self.button_box.accepted.connect(self.confirm_button_clicked)
        self.button_box.rejected.connect(self.reject)
        for button in self.button_box.buttons():
            if isinstance(button, QPushButton):
                button.setAutoDefault(True)

        self.year_edit.setValidator(QRegularExpressionValidator(
                                    QRegularExpression("[1-9][0-9]{3}")))
        self.selected_cover = ""
        self.__songs: list[Song] = []

    def add_song_browse_button_menu(self: AlbumCreationDialog) -> None:
        self.songs_menu = QMenu(self)
        self.songs_button.setMenu(self.songs_menu)
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

    def clear_cover_button_clicked(self: AlbumCreationDialog) -> None:
        self.selected_cover = ""
        self.selected_cover_filename_label.setText("")

    def set_cover_path(self: AlbumCreationDialog, path: str) -> None:
        self.selected_cover = path
        self.selected_cover_filename_label.setText(os.path.basename(path))

    @property
    def songs(self: AlbumCreationDialog) -> list[Song]:
        return self.__songs

    @songs.setter
    def songs(self: AlbumCreationDialog, songs: list[Song]) -> None:
        self.__songs = songs
        self.selected_songs_filenames_label.setText(
            ", ".join([os.path.basename(x.updated_file_path()) for x in songs]))

    def get_new_songs(self: AlbumCreationDialog) -> list[Song]:
        assert hasattr(self, "_new_songs"), \
                "get_new_songs() was called before songs_browse_clicked()"
        if not self._new_songs: return []
        return self.songs

    def cover_browse_clicked(self: AlbumCreationDialog) -> None:
        self.set_cover_path(QFileDialog.getOpenFileName(
                self, "Select Cover Image", ".", "*.jpg")[0])

    def songs_browse_clicked(self: AlbumCreationDialog, already_opened: bool) -> None:
        if already_opened:
            self._new_songs = False
            self.dlg = SongsListDialog(
                "Choose songs", [x.file_name for x in self.__table_songs],
                True, self
            )
            if self.dlg.exec() != QDialog.DialogCode.Accepted: return
            selected_idxs = self.dlg.get_selected_indexes()
            if selected_idxs:
                self.songs = [self.__table_songs[i] for i in selected_idxs]
        else:
            self._new_songs = True
            self.songs = [Song(path) for path in QFileDialog.getOpenFileNames(
                          self, "Select Songs", ".", "Mp3 Files (*.mp3)")[0]]


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
        if not self.songs:
            self.status_bar.setText("Select songs for the album")
            return
        self.status_bar.setText("")

        cover_bytes = None
        if self.selected_cover:
            with open(self.selected_cover, "rb") as f:
                cover_bytes = f.read()

        for song in self.songs:
            song.new_cover = cover_bytes
            song.album = self.title_edit.text()
            song.artist = self.artist_edit.text()
            song.year = int(self.year_edit.text())
            song.update_crop_cover()
        self.accept()

class YearLineEditDelegate(QStyledItemDelegate):
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
        opt.state = QStyle.StateFlag.State_Enabled
        if option.state & QStyle.StateFlag.State_MouseOver:
            opt.state |= QStyle.StateFlag.State_MouseOver
        if option.state & QStyle.StateFlag.State_Selected:
                opt.state |= QStyle.StateFlag.State_Sunken | \
                            QStyle.StateFlag.State_Selected | \
                            QStyle.StateFlag.State_HasFocus
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
        assert isinstance(event, QMouseEvent)
        if not option.rect.contains(event.position().toPoint()): return False

        self.clicked.emit(index)
        return True

class TrackSpinBoxDelegate(QStyledItemDelegate):
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

        assert self.__audio_file
        if not self.__audio_file.tag:
            self.__original_file_has_tags = False
            self.__audio_file.initTag(version=eyed3.id3.ID3_V2_4)

    def updated_file_path(self: Song) -> str:
        return os.path.join(os.path.dirname(self.__file_path), self.__file_name)

    def update_crop_cover(self: Song) -> None:
        if self.__new_cover:
            self.__crop_cover_to_square = not ImageEditor(self.__new_cover).image_is_square()
        elif self.cover:
            self.__crop_cover_to_square = not ImageEditor(self.cover).image_is_square()

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
            assert self.cover
            image_editor = ImageEditor(self.cover)
            self.cover = image_editor.crop_to_center_square()

        self.__audio_file.tag.save(preserve_file_time=self.__preserve_file_time) # type: ignore
        if self.__file_name != os.path.basename(self.__file_path):
            return self.__rename()
        return True

    def __rename(self: Song) -> bool:
        if not self.__file_name.endswith(".mp3"):
            print(f"Error: {self.__file_name} is not a valid mp3 file name")
        new_path = self.updated_file_path()
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
    def track_num(self: Song) -> tuple[int, int]:
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
    def disc_num(self: Song) -> tuple[int, int]:
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
    #                         empty_table
    tableChanged = pyqtSignal(bool)

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

    def remove_rows(self: SongsTableModel, rows: list[int]) -> None:
        rows = sorted(rows)
        self.beginRemoveRows(QModelIndex(), rows[0], rows[-1])
        self.__songs = [self.__songs[i] for i in range(len(self.__songs)) if i not in rows]
        self.endRemoveRows()
        if not self.__songs: self.tableChanged.emit(True)

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
        self.tableChanged.emit(False) # for resizing the columns on update

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
        self.tableChanged.emit(False) # for resizing the columns on update
        return True


    def flags(self:SongsTableModel, index: QModelIndex) -> Qt.ItemFlag:
        if not index.isValid(): return Qt.ItemFlag.NoItemFlags
        flags = Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable
        if index.column() == self.__columns.index("All Tags"):
            return flags
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

class SetAllDialog(QDialog, Ui_SetAllDialog):
    Tags = Enum("Tags", ["TITLE", "ARTIST", "ALBUM", "ALBUM_ARTIST", "YEAR", "GENRE"])
    def __init__(self: SetAllDialog, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setupUi(self)
        self.__tags = {
            "Title": self.Tags.TITLE,
            "Artist": self.Tags.ARTIST,
            "Album": self.Tags.ALBUM,
            "Album Artist": self.Tags.ALBUM_ARTIST,
            "Year": self.Tags.YEAR,
            "Genre": self.Tags.GENRE,
        }
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        self.tags_combobox.addItems(self.__tags.keys())
        self.tags_combobox.currentTextChanged.connect(self.__combobox_changed)
        self.__validator_set = False

    def __combobox_changed(self: SetAllDialog, text: str) -> None:
        if text == "Year":
            self.value_edit.setValidator(QRegularExpressionValidator(
                                        QRegularExpression("[1-9][0-9]{3}")))
            if not self.value_edit.hasAcceptableInput():
                self.value_edit.setText("")
            self.__validator_set = True
        elif self.__validator_set:
            self.value_edit.setValidator(None)
            self.__validator_set = False

    def get_user_input(self: SetAllDialog) -> tuple[SetAllDialog.Tags, str]:
        return self.__tags[self.tags_combobox.currentText()], self.value_edit.text()

class TableWindow(QMainWindow, Ui_TableWindow):
    def __init__(self: TableWindow) -> None:
        super().__init__()
        self.setupUi(self)
        self.centralwidget.destroy()
        self.__songs_added = False

        self.setAcceptDrops(True)

        self.action_new.triggered.connect(self.new_album_dialog)
        self.action_save_all.triggered.connect(self.save_all)
        self.action_autofill_ta.triggered.connect(self.autofill_titles_and_artists)
        self.action_save_all.setEnabled(False)
        self.action_autofill_ta.setEnabled(False)
        self.action_set_all.setEnabled(False)
        self.action_open.triggered.connect(lambda: self.open(False))
        self.action_open_from_cb.triggered.connect(lambda: self.open(True))
        self.action_set_all.triggered.connect(self.set_all)
        self.setup_table()
        if DEBUG:
            self.menuFile.addSeparator()
            self.action_debug = QAction("Debug", self)
            self.menuFile.addAction(self.action_debug)
            self.action_debug.triggered.connect(self.debug)
            self.action_debug.setShortcut(QKeySequence("Ctrl+D"))
            self.style_counter = 0

    def debug(self: TableWindow) -> None:
        # print(" ---- debug ----")
        # print(" ---- end debug ----")
        all_styles = QStyleFactory.keys()
        print("All styles:", all_styles)
        style = QApplication.style()
        if not style: return
        print("Current Style:", style.objectName())
        if self.style_counter == len(all_styles)-1:
            self.style_counter = 0
        else: self.style_counter += 1
        QApplication.setStyle(all_styles[self.style_counter])
        print("New Style:", all_styles[self.style_counter])

    def dragEnterEvent(self: TableWindow, a0: QDragEnterEvent | None) -> None:
        if not a0: return
        mime_data = a0.mimeData()
        if not mime_data: return
        if not mime_data.hasUrls(): return
        all_paths = [url.toLocalFile() for url in mime_data.urls()]

        self.__accepted_drop_paths: list[str] = []
        for path in all_paths:
            if not path.lower().endswith(".mp3") or not os.path.isfile(path):
                continue
            self.__accepted_drop_paths.append(path)

        if self.__accepted_drop_paths:
            a0.acceptProposedAction()
        else:
            a0.ignore()

    def dropEvent(self: TableWindow, a0: QDropEvent | None) -> None:
        if not a0: return
        songs = []
        for path in self.__accepted_drop_paths:
            song = Song(path)
            song.update_crop_cover()
            songs.append(song)
        if songs: self.add_songs(songs)

    def paste(self: TableWindow) -> None:
        cb = QApplication.clipboard()
        if not cb: return
        mime_data = cb.mimeData()
        if not mime_data: return
        if not mime_data.hasUrls(): return
        all_paths = [url.toLocalFile() for url in mime_data.urls()]
        mp3_paths = [path for path in all_paths if path.lower().endswith(".mp3") and os.path.isfile(path)]
        songs = []
        for path in mp3_paths:
            song = Song(path)
            song.update_crop_cover()
            songs.append(song)
        if songs: self.add_songs(songs)

    def set_all(self: TableWindow) -> None:
        self.dlg = SetAllDialog()
        if self.dlg.exec() != QDialog.DialogCode.Accepted: return
        user_inp = self.dlg.get_user_input()
        match user_inp[0]:
            case self.dlg.Tags.TITLE:
                for i in range(len(self.model.songs)):
                    self.model.songs[i].title = user_inp[1]
            case self.dlg.Tags.ARTIST:
                for i in range(len(self.model.songs)):
                    self.model.songs[i].artist = user_inp[1]
            case self.dlg.Tags.ALBUM:
                for i in range(len(self.model.songs)):
                    self.model.songs[i].album = user_inp[1]
            case self.dlg.Tags.ALBUM_ARTIST:
                for i in range(len(self.model.songs)):
                    self.model.songs[i].album_artist = user_inp[1]
            case self.dlg.Tags.YEAR:
                for i in range(len(self.model.songs)):
                    self.model.songs[i].year = int(user_inp[1])
            case self.dlg.Tags.GENRE:
                for i in range(len(self.model.songs)):
                    self.model.songs[i].genre = user_inp[1]

    def keyPressEvent(self: TableWindow, a0: QKeyEvent | None) -> None:
        if not a0: return
        key = a0.key()
        if key not in (Qt.Key.Key_Delete, Qt.Key.Key_Return, Qt.Key.Key_Enter):
            return super().keyPressEvent(a0)
        selected_indexes = self.view.selectedIndexes()
        if not selected_indexes: return

        if key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            if len(selected_indexes) != 1: return
            index = selected_indexes[0]
            if index.column() == self.model.columns.index("All Tags"):
                return self.all_tags_button_clicked(index)
            return self.view.edit(index)
        # key has to be Key_Delete
        if selected_indexes[0].model() is self.proxy:
            selected_indexes = [self.proxy.mapToSource(index) for index in selected_indexes]
        self.model.remove_rows([index.row() for index in selected_indexes])

    def remove_rows(self: TableWindow, indexes: list[QModelIndex]) -> None:
        assert indexes
        if indexes[0].model() is self.proxy:
            indexes = [self.proxy.mapToSource(index) for index in indexes]
        self.model.remove_rows([index.row() for index in indexes])

    def setup_table(self: TableWindow) -> None:
        self.model = SongsTableModel()

        self.proxy = QSortFilterProxyModel()
        self.proxy.setSourceModel(self.model)

        self.action_paste = QAction("Paste", self)
        self.action_paste.setPriority(QAction.Priority.LowPriority)
        self.action_paste.setShortcut(QKeySequence.StandardKey.Paste)
        self.action_paste.triggered.connect(self.paste)
        self.addAction(self.action_paste)

        self.view = TableViewWithContextMenu()
        self.view.removeRows.connect(lambda row: self.remove_rows(row))

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

        self.model.tableChanged.connect(lambda empty_table: self.update_table(empty_table))

    def update_table(self: TableWindow, empty_table: bool):
        if empty_table:
            self.action_save_all.setEnabled(False)
            self.action_autofill_ta.setEnabled(False)
            self.action_set_all.setEnabled(False)
        self.view.resizeColumnsToContents()

    def open(self: TableWindow, from_cb: bool) -> None:
        paths = []
        if from_cb:
            cb = QApplication.clipboard()
            if not cb: return
            cb_contents = cb.text()
            if cb_contents == "": return
            raw_paths = cb_contents.strip().split(os.linesep)
            paths = [os.path.abspath(path) for path in raw_paths \
                            if os.path.isfile(path) and path.endswith(".mp3")]
        else:
            paths = QFileDialog.getOpenFileNames(
                self, "Select Songs", ".", "Mp3 Files (*.mp3)")[0]
        if not paths: return # TODO: might want to tell the user what happened
        songs = []
        for path in paths:
            song = Song(path)
            song.update_crop_cover()
            songs.append(song)
        self.add_songs(songs)

    def save_all(self: TableWindow) -> None:
        failed = []
        for i in range(len(self.model.songs)):
            this_new_path = self.model.songs[i].updated_file_path()
            self.status_bar.showMessage(f"Saving \"{this_new_path}\"")
            if not self.model.songs[i].save(): failed.append(this_new_path)
        message = "Finished Saving"
        time = 5000
        if failed:
            message += " (could not save: \""+", ".join(failed)+"\")"
            time *= 2
        self.status_bar.showMessage(message, time)

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

    def new_album_dialog(self: TableWindow) -> None:
        songs = []
        if self.__songs_added: songs = self.model.songs
        self.album_creation_dialog = AlbumCreationDialog(songs, self)
        res = self.album_creation_dialog.exec()
        if res == QDialog.DialogCode.Accepted:
            self.add_songs(self.album_creation_dialog.get_new_songs())
        else:
            self.action_new.setEnabled(True)

    def all_tags_button_clicked(self: TableWindow, index: QModelIndex) -> None:
        if index.model() is self.proxy: index = self.proxy.mapToSource(index)
        self.dialog = EditTagsDialog(self.model.songs, index.row(), self)
        self.dialog.exec()

    def add_songs(self: TableWindow, songs: list[Song]) -> None:
        # checking if they've already been added
        already_added_paths = [x.file_path for x in self.model.songs]
        songs = [x for x in songs if x.file_path not in already_added_paths]
        self.model.add_songs(songs)
        self.view.resizeColumnsToContents()

        self.action_save_all.setEnabled(True)
        self.action_autofill_ta.setEnabled(True)
        self.action_set_all.setEnabled(True)
        self.__songs_added = True

class TableViewWithContextMenu(QTableView):
    removeRows = pyqtSignal(object)
    def contextMenuEvent(self: TableViewWithContextMenu, a0: QContextMenuEvent | None) -> None:
        if not a0: return
        parent = self.parent()
        assert parent and isinstance(parent, TableWindow)

        context_menu = QMenu(self)

        # mouse is not on any rows
        if self.rowAt(a0.pos().y()) == -1:
            context_menu.addAction(parent.action_paste)
        else:
            selected_indexes = self.selectedIndexes()
            action_remove = QAction(context_menu)

            text = "Remove this row"
            if len(selected_indexes) > 1:
                text = "Remove selected rows"
            action_remove.triggered.connect(lambda: self.removeRows.emit(selected_indexes))
            action_remove.setText(text)

            context_menu.addAction(action_remove)
        context_menu.exec(a0.globalPos())

class CheckableListWidget(QListWidget):
    def keyPressEvent(self, e: QKeyEvent | None) -> None:
        if not e: return
        key = e.key()
        if key not in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            return super().keyPressEvent(e)
        checked_states = [item.checkState() == Qt.CheckState.Checked for item in self.selectedItems()]
        if all(checked_states):
            for item in self.selectedItems():
                item.setCheckState(Qt.CheckState.Unchecked)
        elif not any(checked_states):
            for item in self.selectedItems():
                item.setCheckState(Qt.CheckState.Checked)
        else:
            for item in self.selectedItems():
                if item.checkState() == Qt.CheckState.Checked: continue
                item.setCheckState(Qt.CheckState.Checked)

class SongsListDialog(QDialog):
    def __init__(self: SongsListDialog, title: str, items: list[str], allow_multiple: bool, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedSize(580, 440)
        self.setWindowTitle(title)

        self.allow_multiple = allow_multiple

        layout = QVBoxLayout()
        self.setLayout(layout)
        self.songs_list = CheckableListWidget()
        self.songs_list.itemDoubleClicked.connect(self.accept)
        self.button_box = QDialogButtonBox(
                QDialogButtonBox.StandardButton.Ok |
                QDialogButtonBox.StandardButton.Cancel
        )
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)

        layout.addWidget(self.songs_list)
        layout.addWidget(self.button_box)

        if self.allow_multiple:
            self.songs_list.setSelectionMode(
                    QAbstractItemView.SelectionMode.ExtendedSelection)
            for i in items:
                item = QListWidgetItem(i)
                item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsSelectable)
                item.setCheckState(Qt.CheckState.Unchecked)
                self.songs_list.addItem(item)
        else:
            self.songs_list.addItems(items)

    def get_selected_index(self: SongsListDialog) -> int | None:
        assert not self.allow_multiple
        selected_items = self.songs_list.selectedIndexes()
        if not selected_items: return
        return selected_items[0].row()

    def get_selected_indexes(self: SongsListDialog) -> list[int]:
        assert self.allow_multiple
        checked: list[int] = []
        for i in range(self.songs_list.count()):
            item = self.songs_list.item(i)
            if not item: continue
            if item.checkState() == Qt.CheckState.Checked:
                checked.append(i)
        return checked

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
        if self.__image.format not in  ("JPEG", "PNG"):
            raise ValueError(f"Expected JPEG/PNG format, got {self.__image.format}")

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
            other_songs = [x for x in self.songs]
            other_songs.remove(self.song)
            self.dlg = SongsListDialog(
                "Choose a song", [x.file_name for x in other_songs],
                False, self
            )
            if self.dlg.exec() != QDialog.DialogCode.Accepted: return
            selected_idx = self.dlg.get_selected_index()
            if selected_idx is not None: selected_song = other_songs[selected_idx]
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
    if not DEBUG:
        def custom_message_handler(_, __, ___): return
        qInstallMessageHandler(custom_message_handler)
    app = QApplication(sys.argv)
    table_window = TableWindow()
    table_window.show()

    sys.exit(app.exec())
