import time
from base64 import b64encode
import warnings
import utility as u
import requests
from urllib3.exceptions import InsecureRequestWarning

from utility import print_and_write

# Configure warnings
warnings.formatwarning = u.custom_formatwarning
warnings.simplefilter('ignore', InsecureRequestWarning)


class Connection:
    RUNEPAGE_PREFIX: str = "Auto:"  # Prefix for the name of rune pages created by this script
    BRYAN_SUMMONERID: int = 2742039436911744

    def __init__(self):
        # Info stored in lockfile
        self.lockfile = u.Lockfile()

        # How many seconds to wait before locking in the champ
        self.lock_in_delay: float = float(u.get_config_option("settings", "lock_in_delay"))

        # Flags
        self.started_queue: bool = False
        self.has_banned: bool = False
        self.has_picked: bool = False
        self.role_checked: bool = False
        self.runes_chosen: bool = False
        self.should_change_runes: bool = False

        # Dictionaries of League Champions
        self.all_champs: dict = {}
        self.owned_champs: dict = {}  # champions the player owns

        # Dictionaries storing info about the gamestate
        self.session: dict = {}  # champselect session data
        self.all_actions: dict = {}  # all champselect actions
        self.ban_action: dict = {}  # local player champselect ban action
        self.pick_action: dict = {}  # local player champselect pick action
        self.invalid_picks: list[int] = []  # list of champions that aren't valid picks

        # User intent and actual selections
        self.user_pick: str = ""  # the user's intended pick
        self.user_ban: str = ""  # the user's intended ban
        self.user_role: str = ""  # the user's intended role
        self.pick_intent: str = ""  # actual pick intent
        self.ban_intent: str = ""  # actual ban intent
        self.assigned_role: str = ""  # assigned role

        # Setup
        self.endpoints: dict = {}  # dictionary to store commonly used endpoints
        self.parse_lockfile()
        self.setup_endpoints()

        # Check for Bryan
        self.is_bryan: bool = self.get_summoner_id() == self.BRYAN_SUMMONERID

    # ----------------
    # Connection Setup
    # ----------------
    def parse_lockfile(self) -> None:
        """ Parse the user's lockfile into a dictionary. """
        l: u.Lockfile = self.lockfile
        path: str = u.get_lockfile_path()
        try:
            with open(path) as f:
                contents: list[str] = f.read().split(":")
                l.pid, l.port, l.password, l.protocol = contents[1:5]

        except FileNotFoundError:
            raise FileNotFoundError("Lockfile not found; open league, or specify your installation "
                                    "directory in your config")

        except Exception as e:
            raise Exception(f"Failed to parse lockfile: {str(e)}")


    def setup_endpoints(self) -> None:
        """ Set up a dictionary containing various endpoints for the API. """
        self.endpoints = {
            "gamestate": "/lol-gameflow/v1/gameflow-phase",  # GET
            "lobby": "/lol-lobby/v2/lobby",  # GET
            "start_queue": "/lol-lobby/v2/lobby/matchmaking/search",  # POST
            "match_found": "/lol-matchmaking/v1/ready-check",  # GET
            "accept_match": "/lol-matchmaking/v1/ready-check/accept",  # POST
            "champselect_session": "/lol-champ-select/v1/session",  # GET
            "owned_champs": "/lol-champions/v1/owned-champions-minimal",  # GET
            "current_summoner": "/lol-summoner/v1/current-summoner",  # GET
            "pickable_champs": "/lol-champ-select/v1/pickable-champions",  # GET
            "bannable_champs": "/lol-champ-select/v1/bannable-champion-ids",  # GET
            "runes": "/lol-perks/v1/pages",  # GET / POST
            "send_summs": "/lol-champ-select/v1/session/my-selection",  # PATCH

            # These endpoints need additional parameters added to the end of them
            "send_runes": "/lol-perks/v1/pages/",  # PUT (+runepageid)
            "summoner_info_byid": "/lol-summoner/v1/summoners/",  # GET (+summonerid)
            "champselect_action": "/lol-champ-select/v1/session/actions/"  # PATCH (+actionid)
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

        for champ in all_champs:
            champ_name = self.clean_name(champ["alias"], False)
            champid = champ["id"]
            self.all_champs[champ_name] = champid

        owned_champs = self.api_get("owned_champs").json()
        for champ in owned_champs:
            champ_name = self.clean_name(champ["alias"], False)
            champid = champ["id"]
            self.owned_champs[champ_name] = champid


    def get_first_choices(self) -> None:
        """ Get the user's first choice for picks and bans, as well as the role they're playing. Also ask them if
         they'd like the script to handle their runes and summoner spells.
         """
        # Pick choice
        self.user_pick = self.get_champ_name_input("Who would you like to play?  ")

        # Ban choice
        self.user_ban = self.get_champ_name_input("Who would you like to ban?  ")

        # Choose whether or not the script should handle runes and summoner spells
        self.should_change_runes = u.get_bool_input("Would you like the script to handle runes and summoner "
                                                    "spells automatically? y/n:  ")

        # Set intent to user input (intent can change later if first choice is banned, etc.)
        self.pick_intent = self.user_pick
        self.ban_intent = self.user_ban
        self.assigned_role = self.user_role

    def update_primary_role(self) -> None:
        """ Update the primary role that the user is queueing for. """
        try:
            local_player_data: dict = self.api_get("lobby").json()["localMember"]
            self.user_role = local_player_data["firstPositionPreference"].strip().lower()
        except Exception as e:
            warnings.warn(f"Unable to find player's role. Error raised: {e}", RuntimeWarning)

    # ------
    # Lobby
    # ------
    def start_queue(self) -> None:
        """ Start queueing for a match. """
        # Only want to start queue once - if user stops queue after, it shouldn't start again automatically
        if not self.started_queue:
            self.api_post("start_queue")
            self.started_queue = True

    def accept_match(self) -> None:
        """ Accept a match. """
        self.api_post("accept_match")

    def reset_after_dodge(self) -> None:
        """ Reset class instance variables after someone dodges a lobby. """
        self.started_queue = False
        self.has_picked = False
        self.has_banned = False
        self.runes_chosen = False
        self.role_checked = False
        self.pick_intent = self.user_pick
        self.ban_intent = self.user_ban
        self.assigned_role = self.user_role
        self.invalid_picks = []

    # ------------
    # Champselect
    # ------------
    def ban_or_pick(self) -> None:
        """ Decide whether to pick or ban based on gamestate, then call the corresponding method. """
        # User's turn to pick
        if not self.has_picked and self.is_currently_picking():
            self.lock_champ()

        # User's turn to ban
        elif not self.has_banned and self.is_currently_banning():
            self.ban_champ()
            # Re-hover pick intent after the ban
            self.hover_champ()

        # Not user's turn to do anything
        else:
            # Make sure we're always showing our intent
            champid: int = self.get_champid(self.pick_intent)
            if not self.has_picked and champid != self.get_current_hoverid():
                self.hover_champ(champid)


    def hover_champ(self, champid: int | None = None) -> None:
        """ Hover a champion in champselect. """
        if champid is None:
            champid = self.get_champid(self.pick_intent)
        u.print_and_write(f"trying to hover champ with id {champid}")
        self.do_champ(mode="hover", champid=champid)


    def ban_champ(self, champid: int | None = None) -> None:
        """ Ban a champion in champselect. """
        if champid is None:
            champid = self.get_champid(self.ban_intent)
        u.print_and_write(f"trying to ban champ with id {champid}")
        self.do_champ(mode="ban", champid=champid)


    def lock_champ(self, champid: int | None = None) -> None:
        """ Lock in a champion in champselect. """
        if champid is None:
            champid = self.get_champid(self.pick_intent)
        u.print_and_write(f"\tTrying to lock {self.pick_intent} (id {champid})")
        self.do_champ(mode="pick", champid=champid)


    def do_champ(self, **kwargs) -> None:
        """ Pick or ban a champ in champselect.
        Keyword arguments:
        champid -- the champ to pick/ban (optional)
        mode -- options are hover, ban, and pick
        """
        champid: int | None = kwargs.get("champid")
        mode: str | None = kwargs.get("mode")
        actionid: int | None = kwargs.get("actionid", None)

        # Set up http request
        data = {"championId": champid}
        if actionid is None:
            if mode == "ban":
                try:
                    actionid = self.ban_action["id"]
                except Exception as e:
                    warnings.warn(f"Unable to {mode} the specified champion: {e}", RuntimeWarning)
            else:
                try:
                    actionid = self.pick_action["id"]
                except Exception as e:
                    warnings.warn(f"Unable to {mode} the specified champion: {e}", RuntimeWarning)
        endpoint = self.endpoints["champselect_action"] + str(actionid)

        # Hover the champ in case we're not already
        if mode != "hover":
            self.do_champ(champid=champid, mode="hover", actionid=actionid)
            data["completed"] = True
            tmp_mode: str = "banning" if mode == "ban" else mode + "ing"
            u.print_and_write(f"\nWaiting {self.lock_in_delay} seconds before {tmp_mode}...\n")
            time.sleep(self.lock_in_delay)

        # Lock in the champ and print info
        response = self.api_patch(endpoint, data=data)

        # If the request was successful
        if response.status_code == 204:
            match mode:
                case "ban":
                    self.has_banned = True
                case "pick":
                    self.has_picked = True

        # If unable to lock champ (is banned, etc.)
        elif response.status_code == 500:
            if "banned" in str(response.json()).lower():
                # Note: This will break in custom game tournament drafts and in clash - the API returns an error code
                # of 500 when you try to hover a champ during the ban phase, causing every champ the script tries to
                # hover to be marked as invalid. However, this script is indended for normal draft, so this shouldn't
                # be a problem to begin with, but I still felt it was worth noting.
                self.invalid_picks.append(champid)

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
        :param name: the name to clean
        :param should_filter: if True, return "invalid" when an invalid champion name is passed
        """
        if name == "":
            return name
        # Remove all illegal characters and whitespace
        name = u.trim(name)

        # Handle edge cases (Nunu and Willump -> nunu and Wukong -> monkeyking)
        if "nunu" in name:
            return "nunu"
        elif name == "wukong":
            return "monkeyking"

        # Filter out invalid resulting names
        if should_filter:
            if name in self.all_champs:
                return name
            else:
                return "invalid"
        return name

    def get_champ_name_input(self, prompt: str) -> str:
        """ Get user input for the name of a champion. """
        name: str = self.clean_name(input(prompt))
        while name == "invalid":
            name = self.clean_name(input("Invalid champion name! Please try again:  "))

        return name

    def get_desired_role_input(self, prompt: str) -> str:
        """ Get user input for their desired role. """
        role: str = u.clean_role_name(prompt)
        while role == "invalid":
            role = self.clean_name("Invalid role name! Please try again:  ")

        return role


    def decide_pick(self) -> str:
        """ Decide what champ the user should play. """
        # Make sure Bryan plays his favorite champ
        if self.is_bryan:
            return "yuumi"

        # First check current pick intent
        pick: str = self.pick_intent
        if self.is_valid_pick(pick):
            return pick
        else:
            options: list[str] = u.parse_config(self.get_assigned_role())

        # If current pick intent isn't valid, loop through user's config to find a champ to pick
        is_valid = False
        for pick in options:
            if self.is_valid_pick(pick):
                return pick
        # Last config option isn't valid
        if not self.is_valid_pick(pick):
            raise Exception("Unable to find a valid champion to pick.")

        return pick


    def is_valid_pick(self, champ_name: str) -> bool:
        """ Check if the given champion can be picked """
        # Handle empty input - allows user to skip selecting a champion and default to those in the config
        if champ_name == "":
            return False

        champ_name = self.clean_name(champ_name)
        champid: int = self.get_champid(champ_name)
        error_msg: str = "Invalid pick:"

        # If champ has already been checked, and was invalid
        if champid in self.invalid_picks:
            u.print_and_write(error_msg, "in list of invalid champs")
            return False

        # If champ is banned
        if self.is_banned(champid):
            u.print_and_write(error_msg, "banned")
            return False

        # If user doesn't own the champ
        if champ_name not in self.owned_champs:
            u.print_and_write(error_msg, "unowned")
            return False

        # If a player has already PICKED the champ (hovering is ok)
        if champid in self.get_champ_pickids():
            u.print_and_write(error_msg, "already picked")
            return False


        # If the user got assigned a role other than the one they queued for, disregard the champ they picked
        # This does nothing when queuing for gamemodes that don't have assigned roles
        assigned_role = self.get_assigned_role()
        if (len(assigned_role) != 0
                and (self.user_role != assigned_role and self.user_role != "")
                and (self.user_pick == champ_name and self.user_pick != "")):
            u.print_and_write(error_msg, "autofilled")
            return False

        return True

    def is_valid_ban(self, champ: str) -> bool:
        """ Check if the specified champion can be banned. """
        # TODO: Fix bug where champ is already banned (Note: I think this is already fixed, but haven't tested yet)
        # Handle empty input - allows user to skip selecting a champion and default to those in the config
        if champ == "":
            return False

        champid = self.get_champid(champ)
        champ = self.clean_name(champ)
        u.print_and_write(f"Checking if {champ} is a valid ban...")
        error_msg = "Invalid ban:"

        # If trying to ban the champ the user wants to play
        if champ == self.pick_intent or champ == self.user_pick:
            u.print_and_write(error_msg, f"user intends to play {champ}")
            return False

        # If champ is already banned
        if self.is_banned(champid):
            u.print_and_write(error_msg, "already banned")
            return False

        # If a teammate is hovering the champ
        if self.teammate_hovering(champid):
            u.print_and_write(error_msg, "teammate hovering")
            return False

        return True


    def decide_ban(self) -> str:
        """ Decide what champ the user should ban. """
        # Make sure Bryan bans his least favorite champ
        if self.is_bryan:
            return "kayn"

        # First check current ban intent
        ban = self.ban_intent
        if self.is_valid_ban(ban):
            return ban

        # If current ban intent isn't valid, loop through user's config to find a champ to ban
        options = u.parse_config(self.get_assigned_role(), False)
        for ban in options:
            if self.is_valid_ban(ban):
                return ban

        # Last config option isn't valid
        if not self.is_valid_ban(ban):
            # Unlike with picking a champ, having no ban doesn't stop user from being able to play, so just
            # raise a warning instead of an exception
            warnings.warn("Unable to find a valid champion to ban.", RuntimeWarning)
        return ban


    def get_champ_pickids(self) -> list[int]:
        """ Return a list of champion ids that players have locked in. """
        champids: list[int] = []
        for pick, is_enemy, is_hovering in self.get_all_player_champids():
            if not is_hovering:
                champids.append(pick)
        return champids


    def get_teammate_hoverids(self) -> list[int]:
        """ Return a list of champion ids that teammates are hovering. """
        champids: list[int] = []
        for pick, is_enemy, is_hovering in self.get_all_player_champids():
            if not is_enemy and is_hovering:
                champids.append(pick)
        u.print_and_write(f"Current teammate hovers: {champids}")
        return champids


    def get_all_player_champids(self) -> list[tuple[int, bool, bool]]:
        """ Return a list of tuples. Each tuple contains a player's champ id, a bool indicating whether they are on the
        enemy team, and a bool hovering (True) or have already picked (False) the champion with the specified ID.
        """
        champids: list[tuple[int, bool, bool]] = []
        # Actions are grouped by type (pick, ban, etc.), so we iterate over each group
        for action_group in self.all_actions:
            for action in action_group:
                # Only look at pick actions, and only on user's team that aren't the user
                if action["type"] == "pick" and action["actorCellId"] != self.get_localcellid():
                    champid: int = action["championId"]

                    # If champid is 0, the player isn't hovering a champ
                    if champid != 0:
                        # If the action isn't completed, they're still hovering
                        champids.append((champid, not action["isAllyAction"], not action["completed"]))
        return champids


    def get_runepages(self) -> list[dict]:
        """ Get the runepages the player currently has set. """
        response = self.api_get("runes")
        if 200 <= response.status_code <= 299:  # TODO: Find out the actual response code for this...
            return response.json()
        else:
            raise RuntimeError("Unable to get runepages.")

    def get_runepage(self) -> tuple[dict, bool]:
        """
        Figure out which rune page to overwrite or use, and return its contents
        Returns:
            tuple[int, bool]: the rune page data (dictionary), and a bool indicating whether it should be overwritten
                (True) or used as-is (False)
        """
        # First, check if this script has already created a runepage
        all_pages: list[dict] = self.get_runepages()
        for page in all_pages:
            page_name: str = page["name"]
            prefix = self.RUNEPAGE_PREFIX
            # If rune page with champ name is found
            if self.pick_intent in self.clean_name(page_name, False):
                u.print_and_write(f"Runepage '{page_name}' has '{self.pick_intent}' in it. Using this runepage...")
                return page, False
            # If rune page with this script's naming scheme is found
            if page_name[0:len(prefix)] == prefix:
                u.print_and_write(f"Runepage '{page_name}' was created by this script - overwriting...")
                return page, True

        # No pages have been created by this script - try to create a new one
        u.print_and_write("No runepage created by this script was found. Trying to create a new one...")
        request_body = {
            "current": True,
            "isTemporary": False,
            "name": "temp",
            "order": 0,
        }
        response = self.api_post("runes", request_body)
        if response.status_code == 200:
            # Success - the runepage was created successfully. Now we return its data
            u.print_and_write(f"Success! Created a runepage with id {response.json()["id"]}")
            return response.json(), True
        
        # No empty rune page slots
        elif response.status_code == 400:
            if response.json()["message"] != "Max pages reached":
                raise RuntimeError("An unknown error occured while trying to create a runepage.")
            
            # Full of rune pages - return the id of one to overwrite
            u.print_and_write(f"Couldn't create a new runepage - overwriting page named {all_pages[-1]["name"]}, " +
                         f"with id {all_pages[-1]["id"]}")
            return all_pages[-1], True

    def send_runes_summs(self) -> None:
        """ Get the recommended rune page and summoner spells and send them to the client,
        if the user has opted in to this feature. """
        # Get assigned role
        role_name: str = self.get_assigned_role()
        # Use mid as a temp role to get runes if the user doesn't have an assigned role
        if len(role_name) == 0:
            role_name: str = "middle"

        if not self.runes_chosen and self.should_change_runes:
            # Get the runepage to use
            current_runepage, should_overwrite = self.get_runepage()
            endpoint = self.endpoints["send_runes"] + str(current_runepage["id"])

            # Get recommended runes and summs
            recommended_runepage: dict = self.get_recommended_runepage(role_name)[0]

            if should_overwrite:
                # Set the name for the rune page
                if role_name == "utility":
                    role_name = "support"
                name = f"{self.RUNEPAGE_PREFIX} {self.pick_intent} {role_name} {self.get_assigned_role()} runes"
                runes = recommended_runepage["perks"]
                request_body: dict = {
                    "current": True,
                    "isTemporary": False,
                    "id": current_runepage["id"],
                    "order": 0,
                    "name": name,
                    "primaryStyleId": recommended_runepage["primaryPerkStyleId"],
                    "selectedPerkIds": [rune["id"] for rune in runes],
                    "subStyleId": recommended_runepage["secondaryPerkStyleId"]
                }

            else:  # use existing rune page
                request_body = current_runepage

            summs = recommended_runepage["summonerSpellIds"]

            response = self.api_put(endpoint, request_body)
            try:
                if response.status_code == 400:
                    u.print_and_write("Error code:", response.json())
            except Exception as e:
                u.print_and_write("An exception occured:", e)

            # Make sure flash is always on F
            if summs[0] == 4:
                summs[0], summs[1] = summs[1], 4

            # TODO: Make sure Bryan always takes ghost/cleanse (he needs it)
            # if self.is_bryan:
            #     pass

            # Send summs
            if self.should_change_runes:
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


    def api_call(self, endpoint, method, data=None, should_print=False) -> requests.Response:
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

        # Send the request
        if should_print:
            u.print_and_write(f"Making API call...\n\tEndpoint: {endpoint}")
        result = request(url, headers=headers, json=data, verify=False)
        if should_print:
            u.print_and_write(f"\tResult: {result}\n")
        return result


    def get_session(self) -> dict:
        """ Get the current champselect session info. """
        return self.api_get("champselect_session").json()

    # --------------
    # Getter methods
    # --------------
    def get_assigned_role(self) -> str:
        """ Get the name of the user's assigned role. """
        # TODO: Add "default role" config option? (for gamemodes with no role, use a filler role to get runes)
        # Skip unecessary API calls
        if self.role_checked:
            return self.assigned_role
        role = ""
        my_team = self.session["myTeam"]
        my_id = self.get_summoner_id()
        for player in my_team:
            if player["summonerId"] == my_id:
                role = player["assignedPosition"]

        # Can't find user's role
        if len(role) == 0:
            warnings.warn("Unable to get assigned role", RuntimeWarning)
            role = self.user_role

        self.assigned_role = role
        return role


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
        l = self.lockfile
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


    def get_rune_recommendation_endpoint(self, position: str) -> str:
        """ Get the endpoint used to get recommended runes. """
        champid = self.get_champid(self.pick_intent)
        mapid = 11  # mapid for summoner's rift
        return f"/lol-perks/v1/recommended-pages/champion/{champid}/position/{position}/map/{mapid}"


    def get_recommended_runepage(self, role_name: str) -> dict:
        """ Get the recommended runepage from the client as a dictionary. """
        return self.api_get(self.get_rune_recommendation_endpoint(role_name)).json()


    def get_champselect_phase(self) -> str:
        """ Get the name of the current champselect phase. """
        phase = self.session["timer"]["phase"]

        # If someone dodged, phase will be None, causing an error - return "skip" to handle this
        if phase is None:
            u.print_and_write("phase is None")
            return "skip"
        return phase


    def update_champ_intent(self) -> None:
        """ Update instance variables with up-to-date pick, ban, and role intent, and hover the champ to be locked. """
        # Update pick intent
        if not self.has_picked:
            self.pick_intent = self.decide_pick()
            intent: str = self.pick_intent if self.pick_intent != "" else "None"
            u.print_and_write(f"\tPick intent: {self.pick_intent}")

        # Update ban intent
        if not self.has_banned:
            self.ban_intent = self.decide_ban()
            intent = self.ban_intent if self.ban_intent != "" else "None"
            u.print_and_write(f"\tBan intent: {intent}")


    def update_champselect(self) -> None:
        """ Update all champselect session data. """
        self.session = self.get_session()
        self.all_actions = self.session["actions"]
        local_cellid = self.get_localcellid()

        # Look at each action, and return the one with the corresponding cellid
        for action_group in self.all_actions:
            for action in action_group:
                if action["actorCellId"] == local_cellid:
                    if action["type"] == "ban":
                        self.ban_action = action

                    elif action["type"] == "pick":
                        self.pick_action = action

        self.update_champ_intent()