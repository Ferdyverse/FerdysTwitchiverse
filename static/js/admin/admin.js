let selectedMessage = null;
let selectedUser = null;

// === Generic Modal Handling ===
function openGenericModal(modalId) {
  document.getElementById(modalId).classList.remove("hidden");
}

function closeGenericModal(modalId) {
  document.getElementById(modalId).classList.add("hidden");
}

// === Flash Message Handling ===
function showFlashMessage(message, type = "info") {
  const flashMessage = document.getElementById("flash-message");
  const flashText = document.getElementById("flash-message-text");

  flashText.innerText = message;
  flashMessage.classList.remove("hidden");
  flashMessage.style.opacity = "1";

  // Apply colors based on message type
  let colorClass = "bg-blue-600";
  if (type === "success") colorClass = "bg-green-600";
  if (type === "error") colorClass = "bg-red-600";

  flashMessage.firstElementChild.className = `text-white text-lg px-6 py-3 rounded-lg shadow-lg ${colorClass}`;

  // Hide after 3 seconds
  setTimeout(() => {
    flashMessage.style.opacity = "0";
    setTimeout(() => flashMessage.classList.add("hidden"), 500);
  }, 3000);
}

// === Button Modal (Add/Edit) ===
function openButtonModal(
  isEdit = false,
  buttonId = null,
  label = "",
  action = "show_icon",
  data = "{}",
  prompt = false
) {
  const modal = document.getElementById("button-modal");
  modal.classList.remove("hidden");

  document.getElementById("modal-title").innerText = isEdit
    ? "Edit Button"
    : "Add Button";
  document.getElementById("modal-label").value = isEdit ? label : ""; // Clear for new button
  document.getElementById("modal-action").value = isEdit ? action : ""; // Reset action
  document.getElementById("modal-data").value = isEdit
    ? JSON.stringify(data, null, 2)
    : "{}"; // Reset data
  document.getElementById("modal-prompt").checked = isEdit ? prompt : false;

  setTimeout(() => {
    const submitButton = document.getElementById("modal-submit");
    if (submitButton) {
      submitButton.setAttribute("data-button-id", isEdit ? buttonId : "null");
    } else {
      console.error("❌ Error: 'modal-submit' button not found!");
    }
  }, 50);
}

function closeButtonModal() {
  document.getElementById("button-modal").classList.add("hidden");
}

// === Submit Button Form ===
async function submitButtonForm() {
  const submitButton = document.getElementById("modal-submit");
  if (!submitButton) {
    console.error("❌ Error: 'modal-submit' button not found!");
    showFlashMessage("❌ Error: Submit button missing!", "error");
    return;
  }

  const buttonId = submitButton.getAttribute("data-button-id");
  const isEdit = buttonId && buttonId !== "null";
  const promptChecked = document.getElementById("modal-prompt").checked; // ✅ Prompt-Checkbox auslesen

  const jsonData = {
    label: document.getElementById("modal-label").value.trim(),
    action: document.getElementById("modal-action").value.trim(),
    data: JSON.parse(document.getElementById("modal-data").value || "{}"),
    prompt: promptChecked, // ✅ Prompt in JSON packen
  };

  if (!jsonData.label || !jsonData.action) {
    showFlashMessage("⚠️ Label and Action are required!", "error");
    return;
  }

  const url = isEdit
    ? `/admin/buttons/update/${buttonId}`
    : "/admin/buttons/add/";
  const method = isEdit ? "PUT" : "POST";

  try {
    const response = await fetch(url, {
      method,
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(jsonData),
    });

    if (response.ok) {
      showFlashMessage("✅ Button saved!", "success");
      closeGenericModal("button-modal");

      htmx.ajax("GET", "/admin/buttons", {
        target: "#button-container",
        swap: "innerHTML",
      });
    } else {
      const errorData = await response.json();
      showFlashMessage(
        `❌ Error: ${errorData.detail || "Unknown error"}`,
        "error"
      );
    }
  } catch (error) {
    console.error("❌ Error saving button:", error);
    showFlashMessage("❌ Error saving button", "error");
  }
}

