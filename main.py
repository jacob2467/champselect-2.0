import time
import requests

import utility as u
import connect as c
import champselect
import lobby
import userinput


# Whether or not to print debug info
SHOULD_PRINT: bool = u.get_config_option_bool("settings", "print_debug_info")

# How many seconds to wait after a failed attempt to connect to the client
RETRY_RATE: float = float(u.get_config_option_str("settings", "retry_rate"))

# How many seconds to wait before re-running the main loop
UPDATE_INTERVAL: float = float(u.get_config_option_str("settings", "update_interval"))

MSG_CLIENT_CONNECTION_FAILURE: str = (f"Failed to connect to the league client - "
                                      f"is it open? Retrying in {RETRY_RATE} seconds...")

connection: c.Connection
def initialize_connection() -> c.Connection:
    # Clear output file
    with open("output.log", "w") as file:
        pass

    # Wait for client to open if it's not open already
    while True:
        try:
            connection = c.Connection(int(SHOULD_PRINT))
            initialize_connection_vars(connection)
            connection.populate_champ_table()
            userinput.get_first_choices()
            return connection

        # If the connection isn't successful or the lockfile doesn't exist, the client isn't open yet
        except (requests.exceptions.ConnectionError, FileNotFoundError):
            u.print_and_write(MSG_CLIENT_CONNECTION_FAILURE)
            time.sleep(RETRY_RATE)

        except KeyError:
            # Client is still loading, try again until it finishes loading
            pass

def initialize_connection_vars(con: c.Connection):
    for module in champselect, lobby, userinput:
        module.set_connection(con)
    global connection
    connection = con

def handle_lobby(gamestate_has_changed: bool):
    if gamestate_has_changed:
        lobby.start_queue()
        lobby.reset_after_dodge()

def handle_readycheck(gamestate_has_changed: bool):
    if gamestate_has_changed:
        connection.update_primary_role()
        lobby.reset_after_dodge()
        lobby.accept_match()
        champselect_loop_iteration = 1

def handle_champselect(champselect_loop_iteration: int):
    # Wrap in try block to catch KeyError when someone dodges - champselect actions don't exist anymore
    try:
        champselect.update_champselect()
        phase = champselect.get_champselect_phase()
    except KeyError:
        phase = "skip"

    if SHOULD_PRINT:
        u.print_and_write(f"\nChampselect loop #{champselect_loop_iteration}:")
        u.print_and_write("\tChampselect phase:", u.map_phase_for_display(phase))

    # Handle each champ select phase separately
    match phase:
        case "PLANNING":
            champselect.hover_champ()
        case "BAN_PICK":
            champselect.ban_or_pick()
        case "FINALIZATION":
            champselect.send_runes_and_summs()
        case "skip":
            pass

def main_loop() -> None:
    champselect_loop_iteration: int = 0  # Keep track of how many loops run during champselect
    in_game: bool = False
    gamestate: str = ""
    last_gamestate: str = ""  # Store last gamestate - used to skip redundant API calls and print statements
    gamestate_has_changed: bool = False
    while not in_game:
        time.sleep(UPDATE_INTERVAL)
        # Wrap the loop in a try block to catch errors when the client closes
        try:
            gamestate = connection.get_gamestate()
            gamestate_has_changed = gamestate != last_gamestate

            # Print current gamestate if it's different from the last one
            if gamestate_has_changed:
                u.print_and_write(f"\nCurrent gamestate: {u.map_gamestate_for_display(gamestate)}")
                last_gamestate = gamestate

            match gamestate:
                case "Lobby":
                    handle_lobby(gamestate_has_changed)

                case "ReadyCheck":
                    handle_readycheck(gamestate_has_changed)

                case "ChampSelect":
                    champselect_loop_iteration += 1
                    handle_champselect(champselect_loop_iteration)

                # End loop if a game starts
                case "InProgress":
                    in_game = True

        except requests.exceptions.ConnectionError:
            u.print_and_write(MSG_CLIENT_CONNECTION_FAILURE)
            connection.parse_lockfile(RETRY_RATE)

if __name__ == "__main__":
    initialize_connection()
    main_loop()