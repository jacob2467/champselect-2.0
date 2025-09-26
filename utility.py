from dataclasses import dataclass
import configparser
import warnings
import sys
import os

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
    Get an option from the user's config.
    Args:
        section: the config section to read from
        option: the config option to read from
    """
    return _get_config_option(section, option, False)


def get_config_option_bool(section: str, option: str) -> bool:
    """
    Get an option from the user's config.
    Args:
        section: the config section to read from
        option: the config option to read from
    """
    return _get_config_option(section, option, True)


def _get_config_option(section: str, option: str, is_bool: bool = False) -> str | bool:
    """
    Get an option from the user's config.
    Args:
        section: the config section to read from
        option: the config option to read from
        is_bool: flag indicating whether or not to interpret the config option as a bool
    """
    try:
        if is_bool:
            return config.getboolean(section, option)

        return config.get(section, option)

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
    if config_dir:
        return config_dir

    # If directory not specified in config, use defaults
    osx = "/Applications/League of Legends.app/Contents/LoL/lockfile"
    windows = "C:\\Riot Games\\League of Legends\\lockfile"
    # league can't be played on linux anymore because rito

    match os.name:
        case "nt":
            return windows
        case "posix":
            return osx
        case _:
            raise RuntimeError("Unsupported OS")


def map_gamestate_for_display(gamestate: str) -> str:
    """ Map the League client's gamestate to a more readable format to be displayed to the user, e.g. "None" -> "Main Menu" """
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
        case _:
            return gamestate


def map_phase_for_display(phase: str) -> str:
    """ Map the Champselect phase to a more readable format to be displayed to the user, e.g. "BAN_PICK" -> "Pick/Ban" """
    match phase:
        case "PLANNING":
            return "Planning"
        case "BAN_PICK":
            return "Pick/Ban"
        case "FINALIZATION":
            return "Loadout Selection"
        case _:
            return "None"


def get_backup_config_champs(position: str, picking: bool = True) -> list[str]:
    """
    Parse the user's config for backup champs and return it as a list.
    Args:
        position: the position the user is playing
        picking: (optional) a flag indicating whether the user is picking (True) or banning (False)
    """
    champs: list[str] = []
    if len(position) == 0:
        warnings.warn(f"Unable to find backup champions - the user wasn't assigned a role", RuntimeWarning)
        return champs

    section_name: str = "pick" if picking else "ban"
    section_name += f"_{position}"

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
    """ Capitalize the first letter in a string. """
    return string[:1].upper() + string[1:]


def print_and_write(*args: object, should_print: bool = True) -> None:
    """ Print the input and save it to a log file. """
    text: str = " ".join(str(arg) for arg in args)

    if should_print:
        print(text)

    with open("output.log", "a") as file:
        file.write(text + "\n")


def custom_formatwarning(message, *_) -> str:
    """ Create and return a custom warning format, containing only the warning message. """
    formatted_msg: str = f"\tWarning: {message}\n"
    print_and_write(formatted_msg, should_print=False)  # don't print the error here because it will be printed anyways
    return formatted_msg


def clean_name(all_champs: dict[str, int], name: str, should_filter: bool = True) -> str:
    """
    Remove whitespace and special characters from a champion's name.
    Example output:
        Aurelion Sol -> aurelionsol
        Bel'Veth -> belveth

    Args:
        all_champs: champions that have already been processed
        name: the name to clean
        should_filter: if True, return "invalid" when an invalid champion name is passed
    """
    if not name:
        return name
    # Remove all illegal characters and whitespace
    name = clean_string(name)

    # Handle edge cases (Nunu and Willump -> nunu and Wukong -> monkeyking)
    if "nunu" in name:
        return "nunu"
    elif name == "wukong":
        return "monkeyking"

    if not should_filter:
        return name

    # Filter out invalid resulting names
    return name if name in all_champs else "invalid"


def exit_with_error(err_msg: str, exitcode: int = 1) -> None:
    """ Exit the program with the specified error message. """
    sys.stderr.write(err_msg)
    sys.exit(exitcode)
