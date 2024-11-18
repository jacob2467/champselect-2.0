import os
import time
import configparser
import requests
from dataclasses import dataclass
from base64 import b64encode
import warnings
from urllib3.exceptions import InsecureRequestWarning

# Disable warning for insecure http requests
warnings.simplefilter('ignore', InsecureRequestWarning)


@dataclass
class Lockfile:
    pid: str = ""
    port: str = ""
    password: str = ""
    protocol: str = "https"


def get_lockfile_path():
    # Default path for Windows
    if os.name == "nt":
        return "C:/Riot Games/League of Legends/lockfile"

    # Default path for OSX
    elif os.name == "posix":
        return "/Applications/League of Legends.app/Contents/LoL/lockfile"


class Connection:
    l: Lockfile = Lockfile()
    endpoints = {"gamestate": "/lol-gameflow/v1/gameflow-phase",
                 "start_queue": "/lol-lobby/v2/lobby/matchmaking/search",
                 "match_found": "/lol-matchmaking/v1/ready-check",
                 "accept_match": "/lol-matchmaking/v1/ready-check/accept",
                 "champselect_session": "/lol-champ-select/v1/session",
                 "champselect_action": "/lol-champ-select/v1/session/actions/",
                 "owned_champs": "/lol-champions/v1/owned-champions-minimal"
                 }
    has_picked = False
    has_banned = False
    placeholder_pick = 103
    placeholder_ban = 104


    def __init__(self):
        self.parse_lockfile()


    def parse_lockfile(self):
        l = self.l
        # Find the lockfile, and parse its contents into a dictionary
        path = get_lockfile_path()
        try:
            with open(path) as f:
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


    def reset_after_dodge(self):
        self.has_picked = False
        self.has_banned = False


    def find_champ(self):
        return self.placeholder_pick  # TODO: replace dummy value


    def find_ban(self):
        return self.placeholder_ban  # TODO: replace dummy value


    def get_gamestate(self):
        return self.api_get("gamestate")


    def accept_match(self):
        self.api_post("accept_match")


    def do_champ(self, **kwargs):
        champid = kwargs.get("champid")
        banning = kwargs.get("banning")

        # If champid wasn't specified in method call, find out what champ to pick
        if champid is None:
            if banning:
                champid = self.find_ban()
            else:
                champid = self.find_champ()


        # Set up http request
        data = {"championId": champid, "completed": True}
        id = self.api_get("champselect_session")["actions"][0][0]["id"]

        # Lock in the champ and print info
        print(self.api_patch("champselect_action", data=data, actionid=id))

    def ban_champ(self, champid=None):
        self.do_champ(banning=True, champid=champid)

    def lock_champ(self, champid=None):
        self.do_champ(banning=False, champid=champid)

    def api_get(self, endpoint):
        return self.api_call(endpoint, "get")

    def api_post(self, endpoint, data=None, actionid=None):
        return self.api_call(endpoint, "post", data, actionid)

    def api_patch(self, endpoint, data=None, actionid=None):
        return self.api_call(endpoint, "patch", data, actionid)

    def api_call(self, endpoint, method, data=None, actionid=None):
        """ Make an API call with the specified endpoint and method.
        """
        # Set up endpoint
        endpoint = self.endpoints.get(endpoint)

        # Append actionid to endpoint if it was specified, otherwise no action is being taken
        if actionid is not None:
            actionid = str(actionid)
            endpoint += actionid

        url, headers = self.get_request_url(endpoint)

        # Choose proper http method
        match method:
            case "get":
                request = requests.get
            case "post":
                request = requests.post
            case "patch":
                request = requests.patch

        # Send the request
        try:
            return request(url, headers=headers, json=data, verify=False).json()
        except requests.exceptions.JSONDecodeError:
            return None


    def get_request_url(self, endpoint):
        l = self.l
        https_auth = f"Basic {b64encode(f"riot:{l.password}".encode()).decode()}"
        headers = {
            "Authorization": https_auth,
            "Accept": "application/json"
        }
        url = f"{l.protocol}://127.0.0.1:{l.port}" + endpoint
        return url, headers



c = Connection()
in_game = False
last_action = None
last_gamestate = None

while not in_game:
    time.sleep(1)
    gamestate = c.api_get("gamestate")

    match gamestate:
        case "Lobby":
            c.reset_after_dodge()

        case "ReadyCheck":
            c.reset_after_dodge()
            c.accept_match()

        case "ChampSelect":
            action = c.api_get("champselect_session")["actions"][0][0]["type"]
            print(f"Current champselect phase: {action}")

            match action:
                case "pick":
                    if not c.has_picked:
                        c.lock_champ()
                case "ban":
                    if not c.has_banned:
                        c.ban_champ()
                case default:
                    pass

            # Print current action, only if it's different from the last one
            if action != last_action:
                print(action)
            last_action = action

        # End loop if a game starts
        case "InProgress":
            in_game = True

        case default:
            # Print current gamestate, only if it's different from the last one
            if gamestate != last_gamestate:
                print(gamestate)

    last_gamestate = gamestate