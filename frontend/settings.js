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

   let lockInDelay = document.getElementById("cfg_lock-in-delay");
    lockInDelay.placeholder = mainSettings["lock_in_delay"];

    let autoStartQueue = document.getElementById("cfg_auto-start-queue");
    autoStartQueue.checked = mainSettings["auto_start_queue"] === "True";

    let updateInterval = document.getElementById("cfg_update-interval");
    updateInterval.placeholder = mainSettings["update_interval"];
}


/**
 * Set up the button to save settings to the config file.
 */
async function setUpSaveButton() {
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

