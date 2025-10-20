const formatter = new Intl.DateTimeFormat('en-US', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
});


function showUser(text, shouldPrint = false) {
    if (text.trim() === "") {
        return;
    }
    let timestamp = `${formatter.format(new Date().getTime()).slice(0, -3)}: `
    log.innerHTML += `${timestamp}${text}<br><br>`;
    log.scrollTop = log.scrollHeight;
    if (shouldPrint) {
        console.log(text);
    }
}

window.logger.onLog((event, text, shouldPrint = false) => {
    showUser(text, shouldPrint)
});