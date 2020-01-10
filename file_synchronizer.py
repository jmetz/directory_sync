# -*- coding: utf-8 -*-
"""
Editor de Spyder

Este es un archivo temporal.
"""
import hashlib
import os
import glob
import shutil
import argparse
from dataclasses import dataclass
import numpy as np
import tqdm
# pylint: disable=no-name-in-module
from PyQt5.QtWidgets import (
    QFileDialog,
    QApplication,
)

__qapp__ = QApplication([])
__script_dir__ = os.path.dirname(__file__)


@dataclass
class FileInfo:  # pylint: disable=too-many-instance-attributes
    """
    Class to hold file information
    """
    filepath: bytes
    filename: bytes
    folder: bytes
    atime: float
    mtime: float
    ctime: float
    size: int

    def __init__(self, filepath, use_hash=False):
        filepath = bytes(filepath, 'utf8', 'ignore')
        self.filepath = filepath
        self.folder, self.filename = os.path.split(filepath)
        self.atime = os.path.getatime(filepath)
        self.ctime = os.path.getctime(filepath)
        self.mtime = os.path.getmtime(filepath)
        self.size = os.path.getsize(filepath)
        if use_hash:
            self.hash = get_hash(filepath)


class DirectoryContents(dict):

    def __init__(self, folder):
        self.root = bytes(folder, 'utf8', 'ignore')
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
    if not args.folder1:
        dir1 = get_dir_gui("Select directory 1")
    else:
        dir1 = args.folder1
    if not args.folder2:
        dir2 = get_dir_gui("Select directory 2")
    else:
        dir2 = args.folder2
    # dir1, dir2 = get_dirs()
    print("Directory selected - 1:", dir1)
    if not dir1:
        print("No directory 1 selected, exiting")
        return
    print("Directory selected - 2:", dir2)
    if not dir2:
        print("No directory 2 selected, exiting")
        return
    print("Getting contents...")
    contents1 = get_files(dir1)
    contents2 = get_files(dir2)
    print("Comparing contents...")
    write_comparison_to_file(contents1, contents2)
    create_synchronized(
        contents1, contents2, create_copy=args.copy, dry_run=args.dry_run)


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


def write_comparison_to_file(
        contents1, contents2,
        filename=os.path.join(__script_dir__, 'comparison.txt')):
    """
    Writes the comparison of two folder contents to file
    """
    with open(filename, 'wb') as fout:
        fout.write(b'Processing folder 1 [%s]\n' % contents1.root)
        for file_id, file_infos in contents1.items():
            bfile_id = bytes(str(file_id), 'utf8', 'ignore')
            if len(file_infos) > 1:
                fout.write(b'  Duplicate: %s \n' % bfile_id)
                for finfo in file_infos:
                    fout.write(b'  %s\n' % finfo.filepath)
            if file_id not in contents2:
                fout.write(
                    b'  %s MISSING from %s\n' % (bfile_id, contents2.root))
        fout.write(b'Processing folder 2 [%s]\n' % contents2.root)
        for file_id, file_infos in contents2.items():
            bfile_id = bytes(str(file_id), 'utf8', 'ignore')
            if len(file_infos) > 1:
                fout.write(b'  Duplicate: %s \n' % bfile_id)
                for finfo in file_infos:
                    fout.write(b'  %s\n' % finfo.filepath)
            if file_id not in contents1:
                fout.write(
                    b'  %s MISSING from %s\n' % (bfile_id, contents1.root))


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
        copy_path1 = os.path.join(contents1.root, b'AUTOMATIC_BACKUP')
        if os.path.isdir(copy_path1):
            raise Exception(
                b'AUTOMATIC_BACKUP directory 1 already exists at\n%s' %
                copy_path1)
        copy_path2 = os.path.join(contents2.root, b'AUTOMATIC_BACKUP')
        if os.path.isdir(copy_path2):
            raise Exception(
                b'AUTOMATIC_BACKUP directory 2 already exists at\n%s' %
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
                    os.remove(file_info.filepath)
        else:
            keep_file = file_infos[0]

        if file_id not in contents2:
            # Copy file to contents2
            destpath = b"%s%s" % (
                contents2.root,
                keep_file.filepath[len(contents1.root):])
            print(
                "Copying the kept file (", keep_file.filepath,
                ") to", destpath)
            shutil.copy2(keep_file.filepath, destpath)

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
                    os.remove(file_info.filepath)
        else:
            keep_file = file_infos[0]

        if file_id not in contents1:
            # Copy file to contents1
            destpath = b"%s%s" % (
                contents1.root,
                keep_file.filepath[len(contents2.root):])
            print(
                "Copying the kept file (", keep_file.filepath,
                ") to", destpath)
            shutil.copy2(keep_file.filepath, destpath)



if __name__ == "__main__":
    main()
