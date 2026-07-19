from __future__ import annotations
import os
import re
import sys
from PIL import Image, UnidentifiedImageError
from io import BytesIO
from mutagen.id3 import ID3
from mutagen.id3._frames import (
    Frame, APIC, TRCK, TPOS, USLT, TIT2, TPE1, TALB, TPE2, TCON, TDRC, TDRL,
)
from mutagen.id3._specs import PictureType
from mutagen.id3._util import ID3NoHeaderError
from typing import Any
from enum import Enum
from pathlib import Path
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
    QHeaderView,
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

from .ui.TableWindow import Ui_TableWindow
from .ui.AlbumCreationDialog import Ui_AlbumCreationDialog
from .ui.EditTagsDialog import Ui_EditTagsDialog
from .ui.SetAllDialog import Ui_SetAllDialog
from .config import DISCARD_ICON_PATH, SVG_LOGO_FILE_PATH, PLATFORM

DEBUG = False
if len(sys.argv) > 1:
    debug_place_idx = 1 if Path(sys.argv[0]).name != "bootstrap.py" or len(sys.argv) == 2 else 2
    if sys.argv[debug_place_idx] in ("debug", "--debug"):
        DEBUG = True

class AlbumCreationDialog(QDialog):
    def __init__(self: AlbumCreationDialog, table_songs: list[Song], parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.ui = Ui_AlbumCreationDialog()
        self.ui.setupUi(self)
        self.setFixedSize(self.size())

        self.__table_songs = table_songs

        self.ui.cover_button.clicked.connect(self.cover_browse_clicked)
        self.ui.cover_button.setAutoDefault(True)

        self.ui.clear_cover_button.clicked.connect(self.clear_cover_button_clicked)
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
        self.selected_cover_path: Path | None
        self.__songs: list[Song] = []

    def add_song_browse_button_menu(self: AlbumCreationDialog) -> None:
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

    def clear_cover_button_clicked(self: AlbumCreationDialog) -> None:
        self.selected_cover_path = None
        self.ui.selected_cover_filename_label.setText("")

    def set_cover_path(self: AlbumCreationDialog, path: Path) -> None:
        self.selected_cover_path = path
        self.ui.selected_cover_filename_label.setText(path.name)

    @property
    def songs(self: AlbumCreationDialog) -> list[Song]:
        return self.__songs

    @songs.setter
    def songs(self: AlbumCreationDialog, songs: list[Song]) -> None:
        self.__songs = songs
        self.ui.selected_songs_filenames_label.setText(
            ", ".join([x.updated_file_path().name for x in songs]))

    def get_new_songs(self: AlbumCreationDialog) -> list[Song]:
        assert hasattr(self, "_new_songs"), \
                "get_new_songs() was called before songs_browse_clicked()"
        if not self._new_songs: return []
        return self.songs

    def cover_browse_clicked(self: AlbumCreationDialog) -> None:
        self.set_cover_path(Path(QFileDialog.getOpenFileName(
                self, "Select Cover Image", ".", "*.jpg")[0]))

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
            raw_paths = QFileDialog.getOpenFileNames(
                          self, "Select Songs", ".", "Mp3 Files (*.mp3)")[0]
            self.songs = [Song(path) for path in
                                      [Path(x) for x in raw_paths]]


    def confirm_button_clicked(self: AlbumCreationDialog) -> None:
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
            self.ui.status_bar.setText("Enter a valid album release year "+
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

class YearLineEditDelegate(QStyledItemDelegate):
    def __init__(self, parent: QObject | None = None) -> None:
        self.validation_regex = "^$|[1-9][0-9]{3}"
        super().__init__(parent)
    def createEditor(
        self: YearLineEditDelegate,
        parent: QWidget | None,
        option: QStyleOptionViewItem,
        index: QModelIndex) -> QLineEdit:
        editor = QLineEdit(parent)
        editor.setValidator(QRegularExpressionValidator(
                            QRegularExpression(self.validation_regex)))
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

class Tag:
    def __init__(self: Tag, id3: ID3) -> None:
        self.id3 = id3
        self.__frames: dict[str, tuple[str, type[Frame]]] = {
            "title":          ("TIT2", TIT2),
            "artist":         ("TPE1", TPE1),
            "album":          ("TALB", TALB),
            "album_artist":   ("TPE2", TPE2),
            "genre":          ("TCON", TCON),
            "cover":          ("APIC", APIC),
            "track_num":      ("TRCK", TRCK),
            "disc_num":       ("TPOS", TPOS),
            "lyrics":         ("USLT", USLT),
            "recording_date": ("TDRC", TDRC),
            "release_date":   ("TDRL", TDRL),
        }
        self.year          = self.__init_year()
        self.track_num     = self.__init_track_or_disc_num("track")
        self.disc_num      = self.__init_track_or_disc_num("disc")
        self.__cover_fids  = self.__init_cover_or_lyrics("cover")
        self.__lyrics_fids = self.__init_cover_or_lyrics("lyrics")

    def remove_covers(self: Tag) -> None:
        self.__remove_by_fids(self.__cover_fids)
        self.__cover_fids = []

    def __remove_by_fids(self: Tag, fids: list[str]) -> None:
        for fid in fids:
            del self.id3[fid]

    def __remove_frame_by_fid(self: Tag, fid: str) -> None:
        del self.id3[fid]

    def __simple_string_tag_getter(self: Tag, fid: str) -> str:
        if fid not in self.id3: return ""
        return self.id3[fid][0]

    def __simple_string_tag_setter(self: Tag, name: str, new_value: str) -> None:
        old_value = None
        fid = self.__frames[name][0]
        if fid == self.__frames["title"][0]:
            old_value = self.title
        elif fid == self.__frames["artist"][0]:
            old_value = self.artist
        elif fid == self.__frames["album"][0]:
            old_value = self.album
        elif fid == self.__frames["album_artist"][0]:
            old_value = self.album_artist
        elif fid == self.__frames["genre"][0]:
            old_value = self.genre
        if new_value == old_value: return
        if new_value == "": self.__remove_frame_by_fid(fid)
        self.id3[fid] = self.__frames[name][1](text=new_value)

    @property
    def title(self: Tag):
        return self.__simple_string_tag_getter(self.__frames["title"][0])

    @title.setter
    def title(self: Tag, new_title: str) -> None:
        self.__simple_string_tag_setter("title", new_title)

    @property
    def artist(self: Tag):
        return self.__simple_string_tag_getter(self.__frames["artist"][0])

    @artist.setter
    def artist(self: Tag, new_artist: str) -> None:
        self.__simple_string_tag_setter("artist", new_artist)

    @property
    def album(self: Tag):
        return self.__simple_string_tag_getter(self.__frames["album"][0])

    @album.setter
    def album(self: Tag, new_album: str) -> None:
        self.__simple_string_tag_setter("album", new_album)

    @property
    def album_artist(self: Tag):
        return self.__simple_string_tag_getter(self.__frames["album_artist"][0])

    @album_artist.setter
    def album_artist(self: Tag, new_album_artist: str) -> None:
        self.__simple_string_tag_setter("album_artist", new_album_artist)

    @property
    def genre(self: Tag):
        return self.__simple_string_tag_getter(self.__frames["genre"][0])

    @genre.setter
    def genre(self: Tag, new_genre: str) -> None:
        self.__simple_string_tag_setter("genre", new_genre)

    @property
    def track_num(self: Tag) -> tuple[int, int]:
        text = self.__simple_string_tag_getter(self.__frames["track_num"][0])
        if text == "": return (0, 0)
        if "/" in text:
            count, total = text.split("/")
            return (int(count), int(total))
        return (int(text), 0)

    @track_num.setter
    def track_num(self: Tag, new_track_num: tuple[int, int]) -> None:
        if new_track_num == self.track_num: return
        fid = self.__frames["track_num"][0]
        if new_track_num == (0, 0): return self.__remove_frame_by_fid(fid)
        res = str(new_track_num[0])
        if new_track_num[1] != 0:
            res = str(new_track_num[0])+"/"+str(new_track_num[1])
        self.id3[fid] = TRCK(text=res)

    @property
    def disc_num(self: Tag) -> tuple[int, int]:
        text = self.__simple_string_tag_getter(self.__frames["disc_num"][0])
        if text == "": return (0, 0)
        if "/" in text:
            count, total = text.split("/")
            return (int(count), int(total))
        return (int(text), 0)

    @disc_num.setter
    def disc_num(self: Tag, new_disc_num: tuple[int, int]) -> None:
        if new_disc_num == self.disc_num: return
        fid = self.__frames["disc_num"][0]
        if new_disc_num == (0, 0): return self.__remove_frame_by_fid(fid)
        res = str(new_disc_num[0])
        if new_disc_num[1] != 0:
            res = str(new_disc_num[0])+"/"+str(new_disc_num[1])
        self.id3[fid] = TPOS(text=res)

    @property
    def cover(self: Tag) -> bytes | None:
        if len(self.__cover_fids) == 0: return
        return self.id3[self.__cover_fids[0]].data

    @cover.setter
    def cover(self: Tag, image_data: bytes) -> None:
        fid = self.__frames["cover"][0]
        self.id3[fid] = APIC(
            encoding = 3, # UTF-8
            mime = "image/jpeg", # TODO: not handling png files
            type=PictureType.COVER_FRONT, 
            desc="",
            data=image_data
        )
        self.__cover_fids.append(fid)

    @property
    def lyrics(self: Tag):
        if len(self.__lyrics_fids) == 0: return ""
        return self.id3[self.__lyrics_fids[0]].text

    @lyrics.setter
    def lyrics(self: Tag, new_lyrics: str) -> None:
        if new_lyrics == "":
            self.__remove_by_fids(self.__lyrics_fids)
            self.__lyrics_fids = []
        fid = self.__frames["lyrics"][0]
        self.id3[fid] = USLT(
            encoding=3, # UTF-8
            lang='eng', # TODO: should this be detected?
            desc='',
            text=new_lyrics
        )
        self.__lyrics_fids.append(fid)

    @property
    def year(self: Tag) -> int:
        fid = self.__frames["recording_date"][0]
        if fid not in self.id3: return 0
        year = self.id3[fid][0].year
        return year if year else 0

    @year.setter
    def year(self: Tag, new_year: int) -> None:
        if new_year == self.year: return
        frame = self.__frames["recording_date"]
        if new_year == 0: return self.__remove_frame_by_fid(frame[0])
        self.id3[frame[0]] = frame[1](text=str(new_year))

    def __init_cover_or_lyrics(self: Tag, name: str) -> list[str]:
        res = [k for k in self.id3.keys() if k.startswith(self.__frames[name][0])]
        # TODO: add a general way of showing these messages
        if DEBUG:
            if len(res) > 1:
                print(f"Found more than one {name} for {self.id3.filename}")
        return res

    def __init_track_or_disc_num(self: Tag, name: str) -> tuple[int, int]:
        fid = self.__frames[name+"_num"][0]
        if fid not in self.id3: return (0, 0)
        frame_data = self.id3[fid][0]
        if frame_data == '':
            self.__remove_frame_by_fid(fid)
            return (0, 0)
        count = total = 0
        if "/" in frame_data:
            try:
                count, total = frame_data.split("/")
            except Exception as e:
                print(f"Could not get {name} number for {self.id3.filename}: {e}")
                return (0, 0)
            try:
                count = int(count)
                total = int(total)
            except ValueError:
                self.__remove_frame_by_fid(fid)
                return (0, 0)
        else:
            try:
                count = int(frame_data)
            except ValueError:
                self.__remove_frame_by_fid(fid)
                return (0, 0)
        return (count, total)

    def __init_year(self: Tag) -> int:
        recording_date_fid = self.__frames["recording_date"][0]
        if recording_date_fid in self.id3:
            timestamp = self.id3[recording_date_fid][0]
            year = timestamp.year
            if year: return year
            if timestamp.get_text() == "":
                self.__remove_frame_by_fid(recording_date_fid)
            return 0
        release_date_fid = self.__frames["recording_date"][0]
        if release_date_fid in self.id3:
            timestamp = self.id3[release_date_fid][0]
            year = timestamp.year
            if year:
                self.id3[recording_date_fid] = TDRL(text=timestamp.get_text())
            self.__remove_frame_by_fid(release_date_fid)
            return year
        return 0

class Song(QObject):
    #                           proerty_name, new_value
    propertyChanged = pyqtSignal(str, object)

    def __init__(self: Song, file_path: Path) -> None:
        super().__init__()

        if not file_path.is_file():
            raise FileNotFoundError()
        self.__file_path = file_path.absolute()
        self.__file_name: str = self.__file_path.name

        stat = self.__file_path.stat()
        self.__time: tuple[int, int] = (stat.st_atime_ns, stat.st_mtime_ns)

        self.__new_cover: bytes | None = None

        self.__remove_other_tags:      bool = True
        self.__preserve_file_time:     bool = True
        self.__crop_cover_to_square:   bool = False
        self.__original_file_has_tags: bool = True
        self.edited:                   bool = False

        try:
            id3 = ID3(self.__file_path)
        except ID3NoHeaderError:
            id3 = ID3()
            self.edited = True
        self.__tag: Tag = Tag(id3)

        if not id3: self.__original_file_has_tags = False

    def updated_file_path(self: Song) -> Path:
        return self.__file_path.parent / self.__file_name

    def update_crop_cover(self: Song) -> None:
        if self.__new_cover:
            cover = self.__new_cover
        elif self.cover:
            cover = self.cover
        else: return
        image_editor = ImageEditor(cover)
        if not image_editor.is_image():
            self.remove_covers()
            return
        self.__crop_cover_to_square = not image_editor.image_is_square()

    @property
    def crop_cover_to_square(self: Song) -> bool:
        return self.__crop_cover_to_square

    @crop_cover_to_square.setter
    def crop_cover_to_square(self: Song, value: bool) -> None:
        self.__crop_cover_to_square = value
        if not self.edited: self.edited = True

    @property
    def preserve_file_time(self: Song) -> bool:
        return self.__preserve_file_time

    @preserve_file_time.setter
    def preserve_file_time(self: Song, value: bool) -> None:
        self.__preserve_file_time = value
        if not self.edited: self.edited = True

    @property
    def remove_other_tags(self: Song) -> bool:
        return self.__remove_other_tags

    @remove_other_tags.setter
    def remove_other_tags(self: Song, value: bool) -> None:
        self.__remove_other_tags = value
        if not self.edited: self.edited = True

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
        if not self.edited: self.edited = True

    def __remove_all_tags(self: Song) -> None:
        if not self.__original_file_has_tags: return
        self.__tag = Tag(ID3())

    # TODO
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
        if not self.edited: return False
        if self.__remove_other_tags:
            tags = self._get_relevant_tags()
            self.__remove_all_tags()
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

        # doing this so that the new cover will be treated as the embedded one after saving
        self.__new_cover = None

        self.__tag.id3.save(self.__file_path)
        if self.__preserve_file_time:
            os.utime(self.__file_path, ns=self.__time)

        if self.__file_name != self.__file_path.name:
            return self.__rename()
        return True

    def __rename(self: Song) -> bool:
        if not self.__file_name.endswith(".mp3"):
            print(f"Error: {self.__file_name} is not a valid mp3 file name")
            return False
        new_path = self.updated_file_path()
        if new_path.exists():
            print(f"Error {self.__file_name}: path already exists") # TODO: BETTER ERROR
            return False
        try:
            self.__file_path =  self.__file_path.rename(new_path)
            if self.__preserve_file_time:
                os.utime(new_path, ns=self.__time)
        except Exception as e:
            print(f"Error {self.__file_name}: {e}")
            return False
        return True

    def remove_covers(self: Song) -> None:
        self.__tag.remove_covers()

    def get_title_and_artist_by_file_name(self: Song, file_name: str) -> tuple[str, str] | None:
        file_name = os.path.splitext(file_name)[0]
        # TODO: might want to add regex validation
        splitted_file_name = file_name.split(' - ')
        parts_n = len(splitted_file_name)
        if parts_n == 2: return (splitted_file_name[0], splitted_file_name[1])
        
    @property
    def cover(self: Song) -> bytes | None:
        return self.__tag.cover

    @cover.setter
    def cover(self: Song, image_data: bytes) -> None:
        self.__tag.cover = image_data
        if not self.edited: self.edited = True

    @property
    def file_path(self: Song) -> Path:
        return self.__file_path

    @property
    def file_name(self: Song) -> str:
        return self.__file_name

    @file_name.setter
    def file_name(self: Song, new_file_name: str) -> None:
        if new_file_name == self.__file_name: return
        if new_file_name == "": return

        self.__file_name = new_file_name
        self.propertyChanged.emit("file_name", new_file_name)
        if not self.edited: self.edited = True

    @property
    def title(self: Song) -> str:
        return self.__tag.title

    @title.setter
    def title(self: Song, new_title: str) -> None:
        self.__tag.title = new_title
        self.propertyChanged.emit("title", new_title)
        if not self.edited: self.edited = True

    @property
    def artist(self: Song) -> str:
        return self.__tag.artist

    @artist.setter
    def artist(self: Song, new_artist: str) -> None:
        self.__tag.artist = new_artist
        self.propertyChanged.emit("artist", new_artist)
        if not self.edited: self.edited = True

    @property
    def album(self: Song) -> str:
        return self.__tag.album

    @album.setter
    def album(self: Song, new_album: str) -> None:
        self.__tag.album = new_album
        self.propertyChanged.emit("album", new_album)
        if not self.edited: self.edited = True

    @property
    def album_artist(self: Song) -> str:
        return self.__tag.album_artist

    @album_artist.setter
    def album_artist(self: Song, new_album_artist: str) -> None:
        self.__tag.album_artist = new_album_artist
        self.propertyChanged.emit("album", new_album_artist)
        if not self.edited: self.edited = True

    @property
    def genre(self: Song) -> str:
        return self.__tag.genre

    @genre.setter
    def genre(self: Song, new_genre: str) -> None:
        self.__tag.genre = new_genre
        if not self.edited: self.edited = True

    @property
    def track_num(self: Song) -> tuple[int, int]:
        return self.__tag.track_num

    @track_num.setter
    def track_num(self: Song, new_track_num: tuple[int, int]) -> None:
        self.__tag.track_num = new_track_num
        self.propertyChanged.emit("track_num", new_track_num)
        if not self.edited: self.edited = True

    @property
    def disc_num(self: Song) -> tuple[int, int]:
        return self.__tag.disc_num

    @disc_num.setter
    def disc_num(self: Song, new_disc_num: tuple[int, int]) -> None:
        self.__tag.disc_num = new_disc_num
        self.propertyChanged.emit("disc_num", new_disc_num)
        if not self.edited: self.edited = True

    @property
    def lyrics(self: Song) -> str:
        return self.__tag.lyrics

    @lyrics.setter
    def lyrics(self: Song, new_lyrics: str) -> None:
        if new_lyrics == self.lyrics: return
        self.__tag.lyrics = new_lyrics
        if not self.edited: self.edited = True

    @property
    def year(self: Song) -> int:
        return self.__tag.year

    @year.setter
    def year(self: Song, new_year: int) -> None:
        self.__tag.year = new_year
        if not self.edited: self.edited = True
        self.propertyChanged.emit("year", new_year)

class SongsTableModel(QAbstractTableModel):
    #                         empty_table
    tableChanged = pyqtSignal(bool)

    def __init__(self: SongsTableModel) -> None:
        super().__init__()
        self.__songs: list[Song] = []
        self.__columns: list[str] = [
            "Track #",
            "Title",
            "Artist",
            "Album",
            "Year",
            "All Tags",
            "File Name",
        ]
        self.file_name_validator = FileNameValidator()

    @property
    def columns(self: SongsTableModel) -> list[str]:
        return self.__columns

    @property
    def songs(self: SongsTableModel) -> list[Song]:
        return self.__songs

    def remove_rows(self: SongsTableModel, rows: list[int]) -> None:
        for row in sorted(rows, reverse=True):
            self.beginRemoveRows(QModelIndex(), row, row)
            del self.__songs[row]
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
                track_num_count = song.track_num[0]
                return track_num_count if track_num_count != 0 else None
            case 'Title':
                return song.title
            case 'Artist':
                return song.artist
            case 'Album':
                return song.album
            case 'Year':
                year = song.year
                return year if year != 0 else None
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
                if value == "":
                    song.year = 0
                else:
                    if not value.isdigit(): return False
                    song.year = int(value)
            case 'File Name':
                if not self.file_name_validator.is_file_name_valid(value):
                    return False
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
        self: SongsTableModel,
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

class SetAllDialog(QDialog):
    Tags = Enum("Tags", ["TITLE", "ARTIST", "ALBUM", "ALBUM_ARTIST", "YEAR", "GENRE"])
    def __init__(self: SetAllDialog, year_validation_regex: str, parent: QWidget | None = None) -> None:
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
        self.ui.tags_combobox.currentTextChanged.connect(self.__combobox_changed)
        self.__year_validation_regex = year_validation_regex
        self.__validator_set = False

    def __combobox_changed(self: SetAllDialog, text: str) -> None:
        if text == "Year":
            self.ui.value_edit.setValidator(QRegularExpressionValidator(
                                        QRegularExpression(self.__year_validation_regex)))
            if not self.ui.value_edit.hasAcceptableInput():
                self.ui.value_edit.setText("")
            self.__validator_set = True
        elif self.__validator_set:
            self.ui.value_edit.setValidator(None)
            self.__validator_set = False

    def get_user_input(self: SetAllDialog) -> tuple[SetAllDialog.Tags, str]:
        return self.__tags[self.ui.tags_combobox.currentText()], self.ui.value_edit.text()

class TableWindow(QMainWindow):
    def __init__(self: TableWindow) -> None:
        super().__init__()
        self.ui = Ui_TableWindow()
        self.ui.setupUi(self)
        self.setWindowIcon(QIcon(str(SVG_LOGO_FILE_PATH)))
        self.ui.centralwidget.destroy()
        self.__songs_added = False

        self.setAcceptDrops(True)

        self.ui.action_new.triggered.connect(self.new_album_dialog)
        self.ui.action_save_all.triggered.connect(self.save_all)
        self.ui.action_autofill_ta.triggered.connect(self.autofill_titles_and_artists)
        self.ui.action_save_all.setEnabled(False)
        self.ui.action_autofill_ta.setEnabled(False)
        self.ui.action_set_all.setEnabled(False)
        self.ui.action_open.triggered.connect(self.open)
        self.ui.action_set_all.triggered.connect(self.set_all)

        self.action_paste = QAction("Paste", self)
        self.action_paste.setPriority(QAction.Priority.LowPriority)
        self.action_paste.setShortcut(QKeySequence.StandardKey.Paste)
        self.action_paste.triggered.connect(self.paste)
        self.ui.menu_file.insertAction(self.ui.action_save_all, self.action_paste)
        self.ui.menu_file.insertSeparator(self.ui.action_save_all)

        self.setup_table()
        if DEBUG:
            self.ui.menu_file.addSeparator()
            self.action_debug = QAction("Debug", self)
            self.ui.menu_file.addAction(self.action_debug)
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
        all_paths = [Path(url.toLocalFile()) for url in mime_data.urls()]

        self.__accepted_drop_paths: list[Path] = []
        for path in all_paths:
            if not path.suffix.lower == ".mp3" or not path.is_file():
                continue
            self.__accepted_drop_paths.append(Path(path))

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
        if mime_data.hasUrls():
            all_paths = [Path(url.toLocalFile()) for url in mime_data.urls()]
            mp3_paths = [path for path in all_paths
                         if path.suffix.lower() == ".mp3" and path.is_file()]
        else:
            cb_contents = cb.text()
            if cb_contents == "": return
            raw_paths = cb_contents.strip().split(os.linesep)
            mp3_paths = [path for path in raw_paths
                    if os.path.isfile(path) and path.lower().endswith(".mp3")]
        songs = []
        for path in mp3_paths:
            song = Song(Path(path))
            song.update_crop_cover()
            songs.append(song)
        if songs: self.add_songs(songs)

    def set_all(self: TableWindow) -> None:
        self.dlg = SetAllDialog(self.year_line_edit_delegate.validation_regex, self)
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
                val = user_inp[1]
                if val == "": val = 0
                for i in range(len(self.model.songs)):
                    self.model.songs[i].year = int(val)
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
        for i, idx in enumerate(selected_indexes):
            if idx.model() is self.proxy:
                selected_indexes[i] = self.proxy.mapToSource(selected_indexes[i])
        self.model.remove_rows([index.row() for index in selected_indexes])

    def remove_rows(self: TableWindow, indexes: list[QModelIndex]) -> None:
        assert indexes
        for i, idx in enumerate(indexes):
            if idx.model() is self.proxy:
                indexes[i] = self.proxy.mapToSource(idx)
        self.model.remove_rows([index.row() for index in indexes])

    def setup_table(self: TableWindow) -> None:
        self.model = SongsTableModel()

        self.proxy = QSortFilterProxyModel()
        self.proxy.setSourceModel(self.model)

        self.view = TableViewWithContextMenu()
        self.view.removeRows.connect(lambda row: self.remove_rows(row))

        self.view.setModel(self.proxy)
        self.view.setSortingEnabled(True)
        self.setCentralWidget(self.view)

        header: QHeaderView = self.view.horizontalHeader() # type: ignore
        header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        for col in (self.model.columns.index("Track #"),
                    self.model.columns.index("Year"),
                    self.model.columns.index("All Tags")):
            header.setSectionResizeMode(col,
                                        QHeaderView.ResizeMode.ResizeToContents)

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
            self.ui.action_save_all.setEnabled(False)
            self.ui.action_autofill_ta.setEnabled(False)
            self.ui.action_set_all.setEnabled(False)

    def open(self: TableWindow) -> None:
        paths = QFileDialog.getOpenFileNames(
            self, "Select Songs", ".", "Mp3 Files (*.mp3)")[0]
        if not paths: return # TODO: might want to tell the user what happened
        songs = []
        for path in paths:
            song = Song(Path(path))
            song.update_crop_cover()
            songs.append(song)
        self.add_songs(songs)

    def save_all(self: TableWindow) -> None:
        failed = []
        nothing_to_save = True
        for i in range(len(self.model.songs)):
            if not self.model.songs[i].edited: continue
            nothing_to_save = False
            this_new_path = self.model.songs[i].updated_file_path()
            self.ui.status_bar.showMessage(f"Saving \"{this_new_path}\"")
            if not self.model.songs[i].save(): failed.append(this_new_path)
        time = 5000
        if nothing_to_save:
            return self.ui.status_bar.showMessage("Nothing to save", time)
        message = "Finished Saving"
        if failed:
            message += " (could not save: \""+", ".join(failed)+"\")"
            time *= 2
        self.ui.status_bar.showMessage(message, time)

    def closeEvent(self: TableWindow, a0: QCloseEvent | None) -> None:
        if not a0: return
        a0.accept()
        QApplication.quit()

    def autofill_titles_and_artists(self: TableWindow) -> None:
        for i in range(len(self.model.songs)):
            res = self.model.songs[i].get_title_and_artist_by_file_name(
                self.model.songs[i].file_name
            )
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
            self.ui.action_new.setEnabled(True)

    def all_tags_button_clicked(self: TableWindow, index: QModelIndex) -> None:
        if index.model() is self.proxy: index = self.proxy.mapToSource(index)
        self.dialog = EditTagsDialog(
                        self.model.songs, index.row(),
                        self.year_line_edit_delegate.validation_regex, self)
        self.dialog.exec()

    def add_songs(self: TableWindow, songs: list[Song]) -> None:
        # checking if they've already been added
        already_added_paths = [x.file_path for x in self.model.songs]
        songs = [x for x in songs if x.file_path not in already_added_paths]
        self.model.add_songs(songs)

        self.ui.action_save_all.setEnabled(True)
        self.ui.action_autofill_ta.setEnabled(True)
        self.ui.action_set_all.setEnabled(True)
        self.__songs_added = True

class TableViewWithContextMenu(QTableView):
    removeRows = pyqtSignal(object)
    def contextMenuEvent(self: TableViewWithContextMenu, a0: QContextMenuEvent | None) -> None:
        if not a0: return
        parent = self.parent()
        assert parent and isinstance(parent, TableWindow)

        context_menu = QMenu(self)
        context_menu.setFixedWidth(200)

        # mouse is not on any rows
        if self.rowAt(a0.pos().y()) == -1:
            context_menu.addAction(parent.action_paste)
        else:
            selected_indexes = self.selectedIndexes()
            action_remove = QAction(context_menu)
            action_remove.setShortcut(QKeySequence.StandardKey.Delete)

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
        try:
            self.__image = Image.open(BytesIO(data))
        except UnidentifiedImageError:
            self.__image = None
        if not self.__image: return
        if self.__image.format not in ("JPEG", "PNG"):
            raise ValueError(f"Expected JPEG/PNG format, got {self.__image.format}")

    def is_image(self: ImageEditor) -> bool:
        return self.__image is not None

    def image_is_square(self: ImageEditor) -> bool:
        assert(bool(self.__image))
        return self.__image.width == self.__image.height

    @property
    def data(self: ImageEditor) -> bytes:
        return self.__data

    def crop_to_center_square(self: ImageEditor) -> bytes:
        assert(self.__image)
        width, height = self.__image.size
        x = (width-height)/2
        self.__image = self.__image.crop((x, 0, x+height, height))
        output_bytes = BytesIO()
        self.__image.save(output_bytes, format="JPEG", quality=95)
        return output_bytes.getvalue()

class FileNameValidator:
    def __is_file_name_valid_posix(self: FileNameValidator, file_name: str) -> bool:
        return bool(file_name) and "/" not in file_name and "\x00" not in file_name

    def __is_file_name_valid_windows(self: FileNameValidator, file_name: str) -> bool:
        illegal_chars = r'[<>:"/\\|?*\x00-\x1f]'
        reserved_names = {
            "CON", "PRN", "AUX", "NUL",
            *(f"COM{i}" for i in range(1, 10)),
            *(f"LPT{i}" for i in range(1, 10)),
        }
        if not file_name or file_name != file_name.strip(" ."):
            return False  # can't be empty, or start/end with space or dot (Windows)
        if re.search(illegal_chars, file_name):
            return False
        if file_name.upper().split(".")[0] in reserved_names:
            return False
        if len(file_name) > 255:
            return False
        return True

    def is_file_name_valid(self: FileNameValidator, file_name: str) -> bool:
        func = self.__is_file_name_valid_posix
        if PLATFORM == "win32":
            func = self.__is_file_name_valid_windows
        return func(file_name)

class FileNameLineEditFilter(QObject):
    def __init__(self: FileNameLineEditFilter, initial_text: str,
                                         parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.__initial_text = initial_text
        self.file_name_validator = FileNameValidator()

    def eventFilter(self: FileNameLineEditFilter, a0: QObject | None,
                                                     a1: QEvent | None) -> bool:
        res = super().eventFilter(a0, a1)
        obj: QLineEdit = a0 # type: ignore
        event: QEvent = a1 # type: ignore
        if event.type() not in (
                QEvent.Type.FocusOut, QEvent.Type.Close, QEvent.Type.KeyPress):
            return res

        text = obj.text()
        if not self.file_name_validator.is_file_name_valid(text):
            obj.setText(self.__initial_text)
        return res

class EditTagsDialog(QDialog):
    CoverImageStates = Enum("CoverImageStates", ["SELECTED", "EMBEDDED", "NONE"])

    def __init__(self: EditTagsDialog, songs: list[Song], index: int, year_validation_regex: str, parent: QWidget | None = None) -> None:
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
        self.ui.copy_from_another_file_button.setMenu(self.copy_from_another_file_menu)


        self.copy_from_another_file_menu.addAction(
                QIcon(), "Copy from an already opened file", lambda: self.open_copy_tags_dialog(True),
                Qt.ConnectionType.AutoConnection)
        self.copy_from_another_file_menu.addAction(
                QIcon(), "Browse for file", lambda: self.open_copy_tags_dialog(False),
                Qt.ConnectionType.AutoConnection)

        self.ui.preserve_file_time_checkbox.setChecked(self.song.preserve_file_time)
        self.ui.remove_other_tags_checkbox.setChecked(self.song.remove_other_tags)
        self.ui.crop_cover_checkbox.setChecked(self.song.crop_cover_to_square)

        self.ui.music_list.hide()

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
            if selected_path: selected_song = Song(Path(selected_path))
        if not selected_song: return

        self.copy_tags_from_song(selected_song)

    def copy_tags_from_song(self: EditTagsDialog, selected_song: Song) -> None:
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
        if year == "0": year = ""
        self.ui.year_edit.setText(year)

    def copy_cover(self: EditTagsDialog) -> None:
        selected_path = self.open_file_dialog("*.mp3")
        if not selected_path: return
        selected_song = Song(Path(selected_path))
        if not selected_song.cover: return
        self.new_cover = selected_song.cover
        self.update_cover_display()

    def update_cover_display(self: EditTagsDialog) -> None:
        self.ui.cover_label.clear()
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

    def confirm(self: EditTagsDialog) -> None:
        self.song.title = self.ui.title_edit.text()
        self.song.artist = self.ui.artist_edit.text()
        self.song.album = self.ui.album_edit.text()
        self.song.album_artist = self.ui.album_artist_edit.text()
        self.song.genre = self.ui.genre_edit.text()
        self.song.file_name = self.ui.file_name_edit.text()
        self.song.lyrics = self.ui.lyrics_edit.toPlainText()

        year_edit = self.ui.year_edit.text()
        self.song.year = int(year_edit) if year_edit != "" else 0

        self.song.track_num = (self.ui.track_count_spinbox.value(), self.ui.track_total_spinbox.value())
        self.song.disc_num = (self.ui.disc_count_spinbox.value(), self.ui.disc_total_spinbox.value())

        self.song.new_cover = self.new_cover
        if not self.cover and self.song.cover: self.song.remove_covers()

        self.song.remove_other_tags = self.ui.remove_other_tags_checkbox.isChecked()
        self.song.preserve_file_time = self.ui.preserve_file_time_checkbox.isChecked()
        self.song.crop_cover_to_square = self.ui.crop_cover_checkbox.isChecked()

        self.close()

    def autofill_title_and_artist(self: EditTagsDialog):
        res = self.song.get_title_and_artist_by_file_name(self.ui.file_name_edit.text()) # Better error
        if not res: return
        self.ui.artist_edit.setText(res[0])
        self.ui.title_edit.setText(res[1])

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
            if not self.ui.cover_label.pixmap(): return
            self.ui.cover_label.clear()
            return
        pixmap = QPixmap()
        if which == self.CoverImageStates.SELECTED:
            pixmap.loadFromData(self.new_cover) # type: ignore
        elif which == self.CoverImageStates.EMBEDDED:
            pixmap.loadFromData(self.cover) # type: ignore

        scaled_pixmap = pixmap.scaledToWidth(
                self.ui.cover_label.width(), Qt.TransformationMode.SmoothTransformation)
        self.ui.cover_label.setPixmap(scaled_pixmap)
        # self.cover_label.adjustSize()

    def fill_in_fields_from_song(self: EditTagsDialog):
        self.ui.title_edit.setText(self.song.title)
        self.ui.artist_edit.setText(self.song.artist)
        self.ui.album_edit.setText(self.song.album)
        self.ui.album_artist_edit.setText(self.song.album_artist)
        self.ui.genre_edit.setText(self.song.genre)
        self.ui.track_count_spinbox.setValue(self.song.track_num[0])
        self.ui.disc_count_spinbox.setValue(self.song.disc_num[0])
        year = self.song.year
        if year: self.ui.year_edit.setText(str(year))
        self.ui.file_name_edit.setText(self.song.file_name)
        self.ui.lyrics_edit.setPlainText(self.song.lyrics)

def main() -> int:
    if not DEBUG:
        def custom_message_handler(_, __, ___): return
        qInstallMessageHandler(custom_message_handler)
    app = QApplication(sys.argv)
    table_window = TableWindow()
    table_window.show()

    return app.exec()
