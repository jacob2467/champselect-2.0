""" A collection of static utility methods. """
import os
import configparser
import warnings
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
        windows = "C:\\Riot Games\\League of Legends\\lockfile"
        # league can't be played on linux anymore because rito

        match os.name:
            case "nt":
                dir = windows
            case "posix":
                dir = osx

    return dir


def parse_config(role: str, picking: bool = True) -> list[str]:
    """ Parse the user's config for backup champs and return it as a list. """
    champs: list[str] = []
    if len(role) == 0:
        warnings.warn(f"Unable to find backup champions - the user wasn't assigned a role", RuntimeWarning)
        return champs

    section_name: str = "pick" if picking else "ban"
    section_name += f"_{role}"

    option_index: int = 1
    config_section = config[section_name]
    champ_name: str = config_section.get(str(option_index), "none")

    while champ_name != "none":
        champs.append(champ_name)
        option_index += 1
        champ_name = config_section.get(str(option_index), "none")
    return champs


def trim(string: str) -> str:
    """ Remove whitespace and illegal characters from a string, and convert it to lowercase. """
    illegal = [" ", "'", "."]
    new_string = ""
    for char in string:
        if char not in illegal:
            new_string += char.lower()
    return new_string


def print_and_write(*args: object, **kwargs) -> None:
    """ Print the input and save it to a log file. """
    text: str = " ".join(str(arg) for arg in args)

    should_print: bool = kwargs.get("should_print", True)

    if should_print:
        print(text)

    with open("output.log", "a") as file:
        file.write(text + "\n")


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
    clean_name = trim(name)

    roles = [["top", "t"], ["jungle", "jg", "j"], ["middle", "mid", "m"],
             ["bottom", "bot", "adc", "adcarry", "b"], ["utility", "support", "sup", "supp"]]
    for role in roles:
        if clean_name in role:
            return role[0]

    return "invalid"


def get_bool_input(prompt: str, default_answer: bool = False) -> bool:
    """ Get boolean input from the user. """
    response_str: str = ""
    while response_str not in ("y", "n"):
        response_str = input(prompt).lower()

        # Return default answer if user didn't answer
        if response_str == "":
            return default_answer

        # Normalize "yes" to "y", "no" to "n"
        if response_str in ("yes", "no"):
            response_str = response_str[0]

        # Change prompt after first loop
        prompt = "Invalid input! Please type y or n:  "

    # After the while loop, response_str is guaranteed to either be "y" or "n"
    return response_str == "y"

def custom_formatwarning(message, category, *_):
    """ Create and return a custom warning format, containing only the warning message. """
    formatted_msg: str = f"\tWarning: {message}\n"
    print_and_write(formatted_msg, should_print=False)  # don't print the error here because it will be printed anyways
    return formatted_msg