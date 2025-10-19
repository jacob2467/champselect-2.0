import connect as c

def start_queue(connection: c.Connection) -> None:
    """ Make an API call to start queueing for a match. """
    connection.api_post("start_queue")


def accept_match(connection: c.Connection) -> None:
    """ Make an API call to accept a match. """
    connection.api_post("accept_match")


def create_lobby(connection: c.Connection, lobbytype: str) -> None:
    """ Create a lobby for the specified gamemode. """
    lobbyid: int
    match lobbytype:
        case "draft":
            lobbyid = 400
        case "ranked":
            lobbyid = 420
        case "flex":
            lobbyid = 440
        case "aram":
            lobbyid = 450
        case "arena":
            lobbyid = 1700
        case _:
            raise RuntimeError(f"invalid lobby type: {lobbytype}")
    response = connection.api_post('lobby', {'queueId': lobbyid})

def reset_after_dodge(connection: c.Connection) -> None:
    """ Reset class instance variables after someone dodges a lobby. """
    connection.has_picked = False
    connection.has_banned = False
    connection.runes_chosen = False
    connection.role_checked = False
    connection.has_printed_pick = False
    connection.has_printed_ban = False
    connection.pick_intent = connection.user_pick
    connection.ban_intent = connection.user_ban
    connection.assigned_role = connection.user_role
    connection.invalid_picks.clear()
    connection.invalid_bans.clear()