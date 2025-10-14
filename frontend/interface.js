/**
 * Set up the start button for the script.
 */
function setUpStartButton() {
    // Start script when button is clicked
    startButton.addEventListener("click", async (event) => {
        event.preventDefault();

        let success = await startScript();
        startButton.disabled = true;
        // If unable to start the script, re-enable the start buton after a timeout
        if (! success) {
            setTimeout(() => {
                startButton.disabled = false;
            }, 3000);
        } else {
            scriptStarted = true;
        }
    })
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
    })
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
    })
}

function setUpRuneCheckbox() {
    // Allow the user to enable or disable rune changing
    runeCheckbox.addEventListener("change", (event) => {
        void setRunesPreference(event.target.checked);
    })
}

/**
 * Set up elements for the HTML display.
 */
function setUpDisplay() {
    setUpStartButton();
    setUpPickInput();
    setUpBanInput();
    setUpRuneCheckbox();
}