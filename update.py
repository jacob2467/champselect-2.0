from os.path import isdir

import requests
import zipfile
import shutil
import os

# TODO: Clean up this file. A lot.

owner: str = "jacob2467"
repo: str = "champselect-2.0"
version_file: str = "version.txt"
update_zip: str = "update.zip"

# let me cook
outdated_dir, download_script_name = os.path.split(__file__)

updated_dir_name: str = "update"
updated_dir: str = os.path.join(outdated_dir, "update")

config: str = "config.ini"

download_url: str = f"https://github.com/{owner}/{repo}/archive/refs/heads/main.zip"
version_url: str = f"https://api.github.com/repos/{owner}/{repo}/commits?per_page=1"

ignored = {
    '__pycache__', '.mypy_cache', '.vscode', '.git', '.gitignore', version_file, config, download_script_name,
    updated_dir_name
    }

def check_for_update():
    version = get_version()
    try:
        with open(os.path.join(outdated_dir, version_file), "r") as file:
            old_version = file.read()
            should_update: bool = version != old_version
    except FileNotFoundError:
        should_update = True

    with open(os.path.join(outdated_dir, version_file), "w") as file:
        file.write(version)

    return should_update


def get_version():
    response = requests.get(version_url)

    if response.status_code == 200:
        return response.json()[0]['sha']

def download_update_zip():
    response = requests.get(download_url)
    with open(update_zip, "wb") as file:
        file.write(response.content)

def unzip():
    update = zipfile.ZipFile(update_zip)

    os.makedirs(updated_dir_name, exist_ok=True)

    for file in update.filelist:
        try:
            new_path = os.path.join(updated_dir, os.path.split(file.filename) [1])
            if isdir (new_path) and os.name == "nt":
                new_path = new_path[: -1]
            with open(new_path, "wb") as outfile:
                outfile.write(update.read(file.filename))
        except (IsADirectoryError, PermissionError):
            pass

def copy_update(*, src: str = updated_dir, dest: str = outdated_dir):
    outdated_dir = dest
    outdated_files = os.listdir(outdated_dir)

    updated_dir = src
    updated_files = os.listdir(updated_dir)

    # Delete files that have been deleted on remote
    for file in outdated_files:
        if file in ignored:
            continue

        if file not in updated_files:
            if isdir(file):
                delete_folder(os.path.join(outdated_dir, file))
            else:
                os.remove(file)

    for file in updated_files:
        if file in ignored:
            continue

        full_src = os.path.join(updated_dir, file)
        full_dest = os.path.join(outdated_dir, file)

        shutil.copy(full_src, full_dest)

    delete_folder(os.path.join(outdated_dir, updated_dir_name))

def delete_folder(folder_path: str):
    for file in os.listdir(folder_path):
        try:
            if isdir(file):
                delete_folder(os.path.join(folder_path, file))
            else:
                os.remove(os.path.join(folder_path, file))
        except PermissionError:
            return  # if we don't have permission to delete some of the files, we can't delete the whole folder,
                    # so just early return instead
    os.removedirs(folder_path)

def main():
    should_update = check_for_update()
    if should_update:
        download_update_zip()
        unzip()
        copy_update()

if __name__ == "__main__":
    main()
