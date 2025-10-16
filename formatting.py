def gamestate(gamestate: str) -> str:
    """ Format the gamestate to be more readable for the user, e.g. 'None' -> 'Main Menu' """
    match gamestate:
        case "None":
            return "Main Menu"
        case "Matchmaking":
            return "In Queue"
        case "ReadyCheck":
            return "Ready Check"
        case "ChampSelect" | "FINALIZATION":
            return "Champselect"
        case _:
            return gamestate


def phase(phase: str) -> str:
    """ Format the champselect phase to be more readable for the user, e.g. 'BAN_PICK' -> 'Pick/Ban' """
    match phase:
        case "PLANNING":
            return "Planning"
        case "BAN_PICK":
            return "Pick/Ban"
        case "FINALIZATION":
            return "Loadout Selection"
        case _:
            return "None"


def role(role: str) -> str:
    """ Format the user's role, e.g. 'utility' -> 'Support' """
    match role:
        case "middle":
            return "Mid"
        case "utility":
            return "Support"
        case "bottom":
            return "ADC"
        case _:
            return capitalize(role)


def clean_name(all_champs: dict[str, int], name: str, should_filter: bool = True) -> str:
    """
    Remove whitespace and special characters from a champion's name.
    Example output:
        Aurelion Sol -> aurelionsol
        Bel'Veth -> belveth

    Args:
        all_champs: champions that have already been processed
        name: the name to clean
        should_filter: if True, return "invalid" when an invalid champion name is passed
    """
    if not name:
        return name
    # Remove all illegal characters and whitespace
    name = clean_string(name)

    # Handle edge cases (Nunu and Willump -> nunu and Wukong -> monkeyking)
    if "nunu" in name:
        return "nunu"
    elif name == "wukong":
        return "monkeyking"

    if not should_filter:
        return name

    # Filter out invalid resulting names
    return name if name in all_champs else "invalid"


def clean_string(string: str) -> str:
    """ Remove whitespace and illegal characters from a string, and convert it to lowercase. """
    illegal = (" ", "'", ".")
    new_string = ""
    for char in string:
        if char not in illegal:
            new_string += char.lower()
    return new_string


def champ(name: str) -> str:
    """ Format a champion name for user-facing display. """
    # This method is intended to be used only for display to the user; clean_name is used internally
    # TODO: Implement this (and then actually use it)
    # for now just capitalize it
    return capitalize(name)


def capitalize(string: str) -> str:
    """ Capitalize the first letter in a string. """
    return string[:1].upper() + string[1:]