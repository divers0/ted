import os
from pathlib import Path
from typing import Any

from PyQt6.QtCore import (QAbstractTableModel, QModelIndex, QSize,
                          QSortFilterProxyModel, Qt, pyqtSignal)
from PyQt6.QtGui import (QAction, QCloseEvent, QContextMenuEvent,
                         QDragEnterEvent, QDropEvent, QIcon, QKeyEvent,
                         QKeySequence)
from PyQt6.QtWidgets import (QApplication, QDialog, QFileDialog, QHeaderView,
                             QLabel, QLineEdit, QMainWindow, QMenu,
                             QSizePolicy, QStyleFactory, QTableView,
                             QVBoxLayout, QWidget)

from .config import DEBUG_ENV_VAR_NAME, SVG_LOGO_FILE_PATH
from .delegates import (EditTagsButtonDelegate, TrackSpinBoxDelegate,
                        YearLineEditDelegate)
from .dialogs import AlbumCreationDialog, EditTagsDialog, SetAllDialog
from .filename import FileNameValidator
from .song import Song
from .ui.TableWindow import Ui_TableWindow


class TableWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.ui = Ui_TableWindow()
        self.ui.setupUi(self)
        self.setWindowIcon(QIcon(str(SVG_LOGO_FILE_PATH)))
        self.__songs_added = False

        self.setAcceptDrops(True)

        self.ui.action_new.triggered.connect(self.new_album_dialog)
        self.ui.action_save_all.triggered.connect(self.save_all)
        self.ui.action_autofill_ta.triggered.connect(
            self.autofill_titles_and_artists)
        self.ui.action_save_all.setEnabled(False)
        self.ui.action_autofill_ta.setEnabled(False)
        self.ui.action_set_all.setEnabled(False)
        self.ui.action_open.triggered.connect(self.open)
        self.ui.action_set_all.triggered.connect(self.set_all)

        self.action_paste = QAction("&Paste", self)
        self.action_paste.setPriority(QAction.Priority.LowPriority)
        self.action_paste.setShortcut(QKeySequence.StandardKey.Paste)
        self.action_paste.triggered.connect(self.paste)
        self.ui.menu_file.insertAction(
            self.ui.action_save_all, self.action_paste)
        self.ui.menu_file.insertSeparator(self.ui.action_save_all)

        self.search_bar = QLineEdit(self)
        self.search_bar.setPlaceholderText("Search...")
        self.search_bar.setSizePolicy(QSizePolicy(QSizePolicy.Policy.Fixed,
                                                  QSizePolicy.Policy.Preferred))
        set_focus_to_search_bar = QAction(self)
        set_focus_to_search_bar.setShortcut(QKeySequence("Ctrl+F"))
        set_focus_to_search_bar.triggered.connect(self.search_bar.setFocus)
        self.addAction(set_focus_to_search_bar)
        self.central_widget_layout = QVBoxLayout()
        self.search_bar.setMinimumSize(QSize(300, 0))
        self.central_widget_layout.addWidget(self.search_bar, 0,
                                             Qt.AlignmentFlag.AlignRight)
        central_widget = self.centralWidget()
        assert central_widget
        central_widget.setLayout(self.central_widget_layout)

        self.table_status_label = TableStatusLabel()
        self.ui.status_bar.addPermanentWidget(self.table_status_label)

        self.setup_table()
        self.view.setFocus()

        debug = os.getenv(DEBUG_ENV_VAR_NAME)
        assert debug is not None
        if int(debug):
            self.ui.menu_file.addSeparator()
            self.action_debug = QAction("Debug", self)
            self.ui.menu_file.addAction(self.action_debug)
            self.action_debug.triggered.connect(self.debug)
            self.action_debug.setShortcut(QKeySequence("Ctrl+D"))
            self.style_counter = 0

    def debug(self) -> None:
        # print(" ---- debug ----")
        # print(" ---- end debug ----")
        all_styles = QStyleFactory.keys()
        print("All styles:", all_styles)
        style = QApplication.style()
        if not style:
            return
        print("Current Style:", style.objectName())
        if self.style_counter == len(all_styles)-1:
            self.style_counter = 0
        else:
            self.style_counter += 1
        QApplication.setStyle(all_styles[self.style_counter])
        print("New Style:", all_styles[self.style_counter])

    def dragEnterEvent(self, a0: QDragEnterEvent | None) -> None:
        if not a0:
            return
        mime_data = a0.mimeData()
        if not mime_data:
            return
        if not mime_data.hasUrls():
            return
        all_paths = [Path(url.toLocalFile()) for url in mime_data.urls()]

        self.__accepted_drop_paths: list[Path] = []
        for path in all_paths:
            if not path.suffix.lower() == ".mp3" or not path.is_file():
                continue
            self.__accepted_drop_paths.append(Path(path))

        if self.__accepted_drop_paths:
            a0.acceptProposedAction()
        else:
            a0.ignore()

    def dropEvent(self, a0: QDropEvent | None) -> None:
        if not a0:
            return
        songs = []
        for path in self.__accepted_drop_paths:
            song = Song(path)
            song.update_crop_cover()
            songs.append(song)
        if songs:
            self.add_songs(songs)

    def paste(self) -> None:
        cb = QApplication.clipboard()
        if not cb:
            return
        mime_data = cb.mimeData()
        if not mime_data:
            return
        if mime_data.hasUrls():
            all_paths = [Path(url.toLocalFile()) for url in mime_data.urls()]
            mp3_paths = [path for path in all_paths
                         if path.suffix.lower() == ".mp3" and path.is_file()]
        else:
            cb_contents = cb.text()
            if cb_contents == "":
                return
            raw_paths = cb_contents.strip().split(os.linesep)
            mp3_paths = [path for path in raw_paths
                         if os.path.isfile(path) and path.lower().endswith(".mp3")]
        songs = []
        for path in mp3_paths:
            song = Song(Path(path))
            song.update_crop_cover()
            songs.append(song)
        if songs:
            self.add_songs(songs)

    def set_all(self) -> None:
        self.dlg = SetAllDialog(
            self.year_line_edit_delegate.validation_regex, self)
        if self.dlg.exec() != QDialog.DialogCode.Accepted:
            return
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
                if val == "":
                    val = 0
                for i in range(len(self.model.songs)):
                    self.model.songs[i].year = int(val)
            case self.dlg.Tags.GENRE:
                for i in range(len(self.model.songs)):
                    self.model.songs[i].genre = user_inp[1]

    def keyPressEvent(self, a0: QKeyEvent | None) -> None:
        if not a0:
            return
        key = a0.key()
        if key not in (Qt.Key.Key_Delete, Qt.Key.Key_Return, Qt.Key.Key_Enter):
            return super().keyPressEvent(a0)
        selected_indexes = self.view.selectedIndexes()
        if not selected_indexes:
            return

        if key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            if len(selected_indexes) != 1:
                return
            index = selected_indexes[0]
            if index.column() == self.model.columns.index("All Tags"):
                return self.all_tags_button_clicked(index)
            return self.view.edit(index)
        # key has to be Key_Delete
        for i, idx in enumerate(selected_indexes):
            if idx.model() is self.proxy:
                selected_indexes[i] = self.proxy.mapToSource(
                    selected_indexes[i])
        self.model.remove_rows([index.row() for index in selected_indexes])

    def remove_songs(self, indexes: list[QModelIndex]) -> None:
        assert indexes
        for i, idx in enumerate(indexes):
            if idx.model() is self.proxy:
                indexes[i] = self.proxy.mapToSource(idx)
        self.model.remove_rows([index.row() for index in indexes])
        self.table_status_label.update_text(len(self.model.songs))

    def setup_table(self) -> None:
        self.model = SongsTableModel()

        self.proxy = QSortFilterProxyModel()
        self.proxy.setSourceModel(self.model)

        self.view = TableViewWithContextMenu()
        self.view.removeRows.connect(lambda row: self.remove_songs(row))

        self.view.setModel(self.proxy)
        self.view.setSortingEnabled(True)

        selection_model = self.view.selectionModel()
        assert selection_model
        selection_model.selectionChanged.connect(
            lambda: self.table_status_label.update_text(
                len(self.model.songs),
                len(set(map(lambda x: x.row(), self.view.selectedIndexes())))
            )
        )

        # Search bar
        self.proxy.setFilterKeyColumn(-1)
        self.proxy.setFilterCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.search_bar.textChanged.connect(self.proxy.setFilterFixedString)

        self.central_widget_layout.addWidget(self.view)

        header: QHeaderView = self.view.horizontalHeader()  # type: ignore
        header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        for col in (self.model.columns.index("Track #"),
                    self.model.columns.index("Year"),
                    self.model.columns.index("All Tags")):
            header.setSectionResizeMode(col,
                                        QHeaderView.ResizeMode.ResizeToContents)

        self.year_line_edit_delegate = YearLineEditDelegate()
        self.view.setItemDelegateForColumn(
            self.model.columns.index("Year"), self.year_line_edit_delegate)

        self.edit_tags_button_delegate = EditTagsButtonDelegate()
        self.edit_tags_button_delegate.clicked.connect(
            self.all_tags_button_clicked)
        self.view.setItemDelegateForColumn(self.model.columns.index(
            "All Tags"), self.edit_tags_button_delegate)

        self.track_item_delegate = TrackSpinBoxDelegate()
        self.view.setItemDelegateForColumn(
            self.model.columns.index("Track #"), self.track_item_delegate)

        vertical_header = self.view.verticalHeader()
        if vertical_header is not None:
            vertical_header.hide()

        self.model.tableChanged.connect(self.update_table)

    def update_table(self) -> None:
        self.ui.action_save_all.setEnabled(False)
        self.ui.action_autofill_ta.setEnabled(False)
        self.ui.action_set_all.setEnabled(False)

    def open(self) -> None:
        paths = QFileDialog.getOpenFileNames(
            self, "Select Songs", ".", "Mp3 Files (*.mp3)")[0]
        if not paths:
            return  # TODO: might want to tell the user what happened
        songs = []
        for path in paths:
            song = Song(Path(path))
            song.update_crop_cover()
            songs.append(song)
        self.add_songs(songs)

    def save_all(self) -> None:
        failed = []
        nothing_to_save = True
        for i in range(len(self.model.songs)):
            if not self.model.songs[i].edited:
                continue
            nothing_to_save = False
            this_new_path = self.model.songs[i].updated_file_path()
            self.ui.status_bar.showMessage(f"Saving \"{this_new_path}\"")
            if not self.model.songs[i].save():
                failed.append(this_new_path)
        time = 5000
        if nothing_to_save:
            return self.ui.status_bar.showMessage("Nothing to save", time)
        message = "Finished Saving"
        if failed:
            message += " (could not save: \""+", ".join(failed)+"\")"
            time *= 2
        self.ui.status_bar.showMessage(message, time)

    def closeEvent(self, a0: QCloseEvent | None) -> None:
        if not a0:
            return
        a0.accept()
        QApplication.quit()

    def autofill_titles_and_artists(self) -> None:
        for i in range(len(self.model.songs)):
            res = self.model.songs[i].get_title_and_artist_by_file_name(
                self.model.songs[i].file_name
            )
            if not res:
                return  # TODO: Better error
            self.model.songs[i].artist = res[0]
            self.model.songs[i].title = res[1]

    def new_album_dialog(self) -> None:
        songs = []
        if self.__songs_added:
            songs = self.model.songs
        self.album_creation_dialog = AlbumCreationDialog(songs, self)
        res = self.album_creation_dialog.exec()
        if res == QDialog.DialogCode.Accepted:
            self.add_songs(self.album_creation_dialog.get_new_songs())
        else:
            self.ui.action_new.setEnabled(True)

    def all_tags_button_clicked(self, index: QModelIndex) -> None:
        if index.model() is self.proxy:
            index = self.proxy.mapToSource(index)
        self.dialog = EditTagsDialog(
            self.model.songs, index.row(),
            self.year_line_edit_delegate.validation_regex, self)
        self.dialog.exec()

    def add_songs(self, songs: list[Song]) -> None:
        assert len(songs) > 0
        already_added_paths = [x.file_path for x in self.model.songs]
        new_songs = [
            x for x in songs if x.file_path not in already_added_paths]
        self.model.add_songs(new_songs)
        self.table_status_label.update_text(len(self.model.songs))

        self.ui.action_save_all.setEnabled(True)
        self.ui.action_autofill_ta.setEnabled(True)
        self.ui.action_set_all.setEnabled(True)
        self.__songs_added = True