// === Delete Button ===
async function confirmDelete(buttonId) {
  if (!confirm("Are you sure?")) return;
  await fetch(`/admin/buttons/remove/${buttonId}`, { method: "DELETE" });
  htmx.ajax("GET", "/admin/buttons", {
    target: "#button-container",
    swap: "innerHTML",
  });
}

// === Auto-Scroll Functions ===
function scrollChatToBottom() {
  let chatBox = document.getElementById("chat-box");
  if (chatBox) chatBox.scrollTop = chatBox.scrollHeight;
}

function scrollEventsToBottom() {
  let eventLog = document.getElementById("event-log");
  if (eventLog) eventLog.scrollTop = eventLog.scrollHeight;
}

// Ensure scrolling to bottom when HTMX swaps content
document.body.addEventListener("htmx:afterSwap", function (event) {
  if (event.detail.target.id === "chat-box") scrollChatToBottom();
  if (event.detail.target.id === "event-log") scrollEventsToBottom();
  if (event.detail.target.id === "button-container") initSortable();
});

// === Channel Point Reward Management ===
async function createReward() {
  const title = document.getElementById("reward-title").value;
  const cost = document.getElementById("reward-cost").value;
  const description = document.getElementById("reward-description").value;
  const requireInput = document.getElementById("reward-require-input").checked;

  if (!title || !cost) {
    showFlashMessage("⚠️ Title and cost are required!", "error");
    return;
  }

  const response = await fetch("/admin/twitch/create-reward/", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      title,
      cost,
      prompt: description,
      require_input: requireInput,
    }),
  });

  const result = await response.json();
  showFlashMessage(
    result.message,
    result.status === "success" ? "success" : "error"
  );

  if (result.status === "success") {
    closeGenericModal("reward-modal");
    htmx.ajax("GET", "/admin/twitch/rewards/", {
        target: "#reward-list",
        swap: "innerHTML",
      });
  }
}

// === Channel Point Redemptions ===
async function fulfillRedemption(rewardId, redeemId) {
  const response = await fetch("/admin/twitch/fulfill-redemption", {
    method: "POST",
    body: JSON.stringify({ reward_id: rewardId, redeem_id: redeemId }),
    headers: { "Content-Type": "application/json" },
  });

  const result = await response.json();
  showFlashMessage(result.message, result.status);

  htmx.ajax("GET", "/admin/twitch/pending-rewards", {
    target: "#pending-rewards",
    swap: "innerHTML",
  });
}

async function cancelRedemption(rewardId, redeemId) {
  const response = await fetch("/admin/twitch/cancel-redemption", {
    method: "POST",
    body: JSON.stringify({ reward_id: rewardId, redeem_id: redeemId }),
    headers: { "Content-Type": "application/json" },
  });

  const result = await response.json();
  showFlashMessage(result.message, result.status);

  htmx.ajax("GET", "/admin/twitch/pending-rewards", {
    target: "#pending-rewards",
    swap: "innerHTML",
  });
}

// Listen for "Enter" key in the chat input
document
  .getElementById("admin-chat-input")
  .addEventListener("keypress", function (event) {
    if (event.key === "Enter") {
      event.preventDefault(); // Prevents accidental new lines
      sendChatMessage();
    }
  });

async function sendChatMessage() {
  const messageInput = document.getElementById("admin-chat-input");
  const senderType = document.getElementById("sender-type").value;
  const message = messageInput.value.trim();

  if (!message) {
    showFlashMessage("⚠️ Cannot send an empty message!", "error");
    return;
  }

  try {
    const response = await fetch("/chat/send/", {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: new URLSearchParams({ message, sender: senderType }),
    });

    if (response.ok) {
      messageInput.value = ""; // Clear input after sending
    } else {
      showFlashMessage("❌ Failed to send message", "error");
    }
  } catch (error) {
    console.error("❌ Error sending chat message:", error);
    showFlashMessage("❌ Error sending message", "error");
  }
}

