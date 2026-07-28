from io import BytesIO

from PIL import Image, UnidentifiedImageError
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import QLabel, QVBoxLayout, QWidget


class ImageViewer(QWidget):
    def __init__(self, image_data: bytes, parent: QWidget | None = None) -> None:
        super().__init__(parent, Qt.WindowType.Window)

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        label = QLabel()
        layout.addWidget(label)

        image_editor = ImageEditor(image_data)
        self.setWindowTitle(
            f"Image Viewer ({image_editor.width}x{image_editor.height})")

        pixmap = QPixmap()
        pixmap.loadFromData(image_editor.scale_down())
        label.setPixmap(pixmap)
        self.setLayout(layout)
        self.setFixedSize(pixmap.width(), pixmap.height())
        self.setWindowModality(Qt.WindowModality.NonModal)


class ImageEditor:
    def __init__(self, data: bytes) -> None:
        self.__data = data
        try:
            self.__image = Image.open(BytesIO(data))
        except UnidentifiedImageError:
            self.__image = None
        if not self.__image:
            return
        if self.__image.format not in ("JPEG", "PNG"):
            raise ValueError(
                f"Expected JPEG/PNG format, got {self.__image.format}")

        self.__QUALITY = 95

    @property
    def width(self) -> int:
        assert self.__image
        return self.__image.width

    @property
    def height(self) -> int:
        assert self.__image
        return self.__image.height

    def is_image(self) -> bool:
        return self.__image is not None

    def image_is_square(self) -> bool:
        assert bool(self.__image)
        return self.__image.width == self.__image.height

    def crop_to_center_square(self) -> bytes:
        assert self.__image
        width, height = self.__image.size
        x = (width-height)/2
        self.__image = self.__image.crop((x, 0, x+height, height))
        output_bytes = BytesIO()
        self.__image.save(output_bytes, format="JPEG",
                          quality=self.__QUALITY)
        self.__data = output_bytes.getvalue()
        return self.__data

    def scale_down(self) -> bytes:
        assert self.__image
        if self.__image.height <= 720:
            return self.__data
        new_height = 720
        scale = 1 - ((self.__image.height - new_height)/self.__image.height)
        new_width = int(self.__image.width*scale)

        output_bytes = BytesIO()
        self.__image.resize((new_width, new_height)).save(
            output_bytes, format="PNG", quality=self.__QUALITY)
        return output_bytes.getvalue()
