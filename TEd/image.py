from io import BytesIO

from PIL import Image, UnidentifiedImageError
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import QLabel, QVBoxLayout, QWidget


class ImageViewer(QWidget):
    def __init__(self, image_data: bytes, parent: QWidget | None = None) -> None:
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

    def is_image(self) -> bool:
        return self.__image is not None

    def image_is_square(self) -> bool:
        assert bool(self.__image)
        return self.__image.width == self.__image.height

    @property
    def data(self) -> bytes:
        return self.__data

    def crop_to_center_square(self) -> bytes:
        assert self.__image
        width, height = self.__image.size
        x = (width-height)/2
        self.__image = self.__image.crop((x, 0, x+height, height))
        output_bytes = BytesIO()
        self.__image.save(output_bytes, format="JPEG", quality=95)
        return output_bytes.getvalue()
