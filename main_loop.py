import requests
import time
import sys

import utility as u
import connect as c
import champselect
import formatting
import runes
import lobby

# Whether or not to print debug info
SHOULD_PRINT: bool = u.get_config_option_bool("settings", "print_debug_info")

# Whether or not to automatically start the queue
SHOULD_START_QUEUE: bool = u.get_config_option_bool("settings", "start_queue")

# How many seconds to wait before re-running the main loop
UPDATE_INTERVAL: float = float(u.get_config_option_str("settings", "update_interval"))

MSG_ATTEMPT_RECONNECT: str = "Unable to connect to the League of Legends client. Retrying..."


def handle_lobby(connection: c.Connection) -> None:
    if SHOULD_START_QUEUE and not connection.started_queue:
        lobby.start_queue(connection)
        connection.started_queue = True
    lobby.reset_after_dodge(connection)


def handle_readycheck(connection: c.Connection) -> None:
    connection.update_primary_role()
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
        u.print_and_write("\tChampselect phase:", formatting.phase(phase))

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


def main_loop(connection: c.Connection) -> None:
    in_game: bool = False
    last_gamestate: str = ""  # Store last gamestate - used to skip redundant API calls and print statements
    champselect_loop_iteration: int = 0  # Keep track of how many loops run during champselect

    while not in_game:
        time.sleep(UPDATE_INTERVAL)
        # Wrap the loop in a try block to catch errors when the client closes
        try:
            gamestate: str = connection.get_gamestate()
            gamestate_has_changed: bool = gamestate != last_gamestate

            # Print current gamestate if it's different from the last one
            if gamestate_has_changed:
                u.print_and_write(f"\nCurrent gamestate: {formatting.gamestate(gamestate)}")
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
            connection.re_parse_lockfile()
