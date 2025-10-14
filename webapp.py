from flask_cors import CORS
from functools import wraps
from typing import Any
import threading
import requests
import flask

import utility as u
import connect as c
import champselect
import main

MSG_CHAMP_DOESNT_EXIST: str = "Specified champion doesn't exist"

api = flask.Flask(__name__)
CORS(api)

class BotState:
    def __init__(self):
        self.connection = None
        self.script_thread = None
state: BotState = BotState()


def run_on_thread(func, *args, **kwargs):
    """ Spawn a new thread and run the target on it. """
    thread = threading.Thread(target=func, args=args, kwargs=kwargs)
    state.script_thread = thread
    thread.start()

# Note that this function is not decorated with @ensure_connection because it should only be called from inside
# other functions that are.
def _get_gamestate():
    """ Get a formatted string representing the League client's gamestate. """
    return u.map_gamestate_for_display(state.connection.get_gamestate())


def build_response(success: bool, body: Any, status: int):
    """ Build an API response in JSON format. """
    return flask.jsonify({
        "success": success,
        "statusText": body,
    }), status


def build_success_response(*, success: bool = True, body: Any = "", status: int = 200):
    """ Build an API response in JSON format, with default values for an empty success response. """
    return build_response(success, body, status)


def build_failure_response(*, success: bool = False, body: Any = "", status: int = 400):
    """ Build an API response in JSON format, with default values for an empty failure response. """
    return build_response(success, body, status)


def ensure_connection(func):
    """
    Wrapper function to ensure that a connection to the League client has already been established before trying to
    communicate with it. If it hasn't, instead return an error message.
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not script_is_running():
            return build_failure_response(body="Not connected to League client", status=404)

        return func(*args, **kwargs)
    return wrapper

def script_is_running():
    """ Check whether or not the script is running. """
    if state.script_thread is None:
        return False
    return state.script_thread.is_alive()

@api.route("/start", methods=["GET", "POST"])
@ensure_connection
def start():
    """ Start the script, if it hasn't been started already. If it has, do nothing, returning a failure response. """
    if script_is_running():
        body = "A connection to the League client has already been established."
        return build_failure_response(body=body)

    state.connection = c.Connection()
    run_on_thread(main.main, state.connection)
    return build_success_response()


@api.route("/status/gamestate", methods=["GET"])
@ensure_connection
def get_gamestate():
    return build_success_response(body=_get_gamestate())

@api.route("/status", methods=["GET"])
@ensure_connection
def get_status():
    return flask.jsonify({
        "success": script_is_running()
    }), 200

def _get_role():
    match _get_gamestate():
        case "Main Menu":
            return False, "User not in champselect or in queue."

        case "Lobby" | "In Queue" | "Ready Check":
            return True, u.map_role_for_display(state.connection.update_primary_role())

        case "Champselect":
            return True, u.map_role_for_display(state.connection.get_assigned_role())

        case _:
            return False, "Unable to process the request."

@api.route("/status/role", methods=["GET"])
@ensure_connection
def get_role():
    success, body = _get_role()
    if success:
        return build_success_response(body=body)
    return build_failure_response(body=body)


def _get_champ():
    return True, state.connection.pick_intent


@api.route("/status/champ", methods=["GET"])
@ensure_connection
def get_champ():
    success, body = _get_champ()
    if success:
        return build_success_response(body=body)
    return build_failure_response(body=body)


def _get_ban():
    return True, state.connection.ban_intent


@api.route("/status/ban", methods=["GET"])
@ensure_connection
def get_ban():
    success, body = _get_ban()
    if success:
        return build_success_response(body=body)
    return build_failure_response(body=body)


@api.route("/data/pick", methods=["POST"])
@ensure_connection
def set_pick():
    data = flask.request.json
    if champ := state.connection.champ_exists(data["champ"]):
        is_valid, reason = champselect.is_valid_pick(state.connection, champ)
        state.connection.user_pick = champ

        # Note: Potentially confusing - sets user's desired pick regardless of gamestate, but will return a failure
        # code if that champ isn't pickable *right now*
        if is_valid:
            state.connection.pick_intent = champ
            return build_success_response()

        # Invalid pick
        return build_failure_response(body=reason)

    # Champ doesn't exist
    return build_failure_response(body=MSG_CHAMP_DOESNT_EXIST)


@api.route("/data/ban", methods=["POST"])
@ensure_connection
def set_ban():
    data = flask.request.json
    if champ := state.connection.champ_exists(data["champ"]):
        is_valid, reason = champselect.is_valid_ban(state.connection, champ)
        state.connection.user_ban = champ

        # Note: Potentially confusing - sets user's desired ban regardless of gamestate, but will return a failure
        # code if that champ isn't bannable *right now*
        if is_valid:
            state.connection.ban_intent = champ
            return build_success_response()

        # Invalid ban
        return build_failure_response(body=reason)

    # Champ doesn't exist
    return build_failure_response(body=MSG_CHAMP_DOESNT_EXIST)

@api.route("/status/runespreference", methods=["GET"])
@ensure_connection
def get_runes_preference():
    return build_success_response(body=state.connection.should_modify_runes)

@api.route("/data/runespreference", methods=["POST"])
@ensure_connection
def set_runes_preference():
    try:
        state.connection.should_modify_runes = bool(flask.request.json["setrunes"])
        return build_success_response()
    except KeyError:
        body = "Invalid data parameter: POST request should contain a 'setrunes' key."
        return build_failure_response(body=body)

if __name__ == "__main__":
    api.run()