import sys
import subprocess
from shutil import which, rmtree
from config import (
    PLATFORM,
    ROOT_PATH,
    ENTRY_POINT_PATH,
    APP_ICON_FILE_PATH,
    UI_FILE_PATHS,
    GENERATED_UI_DIR_PATH,
    ICONS_DIR_PATH,
)

USAGE = """USAGE: [run|build|build-ui]
run: regenerates python ui files if needed and runs the main script.
    subcommand: [debug]: runs the main script in debug mode.

build: regenerates python ui files if needed and builds the executable using pyinstaller.

build-ui: regenerates python ui files if needed. """

COMMANDS = {
    "build",
    "build-ui",
    "run",
}

def error(message, fatal=True):
    print("ERROR: " + message)
    if fatal: sys.exit(1)

def run_command(command):
    subprocess.run(command, check=True)

def update_ui_files():
    check_if_its_installed("pyuic6")
    for ui_file_path in UI_FILE_PATHS:
        py_file_path = GENERATED_UI_DIR_PATH / (ui_file_path.stem.title().replace("_", "")+".py")

        if not ui_file_path.is_file():
            error(f"{ui_file_path} does not exist. skipping...", fatal=False)
            continue

        if not py_file_path.is_file():
            print(f"Making {py_file_path} for {ui_file_path}...")
            run_command(["pyuic6", str(ui_file_path), "-o", str(py_file_path)])
            continue
        if ui_file_path.stat().st_mtime_ns > py_file_path.stat().st_mtime_ns:
            print(f"Updating {py_file_path}...")
            run_command(["pyuic6", str(ui_file_path), "-o", str(py_file_path)])

def parse_args():
    argv = sys.argv[1:]
    if len(argv) not in (1, 2): error(USAGE)
    command = argv[0]
    if command not in COMMANDS: error(USAGE)
    if command != "run":
        if len(argv) == 2: error(USAGE)
        return command
    debug = False
    if len(argv) == 2:
        if argv[1] != "debug": error(USAGE)
        debug = True
    return command if not debug else "debug"

def check_if_its_installed(name):
    if not which(name): error(f"{name} is not installed")

def cleanup_previous_builds():
    dist = ROOT_PATH / "dist"
    build = ROOT_PATH / "build"
    if dist.is_dir():
        rmtree(dist)
    if build.is_dir():
        rmtree(build)

def build():
    separator = ";"
    run_command(["pyinstaller",
        "--clean",
        "--onedir",
        "--windowed",
        "-n=TEd",
        "--icon="+str(APP_ICON_FILE_PATH),
        "--add-data="+str(ICONS_DIR_PATH)+separator+ICONS_DIR_PATH.name,
        "main.py"
    ])

if __name__ == "__main__":
    for path in (ENTRY_POINT_PATH, APP_ICON_FILE_PATH):
        if not path.is_file():
            error(f"{path} does not exist or is not a file.")

    args = parse_args()
    update_ui_files()
    match args:
        case "build-ui":
            pass
        case "build":
            check_if_its_installed("pyinstaller")
            cleanup_previous_builds()
            if PLATFORM != "win32":
                error("building on your platform is not supported.")
            build()
        case "run" | "debug":
            command = ["python", str(ENTRY_POINT_PATH)]
            if args == "debug": command.append("--debug")
            run_command(command)