async function deleteReward(rewardId) {
  if (!rewardId) {
    console.error("❌ Error: Reward ID is missing!");
    showFlashMessage("❌ Error: Reward ID is missing!", "error");
    return;
  }

  const confirmDelete = confirm("Are you sure you want to delete this reward?");
  if (!confirmDelete) return;

  try {
    const response = await fetch(`/admin/twitch/delete-reward/${rewardId}`, {
      method: "DELETE",
    });

    const result = await response.json();
    if (response.ok) {
      showFlashMessage("✅ Reward deleted!", "success");

      htmx.ajax("GET", "/admin/twitch/rewards/", {
        target: "#reward-list",
        swap: "innerHTML",
      });
    } else {
      showFlashMessage(
        `❌ Error: ${result.detail || "Failed to delete reward"}`,
        "error"
      );
    }
  } catch (error) {
    console.error("❌ Error deleting reward:", error);
    showFlashMessage("❌ Error deleting reward!", "error");
  }
}

async function triggerButtonAction(action, data, ask = false) {
  if (!action) {
    console.error("❌ No action specified.");
    showFlashMessage("❌ No action specified!", "error");
    return;
  }

  if (ask == Boolean(true)) {
    const userInput = prompt("Enter the required input:");
    if (userInput === null) {
      console.log("❌ Action canceled.");
      return;
    }
    data.userInput = userInput; // Attach user input
  } else {
    data.userInput = String(ask);
  }

  try {
    const response = await fetch("/overlay/trigger/", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ action, data }),
    });

    const result = await response.json();
    if (response.ok) {
      showFlashMessage("✅ Overlay triggered!", "success");
    } else {
      showFlashMessage(
        `❌ Error: ${result.detail || "Unknown error"}`,
        "error"
      );
    }
  } catch (error) {
    console.error("❌ Error triggering overlay:", error);
    showFlashMessage("❌ Failed to trigger overlay.", "error");
  }
}

document.addEventListener("DOMContentLoaded", () => {
    const chatBox = document.getElementById("chat-box");
    const contextMenu = document.getElementById("chat-context-menu");
    let selectedMessage = null;
    let selectedMessageId = null; // Store message ID
    let selectedUser = null; // Store user ID

    chatBox.addEventListener("contextmenu", (event) => {
        event.preventDefault();
        const messageElement = event.target.closest(".chat-message");
        if (!messageElement) return;

        selectedMessage = messageElement;
        selectedMessageId = selectedMessage.getAttribute("data-message-id"); // Get message ID
        selectedUser = selectedMessage.getAttribute("data-user-id"); // Get user ID
        const username = selectedMessage.querySelector(".chat-username").textContent.trim();

        document.getElementById("context-username").textContent = `@${username}`;
        contextMenu.style.top = `${event.pageY}px`;
        contextMenu.style.left = `${event.pageX}px`;
        contextMenu.classList.remove("hidden");
    });

    document.addEventListener("click", (event) => {
        if (!contextMenu.contains(event.target)) {
            contextMenu.classList.add("hidden");
        }
    });

    // Copy Message
    window.copyMessage = () => {
        if (!selectedMessage) return;
        const text = selectedMessage.querySelector(".chat-text").textContent.trim();
        navigator.clipboard.writeText(text);
        showFlashMessage("Message copied to clipboard!", "success");
        contextMenu.classList.add("hidden");
    };

    // Pin Message
    window.pinMessage = () => {
        if (!selectedMessage) return;
        const pinnedContainer = document.getElementById("pinned-messages");
        if (!pinnedContainer) return;

        const clonedMessage = selectedMessage.cloneNode(true);
        clonedMessage.classList.add("border-yellow-400", "bg-yellow-900/20", "p-2");
        pinnedContainer.appendChild(clonedMessage);

        showFlashMessage("Message pinned!", "success");
        contextMenu.classList.add("hidden");
    };

    // Delete Message
    window.deleteMessage = async () => {
        if (!selectedMessageId) return;

        const response = await fetch(`/admin/twitch/delete-message/${selectedMessageId}`, {
            method: "DELETE",
        });

        const result = await response.json();
        showFlashMessage(
            result.message,
            result.status === "success" ? "success" : "error"
        );

        contextMenu.classList.add("hidden");
        htmx.ajax("GET", "/chat", {
            target: "#chat-box",
            swap: "innerHTML",
        });
    };

    // Ban User
    window.banUser = async () => {
        if (!selectedUser) return;
        const response = await fetch(`/admin/twitch/ban-user/${selectedUser}`, {
            method: "POST",
        });

        const result = await response.json();
        showFlashMessage(
            result.message,
            result.status === "success" ? "success" : "error"
        );

        contextMenu.classList.add("hidden");
    };

    // Timeout User
    window.timeoutUser = async () => {
        if (!selectedUser) return;
        const response = await fetch(`/admin/twitch/timeout-user/${selectedUser}`, {
            method: "POST",
        });

        const result = await response.json();
        showFlashMessage(
            result.message,
            result.status === "success" ? "success" : "error"
        );

        contextMenu.classList.add("hidden");
    };

    // Update Viewer
    window.updateViewer = async () => {
        if (!selectedUser) return;
        const response = await fetch(`/admin/twitch/update-viewer/${selectedUser}`, {
            method: "POST",
        });

        const result = await response.json();
        showFlashMessage(
            result.message,
            result.status === "success" ? "success" : "error"
        );

        contextMenu.classList.add("hidden");
    };
});

