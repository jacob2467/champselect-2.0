import connect as c

def start_queue(connection: c.Connection) -> None:
    """ Make an API call to start queueing for a match. """
    connection.api_post("start_queue")


def accept_match(connection: c.Connection) -> None:
    """ Make an API call to accept a match. """
    connection.api_post("accept_match")


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