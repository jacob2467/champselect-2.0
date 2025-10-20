const { app, BrowserWindow, ipcMain } = require("electron/main");
const { spawn } = require('node:child_process');
const path = require('node:path')

const isDev = ! app.isPackaged;
const backendDir = isDev
    ? path.join(__dirname, "..")
    : path.join(process.resourcesPath, "backend");

const venvDir = path.join(process.resourcesPath, "venv");

const pyExecutable = isDev
    // If in development environment, use system interpreter
    ? "python"

    // If in bundled executable, path to Python interpreter in venv
    : process.platform === "darwin"
        ? path.join(venvDir, "bin", "python")
        : path.join(venvDir, "python.exe")

let mainWindow;
let flaskProcess = startFlask();


function startFlask() {
    return spawn(pyExecutable, [path.join(backendDir, "webapp.py")]);
}


function createWindow() {
    let win = new BrowserWindow({
        width: 800,
        height: 600,
        webPreferences: {
            preload: path.join(__dirname, 'preload.js')
        }
    });

    win.loadFile(path.join(__dirname, "index.html"));
    return win;
}


function displayToUser(content, shouldPrint = true) {
    try {
        mainWindow.webContents.send("log", content.toString(), shouldPrint);
    } catch (error) {
        console.log(content.toString());
    }
}


/**
 * Set up event listeners for console output from the spawned Flask process.
 */
function setupFlaskLogging() {
    flaskProcess.stdout.on('data', (data) => {
        displayToUser(data);
    });

    flaskProcess.stderr.on('data', (data) => {
        displayToUser(data);
    });

    flaskProcess.on('error', (err) => {
        displayToUser(`Error with Flask process: ${err}`);
    });

    flaskProcess.on('exit', (code, signal) => {
        displayToUser(`Flask process exited with code: ${code}, signal: ${signal}`);
    });
}

app.whenReady().then(async () => {
    setupFlaskLogging();

    // Wait for Flask server to start
    setTimeout(() => {
        // TODO: Repeatedly check if it's started rather than using a timeout
        mainWindow = createWindow();
    }, 1000);

    ipcMain.handle("openDevConsole", () => mainWindow.openDevTools());
});

/**
 * Attempt to terminate the running Flask process. If the attempt fails, log the error in the console.
 */
function terminateFlask() {
    if (!flaskProcess || flaskProcess.killed) {
        return;
    }

    try {
        flaskProcess.kill();
    } catch (error) {
        console.log(`Unable to terminate the flask process due to an error: ${error}`);
    }
}

// Make sure app closes when last window is closed
app.on('window-all-closed', app.quit);

app.on('before-quit', terminateFlask);