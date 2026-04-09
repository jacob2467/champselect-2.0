let saveButton = document.getElementById("saveButton");
let cfg;

async function setUpSettingsPage() {
    let result = await apiCall("settings/sections", "GET");
    if (result["success"]) {
        cfg = result["data"];
    }
    console.log(cfg);
    await setUpMainSettings();
    await setUpSaveButton();
}


async function setUpMainSettings() {
    let mainSettings = cfg["settings"];
    console.log(mainSettings);

    let directory = document.getElementById("cfg_directory");
    directory.placeholder = mainSettings["directory"];

    let lockInDelay = document.getElementById("cfg_lock_in_delay");
    lockInDelay.placeholder = mainSettings["lock_in_delay"];

    let autoStartQueue = document.getElementById("cfg_auto_start_queue");
    autoStartQueue.checked = mainSettings["auto_start_queue"] === "True";

    let updateInterval = document.getElementById("cfg_update_interval");
    updateInterval.placeholder = mainSettings["update_interval"];
}


async function setUpPickBanSettings() {
    let result = await apiCall("settings/sections", "GET");
    if (result["success"]) {
        cfg = result["data"];
    }

    let roles = ["top", "jungle", "middle", "bottom", "utility"];
    let actionTypes = ["pick", "ban"];
    for (let actionType of actionTypes) {
         for (let role of roles) {
            let key = `${actionType}_${role}`
            // Set up placeholder text
            for (let i = 1; i <= 3; i++) {
                let champ = cfg[key][i];
                let htmelement = document.getElementById(`cfg_${role}-${actionType}-${i}`);
                htmelement.placeholder = champ;
            }
        }
    }
   console.log(cfg);
}


/**
 * Set up the button to save settings to the config file.
 */
async function setUpSaveButton() {
   saveButton.addEventListener("click", async (event) => {
        event.preventDefault();
        let newConfig = {};
        let roles = ["top", "jungle", "middle", "bottom", "utility"];
        let actionTypes = ["pick", "ban"];
        console.log("type xi");
        // behold
        for (let actionType of actionTypes) { for (let role of roles) {
            for (let i = 1; i <= 3; i++) {
                let cfgSectionName = `${actionType}_${role}`
                let htmelement = document.getElementById(`cfg_${cfgSectionName}-${i}`);
                // If the text content is null, do nothing
                try {
                    console.log(cfgSectionName);
                    newConfig[cfgSectionName][`${i}`] = htmelement.textContent;
                    console.log(newConfig[cfgSectionName][`${i}`]);
                } catch (e) {}
            }
        }}

        let sections = ["directory", "update_interval", "lock_in_delay", "auto_start_queue"];
        for (let section of sections) {
            try {
                let htmelement = document.getElementById("cfg_directory");
                newConfig["settings"][section] = htmelement.textContent;
            } catch (e) {}
        }
        console.log(newConfig);
        let result = await apiCall("settings/sections", "POST", newConfig);
        console.log("Result of sending settings...");
        console.log(result);
    });
}

