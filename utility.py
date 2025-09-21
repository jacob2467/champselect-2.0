""" A collection of static utility methods. """
import os
import configparser
import warnings
from dataclasses import dataclass

config_name = "config.ini"

# Read config
config = configparser.ConfigParser()
config_contents = config.read(config_name)

# Check for empty/missing config
if not config_contents:
    raise RuntimeError(f"Unable to parse {config_name} - does it exist?")

@dataclass
class Lockfile:
    pid: str = ""
    port: str = ""
    password: str = ""
    protocol: str = "https"

def get_config_option_str(section: str, option: str) -> str:
    """ Get the specified string option from the config file. """
    return _get_config_option(section, option, False) # type: ignore

def get_config_option_bool(section: str, option: str) -> bool:
    """ Get the specified bool option from the config file. """
    return _get_config_option(section, option, True) # type: ignore

def _get_config_option(section: str, option: str, is_bool: bool = False) -> str | bool:
    """ Get and return the value (str or bool) of a config option from the config file. """
    try:
        value: str | bool
        if is_bool:
            value = config.getboolean(section, option)
        else:
            value = config.get(section, option)
        return value

    except configparser.NoSectionError as e:
        raise RuntimeError(f"Invalid config section '{section}': {e}")
    except configparser.NoOptionError as e:
        raise RuntimeError(f"Invalid config option '{option}': {e}")

    except Exception as e:
        raise RuntimeError(f"An unknown error occurred while reading {config_name}: {e}")

def get_lockfile_path() -> str:
    """ Get the path to the user's lockfile. """
    config_dir: str = get_config_option_str("settings", "directory")

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

def map_gamestate_for_display(gamestate: str) -> str:
    match gamestate:
        case "None":
            return "Main Menu"
        case "Matchmaking":
            return "In Queue"
        case "ReadyCheck":
            return "Ready Check"
        case "ChampSelect":
            return "Champselect"
        case "FINALIZATION":
            return "Champselect"
        case default:
            return gamestate

def map_phase_for_display(phase: str) -> str:
    match phase:
        case "PLANNING":
            return "Planning"
        case "BAN_PICK":
            return "Pick/Ban"
        case "FINALIZATION":
            return "Loadout Selection"
        case default:
            return "None"

def get_backup_config_champs(role: str, picking: bool = True) -> list[str]:
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


def clean_string(string: str) -> str:
    """ Remove whitespace and illegal characters from a string, and convert it to lowercase. """
    illegal = (" ", "'", ".")
    new_string = ""
    for char in string:
        if char not in illegal:
            new_string += char.lower()
    return new_string

def capitalize_first(string: str) -> str:
    """ Capitalize the first letter in a string and return the result. """
    return string[0].upper() + string[1:]

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
    clean_name = clean_string(name)

    roles = [("top", "t"), ("jungle", "jg", "j"), ("middle", "mid", "m"),
             ("bottom", "bot", "adc", "adcarry", "b"), ("utility", "support", "sup", "supp")]

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

def custom_formatwarning(message, category, *_) -> str:
    """ Create and return a custom warning format, containing only the warning message. """
    formatted_msg: str = f"\tWarning: {message}\n"
    print_and_write(formatted_msg, should_print=False)  # don't print the error here because it will be printed anyways
    return formatted_msg

def clean_name(all_champs: dict[str, int], name: str, should_filter=True) -> str:
    """ Remove whitespace and special characters from a champion's name. Example output:
    Aurelion Sol -> aurelionsol
    Bel'Veth -> belveth
    :param all_champs: champions that have already been processed
    :param name: the name to clean
    :param should_filter: if True, return "invalid" when an invalid champion name is passed
    """
    if name == "":
        return name
    # Remove all illegal characters and whitespace
    name = clean_string(name)

    # Handle edge cases (Nunu and Willump -> nunu and Wukong -> monkeyking)
    if "nunu" in name:
        return "nunu"
    elif name == "wukong":
        return "monkeyking"

    # Filter out invalid resulting names
    if should_filter:
        if name in all_champs:
            return name
        return "invalid"
    return name