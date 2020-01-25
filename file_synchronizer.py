# -*- coding: utf-8 -*-
"""file_synchronizer.py

Folder synchronization and duplicate file remover

J. Metz <metz.jp@gmail.com>
"""
import hashlib
import os
import glob
import shutil
import argparse
import platform
import subprocess
import traceback
from dataclasses import dataclass
import numpy as np
import tqdm
# pylint: disable=no-name-in-module
from PyQt5.QtWidgets import (
    QFileDialog,
    QMessageBox,
    QApplication,
)

__qapp__ = QApplication([])
__script_dir__ = os.path.dirname(__file__)


@dataclass
class FileInfo:  # pylint: disable=too-many-instance-attributes
    """
    Class to hold file information
    """
    filepath: str
    filename: str
    folder: str
    atime: float
    mtime: float
    ctime: float
    size: int

    def __init__(self, filepath, use_hash=False):
        self.filepath = filepath
        self.folder, self.filename = os.path.split(filepath)
        try:
            self.atime = os.path.getatime(filepath)
        except Exception:
            self.atime = -1
        try:
            self.ctime = os.path.getctime(filepath)
        except Exception:
            self.ctime = -1
        try:
            self.mtime = os.path.getmtime(filepath)
        except Exception:
            self.mtime = -1
        try:
            self.size = os.path.getsize(filepath)
        except Exception:
            self.size = -1
        if use_hash:
            self.hash = get_hash(filepath)


class DirectoryContents(dict):

    def __init__(self, folder):
        self.root = folder
        super().__init__()


def get_args():
    """
    Get command-line arguments
    """
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "folder1", help="First folder to synchronize", nargs="?")
    parser.add_argument(
        "folder2", help="Second folder to synchronize", nargs="?")
    parser.add_argument(
        "-c", "--copy",
        help="Create copies instead of modifying in place",
        action="store_true")
    parser.add_argument(
        "-d", "--dry-run",
        help="Only reports what would happen",
        action="store_true")
    return parser.parse_args()


def main():
    """
    Main script entry point
    """
    args = get_args()
    startoptionwindow = QMessageBox()
    startoptionwindow.setWindowTitle("File Synchronizer")
    startoptionwindow.setText("Please select a run mode")
    cancelbutton = startoptionwindow.addButton(
        "Cancel", QMessageBox.ActionRole)
    dryrunbutton = startoptionwindow.addButton(
        "Dry-run (no changes, only creates comparison file)",
        QMessageBox.ActionRole)
    copyrunbutton = startoptionwindow.addButton(
        "Use copy",
        QMessageBox.ActionRole)
    overwritebutton = startoptionwindow.addButton(
        "Overwrite originals",
        QMessageBox.ActionRole)
    startoptionwindow.exec()
    clicked = startoptionwindow.clickedButton()
    if clicked == cancelbutton:
        print("Cancelling")
        return
    if clicked == dryrunbutton:
        args.dry_run = True
    elif clicked == copyrunbutton:
        args.copy = True
        args.dry_run = False
    elif clicked == overwritebutton:
        args.copy = False
        args.dry_run = False
    else:
        print("Unhandled option", clicked)
        return
    if not args.folder1:
        dir1 = get_dir_gui("Select directory 1")
    else:
        dir1 = args.folder1
    print("Directory selected - 1:", dir1)
    if not dir1:
        print("No directory 1 selected, exiting")
        return

    if not args.folder2:
        dir2 = get_dir_gui("Select directory 2")
    else:
        dir2 = args.folder2
    print("Directory selected - 2:", dir2)
    if not dir2:
        print("No directory 2 selected, exiting")
        return
    # dir1, dir2 = get_dirs()
    print("Getting contents...")
    contents1 = get_files(dir1)
    contents2 = get_files(dir2)
    print("Comparing contents...")
    output_filepath = os.path.join(__script_dir__, 'comparison.txt')
    write_comparison_to_file(contents1, contents2, filename=output_filepath)
    create_synchronized(
        contents1, contents2, create_copy=args.copy, dry_run=args.dry_run)

    if platform.system() == 'Darwin':       # macOS
        subprocess.call(('open', output_filepath))
    elif platform.system() == 'Windows':    # Windows
        os.startfile(output_filepath)
    else:                                   # linux variants
        subprocess.call(('xdg-open', output_filepath))


def count_files(folder):
    """
    Counts the number of files under a folder using `os.walk`
    """
    num = 0
    for _, _, files in os.walk(folder):
        num += len(files)
    return num


def get_files(folder):
    """
    Gets all files under a current folder
    """
    num = count_files(folder)
    contents = DirectoryContents(folder)
    progress = tqdm.tqdm(total=num)
    for root, _, files in os.walk(folder):
        for filename in files:
            filepath = os.path.join(root, filename)
            # file_info = FileInfo(filepath, use_hash=False)
            file_info = FileInfo(filepath)
            if file_info.size == -1:
                print("FAILED TO GET STATS FOR", filepath)
                continue
            # file_id = file_info.hash
            # file_id = filepath
            file_id = (file_info.filename, file_info.size)
            if file_id in contents:
                # print("File already present in this root:")
                contents[file_id].append(file_info)
                # print(contents[file_id])
            else:
                contents[file_id] = [file_info]
            progress.update()
    return contents


