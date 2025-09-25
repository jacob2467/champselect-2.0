import sys
from base64 import b64encode
import warnings
import requests
from urllib3.exceptions import InsecureRequestWarning

import utility as u

# Configure warnings
warnings.formatwarning = u.custom_formatwarning
warnings.simplefilter('ignore', InsecureRequestWarning)


MSG_LOCKFILE_PARSING_ERR: str = ("Unable to connect to the League of Legends client. If it's open, try updating your "
"game directory in the config file (config.ini) and restart the program.")

class Connection:
    RUNEPAGE_PREFIX: str = "Blitz:"  # Prefix for the name of rune pages created by this script
    BRYAN_SUMMONERID: int = 2742039436911744

    def __init__(self, indentation: int = 0):
        # Info stored in lockfile
        # self.lockfile = u.Lockfile()

        # How many seconds to wait before locking in the champ
        self.lock_in_delay: int = int(u.get_config_option_str("settings", "lock_in_delay"))

        # Flags
        self.started_queue: bool = False
        self.has_banned: bool = False
        self.has_picked: bool = False
        self.role_checked: bool = False
        self.runes_chosen: bool = False
        self.should_modify_runes: bool = False
        self.has_printed_pick: bool = False
        self.has_printed_ban: bool = False

        # Dictionaries of League Champions
        self.all_champs: dict[str, int] = {}
        self.owned_champs: dict = {}  # champions the player owns

        # Info about the current gamestate
        self.gamestate: requests.Response
        self.session: dict = {}  # champselect session data
        self.all_actions: dict = {}  # all champselect actions
        self.ban_action: dict = {}  # local player champselect ban action
        self.pick_action: dict = {}  # local player champselect pick action
        self.invalid_picks: set[int] = set()  # set of champions that aren't valid picks

        # User intent and actual selections
        self.user_pick: str = ""  # the user's intended pick
        self.user_ban: str = ""  # the user's intended ban
        self.user_role: str = ""  # the user's intended role
        self.pick_intent: str = ""  # actual pick intent
        self.ban_intent: str = ""  # actual ban intent
        self.assigned_role: str = ""  # assigned role

        # Setup
        self.endpoints: dict = {}  # dictionary to store commonly used endpoints
        self.indentation = indentation # amount of tab characters used for certain print statements
        self.request_url: str
        self.http_headers: dict[str, str]
        self.request_url, self.http_headers = self.setup_http_requests()
        self.setup_endpoints()

        # Bryan check
        self.is_bryan: bool = self.get_summoner_id() == self.BRYAN_SUMMONERID

    # ----------------
    # Connection Setup
    # ----------------
    @staticmethod
    def parse_lockfile(wait_time: float = 5) -> u.Lockfile:
        """
        Parse the user's lockfile to be used to connect to the LCU API.
        :param wait_time: number of seconds to wait between failed attmepts to parse the lockfile
        """
        # Keep trying until lockfile is found
        lockfile_err: Exception | None = None
        lockfile: u.Lockfile = u.Lockfile()
        path: str = u.get_lockfile_path()
        try:
            with open(path) as f:
                contents: list[str] = f.read().split(":")
                lockfile.pid, lockfile.port, lockfile.password, lockfile.protocol = contents[1:5]
            lockfile_found = True

        except FileNotFoundError:
            sys.tracebacklimit = 0
            u.print_and_write(MSG_LOCKFILE_PARSING_ERR, should_print=False)
            lockfile_err = Exception(MSG_LOCKFILE_PARSING_ERR)

        except Exception as e:
            raise Exception(f"Error while parsing lockfile: {e}")

        if lockfile_err:
            raise lockfile_err

        return lockfile

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
            "current_champ": "/lol-champ-select/v1/current-champion", # GET
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
        # This endpoint requires the player's summoner id, which requires the current_summoner endpoint
        # to be initialized already, so initialize it separately
        self.endpoints.update(
            {"all_champs": f"/lol-champions/v1/inventories/{self.get_summoner_id()}/champions-minimal"  # GET
            }
        )

    def populate_champ_table(self) -> None:
        """ Get a list of all champions in the game and another of all that the player owns, and store them
        in a dictionary along with their id numbers.
        """
        response: requests.Response = self.api_get("all_champs")

        # TODO: Find a different endpoint for this (?)
        # Handle this strange error that only happens on certain accounts
        # {'errorCode': 'RPC_ERROR', 'httpStatus': 404, 'implementationDetails': {},
        # 'message': 'Champion data has not yet been received.'}
        if response.status_code == 404:
            # Fall back to endpoint for player-owned champs, which, for some reason, breaks less
            response = self.api_get("owned_champs")
            if response.status_code == 404:
                raise RuntimeError(f"Unable to get list of of champs: {response.json()}")
        all_champs: dict = response.json()

        for champ in all_champs:
            champ_name = u.clean_name(self.all_champs, champ["alias"], False)
            champid = champ["id"]
            self.all_champs[champ_name] = champid

        owned_champs = self.api_get("owned_champs").json()
        for champ in owned_champs:
            champ_name = u.clean_name(self.all_champs, champ["alias"], False)
            champid = champ["id"]
            self.owned_champs[champ_name] = champid

    def update_primary_role(self) -> None:
        """ Update the primary role that the user is queueing for. """
        try:
            local_player_data: dict = self.api_get("lobby").json()["localMember"]
            self.user_role = local_player_data["firstPositionPreference"].strip().lower()
        except Exception as e:
            warnings.warn(f"Unable to find player's role: {e}", RuntimeWarning)

    # --------------
    # Getter methods
    # --------------
    def get_runepages(self) -> list[dict]:
        """ Get the runepages the player currently has set. """
        response = self.api_get("runes")
        if response.status_code == 200:
            return response.json()

        raise RuntimeError(f"Unable to get rune pages: {response}")

    def get_assigned_role(self) -> str:
        """ Get the name of the user's assigned role. """
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
        if not role:
            # If no role was assigned, default to the role the user was queueing for. If that doesn't exist either,
            # default to mid
            role = self.user_role if self.user_role else "middle"
            warnings.warn(f"Unable to get assigned role, defaulting to {role}", RuntimeWarning)

        self.assigned_role = role
        self.role_checked = True
        return role

    def get_session(self) -> dict:
        """ Get the current champselect session info. """
        return self.api_get("champselect_session").json()

    def get_champid(self, champ: str) -> int:
        """ Get the id of the champion with the given name. """
        return self.all_champs[u.clean_name(self.all_champs, champ)]

    def get_gamestate(self) -> str:
        """ Get the current state of the game (Lobby, ChampSelect, etc.) """
        return self.api_get("gamestate").json()

    def get_localcellid(self) -> int:
        """ Get the cell id of the user. """
        return self.session["localPlayerCellId"]

    def get_summoner_id(self) -> int:
        """ Get the summoner id of the user. """
        return self.api_get("current_summoner").json()["accountId"]

    def get_recommended_runepage(self, champid: int, role_name: str) -> dict:
        """ Get the recommended runepage from the client as a dictionary. """
        endpoint: str = self.get_rune_recommendation_endpoint(champid, role_name)
        return self.api_get(endpoint).json()

    def setup_http_requests(self) -> tuple[str, dict[str, str]]:
        """
        Set up the request URL and HTTP header data for API calls.
        """
        lockfile = self.parse_lockfile()
        return self.get_request_url(lockfile), self.get_http_headers(lockfile)

    @staticmethod
    def get_rune_recommendation_endpoint(champid: int, position: str) -> str:
        """ Get the endpoint used to get recommended runes. """
        mapid = 11  # mapid for summoner's rift
        return f"/lol-perks/v1/recommended-pages/champion/{champid}/position/{position}/map/{mapid}"

    @staticmethod
    def get_request_url(lockfile: u.Lockfile) -> str:
        """
        Get the url to send http reqeusts to.
        """
        return f"{lockfile.protocol}://127.0.0.1:{lockfile.port}"

    @staticmethod
    def get_http_headers(lockfile: u.Lockfile) -> dict[str, str]:
        """
        Get a dictionary containing http auth header data. monkeysexpoop
        """
        https_auth = f"Basic {b64encode(f"riot:{lockfile.password}".encode()).decode()}"
        return {
            "Authorization": https_auth,
            "Accept": "application/json"
        }

    # -----------
    # API Methods
    # -----------
    def api_get(self, endpoint: str) -> requests.Response:
        """
        Send an HTTP GET request.
        :param endpoint: the endpoint to use
        """
        return self.api_call(endpoint, "get")

    def api_post(self, endpoint, data=None) -> requests.Response:
        """ Send an HTTP POST request. """
        return self.api_call(endpoint, "post", data)

    def api_put(self, endpoint, data=None) -> requests.Response:
        """ Send an HTTP PUT request. """
        return self.api_call(endpoint, "put", data)

    def api_patch(self, endpoint, data=None) -> requests.Response:
        """ Send an HTTP PATCH request. """
        return self.api_call(endpoint, "patch", data)

    def api_call(self, endpoint, method, data=None, should_print=False) -> requests.Response:
        """ Make an API call with the specified endpoint and method. """
        # Check if endpoint parameter is an alias for one stored in the endpoints dictionary, otherwise use as-is
        endpoint = self.endpoints.get(endpoint, endpoint)

        # Set up request URL
        url = self.request_url + endpoint
        headers = self.http_headers

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
        if should_print:  # debug print
            u.print_and_write(f"Making API call...\n\tEndpoint: {endpoint}")
        result = request(url, headers=headers, json=data, verify=False)
        if should_print:  # debug print
            u.print_and_write(f"\tResult: {result}\n")
        return result