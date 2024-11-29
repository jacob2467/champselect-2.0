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
    has_picked: bool
    ip_address = "127.0.0.1"

    def __init__(self):
        self.l: Lockfile = Lockfile()
        # self.has_hovered: bool = False  # Unecessary? Possibly remove later
        self.has_banned: bool = False
        self.has_picked: bool = False
        self.role_checked: bool = False
        self.runes_chosen: bool = False
        self.endpoints: dict = {}
        self.all_champs: dict = {}
        self.owned_champs: dict = {}
        self.ban_action: dict = {}
        self.pick_action: dict = {}
        self.all_actions: dict = {}
        self.user_pick: str = ""
        self.user_ban: str = ""
        self.role_intent: str = ""
        self.user_role: str = ""
        self.pick_intent: str = ""
        self.ban_intent: str = ""
        self.parse_lockfile()
        self.setup_endpoints()
        self.populate_champ_table()
        self.get_first_choices()

    # ----------------
    # Connection Setup
    # ----------------
    def parse_lockfile(self) -> None:
        """ Parse the user's lockfile into a dictionary. """
        l: Lockfile = self.l
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
            "send_runes": "/lol-perks/v1/pages",  # POST
        }

        self.endpoints.update(
            {"all_champs": f"/lol-champions/v1/inventories/{self.get_summoner_id()}/champions-minimal"  # GET
             }
        )


    def populate_champ_table(self) -> None:
        """ Get a list of all champions in the game and another of all that the player owns, and store them
        in a dictionary along with their id numbers.
        """
        all_champs: dict = self.api_get("all_champs").json()
        error: bool = False
        for champ in all_champs:
            try:
                alias, id = self.clean_name(champ["alias"], False), champ["id"]
                self.all_champs[alias] = id
            except TypeError:
                warnings.warn("Champ data couldn't be retrieved, falling back to only"
                              "using data for owned champs...", RuntimeWarning)
                error = True

        owned_champs = self.api_get("owned_champs").json()
        for champ in owned_champs:
            alias, id = self.clean_name(champ["alias"], False), champ["id"]
            self.owned_champs[alias] = id

        if error:
            self.all_champs = copy.deepcopy(owned_champs)


    def get_first_choices(self) -> None:
        """ Get the user's first choice for picks and bans, as well as the role they're playing"""
        # TODO: Add option to skip this and use config by pressing enter without typing anything
        self.user_pick = self.clean_name(input("Who would you like to play?  "))
        self.user_ban = self.clean_name(input("Who would you like to ban?  "))
        self.user_role = clean_role_name(input("What role would you like to play?  "))

        # Set intent to userinput (intent can change later if first choice is banned, etc.)
        self.pick_intent = self.user_pick
        self.ban_intent = self.user_ban
        self.role_intent = self.user_role

    # ------
    # Lobby
    # ------
    def reset_after_dodge(self) -> None:
        """ Reset instance variables. """
        # self.has_hovered = False
        self.has_picked = False
        self.has_banned = False
        self.runes_chosen = False
        self.role_checked = False
        self.pick_intent = self.user_pick
        self.ban_intent = self.user_ban
        self.role_intent = self.user_role

    def accept_match(self) -> None:
        """ Accept a match. """
        self.api_post("accept_match")

    def check_role(self):
        # TODO: Get primary role the user is queueing for instead of getting it as user input
        a = self  # so pycharm doesn't yell at me and say this method is static
        a += 1
        return "top"  # dummy value

    # ------------
    # Champselect
    # ------------
    def clean_name(self, name: str, filter=True) -> str:
        """ Remove whitespace and special characters from a champion's name. Example output:
        Aurelion Sol -> aurelionsol
        Bel'Veth -> belveth
        Parameters:
        name: the name to clean
        filter: whether or not to throw an error when an invalid name is selected
        """
        if name == "":
            return name
        # Remove all illegal characters and whitespace
        new_name = trim(name)

        # Handle edge cases (Nunu and Willump -> nunu and Wukong -> monkeyking)
        if "nunu" in new_name:
            return "nunu"
        elif new_name == "wukong":
            return "monkeyking"

        # Filter out invalid resulting names
        if filter:
            if new_name in self.all_champs:
                return new_name
            else:
                raise Exception("Invalid champion selection. Please try again")
                # TODO:
                #  - Implement fuzzy search
                #  - Finish error handling
        return new_name



    def decide_pick(self) -> str:
        """ Decide what champ the user should play. """
        pick: str = self.pick_intent
        if self.is_valid_pick(pick):
            return pick
        else:
            options: list[str] = parse_config(self.get_assigned_role())

        i = 0
        is_valid = False
        while not is_valid and i < len(options):
            pick = self.clean_name(options[i])
            is_valid = self.is_valid_pick(pick)
            i += 1
        if not self.is_valid_pick(pick):
            raise Exception("Unable to find a valid champion to pick.")
        return pick


    def is_valid_pick(self, champ: str) -> bool:
        """ Check if the given champion can be picked """
        debugprint(f"Checking if {champ} is a valid pick...")
        # Handle empty input - allows user to skip selecting a champion and default to those in the config
        if champ == "":
            return False

        champ = self.clean_name(champ)
        id: int = self.get_champid(champ)
        error_msg: str = "Invalid pick:"

        # If champ is banned
        if id in self.get_banned_champids():
            debugprint(error_msg, "banned")
            return False

        # If user doesn't own the champ
        if champ not in self.owned_champs:
            debugprint(error_msg, "unowned")
            return False

        # If a teammate has already PICKED the champ (hovering is ok)
        if id in self.get_teammate_pickids():
            debugprint(error_msg, "teammate picked")
            return False


        # If the user got assigned a role other than the one they queued for, disregard the champ they picked...
        # UNLESS they didn't enter a role they wanted to play
        role_intent = self.get_assigned_role()
        debugprint(f"Role choice: {self.user_role}, assigned role: {role_intent}\n")
        if (len(role_intent) != 0
        and (self.user_role != role_intent and self.user_role != "")
        and (self.user_pick == self.pick_intent and self.user_pick == "")):
            debugprint(error_msg, "autofilled")
            return False

        return True


    def decide_ban(self) -> str:
        """ Decide what champ the user should ban. """
        ban = self.ban_intent
        if self.is_valid_ban(ban):
            return ban
        else:
            options = parse_config(self.get_assigned_role(), False)

        i = 0
        is_valid = False
        while not is_valid and i < len(options):
            ban = options[i]
            is_valid = self.is_valid_ban(ban)
            i += 1
        # TODO: Add error handling
        return ban


    def is_valid_ban(self, champ: str) -> bool:
        """ Check if the given champion can be banned """
        # Handle empty input - allows user to skip selecting a champion and default to those in the config
        if champ == "":
            return False

        champ = self.clean_name(champ)
        id = self.get_champid(champ)
        error_msg = "Invalid ban:"

        debugprint(f"Checking if {champ} (id: {id}) is valid to ban...")

        # If champ is already banned
        if id in self.get_banned_champids():
            debugprint(error_msg, "already banned")
            return False

        # If a teammate is hovering the champ
        hovering = self.teammate_hovering(id)
        debugprint(f"Teammate hovering {champ}: {hovering}")
        if hovering:
            debugprint(error_msg, "teammate hovering")
            return False

        return True


    def get_teammate_champids(self) -> list[tuple[int, bool]]:
        """ Return a list of tuples. Each tuple contains a teammate's champion id and a boolean indicating whether they
        are hovering (True) or have already picked (False) the champion with the specified ID.
        """
        champids: list[tuple[int, bool]] = []

        # Actions are grouped by type (pick, ban, etc), so we iterate over each group
        for action_group in self.all_actions:
            for action in action_group:
                # Only look at pick actions, and only on user's team that aren't the user
                if (action["type"] == "pick"
                and action["isAllyAction"]
                and action["actorCellId"] != self.get_localcellid()):
                    champid: int = action["championId"]

                    # If champid is 0, the player isn't hovering a champ
                    if champid != 0:
                        # If the action isn't completed, they're still hovering
                        champids.append((champid, not action["completed"]))
        return champids

    def get_teammate_pickids(self) -> list[int]:
        """ Return a list of champion ids that teammates have locked in. """
        champids: list[int] = []
        for pick, is_hovering in self.get_teammate_champids():
            if not is_hovering:
                champids.append(pick)
        return champids


    def get_teammate_hoverids(self) -> list[int]:
        """ Return a list of champion ids that teammates are hovering. """
        champids: list[int] = []
        for pick, is_hovering in self.get_teammate_champids():
            if is_hovering:
                champids.append(pick)
        debugprint(f"Current teammate hovers: {champids}")
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


    def teammate_hovering(self, champid: int) -> bool:
        """ Check if the given champion is being hovered by a teammate. """
        # debugprint("teammates hovering id#", champid, ":", champid in self.get_teammate_hovers())
        return champid in self.get_teammate_hoverids()


    def ban_or_pick(self) -> None:
        """ Handle logic of whether to pick or ban, and then call the corresponding method. """
        # Always make sure
        self.hover_champ()

        # If it's my turn to pick
        if self.is_currently_picking():
            # debugprint("pick action:", self.pick_action, "\n")
            self.lock_champ()

        # If it's my turn to ban
        elif self.is_currently_banning():
            # debugprint("ban action:", self.ban_action, "\n")
            self.ban_champ()
            self.hover_champ()


    def ban_champ(self) -> None:
        """ Ban a champion. """
        champid = self.get_champid(self.ban_intent)
        if not self.has_banned:
            debugprint("trying to ban champ with id", champid)
            self.do_champ(mode="ban", champid=champid)


    def lock_champ(self) -> None:
        """ Lock in a champion. """
        champid = self.get_champid(self.pick_intent)
        if not self.has_picked:
            debugprint("trying to lock champ with id", champid)
            self.do_champ(mode="pick", champid=champid)


    def hover_champ(self, champid: int = None) -> None:
        """ Hover a champion. """
        # Default to hovering the pick intent
        if champid is None:
            champid = self.get_champid(self.pick_intent)
        # Otherwise hover the specified champ
        # Don't make the API call if we're already hovering the desired champ or have already picked
        if champid != self.get_current_hoverid() and not self.has_picked:
            debugprint("trying to hover champ with id", champid)
            self.do_champ(mode="hover", champid=champid)


    def do_champ(self, **kwargs) -> None:
        """ Pick or ban a champ in champselect.
        Keyword arguments:
        champid -- the champ to pick/ban (optional)
        mode -- options are hover, ban, and pick
        """
        champid = kwargs.get("champid")
        mode = kwargs.get("mode")

        # Set up http request
        data = {"championId": champid}
        if mode == "ban":
            actionid = self.ban_action["id"]
        else:
            actionid = self.pick_action["id"]
        endpoint = self.endpoints["champselect_action"] + str(actionid)

        # Hover the champ if we're not already
        if mode != "hover":
            api_method = self.api_post
            self.hover_champ(champid)
            endpoint += "/complete"
        else:  # mode == "hover"
            api_method = self.api_patch

        # Lock in the champ and print info
        response = api_method(endpoint, data=data)
        debugprint(response, "\n")
        try:
            debugprint(response.json())
        except:
            debugprint("Failed to parse response as json, the response is empty.")
        if 200 <= response.status_code <= 299:
            match mode:
                # case "hover":
                #     self.has_hovered = True
                case "ban":
                    self.has_banned = True
                case "pick":
                    self.has_picked = True


    def update_intent(self) -> None:
        """ Update instance variables with up-to-date pick, ban, and role intent, and hover the champ to be locked. """
        # Only update intent if user hasn't already picked
        if not self.has_picked:
            self.pick_intent = self.decide_pick()
            champid: int = self.get_champid(self.pick_intent)
            if champid != self.get_current_hoverid():
                self.hover_champ(champid)

            debugprint("pick intent:", self.pick_intent)

        # Always update ban intent to support custom games with multiple bans
        self.ban_intent = self.decide_ban()
        debugprint("ban intent:", self.ban_intent)
        debugprint()


    def get_current_hoverid(self) -> int:
        """ Get the id number of the champ the player is currently hovering. """
        return self.pick_action["championId"]


    def is_currently_picking(self) -> bool:
        """ Return a bool indicating whether or not the user is currently picking. """
        return self.pick_action.get("isInProgress", False)


    def is_currently_banning(self) -> bool:
        """ Return a bool indicating whether or not the user is currently banning. """
        return self.ban_action.get("isInProgress", False)


    def is_hovering(self) -> bool:
        """ Return a bool indicating whether or not the player is currently hovering a champ. """
        # print("is_hovering():", "self.pick_action['championId']", self.pick_action["championId"])
        return self.get_current_hoverid() != 0


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


    def get_assigned_role(self) -> str | None:
        """ Get the name of the user's assigned role. """
        # Skip unecessary API calls
        if self.role_checked:
            return self.role_intent
        else:
            to_return = "none"
            my_team = self.get_session()["myTeam"]
            my_id = self.get_summoner_id()
            for player in my_team:
                if player["summonerId"] == my_id:
                    to_return = player["assignedPosition"]
            self.role_intent = to_return
            return to_return


    def get_champid(self, champ: str) -> int:
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

        url = f"{l.protocol}://{self.ip_address}:{l.port}" + endpoint
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


    def get_recommended_runepage(self) -> dict:
        """ Get the recommended runepage from the client as a dictionary. """
        return self.api_get(self.get_rune_endpoint()).json()


    def get_champselect_phase(self) -> str:
        """ Get the name of the current champselect phase. """
        phase = self.get_session()["timer"]["phase"]

        # If someone dodged, phase will be None, causing an error - return "skip" to handle this
        if phase is None:
            debugprint("phase is None")
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