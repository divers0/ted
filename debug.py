# Script for generating the PyQt6 Ui files from their .ui counterparts
import os
import sys
import subprocess
from shutil import which
from main import UI_DIR_NAME, UI_FILE_NAMES

MAIN_FILE_NAME = "main.py"

def create_py_ui_file(ui_file_path, py_file_path, ui_file_stat):
    subprocess.run(["pyuic6", ui_file_path, "-o", py_file_path])
    os.utime(py_file_path, (ui_file_stat.st_atime, ui_file_stat.st_mtime))

def main():
    for ui_file_name in UI_FILE_NAMES:
        py_file_name = os.path.splitext(ui_file_name)[0].title().replace("_", "")+".py"
        ui_file_path = os.path.join(UI_DIR_NAME, ui_file_name)
        py_file_path = os.path.join(UI_DIR_NAME, py_file_name)

        if not os.path.isfile(ui_file_path):
            print(f"ERROR: {ui_file_path} does not exist. skipping...")
            continue

        ui_file_stat = os.stat(ui_file_path)
        if not os.path.isfile(py_file_path):
            print(f"Making {py_file_path} for {ui_file_path}...")
            create_py_ui_file(ui_file_path, py_file_path, ui_file_stat)
            continue
        py_file_stat = os.stat(py_file_path)
        if ui_file_stat.st_mtime != py_file_stat.st_mtime:
            print(f"Updating {py_file_path}...")
            create_py_ui_file(ui_file_path, py_file_path, ui_file_stat)

if __name__ == "__main__":
    run = False
    if len(sys.argv) > 1:
        if sys.argv[1] == "run":
            run = True
        else:
            print(f"ERROR: invalid argument '{sys.argv[1]}'")
            sys.exit(1)
    if not which("pyuic6"):
        print("ERROR: pyuic6 is not installed")
        sys.exit(1)
    main()
    if run:
        subprocess.run(["python", MAIN_FILE_NAME, "--debug"])