class TableViewWithContextMenu(QTableView):
    removeRows = pyqtSignal(object)

    def contextMenuEvent(self, a0: QContextMenuEvent | None) -> None:
        if not a0:
            return
        parent = self.parent()
        assert parent
        table_window = parent.parent()
        assert isinstance(table_window, TableWindow)

        context_menu = QMenu(self)
        context_menu.setFixedWidth(200)

        # mouse is not on any rows
        if self.rowAt(a0.pos().y()) == -1:
            context_menu.addAction(table_window.action_paste)
        else:
            selected_indexes = self.selectedIndexes()
            action_remove = QAction(context_menu)
            action_remove.setShortcut(QKeySequence.StandardKey.Delete)

            text = "Remove this row"
            if len(selected_indexes) > 1:
                text = "Remove selected rows"
            action_remove.triggered.connect(
                lambda: self.removeRows.emit(selected_indexes))
            action_remove.setText(text)

            context_menu.addAction(action_remove)
        context_menu.exec(a0.globalPos())


class SongsTableModel(QAbstractTableModel):
    tableChanged = pyqtSignal()

    def __init__(self) -> None:
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

    @property
    def columns(self) -> list[str]:
        return self.__columns

    @property
    def songs(self) -> list[Song]:
        return self.__songs

    def remove_rows(self, rows: list[int]) -> None:
        for row in sorted(rows, reverse=True):
            self.beginRemoveRows(QModelIndex(), row, row)
            del self.__songs[row]
            self.endRemoveRows()
        if not self.__songs:
            self.tableChanged.emit()

    def add_songs(self, songs: list[Song]) -> None:
        songs_n = len(self.__songs)
        self.beginInsertRows(QModelIndex(), songs_n, songs_n+len(songs)-1)
        for row, song in enumerate(songs):
            song.propertyChanged.connect(
                lambda name, _, row=row: self._on_song_prop_change(name, row))
            self.__songs.append(song)
        self.endInsertRows()

    def _on_song_prop_change(self, name: str, row: int) -> None:
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
        if col is None:
            return

        # they're the same because we're only trying to specify one cell
        top_left = bottom_right = self.index(row, col)
        self.dataChanged.emit(top_left, bottom_right, [
                              Qt.ItemDataRole.DisplayRole])

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        if not index.isValid():
            return
        song = self.__songs[index.row()]
        col = self.__columns[index.column()]
        if role not in (Qt.ItemDataRole.DisplayRole, Qt.ItemDataRole.EditRole):
            return
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
            self,
            index: QModelIndex,
            value: str,
            role: int = Qt.ItemDataRole.EditRole) -> bool:
        if not index.isValid() or role != Qt.ItemDataRole.EditRole:
            return False
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
                    if not value.isdigit():
                        return False
                    song.year = int(value)
            case 'File Name':
                if not FileNameValidator(value).is_valid():
                    return False
                song.file_name = value
            case _:
                return False
        return True

    def flags(self: SongsTableModel, index: QModelIndex) -> Qt.ItemFlag:
        if not index.isValid():
            return Qt.ItemFlag.NoItemFlags
        flags = Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable
        if index.column() == self.__columns.index("All Tags"):
            return flags
        return flags | Qt.ItemFlag.ItemIsEditable

    def headerData(
            self,
            section: int,
            orientation: Qt.Orientation,
            role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        if role != Qt.ItemDataRole.DisplayRole:
            return
        if orientation != Qt.Orientation.Horizontal:
            return
        return self.__columns[section]

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return len(self.__songs)

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return len(self.__columns)


class TableStatusLabel(QLabel):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.__songs_len = 0
        self.__selected_len = 0

    def update_text(self, songs_len: int, selected_len: int | None = None) -> None:
        if songs_len == self.__songs_len and selected_len == self.__selected_len:
            return
        self.__songs_len = songs_len
        self.__selected_len = selected_len

        status_bar_right_text = f"{songs_len} Song"
        if songs_len > 1:
            status_bar_right_text += "s"
        # if it's None or equals zero
        if not selected_len:
            return self.setText(status_bar_right_text)

        self.setText(status_bar_right_text + f" ({selected_len} selected)")
