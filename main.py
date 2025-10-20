from configparser import NoSectionError, NoOptionError
import requests
import sys
import os

import connect as c
import main_loop
import userinput

LOGFILE: str = "output.log"

def handle_error(original_err: Exception, err_msg: str = "", exit_code: int = 1):
    """
    If this file was run as a script, write the error message to stderr and then clean exit with sys.exit() for
    user-facing errors. No stacktrace, no exception chaining. If this file was *not* run as a script, just raise
    the original exception, and let it (potentially) be caught elsewhere.
    """
    # This allows the error to be caught in the web app. But we want a clean exit here if running as a script.
    if __name__ != "__main__":
        raise original_err

    # Special treatment for certain exception types
    if isinstance(original_err, (NoSectionError, NoOptionError)):
        sys.stderr.write("Error while parsing config: ")

    # Use original error message if none was provided
    if not err_msg:
        err_msg = str(original_err)

    sys.stderr.write(err_msg + "\n")
    sys.exit(exit_code)

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
            connection = c.Connection()
            userinput.get_first_choices(connection)
            return connection

        # If the connection isn't successful or the lockfile doesn't exist, the client isn't open yet
        except (requests.exceptions.ConnectionError, KeyError) as e:
            handle_error(e, c.MSG_CLIENT_CONNECTION_ERR)

if __name__ == "__main__":
    try:
        connection: c.Connection = initialize_connection()
        main_loop.main_loop(connection)
    except Exception as e:
        handle_error(e)