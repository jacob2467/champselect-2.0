import os
import configparser
from dataclasses import dataclass

# Read config
config = configparser.ConfigParser()
config.read("config.ini")

@dataclass
class Lockfile:
    pid: str = ""
    port: str = ""
    password: str = ""
    protocol: str = "https"


def get_lockfile_path() -> str:
    """ Get the path to the user's lockfile. """
    config_dir = config.get("league_directory", "directory")

    # Use directory specified in config if it exists
    if config_dir != "":
        dir = config_dir
    else:  # Use default filepaths
        osx = "/Applications/League of Legends.app/Contents/LoL/lockfile"
        windows = "C:/Riot Games/League of Legends/lockfile"

        match os.name:
            case "nt":
                dir = windows
            case "posix":
                dir = osx

    return dir


def parse_config(role: str, picking: bool = True) -> list[str]:
    """ Parse the user's config for backup champs and return it as a dictionary"""
    champs = []
    if picking:
        config_section = "pick"
    else:
        config_section = "ban"

    config_section += "_" + role

    for i in range(5):
        champs.append(config.get(config_section, str(i + 1)))
    return champs


def trim(string: str) -> str:
    """ Remove whitespace and illegal characters from a string. """
    illegal = [" ", "'", "."]
    new_string = ""
    for char in string:
        if char not in illegal:
            new_string += char.lower()
    return new_string


def debugprint(*args):
    """ Functions exactly like print; only difference is the name. Useful for differentiating between
    regular prints and ones intended for debugging. """
    temp: str = ""
    for arg in args:
        temp += str(arg) + " "
    print(temp)


def clean_role_name(name: str) -> str:
    """ Convert various role naming conventions to the format used by the game. Example output:
    mid -> middle
    supp -> utility
    jg -> jungle
    """
    if name == "":
        return name
    # Remove all illegal characters and whitespace
    new_name = trim(name)

    roles = [["top", "t"], ["jungle", "jg", "j"], ["middle", "mid", "m"], ["bottom", "bot", "adc", "adcarry", "b"], ["utility", "support", "supp", "faggot", "fag"]]
    for role in roles:
        if new_name in role:
            return role[0]

    raise Exception("Invalid role selection. Please try again")