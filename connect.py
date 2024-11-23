# These libraries are included with Python, and therefore don't require installation
from base64 import b64encode
import warnings
import copy

# These files are part of this project, and also don't require installation
import dependencies as d
from utility import *

# These libraries need to be installed, but urllib3 is a dependency of requests, so we only need to install requests
try:
    import requests
except ModuleNotFoundError:
    d.install("requests")
    import requests
from urllib3.exceptions import InsecureRequestWarning

# Disable warning for insecure http requests
warnings.simplefilter('ignore', InsecureRequestWarning)


class Connection:
    l: Lockfile = Lockfile()
    has_picked: bool = False
    has_banned: bool = False
    has_hovered: bool = False
    runes_chosen: bool = False
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
    def parse_lockfile(self) -> None:
        """ Parse the user's lockfile into a dictionary. """
        l = self.l
        path: str = get_lockfile_path()
        try:
            with open(path) as f:
                contents: str = f.read()
                contents: list[str] = contents.split(":")
                l.pid, l.port, l.password, l.protocol = contents[1:5]

        except FileNotFoundError:
            raise FileNotFoundError("Lockfile not found; open league, or specify your installation "
                                    "directory in your config")

        except Exception as e:
            raise Exception(f"Failed to parse lockfile: {str(e)}")


    def setup_endpoints(self) -> None:
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
            "pickable_champs": "/lol-champ-select/v1/pickable-champions",  # GET
            "bannable_champs": "/lol-champ-select/v1/bannable-champion-ids",  # GET
            "summoner_info_byid": "/lol-summoner/v1/summoners/",  # GET
            "send_runes": "/lol-perks/v1/pages"  # POST
        }

        # These keys use endpoints from the dictionary, so we initialize the dict first and then add these keys after
        self.endpoints.update(
            {"all_champs": f"/lol-champions/v1/inventories/{self.get_summoner_id()}/champions-minimal",  # GET
             "recommended_runes": lambda: self.get_rune_endpoint()},  # GET
            )


    def populate_champ_table(self) -> None:
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

        owned_champs = self.api_get("owned_champs").json()
        for champ in owned_champs:
            alias, id = self.clean_name(champ["alias"]), champ["id"]
            self.owned_champs[alias] = id

        # If there was a problem getting the list of all champs, just use the ones owned by the user
        if error:
            self.all_champs = copy.deepcopy(owned_champs)


    def get_first_choices(self) -> None:
        """ Get the user's first choice for picks and bans, as well as the role they're playing"""
        self.user_pick = self.clean_name(input("Who would you like to play?  "))
        self.user_ban = self.clean_name(input("Who would you like to ban?  "))
        self.role_choice = self.clean_role_name(input("What role would you like to play?  "))

        # Set intent to userinput (intent can change later if first choice is banned, etc.)
        self.pick_intent = self.user_pick
        self.ban_intent = self.user_ban

    # --------------
    # Helper methods
    # --------------
    def reset_after_dodge(self) -> None:
        """ Reset has_picked, has_banned, and has_hovered to False after someone dodges a lobby. """
        self.has_picked = False
        self.has_banned = False
        self.has_hovered = False
        self.runes_chosen = False


    def decide_pick(self) -> int:
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


    def decide_ban(self) -> int:
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


    def is_valid_pick(self, champ: str) -> bool:
        """ Check if the given champion can be picked """
        champ = self.clean_name(champ)
        id = self.get_champid(champ)
        error_msg = "Invalid pick:"

        # If user doesn't own the champ
        if champ not in self.owned_champs:
            print(error_msg, "unowned")
            return False

        # If champ is banned
        if id in self.get_banned_champids():
            print(error_msg, "banned")
            return False

        # If a teammate has already PICKED the champ (hovers ok, stealing champs is based)
        if id in self.get_teammate_pickids():
            print(error_msg, "teammate picked")
            return False

        # If the user got assigned a role other than the one they queued for, disregard the champ they picked
        # print(f"Role choice: {self.role_choice}, assigned role: {self.get_assigned_role()}")
        if len(self.get_assigned_role()) != 0 and self.role_choice != self.get_assigned_role():
                print(error_msg, "autofilled")
                return False

        return True


    def is_valid_ban(self, champ: str):
        """ Check if the given champion can be banned """
        champ = self.clean_name(champ)
        id = self.get_champid(champ)
        error_msg = "Invalid ban:"

        # If champ is banned already
        if id in self.get_banned_champids():
            print(error_msg, "banned already")
            return False

        # If a teammate is hovering the champ
        if self.teammate_hovering(id):
            print(error_msg, "teammate hovering")
            return False

        return True


    def get_teammate_champids(self) -> list[tuple[int, bool]]:
        """ Return a list of tuples. Each tuple contains a teammate's champion id and a boolean indicating whether they
        are hovering (True) or have already picked (False) the champion with the specified ID.
        """
        champids = []
        hovering = False
        for action_group in self.all_actions:
            for action in action_group:
                id: int = action["championId"]
                if action["isAllyAction"] and action["type"] == "pick" and id != 0:
                    if action["isInProgress"]:
                        hovering = True
                    champids.append((id, hovering))
        return champids

    def get_teammate_pickids(self) -> list[int]:
        """ Return a list of champion ids that teammates have locked in. """
        champs = []
        for pick, is_hovering in self.get_teammate_champids():
            if not is_hovering:
                champs.append(pick)
        return champs


    def get_teammate_hovers(self) -> list[int]:
        """ Return a list of champion ids that teammates are hovering. """
        champids = []
        for pick, is_hovering in self.get_teammate_champids():
            if is_hovering:
                champids.append(pick)
        return champids


    def send_runes(self) -> None:
        """ Get the recommended rune page and send it to the client. """
        # Can't send runes if playing a mode that doesn't have assigned roles
        if len(self.get_assigned_role()) == 0:
            return
        # TODO: Actually send the runes


    def send_summs(self) -> None:
        # TODO: Implement this
        return


    def get_banned_champids(self) -> list[int]:
        """ Get a list of all champion ids that have been banned. """
        session = self.get_session()
        return session["bans"]["myTeamBans"] + session["bans"]["theirTeamBans"]


    def is_banned(self, champid: int) -> bool:
        """ Check if the given champion is banned. """
        return champid in self.get_banned_champids()


    def check_role(self):
        # TODO: Get primary role the user is queueing for instead of getting it as user input
        a = self  # so pycharm doesn't yell at me and say this method is static
        return "top"  # dummy value


    def teammate_hovering(self, champid: int) -> bool:
        """ Check if the given champion is being hovered by a teammate. """
        print("teammates hovering id#", champid, ":", champid in self.get_teammate_hovers())
        return champid in self.get_teammate_hovers()


    @staticmethod
    def clean_name(name: str) -> str:
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
    def clean_role_name(name: str) -> str:
        """ Convert various role naming conventions to the format used by the game. Example output:
        mid -> middle
        supp -> utility
        jg -> jungle
        """
        # Remove all illegal characters and whitespace
        new_name = trim(name)

        roles = [["top", "t"], ["jungle", "jg", "j"], ["middle", "mid", "m"], ["bottom", "bot", "adc", "adcarry", "b"], ["utility", "support", "supp", "faggot", "fag"]]
        for role in roles:
            if new_name in role:
                return role[0]

        raise Exception("Invalid role selection. Please try again")

    # ----------------
    # API Call Methods
    # ----------------
    def accept_match(self) -> None:
        """ Accept a match. """
        self.api_post("accept_match")


    def ban_or_pick(self) -> None:
        """ Handle logic of whether to pick or ban, and then call the corresponding method. """
        # If it's my turn to pick (set False as default value)
        # print("ban_or_pick():", "self.pick_action.get('isInProgress', False)", self.pick_action.get("isInProgress", False), "self.ban_action.get('isInProgress', False)", self.ban_action.get("isInProgress", False))
        if self.pick_action.get("isInProgress", False):
            # print("pick action:", self.pick_action, "\n")
            self.hover_champ()
            self.lock_champ()

        # If it's my turn to ban (set False as default value)
        elif self.ban_action.get("isInProgress", False):
            # print("ban action:", self.ban_action, "\n")
            self.ban_champ()


    def ban_champ(self, champid: int = None) -> None:
        """ Ban a champion. """
        # print("ban_champ(): self.has_banned = ", self.has_banned)
        if not self.has_banned:
            self.do_champ(mode="ban", champid=champid)


    def lock_champ(self, champid: int = None) -> None:
        """ Lock in a champion. """
        # print("lock_champ(): self.has_picked = ", self.has_picked)
        if not self.has_picked:
            self.do_champ(mode="pick", champid=champid)


    def hover_champ(self, champid: int = None):
        """ Hover a champion. """
        # print("hover_champ(): self.is_hovering() = ", self.is_hovering(), "self.has_hovered:", self.has_hovered)
        if not self.is_hovering() and not self.has_hovered:
            self.do_champ(mode="hover", champid=champid)


    def do_champ(self, **kwargs) -> None:
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
        # try:
        #     print(response.json())
        # except:
        #     print("Failed to parse response as json, the response is empty.")
        if 200 <= response.status_code <= 299:
            match mode:
                case "hover":
                    self.has_hovered = True
                case "ban":
                    self.has_banned = True
                case "pick":
                    self.has_picked = True


    def is_hovering(self) -> bool:
        """ Return a bool indicating whether or not the player is currently hovering a champ. """
        # print("is_hovering():", "self.pick_action['championId']", self.pick_action["championId"])
        return self.pick_action["championId"] != 0


    def api_get(self, endpoint) -> requests.Response:
        """ Send an API GET request. """
        return self.api_call(endpoint, "get")


    def api_post(self, endpoint, data=None) -> requests.Response:
        """ Send an API POST request. """
        return self.api_call(endpoint, "post", data)


    def api_patch(self, endpoint, data=None) -> requests.Response:
        """ Send an API PATCH request. """
        return self.api_call(endpoint, "patch", data)


    def api_call(self, endpoint, method, data=None) -> requests.Response:
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
    def get_session(self) -> dict:
        """ Get the current champselect session info. """
        return self.api_get("champselect_session").json()


    def get_assigned_role(self) -> str:
        """ Get the name of the role the user was assigned to. """
        my_team = self.get_session()["myTeam"]
        my_id = self.get_summoner_id()
        for player in my_team:
            if player["summonerId"] == my_id:
                return player["assignedPosition"]
        return None


    def get_champid(self, champ) -> int:
        """ Get the id of the champion with the given name. """
        return self.all_champs[self.clean_name(champ)]

    def get_gamestate(self) -> requests.Response:
        """ Get the current state of the game (Lobby, ChampSelect, etc.) """
        return self.api_get("gamestate")


    def get_localcellid(self) -> int:
        """ Get the cell id of the user. """
        return self.get_session()["localPlayerCellId"]


    def get_request_url(self, endpoint: str) -> tuple[str, dict[str, str]]:
        """ Get the url to send http reqeusts to, and header data to send with it. """
        l = self.l
        https_auth = f"Basic {b64encode(f"riot:{l.password}".encode()).decode()}"
        headers = {
            "Authorization": https_auth,
            "Accept": "application/json"
        }

        url = f"{l.protocol}://127.0.0.1:{l.port}" + endpoint
        return url, headers


    def get_summoner_id(self) -> int:
        """ Get the id number of the user. """
        return self.api_get("current_summoner").json()["accountId"]


    def get_rune_endpoint(self) -> str:
        """ Get the endpoint used to get recommended runes. """
        champid = self.get_champid(self.pick_intent)
        position = self.get_assigned_role()
        mapid = 11  # TODO: Add options for other maps (default to summoner's rift for now)
        return f"/lol-perks/v1/recommended-pages/champion/{champid}/position/{position}/map/{mapid}"


    def get_recommended_runepage(self):
        return self.api_get(self.get_rune_endpoint()).json()


    def get_champselect_phase(self) -> str:
        """ Get the name of the current champselect phase. """
        phase = self.get_session()["timer"]["phase"]
        if phase is None:
            print("phase is None")
            return "skip"
        return phase


    def update_actions(self) -> None:
        """ Get the champselect action corresponding to the local player, and return it. """
        self.all_actions = self.get_session()["actions"]
        # print("actions:", actions, "\n")
        local_cellid = self.get_localcellid()

        # Look at each action, and return the one with the corresponding cellid
        for action_group in self.all_actions:
            for action in action_group:
                if action["actorCellId"] == local_cellid:
                    if action["type"] == "ban":
                        self.ban_action = action

                    elif action["type"] == "pick":
                        self.pick_action = action