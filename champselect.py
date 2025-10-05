import warnings
import time

import utility as u
import connect as c


def ban_or_pick(connection: c.Connection) -> None:
    """ Decide whether to pick or ban based on gamestate, then call the corresponding method. """
    # User's turn to pick
    if not connection.has_picked and is_currently_picking(connection):
        lock_champ(connection)
        return

    # User's turn to ban
    elif not connection.has_banned and is_currently_banning(connection):
        ban_champ(connection)
        # Re-hover pick intent after the ban
        hover_champ(connection)
        return

    # Not user's turn to do anything
    # Make sure we're always showing our intent
    champid: int = connection.get_champid(connection.pick_intent)
    if not connection.has_picked and champid != get_current_hoverid(connection):
        hover_champ(connection, champid)


def hover_champ(connection: c.Connection, champid: int | None = None) -> None:
    """
    Hover a champion in champselect.
    Args:
        champid: (optional) the id number of the champion to hover
    """
    if champid is None:
        champid = connection.get_champid(connection.pick_intent)
    do_champ(connection, mode="hover", champid=champid)


def ban_champ(connection: c.Connection, champid: int | None = None) -> None:
    """
    Ban a champion in champselect.
    Args:
        champid: (optional) the id number of the champion to ban
    """
    if champid is None:
        champid = connection.get_champid(connection.ban_intent)
    do_champ(connection, mode="ban", champid=champid)


def lock_champ(connection: c.Connection, champid: int | None = None) -> None:
    """
    Lock in a champion in champselect.
    Args:
        champid: (optional) the id number of the champion to lock
    """
    if champid is None:
        champid = connection.get_champid(connection.pick_intent)
    do_champ(connection, mode="pick", champid=champid)


def do_champ(connection: c.Connection, champid: int = 0, mode: str = "pick", actionid: int | None = None) -> None:
    """
    Pick or ban a champ in champselect.
    Args:
        champid: (optional) the id number of the champion
        mode: (optional) the mode to use (options are pick, ban, or hover)
        actionid: (optional) the actionid of the Champselect action to use
    """
    # Set up http request
    data: dict[str, int] = {"championId": champid}
    if actionid is None:
        actionid = get_actionid(connection, mode)

    endpoint: str = connection.endpoints["champselect_action"] + str(actionid)

    # Hover the champ in case we're not already
    if mode != "hover":
        do_champ(connection, champid=champid, mode="hover", actionid=actionid)
        data["completed"] = True
        wait_before_locking(connection, mode)

    # Lock in the champ and print info
    response = connection.api_patch(endpoint, data=data)

    # If the request was successful
    if response.status_code == 204:
        match mode:
            case "ban":
                connection.has_banned = True
            case "pick":
                connection.has_picked = True

    # If unable to lock champ (is banned, etc.)
    elif response.status_code == 500:
        if "banned" in str(response.json()).lower():
            # Note: This will break in custom game tournament drafts and in clash - the API returns an error code
            # of 500 when you try to hover a champ during the ban phase, causing every champ the script tries to
            # hover to be marked as invalid.
            connection.invalid_picks.add(champid)


def decide_pick(connection: c.Connection) -> str:
    """ Decide what champion the user should pick. """
    # Make sure Bryan plays his favorite champ
    if connection.is_bryan:
        return "yuumi"

    # First check current pick intent
    pick: str = connection.pick_intent
    if is_valid_pick(connection, pick):
        return pick

    # If current pick intent isn't valid, loop through user's config to find a champ to pick
    options: list[str] = u.get_backup_config_champs(connection.get_assigned_role())
    for pick in options:
        is_valid: bool = is_valid_pick(connection, pick)
        if is_valid:
            return pick
    # Last config option isn't valid
    if not is_valid:
        raise RuntimeError("Unable to find a valid champion to pick.")

    return pick


def decide_ban(connection: c.Connection) -> str:
    """ Decide what champion the user should ban. """
    # Make sure Bryan bans his least favorite champ
    if connection.is_bryan:
        return "kayn"

    # First check current ban intent
    ban = connection.ban_intent
    if is_valid_ban(connection, ban):
        return ban

    # If current ban intent isn't valid, loop through user's config to find a champ to ban
    options = u.get_backup_config_champs(connection.get_assigned_role(), False)
    for ban in options:
        if is_valid_ban(connection, ban):
            return ban

    # Last config option isn't valid
    if not is_valid_ban(connection, ban):
        # Unlike with picking a champ, having no ban doesn't stop user from being able to play, so just
        # raise a warning instead of an exception
        warnings.warn("Unable to find a valid champion to ban.", RuntimeWarning)
    return ban


