import connect
import time
c = connect.Connection()
in_game = False
last_action = None
last_gamestate = None

# temp
summoner_id = 42069
endpoints = {
    "gamestate": "/lol-gameflow/v1/gameflow-phase",  # GET
    "start_queue": "/lol-lobby/v2/lobby/matchmaking/search",  # POST
    "match_found": "/lol-matchmaking/v1/ready-check",  # GET
    "accept_match": "/lol-matchmaking/v1/ready-check/accept",  # POST
    "champselect_session": "/lol-champ-select/v1/session",  # GET
    "champselect_action": "/lol-champ-select/v1/session/actions/",  # PATCH
    "owned_champs": "/lol-champions/v1/owned-champions-minimal",  # GET
    "current_summoner": "/lol-summoner/v1/current-summoner",  # GET
    "all_champs": f"/lol-champions/v1/inventories/{summoner_id}/champions",  # GET
    "pickable_champs": "/lol-champ-select/v1/pickable-champions"  # GET
}


def save_to_file(header, text):
    with open("C:/Users/jamo0/Desktop/text.txt", "w") as file:
        string = f"{header}: \n{text}\n"
        file.write(string)
        print(string)


while not in_game:
    time.sleep(1)
    gamestate = c.api_get("gamestate")

    # Print current gamestate if it's different from the last one
    if gamestate != last_gamestate:
        save_to_file("Current gamestate", gamestate)
        last_gamestate = gamestate


    match gamestate:
        case "Lobby":
            c.reset_after_dodge()

        case "ReadyCheck":
            c.reset_after_dodge()
            c.accept_match()

        case "ChampSelect":
            session = c.get_session()

            my_cellid = c.get_localcellid()
            action = c.find_action()
            action_type = action["type"]

            # Print current action if it's different from the last one
            if action_type != last_action:
                save_to_file(f"Current champselect phase", action_type)
            last_action = action_type
            save_to_file("Action type: ", action_type)

            match action_type:
                case "pick":
                    if c.can_pick(action):
                        c.lock_champ()
                case "ban":
                    if not c.has_banned:
                        c.ban_champ()
                case default:
                    pass

        # End loop if a game starts
        case "InProgress":
            in_game = True

        case default:
            pass