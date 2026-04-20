let saveButton = document.getElementById("saveButton");
let cfg;

async function setUpSettingsPage() {
    let result = await apiCall("settings/sections", "GET");
    if (result["success"]) {
        cfg = result["data"];
    }
    console.log(cfg);
    await setUpMainSettings();
    await setUpPickBanSettings();
    await setUpSaveButton();

}


async function setUpMainSettings() {
    let mainSettings = cfg["settings"];

    let directory = document.getElementById("cfg_directory");
    directory.placeholder = mainSettings["directory"];

    let lockInDelay = document.getElementById("cfg_lock_in_delay");
    lockInDelay.placeholder = mainSettings["lock_in_delay"];

    let autoStartQueue = document.getElementById("cfg_auto_start_queue");
    autoStartQueue.checked = mainSettings["auto_start_queue"] === "True";

    let autoSendRunes = document.getElementById("cfg_auto_send_runes");
    autoSendRunes.checked = mainSettings["auto_send_runes"] === "True";

    let updateInterval = document.getElementById("cfg_update_interval");
    updateInterval.placeholder = mainSettings["update_interval"];
}


async function setUpPickBanSettings() {
    let roles = ["top", "jungle", "middle", "bottom", "utility"];
    let actionTypes = ["pick", "ban"];
    for (let actionType of actionTypes) { for (let role of roles) {
        let key = `${actionType}_${role}`
        // Set up placeholder text
        for (let i = 1; i <= 3; i++) {
            let champ = cfg[key][i];
            let name = `cfg_${actionType}_${role}-${i}`;
            let htmelement = document.getElementById(name);
            htmelement.placeholder = champ;
        }
    }}
}


/**
 * Set up the button to save settings to the config file.
 */
async function setUpSaveButton() {
   saveButton.addEventListener("click", async (event) => {
        let newCfg = {};
        console.log(newCfg);
        event.preventDefault();
        let roles = ["top", "jungle", "middle", "bottom", "utility"];
        let actionTypes = ["pick", "ban"];
        // behold
        for (let actionType of actionTypes) { for (let role of roles) {
            for (let i = 1; i <= 3; i++) {
                let cfgSectionName = `${actionType}_${role}`
                let htmelement = document.getElementById(`cfg_${cfgSectionName}-${i}`);
                // Do nothing if the value hasn't been changed
                let name = htmelement.value;
                if (! name) {
                    continue;
                }
                if (! newCfg[cfgSectionName]) {
                    newCfg[cfgSectionName] = {};
                }
                newCfg[cfgSectionName][i] = name;
            }
        }}

        let options = ["directory", "update_interval", "lock_in_delay", "auto_start_queue", "auto_send_runes"];
        newCfg["settings"] = {};
        for (let option of options) {
            try {
                let value;
                let htmelement = document.getElementById(`cfg_${option}`);
                if (option.startsWith("auto_")) {  // use checkbox for bool options
                    value = htmelement.checked
                } else {
                    value = htmelement.value;
                    if (! value) { continue; }
                }
                newCfg["settings"][option] = value;
            } catch (e) {}
        }
        let result = await apiCall("settings/sections", "POST", newCfg);
        console.log("Result of sending settings...");
        console.log(result);
    });
}

