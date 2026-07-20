from PyQt6.QtCore import (QAbstractItemModel, QEvent, QModelIndex, QObject,
                          QRegularExpression, pyqtSignal)
from PyQt6.QtGui import QMouseEvent, QPainter, QRegularExpressionValidator
from PyQt6.QtWidgets import (QApplication, QLineEdit, QSpinBox, QStyle,
                             QStyledItemDelegate, QStyleOptionButton,
                             QStyleOptionViewItem, QWidget)


class YearLineEditDelegate(QStyledItemDelegate):
    def __init__(self, parent: QObject | None = None) -> None:
        self.validation_regex = "^$|[1-9][0-9]{3}"
        super().__init__(parent)

    def createEditor(
            self,
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
            self,
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
        if not style:
            return
        style.drawControl(QStyle.ControlElement.CE_PushButton, opt, painter)

    def editorEvent(
            self,
            event: QEvent | None,
            model: QAbstractItemModel | None,
            option: QStyleOptionViewItem,
            index: QModelIndex) -> bool:
        if not event:
            return False
        if event.type() != QEvent.Type.MouseButtonRelease:
            return False
        assert isinstance(event, QMouseEvent)
        if not option.rect.contains(event.position().toPoint()):
            return False

        self.clicked.emit(index)
        return True


class TrackSpinBoxDelegate(QStyledItemDelegate):
    def createEditor(
            self,
            parent: QWidget | None,
            option: QStyleOptionViewItem,
            index: QModelIndex) -> QWidget | None:
        editor = QSpinBox(parent)
        editor.setFrame(False)
        editor.setMinimum(0)
        editor.setMaximum(100)
        return editor
