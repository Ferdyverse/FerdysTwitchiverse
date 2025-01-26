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
        updateTopBar("message", "Connected to server");
    };

    // WebSocket message received
    socket.onmessage = (event) => {
        const data = JSON.parse(event.data);

        if (data.alert) {
            const { type, user } = data.alert;

            // Update top bar and show alert
            if (type === "follower") {
                updateTopBar("follower", user);
            } else if (type === "subscriber") {
                updateTopBar("subscriber", user);
            }

            showAlertWithGSAP(type, user);
        } else if (data.message) {
            // Update custom message
            updateTopBar("message", data.message);
        } else {
            console.warn("Unknown data format received:", data);
        }
    };

    // WebSocket connection closed
    socket.onclose = (event) => {
        console.warn("WebSocket connection closed:", event.reason || "No reason provided");
        updateTopBar("message", "Reconnecting to server...");
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
