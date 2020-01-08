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
import tqdm
from PyQt5.QtWidgets import QFileDialog, QApplication

__qapp__ = QApplication([])
__script_dir__ = os.path.dirname(__file__)


@dataclass
class FileInfo:
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
        self.atime = os.path.getatime(filepath)
        self.ctime = os.path.getctime(filepath)
        self.mtime = os.path.getmtime(filepath)
        self.size = os.path.getsize(filepath)
        if use_hash:
            self.hash = get_hash(filepath)


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
    with open(os.path.join(__script_dir__, 'comparison.txt'), 'wb') as fout:
        for file_id, file_infos in contents1.items():
            if file_id in contents2:
                # print("Duplicate file found:")
                # print(file_infos)
                # print(contents2[file_id])
                fout.write(b''.join((
                    b'Duplicate: ',
                    bytes(str(file_id), 'utf8', 'ignore'),
                    b'\n')))
                for finfo in file_infos:
                    fout.write(bytes(finfo.filepath, 'utf8', 'ignore'))
                    fout.write(b'\n')
                for finfo in contents2[file_id]:
                    fout.write(bytes(finfo.filepath, 'utf8', 'ignore'))
                    fout.write(b'\n')
    create_synchronized(contents1, contents2, create_copy=args.copy)



def count_files(folder):
    num = 0
    for root, folders, files in os.walk(folder):
        num += len(files)
    return num


def get_files(folder):
    num = count_files(folder)
    contents = {}
    progress = tqdm.tqdm(total=num)
    for root, folders, files in os.walk(folder):
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
    with open(filepath, "rb") as fobj:
        file_hash = hashlib.md5()
        chunk = fobj.read(8192)
        while chunk:
            file_hash.update(chunk)
            chunk = fobj.read(8192)
    return file_hash


def get_dir_gui(prompt="Select directory"):
    return str(QFileDialog.getExistingDirectory(None, prompt))


def get_dirs():
    """
    Gets two directories graphically
    """
    dir1 = str(QFileDialog.getExistingDirectory(None, "Select Directory 1"))
    dir2 = str(QFileDialog.getExistingDirectory(None, "Select Directory 2"))
    return dir1, dir2


def create_synchronized(contents1, contents2, create_copy=True):
    """
    Performs the actual synchronization
    """
    raise NotImplementedError("Not performing actual synchronization")


if __name__ == "__main__":
    main()
