import connect
import requests
import time
from utility import *

connection_initiated: bool = False
in_game: bool = False
should_print: bool = True
last_gamestate: dict = {}
champselect_loop_iteration: int = 0  # Keep track of how many loops run during champselect
RETRY_RATE: int = 10  # How many seconds to wait after a failed connection attempt
UPDATE_INTERVAL: float = 1  # How many seconds to wait before re-running the main loop

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
        debugprint(f"Failed to connect to the league client - is it open? Retrying in {RETRY_RATE} seconds...")
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
        gamestate = c.api_get("gamestate").json()

        # TODO: Fix this
        updated_gamestate: bool = gamestate != last_gamestate

        # Print current gamestate if it's different from the last one
        if updated_gamestate:
            debugprint("Current gamestate:", gamestate)
            last_gamestate = gamestate

        match gamestate:
            case "Lobby":
                if updated_gamestate:
                    c.start_queue()

            case "ReadyCheck":
                if updated_gamestate:
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
                if should_print:
                    debugprint(f"\nChampselect loop # {champselect_loop_iteration}:")
                    debugprint("Champselect phase:", phase)

                # Handle each champ select phase separately
                match phase:
                    case "PLANNING":
                        c.hover_champ()
                        should_print = True
                    case "BAN_PICK":
                        c.ban_or_pick()
                    case "FINALIZATION":
                        c.send_runes_summs()
                        should_print = False
                    case "skip":
                        pass

            # End loop if a game starts
            case "InProgress":
                in_game = True

            case default:
                pass
    except requests.exceptions.ConnectionError:
        debugprint("Connection error. Did you close the league client?")
        c.parse_lockfile()