def get_hash(filepath):
    """
    Get's a file objects' hash
    """
    with open(filepath, "rb") as fobj:
        file_hash = hashlib.md5()
        chunk = fobj.read(8192)
        while chunk:
            file_hash.update(chunk)
            chunk = fobj.read(8192)
    return file_hash


def get_dir_gui(prompt="Select directory"):
    """
    Uses Qt to get existing folder using a graphical user interface
    """
    return str(QFileDialog.getExistingDirectory(None, prompt))


def get_dirs():
    """
    Gets two directories graphically
    """
    dir1 = str(QFileDialog.getExistingDirectory(None, "Select Directory 1"))
    dir2 = str(QFileDialog.getExistingDirectory(None, "Select Directory 2"))
    return dir1, dir2


def write_comparison_to_file(contents1, contents2, filename):
    """
    Writes the comparison of two folder contents to file
    """
    with open(filename, 'w') as fout:
        fout.write('Processing folder 1 [%s]\n' % contents1.root)
        for file_id, file_infos in contents1.items():
            bfile_id = str(file_id)
            if len(file_infos) > 1:
                fout.write('  Duplicate: %s \n' % bfile_id)
                for finfo in file_infos:
                    fout.write('  %s\n' % finfo.filepath)
            if file_id not in contents2:
                fout.write(
                    '  %s MISSING from %s\n' % (bfile_id, contents2.root))
        fout.write('Processing folder 2 [%s]\n' % contents2.root)
        for file_id, file_infos in contents2.items():
            bfile_id = str(file_id)
            if len(file_infos) > 1:
                fout.write('  Duplicate: %s \n' % bfile_id)
                for finfo in file_infos:
                    fout.write('  %s\n' % finfo.filepath)
            if file_id not in contents1:
                fout.write(
                    '  %s MISSING from %s\n' % (bfile_id, contents1.root))


def create_synchronized(
        contents1, contents2, create_copy=True, dry_run=True):
    """
    Performs the actual synchronization
    """
    if not dry_run:
        ans = input(
            "Warning, this is not a drill, do you want to continue [Ny]?")
        if ans.lower() != "y":
            print("Aborting")
            return

    if create_copy:
        copy_path1 = os.path.join(contents1.root, 'AUTOMATIC_BACKUP')
        if os.path.isdir(copy_path1):
            raise Exception(
                'AUTOMATIC_BACKUP directory 1 already exists at\n%s' %
                copy_path1)
        copy_path2 = os.path.join(contents2.root, 'AUTOMATIC_BACKUP')
        if os.path.isdir(copy_path2):
            raise Exception(
                'AUTOMATIC_BACKUP directory 2 already exists at\n%s' %
                copy_path2)
        shutil.copytree(contents1.root, copy_path1)
        shutil.copytree(contents2.root, copy_path2)

    for file_id, file_infos in contents1.items():
        if len(file_infos) > 1:
            # Delete the older files
            mtimes = [info.mtime for info in file_infos]
            youngest = np.argmax(mtimes)
            keep_file = file_infos.pop(youngest)
            print("Keeping", keep_file.filepath)
            # Delete remaining
            for file_info in file_infos:
                print("Removing", file_info.filepath)
                if not dry_run:
                    try:
                        os.remove(file_info.filepath)
                    except Exeption:
                        print("FAILED TO REMOVE FILE")
        else:
            keep_file = file_infos[0]

        if file_id not in contents2:
            # Copy file to contents2
            destpath = "%s%s" % (
                contents2.root,
                keep_file.filepath[len(contents1.root):])
            print(
                "Copying the kept file (", keep_file.filepath,
                ") to", destpath)
            try:
                shutil.copy2(keep_file.filepath, destpath)
            except Exception:
                print("FAILED TO COPY FILE")

    for file_id, file_infos in contents2.items():
        if len(file_infos) > 1:
            # Delete the older files
            mtimes = [info.mtime for info in file_infos]
            youngest = np.argmax(mtimes)
            keep_file = file_infos.pop(youngest)
            print("Keeping", keep_file.filepath)
            # Delete remaining
            for file_info in file_infos:
                print("Removing", file_info.filepath)
                if not dry_run:
                    try:
                        os.remove(file_info.filepath)
                    except Exception:
                        print("FAILED TO REMOVE FILE")
        else:
            keep_file = file_infos[0]

        if file_id not in contents1:
            # Copy file to contents1
            destpath = "%s%s" % (
                contents1.root,
                keep_file.filepath[len(contents2.root):])
            print(
                "Copying the kept file (", keep_file.filepath,
                ") to", destpath)
            try:
                shutil.copy2(keep_file.filepath, destpath)
            except Exception:
                print("FAILED TO COPY FILE")


if __name__ == "__main__":
    try:
        main()
    except Exception:
        print("FAILED WITH ERROR")
        traceback.print_exc()
    input("Program ended, press any key to exit") 
