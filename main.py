import connect
import time
c = connect.Connection()
in_game = False
last_action = None
last_gamestate = None
last_phase = None
last_session = None

output_filepath = "C:/Users/jamo0/Desktop/text2.json"

def save_to_file(header, text):
    with open(output_filepath, "a") as file:
        string = f"{header}: {text}\n"
        file.write(string)
        print(string)
        file.close()


# Initialize output file
with open(output_filepath, "w") as file:
    file.write("Champ select data: \n")

while not in_game:
    time.sleep(2)
    gamestate = c.api_get("gamestate")

    # Print current gamestate if it's different from the last one
    if gamestate != last_gamestate:
        save_to_file("Current gamestate", gamestate)
        last_gamestate = gamestate


    match gamestate:
        case "Lobby":
            c.reset_after_dodge()

        case "ReadyCheck":
            c.accept_match()

        case "ChampSelect":
            session = c.get_session()

            action = c.find_action()
            action_type = action["type"]
            champselect_phase = session["timer"]["phase"]

            # Print current status if it's different from the last one
            if session != last_session:
                save_to_file("Sesssion", session)
            # if action_type != last_action:
                save_to_file("Current action type", action_type)
            # if champselect_phase != last_phase:
                save_to_file("Current champselect phase", champselect_phase)

            # Store this phase and action type to compare to on the next loop (avoid re-printing the same information)
            last_session = session
            last_action = action_type
            last_phase = champselect_phase

            # Handle each champ select phase

            match action_type:
                case "ban":
                    if not c.has_hovered:
                        c.hover_champ()
                    if not c.has_banned:
                        c.ban_champ()
                case "pick":
                    if c.can_pick(action):
                        c.lock_champ()
                case default:
                    pass
        # End loop if a game starts
        case "InProgress":
            in_game = True

        case default:
            pass