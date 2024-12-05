import connect
import requests
import time
c = connect.Connection()
in_game = False
last_action = None
last_gamestate = None
last_phase = None
last_session = None

while not in_game:
    time.sleep(1)
    # Wrap the loop in a try block to catch errors when the client closes
    try:
        gamestate = c.api_get("gamestate").json()

        # Print current gamestate if it's different from the last one
        if gamestate != last_gamestate:
            print("Current gamestate:", gamestate)
            last_gamestate = gamestate


        match gamestate:
            case "Lobby":
                c.start_queue()
                c.reset_after_dodge()
                # TODO: Start queue

            case "ReadyCheck":
                c.accept_match()
                # pass

            case "ChampSelect":
                # Stop error that can happen if this block of code is run immediately after someone dodges
                try:
                    phase = c.get_champselect_phase()
                    c.update_actions()
                    c.update_intent()
                    print("Champselect phase:", phase)
                except Exception as e:
                    print("There was an error, did someone dodge?\n", e)
                    phase = "skip"


                # Handle each champ select phase
                match phase:
                    case "PLANNING":
                        c.hover_champ()
                    case "BAN_PICK":
                        c.ban_or_pick()
                    case "FINALIZATION":
                        c.send_runes()
                        c.send_summs()
                    case "skip":
                        pass

            # End loop if a game starts
            case "InProgress":
                in_game = True

            case default:
                pass
    except requests.exceptions.ConnectionError:
        print("Connection error. Did you close the league client?")
        c.parse_lockfile()