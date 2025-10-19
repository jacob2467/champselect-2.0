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
    """ Format a champion name for user-facing display. Does NOT perform input validation. """
    # This method is intended to be used only for display to the user; clean_name is used internally
    # There may be an endpoint provided by the LCU API for this, but this is good enough (for now ?).
    name = capitalize(name)
    match name:
        case "Belveth" | "Kaisa" | "Reksai" | "Kogmaw" | "Velkoz":
            return format_void_champ(name)

        case "Nunu":
            return "Nunu and Willump"

        case "Monkeyking":
            return "Wukong"

        case "Twistedfate":
            return "Twisted Fate"

        case "Xinzhao":
            return "Xin Zhao"

        case "Leblanc":
            return "LeBlanc"

        case "Masteryi":
            return "Master Yi"

        case "Missfortune":
            return "Miss Fortune"

        case "Drmundo":
            return "Dr. Mundo"

        case "Jarvaniv":
            return "Jarvan IV"

        case "Leesin":
            return "Lee Sin"

        case "Aurelionsol":
            return "Aurelion Sol"

        case "Tahmkench":
            return "Tahm Kench"

        case "Neeko":
            return "Not Neeko"

        case "Ksante":
            return "K'Sante"

        case _:
            return name


def format_void_champ(name: str) -> str:
    """
    Format the specified void champion's name for user-facing display.
    Examples:
        - Belveth -> Bel'Veth
        - Kaisa -> Kai'Sa
    """
    return f"{name[:3]}'{capitalize(name[3:])}"


def capitalize(string: str) -> str:
    """ Capitalize the first letter in a string. """
    return string[:1].upper() + string[1:]