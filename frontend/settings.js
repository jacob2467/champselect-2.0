// TODO: Better function name
async function settingsInterface() {
    let configSections = document.getElementById("config-sections");
    let sections = await apiCall("settings/sections", "GET");
    let sectionsString = "";
    let data;
    for (let i in sections.data) {
        data = sections.data[i];
        // console.log(`data=${data}`);
        sectionsString += data + "\n";
        // console.log(sections.data[i]);
    }
    configSections.textContent = sectionsString;
    // console.log(configSections);
    let toSet = {
        "balls": {
            "1": "cum"
        },
        "pick_top": {
            "1": "Leona",
            "2": "Sivir",
        }
    }
    console.log(await apiCall("settings/sections", "POST", toSet));
}