import requests
import zipfile
import os

owner: str = "jacob2467"
repo: str = "champselect-2.0"
version_file: str = "version.txt"
update_zip: str = "update.zip"
out_dir: str = "update"

config: str = "config.ini"
download_script: str = __file__.split("/")[-1]

download_url: str = f"https://github.com/{owner}/{repo}/archive/refs/heads/main.zip"
version_url: str = f"https://api.github.com/repos/{owner}/{repo}/commits?per_page=1"

def get_version():
    response = requests.get(version_url)

    if response.status_code == 200:
        return response.json()[0]['sha']

def download_update():
    response = requests.get(download_url)
    with open(update_zip, "wb") as file:
        file.write(response.content)

def unzip():
    update = zipfile.ZipFile(update_zip)

    os.makedirs(out_dir, exist_ok=True)

    for file in update.filelist:
        try:
            new_path = os.path.join(out_dir, file.filename.split("/")[-1])
            with open(new_path, "wb") as outfile:
                outfile.write(update.read(file.filename))
        except IsADirectoryError:
            pass

def copy_update():
    # let me cook
    dir = os.path.join("/", *(__file__.split("/")[:-1]), "")
    file_list = os.listdir(dir)
    print(file_list)

def main():
    version = get_version()

    with open(version_file, "r") as file:
        old_version = file.read()
        should_update: bool = version != old_version

    with open(version_file, "w") as file:
        file.write(version)

    if should_update:
        pass  # TODO: something here, idk

if __name__ == "__main__":
    main()
    download_update()
    unzip()
    copy_update()