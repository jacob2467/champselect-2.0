import connect
import time
c = connect.Connection()
in_game = False
last_action = None
last_gamestate = None
last_phase = None
last_session = None

while not in_game:
    time.sleep(1)
    gamestate = c.api_get("gamestate").json()

    # Print current gamestate if it's different from the last one
    if gamestate != last_gamestate:
        print("Current gamestate:", gamestate)
        last_gamestate = gamestate


    match gamestate:
        case "Lobby":
            c.reset_after_dodge()
            # TODO: Start queue

        case "ReadyCheck":
            c.accept_match()

        case "ChampSelect":
            # Stop error that can happen if this block of code is run immediately after someone dodges
            session = c.get_session()
            phase = session["timer"]["phase"]
            c.update_actions()


            # Handle each champ select phase
            match phase:
                case "PLANNING":
                    # TODO: Check if already hovering a champ (NOT if hovered previously, in case of bans)
                    c.hover_champ()
                case "BAN_PICK":
                    c.ban_or_pick()
                case "FINALIZATION":
                    c.send_runes()
                    c.send_summs()

        # End loop if a game starts
        case "InProgress":
            in_game = True

        case default:
            pass