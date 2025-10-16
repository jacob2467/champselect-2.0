/**
 * Make an API call.
 * @param endpoint the endpoint to send the HTTP request to
 * @param method the HTTP method to use
 * @param data (optional) the data to send with the HTTP request
 */
async function apiCall(endpoint, method, data) {
    let fullEndpoint = "http://127.0.0.1:5000/" + endpoint;

    try {
        return await (await fetch(fullEndpoint, {
            method: method,
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify(data)
        })).json()
    } catch (error) {
        console.log(`Error while trying to send the request to endpoint ${endpoint}:\n\t${error}`)
    }
}

/**
 * Send an HTTP POST request.
 * @param endpoint the endpoint to send the request to
 * @param data (optional) the data to send with the request
 */
async function post(endpoint, data) {
    return await apiCall(endpoint, "POST", data)
}

/**
 * Send an HTTP GET request.
 * @param endpoint the endpoint to send the request to
 * @param data (optional) the data to send with the request
 */
async function get(endpoint, data) {
    return await apiCall(endpoint, "GET", data)
}


/**
 * Attempt to start the script, and return a bool indicating whether it's running or not.
 */
async function startScript() {
    let response = await post("start");
    let isRunning;
    if (! response['success']) {
        console.log(response['statusText']);
        isRunning = await scriptIsRunning();  /* if the reason the attempt failed was because the script was already
                                            running, then still return true - it's running, doesn't matter why */
    } else {
        console.log("Successfully started the script!");
        isRunning = true;
    }
    scriptCurrentlyRunning = isRunning;
    startButton.disabled = isRunning;
    return isRunning;
}


/**
 * Get the curret pick intent from the client. If unable to get the pick intent, return an empty string.
 */
async function getPick() {
    let pickResponse = await get("status/champ");
    if (pickResponse['success']) {
        return capitalize(pickResponse['data']);
    } else {
        return "";
    }
}


/**
 * Set the champion pick intent.
 * @param champ the name of the champion to pick
 */
async function setPick(champ) {
    let response = await post("data/pick", {champ: champ});
    if (! response['success']) {
        console.log(`Unable to set pick intent: ${response['statusText']}`)
    }
    return response['success'];
}


/**
 * Get the curret ban intent from the client. If unable to get the ban intent, return an empty string.
 */
async function getBan() {
    let banResponse = await get("status/ban");
    if (banResponse['success']) {
        return capitalize(banResponse['data']);
    }

    return "";
}


/**
 * Set the champion ban intent.
 * @param champ the name of the champion to ban
 */
async function setBan(champ) {
    let response = await post("data/ban", {champ: champ});
    if (! response['success']) {
        console.log(`Unable to set ban intent: ${response['statusText']}`)
    }
    return response['success'];
}


/**
 * Set the user's preference for whether or not their runes should be changed by the script.
 */
async function setRunesPreference(preference) {
    await post("data/runespreference", {setrunes: preference});
}


/**
 * Get the current gamestate. If unable to, return an empty string instead.
 */
async function getGamestate() {
    let response = await get('status/gamestate');
    if (response['success']) {
        return response['data'];
    }

    return "";
}

/**
 * Get the user's role.
 */
async function getRole() {
    let response = await get('status/role');
    if (response['success']) {
        return response['data'];
    }
    return "";
}


/**
 * Update the status display of the program.
 */
async function updateStatus() {
    scriptCurrentlyRunning = await scriptIsRunning();
    // TODO: Make some of these API calls conditional based on gamestate, etc.; reduce noise
    if (scriptCurrentlyRunning) {
        pickDisplay.textContent = await getPick();
        banDisplay.textContent = await getBan();
        gamestateDisplay.textContent = await getGamestate();
        roleDisplay.textContent = await getRole();
        statusDisplay.textContent = "Running!";
        startButton.disabled = true;
    } else {
        // TODO: Make script stay alive while game is running, but reduce polling rate (?)
        pickDisplay.textContent = "";
        banDisplay.textContent = "";
        gamestateDisplay.textContent = "";
        roleDisplay.textContent = "";
        statusDisplay.textContent = "Not running";
        startButton.disabled = false;
    }
}


/**
 * Check if the script is currently running.
 */
async function scriptIsRunning() {
    try {
        let response = await get('status');
        return response['data'];
    } catch (error) {
        console.log(`Script not running due to an error: ${error}`)
        return false;
    }
}


/**
 * Capitalize the first character in a string.
 */
function capitalize(name) {
    if (name.length === 0) {
        return "";
    }
    return name.charAt(0).toUpperCase() + name.slice(1)
}
