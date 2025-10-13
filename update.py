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
    Determine whether a newer version of the script is available.
    
    Checks the latest remote version and compares it to the local version stored in the version file; if the local version file is missing, an update is required.
    
    Returns:
        should_update (bool): `true` if the local installation should be updated, `false` otherwise.
        version (str): The latest remote version identifier (commit SHA).
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
    """
    Retrieve the latest commit SHA for the repository branch used by the updater.
    
    Returns:
        str: The SHA of the most recent commit from the remote version endpoint.
    
    Raises:
        RuntimeError: If the remote version endpoint does not return a successful (200) response.
    """
    response = requests.get(version_url)

    if response.status_code == 200:
        return response.json()[0]['sha']
    else:
        raise RuntimeError("Unable to find the most recent version of the script.")



def download_update():
    """
    Download the repository archive for the configured branch and save it as the update zip file in the outdated directory.
    
    Raises:
        RuntimeError: If the HTTP request to download the archive does not return status code 200.
    """
    response = requests.get(download_url)

    if response.status_code != 200:
        raise RuntimeError("Unable to download the most recent version of the script.")

    full_path = os.path.join(outdated_dir, update_zip)
    with open(full_path, 'wb') as file:
        file.write(response.content)


def unzip():
    """
    Extract the downloaded update archive into the temporary updated directory.
    
    Unpacks the repository archive located in the outdated directory into the configured updated directory so the new files are available for installation.
    """
    full_zip_path: str = os.path.join(outdated_dir, update_zip)
    full_output_path: str = os.path.join(outdated_dir, updated_dir_name)
    shutil.unpack_archive(full_zip_path, full_output_path)


def install_update():
    """
    Synchronize the current install directory with the unpacked update by removing removed files and copying new or changed files.
    
    Removes any files or directories in the installation directory that are not present in the update (excluding entries listed in `ignored`), copies files and directories from the update into the installation location (preserving directory structure and replacing existing entries), and removes the temporary update directory named by `updated_dir_name`.
    """
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
            shutil.copytree(full_src, full_dest)
        else:
            shutil.copy2(full_src, full_dest)

    # Delete the folder containing the updated script
    shutil.rmtree(os.path.join(outdated_dir, updated_dir_name))


def update_version_info(version: str):
    """
    Write the given version string to the local version tracking file, overwriting any existing contents.
    
    Parameters:
        version (str): Version identifier to record (e.g., commit SHA).
    """
    with open(os.path.join(outdated_dir, version_file), 'w') as file:
        file.write(version)


def main():
    """
    Coordinate the self-update workflow for the script.
    
    Performs a version check and, if an update is available, downloads the latest archive, unpacks and installs the update, updates stored version information, and ensures required dependencies are installed. If no update is needed, reports that the script is up to date. Side effects include console output and modifying the local installation files.
    """
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