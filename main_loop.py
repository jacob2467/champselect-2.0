import requests
import time

import connect as c
import utility as u
import champselect
import formatting
import lobby
import runes

MSG_ATTEMPT_RECONNECT: str = "Unable to connect to the League of Legends client. Retrying..."

def update_interval():
    """ Read the update interval from the config file. """
    # This needs to be done lazily now that the config can be changed while the app is running
    return float(u.get_config_option_str("settings", "update_interval"))


def should_start_queue():
    """ Read the config file to find out if the queue should be started automatically or not. """
    # This needs to be done lazily now that the config can be changed while the app is running
    return u.get_config_option_bool("settings", "auto_start_queue")


def handle_lobby(connection: c.Connection) -> None:
    if should_start_queue() and not connection.started_queue:
        lobby.start_queue(connection)
        connection.started_queue = True


def handle_readycheck(connection: c.Connection) -> None:
    connection.update_primary_role()
    lobby.accept_match(connection)
    lobby.reset_after_dodge(connection)


def handle_champselect(connection: c.Connection, champselect_loop_iteration: int) -> None:
    # Wrap in try block to catch KeyError when someone dodges - champselect actions don't exist anymore
    try:
        champselect.update_champselect(connection)
        phase = champselect.get_champselect_phase(connection)
    except KeyError:
        phase = "skip"

    # u.print_and_write(f"\nChampselect loop #{champselect_loop_iteration}:")
    # u.print_and_write("\tChampselect phase:", formatting.phase(phase))

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
    last_gamestate: str = ""  # Store last gamestate - used to skip redundant API calls and print statements
    champselect_loop_iteration: int = 0  # Keep track of how many loops run during champselect

    while True:
        time.sleep(update_interval())
        # Wrap the loop in a try block to catch errors when the client closes
        try:
            gamestate: str = connection.get_gamestate()
            gamestate_has_changed: bool = gamestate != last_gamestate

            # Print current gamestate if it's different from the last one
            if gamestate_has_changed:
                # u.print_and_write(f"\nCurrent gamestate: {formatting.gamestate(gamestate)}")
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

                # Reduce polling rate if in-game
                case "InProgress":
                    time.sleep(30)

        except requests.exceptions.ConnectionError:
            connection.re_parse_lockfile()
