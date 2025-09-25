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
    """
    A Class to store information about the Lockfile used to allow access to the LCU API.
    """
    pid: str = ""
    port: str = ""
    password: str = ""
    protocol: str = "https"

def get_config_option_str(section: str, option: str) -> str:
    """
    Get the specified string option from the config file.
    :param section: the config section to read from
    :param option: the option in the config section to read the value of
    """
    return _get_config_option(section, option, False)

def get_config_option_bool(section: str, option: str) -> bool:
    """
    Get the specified bool option from the config file.
    :param section: the config section to read from
    :param option: the option in the config section to read the value of
    """
    return _get_config_option(section, option, True)

def _get_config_option(section: str, option: str, is_bool: bool=False) -> str | bool:
    """
    Get and return the value (str or bool) of a config option from the config file.
    :param section: the config section to read from
    :param option: the option in the config section to read the value of
    :param is_bool: a bool indicating whether to interpret the config option as a bool (True) or as a str (False)
    """
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
    """
    Get the path to the user's lockfile.
    """
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
    """
    Map the League client's gamestate to a more readable format to be displayed to the user, e.g. "None" -> "Main Menu"
    :param gamestate: the gamestate to be displayed
    """
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
    """
    Map the Champselect phase to a more readable format to be displayed to the user, e.g. "BAN_PICK" -> "Pick/Ban"
    :param phase: the phase to be displayed
    """
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
    """
    Parse the user's config for backup champs and return it as a list.
    :param role: the role (position) the user is playing
    :param picking: a bool indicating whether to look for champions to pick (True) or champions to ban (False)
    """
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
    """
    Remove whitespace and illegal characters from a string, and convert it to lowercase.
    :param string: the string to clean
    """
    illegal = (" ", "'", ".")
    new_string = ""
    for char in string:
        if char not in illegal:
            new_string += char.lower()
    return new_string

def capitalize(string: str) -> str:
    """
    Capitalize the first letter in a string and return the result.
    :param string: the string to capitalize
    """
    return string[:1].upper() + string[1:]

def print_and_write(*args: object, **kwargs) -> None:
    """
    Print the input and save it to a log file.
    :param args: the items to print

    Keyword Arguments:
        * `should_print` - a bool indicating whether or not to print the output (if False, only write to file)
    """
    text: str = " ".join(str(arg) for arg in args)

    should_print: bool = kwargs.get("should_print", True)

    if should_print:
        print(text)

    with open("output.log", "a") as file:
        file.write(text + "\n")

def custom_formatwarning(message: str, _category, *_) -> str:
    """
    Create and return a custom warning format, containing only the warning message.
    """
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