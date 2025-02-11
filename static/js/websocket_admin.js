import { updateAdminChat } from "./modules/chat.js";

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
  };

  // WebSocket message received
  socket.onmessage = (event) => {
    const data = JSON.parse(event.data);

    if (data.admin_chat) {
      const { username, message } = data.admin_chat;
      updateAdminChat(username, message);
    } else if (data.admin_alert && data.admin_alert.type === "ad_break") {
      startAdCountdown(data.admin_alert.duration, data.admin_alert.start_time);
    }
  };

  // WebSocket connection closed
  socket.onclose = (event) => {
    console.warn(
      "WebSocket connection closed:",
      event.reason || "No reason provided"
    );
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
