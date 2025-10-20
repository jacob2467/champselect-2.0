const { contextBridge, ipcRenderer } = require('electron')

contextBridge.exposeInMainWorld("logger", {
    onLog: (callback) => ipcRenderer.on("log", callback)
});

contextBridge.exposeInMainWorld("debugging", {
    openConsole: () => ipcRenderer.invoke("openDevConsole")
});