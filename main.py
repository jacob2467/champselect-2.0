import connect
import time
c = connect.Connection()
in_game = False
last_action = None
last_gamestate = None

output_filepath = "C:/Users/jamo0/Desktop/text.txt"

def save_to_file(header, text):
    with open(output_filepath, "a") as file:
        string = f"{header}: \n{text}\n"
        file.write(string)
        print(string)


# Initialize output file
with open(output_filepath, "w") as file:
    file.write("Champ select data: \n")

while not in_game:
    time.sleep(1)
    gamestate = c.api_get("gamestate")

    # Print current gamestate if it's different from the last one
    if gamestate != last_gamestate:
        save_to_file("Current gamestate", gamestate)
        last_gamestate = gamestate


    match gamestate:
        case "Lobby":
            pass

        case "ReadyCheck":
            c.reset_after_dodge()
            c.accept_match()

        case "ChampSelect":
            session = c.get_session()

            action = c.find_action()
            action_type = action["type"]

            # Print current action if it's different from the last one
            if action_type != last_action:
                save_to_file(f"Current champselect phase", action_type)
            last_action = action_type
            save_to_file("Action type: ", action_type)

            # Handle each champ select phase
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