def wait_before_locking(connection: c.Connection, mode: str) -> None:
    """ Wait to lock in or ban a champ if the user specified a lock-in delay in their config. """
    if connection.lock_in_delay == 0:
        return

    display_mode: str = "banning" if mode == "ban" else "picking"
    u.print_and_write(f"\nWaiting {connection.lock_in_delay} seconds before {display_mode}...\n")

    start_time: float = time.time()
    still_waiting: bool = True

    while still_waiting:
        # TODO: Check # of seconds left on timer, lock in/ban if timer is ending soon
        time.sleep(1)

        # Check if enough time elapsed
        if time.time() > start_time + connection.lock_in_delay:
            still_waiting = False

        update_champselect(connection)

        # Check if user manually completed the action
        if (mode == "ban" and connection.ban_action["completed"]
                or mode == "pick" and connection.pick_action["completed"]):
            still_waiting = False

        # Check if someone dodged the lobby
        if mode == "skip":
            still_waiting = False


def send_runes_and_summs(connection: c.Connection) -> None:
    """ Get the recommended rune page and summoner spells and send them to the client. """
    # Get assigned role
    role_name: str = connection.get_assigned_role()

    champid: int = connection.api_get("current_champ").json()
    champ_name: str = connection.get_champ_name_by_id(champid)

    ##### Get runes to be sent #####
    if not connection.runes_chosen and connection.should_modify_runes:
        # Get the runepage to use
        current_runepage, should_overwrite = get_runepage(connection, champ_name)
        endpoint = connection.endpoints["send_runes"] + str(current_runepage["id"])

        # Get recommended runes and summs
        recommended_runepage: dict = connection.get_recommended_runepage(champid, role_name)[0]

        if should_overwrite:
            # Set the name for the rune page
            if role_name == "utility":
                role_name = "support"
            name = f"{connection.RUNEPAGE_PREFIX} {champ_name} {role_name} runes"
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

        ##### Send the chosen runes #####
        response = connection.api_put(endpoint, request_body)
        try:
            if response.status_code == 400:
                u.print_and_write("Error code:", response.json())
        except Exception as e:
            u.print_and_write("An exception occured while trying to send runes:", e)

        flash: int = 4
        ghost: int = 1
        cleanse: int = 6
        d: int = 0  # index of left summoner spell (bound to D by default)
        f: int = 1  # index of right summoner spell (bound to F by default)

        summs = recommended_runepage["summonerSpellIds"]
        # Make sure Bryan always takes ghost/cleanse (he needs it)
        if connection.is_bryan:
            summs[d], summs[f] = ghost, cleanse

        # Make sure flash is always on F (higher winrate fr) https://www.leagueofgraphs.com/stats/flash-d-vs-f
        if summs[d] == flash:
            summs[d], summs[f] = summs[f], flash

        ##### Send summoner spells #####
        if connection.should_modify_runes or connection.is_bryan:
            request_body = {
                "spell1Id": summs[d],
                "spell2Id": summs[f]
            }
            connection.api_patch("send_summs", request_body)
            connection.runes_chosen = True


def get_actionid(connection: c.Connection, mode: str) -> int | None:
    """ Get the user's actionid from the current Champselect action. """
    try:
        action = connection.ban_action if mode == "ban" else connection.pick_action
        return action["id"]

    except Exception as e:
        warnings.warn(f"Unable to {mode} the specified champion: {e}", RuntimeWarning)
        return None


def get_champselect_phase(connection: c.Connection) -> str:
    """ Get the name of the current champselect phase. """
    phase = connection.session["timer"]["phase"]

    # If someone dodged, phase will be None, causing an error - return "skip" to handle this
    if phase is None:
        u.print_and_write("Champselect phase is 'None' - did someone dodge?")
        return "skip"
    return phase