function applyVisualReordering(buttons) {
  const btn_container = document.getElementById("button-container");
  btn_container.innerHTML = ""; // Clear container
  buttons.forEach((button) => btn_container.appendChild(button)); // Re-add buttons in new order
  console.log("🔄 Applied visual reordering after first move!");
}

function initSortable() {
  const btn_container = document.getElementById("button-container");

  if (!btn_container) {
    console.error("❌ #button-container not found!");
    return;
  }

  new Sortable(btn_container, {
    animation: 150, // Smooth animation
    ghostClass: "dragging", // Adds opacity when dragging
    chosenClass: "chosen", // Adds highlight when selected
    dragClass: "drag", // Class while dragging
    handle: ".drag-handle", // Allows dragging only via ☰ handle
    filter: ".no-drag", // Prevents certain elements from being dragged
    onEnd: function (evt) {
      const buttons = [...btn_container.querySelectorAll(".draggable")]; // Get only draggable buttons

      const orderedButtons = buttons.map((button, index) => ({
        id: button.getAttribute("data-id"),
        position: index,
      }));

      fetch("/admin/buttons/reorder", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(orderedButtons),
      }).then((response) => {
        if (response.ok) {
          console.log("✅ Button order saved!");
          applyVisualReordering(buttons); // Update UI immediately
        } else {
          console.error("❌ Failed to save button order");
        }
      });
    },
  });

  console.log("✅ Sortable initialized successfully!");
}

// 📅 Submit Scheduled Message (Add or Edit)
async function submitScheduledMessage(event) {
  event.preventDefault();

  const messageId = document.getElementById("scheduled-message-id").value;
  const messageText = document.getElementById("scheduled-message-text").value;
  const interval = document.getElementById("scheduled-message-interval").value;
  const category = document.getElementById("scheduled-message-category").value;

  const data = {
    message: messageText,
    interval: parseInt(interval, 10),
    category: category || null, // ✅ Handle "No Category" case
  };

  const url = messageId
    ? `/admin/scheduled/messages/edit/${messageId}`
    : "/admin/scheduled/messages/add";
  const method = messageId ? "POST" : "POST";

  try {
    const response = await fetch(url, {
      method: method,
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    });

    const result = await response.json();
    if (result.success) {
      console.log("✅ Scheduled message updated!");
      reloadScheduledMessages(); // ✅ Reload table after success
      resetScheduledMessageForm(); // ✅ Reset form but KEEP modal open
    } else {
      console.error("❌ Failed to update scheduled message:", result.error);
    }
  } catch (error) {
    console.error("❌ Error updating scheduled message:", error);
  }
}

