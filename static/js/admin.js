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
  data = "{}"
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
  const isEdit = buttonId && buttonId !== "null"; // ✅ Properly check if it's an edit action

  const jsonData = {
    label: document.getElementById("modal-label").value.trim(),
    action: document.getElementById("modal-action").value.trim(),
    data: JSON.parse(document.getElementById("modal-data").value || "{}"),
  };

  if (!jsonData.label || !jsonData.action) {
    showFlashMessage("⚠️ Label and Action are required!", "error");
    return;
  }

  const url = isEdit
    ? `/admin/buttons/update/${buttonId}`
    : "/admin/buttons/add/";
  const method = isEdit ? "PUT" : "POST"; // ✅ Use POST when adding a button

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

  const response = await fetch("/admin/create-reward/", {
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
    htmx.trigger("#reward-list", "load");
  }
}

// === Channel Point Redemptions ===
async function fulfillRedemption(rewardId, redeemId) {
  const response = await fetch("/admin/fulfill-redemption", {
    method: "POST",
    body: JSON.stringify({ reward_id: rewardId, redeem_id: redeemId }),
    headers: { "Content-Type": "application/json" },
  });

  const result = await response.json();
  showFlashMessage(result.message, result.status);

  htmx.ajax("GET", "/admin/pending-rewards", {
    target: "#pending-rewards",
    swap: "innerHTML",
  });
}

async function cancelRedemption(rewardId, redeemId) {
  const response = await fetch("/admin/cancel-redemption", {
    method: "POST",
    body: JSON.stringify({ reward_id: rewardId, redeem_id: redeemId }),
    headers: { "Content-Type": "application/json" },
  });

  const result = await response.json();
  showFlashMessage(result.message, result.status);

  htmx.ajax("GET", "/admin/pending-rewards", {
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
    const response = await fetch("/send-chat/", {
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
    const response = await fetch(`/admin/delete-reward/${rewardId}`, {
      method: "DELETE",
    });

    const result = await response.json();
    if (response.ok) {
      showFlashMessage("✅ Reward deleted!", "success");

      htmx.ajax("GET", "/admin/rewards/", {
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

async function triggerButtonAction(action, data) {
  if (!action) {
    console.error("❌ No action specified.");
    showFlashMessage("❌ No action specified!", "error");
    return;
  }

  try {
    const response = await fetch("/trigger-overlay/", {
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

document.addEventListener("DOMContentLoaded", function () {
  const chatBox = document.getElementById("chat-box");
  const chatMenu = document.getElementById("chat-context-menu");

  chatBox.addEventListener("contextmenu", function (event) {
    event.preventDefault();

    // Find the clicked chat message
    let messageElement = event.target.closest(".chat-message");
    if (!messageElement) return;

    // Store message and user info
    selectedMessage = messageElement.dataset.messageId;
    selectedUser = messageElement.dataset.userId;

    // Position the menu at cursor
    chatMenu.style.left = `${event.pageX}px`;
    chatMenu.style.top = `${event.pageY}px`;
    chatMenu.classList.remove("hidden");
  });

  // Hide menu when clicking outside
  document.addEventListener("click", function (event) {
    if (!event.target.closest("#chat-context-menu")) {
      chatMenu.classList.add("hidden");
    }
  });

  scrollChatToBottom();
  scrollEventsToBottom();
  initSortable();
});

async function deleteMessage() {
  if (!selectedMessage) return;
  const response = await fetch(`/admin/delete-message/${selectedMessage}`, {
    method: "DELETE",
  });

  const result = await response.json();
  showFlashMessage(
    result.message,
    result.status === "success" ? "success" : "error"
  );

  document.getElementById("chat-context-menu").classList.add("hidden");
  htmx.ajax("GET", "/chat", {
    target: "#pending-rewards",
    swap: "innerHTML",
  });
}

async function banUser() {
  if (!selectedUser) return;
  const response = await fetch(`/admin/ban-user/${selectedUser}`, {
    method: "POST",
  });

  const result = await response.json();
  showFlashMessage(
    result.message,
    result.status === "success" ? "success" : "error"
  );

  document.getElementById("chat-context-menu").classList.add("hidden");
}

async function timeoutUser() {
  if (!selectedUser) return;
  const response = await fetch(`/admin/timeout-user/${selectedUser}`, {
    method: "POST",
  });

  const result = await response.json();
  showFlashMessage(
    result.message,
    result.status === "success" ? "success" : "error"
  );

  document.getElementById("chat-context-menu").classList.add("hidden");
}

async function updateViewer() {
  if (!selectedUser) return;
  const response = await fetch(`/admin/update-viewer/${selectedUser}`, {
    method: "POST",
  });

  const result = await response.json();
  showFlashMessage(
    result.message,
    result.status === "success" ? "success" : "error"
  );

  document.getElementById("chat-context-menu").classList.add("hidden");
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

function applyVisualReordering(buttons) {
  const btn_container = document.getElementById("button-container");
  btn_container.innerHTML = ""; // Clear container
  buttons.forEach((button) => btn_container.appendChild(button)); // Re-add buttons in new order
  console.log("🔄 Applied visual reordering after first move!");
}
