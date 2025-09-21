import utility as u
import connect as c

connection: c.Connection

def set_connection(con: c.Connection):
    """ Set up the global connection variable for this module. """
    global connection
    connection = con

def get_champ_name_input(prompt: str) -> str:
    """ Get user input for the name of a champion. """
    name: str = u.clean_name(connection.all_champs, input(prompt))
    while name == "invalid":
        name = u.clean_name(connection.all_champs, input("Invalid champion name! Please try again:  "))

    return name


def get_desired_role_input(prompt: str) -> str:
    """ Get user input for their desired role. """
    role: str = u.clean_role_name(prompt)
    while role == "invalid":
        role = u.clean_name(connection.all_champs, "Invalid role name! Please try again:  ")

    return role

def get_first_choices() -> None:
    """ Get the user's first choice for champion picks and bans, and ask them if they'd like the script to handle
    their runes and summoner spells.
    """
    # Pick choice
    connection.user_pick = get_champ_name_input("Who would you like to play?  ")

    # Ban choice
    connection.user_ban = get_champ_name_input("Who would you like to ban?  ")

    # Choose whether or not the script should handle runes and summoner spells
    connection.should_modify_runes = u.get_bool_input("Would you like the script to handle runes and summoner "
                                                "spells automatically? y/n:  ", True)

    # Set intent to user input (intent can change later if first choice is banned, etc.)
    connection.pick_intent = connection.user_pick
    connection.ban_intent = connection.user_ban
    connection.assigned_role = connection.user_role