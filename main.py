import connect
import requests
import time
import utility as u

connection_initiated: bool = False
in_game: bool = False
last_gamestate: str = ""  # Store last gamestate - used to skip redundant API calls and print statements
champselect_loop_iteration: int = 0  # Keep track of how many loops run during champselect

# Whether or not to print debug info
SHOULD_PRINT: bool = u.get_config_option_bool("settings", "print_debug_info")

# How many seconds to wait after a failed attempt to connect to the client
RETRY_RATE: float = float(u.get_config_option_str("settings", "retry_rate"))

# How many seconds to wait before re-running the main loop
UPDATE_INTERVAL: float = float(u.get_config_option_str("settings", "update_interval"))

MSG_CLIENT_CONNECTION_FAILURE: str = (f"Failed to connect to the league client - "
                                      f"is it open? Retrying in {RETRY_RATE} seconds...")

# Clear output file
with open("output.log", "w") as file:
    pass

# Wait for client to open if it's not open already
while not connection_initiated:
    try:
        c = connect.Connection()
        connection_initiated = True
    # If the connection isn't successful or the lockfile doesn't exist, the client isn't open yet
    except (requests.exceptions.ConnectionError, FileNotFoundError) as e:
        u.print_and_write(MSG_CLIENT_CONNECTION_FAILURE)
        time.sleep(RETRY_RATE)

    except KeyError as e:
        # Client is still loading, try again until it finishes loading
        pass

c.populate_champ_table()
c.get_first_choices()
while not in_game:
    time.sleep(UPDATE_INTERVAL)
    # Wrap the loop in a try block to catch errors when the client closes
    try:
        gamestate: str = c.get_gamestate()
        gamestate_has_changed: bool = gamestate != last_gamestate

        # Print current gamestate if it's different from the last one
        if gamestate_has_changed:
            u.print_and_write(f"\nCurrent gamestate: {gamestate}")
            last_gamestate = gamestate

        match gamestate:
            case "Lobby":
                if gamestate_has_changed:
                    c.start_queue()
                    # c.reset_after_dodge()  # for testing the script in custom games, unnecessary for real games

            case "ReadyCheck":
                if gamestate_has_changed:
                    c.update_primary_role()
                    c.accept_match()
                    c.reset_after_dodge()
                    champselect_loop_iteration = 1

            case "ChampSelect":
                # Wrap in try block to catch KeyError when someone dodges - champselect actions don't exist anymore
                try:
                    c.update_champselect()
                    phase = c.get_champselect_phase()
                except KeyError:
                    phase = "skip"

                champselect_loop_iteration += 1
                if SHOULD_PRINT:
                    u.print_and_write(f"\nChampselect loop #{champselect_loop_iteration}:")
                    u.print_and_write("\tChampselect phase:", phase)

                # Handle each champ select phase separately
                match phase:
                    case "PLANNING":
                        c.hover_champ()
                    case "BAN_PICK":
                        c.ban_or_pick()
                    case "FINALIZATION":
                        c.send_runes_summs()
                    case "skip":
                        pass

            # End loop if a game starts
            case "InProgress":
                in_game = True

            case default:
                pass
    except requests.exceptions.ConnectionError:
        u.print_and_write(MSG_CLIENT_CONNECTION_FAILURE)
        c.parse_lockfile(RETRY_RATE)