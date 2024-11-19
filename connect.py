import os
import configparser
import time

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
    """ Get the path to the user's lockfile. """
    # Default path for Windows
    if os.name == "nt":
        return "C:/Riot Games/League of Legends/lockfile"

    # Default path for OSX
    elif os.name == "posix":
        return "/Applications/League of Legends.app/Contents/LoL/lockfile"


class Connection:
    l: Lockfile = Lockfile()
    has_picked: bool = False
    has_banned: bool = False
    has_hovered: bool = False
    endpoints: dict = {}
    all_champs: dict = {}
    owned_champs: dict = {}
    bannable_champids: list = []
    ban_action: dict = {}
    pick_action: dict = {}
    pick_choice: str = ""
    ban_choice: str = ""
    role_choice: str = ""


    def __init__(self):
        self.parse_lockfile()
        self.setup_endpoints()
        self.populate_champ_table()
        self.get_first_choices()

    # ----------------
    # Connection Setup
    # ----------------
    def parse_lockfile(self):
        """ Find the user's lockfile, and parse it into a dictionary. """
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
            raise FileNotFoundError("Lockfile not found; open league, or specify your installation directory")
            # TODO: Get user input for game directory here

        # Handle other exceptions
        except Exception as e:
            raise Exception(f"Failed to parse lockfile: {str(e)}")


    def setup_endpoints(self):
        """ Set up a dictionary containing varius endpoints for the API. """
        self.endpoints = {
            "gamestate": "/lol-gameflow/v1/gameflow-phase",  # GET
            "start_queue": "/lol-lobby/v2/lobby/matchmaking/search",  # POST
            "match_found": "/lol-matchmaking/v1/ready-check",  # GET
            "accept_match": "/lol-matchmaking/v1/ready-check/accept",  # POST
            "champselect_session": "/lol-champ-select/v1/session",  # GET
            "champselect_action": "/lol-champ-select/v1/session/actions/",  # PATCH
            # "champselect_action2": "/lol-lobby-team-builder/champ-select/v1/session/actions/",  # PATCH
            "owned_champs": "/lol-champions/v1/owned-champions-minimal",  # GET
            "current_summoner": "/lol-summoner/v1/current-summoner",  # GET
            "all_champs": f"/lol-champions/v1/inventories/{self.get_summoner_id()}/champions",  # GET
            "pickable_champs": "/lol-champ-select/v1/pickable-champions",  # GET
            "bannable_champs": "/lol-champ-select/v1/bannable-champion-ids"  # GET
        }


    def populate_champ_table(self):
        """ Get a list of all champions in the game and another of all that the player owns, and store them
        in a dictionary along with their id numbers.
        """
        all_champs = self.api_get("all_champs")
        error = False
        for champ in all_champs.json():
            try:
                alias, id = self.clean_name(champ["alias"]), champ["id"]
                self.all_champs[alias] = id
            except Exception:
                print("Champ data couldn't be retrieved, falling back to only using data for owned champs...")
                error = True
                break

        if error:
            all_champs = self.api_get("owned_champs")
            for champ in all_champs.json():
                try:
                    alias, id = self.clean_name(champ["alias"]), champ["id"]
                    self.all_champs[alias] = id
                except Exception:
                    raise Exception("Champion data has not yet been received.")

        owned_champs = self.api_get("owned_champs").json()
        for champ in owned_champs:
            alias, id = self.clean_name(champ["alias"]), champ["id"]
            self.owned_champs[alias] = id

    def get_first_choices(self):
        """ Get the user's first choice for picks and bans, as well as the role they're playing"""
        # TODO:
        #  - Check for autofill
        #  - Check if user owns champ
        #  - Get role from API rather than user input
        self.pick_choice = "senna"
        self.ban_choice = "pyke"
        self.role_choice = "bottom"
        # self.pick_choice = self.cleanup_name(input("Who would you like to play?  "))
        # self.ban_choice = self.cleanup_name(input("Who would you like to ban?  "))

    # --------------
    # Helper methods
    # --------------
    def reset_after_dodge(self):
        """ Reset has_picked, has_banned, and has_hovered to False after someone dodges a lobby. """
        self.has_picked = False
        self.has_banned = False
        self.has_hovered = False


    def decide_champ(self):
        """ Decide what champ the user should play. """
        # TODO: Ensure user can pick the champ (is owned, and is not banned or taken)
        pick = self.pick_choice
        if pick not in self.owned_champs:
            # TODO: Parse config here
            pick = "jinx"
        champid = self.get_champid(pick)
        return champid


    def decide_ban(self):
        """ Decide what champ the user should ban. """
        # TODO: Make sure teammates aren't hovering the champ
        ban = self.ban_choice
        champid = self.get_champid(ban)
        return champid

    @staticmethod
    def clean_name(name):
        """ Remove whitespace and special characters from a champion's name. Example output:
        Aurelion Sol -> aurelionsol
        Bel'Veth -> belveth
        """
        # Trim illegal characters & whitespace
        illegal = [" ", "'", "."]
        new_name = ""
        for char in name:
            if char not in illegal:
                new_name += char.lower()

        # Handle edge cases (Nunu and Willump -> nunu and Wukong -> monkeyking)
        if "nunu" in new_name:
            return "nunu"
        elif new_name == "wukong":
            return "monkeyking"

        return new_name


    # ----------------
    # API Call Methods
    # ----------------


    def accept_match(self):
        """ Accept a match. """
        self.api_post("accept_match")


    def ban_or_pick(self):
        """ Handle logic of whether to pick or ban, and then call the corresponding method. """
        if self.pick_action.get("isInProgress", False):
            print("pick action:", self.pick_action, "\n")
            self.lock_champ()
        elif self.ban_action.get("isInProgress", False):
            print("ban action:", self.ban_action, "\n")
            self.ban_champ()



    def ban_champ(self, champid=None):
        """ Ban a champion. """
        if not self.has_banned:
            self.do_champ(mode="ban", champid=champid)


    def lock_champ(self, champid=None):
        """ Lock in a champion. """
        self.hover_champ()
        if not self.has_picked:
            self.do_champ(mode="pick", champid=champid)


    def hover_champ(self, champid=None):
        """ Hover in a champion. """
        if not self.has_hovered:
            self.do_champ(mode="hover", champid=champid)


    def do_champ(self, **kwargs):
        """ Pick or ban a champ in champselect.

        Keyword arguments:
        champid -- the champ to pick/ban (optional)
        mode -- options are hover, ban, and pick
        """
        champid = kwargs.get("champid")
        mode = kwargs.get("mode")

        # If champid wasn't specified in method call, find out what champ to pick
        if champid is None:
            if mode == "ban":
                champid = self.decide_ban()
            else:
                champid = self.decide_champ()

        # Set up http request
        data = {"championId": champid}  # , "completed": mode != "hover"}
        if mode == "ban":
            actionid = self.ban_action["id"]
        else:
            actionid = self.pick_action["id"]
        endpoint = self.endpoints["champselect_action"] + str(actionid)
        if mode != "hover":
            api_method = self.api_post
            self.api_patch(endpoint, data=data)
            endpoint += "/complete"
        else:
            api_method = self.api_patch

        # Debug print
        # print(f"champid: {champid}, actionid: {actionid}")

        # Lock in the champ and print info
        print(f"endpoint: {endpoint}")
        response = api_method(endpoint, data=data)
        print(response, "\n")
        try:
            print(response.json())
        except:
            print("Failed to parse response as json, the response is empty.")
        print(type(response.status_code))
        if 200 <= response.status_code <= 299:
            match mode:
                case "hover":
                    self.has_hovered = True
                case "ban":
                    self.has_banned = True
                case "pick":
                    self.has_picked = True
        # self.has_banned = False


    def api_get(self, endpoint):
        """ Send an API GET request. """
        return self.api_call(endpoint, "get")


    def api_post(self, endpoint, data=None):
        """ Send an API POST request. """
        return self.api_call(endpoint, "post", data)


    def api_patch(self, endpoint, data=None):
        """ Send an API PATCH request. """
        return self.api_call(endpoint, "patch", data)


    def api_call(self, endpoint, method, data=None):
        """ Make an API call with the specified endpoint and method. """
        # Check if endpoint alias from parameter is in dictionary; if not, use endpoint parameter as the full endpoint
        endpoint = self.endpoints.get(endpoint, endpoint)

        # Set up request URL
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
        return request(url, headers=headers, json=data, verify=False)


    # --------------
    # Getter methods
    # --------------
    def get_session(self):
        return self.api_get("champselect_session").json()


    def get_assigned_role(self):
        # TODO: Implement this
        return


    def get_champid(self, champ):
        return self.all_champs[self.clean_name(champ)]

    def get_gamestate(self):
        return self.api_get("gamestate")


    def get_localcellid(self):
        return self.get_session()["localPlayerCellId"]


    def get_request_url(self, endpoint):
        l = self.l
        https_auth = f"Basic {b64encode(f"riot:{l.password}".encode()).decode()}"
        headers = {
            "Authorization": https_auth,
            "Accept": "application/json"
        }
        url = f"{l.protocol}://127.0.0.1:{l.port}" + endpoint
        return url, headers

    def get_summoner_id(self):
        return self.api_get("/lol-summoner/v1/current-summoner").json()["accountId"]

    def update_actions(self):
        """ Get the champselect action corresponding to the local player, and return it. """
        session = self.get_session()
        actions = session["actions"]
        # print("actions:", actions, "\n")
        local_cellid = self.get_localcellid()

        # Look at each action, and return the one with the corresponding cellid
        for action_group in actions:
            for action in action_group:
                if action["actorCellId"] == local_cellid:
                    if action["type"] == "ban":
                        self.ban_action = action
                    elif action["type"] == "pick":
                        self.pick_action = action