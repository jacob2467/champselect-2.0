import connect as c
import utility as u
import formatting


FLASH: int = 4
GHOST: int = 1
CLEANSE: int = 6
D: int = 0  # index of left summoner spell (bound to D by default)
F: int = 1  # index of right summoner spell (bound to F by default)

def send_runes_and_summs(connection: c.Connection) -> None:
    """ Get the recommended rune page and summoner spells and send them to the client. """
    # Prevent redundant API calls - early return if we've already sent runes, or the user doesn't want us to.
    if connection.runes_chosen or not connection.should_modify_runes:
        if not connection.is_bryan:  # only return if not Bryan
            return

    # Get runes and summoner spells to send
    request_body, summoner_spells = build_runepage_request(connection)

    # Send the chosen runes
    endpoint = connection.endpoints["send_runes"] + str(request_body["id"])
    response = connection.api_put(endpoint, request_body)
    if response.status_code == 400:
        u.print_and_write(f"Unable to send runes to the client; received response {response.json()}")

    # Send summoner spells
    if connection.should_modify_runes or connection.is_bryan:
        request_body = {
            "spell1Id": summoner_spells[D],
            "spell2Id": summoner_spells[F]
        }
        connection.api_patch("send_summs", request_body)
    connection.runes_chosen = True

def build_runepage_request(connection: c.Connection) -> tuple[dict, list[int]]:
    """
    Build an HTTP request body for setting the user's rune page and summoner spells.
    Returns:
        a tuple containing the HTTP request (dictionary), and a list of summoner spell IDs.
    """
    # Check pick intent if we haven't locked yet
    if connection.get_gamestate() == "ChampSelect":
        champ_name: str = connection.pick_intent
        champid: int = connection.get_champid(champ_name)

    # If we already locked in, check what champ was locked using API (in case user picks something besides pick intent)
    else:
        champid: int = connection.api_get("current_champ").json()  # this endpoint only works after locking
        champ_name = connection.get_champ_name_by_id(champid)

    role_name: str = connection.get_assigned_role()

    # Get the runepage to use
    current_runepage, should_overwrite = pick_from_existing_runepages(connection, champ_name)

    # Get recommended runes and summs
    recommended_runepage: dict = get_recommended_runepage(connection, champid, role_name)[0]
    summoner_spells: list[int] = get_recommended_spells(connection.is_bryan, recommended_runepage["summonerSpellIds"])

    # If we're not modifying the rune page, just return it as-is
    if not should_overwrite:
        return current_runepage, summoner_spells

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

    return request_body, summoner_spells

def pick_from_existing_runepages(connection: c.Connection, champ_name: str) -> tuple[dict, bool]:
    """
    Figure out which runepage to overwrite or use.
    Returns:
        a tuple containing the runepage data (dictionary), and a bool indicating whether it should be overwritten
            (True) or used as-is (False)
    """
    to_return: None | tuple[dict, bool] = None
    auto_page_name: str
    prefix = connection.RUNEPAGE_PREFIX

    all_pages: list[dict] = get_existing_runepages(connection)

    for page in all_pages:
        page_name: str = page["name"]
        clean_page_name: str = formatting.clean_name(connection.all_champs, page_name, False)

        # If rune page with this script's naming scheme is found
        if page_name.startswith(prefix):
            should_overwrite: bool = False if champ_name in clean_page_name else True
            # Don't return here - might find a matching user-created runepage later...
            auto_page_name = page_name
            to_return = page, should_overwrite  # ... but save it in case we don't

        # Page not made by this script
        elif champ_name in clean_page_name:
            # This is a user-created rune page for the champ they're playing - return it immediately
            u.print_and_write(f"Runepage '{page_name}' has '{champ_name}' in it. Using this runepage...")
            return page, False


    # If we found a page created by this script, return it now
    if to_return is not None:
        # If the runepage is being overwritten
        if to_return[1]:
            u.print_and_write(f"Runepage '{auto_page_name}' was created by this script - overwriting...")
        # Using rune page without modifying (it has the user's champ name in it already, could have been modified
        # by the user, so leave it alone)
        return to_return

    # Try to create a new rune page and return it
    return create_new_runepage(connection, all_pages), True

def get_recommended_runepage(connection, champid: int, position: str) -> dict:
    """
    Get the recommended runepage from the client.
    Args:
        champid: the id number of the champion to get runes for
        position: the position the user is playing
    """
    endpoint: str = get_rune_recommendation_endpoint(champid, position)
    return connection.api_get(endpoint).json()

def get_recommended_spells(is_bryan: bool, summoner_spells: list[int]) -> list[int]:
    """
    "Fix" the user's summoner spells by modifying the list in-place:
        * If the user is taking flash, make sure it's on F (it has a higher winrate)
        * If the user is Bryan, make sure he takes ghost/cleanse
    Returns:
        the modified list
    """

    # Make sure Bryan always takes ghost/cleanse (he needs it)
    if is_bryan:
        summoner_spells[D], summoner_spells[F] = GHOST, CLEANSE

    # Make sure flash is always on F https://www.leagueofgraphs.com/stats/flash-d-vs-f
    if summoner_spells[D] == FLASH:
        summoner_spells[D], summoner_spells[F] = summoner_spells[F], FLASH

    return summoner_spells

def get_existing_runepages(connection) -> list[dict]:
    """ Get a list of the runepages the player currently has set. """
    response = connection.api_get("runes")
    if response.status_code == 200:
        return response.json()

    raise RuntimeError(f"Unable to get rune pages: {response}")

def create_new_runepage(connection: c.Connection, all_pages: list[dict]) -> dict:
    """
    Create a new (blank) runepage, and return its information. If unable to create one, return an existing one instead.
    """
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
        u.print_and_write(f"Success! Created a rune page with id {response.json()['id']}")
        return response.json()

    # No empty rune page slots
    elif response.status_code == 400:
        response_msg: str = response.json()["message"]
        if response_msg != "Max pages reached":
            raise RuntimeError(f"An error occured while trying to create a rune page: {response_msg}")

        # Full of rune pages - return the id of one to overwrite (the last one)
        page = all_pages[-1]
        u.print_and_write(f"No room for new rune pages - overwriting page named {page['name']}")
        return page

    else:
        raise RuntimeError("An unknown error occured while trying to create a runepage.")

def get_rune_recommendation_endpoint(champid: int, position: str) -> str:
    """
    Get the endpoint used to get recommended runes.
    Args:
        champid: the id number of the champion to get runes for
        position: the position the user is playing
    """
    mapid = 11  # mapid for summoner's rift
    return f"/lol-perks/v1/recommended-pages/champion/{champid}/position/{position}/map/{mapid}"