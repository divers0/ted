import os
from pathlib import Path
from typing import Any

from mutagen.id3 import ID3
from mutagen.id3._frames import (APIC, TALB, TCON, TDRC, TDRL, TIT2, TPE1,
                                 TPE2, TPOS, TRCK, USLT, Frame)
from mutagen.id3._specs import PictureType
from mutagen.id3._util import ID3NoHeaderError
from PyQt6.QtCore import QObject, pyqtSignal

from TEd.config import DEBUG_ENV_VAR_NAME

from .image import ImageEditor


class Tag:
    def __init__(self, id3: ID3) -> None:
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
        self.year = self.__init_year()
        self.track_num = self.__init_track_or_disc_num("track")
        self.disc_num = self.__init_track_or_disc_num("disc")
        self.__cover_fids = self.__init_cover_or_lyrics("cover")
        self.__lyrics_fids = self.__init_cover_or_lyrics("lyrics")

    def remove_covers(self) -> None:
        self.__remove_by_fids(self.__cover_fids)
        self.__cover_fids = []

    def __remove_by_fids(self, fids: list[str]) -> None:
        for fid in fids:
            del self.id3[fid]

    def __remove_frame_by_fid(self, fid: str) -> None:
        del self.id3[fid]

    def __simple_string_tag_getter(self, fid: str) -> str:
        if fid not in self.id3:
            return ""
        return self.id3[fid][0]

    def __simple_string_tag_setter(self, name: str, new_value: str) -> None:
        old_value = getattr(self, name)
        if new_value == old_value:
            return

        fid = self.__frames[name][0]
        if new_value == "":
            self.__remove_frame_by_fid(fid)
            return

        self.id3[fid] = self.__frames[name][1](text=new_value)

    @property
    def title(self) -> str:
        return self.__simple_string_tag_getter(self.__frames["title"][0])

    @title.setter
    def title(self, new_title: str) -> None:
        self.__simple_string_tag_setter("title", new_title)

    @property
    def artist(self) -> str:
        return self.__simple_string_tag_getter(self.__frames["artist"][0])

    @artist.setter
    def artist(self, new_artist: str) -> None:
        self.__simple_string_tag_setter("artist", new_artist)

    @property
    def album(self) -> str:
        return self.__simple_string_tag_getter(self.__frames["album"][0])

    @album.setter
    def album(self, new_album: str) -> None:
        self.__simple_string_tag_setter("album", new_album)

    @property
    def album_artist(self) -> str:
        return self.__simple_string_tag_getter(self.__frames["album_artist"][0])

    @album_artist.setter
    def album_artist(self, new_album_artist: str) -> None:
        self.__simple_string_tag_setter("album_artist", new_album_artist)

    @property
    def genre(self) -> str:
        return self.__simple_string_tag_getter(self.__frames["genre"][0])

    @genre.setter
    def genre(self, new_genre: str) -> None:
        self.__simple_string_tag_setter("genre", new_genre)

    @property
    def track_num(self) -> tuple[int, int]:
        text = self.__simple_string_tag_getter(self.__frames["track_num"][0])
        if text == "":
            return (0, 0)
        if "/" in text:
            count, total = text.split("/")
            return (int(count), int(total))
        return (int(text), 0)

    @track_num.setter
    def track_num(self, new_track_num: tuple[int, int]) -> None:
        if new_track_num == self.track_num:
            return
        fid = self.__frames["track_num"][0]
        if new_track_num == (0, 0):
            return self.__remove_frame_by_fid(fid)
        res = str(new_track_num[0])
        if new_track_num[1] != 0:
            res = str(new_track_num[0])+"/"+str(new_track_num[1])
        self.id3[fid] = TRCK(text=res)

    @property
    def disc_num(self) -> tuple[int, int]:
        text = self.__simple_string_tag_getter(self.__frames["disc_num"][0])
        if text == "":
            return (0, 0)
        if "/" in text:
            count, total = text.split("/")
            return (int(count), int(total))
        return (int(text), 0)

    @disc_num.setter
    def disc_num(self, new_disc_num: tuple[int, int]) -> None:
        if new_disc_num == self.disc_num:
            return
        fid = self.__frames["disc_num"][0]
        if new_disc_num == (0, 0):
            return self.__remove_frame_by_fid(fid)
        res = str(new_disc_num[0])
        if new_disc_num[1] != 0:
            res = str(new_disc_num[0])+"/"+str(new_disc_num[1])
        self.id3[fid] = TPOS(text=res)

    @property
    def cover(self) -> bytes | None:
        if len(self.__cover_fids) == 0:
            return
        return self.id3[self.__cover_fids[0]].data

    @cover.setter
    def cover(self, image_data: bytes) -> None:
        fid = self.__frames["cover"][0]
        self.id3[fid] = APIC(
            encoding=3,  # UTF-8
            mime="image/jpeg",  # TODO: not handling png files
            type=PictureType.COVER_FRONT,
            desc="",
            data=image_data
        )
        self.__cover_fids.append(fid)

    @property
    def lyrics(self) -> str:
        if len(self.__lyrics_fids) == 0:
            return ""
        return self.id3[self.__lyrics_fids[0]].text

    @lyrics.setter
    def lyrics(self, new_lyrics: str) -> None:
        if new_lyrics == "":
            self.__remove_by_fids(self.__lyrics_fids)
            self.__lyrics_fids = []
        fid = self.__frames["lyrics"][0]
        self.id3[fid] = USLT(
            encoding=3,  # UTF-8
            lang='eng',  # TODO: should this be detected?
            desc='',
            text=new_lyrics
        )
        self.__lyrics_fids.append(fid)

    @property
    def year(self) -> int:
        fid = self.__frames["recording_date"][0]
        if fid not in self.id3:
            return 0
        year = self.id3[fid][0].year
        return year if year else 0

    @year.setter
    def year(self, new_year: int) -> None:
        if new_year == self.year:
            return
        frame = self.__frames["recording_date"]
        if new_year == 0:
            return self.__remove_frame_by_fid(frame[0])
        self.id3[frame[0]] = frame[1](text=str(new_year))

    def __init_cover_or_lyrics(self, name: str) -> list[str]:
        res = [k for k in self.id3.keys() if k.startswith(self.__frames[name][0])]
        # TODO: add a general way of showing these messages
        debug = os.getenv(DEBUG_ENV_VAR_NAME)
        assert debug is not None
        if int(debug):
            if len(res) > 1:
                print(f"Found more than one {name} for {self.id3.filename}")
        return res

    def __init_track_or_disc_num(self, name: str) -> tuple[int, int]:
        fid = self.__frames[name+"_num"][0]
        if fid not in self.id3:
            return (0, 0)
        frame_data = self.id3[fid][0]
        if frame_data == '':
            self.__remove_frame_by_fid(fid)
            return (0, 0)
        count = total = 0
        if "/" in frame_data:
            try:
                count, total = frame_data.split("/")
            except Exception as e:
                print(
                    f"Could not get {name} number for {self.id3.filename}: {e}")
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

    def __init_year(self) -> int:
        recording_date_fid = self.__frames["recording_date"][0]
        if recording_date_fid in self.id3:
            timestamp = self.id3[recording_date_fid][0]
            year = timestamp.year
            if year:
                return year
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

    def __init__(self, file_path: Path) -> None:
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

        if not id3:
            self.__original_file_has_tags = False

    def updated_file_path(self) -> Path:
        return self.__file_path.parent / self.__file_name

    def update_crop_cover(self) -> None:
        if self.__new_cover:
            cover = self.__new_cover
        elif self.cover:
            cover = self.cover
        else:
            return
        image_editor = ImageEditor(cover)
        if not image_editor.is_image():
            self.remove_covers()
            return
        self.__crop_cover_to_square = not image_editor.image_is_square()

    @property
    def crop_cover_to_square(self) -> bool:
        return self.__crop_cover_to_square

    @crop_cover_to_square.setter
    def crop_cover_to_square(self, value: bool) -> None:
        self.__crop_cover_to_square = value
        if not self.edited:
            self.edited = True

    @property
    def preserve_file_time(self) -> bool:
        return self.__preserve_file_time

    @preserve_file_time.setter
    def preserve_file_time(self, value: bool) -> None:
        self.__preserve_file_time = value
        if not self.edited:
            self.edited = True

    @property
    def remove_other_tags(self) -> bool:
        return self.__remove_other_tags

    @remove_other_tags.setter
    def remove_other_tags(self, value: bool) -> None:
        self.__remove_other_tags = value
        if not self.edited:
            self.edited = True

    def __repr__(self) -> str:
        return f"Song(track=\"{self.track_num}\" title={self.title.__repr__()} " + \
            f"artist={self.artist.__repr__()} album={self.album.__repr__()} " + \
            f"year={self.year.__repr__()} file_path={self.file_path.__repr__()}" + \
            ")"
        # f" orig_file_path={self.orig_file_path.__repr__()})"

    @property
    def new_cover(self) -> bytes | None:
        return self.__new_cover

    @new_cover.setter
    def new_cover(self, new_cover: bytes | None) -> None:
        if new_cover == self.__new_cover:
            return
        self.__new_cover = new_cover
        if not self.edited:
            self.edited = True

    def __remove_all_tags(self) -> None:
        if not self.__original_file_has_tags:
            return
        self.__tag = Tag(ID3())

    # TODO
    def _get_relevant_tags(self) -> dict[str, Any]:
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

    def save(self) -> bool:
        if not self.edited:
            return False
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

    def __rename(self) -> bool:
        if not self.__file_name.endswith(".mp3"):
            print(f"Error: {self.__file_name} is not a valid mp3 file name")
            return False
        new_path = self.updated_file_path()
        if new_path.exists():
            # TODO: BETTER ERROR
            print(f"Error {self.__file_name}: path already exists")
            return False
        try:
            self.__file_path = self.__file_path.rename(new_path)
            if self.__preserve_file_time:
                os.utime(new_path, ns=self.__time)
        except Exception as e:
            print(f"Error {self.__file_name}: {e}")
            return False
        return True

    def remove_covers(self) -> None:
        self.__tag.remove_covers()

    def get_title_and_artist_by_file_name(self, file_name: str) -> tuple[str, str] | None:
        file_name = os.path.splitext(file_name)[0]
        # TODO: might want to add regex validation
        splitted_file_name = file_name.split(' - ')
        parts_n = len(splitted_file_name)
        if parts_n == 2:
            return (splitted_file_name[0], splitted_file_name[1])

    @property
    def cover(self) -> bytes | None:
        return self.__tag.cover

    @cover.setter
    def cover(self, image_data: bytes) -> None:
        self.__tag.cover = image_data
        if not self.edited:
            self.edited = True

    @property
    def file_path(self) -> Path:
        return self.__file_path

    @property
    def file_name(self) -> str:
        return self.__file_name

    @file_name.setter
    def file_name(self, new_file_name: str) -> None:
        if new_file_name == self.__file_name:
            return
        if new_file_name == "":
            return

        self.__file_name = new_file_name
        self.propertyChanged.emit("file_name", new_file_name)
        if not self.edited:
            self.edited = True

    @property
    def title(self) -> str:
        return self.__tag.title

    @title.setter
    def title(self, new_title: str) -> None:
        self.__tag.title = new_title
        self.propertyChanged.emit("title", new_title)
        if not self.edited:
            self.edited = True

    @property
    def artist(self) -> str:
        return self.__tag.artist

    @artist.setter
    def artist(self, new_artist: str) -> None:
        self.__tag.artist = new_artist
        self.propertyChanged.emit("artist", new_artist)
        if not self.edited:
            self.edited = True

    @property
    def album(self) -> str:
        return self.__tag.album

    @album.setter
    def album(self, new_album: str) -> None:
        self.__tag.album = new_album
        self.propertyChanged.emit("album", new_album)
        if not self.edited:
            self.edited = True

    @property
    def album_artist(self) -> str:
        return self.__tag.album_artist

    @album_artist.setter
    def album_artist(self, new_album_artist: str) -> None:
        self.__tag.album_artist = new_album_artist
        self.propertyChanged.emit("album", new_album_artist)
        if not self.edited:
            self.edited = True

    @property
    def genre(self) -> str:
        return self.__tag.genre

    @genre.setter
    def genre(self, new_genre: str) -> None:
        self.__tag.genre = new_genre
        if not self.edited:
            self.edited = True

    @property
    def track_num(self) -> tuple[int, int]:
        return self.__tag.track_num

    @track_num.setter
    def track_num(self, new_track_num: tuple[int, int]) -> None:
        self.__tag.track_num = new_track_num
        self.propertyChanged.emit("track_num", new_track_num)
        if not self.edited:
            self.edited = True

    @property
    def disc_num(self) -> tuple[int, int]:
        return self.__tag.disc_num

    @disc_num.setter
    def disc_num(self, new_disc_num: tuple[int, int]) -> None:
        self.__tag.disc_num = new_disc_num
        self.propertyChanged.emit("disc_num", new_disc_num)
        if not self.edited:
            self.edited = True

    @property
    def lyrics(self) -> str:
        return self.__tag.lyrics

    @lyrics.setter
    def lyrics(self, new_lyrics: str) -> None:
        if new_lyrics == self.lyrics:
            return
        self.__tag.lyrics = new_lyrics
        if not self.edited:
            self.edited = True

    @property
    def year(self) -> int:
        return self.__tag.year

    @year.setter
    def year(self, new_year: int) -> None:
        self.__tag.year = new_year
        if not self.edited:
            self.edited = True
        self.propertyChanged.emit("year", new_year)
