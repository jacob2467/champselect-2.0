const { app, BrowserWindow } = require("electron");

const createWindow = () => {
    const win = new BrowserWindow({
        width: 800,
        height: 600,
    });

    win.loadFile("index.html");
    return win;
}

app.whenReady().then(() => {
    win = createWindow();

    win.openDevTools();
    console.log("Hello, world!");
});
