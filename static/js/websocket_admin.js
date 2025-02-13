let socket;
let reconnectAttempts = 0;
let reconnectInterval = 5000; // Reconnect every 5 seconds if disconnected
const MAX_CHAT_MESSAGES = 50; // Limit chat messages to prevent overflow
const MAX_EVENTS = 50; // Limit events to prevent overflow

// Ensure chat history is loaded on page load via HTMX
document.addEventListener("DOMContentLoaded", function () {
  loadChatHistory();
  connectWebSocket();
});

/**
 * Load the last 50 chat messages using HTMX
 */
function loadChatHistory() {
  console.log("📥 Loading chat history...");
  htmx.ajax("GET", "/chat", { target: "#chat-box", swap: "innerHTML" });
}

/**
 * Establish WebSocket connection
 */
function connectWebSocket() {
  console.log("🔌 Connecting to WebSocket...");
  socket = new WebSocket(`ws://${window.location.host}/ws`);

  // WebSocket connection established
  socket.onopen = () => {
    console.log("✅ WebSocket connected!");
    reconnectAttempts = 0;
  };

  // WebSocket message received
  socket.onmessage = (event) => {
    const data = JSON.parse(event.data);

    if (data.admin_chat) {
        const { username, message, avatar, badges, color, timestamp } = data.admin_chat;
        updateAdminChat(username, message, avatar, badges, color, timestamp);
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
    attemptReconnect();
  };

  // WebSocket error
  socket.onerror = (error) => {
    console.error("❌ WebSocket error:", error);
    socket.close();
  };
}

/**
 * Update Admin Chat Box (WebSocket Messages)
 */
function updateAdminChat(username, message, avatarUrl = "", badges = [], userColor = "#ffffff", timestamp = null) {
    const chatBox = document.getElementById("chat-box");

    // Convert timestamp to local time ⏰
    const now = timestamp ? new Date(timestamp * 1000) : new Date();
    const localTime = now.toLocaleTimeString("de-DE", { hour: "2-digit", minute: "2-digit" });

    // Create message container
    const newMessage = document.createElement("div");
    newMessage.classList.add("chat-message", "flex", "items-start", "space-x-3", "p-3", "rounded-md", "bg-gray-800", "border", "border-gray-700", "mb-2", "shadow-sm");

    // Avatar (Optional)
    const avatar = avatarUrl
        ? `<img src="${avatarUrl}" alt="${username}" class="chat-avatar w-10 h-10 rounded-full border border-gray-600">`
        : `<img src="/static/images/default_avatar.png" class="chat-avatar w-10 h-10 rounded-full border border-gray-600">`;

    // Badges 🏅
    let badgeHtml = "";
    if (badges.length > 0) {
        badgeHtml = badges
            .map((badge) => `<img src="${badge}" class="chat-badge" alt="badge">`)
            .join("");
    }

    // Message HTML
    newMessage.innerHTML = `
        ${avatar}
        <div class="chat-content flex flex-col w-full">
            <div class="chat-header flex justify-between items-center text-gray-400 text-sm mb-1">
                <div class="chat-username font-bold flex items-center" style="color: ${userColor};">
                    ${badgeHtml} ${username}
                </div>
                <div class="chat-timestamp text-xs">${localTime}</div>
            </div>
            <div class="chat-text text-gray-300 break-words bg-gray-900 p-2 rounded-lg w-fit max-w-3xl">
                ${message}
            </div>
        </div>
    `;

    // Append message to chat
    chatBox.appendChild(newMessage);

    // Auto-scroll to bottom
    chatBox.scrollTop = chatBox.scrollHeight;

    // Remove old messages if limit is reached
    while (chatBox.children.length > MAX_CHAT_MESSAGES) {
        chatBox.removeChild(chatBox.firstChild);
    }
}

/**
 * Ensure the chat box auto-scrolls to the latest message
 */
function scrollChatToBottom() {
    let chatBox = document.getElementById("chat-box");
    chatBox.scrollTop = chatBox.scrollHeight;
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
 * Attempt Reconnection to WebSocket
 */
function attemptReconnect() {
  reconnectAttempts++;
  const delay = Math.min(reconnectInterval * reconnectAttempts, 30000); // Cap at 30 seconds
  console.log(`🔄 Attempting to reconnect in ${delay / 1000} seconds...`);

  setTimeout(() => {
    connectWebSocket();
  }, delay);
}
