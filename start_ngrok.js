const ngrok = require('ngrok');
(async function () {
    try {
        const url = await ngrok.connect(5001);
        console.log("NGROK_URL=" + url);
        // Keep alive indefinitely
        setInterval(() => { }, 1000 * 60 * 60);
    } catch (e) {
        console.error("NGROK_ERROR: " + e.message);
        process.exit(1);
    }
})();
