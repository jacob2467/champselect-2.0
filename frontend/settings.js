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
    let toSet = {
        "pick_top": {
            "1": "Soraka",
            "2": "Jhin",
            "3": "Briar"
        }
    }
    saveButton.addEventListener("click", async (event) => {
        event.preventDefault();
        let result = await apiCall("settings/sections", "POST", toSet);
        console.log("Result of sending settings...");
        console.log(result);
    });
}

