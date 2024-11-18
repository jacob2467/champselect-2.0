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

def find_action(actions, local_cellid):
    for action in actions:
        if action["actorCellId"] == local_cellid:
            return action
    return None



while not in_game:
    time.sleep(1)
    gamestate = c.api_get("gamestate")

    # Print current gamestate, only if it's different from the last one
    if gamestate != last_gamestate:
        print(f"Current gamestate: {gamestate}")
        last_gamestate = gamestate


    match gamestate:
        case "Lobby":
            c.reset_after_dodge()

        case "ReadyCheck":
            c.reset_after_dodge()
            c.accept_match()

        case "ChampSelect":
            session = c.api_get("champselect_session")

            my_cellid = session["localPlayerCellId"]
            action = find_action(session["actions"][0], my_cellid)
            action_type = action["type"]
            current_cellid = action["actorCellId"]

            # Print current action if it's different from the last one
            if action_type != last_action:
                print(f"Current champselect phase: {action_type}")
            last_action = action_type

            match action_type:
                case "pick":
                    if c.can_pick(my_cellid, action):
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