def get_runepage(connection: c.Connection, champ_name: str) -> tuple[dict, bool]:
    """
    Figure out which runepage to overwrite or use.
    Returns:
        a tuple containing the runepage data (dictionary), and a bool indicating whether it should be overwritten
            (True) or used as-is (False)
    """
    to_return: None | tuple[dict, bool] = None
    auto_page_name: str
    prefix = connection.RUNEPAGE_PREFIX

    # First, check if this script has already created a runepage
    all_pages: list[dict] = connection.get_runepages()

    for page in all_pages:
        page_name: str = page["name"]
        clean_page_name: str = u.clean_name(connection.all_champs, page_name, False)

        # If rune page with champ name is found
        if champ_name in clean_page_name:
            # If rune page was user-created
            if not page_name.startswith(prefix):
                u.print_and_write(f"Runepage '{page_name}' has '{champ_name}' in it. Using this runepage...")
                return page, False
            # If the page was created by this script, keep looking for a user-created one
            else:
                auto_page_name = page_name
                to_return = page, False

        # If rune page with this script's naming scheme is found (that has *not* been modified by the player)
        elif page_name.startswith(prefix):
            auto_page_name = page_name
            # don't return here, because we might find a user-created rune page in a future iteration of this
            # loop that contains the champ's name
            to_return = page, True

    # If we found a page created by this script, return it now
    if to_return is not None:
        # If the runepage is being overwritten
        if to_return[1]:
            u.print_and_write(f"Runepage '{auto_page_name}' was created by this script - overwriting...")
        # Using rune page without modifying (it has the user's champ name in it already, could have been modified
        # by the user, so leave it alone)
        return to_return

    # No pages have been created by this script - try to create a new one
    u.print_and_write("No runepage created by this script was found. Trying to create a new one...")
    request_body = {
        "current": True,
        "isTemporary": False,
        "name": "temp",
        "order": 0,
    }
    response = connection.api_post("runes", request_body)
    if response.status_code == 200:
        # Success - the runepage was created successfully. Now return its data
        u.print_and_write(f"Success! Created a rune page with id {response.json()["id"]}")
        return response.json(), True

    # No empty rune page slots
    elif response.status_code == 400:
        response_msg: str = response.json()["message"]
        if response_msg != "Max pages reached":
            raise RuntimeError(f"An error occured while trying to create a rune page: {response_msg}")

        # Full of rune pages - return the id of one to overwrite (the last one)
        page = all_pages[-1]
        u.print_and_write(f"No room for new rune pages - overwriting page named {page["name"]}, " +
                          f"with id {page["id"]}")
        return page, True

    else:
        raise RuntimeError("An unknown error occured while trying to create a runepage.")


def is_valid_pick(connection: c.Connection, champ_name: str) -> bool:
    """ Check if the given champion can be picked. """
    # Handle empty input - allows user to skip selecting a champion and default to those in the config
    if not champ_name:
        return False

    champ_name = u.clean_name(connection.all_champs, champ_name)
    champid: int = connection.get_champid(champ_name)
    error_msg: str = "Invalid pick:"

    # If champ has already been checked, and was invalid
    if champid in connection.invalid_picks:
        u.print_and_write(error_msg, "in list of invalid champs")
        connection.invalid_picks.add(champid)
        return False

    # If champ is banned
    if is_banned(connection, champid):
        u.print_and_write(error_msg, "banned")
        connection.invalid_picks.add(champid)
        return False

    # If user doesn't own the champ
    if champ_name not in connection.owned_champs:
        u.print_and_write(error_msg, f"{u.capitalize(champ_name)} is unowned.")
        connection.invalid_picks.add(champid)
        return False

    # If a player has already PICKED the champ (hovering is ok)
    if champid in get_champ_pickids(connection):
        u.print_and_write(error_msg, f"{u.capitalize(champ_name)} has already been picked")
        connection.invalid_picks.add(champid)
        return False


    # If the user got assigned a role other than the one they queued for, disregard the champ they picked
    # This does nothing when queuing for gamemodes that don't have assigned roles
    assigned_role = connection.get_assigned_role()
    if (len(assigned_role) != 0  # assigned role exists
            # and role user queued for doesn't match
            and (connection.user_role != assigned_role and connection.user_role)
            # and champ user picked is the pick in question
            and (connection.user_pick == champ_name and connection.user_pick)):
        u.print_and_write(error_msg, "autofilled")
        connection.invalid_picks.add(champid)
        return False
    return True


def is_valid_ban(connection: c.Connection, champ: str) -> bool:
    """ Check if the specified champion can be banned. """
    # Handle empty input - allows user to skip selecting a champion and default to those in the config
    if not champ:
        return False

    champid = connection.get_champid(champ)
    champ = u.clean_name(connection.all_champs, champ)
    error_msg = "Invalid ban:"

    # If trying to ban the champ the user wants to play
    if champ == connection.pick_intent or champ == connection.user_pick:
        u.print_and_write(error_msg, f"user intends to play {champ}")
        return False

    # If champ is already banned
    if is_banned(connection, champid):
        u.print_and_write(error_msg, f"{champ} is already banned")
        return False

    # If a teammate is hovering the champ
    if teammate_hovering(connection, champid):
        u.print_and_write(error_msg, f"teammate already hovering {champ}")
        return False

    return True


