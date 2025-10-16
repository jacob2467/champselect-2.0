/**
 * Set up the start button for the script.
 */
function setUpStartButton() {
    // Start script when button is clicked
    startButton.addEventListener("click", async (event) => {
        event.preventDefault();

        await startScript();
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

        let success = await setPick(name);
        if (success) {
            pickInput.value = "";
            pickDisplay.textContent = capitalize(name);
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

        let success = await setBan(name);
        if (success) {
            banInput.value = "";
            banDisplay.textContent = capitalize(name);
        }
    });
}

function setUpRuneCheckbox() {
    // Allow the user to enable or disable rune changing
    runeCheckbox.addEventListener("change", async (event) => {
        event.preventDefault();

        // TODO: Log error message here instad of discarding
        void setRunesPreference(event.target.checked);

        if (! event.target.checked) {
            return;
        }
        // Send runes to the client if we're in champselect
        if (await getGamestate() === "Champselect") {
            let response = await post("actions/sendrunes");
            if (response['success']) {
                console.log("Successfully set runes!");
            } else {
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
            console.log(`Unable to create lobby due to an error: ${response['statusText']}`);
        }
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
}