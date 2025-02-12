let socket;
let reconnectAttempts = 0;
let reconnectInterval = 5000; // Reconnect every 5 seconds if disconnected
const MAX_CHAT_MESSAGES = 50; // Limit chat messages to prevent overflow
const MAX_EVENTS = 50; // Limit events to prevent overflow

function connectWebSocket() {
  console.log("Connecting to WebSocket...");
  socket = new WebSocket(`ws://${window.location.host}/ws`);

  // WebSocket connection established
  socket.onopen = () => {
    console.log("✅ WebSocket connected!");
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
    } else if (data.event) {
      updateEventLog(data.event.message);
    }
  };

  // WebSocket connection closed
  socket.onclose = (event) => {
    console.warn(
      "⚠️ WebSocket connection closed:",
      event.reason || "No reason provided"
    );
    attemptReconnect(); // Attempt to reconnect
  };

  // WebSocket error
  socket.onerror = (error) => {
    console.error("❌ WebSocket error:", error);
    socket.close(); // Close connection on error
  };
}

/**
 * Update Admin Chat Box
 */
function updateAdminChat(username, message) {
  const chatBox = document.getElementById("chat-box");
  const newMessage = document.createElement("div");
  newMessage.classList.add("chat-message");
  newMessage.innerHTML = `<span class="chat-username">${username}</span>: <span class="chat-text">${message}</span>`;

  chatBox.appendChild(newMessage);

  // Auto-scroll to the latest message
  chatBox.scrollTop = chatBox.scrollHeight;

  // Remove old messages if limit is reached
  while (chatBox.children.length > MAX_CHAT_MESSAGES) {
    chatBox.removeChild(chatBox.firstChild);
  }
}

/**
 * Update Event Log
 */
function updateEventLog(message) {
  const eventBox = document.getElementById("event-log");
  const newEvent = document.createElement("div");
  newEvent.classList.add("event-message");
  newEvent.innerHTML = `<span class="event-text">${message}</span>`;

  eventBox.appendChild(newEvent);

  // Auto-scroll to the latest event
  eventBox.scrollTop = eventBox.scrollHeight;

  // Remove old events if limit is reached
  while (eventBox.children.length > MAX_EVENTS) {
    eventBox.removeChild(eventBox.firstChild);
  }
}

/**
 * Ad Break Countdown
 */
function startAdCountdown(duration, startTime) {
  const adCountdown = document.getElementById("ad-countdown");
  adCountdown.style.display = "block";

  let remainingTime = duration - (Math.floor(Date.now() / 1000) - startTime);

  function updateCountdown() {
    if (remainingTime <= 0) {
      adCountdown.style.display = "none";
      return;
    }

    adCountdown.innerHTML = `⏳ Ad break starts in ${remainingTime} seconds...`;
    remainingTime--;

    setTimeout(updateCountdown, 1000);
  }

  updateCountdown();
}

/**
 * Attempt Reconnection
 */
function attemptReconnect() {
  reconnectAttempts++;
  const delay = Math.min(reconnectInterval * reconnectAttempts, 30000); // Cap at 30 seconds
  console.log(`🔄 Attempting to reconnect in ${delay / 1000} seconds...`);

  setTimeout(() => {
    connectWebSocket();
  }, delay);
}

// Establish WebSocket connection
connectWebSocket();
