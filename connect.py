# These libraries are included with Python, and therefore don't require installation
from base64 import b64encode
import warnings
import copy

# These files are part of this project, and also don't require installation
import dependencies as d
from utility import *

# These libraries need to be installed, but urllib3 is a dependency of requests, so we only need to install requests
requests = d.install_and_import("requests")
from urllib3.exceptions import InsecureRequestWarning

# Disable warning for insecure http requests
warnings.simplefilter('ignore', InsecureRequestWarning)


class Connection:
    RUNEPAGE_PREFIX = "Jacob:"  # Prefix for the name of rune pages created by this script

    def __init__(self):
        self.l: Lockfile = Lockfile()
        self.started_queue: bool = False
        self.has_banned: bool = False
        self.has_picked: bool = False
        self.role_checked: bool = False
        self.runes_chosen: bool = False
        self.endpoints: dict = {}
        self.all_champs: dict = {}
        self.owned_champs: dict = {}
        self.session: dict = {}
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
            "runes": "/lol-perks/v1/pages",  # GET / POST
            "send_runes": "/lol-perks/v1/pages/",  # PUT
            "send_summs": "/lol-champ-select/v1/session/my-selection"  # PATCH
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
                alias, champid = self.clean_name(champ["alias"], False), champ["id"]
                self.all_champs[alias] = champid
            except TypeError:
                warnings.warn("Champ data couldn't be retrieved, falling back to only"
                              "using data for owned champs...", RuntimeWarning)
                error = True

        owned_champs = self.api_get("owned_champs").json()
        for champ in owned_champs:
            alias, champid = self.clean_name(champ["alias"], False), champ["id"]
            self.owned_champs[alias] = champid

        if error:
            self.all_champs = copy.deepcopy(owned_champs)


    def get_first_choices(self) -> None:
        """ Get the user's first choice for picks and bans, as well as the role they're playing. """
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
    def start_queue(self) -> None:
        """ Start queueing for a match. """
        if not self.started_queue:
            self.api_post("start_queue")
            self.started_queue = True


    def reset_after_dodge(self) -> None:
        """ Reset instance variables. """
        self.started_queue = False
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

    # def check_role(self):
    #     TODO: Get role user is queuing for from API rather than user input
    # return "top"  # dummy value

    # ------------
    # Champselect
    # ------------
    def ban_or_pick(self) -> None:
        """ Handle logic of whether to pick or ban, and then call the corresponding method. """
        # If it's my turn to pick
        if not self.has_picked and self.is_currently_picking():
            # debugprint("pick action:", self.pick_action, "\n")
            self.lock_champ()

        # If it's my turn to ban
        elif not self.has_banned and self.is_currently_banning():
            # debugprint("ban action:", self.ban_action, "\n")
            self.ban_champ()
            # Hover after the ban
            self.hover_champ()
        # Make sure we're always showing our intent
        else:
            champid: int = self.get_champid(self.pick_intent)
            if not self.has_picked and champid != self.get_current_hoverid():
                self.hover_champ(champid)


    def hover_champ(self, champid: int = None) -> None:
        """ Hover a champion. """
        if champid is None:
            champid = self.get_champid(self.pick_intent)
        debugprint("trying to hover champ with id", champid)
        self.do_champ(mode="hover", champid=champid)


    def ban_champ(self, champid: int = None) -> None:
        """ Ban a champion. """
        if champid is None:
            champid = self.get_champid(self.ban_intent)
        debugprint("trying to ban champ with id", champid)
        self.do_champ(mode="ban", champid=champid)


    def lock_champ(self, champid: int = None) -> None:
        """ Lock in a champion. """
        if champid is None:
            champid = self.get_champid(self.pick_intent)
        debugprint("trying to lock champ with id", champid)
        self.do_champ(mode="pick", champid=champid)


    def do_champ(self, **kwargs) -> None:
        """ Pick or ban a champ in champselect.
        Keyword arguments:
        champid -- the champ to pick/ban (optional)
        mode -- options are hover, ban, and pick
        """
        champid = kwargs.get("champid")
        mode = kwargs.get("mode")
        actionid = kwargs.get("actionid", -1)

        # Set up http request
        data = {"championId": champid}
        if actionid == -1:
            if mode == "ban":
                try:
                    actionid = self.ban_action["id"]
                except KeyError as e:
                    warnings.warn(f"Unable to {mode} the specified champion - KeyError: {e}", RuntimeWarning)
            else:
                try:
                    actionid = self.pick_action["id"]
                except KeyError as e:
                    warnings.warn(f"Unable to {mode} the specified champion - KeyError: {e}", RuntimeWarning)
        endpoint = self.endpoints["champselect_action"] + str(actionid)

        # Hover the champ in case we're not already
        if mode != "hover":
            api_method = self.api_post
            self.do_champ(champid=champid, mode="hover", actionid=actionid)
            endpoint += "/complete"
        else:  # mode == "hover"
            api_method = self.api_patch

        # Lock in the champ and print info
        response = api_method(endpoint, data=data)
        debugprint(response, "\n")
        try:
            debugprint("Success:", response.json())
        except Exception as e:
            debugprint("Failed to parse response as json, the response is empty.")
            print("Error raised by response.json():", e)
        # don't worry about it
        if 200 <= response.status_code <= 299:
            match mode:
                case "ban":
                    self.has_banned = True
                case "pick":
                    self.has_picked = True
        else:
            match mode:
                case "ban":
                    self.has_banned = False
                case "pick":
                    self.has_picked = False


    def clean_name(self, name: str, should_filter=True) -> str:
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
        if should_filter:
            if new_name in self.all_champs:
                return new_name
            else:
                raise Exception("Invalid champion selection. Please try again")
                # TODO: Implement fuzzy search (?)
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
        # Handle empty input - allows user to skip selecting a champion and default to those in the config
        if champ == "":
            return False

        champ = self.clean_name(champ)
        champid: int = self.get_champid(champ)
        debugprint(f"Checking if {champ} is a valid pick...")
        error_msg: str = "Invalid pick:"

        # If champ is banned
        if self.is_banned(champid):
            debugprint(error_msg, "banned")
            return False

        # If user doesn't own the champ
        if champ not in self.owned_champs:
            debugprint(error_msg, "unowned")
            return False

        # If a player has already PICKED the champ (hovering is ok)
        if champid in self.get_champ_pickids():
            debugprint(error_msg, "already picked")
            return False

        # TODO: Check if an enemy locked it


        # If the user got assigned a role other than the one they queued for, disregard the champ they picked...
        # UNLESS they didn't enter a role they wanted to play
        role_intent = self.get_assigned_role()
        debugprint(f"Role choice: {self.user_role}, assigned role: {role_intent}\n")
        if (len(role_intent) != 0
                and (self.user_role != role_intent and self.user_role != "")
                and (self.user_pick == champ and self.user_pick != "")):
            debugprint(error_msg, "autofilled")
            return False

        return True

    def is_valid_ban(self, champ: str) -> bool:
        """ Check if the given champion can be banned """
        # Handle empty input - allows user to skip selecting a champion and default to those in the config
        if champ == "":
            return False

        champid = self.get_champid(champ)
        champ = self.clean_name(champ)
        debugprint(f"Checking if {champ} (id: {champid}) is a valid ban...")
        error_msg = "Invalid ban:"

        # If trying to ban the champ the user wants to play
        if champ == self.pick_intent:
            debugprint(error_msg, f"user intends to play {champ}")
            return False

        # If champ is already banned
        if self.is_banned(champid):
            debugprint(error_msg, "already banned")
            return False

        # If a teammate is hovering the champ
        if self.teammate_hovering(champid):
            debugprint(error_msg, "teammate hovering")
            return False

        return True


    def decide_ban(self) -> str:
        """ Decide what champ the user should ban. """
        ban = self.ban_intent
        if self.is_valid_ban(ban):
            return ban
        else:
            debugprint("assigned role:", self.get_assigned_role())
            options = parse_config(self.get_assigned_role(), False)

        i = 0
        is_valid = False
        while not is_valid and i < len(options):
            ban = options[i]
            is_valid = self.is_valid_ban(ban)
            i += 1
        return ban


    def get_champ_pickids(self) -> list[int]:
        """ Return a list of champion ids that players have locked in. """
        champids: list[int] = []
        for pick, is_enemy, is_hovering in self.get_champids():
            if not is_hovering:
                champids.append(pick)
        return champids


    def get_teammate_hoverids(self) -> list[int]:
        """ Return a list of champion ids that teammates are hovering. """
        champids: list[int] = []
        for pick, is_enemy, is_hovering in self.get_champids():
            if not is_enemy and is_hovering:
                champids.append(pick)
        debugprint(f"Current teammate hovers: {champids}")
        return champids


    def get_champids(self) -> list[tuple[int, bool, bool]]:
        """ Return a list of tuples. Each tuple contains a player's champ id, a bool indicating whether they are on the
        user's team, and a bool hovering (True) or have already picked (False) the champion with the specified ID.
        """
        champids: list[tuple[int, bool, bool]] = []

        # Actions are grouped by type (pick, ban, etc), so we iterate over each group
        for action_group in self.all_actions:
            for action in action_group:
                # Only look at pick actions, and only on user's team that aren't the user
                if (action["type"] == "pick"
                        and action["actorCellId"] != self.get_localcellid()):
                    champid: int = action["championId"]

                    # If champid is 0, the player isn't hovering a champ
                    if champid != 0:
                        # If the action isn't completed, they're still hovering
                        champids.append((champid, action["isAllyAction"], not action["completed"]))
        return champids


    def get_runepages(self) -> list[dict]:
        """ Get the runepages the player currently has set. """
        response = self.api_get("runes")
        print(response)
        if 200 <= response.status_code <= 299:
            return response.json()
        else:
            raise RuntimeError("Unable to get runepages.")

    def get_runepage_id(self) -> int:
        """ Figure out which rune page to overwrite, and return its id. """
        # First, check if this script has already created a runepage
        all_pages: list[dict] = self.get_runepages()
        debugprint("Checking for a rune page created by this script...")
        for page in all_pages:
            name: str = page["name"]
            prefix = self.RUNEPAGE_PREFIX
            if name[0:len(prefix)] == prefix:
                debugprint(f"Runepage with id {page["id"]} was created by this script - overwriting...")
                return page["id"]

        # No pages have been created by this script - try to create a new one
        debugprint("No runepage created by this script was found. Trying to create a new one...")
        request_body = {
            "current": True,
            "isTemporary": False,
            "name": "temp",
            "order": 0,
        }
        response = self.api_post("runes", request_body)
        if response.status_code == 200:
            # Success - the runepage was created successfully. Now we return its id
            debugprint(f"Success! Created a runepage with id {response.json()["id"]}")
            return response.json()["id"]
        elif response.status_code == 400:
            if response.json()["message"] == "Max pages reached":
                # Full of rune pages - return the id of one to overwrite
                debugprint(f"Couldn't create a new runepage - overwriting page named {all_pages[-1]["name"]}, " +
                           f"with id {all_pages[-1]["id"]}")
                return all_pages[-1]["id"]
            else:
                raise RuntimeError("An unknown error occured while trying to create a runepage.")


    def send_runes_summs(self) -> None:
        """ Get the recommended rune page and summoner spells, and send them to the client. """
        # Can't send runes if playing a mode that doesn't have assigned roles
        if len(self.get_assigned_role()) == 0:
            return

        if not self.runes_chosen:
            # Get the runepage to be overwritten
            endpoint = self.endpoints["send_runes"] + str(self.get_runepage_id())

            # Get recommended runes and summs
            recommended_runepage: dict = self.get_recommended_runepage()[0]
            runes = recommended_runepage["perks"]
            summs = recommended_runepage["summonerSpellIds"]

            # Send runes
            request_body = {
                "current": True,
                "isTemporary": False,
                # TODO: If bryan, add "I love child porn" to runepage name
                "name": f"{self.RUNEPAGE_PREFIX} {self.pick_intent} {self.get_assigned_role()} runes",
                "order": 0,
                "primaryStyleId": recommended_runepage["primaryPerkStyleId"],
                "selectedPerkIds": [rune["id"] for rune in runes],
                "subStyleId": recommended_runepage["secondaryPerkStyleId"]
            }
            response = self.api_put(endpoint, request_body)
            debugprint(response)
            try:
                if not (200 <= response.status_code <= 299):
                    debugprint("Error code:", response.json())
            except Exception as e:
                debugprint("An exception occured:", e)

            # Make sure flash is always on F
            if summs[0] == 4:
                summs[0] = summs[1]
                summs[1] = 4

            # Send summs
            request_body = {
                "spell1Id": summs[0],
                "spell2Id": summs[1]
            }
            self.api_patch("send_summs", request_body)
            self.runes_chosen = True

    def get_banned_champids(self) -> list[int]:
        """ Get a list of all champion ids that have been banned. """
        return self.session["bans"]["myTeamBans"] + self.session["bans"]["theirTeamBans"]


    def is_banned(self, champid: int) -> bool:
        """ Check if the given champion is banned. """
        return champid in self.get_banned_champids()


    def teammate_hovering(self, champid: int) -> bool:
        """ Check if the given champion is being hovered by a teammate. """
        # debugprint("teammates hovering id#", champid, ":", champid in self.get_teammate_hovers())
        return champid in self.get_teammate_hoverids()


    def get_current_hoverid(self) -> int:
        """ Get the id number of the champ the player is currently hovering. """
        return self.pick_action.get("championId", 0)


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


    def api_put(self, endpoint, data=None) -> requests.Response:
        """ Send an API PUT request. """
        return self.api_call(endpoint, "put", data)


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
            case "put":
                request = requests.put
            case _:
                request = None

        # Send the request
        return request(url, headers=headers, json=data, verify=False)


    def get_session(self) -> dict:
        """ Get the current champselect session info. """
        return self.api_get("champselect_session").json()

    # --------------
    # Getter methods
    # --------------
    def get_assigned_role(self) -> str | None:
        """ Get the name of the user's assigned role. """
        # Skip unecessary API calls
        if self.role_checked:
            return self.role_intent
        else:
            to_return = None
            my_team = self.session["myTeam"]
            my_id = self.get_summoner_id()
            for player in my_team:
                if player["summonerId"] == my_id:
                    to_return = player["assignedPosition"]

            # Fall back on user input role if playing a gamemode with no assigned roles (customs, etc)
            if len(to_return) == 0:
                debugprint("unable to get assigned role, falling back to userinput...")
                to_return = self.user_role

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
        return self.session["localPlayerCellId"]


    def get_request_url(self, endpoint: str) -> tuple[str, dict[str, str]]:
        """ Get the url to send http reqeusts to, and header data to send with it. """
        l = self.l
        https_auth = f"Basic {b64encode(f"riot:{l.password}".encode()).decode()}"
        headers = {
            "Authorization": https_auth,
            "Accept": "application/json"
        }

        url = f"{l.protocol}://{"127.0.0.1"}:{l.port}" + endpoint
        return url, headers


    def get_summoner_id(self) -> int:
        """ Get the id number of the user. """
        return self.api_get("current_summoner").json()["accountId"]


    def get_rune_recommendation_endpoint(self) -> str:
        """ Get the endpoint used to get recommended runes. """
        champid = self.get_champid(self.pick_intent)
        position = self.get_assigned_role()
        mapid = 11  # TODO: Add options for other maps (default to summoner's rift for now)
        return f"/lol-perks/v1/recommended-pages/champion/{champid}/position/{position}/map/{mapid}"


    def get_recommended_runepage(self) -> dict:
        """ Get the recommended runepage from the client as a dictionary. """
        return self.api_get(self.get_rune_recommendation_endpoint()).json()


    def get_champselect_phase(self) -> str:
        """ Get the name of the current champselect phase. """
        phase = self.session["timer"]["phase"]

        # If someone dodged, phase will be None, causing an error - return "skip" to handle this
        if phase is None:
            debugprint("phase is None")
            return "skip"
        return phase


    def update_champ_intent(self) -> None:
        """ Update instance variables with up-to-date pick, ban, and role intent, and hover the champ to be locked. """
        # Only update intent if user hasn't already picked
        debugprint("Updating champ intent...")
        debugprint(f"{self.has_picked=}")

        # Update pick intent
        if not self.has_picked:
            self.pick_intent = self.decide_pick()
            debugprint(f"{self.pick_intent=}")

        # Update ban intent
        if not self.has_banned:
            self.ban_intent = self.decide_ban()
            debugprint(f"{self.ban_intent=}")
        debugprint()


    def update(self) -> None:
        """ Update all champselect session data. """
        self.session = self.get_session()
        self.all_actions = self.session["actions"]
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
                        debugprint("pick action:", action)

        self.update_champ_intent()