function resetScheduledMessageForm() {
  document.getElementById("scheduled-message-id").value = "";
  document.getElementById("scheduled-message-text").value = "";
  document.getElementById("scheduled-message-interval").value = "";
  document.getElementById("scheduled-message-category").value = ""; // ✅ Reset category
}

// 🗑️ Delete Scheduled Message
async function removeScheduledMessage(messageId) {
  try {
    const response = await fetch(`/admin/scheduled/messages/${messageId}`, {
      method: "DELETE",
    });
    if (response.ok) {
      console.log("✅ Scheduled message deleted!");
      reloadScheduledMessages(); // ✅ Reload table
    }
  } catch (error) {
    console.error("❌ Failed to delete scheduled message:", error);
  }
}

// 🎲 Submit Message Pool Entry (Add or Edit)
async function submitScheduledMessage(event) {
  event.preventDefault();

  const messageId =
    document.getElementById("scheduled-message-id").value || null;
  const messageText = document
    .getElementById("scheduled-message-text")
    .value.trim();
  const interval = document.getElementById("scheduled-message-interval").value;
  const category =
    document.getElementById("scheduled-message-category").value || null;

  if ((!messageText && !category) || !interval) {
    console.error("❌ Either a message or a category must be provided.");
    return;
  }

  const data = {
    id: messageId, // ✅ Send the ID for edit mode
    message: messageText || null,
    interval: parseInt(interval, 10),
    category: category,
  };

  console.log("🚀 Sending Scheduled Message:", data);

  try {
    const response = await fetch(`/admin/scheduled/messages/add`, {
      // ✅ Always use /add
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    });

    const result = await response.json();
    if (result.success) {
      console.log("✅ Scheduled message updated/added!");
      reloadScheduledMessages();
      resetScheduledMessageForm();
    } else {
      console.error("❌ Failed to update/add scheduled message:", result.error);
    }
  } catch (error) {
    console.error("❌ Error updating/adding scheduled message:", error);
  }
}

async function submitMessagePool(event) {
  event.preventDefault();

  const messageId = document.getElementById("message-pool-id").value;
  const category = document.getElementById("message-pool-category").value;
  const message = document.getElementById("message-pool-message").value;

  const data = {
    category: category || null,
    message: message,
  };

  const url = messageId
    ? `/admin/scheduled/pool/edit/${messageId}`
    : "/admin/scheduled/pool/add";
  const method = messageId ? "POST" : "POST";

  try {
    const response = await fetch(url, {
      method: method,
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    });

    const result = await response.json();
    if (result.success) {
      console.log("✅ Message pool updated!");
      reloadMessagePool();
      resetMessagePoolForm();
    } else {
      console.error("❌ Failed to update message pool:", result.error);
    }
  } catch (error) {
    console.error("❌ Error updating message pool:", error);
  }
}

function resetMessagePoolForm() {
  document.getElementById("message-pool-id").value = "";
  document.getElementById("message-pool-category").value = "";
  document.getElementById("message-pool-message").value = "";
}

// 🗑️ Delete Message from Pool
async function removePoolMessage(messageId) {
  try {
    const response = await fetch(`/admin/scheduled/pool/${messageId}`, {
      method: "DELETE",
    });
    if (response.ok) {
      console.log("✅ Pool message deleted!");
      reloadMessagePool(); // ✅ Reload table
    }
  } catch (error) {
    console.error("❌ Failed to delete message from pool:", error);
  }
}

// ✏️ Edit Scheduled Message (Fills the form for editing)
function editScheduledMessage(id, message, interval) {
  document.getElementById("scheduled-message-id").value = id;
  document.getElementById("scheduled-message-text").value = message;
  document.getElementById("scheduled-message-interval").value = interval;

  openGenericModal("scheduled-messages-modal"); // Show modal
}

