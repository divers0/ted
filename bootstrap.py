import json
import subprocess
import sys
import tempfile
import venv
from pathlib import Path
from shutil import rmtree

from TEd.config import (APP_ICON_FILE_PATH, ICONS_DIR_PATH, PLATFORM,
                        UI_DIR_PATH, UI_FILE_PATHS)

USAGE = """USAGE: [setup|run|build|build-ui|help]
setup: creates a virtual environment named `.venv` if there isn't one already
       and installs the dependencies in it.

run: regenerates python ui files if needed and runs the main script.
  subcommand: [debug]: runs the main script in debug mode.

build: regenerates python ui files if needed and builds the executable using pyinstaller.

build-ui: regenerates python ui files if needed.

help: prints this and exits."""

COMMANDS = {
    "setup",
    "build",
    "build-ui",
    "run",
    "help",
}

DEPENDENCIES = {
    "PyQt6",
    "mutagen",
    "pillow",
    "pyinstaller",
}

ROOT = Path(__file__).parent.resolve()
REQUIREMENTS_FILE_PATH = ROOT / "requirements.lock"
VENV_DIR_PATH = ROOT / ".venv"


def error(message, fatal=True):
    print("ERROR: " + message)
    if fatal:
        sys.exit(1)


def run_command(command, **kwargs):
    return subprocess.run(command, check=True, **kwargs)


def update_ui_files(python_exec_path):
    for ui_file_path in UI_FILE_PATHS:
        py_file_path = UI_DIR_PATH / \
            (ui_file_path.stem.title().replace("_", "")+".py")

        if not ui_file_path.is_file():
            error(f"{ui_file_path} does not exist. skipping...", fatal=False)
            continue
        if not py_file_path.is_file():
            print(f"Making {py_file_path} for {ui_file_path}...")
        elif ui_file_path.stat().st_mtime_ns > py_file_path.stat().st_mtime_ns:
            print(f"Updating {py_file_path}...")
        else:
            continue

        run_command([str(python_exec_path), "-m", "PyQt6.uic.pyuic",
                    str(ui_file_path), "-o", str(py_file_path)])


def parse_args():
    argv = sys.argv[1:]
    if len(argv) not in (1, 2):
        error(USAGE)
    command = argv[0]
    if command.startswith("--"):
        command = command[2:]
    if command not in COMMANDS:
        error(USAGE)
    if command != "run":
        if len(argv) == 2:
            error(USAGE)  # only run can accept a subcommand
        return command
    if len(argv) == 2:
        if argv[1] not in ("debug", "--debug"):
            error(USAGE)
    return command


def cleanup_previous_builds():
    dist = ROOT / "dist"
    build = ROOT / "build"
    if dist.is_dir():
        rmtree(dist)
    if build.is_dir():
        rmtree(build)


def build(python_exec_path):
    assert (PLATFORM == "win32")
    with tempfile.TemporaryDirectory() as tmp:
        launcher = Path(tmp) / "launcher.py"
        launcher.write_text(
            "import sys\n"
            "from TEd.main import main\n"
            "if __name__ == '__main__':\n"
            "    sys.exit(main())\n",
        )
        separator = ";"
        run_command([str(python_exec_path), "-m", "PyInstaller",
                     "--clean",
                     "--onedir",
                     "--windowed",
                     "-n=TEd",
                     "--icon="+str(APP_ICON_FILE_PATH),
                     "--add-data="+str(ICONS_DIR_PATH) +
                     separator+ICONS_DIR_PATH.name,
                     "--specpath="+str(launcher.parent),
                     str(launcher),
                     ])


def get_venv_python_exec_path():
    if PLATFORM == "win32":
        python_exec_path = VENV_DIR_PATH / "Scripts" / "python.exe"
    else:
        python_exec_path = VENV_DIR_PATH / "bin" / "python"
    return python_exec_path


def get_correct_python_exec_path():
    if VENV_DIR_PATH.is_dir():
        return get_venv_python_exec_path()
    print("No .venv found: using the current Python interpreter.")
    return sys.executable


def setup_venv():
    if not VENV_DIR_PATH.is_dir():
        print("No .venv directory, setting up a virtual environment...")
        venv.create(VENV_DIR_PATH, with_pip=True)
    python_exec_path = get_venv_python_exec_path()
    if not REQUIREMENTS_FILE_PATH.is_file():
        error(f"{str(REQUIREMENTS_FILE_PATH)} does not exist")
    print("Installing the dependencies...")
    run_command([
        str(python_exec_path), "-m",
        "pip", "install", "-r", str(REQUIREMENTS_FILE_PATH),
    ])
    return python_exec_path


def check_for_dependencies(python_exec_path, force_pyinstaller=False):
    res = run_command(
        [str(python_exec_path), "-m", "pip", "list", "--format=json"],
        capture_output=True,
        text=True
    )
    installed_packages = {
        pkg["name"] for pkg in json.loads(res.stdout)
    }
    for dep in DEPENDENCIES:
        if dep not in installed_packages:
            if dep.lower() == "pyinstaller" and not force_pyinstaller:
                continue
            error(f"{dep} is not installed.\n" +
                  "Run `python bootstrap.py setup` or " +
                  "install the packages however you want.")


def check_python_version():
    ver = sys.version_info
    if ver.major+(ver.minor/100) < 3.10:
        error("You'll need at least Python 3.10 to run this program")


def main():
    check_python_version()
    args = parse_args()
    match args:
        case "help":
            print(USAGE)
            return
        case "build-ui":
            python_exec_path = get_correct_python_exec_path()
            check_for_dependencies(python_exec_path)
            update_ui_files(python_exec_path)
        case "setup":
            setup_venv()
        case "build":
            if PLATFORM != "win32":
                error("building on your platform is not supported.")
            python_exec_path = get_correct_python_exec_path()
            check_for_dependencies(python_exec_path, force_pyinstaller=True)
            update_ui_files(python_exec_path)
            cleanup_previous_builds()
            build(python_exec_path)
        case "run":
            python_exec_path = get_correct_python_exec_path()
            check_for_dependencies(python_exec_path)
            update_ui_files(python_exec_path)
            from TEd.main import main as ted_main
            ted_main()


if __name__ == "__main__":
    main()
