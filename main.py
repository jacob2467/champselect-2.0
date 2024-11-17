import api


loaded_in = False
while not loaded_in:
    state = api.get_gamestate()

    match state:
        case "queue":
            match_found = True  # dummy value
            if match_found:
                api.accept_match()
        case "champselect":
            pass