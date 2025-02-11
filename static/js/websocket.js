import { updateTopBar } from "./modules/topbar.js";
import {
  showAlertWithGSAP,
  showSubBanner,
  startAdCountdown,
} from "./modules/alerts.js";
import { updateGoal } from "./modules/goal.js";
import { addIcon, removeIcon } from "./modules/icons.js";
import { showHTML } from "./modules/display.js";
import { triggerStarExplosion } from "./modules/stars.js";
import { updateChat, updateAdminChat } from "./modules/chat.js";
import {
  createClickableElement,
  removeClickableElement,
} from "./modules/clickables.js";

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
        showSubBanner(user);
      } else if (type === "gift_sub") {
        updateTopBar("message", `${user} gifted ${size} subs!`);
        showSubBanner(user);
      } else if (type === "raid") {
        updateTopBar("message", "Something changed in the Ferdyverse!");
        showURL(
          "http://localhost:8000/raid",
          { raider: user, viewers: size },
          27000
        );
      } else if (type === "redemption") {
        updateTopBar("message", `${user} redeemed: ${data.alert.message}`);
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
    } else if (data.html) {
      const { content, lifetime = 0 } = data.html;
      showHTML(content, lifetime);
    } else if (data.clickable) {
      const { action, object_id } = data.clickable;
      if (action === "add") {
        createClickableElement(object_id, data.clickable);
      } else if (action === "remove") {
        removeClickableElement(object_id);
      }
    } else if (data.hidden) {
      const { action, user, x, y } = data.hidden;
      if (action === "found") {
        triggerStarExplosion(x, y);
        updateTopBar("message", `${user} hat etwas gefunden!`);
      }
    } else if (data.chat) {
      updateChat(data.chat);
    } else if (data.admin_chat) {
      const { username, message } = data.admin_chat;
      updateAdminChat(username, message);
    } else if (data.admin_alert && data.admin_alert.type === "ad_break") {
      startAdCountdown(data.admin_alert.duration, data.admin_alert.start_time);
    }
    if (data.overlay_event) {
      const { action, data: payload } = data.overlay_event;
      handleOverlayAction(action, payload);
    } else {
      console.warn("Unknown data format received:", data);
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

function handleOverlayAction(action, payload) {
  switch (action) {
    case "show_icon":
      addIcon(payload.id, payload.name);
      break;
    case "play_animation":
      showAlertWithGSAP(payload.type, payload.user, payload.size);
      break;
    default:
      console.warn("Unknown overlay action:", action);
  }
}

// Establish WebSocket connection
connectWebSocket();
