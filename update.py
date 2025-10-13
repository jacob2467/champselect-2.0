import dependencies
import requests
import shutil
import os

owner: str = "jacob2467"
repo: str = "champselect-2.0"
branch: str = "main"
version_file: str = "version.txt"
update_zip: str = "update.zip"

outdated_dir, download_script_name = os.path.split(__file__)

updated_dir_name: str = "update"
updated_dir: str = os.path.join(outdated_dir, updated_dir_name, f"{repo}-{branch}")

config: str = "config.ini"

download_url: str = f"https://github.com/{owner}/{repo}/archive/refs/heads/{branch}.zip"
version_url: str = f"https://api.github.com/repos/{owner}/{repo}/commits?per_page=1"


ignored = {
    '__pycache__', '.mypy_cache', '.vscode', '.git', '.gitignore', version_file, config, download_script_name,
    updated_dir_name
}

def check_for_update() -> tuple[bool, str]:
    """
    Check if the script needs to be updated.
    Returns:
        - a bool indicating whether or not the script needs to be updated
        - the version of the script the user currently has
    """
    version = get_version()

    # Look for version.txt
    try:
        with open(os.path.join(outdated_dir, version_file), 'r') as file:
            old_version = file.read()
            should_update: bool = version != old_version
    except FileNotFoundError:
        should_update = True

    return should_update, version


def get_version():
    """ Check the most recent version of the script. """
    response = requests.get(version_url, timeout=10)

    if response.status_code == 200:
        return response.json()[0]['sha']
    else:
        raise RuntimeError("Unable to find the most recent version of the script.")


def download_update():
    """ Download the most recent version of the script and store it as a zip file. """
    response = requests.get(download_url, timeout=30)

    if response.status_code != 200:
        raise RuntimeError("Unable to download the most recent version of the script.")

    full_path = os.path.join(outdated_dir, update_zip)
    with open(full_path, 'wb') as file:
        file.write(response.content)


def unzip():
    """ Unzip the downloaded zip archive. """
    full_zip_path: str = os.path.join(outdated_dir, update_zip)
    full_output_path: str = os.path.join(outdated_dir, updated_dir_name)
    shutil.unpack_archive(full_zip_path, full_output_path)


def install_update():
    """ Copy the updated files to the script's install location. """
    outdated_files = os.listdir(outdated_dir)

    updated_files = os.listdir(updated_dir)

    # Delete files that have been deleted on remote
    for file in outdated_files:
        full_path: str = os.path.join(outdated_dir, file)
        if file in ignored:
            continue

        if file not in updated_files:
            if os.path.isdir(full_path):
                shutil.rmtree(full_path)
            else:
                os.remove(full_path)

    # Copy over new files
    for file in updated_files:
        if file in ignored:
            continue

        full_src = os.path.join(updated_dir, file)
        full_dest = os.path.join(outdated_dir, file)

        if os.path.isdir(full_src):
            shutil.rmtree(full_dest, ignore_errors=True)
            shutil.copytree(full_src, full_dest)
        else:
            shutil.copy2(full_src, full_dest)

    # Delete the folder containing the updated script
    shutil.rmtree(os.path.join(outdated_dir, updated_dir_name))


def update_version_info(version: str):
    """ Update the file storing the script's current version. """
    with open(os.path.join(outdated_dir, version_file), 'w') as file:
        file.write(version)


def main():
    print("Checking for updates...\n")
    should_update, current_version = check_for_update()
    if should_update:
        print("Script is out of date. Downloading update...\n")
        download_update()
        unzip()
        install_update()
        update_version_info(current_version)
        print("Update successfully installed! Checking dependencies...\n")
        dependencies.install_dependencies()
    else:
        print("Script is already up to date!")


if __name__ == "__main__":
    main()