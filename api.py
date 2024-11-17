import os
import configparser
from base64 import b64encode
DEFAULT_LOCKFILE_PATH = "C:/Riot Games/League of Legends/lockfile"

def parse_lockfile():
    lockfile = {}

    # Find the lockfile, and parse its contents into a dictionary
    try:
        with open(DEFAULT_LOCKFILE_PATH) as f:
            contents = f.read()
            contents = contents.split(":")
            lockfile["pid"] = contents[1]
            lockfile["port"] = contents[2]
            lockfile["password"] = contents[3]
            lockfile["protocol"] = contents[4]

    # Can't find file error
    except FileNotFoundError:
        raise FileNotFoundError("Lockfile couldn't be found, did you install league to a non-default directory?")
        # TODO: Get user input for game directory here

    # Handle other exceptions
    except Exception as e:
        raise Exception(f"Failed to parse lockfile: {str(e)}")

    return lockfile


def get_gamestate():
    return 0  # TODO: Implement this


def accept_match():
    return


def pick_champ():
    return


def ban_champ():
    return

lockfile = parse_lockfile()
https_auth = f"Basic {b64encode(f"riot:{lockfile["password"]}".encode()).decode()}"

url = f"{lockfile["protocol"]}://127.0.0.1{lockfile["port"]}"

print(lockfile)