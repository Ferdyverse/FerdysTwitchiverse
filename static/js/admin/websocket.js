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
        const { username, message, avatar, badges, color, timestamp, message_id, is_first } = data.admin_chat;
        updateAdminChat(username, message, avatar, badges, color, timestamp, message_id, is_first);
    } else if (data.admin_alert) {
        if (data.admin_alert.type === "ad_break"){
          startAdCountdown(data.admin_alert.duration, data.admin_alert.start_time);
        }
    } else if (data.event) {
        updateEventLog(data.event.message);
    } else {
      console.log(data)
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
function updateAdminChat(username, message, avatarUrl = "", badges = [], userColor = "#ffffff", timestamp = null, message_id = null, is_first = false) {
    const chatBox = document.getElementById("chat-box");

    // Convert timestamp to local time ⏰
    const now = timestamp ? new Date(timestamp * 1000) : new Date();
    const localTime = now.toLocaleTimeString("de-DE", { hour: "2-digit", minute: "2-digit" });

    console.log(is_first)

    // Create message container
    const newMessage = document.createElement("div");
    newMessage.classList.add("chat-message", "flex", "items-start", "space-x-3", "p-3", "rounded-md", "bg-gray-800", "border", "border-gray-700", "mb-2", "shadow-sm");
    newMessage.dataset.messageId = message_id;
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

    let important = false;
    if (message && message.trim().toLowerCase().includes("!ping")) {
        important = true;
    }

    // Set background color based on importance
    let chatColor = important ? "bg-red-400 text-black-600" : "bg-gray-900 text-gray-300";

    // Message HTML
    newMessage.innerHTML = `
        <div class="chat-avatar-container flex flex-col items-center">
          ${avatar}
          ${is_first ? '<span class="first-marker mt-1">First</span>' : ''}
      </div>
        <div class="chat-content flex flex-col w-full">
            <div class="chat-header flex justify-between items-center text-gray-400 text-sm mb-1">
                <div class="chat-username font-bold flex items-center" style="color: ${userColor};">
                    ${badgeHtml} ${username}
                </div>
                <div class="chat-timestamp text-xs">${localTime}</div>
            </div>
            <div class="chat-text ${chatColor} break-words p-2 rounded-lg w-fit max-w-3xl">
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
  const progressBar = document.createElement("div");
  progressBar.classList.add("progress-bar");

  if (!adCountdown.querySelector(".progress-bar")) {
    adCountdown.appendChild(progressBar);
  }

  adCountdown.style.display = "flex";
  adCountdown.style.opacity = "1";

  function formatTime(seconds) {
    const minutes = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${minutes}:${secs.toString().padStart(2, "0")}`;
  }

  function updateCountdown() {
    const currentTime = Math.floor(Date.now() / 1000);
    let remainingTime = (currentTime - startTime);

    if (remainingTime <= 0) {
      adCountdown.innerHTML = `🚨 <strong>Ad Break Now!</strong>`;
      progressBar.style.width = "0%";
      adCountdown.classList.add("blinking");

      // Hide after 5 seconds
      setTimeout(() => {
        adCountdown.style.opacity = "0";
        setTimeout(() => (adCountdown.style.display = "none"), 500);
      }, 5000);
      return;
    }

    // Apply blinking effect if < 60 seconds left
    if (remainingTime <= 60) {
      adCountdown.classList.add("blinking");
    } else {
      adCountdown.classList.remove("blinking");
    }

    adCountdown.innerHTML = `⏳ <strong>${formatTime(remainingTime)}</strong>`;
    adCountdown.appendChild(progressBar);
    progressBar.style.width = `${(remainingTime / duration) * 100}%`;

    requestAnimationFrame(updateCountdown);
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
