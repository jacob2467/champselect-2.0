let saveButton = document.getElementById("saveButton");

// TODO: Better function name
async function settingsInterface() {
    let configSections = document.getElementById("config-sections");
    let sections = await apiCall("settings/sections", "GET");
    let sectionsString = "";
    for (let data of sections.data) {
        // console.log(`data=${data}`);
        sectionsString += data + "\n";
        // console.log(sections.data[i]);
    }
    configSections.textContent = sectionsString;
    // console.log(configSections);
    await setUpSaveButton();
}

/**
 * Set up the button to save settings to the config file.
 */
async function setUpSaveButton() {
    // Start script when button is clicked
    let toSet = {
        "pick_top": {
            "1": "Leona",
            "2": "Sivir",
        }
    }
    saveButton.addEventListener("click", async (event) => {
        event.preventDefault();
        let result = await apiCall("settings/sections", "POST", toSet);
        console.log("Result of sending settings...");
        console.log(result);
    });
}

