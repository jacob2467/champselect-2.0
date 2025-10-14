from flask_cors import CORS
from functools import wraps
from typing import Any
import threading
import requests
import flask

import utility as u
import connect as c
import champselect
import main_loop

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


def empty_success_response():
    """ Build an empty success response. """
    return flask.jsonify({
        "success": True,
        "statusText": "",
    }), 200

def build_response(**kwargs):
    if "status" in kwargs:
        status = kwargs.pop("status")
    else:
        raise SyntaxError(f"Function {build_response} called without a status code argument.")
    return flask.jsonify(kwargs), status

def ensure_connection(func):
    """
    Wrapper function to ensure that a connection to the League client has already been established before trying to
    communicate with it.
    Returns:
        - the return value of the function, if the client is connected
        - a JSON response with an error message, if the client is not connected
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not script_is_running():
            return build_response(
                success=False,
                statusText="Not connected to League client",
                status=404,
            )

        return func(*args, **kwargs)
    return wrapper

def script_is_running():
    """ Check whether or not the script is running. """
    if state.script_thread is None:
        return False
    return state.script_thread.is_alive()

@api.route("/start", methods=["POST"])
def start():
    """ Start the script, if it hasn't been started already. If it has, do nothing, returning a failure response. """
    if script_is_running():
        return build_response(
            success=False,
            statusText="A connection to the League client has already been established.",
            status=409,
        )

    try:
        state.connection = c.Connection()
        run_on_thread(main_loop.main_loop, state.connection)
    except Exception as e:
        return build_response(
            success=False,
            statusText=str(e),
            status=500,
        )

    return empty_success_response()


@api.route("/status/gamestate", methods=["GET"])
@ensure_connection
def get_gamestate():
    try:
        gamestate: str = u.map_gamestate_for_display(state.connection.get_gamestate())
    except Exception as e:
        return build_response(
            success=False,
            statusText=f"Unable to get gamestate due to an error: {e}",
            status=400
        )

    return build_response(
        success=True,
        statusText=gamestate,
        status=200,
    )


@api.route("/status", methods=["GET"])
@ensure_connection
def get_status():
    if script_is_running():
        return build_response(
            success=True,
            statusText="Script is running!",
            status=200,
        )

    return build_response(
        success=False,
        statusText="Script is not running.",
        status=400,
    )


@api.route("/status/role", methods=["GET"])
@ensure_connection
def get_role():
    """ Get the user's role. """
    gamestate: str = u.map_gamestate_for_display(state.connection.get_gamestate())
    match gamestate:
        case "Lobby" | "In Queue" | "Ready Check":
            role = u.map_role_for_display(state.connection.update_primary_role())

        case "Champselect":
            role = u.map_role_for_display(state.connection.get_assigned_role())

        case _:
            return build_response(
                success=False,
                statusText=f"Unable to get role: user doesn't have a role in gamestate {gamestate}",
                status=400,
            )

    return build_response(
        success=True,
        statusText=role,
        status=200
    )


@api.route("/status/champ", methods=["GET"])
@ensure_connection
def get_champ():
    champ: str = state.connection.pick_intent or state.connection.user_pick or ""
    return build_response(
        success=True,
        statusText=champ,
        status=200
    )


@api.route("/status/ban", methods=["GET"])
@ensure_connection
def get_ban():
    ban: str = state.connection.ban_intent or state.connection.user_ban or ""
    return build_response(
        success=True,
        statusText=ban,
        status=200
    )


@api.route("/data/pick", methods=["POST"])
@ensure_connection
def set_pick():
    desired_champ: str = flask.request.json['champ']
    champ = state.connection.champ_exists(desired_champ)
    if not champ:
        return build_response(
            success=False,
            statusText=f"Champion '{desired_champ}' does not exist.",
            status=400,
        )

    is_valid, reason = champselect.is_valid_pick(state.connection, champ)
    state.connection.user_pick = champ
    if is_valid:
        state.connection.pick_intent = champ
        return empty_success_response()

    # Invalid pick
    return build_response(
        success=False,
        statusText=reason,
        status=400
    )


@api.route("/data/ban", methods=["POST"])
@ensure_connection
def set_ban():
    desired_ban: str = flask.request.json['champ']
    ban = state.connection.champ_exists(desired_ban)
    if not ban:
        return build_response(
            success=False,
            statusText=f"Champion '{ban}' does not exist.",
            status=400,
        )

    is_valid, reason = champselect.is_valid_ban(state.connection, ban)
    state.connection.user_ban = ban
    if is_valid:
        state.connection.ban_intent = ban
        return empty_success_response()

    # Invalid pick
    return build_response(
        success=False,
        statusText=reason,
        status=400
    )

@api.route("/status/runespreference", methods=["GET"])
@ensure_connection
def get_runes_preference():
    return build_response(
        success=True,
        statusText=state.connection.should_modify_runes,
        status=200
    )


@api.route("/data/runespreference", methods=["POST"])
@ensure_connection
def set_runes_preference():
    try:
        state.connection.should_modify_runes = bool(flask.request.json["setrunes"])
        return empty_success_response()
    except KeyError:
        statusText = "Invalid data parameter: POST request should contain a 'setrunes' key."
        return build_response(
            success=False,
            statusText=statusText,
            status=400
        )

if __name__ == "__main__":
    api.run()