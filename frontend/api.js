/**
 * Make an API call.
 * @param endpoint the endpoint to send the HTTP request to
 * @param method the HTTP method to use
 * @param data (optional) the data to send with the HTTP request
 */
async function apiCall(endpoint, method, data) {
    let fullEndpoint = "http://127.0.0.1:6969/" + endpoint;
    let response = await fetch(fullEndpoint, {
        method: method,
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify(data),
    });

    try {
        return await response.json();
    } catch (error) {
        console.log(response);
        console.log(`Error while trying to send the request to endpoint ${endpoint}:\n\t${error}`);
        return {
            success: false,
            statusText: error.message
        }
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
async function get(endpoint) {
    return await apiCall(endpoint, "GET")
}


async function flaskIsRunning() {
    try {
        let response = await get("status");
        return response['success'];
    } catch (error) {
        console.log(error)
        return false;
    }
}

/**
 * Attempt to start the script, and return a bool indicating whether it's running or not.
 */
async function startScript() {
    let response;

    if (! await flaskIsRunning()) {
        console.log(`Couldn't start the script - Flask server isn't running.`);
        return false;
    }

    let isRunning;
    try {
        response = await post("start");
            if (! response['success']) {
                console.log(response['statusText']);
                isRunning = await scriptIsRunning();  /* if the reason the attempt failed was because the script was
                                                already running, then return true - it's running, doesn't matter why */
            } else {
                console.log("Successfully started the script!");
                isRunning = true;
            }
    } catch (error) {
        console.log(`Error starting the script: ${error}`);
        isRunning = false;
    }
    scriptCurrentlyRunning = isRunning;
    startButton.disabled = isRunning;
    return isRunning;
}


/**
 * Get the curret pick intent from the client. If unable to get the pick intent, return an empty string.
 */
async function getPick() {
    let response = await get("status/pick");
    if (response && response['success']) {
        return await formatName(response['data']);
    }
    return "";
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
    return response;
}


/**
 * Get the current ban intent from the client. If unable to get the ban intent, return an empty string.
 */
async function getBan() {
    let response = await get("status/ban");
    if (response && response['success']) {
        return await formatName(response['data']);
    }
    return "";
}


/**
 * Set the champion ban intent.
 * @param champ the name of the champion to ban
 * @returns the response object from the API call
 */
async function setBan(champ) {
    let response = await post("data/ban", {champ: champ});
    if (! response['success']) {
        console.log(`Unable to set ban intent: ${response['statusText']}`);
    }
    return response;
}


async function formatName(name) {
    if (name === "") {
        return "";
    }

    let response = await post("actions/formatname", {champ: name});
    if (response && response['success']) {
        return response['data'];
    } else {
        console.log("Unable to format the name via an API call - attempting to do it manually");
        return capitalize(name);
    }
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
    if (! await flaskIsRunning()) {
        return false;
    }

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
