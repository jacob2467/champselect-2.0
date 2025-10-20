from flask_cors import CORS
from functools import wraps
import threading
import logging
import flask

import connect as c
import champselect
import formatting
import main_loop
import utility
import lobby
import runes

# stolen from here https://stackoverflow.com/questions/14888799/disable-console-messages-in-flask-server
log = logging.getLogger('werkzeug')
log.disabled = True

api = flask.Flask(__name__)
CORS(api)

utility.setup_autoflushing()

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


def empty_success_response():
    """ Build an empty success response. """
    return flask.jsonify({
        "success": True,
        "statusText": "",
    }), 200


def build_response(**kwargs):
    # Make status code mandatory
    if "status" in kwargs:
        status = kwargs.pop("status")
    else:
        raise SyntaxError(f"Function {build_response} called without a status code argument.")

    # 'data' is the data the user requested (ifs present), and 'statusText' is a supplementary/explanatory message
    # where applicable (error messages, for example). If either of them is not present, set them to an empty string
    # so that they don't show up as undefined in the browser console
    if "statusText" not in kwargs:
        kwargs['statusText'] = ""
    if "data" not in kwargs:
        kwargs['data'] = ""

    return flask.jsonify(kwargs), status


def script_is_running():
    """ Check whether or not the script is running. """
    if state.script_thread is None:
        return False
    return state.script_thread.is_alive()


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
                status=503,
            )

        return func(*args, **kwargs)
    return wrapper


@api.route("/start", methods=["POST"])
def start():
    """ Start the script if it hasn't been started already. If it has, do nothing, returning a failure response. """
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


@api.route("/actions/queue", methods=["POST"])
@ensure_connection
def start_queue():
    """ Start queuing for a match. """
    gamestate: str = formatting.gamestate(state.connection.get_gamestate())
    if gamestate != "Lobby":
        return build_response(
            success=False,
            statusText="not in lobby",
            status=400,
        )

    lobby.start_queue(state.connection)
    return empty_success_response()


@api.route("/status/gamestate", methods=["GET"])
@ensure_connection
def get_gamestate():
    gamestate: str = formatting.gamestate(state.connection.get_gamestate())

    return build_response(
        success=True,
        data=gamestate,
        status=200,
    )


@api.route("/status", methods=["GET"])
def get_status():
    if script_is_running():
        return build_response(
            success=True,
            statusText="Script is running!",
            data=True,
            status=200,
        )

    return build_response(
        success=True,
        statusText="Script is not running.",
        data=False,
        status=200,
    )


@api.route("/status/role", methods=["GET"])
@ensure_connection
def get_role():
    """ Get the user's role. """
    gamestate: str = formatting.gamestate(state.connection.get_gamestate())
    match gamestate:
        case "Lobby" | "In Queue" | "Ready Check":
            role = formatting.role(state.connection.update_primary_role())

        case "Champselect":
            role = formatting.role(state.connection.get_assigned_role())

        case _:
            role = ""


    return build_response(
        success=True,
        data=role,
        status=200
    )


@api.route("/status/pick", methods=["GET"])
@ensure_connection
def get_champ():
    champ: str = state.connection.pick_intent or state.connection.user_pick or ""
    return build_response(
        success=True,
        data=champ,
        status=200
    )


@api.route("/data/pick", methods=["POST"])
@ensure_connection
def set_pick():
    desired_champ: str = flask.request.json['champ']
    champ_exists = state.connection.champ_exists(desired_champ)
    if not champ_exists:
        return build_response(
            success=False,
            statusText=f"Champion '{desired_champ}' does not exist.",
            status=400,
        )

    champ_name: str = formatting.clean_name(state.connection.all_champs, desired_champ)
    state.connection.user_pick = champ_name
    # If the pick is currently valid
    if champselect.is_valid_pick(state.connection, champ_name):
        state.connection.pick_intent = champ_name
        return build_response(
            success=True,
            data=formatting.champ(champ_name),
            status=200
        )

    # Invalid pick
    return build_response(
        success=False,
        statusText="Invalid pick",
        status=400
    )


@api.route("/status/ban", methods=["GET"])
@ensure_connection
def get_ban():
    ban: str = state.connection.ban_intent or state.connection.user_ban or ""
    return build_response(
        success=True,
        data=ban,
        status=200
    )


@api.route("/data/ban", methods=["POST"])
@ensure_connection
def set_ban():
    desired_champ: str = flask.request.json['champ']
    champ_exists = state.connection.champ_exists(desired_champ)
    if not champ_exists:
        return build_response(
            success=False,
            statusText=f"Champion '{desired_champ}' does not exist.",
            status=400,
        )

    champ_name: str = formatting.clean_name(state.connection.all_champs, desired_champ)
    state.connection.user_ban = champ_name
    # If ban is currently valid
    if champselect.is_valid_ban(state.connection, champ_name):
        state.connection.ban_intent = champ_name
        return build_response(
            success=True,
            data=formatting.champ(champ_name),
            status=200
        )

    # Invalid ban
    return build_response(
        success=False,
        statusText="Invalid ban",
        status=400
    )


@api.route("/status/runespreference", methods=["GET"])
@ensure_connection
def get_runes_preference():
    return build_response(
        success=True,
        data=state.connection.should_modify_runes,
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


@api.route("/actions/sendrunes", methods=["POST"])
@ensure_connection
def set_runes():
    try:
        runes.send_runes_and_summs(state.connection)
        return empty_success_response()
    except Exception as e:
        return build_response(
            success=False,
            statusText=f"Unable to set runes due to an error: {e}",
            status=400
        )



@api.route("/actions/createlobby", methods=["POST"])
@ensure_connection
def create_lobby():
    lobbytype = flask.request.json['lobbytype']
    try:
        lobby.create_lobby(state.connection, lobbytype)
        return empty_success_response()

    except Exception as e:
        return build_response(
            success=False,
            statusText=f"Unable to create the lobby due to an error: {e}",
            status=400
        )


@api.route("/actions/formatname", methods=["POST"])
def format_name():
    return build_response(
        success=True,
        data=formatting.champ(flask.request.json['champ']),
        status=200
    )


if __name__ == "__main__":
    api.run(port=6969)