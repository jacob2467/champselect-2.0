import connect as c

connection: c.Connection

def set_connection(con: c.Connection):
    """ Set up the global connection variable for this module. """
    global connection
    connection = con

def start_queue() -> None:
    """ Start queueing for a match. """
    # Only want to start queue once - if user stops queue after, it shouldn't start again automatically
    if not connection.started_queue:
        connection.api_post("start_queue")
        connection.started_queue = True

def accept_match() -> None:
    """ Accept a match. """
    connection.api_post("accept_match")

def reset_after_dodge() -> None:
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