// ✏️ Edit Pool Message (Fills the form for editing)
function editPoolMessage(id, message, category = "") {
  document.getElementById("message-pool-id").value = id;
  document.getElementById("message-pool-message").value = message;
  document.getElementById("message-pool-category").value = category; // May be empty

  openGenericModal("message-pool-modal"); // Show modal
}

// Reset Scheduled Message Form when opening for adding a new entry
function addScheduledMessage() {
  document.getElementById("scheduled-message-id").value = "";
  document.getElementById("scheduled-message-text").value = "";
  document.getElementById("scheduled-message-interval").value = "";

  openGenericModal("scheduled-messages-modal");
}

// Reset Pool Message Form when opening for adding a new entry
function addMessageToPool() {
  document.getElementById("message-pool-id").value = "";
  document.getElementById("message-pool-message").value = "";
  document.getElementById("message-pool-category").value = "";

  openGenericModal("message-pool-modal");
}

// ✏️ Edit Scheduled Message (Fills the form for editing)
function editScheduledMessage(id, message, interval, category = "") {
  resetScheduledMessageForm();
  document.getElementById("scheduled-message-id").value = id;
  document.getElementById("scheduled-message-text").value = message;
  document.getElementById("scheduled-message-interval").value = interval;
  document.getElementById("scheduled-message-category").value = category; // Default to "" if empty
  openGenericModal("scheduled-messages-modal");
}
function editPoolMessage(id, message, category) {
  resetMessagePoolForm();

  document.getElementById("message-pool-id").value = id;
  document.getElementById("message-pool-message").value = message;

  if (category !== undefined && category !== "undefined") {
    document.getElementById("message-pool-category").value = category;
  } else {
    document.getElementById("message-pool-category").value = ""; // Default empty
  }

  console.log("Editing Pool Message:", { id, message, category }); // Debugging

  openGenericModal("message-pool-modal");
}

// Open Modals and Reset Forms
function openScheduledMessagesModal() {
  resetScheduledMessagesForm();
  openGenericModal("scheduled-messages-modal");
}

function openMessagePoolModal() {
  resetMessagePoolForm();
  openGenericModal("message-pool-modal");
}

// ❌ Close Modals and Reset Forms
function closeScheduledMessagesModal() {
  resetScheduledMessagesForm();
  closeGenericModal("scheduled-messages-modal");
}

function closeMessagePoolModal() {
  resetMessagePoolForm();
  closeGenericModal("message-pool-modal");
}

// ➕ Add Scheduled Message
function addScheduledMessage() {
  openScheduledMessagesModal();
}

// ➕ Add Message to Pool
function addMessageToPool() {
  openMessagePoolModal();
}

async function reloadScheduledMessages() {
  try {
    const response = await fetch("/admin/scheduled/messages");
    const html = await response.text();
    document.getElementById("scheduled-messages").innerHTML = html;
  } catch (error) {
    console.error("❌ Failed to reload scheduled messages:", error);
  }
}

async function reloadMessagePool() {
  try {
    const response = await fetch("/admin/scheduled/messages/pool");
    const html = await response.text();
    document.getElementById("message-pool").innerHTML = html;
  } catch (error) {
    console.error("❌ Failed to reload message pool:", error);
  }
}

// 📋 Load ToDos with status filter
function loadTodos(status = null) {
  const url = status ? `/todo/todos?status=${status}` : "/todo/todos";

  htmx.ajax("GET", url, {
    target: "#todo-list",
    swap: "innerHTML",
  });
}


// Action sidebar
const toggleButton = document.getElementById("toggle-menu");
  const closeButton = document.getElementById("close-menu");
  const menu = document.getElementById("button-menu");
  const actionButtons = menu.querySelectorAll("button:not(#close-menu)");

  // Toggle menu visibility
  toggleButton.addEventListener("click", () => {
      menu.classList.toggle("-translate-x-full");
  });

  closeButton.addEventListener("click", () => {
      menu.classList.add("-translate-x-full");
  });

  // Close menu when clicking any action button
  actionButtons.forEach(button => {
      button.addEventListener("click", () => {
          menu.classList.add("-translate-x-full");
      });
  });