def is_banned(connection: c.Connection, champid: int) -> bool:
    """ Check if the given champion is banned. """
    return champid in get_banned_champids(connection)


def teammate_hovering(connection: c.Connection, champid: int) -> bool:
    """ Check if the given champion is being hovered by a teammate. """
    return champid in get_teammate_hoverids(connection)


def is_currently_picking(connection: c.Connection) -> bool:
    """ Return a bool indicating whether or not the user is currently picking. """
    return connection.pick_action.get("isInProgress", False)


def is_currently_banning(connection: c.Connection) -> bool:
    """ Return a bool indicating whether or not the user is currently banning. """
    return connection.ban_action.get("isInProgress", False)


def is_hovering(connection: c.Connection) -> bool:
    """ Return a bool indicating whether or not the player is currently hovering a champ. """
    return get_current_hoverid(connection) != 0


def get_banned_champids(connection: c.Connection) -> list[int]:
    """ Get a list of all champion ids that have been banned. """
    return connection.session["bans"]["myTeamBans"] + connection.session["bans"]["theirTeamBans"]


def get_current_hoverid(connection: c.Connection) -> int:
    """ Get the id number of the champ the player is currently hovering. """
    return connection.pick_action.get("championId", 0)


def get_champ_pickids(connection: c.Connection) -> list[int]:
    """ Return a list of champion ids that players have locked in. """
    champids: list[int] = []
    for champ, is_enemy, is_hovering in get_all_player_champids(connection):
        if not is_hovering:
            champids.append(champ)
    return champids


def get_teammate_hoverids(connection: c.Connection) -> list[int]:
    """ Return a list of champion ids that teammates are hovering. """
    champids: list[int] = []
    for champ, is_enemy, is_hovering in get_all_player_champids(connection):
        if not is_enemy and is_hovering:
            champids.append(champ)
    return champids


def get_all_player_champids(connection: c.Connection) -> list[tuple[int, bool, bool]]:
    """
    Return a list of tuples. Each tuple contains a player's champ id, a bool indicating whether they are on the
    enemy team, and a bool hovering (True) or have already picked (False) the champion with the specified ID.
    """
    champids: list[tuple[int, bool, bool]] = []
    # Actions are grouped by type (pick, ban, etc.), so we iterate over each group
    for action_group in connection.all_actions:
        for action in action_group:
            # Only look at pick actions, and only on user's team that aren't the user
            if action["type"] == "pick" and action["actorCellId"] != connection.get_localcellid():
                champid: int = action["championId"]

                # If champid is 0, the player isn't hovering a champ
                if champid != 0:
                    # If the action isn't completed, they're still hovering
                    champids.append((champid, not action["isAllyAction"], not action["completed"]))
    return champids


def update_champ_intent(connection: c.Connection) -> None:
    """ Update instance variables with up-to-date pick, ban, and role intent, and hover the champ to be locked. """
    ##### Update pick intent #####
    if not connection.has_picked:
        last_intent: str = connection.pick_intent
        connection.pick_intent = decide_pick(connection)

        # Only print pick intent if it's different from the last loop iteration
        if last_intent != connection.pick_intent:
            connection.has_printed_pick = False

        if not connection.has_printed_pick:
            u.print_and_write(f"{'\t' * connection.indentation}Pick intent: {u.capitalize(connection.pick_intent)}")
            connection.has_printed_pick = True

    ##### Update ban intent #####
    if not connection.has_banned:
        last_intent: str = connection.ban_intent
        connection.ban_intent = decide_ban(connection)

        # Only print ban intent if it's different from the last loop iteration
        if last_intent != connection.ban_intent:
            connection.has_printed_ban = False

        if not connection.has_printed_ban:
            u.print_and_write(f"{'\t' * connection.indentation}Ban intent: {u.capitalize(connection.ban_intent)}")
            connection.has_printed_ban = True


def update_champselect(connection: c.Connection) -> None:
    """ Update all champselect session data. """
    connection.session = connection.get_session()
    if get_champselect_phase(connection) != "FINALIZATION":  # skip unnecessary API calls
        connection.all_actions = connection.session["actions"]
        # Look at each action, and return the one with the corresponding cellid
        for action_group in connection.all_actions:
            for action in action_group:
                if action["actorCellId"] == connection.get_localcellid():
                    if action["type"] == "ban":
                        connection.ban_action = action

                    elif action["type"] == "pick":
                        connection.pick_action = action

        update_champ_intent(connection)