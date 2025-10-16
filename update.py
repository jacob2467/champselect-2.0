import importlib.util
import subprocess
import shutil
import os


owner: str = "jacob2467"
repo: str = "champselect-2.0"
branch: str = "webserver"
version_file: str = "version.txt"
update_zip: str = "update.zip"

outdated_dir, download_script_name = os.path.split(__file__)

updated_dir_name: str = "update"
updated_dir: str = os.path.join(outdated_dir, updated_dir_name, f"{repo}-{branch}")

config: str = "config.ini"

download_url: str = f"https://github.com/{owner}/{repo}/archive/refs/heads/{branch}.zip"
version_url: str = f"https://api.github.com/repos/{owner}/{repo}/commits?sha={branch}&per_page=1"

package_names: list[str] = ["requests", "flask", "flask_cors"]


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
    import requests  # lazy import for dependency reasons
    response = requests.get(version_url, timeout=10)

    if response.status_code == 200:
        return response.json()[0]['sha']
    else:
        raise RuntimeError("Unable to find the most recent version of the script.")


def download_update():
    """ Download the most recent version of the script and store it as a zip file. """
    import requests  # lazy import for dependency reasons
    print("Script is out of date. Downloading update...")
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
            if file != config or file not in outdated_files:
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
    print("Update successfully installed!")


def update_version_info(version: str):
    """ Update the file storing the script's current version. """
    with open(os.path.join(outdated_dir, version_file), 'w') as file:
        file.write(version)


def install_dependencies():
    for package in package_names:
        # Skip installing if the module is already installed
        if importlib.util.find_spec(package) is not None:
            continue
        else:
            print(f"Package '{package}' not found - attempting to install...")

        try:
            subprocess.run(["pip", "install", package], check=True, capture_output=True)
        except Exception:
            try:
                subprocess.run(["pip3", "install", package], check=True, capture_output=True)
            except Exception:
                try:
                    subprocess.run(["python.exe", "-m", "pip", "install", package], check=True, capture_output=True)
                except Exception as e:
                    raise RuntimeError(f"Unable to install package '{package}' due to an error: {e}")
        print(f"Successfully installed package '{package}'!")


def main():
    print("Checking for updates...")
    install_dependencies()
    should_update, current_version = check_for_update()
    if should_update:
        download_update()
        unzip()
        install_update()
        update_version_info(current_version)
    else:
        print("Script is already up to date!")


if __name__ == "__main__":
    main()