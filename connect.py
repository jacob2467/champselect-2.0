# These libraries are included with Python or are part of this project, and therefore don't require installation
import os
import configparser
from dataclasses import dataclass
from base64 import b64encode
import warnings
import dependencies as d

# These libraries need to be installed, but urllib3 is a dependency of requests, so we only need to install requests
try:
    import requests
except ModuleNotFoundError:
    d.install("requests")
    import requests
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
    config_dir = config.get("league_directory", "directory")

    # Use directory specified in config if it exists
    if config_dir != "":
        dir = config_dir
    else:  # Use default filepaths
        osx = "/Applications/League of Legends.app/Contents/LoL/lockfile"
        windows = "C:/Riot Games/League of Legends/lockfile"

        match os.name:
            case "nt":
                dir = windows
            case "posix":
                dir = osx

    return dir


config = configparser.ConfigParser()
config.read("config.ini")


def parse_config(role: str, picking: bool = True):
    """ Parse the user's config for backup champs and return it as a dictionary"""
    champs = []
    config_section = ""
    if picking:
        config_section += "pick"
    else:
        config_section += "ban"

    config_section += "_" + role

    for i in range(5):
        champs.append(config.get(config_section, str(i + 1)))
    return champs

def trim(string: str):
    illegal = [" ", "'", "."]
    new_string = ""
    for char in string:
        if char not in illegal:
            new_string += char.lower()
    return new_string



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
    all_actions: dict = {}
    user_pick: str = ""
    user_ban: str = ""
    pick_intent: str = ""
    ban_intent: str = ""
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
        """ Parse the user's lockfile into a dictionary. """
        l = self.l
        path = get_lockfile_path()
        try:
            with open(path) as f:
                contents = f.read()
                contents = contents.split(":")
                l.pid, l.port, l.password, l.protocol = contents[1:5]

        # Can't find file error
        except FileNotFoundError:
            raise FileNotFoundError("Lockfile not found; open league, or specify your installation"
                                    "directory in your config")

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
        all_champs = self.api_get("all_champs").json()
        error = False
        for champ in all_champs:
            try:
                alias, id = self.clean_name(champ["alias"]), champ["id"]
                self.all_champs[alias] = id
            except Exception:
                warnings.warn("Champ data couldn't be retrieved, falling back to only"
                              "using data for owned champs...", RuntimeWarning)
                error = True

        if error:
            all_champs = self.api_get("owned_champs")
            for champ in all_champs:
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
        self.user_pick = self.clean_name(input("Who would you like to play?  "))
        self.user_ban = self.clean_name(input("Who would you like to ban?  "))
        # Set intent to userinput (intent can change later if first choice is banned, etc.)
        self.pick_intent = self.user_pick
        self.ban_intent = self.user_ban
        self.role_choice = self.clean_role_name(input("What role would you like to play?  "))

    # --------------
    # Helper methods
    # --------------
    def reset_after_dodge(self):
        """ Reset has_picked, has_banned, and has_hovered to False after someone dodges a lobby. """
        self.has_picked = False
        self.has_banned = False
        self.has_hovered = False


    def decide_pick(self):
        """ Decide what champ the user should play. """
        pick = self.pick_intent
        if self.is_valid_pick(pick):
            return self.get_champid(pick)
        else:
            options = parse_config(self.role_choice)

        i = 0
        is_valid = False
        while not is_valid and i < len(options):
            pick = options[i]
            is_valid = self.is_valid_pick(pick)
            i += 1
        self.pick_intent = pick
        return self.get_champid(pick)


    def decide_ban(self):
        """ Decide what champ the user should ban. """
        ban = self.ban_intent
        if self.is_valid_ban(ban):
            return self.get_champid(ban)
        else:
            options = parse_config(self.role_choice, False)

        i = 0
        is_valid = False
        while not is_valid and i < len(options):
            ban = options[i]
            is_valid = self.is_valid_ban(ban)
            i += 1
        self.ban_intent = ban
        return self.get_champid(ban)


    def is_valid_pick(self, champ: str):
        champ = self.clean_name(champ)
        id = self.get_champid(champ)

        # If user doesn't own the champ
        if champ not in self.owned_champs:
            return False

        # If champ is banned
        if id in self.get_banned_champids():
            return False

        # If a teammate has already PICKED the champ (hovers ok, stealing champs is based)
        if id in self.get_teammate_picks():
            return False

        # If the user got assigned a role other than the one they queued for
        if self.get_assigned_role() == "" or self.role_choice != self.get_assigned_role():
            print(f"Role choice: {self.role_choice}, assigned role: {self.get_assigned_role()}")
            return False
        return True


    def is_valid_ban(self, champ: str):
        champ = self.clean_name(champ)
        id = self.get_champid(champ)
        # If champ is banned already
        if id in self.get_banned_champids():
            return False

        # If a teammate is hovering the champ
        if self.teammate_hovering(id):
            return False

        return True


    def get_teammate_champids(self):
        champids = []
        hovering = False
        for action in self.all_actions:
            id = action["championId"]
            if action["isAllyAction"] and action["type"] == "pick" and id != 0:
                if action["isInProgress"]:
                    hovering = True
                champids.append((id, hovering))
        return champids

    def get_teammate_picks(self):
        champs = []
        for pick, is_hovering in self.get_teammate_champids():
            if not is_hovering:
                champs.append(pick)
        return champs


    def get_teammate_hovers(self):
        champids = []
        for pick, is_hovering in self.get_teammate_champids():
            if is_hovering:
                champids.append(pick)
        return champids


    def send_runes(self):
        # TODO: Implement this
        return


    def send_summs(self):
        # TODO: Implement this
        return


    def get_banned_champids(self):
        session = self.get_session()
        bans = session["bans"]["myTeamBans"] + session["bans"]["theirTeamBans"]
        return bans


    def is_banned(self, champname):
        return self.all_champs[champname] in self.get_banned_champids()


    def check_role(self):
        # TODO: Get primary role the user is queueing for instead of getting it as user input
        a = self
        return "top"


    def teammate_hovering(self, champid: int):
        return champid in self.get_teammate_hovers()


    @staticmethod
    def clean_name(name: str):
        """ Remove whitespace and special characters from a champion's name. Example output:
        Aurelion Sol -> aurelionsol
        Bel'Veth -> belveth
        """
        # Remove all illegal characters and whitespace
        new_name = trim(name)

        # Handle edge cases (Nunu and Willump -> nunu and Wukong -> monkeyking)
        if "nunu" in new_name:
            return "nunu"
        elif new_name == "wukong":
            return "monkeyking"

        return new_name


    @staticmethod
    def clean_role_name(name: str):
        # Remove all illegal characters and whitespace
        new_name = trim(name)

        roles = [["top", "t"], ["jungle", "jg", "j"], ["middle", "mid", "m"], ["bottom", "bot", "adc", "adcarry", "b"], ["support", "supp", "faggot", "fag"]]
        for role in roles:
            if new_name in role:
                return role[0]

        raise Exception("Invalid role selection. Please try again")


    # ----------------
    # API Call Methods
    # ----------------


    def accept_match(self):
        """ Accept a match. """
        self.api_post("accept_match")


    def ban_or_pick(self):
        """ Handle logic of whether to pick or ban, and then call the corresponding method. """
        if self.pick_action.get("isInProgress", False):
            # print("pick action:", self.pick_action, "\n")
            self.lock_champ()
        elif self.ban_action.get("isInProgress", False):
            # print("ban action:", self.ban_action, "\n")
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
        """ Hover a champion. """
        if not self.is_hovering() and not self.has_hovered:
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
                champid = self.decide_pick()

        # Set up http request
        data = {"championId": champid}
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

        # Lock in the champ and print info
        # print(f"endpoint: {endpoint}")
        response = api_method(endpoint, data=data)
        # print(response, "\n")
        try:
            print(response.json())
        except:
            print("Failed to parse response as json, the response is empty.")
        if 200 <= response.status_code <= 299:
            match mode:
                case "hover":
                    self.has_hovered = True
                case "ban":
                    self.has_banned = True
                case "pick":
                    self.has_picked = True
        # self.has_banned = False


    def is_hovering(self):
        """ Return a bool indicating whether or not the player is currently hovering a champ. """
        return self.pick_action["id"] != 0


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
        my_team = self.get_session()["myTeam"]
        my_id = self.get_summoner_id()
        for player in my_team:
            if player["summonerId"] == my_id:
                return player["assignedPosition"]
        # TODO: Error handling (?)
        return None


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
        # self.all_actions = actions
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