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
import { updateChat } from "./modules/chat.js";
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
      handleAlert(data.alert);
    } else if (data.message) {
      updateTopBar("message", data.message);
    } else if (data.goal) {
      const { text, current, target } = data.goal;
      updateGoal(text, current, target);
    } else if (data.icon) {
      handleIcon(data.icon);
    } else if (data.html) {
      showHTML(data.html.content, data.html.lifetime || 0);
    } else if (data.clickable) {
      handleClickable(data.clickable);
    } else if (data.hidden) {
      handleHiddenItem(data.hidden);
    } else if (data.chat) {
      updateChat(data.chat);
    } else if (data.overlay_event) {
      handleOverlayAction(data.overlay_event.action, data.overlay_event.data);
    } else if (data.todo) {
      handleTodo(data.todo, data.action);
    } else {
      console.warn("Unknown data format received:", data);
    }
  };

  // 📌 Alert Handling
  function handleAlert(alert) {
    const { type, user, size, message } = alert;

    switch (type) {
      case "follower":
        updateTopBar("follower", user);
        showAlertWithGSAP(type, user, size);
        break;
      case "subscriber":
        updateTopBar("subscriber", user);
        updateTopBar("message", "NEW SUBSCRIBER!");
        showSubBanner(user);
        break;
      case "gift_sub":
        updateTopBar("message", `${user} hat ${size} subs verschenkt!`);
        showSubBanner(`${user} hat ${size} subs verschenkt!`);
        break;
      case "raid":
        updateTopBar("message", "Something changed in the Ferdyverse!");
        showURL(
          "http://localhost:8000/raid",
          { raider: user, viewers: size },
          27000
        );
        break;
      case "redemption":
        updateTopBar("message", `${user} redeemed: ${message}`);
        showAlertWithGSAP(type, user, size);
        break;
      case "subscription_message":
        updateTopBar("subscriber", user);
        updateTopBar("message", message);
        showSubBanner(user);
        break;
      case "cheer":
        showCheerAnimation(user, alert.bits, message);
        break;
      default:
        console.warn("Unknown alert type:", type);
    }
  }

  // 📌 Icon Handling
  function handleIcon({ id, action, name }) {
    action === "add" ? addIcon(id, name) : removeIcon(id);
  }

  // 📌 Clickable Handling
  function handleClickable({ action, object_id, ...data }) {
    action === "add"
      ? createClickableElement(object_id, data)
      : removeClickableElement(object_id);
  }

  // 📌 Hidden Item Handling
  function handleHiddenItem({ action, user, x, y }) {
    if (action === "found") {
      triggerStarExplosion(x, y);
      updateTopBar("message", `${user} hat etwas gefunden!`);
    }
  }

  // 📌 ToDo Handling
  function handleTodo(todo, action) {
    switch (action) {
      case "create":
        createTodo(todo.id, todo.text, todo.user);
        break;
      case "show":
        showTodo(todo.id);
        break;
      case "remove":
        removeTodo(todo.id);
        break;
      default:
        console.warn("Unknown ToDo action:", action);
    }
  }

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
