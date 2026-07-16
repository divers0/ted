import sys
from pathlib import Path

ROOT_PATH = Path(__file__).resolve().parent
# for pyinstaller
if hasattr(sys, "_MEIPASS"):
    ROOT_PATH = Path(sys._MEIPASS).resolve()

PLATFORM = sys.platform

ENTRY_POINT_PATH = ROOT_PATH / "main.py"
ICONS_DIR_PATH = ROOT_PATH / "icons"
DISCARD_ICON_PATH = ICONS_DIR_PATH / "discard-22.png"
_LOGOS_DIR_PATH = ICONS_DIR_PATH / "logo"
APP_ICON_FILE_PATH = _LOGOS_DIR_PATH / "TEd.ico"
SVG_LOGO_FILE_PATH = _LOGOS_DIR_PATH / "TEd.svg"
_UI_DIR_PATH = ROOT_PATH / "ui"
GENERATED_UI_DIR_PATH = _UI_DIR_PATH / "generated"

UI_FILE_PATHS = [_UI_DIR_PATH / name for name in (
    "table_window.ui",
    "album_creation_dialog.ui",
    "edit_tags_dialog.ui",
    "set_all_dialog.ui",
)]
