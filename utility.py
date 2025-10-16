from dataclasses import dataclass
import configparser
import warnings
import os

CONFIG = "config.ini"
LOGFILE = "output.log"

TAB_CHARACTER = '\t'

# Read config
config = configparser.ConfigParser()
config_contents = config.read(CONFIG)

# Check for empty/missing config
if not config_contents:
    raise FileNotFoundError(f"Unable to parse {CONFIG} - does it exist?")


@dataclass
class Lockfile:
    """ A Class to store information about the Lockfile used to allow access to the LCU API. """
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

    except Exception as e:
        raise type(e)(f"An unknown error occurred while reading {CONFIG}: {e}")


def get_lockfile_path() -> str:
    """ Get the path to the user's lockfile. """
    config_dir: str = get_config_option_str("settings", "directory")

    # Use directory specified in config if it exists
    if config_dir:
        return os.path.join(config_dir, "lockfile")

    # If directory not specified in config, use defaults
    # Hardcoding these is fine. More readable than os.path.join(), and I'm handling each OS separately anyways.
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


def get_backup_config_champs(position: str, picking: bool = True) -> list[str]:
    """
    Parse the user's config for backup champs and return it as a list.
    Args:
        position: the position the user is playing
        picking: (optional) a flag indicating whether the user is picking (True) or banning (False)
    """
    champs: list[str] = []
    if len(position) == 0:
        warnings.warn(f"Unable to find backup champions - the user wasn't assigned a role",
                      RuntimeWarning, stacklevel=2)
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


def print_and_write(*args, **kwargs) -> None:
    """ Print the input and save it to the log file. """
    indentation: str = TAB_CHARACTER * kwargs.pop("indentation", 0)
    print(indentation, end="")
    print(*args, **kwargs)
    log(*args, **kwargs)


def log(*args, **kwargs):
    """ Write the input to the log file. """
    with open(LOGFILE, "a") as file:
        indentation: str = TAB_CHARACTER * kwargs.pop("indentation", 0)
        print(indentation, end="", file=file)
        print(*args, **kwargs, file=file)

def custom_formatwarning(message, *_) -> str:
    """ Create and return a custom warning format, containing only the warning message. """
    formatted_msg: str = f"\tWarning: {message}\n"
    log(formatted_msg)  # don't print the error here because it will be printed anyways
    return formatted_msg