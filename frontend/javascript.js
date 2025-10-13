/**
 * Make an API call.
 * @param endpoint the endpoint to send the HTTP request to
 * @param method the HTTP method to use
 * @param data (optional) the data to send with the HTTP request
 */
async function apiCall(endpoint, method, data) {
    let fullEndpoint = "http://127.0.0.1:5000/" + endpoint

    return await (await fetch(fullEndpoint, {
        method: method,
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify(data)
    })).json()
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
 * Start the script.
 */
async function startScript() {
    let response = await post("start");
    if (! response['success']) {
        console.log(`Unable to start the bot: ${response['statusText']}`)
        if (await getStatus()) {
            return true;
        }
    } else {
        console.log("Successfully started the bot!");
    }
    return response['success'];
}


/**
 * Set the champion pick intent.
 * @param champ the name of the champion to pick
 */
async function setPickIntent(champ) {
    let response = await post("data/pick", {champ: champ});
    if (! response['success']) {
        console.log(`Unable to set pick intent: ${response['statusText']}`)
    }
    return response['success'];
}


/**
 * Set the champion ban intent.
 * @param champ the name of the champion to ban
 */
async function setBanIntent(champ) {
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
 * Capitalize the first character in a string.
 */
function capitalize(name) {
    return name.charAt(0).toUpperCase() + name.slice(1)
}

/**
 * Get the curret pick intent from the client.
 */
async function getPick() {
    let pickResponse = await get("status/champ");
    if (pickResponse['success']) {
        return capitalize(pickResponse['statusText']);
    }
    return "None";
}

/**
 * Get the curret ban intent from the client.
 */
async function getBan() {
    let banResponse = await get("status/ban");
    if (banResponse['success']) {
        return capitalize(banResponse['statusText']);
    }
    return "None";
}

/**
 * Check if the script is currently running.
 */
async function getStatus() {
    let response = await get('status');
    return response['success'];
}

/**
 * Get the current gamestate.
 */
async function getGamestate() {
    let response = await get('status/gamestate');
    if (response['success']) {
        return response['statusText'];
    }
    return "None";
}

/**
 * Get the user's role.
 */
async function getRole() {
    let response = await get('status/role');
    if (response['success']) {
        return response['statusText'];
    }
    return "None";
}

/**
 * Update the status of the program.
 */
async function updateStatus() {
    let isRunning = await getStatus();

    if (isRunning) {
        pickDisplay.textContent = await getPick();
        banDisplay.textContent = await getBan();
        gamestateDisplay.textContent = await getGamestate();
        roleDisplay.textContent = await getRole();
        statusDisplay.textContent = "Running!";
    } else {
        pickDisplay.textContent = "";
        banDisplay.textContent = "";
        gamestateDisplay.textContent = "";
        roleDisplay.textContent = "";
        statusDisplay.textContent = "Not running";
    }
}

/**
 * Set up elements for the HTML display.
 */
function setUpDisplay() {
    // Start script when button is clicked
    start.addEventListener("click", async (event) => {
        event.preventDefault();

        let success = await startScript();
        start.disabled = true;
        // If unable to start the script, re-enable the start buton after a timeout
        if (! success) {
            setTimeout(() => {
                start.disabled = false;
            }, 3000);
        }
        scriptStarted = true;
    })

    // Take input for the desired pick
    pickInput.addEventListener("blur", async (event) => {
        event.preventDefault();

        // Do nothing if the user leaves the text box blank
        let name = event.target.value;
        if (name === "") {
            return;
        }

        let success = await setPickIntent(name);
        if (success) {
            pickInput.value = "";
            pickDisplay.textContent = capitalize(name);
        }
    })

    // Take input for the desired ban
    banInput.addEventListener("blur", async (event) => {
        event.preventDefault();

        // Do nothing if the user leaves the text box blank
        let name = event.target.value;
        if (name === "") {
            return;
        }

        let success = await setBanIntent(name);
        if (success) {
            banInput.value = "";
            banDisplay.textContent = capitalize(name);
        }
    })

    // Allow the user to enable or disable rune changing
    runeCheckbox.addEventListener("change", (event) => {
        void setRunesPreference(event.target.checked);
    })
}
