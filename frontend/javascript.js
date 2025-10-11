async function apiCall(endpoint, method, data) {
    let fullEndpoint = "http://127.0.0.1:5000/" + endpoint

    return await (await fetch(fullEndpoint, {
        method: method,
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify(data)
    })).json()
}

async function post(endpoint, data) {
    return await apiCall(endpoint, "POST", data)
}

async function get(endpoint, data) {
    return await apiCall(endpoint, "GET", data)
}

async function getPickIntent() {
    return await get("status/champ");
}

async function getStatus() {
    return get("status");
}

async function startBot() {
    let response = await post("start");
    if (! response['success']) {
        console.log(`Unable to start the bot: ${response['statusText']}`)
    } else {
        console.log("Successfully started the bot!");
    }
    return response['success'];
}

async function setPickIntent(champ) {
    let response = await post("data/pick", {champ: champ});
    console.log(response)
    if (! response['success']) {
        console.log(`Unable to set pick intent: ${response['statusText']}`)
    }
    return response['success'];
}

async function setBanIntent(champ) {
    let response = await post("data/ban", {champ: champ});
    console.log(response)
    if (! response['success']) {
        console.log(`Unable to set ban intent: ${response['statusText']}`)
    }
    return response['success'];
}

async function setRunesPreference(preference) {
    await post("data/runespreference", {setrunes: preference});
}

function capitalize(name) {
    return name.charAt(0).toUpperCase() + name.slice(1)
}

async function update() {
    console.log("Attempting to update status...");

    let data = await getStatus();

    console.log(data);

    if (data['success']) {
        pickDisplay.textContent = capitalize(data['champ']);
        banDisplay.textContent = capitalize(data['ban']);
        gamestateDisplay.textContent = data['gamestate'];
        roleDisplay.textContent = data['role'];
    }
}
