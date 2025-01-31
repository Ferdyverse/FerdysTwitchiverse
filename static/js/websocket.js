let socket;
let reconnectAttempts = 0;
let reconnectInterval = 5000; // Reconnect every 5 seconds if disconnected

function connectWebSocket() {
    console.log("Connecting to WebSocket...");
    socket = new WebSocket(`ws://${window.location.host}/ws`);

    // WebSocket connection established
    socket.onopen = () => {
        console.log("WebSocket connected!");
        reconnectAttempts = 0; // Reset reconnect attempts
        updateTopBar("message", "Ferdyverse online!");
    };

    // WebSocket message received
    socket.onmessage = (event) => {
        const data = JSON.parse(event.data);

        if (data.alert) {
            const { type, user, size } = data.alert;

            // Update top bar and show alert
            if (type === "follower") {
                updateTopBar("follower", user);
                showAlertWithGSAP(type, user, size);
            } else if (type === "subscriber") {
                updateTopBar("subscriber", user);
                updateTopBar("message", "NEW SUBSCRIBER!");
                showAlertWithGSAP(type, user, size);
            } else if (type === "raid") {
                updateTopBar("message", "Something changed in the Ferdyverse!");
                showURL("http://localhost:8000/raid", { raider: user, viewers: size }, 27000);
            } else if (type === "donation") {
                updateTopBar("message", "NEW DONATION!");
                showAlertWithGSAP(type, user, size);
            }
        } else if (data.message) {
            // Update custom message
            updateTopBar("message", data.message);
        } else if (data.goal) {
            const { text, current, target } = data.goal;
            updateGoal(text, current, target);
        } else if (data.icon) {
            const { id, action, name } = data.icon;
            if (action === "add") {
                addIcon(id, name);
            } else {
                removeIcon(id);
            }
        } else if (data.html){
            const { content, lifetime=0 } = data.html
            showHTML(content, lifetime)
        } else if (data.clickable) {
            const { action, object_id } = data.clickable
            if (action === "add") {
                createClickableElement(object_id, data.clickable);
            } else if (action === "remove") {
                removeClickableElement(object_id);
            }
        } else {
            console.warn("Unknown data format received:", data);
        }
    };

    // WebSocket connection closed
    socket.onclose = (event) => {
        console.warn("WebSocket connection closed:", event.reason || "No reason provided");
        updateTopBar("message", "WS: reconnecting to server...");
        attemptReconnect(); // Attempt to reconnect
    };

    // WebSocket error
    socket.onerror = (error) => {
        console.error("WebSocket error:", error);
        socket.close(); // Close connection on error
    };
}

function attemptReconnect() {
    reconnectAttempts++;
    const delay = Math.min(reconnectInterval * reconnectAttempts, 30000); // Cap at 30 seconds
    console.log(`Attempting to reconnect in ${delay / 1000} seconds...`);

    setTimeout(() => {
        connectWebSocket();
    }, delay);
}

// Establish WebSocket connection
connectWebSocket();
