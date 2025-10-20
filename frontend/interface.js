/**
 * Set up the start button for the script.
 */
function setUpStartButton() {
    // Start script when button is clicked
    startButton.addEventListener("click", async (event) => {
        event.preventDefault();

        scriptCurrentlyRunning = await startScript();
    });
}

function setUpPickInput() {
    // Take input for the desired pick
    pickInput.addEventListener("blur", async (event) => {
        event.preventDefault();

        // Do nothing if the user leaves the text box blank
        let name = event.target.value;
        if (name === "") {
            return;
        }

        let response = await setPick(name);
        if (response['success']) {
            pickInput.value = "";
            pickDisplay.textContent = response['data'];
        } else {
            showUser("Unable to set pick - check the console for errors");
            console.log(`Unable to set pick due to an error: ${response['statusText']}`);
        }
    });
}

function setUpBanInput() {
    // Take input for the desired ban
    banInput.addEventListener("blur", async (event) => {
        event.preventDefault();

        // Do nothing if the user leaves the text box blank
        let name = event.target.value;
        if (name === "") {
            return;
        }

        let response = await setBan(name);
        if (response['success']) {
            banInput.value = "";
            banDisplay.textContent = response['data'];
        } else {
            showUser("Unable to set ban - check the console for errors");
            console.log(`Unable to set ban due to an error: ${response['statusText']}`);
        }
    });
}

function setUpRuneCheckbox() {
    // Allow the user to enable or disable rune changing
    runeCheckbox.addEventListener("change", async (event) => {
        event.preventDefault();
        void setRunesPreference(event.target.checked);
        if (! event.target.checked) {
            return;
        }
        // Send runes to the client if we're in champselect
        if (await getGamestate() === "Champselect") {
            let response = await post("actions/sendrunes");
            if (response['success']) {
                showUser("Successfully set runes!");
            } else {
                showUser("Unable to set runes - check the console for errors");
                console.log(`Unable to set runes due to an error: ${response['statusText']}`);
            }
        }
    });
}

function setUpQueueButton() {
    queueButton.addEventListener("click", async (event) => {
        event.preventDefault();

        let response = await post("actions/queue");
        if (response['success']) {
            console.log("Successfully started queue!");
        } else {
            showUser("Unable to start queue - check the console for errors");
            console.log(`Unable to start queue due to an error: ${response['statusText']}`);
        }
    });
}

function setUpLobbyControls() {
    lobbyButton.addEventListener("click", async (event) => {
        event.preventDefault();

        let response = await post("actions/createlobby", {lobbytype: lobbyDropdown.value});
        if (response['success']) {
            console.log("Successfully created a lobby!");
        } else {
            showUser("Unable to create a lobby - check the console for errors");
            console.log(`Unable to create lobby due to an error: ${response['statusText']}`);
        }
    });
}

function setUpConsoleButton() {
    consoleButton.addEventListener("click", async (event) => {
        event.preventDefault();
        if (! window.debugging) {
            console.log("Unable to open debug console - window.debugging is null");
            return;
        }
        window.debugging.openConsole();
    });
}

/**
 * Set up elements for the HTML display.
 */
function setUpDisplay() {
    setUpStartButton();
    setUpPickInput();
    setUpBanInput();
    setUpRuneCheckbox();
    setUpQueueButton();
    setUpLobbyControls();
    setUpConsoleButton();
}


async function main() {
    // Set up buttons
    startButton = document.getElementById("startbutton");
    pickInput = document.getElementById("pick-intent-input");
    banInput = document.getElementById("ban-intent-input");
    runeCheckbox = document.getElementById("setrunes");
    queueButton = document.getElementById("queuebutton");
    lobbyDropdown = document.getElementById("lobbyDropdown");
    lobbyButton = document.getElementById("lobbyButton");
    consoleButton = document.getElementById("consoleButton");

    // Set up displays
    pickDisplay = document.getElementById("pick-intent");
    banDisplay = document.getElementById("ban-intent");
    gamestateDisplay = document.getElementById("gamestate");
    statusDisplay = document.getElementById("scriptstatus");
    roleDisplay = document.getElementById("role");
    log = document.getElementById("log");


    setUpDisplay();

    let scriptCurrentlyRunning;

    await startScript().then( async() => {
        // Only try to start the script automatically once. If that fails, wait for user to start manually
        scriptCurrentlyRunning = await scriptIsRunning();
        await updateStatus();
        setInterval(async () => {
            if (scriptCurrentlyRunning) {
                await updateStatus();
            }
        }, 3000);
    });
}
