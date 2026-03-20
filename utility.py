from dataclasses import dataclass
import configparser
import warnings
import sys
import os

BASE_DIR = os.path.dirname(__file__)
CFG_PATH = os.path.join(BASE_DIR, "config.ini")
CONFIG_TEMPLATE_PATH = os.path.join(BASE_DIR, "config-template.ini")
LOGFILE_PATH = os.path.join(BASE_DIR, "output.log")

TAB_CHARACTER = "\t"

# Read config
cfg_reader = configparser.ConfigParser()
config_contents = cfg_reader.read(CFG_PATH)

cfg_reader.update()

# Backup config
config_template = configparser.ConfigParser()
config_template_contents = config_template.read(CONFIG_TEMPLATE_PATH)

# Check for empty/missing config
if not config_contents:
    warnings.warn(f"Unable to parse {CFG_PATH} - does it exist? Falling back to default config", RuntimeWarning)
    cfg_reader = config_template


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


def _get_config_option(section: str, option: str, is_bool: bool = False, config=cfg_reader) -> str | bool:
    """
    Get an option from the user's config.
    Args:
        section: the config section to read from
        option: the config option to read from
        is_bool (False): flag indicating whether or not to interpret the config option as a bool
        config (cfg_reader): the config to read from
    """
    try:
        if is_bool:
            return config.getboolean(section, option)
        return config.get(section, option)

    except configparser.NoSectionError as e:
        # Check config template for the section if it doesn't exist in user's config
        if config != config_template:
            return _get_config_option(section, option, is_bool, config=config_template)
        else:
            raise e

    except configparser.NoOptionError as e:
        # Check config template for the option if it doesn't exist in user's config
        if config != config_template:
            return _get_config_option(section, option, is_bool, config=config_template)
        else:
            raise e

    except Exception as e:
        raise type(e)(f"An error occurred while reading {CFG_PATH}: {e}")


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
        picking (True): a flag indicating whether the user is picking (True) or banning (False)
    Returns:
        a list of champion names in order of preference
    """
    champs: list[str] = []
    if len(position) == 0:
        warnings.warn(
            f"Unable to find backup champions - the user wasn't assigned a role",
            RuntimeWarning, stacklevel=2
        )
        return champs

    section_name: str = "pick_" if picking else "ban_"
    section_name += position

    option_index: int = 1
    config_section = cfg_reader[section_name]
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
    with open(LOGFILE_PATH, "a") as file:
        indentation: str = TAB_CHARACTER * kwargs.pop("indentation", 0)
        print(indentation, end="", file=file)
        print(*args, **kwargs, file=file)


def custom_formatwarning(message, *_) -> str:
    """ Create and return a custom warning format, containing only the warning message. """
    formatted_msg: str = f"\tWarning: {message}\n"
    log(formatted_msg)  # don't print the error here because it will be printed anyways
    return formatted_msg


def setup_autoflushing():
    """
    Wrap stdout and stderr in a class that manually flushes the output after every write so that it can be sent
    properly to the web app.
    """

    class AutoFlusher:
        def __init__(self, out):
            self._out = out

        def write(self, text):
            self._out.write(text)
            self._out.flush()

        # Only want to override write - any other method should use default behavior from original
        def __getattr__(self, attr):
            return getattr(self._out, attr)

    sys.stdout = AutoFlusher(sys.stdout)
    sys.stderr = AutoFlusher(sys.stderr)


def clean_exit(err_msg: str = "", exit_code: int = 1):
    """ Terminate the program, with an optional error message and exit code. """
    if err_msg:
        sys.stderr.write(f"{err_msg}\n")
    sys.exit(exit_code)
