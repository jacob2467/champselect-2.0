""" A collection of static utility methods. """
import os
import configparser
from dataclasses import dataclass

# Read config
config = configparser.ConfigParser()
config_contents = config.read("config.ini")

# Check for empty/missing config
if not config_contents:
    raise RuntimeError("Unable to parse config.ini - does it exist?")

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
    if len(role) == 0:
        raise RuntimeError("Unable to find an appropriate champion - no role was specified, " +
                           "and the game didn't assign you a role.")
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
    """ Remove whitespace and illegal characters from a string, and convert it to lowercase. """
    illegal = [" ", "'", "."]
    new_string = ""
    for char in string:
        if char not in illegal:
            new_string += char.lower()
    return new_string


def debugprint(*args: object) -> None:
    """ Print the input, and save it to a log file. """
    temp: str = ""
    for arg in args:
        temp += str(arg) + " "
    print(temp)
    with open("output.log", "a") as file:
        file.write(temp + "\n")


def clean_role_name(prompt: str) -> str:
    """ Convert various role naming conventions to the format used by the game. Example output:
    mid -> middle
    supp -> utility
    jg -> jungle
    """
    name: str = input(prompt)
    if name == "":
        return name
    # Remove all illegal characters and whitespace
    new_name = trim(name)

    roles = [["top", "t"], ["jungle", "jg", "j"], ["middle", "mid", "m"], ["bottom", "bot", "adc", "adcarry", "b"], ["utility", "support", "sup", "supp", "faggot", "fag"]]
    for role in roles:
        if new_name in role:
            return role[0]

    return "invalid"


def get_bool_input(prompt: str, default_answer: bool = False) -> bool:
    """ Get boolean input from the user. """
    response_str: str = input(prompt)
    if response_str == "":
        return default_answer

    response_str = response_str.lower()

    if response_str == "yes" or response_str == "no":
        response_str = response_str[0]

    while response_str != "y" and response_str != "n":
        response_str = input("Invalid input! Please type y or n:  ").lower()

        if response_str == "yes" or response_str == "no":
            response_str = response_str[0]

        if response_str == "y":
            response = True

        if response_str == "n":
            response = False