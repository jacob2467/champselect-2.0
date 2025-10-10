import requests
import time
import os

import utility as u
import connect as c
import champselect
import userinput
import runes
import lobby


# Whether or not to print debug info
SHOULD_PRINT: bool = u.get_config_option_bool("settings", "print_debug_info")

# How many seconds to wait before re-running the main loop
UPDATE_INTERVAL: float = float(u.get_config_option_str("settings", "update_interval"))

LOGFILE: str = "output.log"

MSG_ATTEMPT_RECONNECT: str = "Unable to connect to the League of Legends client. Retrying..."

def initialize_connection() -> c.Connection:
    """ Initialize a connection to the League client. """
    # Remove old log file if it exists
    try:
        os.remove(LOGFILE)
    except FileNotFoundError:
        pass

    # Wait for client to open if it's not open already
    while True:
        try:
            connection = c.Connection(int(SHOULD_PRINT))
            userinput.get_first_choices(connection)
            return connection

        # If the connection isn't successful or the lockfile doesn't exist, the client isn't open yet
        except (requests.exceptions.ConnectionError, FileNotFoundError, KeyError):
            u.exit_with_error(c.MSG_CLIENT_CONNECTION_ERR)


def handle_lobby(connection: c.Connection) -> None:
    lobby.start_queue(connection)
    lobby.reset_after_dodge(connection)


def handle_readycheck(connection: c.Connection) -> None:
    connection.update_primary_role()
    lobby.reset_after_dodge(connection)
    lobby.accept_match(connection)


def handle_champselect(connection: c.Connection, champselect_loop_iteration: int) -> None:
    # Wrap in try block to catch KeyError when someone dodges - champselect actions don't exist anymore
    try:
        champselect.update_champselect(connection)
        phase = champselect.get_champselect_phase(connection)
    except KeyError:
        phase = "skip"

    if SHOULD_PRINT:
        u.print_and_write(f"\nChampselect loop #{champselect_loop_iteration}:")
        u.print_and_write("\tChampselect phase:", u.map_phase_for_display(phase))

    # Handle each champ select phase separately
    match phase:
        case "PLANNING":
            champselect.hover_champ(connection)
        case "BAN_PICK":
            champselect.ban_or_pick(connection)
        case "FINALIZATION":
            runes.send_runes_and_summs(connection)
        case "skip":
            pass


def main() -> None:
    in_game: bool = False
    last_gamestate: str = ""  # Store last gamestate - used to skip redundant API calls and print statements
    champselect_loop_iteration: int = 0  # Keep track of how many loops run during champselect
    connection: c.Connection = initialize_connection()
    while not in_game:
        time.sleep(UPDATE_INTERVAL)
        # Wrap the loop in a try block to catch errors when the client closes
        try:
            gamestate: str = connection.get_gamestate()
            gamestate_has_changed: bool = gamestate != last_gamestate

            # Print current gamestate if it's different from the last one
            if gamestate_has_changed:
                u.print_and_write(f"\nCurrent gamestate: {u.map_gamestate_for_display(gamestate)}")
                last_gamestate = gamestate

            match gamestate:
                case "Lobby":
                    if gamestate_has_changed:
                        handle_lobby(connection)

                case "ReadyCheck":
                    if gamestate_has_changed:
                        champselect_loop_iteration = 1
                        handle_readycheck(connection)

                case "ChampSelect":
                    champselect_loop_iteration += 1
                    handle_champselect(connection, champselect_loop_iteration)

                # End loop if a game starts
                case "InProgress":
                    in_game = True

        except requests.exceptions.ConnectionError:
            u.print_and_write(c.MSG_CLIENT_CONNECTION_ERR)
            connection.parse_lockfile()

if __name__ == "__main__":
    main()