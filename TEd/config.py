import sys
from pathlib import Path

_PACKAGE_ROOT_PATH = Path(__file__).resolve().parent
# for pyinstaller
if hasattr(sys, "_MEIPASS"):
    _PACKAGE_ROOT_PATH = Path(sys._MEIPASS).resolve()

PLATFORM = sys.platform
APP_NAME = "TEd"
DEBUG_ENV_VAR_NAME = "_TED_DEBUG"

ICONS_DIR_PATH = _PACKAGE_ROOT_PATH / "icons"
DISCARD_ICON_PATH = ICONS_DIR_PATH / "discard-22.png"
_LOGOS_DIR_PATH = ICONS_DIR_PATH / "logo"
APP_ICON_FILE_PATH = _LOGOS_DIR_PATH / "TEd.ico"
SVG_LOGO_FILE_PATH = _LOGOS_DIR_PATH / "TEd.svg"
UI_DIR_PATH = _PACKAGE_ROOT_PATH / "ui"
SOURCE_UI_DIR_PATH = UI_DIR_PATH / "source"

UI_FILE_PATHS = [SOURCE_UI_DIR_PATH / name for name in (
    "table_window.ui",
    "album_creation_dialog.ui",
    "edit_tags_dialog.ui",
    "set_all_dialog.ui",
)]
