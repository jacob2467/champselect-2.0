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

def get_first_choices() -> None:
    """ Get the user's first choice for champion picks and bans, and ask them if they'd like the script to handle
    their runes and summoner spells.
    """
    # Pick choice
    connection.user_pick = get_champ_name_input("Who would you like to play?  ")

    # Ban choice
    connection.user_ban = get_champ_name_input("Who would you like to ban?  ")

    # Choose whether or not the script should handle runes and summoner spells
    connection.should_modify_runes = get_bool_input("Would you like the script to handle runes and summoner "
                                                "spells automatically? y/n:  ", True)

    # Set intent to user input (intent can change later if first choice is banned, etc.)
    connection.pick_intent = connection.user_pick
    connection.ban_intent = connection.user_ban
    connection.assigned_role = connection.user_role

def get_bool_input(prompt: str, default_answer: bool = False) -> bool:
    """ Get boolean input from the user. """
    response_str: str = ""
    while response_str not in ("y", "n"):
        response_str = input(prompt).lower()

        # Return default answer if user didn't answer
        if response_str == "":
            return default_answer

        # Normalize "yes" to "y", "no" to "n"
        if response_str in ("yes", "no"):
            response_str = response_str[0]

        # Change prompt after first loop
        prompt = "Invalid input! Please type y or n:  "

    # After the while loop, response_str is guaranteed to either be "y" or "n"
    return response_str == "y"