import os
import configparser
import requests
from dataclasses import dataclass
from base64 import b64encode

DEFAULT_LOCKFILE_PATH = "C:/Riot Games/League of Legends/lockfile"


@dataclass
class Lockfile:
    pid: str = ""
    port: str = ""
    password: str = ""
    protocol: str = "https"


class Connection:
    l: Lockfile = Lockfile()
    endpoints = {"gamestate": "/lol-gameflow/v1/gameflow-phase",
                 "start_queue": "/lol-lobby/v2/matchmaking/search",
                 "match_found": "/lol-matchmaking/v1/ready-check",
                 "accept_match": "/lol-matchmaking/v1/ready-check/accept",
                 "champselect_session": "/lol-champ-select/v1/session",
                 "champselect_action": "/lol-champ-select/v1/session/actions/",
                 "owned_champs": "/lol-champions/v1/owned-champions-minimal"}

    def parse_lockfile(self):
        l = self.l
        # Find the lockfile, and parse its contents into a dictionary
        try:
            with open(DEFAULT_LOCKFILE_PATH) as f:
                contents = f.read()
                contents = contents.split(":")
                l.pid = contents[1]
                l.port = contents[2]
                l.password = contents[3]
                l.protocol = contents[4]

        # Can't find file error
        except FileNotFoundError:
            raise FileNotFoundError("Lockfile couldn't be found, did you install league to a non-default directory?")
            # TODO: Get user input for game directory here

        # Handle other exceptions
        except Exception as e:
            raise Exception(f"Failed to parse lockfile: {str(e)}")

    # TODO: Implement these
    def get_gamestate(self):
        return 0

    def accept_match(self):
        return

    def pick_champ(self):
        return

    def ban_champ(self):
        return

    def api_call(self, endpoint):
        l = self.l
        endpoint = self.endpoints.get(endpoint)
        https_auth = f"Basic {b64encode(f"riot:{l.password}".encode()).decode()}"
        headers = {
            "Authorization": https_auth,
            "Accept": "application/json"
        }
        url = f"{l.protocol}://127.0.0.1:{l.port}" + endpoint

    print(l)
