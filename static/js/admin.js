// Open Modal (Add/Edit)
function openModal(
  isEdit = false,
  buttonId = null,
  label = "",
  action = "show_icon",
  data = "{}"
) {
  const modal = document.getElementById("button-modal");
  modal.classList.remove("hidden");

  const title = document.getElementById("modal-title");
  title.innerText = isEdit ? "Edit Button" : "Add Button";

  // Populate the form
  document.getElementById("modal-label").value = label;
  document.getElementById("modal-action").value = action;
  document.getElementById("modal-data").value = JSON.stringify(data, null, 2);

  document.getElementById("modal-submit").onclick = function () {
    submitButtonForm(isEdit, buttonId);
  };
}

// Close Modal
function closeModal() {
  document.getElementById("button-modal").classList.add("hidden");
}

// Submit Form
async function submitButtonForm(isEdit, buttonId) {
  const jsonData = {
    label: document.getElementById("modal-label").value,
    action: document.getElementById("modal-action").value,
    data: JSON.parse(document.getElementById("modal-data").value || "{}"),
  };

  const url = isEdit
    ? `/admin/buttons/update/${buttonId}`
    : "/admin/buttons/add/";
  const method = isEdit ? "PUT" : "POST";

  await fetch(url, {
    method,
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(jsonData),
  });

  closeModal();
  htmx.ajax("GET", "/admin/buttons", {
    target: "#button-container",
    swap: "innerHTML",
  });
}

// Delete Confirmation
async function confirmDelete(buttonId) {
  if (!confirm("Are you sure?")) return;
  await fetch(`/admin/buttons/remove/${buttonId}`, { method: "DELETE" });
  htmx.ajax("GET", "/admin/buttons", {
    target: "#button-container",
    swap: "innerHTML",
  });
}

function showFlashMessage(message, type = "info") {
  const flashMessage = document.getElementById("flash-message");

  // Set message and styles based on type
  flashMessage.innerText = message;
  flashMessage.className = `fixed top-4 right-4 px-4 py-2 rounded-md shadow-md transition-opacity duration-500 opacity-100`;

  if (type === "success") {
    flashMessage.classList.add("bg-green-500");
  } else if (type === "error") {
    flashMessage.classList.add("bg-red-500");
  } else {
    flashMessage.classList.add("bg-blue-500");
  }

  // Show message
  flashMessage.classList.remove("hidden");

  // Hide after 3 seconds
  setTimeout(() => {
    flashMessage.classList.add("opacity-0");
    setTimeout(() => flashMessage.classList.add("hidden"), 500);
  }, 3000);
}

function handleButtonClick(event) {
  const button = event.target;
  const action = button.getAttribute("hx-vals");

  fetch("/trigger-overlay/", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: action,
  });
}

// === Auto-Scroll Chat Box ===
function scrollChatToBottom() {
  let chatBox = document.getElementById("chat-box");
  chatBox.scrollTop = chatBox.scrollHeight;
}

function scrollEventsToBottom() {
  let eventLog = document.getElementById("event-log");
  eventLog.scrollTop = eventLog.scrollHeight;
}

document.body.addEventListener("htmx:afterSwap", function (event) {
  if (event.detail.target.id === "chat-box") {
    scrollChatToBottom();
  }
  if (event.detail.target.id === "event-log") {
    scrollEventsToBottom();
  }
});

document.addEventListener("DOMContentLoaded", function () {
  scrollChatToBottom();
  scrollEventsToBottom();
});

let selectedMessage = null;
let selectedUser = null;

/**
 * Show context menu on message right-click
 */
document.addEventListener("DOMContentLoaded", function () {
  document
    .getElementById("chat-box")
    .addEventListener("contextmenu", function (event) {
      event.preventDefault();

      // Find the clicked message element
      let messageElement = event.target.closest(".chat-message");
      if (!messageElement) return;

      // Store message and user info
      selectedMessage = messageElement.dataset.messageId;
      selectedUser = messageElement.dataset.userId;

      // Position the menu at the cursor
      const menu = document.getElementById("chat-context-menu");
      menu.style.left = `${event.pageX}px`;
      menu.style.top = `${event.pageY}px`;
      menu.classList.remove("hidden");
    });
});

/**
 * Hide context menu on click outside
 */
document.addEventListener("click", function (event) {
  if (!event.target.closest("#chat-context-menu")) {
    document.getElementById("chat-context-menu").classList.add("hidden");
  }
});

/**
 * Actions for context menu
 */
// Update Viewer
async function updateViewer() {
  if (!selectedUser) return;

  try {
    const response = await fetch(`/admin/update-viewer/${selectedUser}`, {
      method: "POST",
    });
    if (response.ok) {
      showFlashMessage("✅ Viewer updated successfully!", "success");
    } else {
      showFlashMessage("❌ Failed to update viewer.", "error");
    }
  } catch (error) {
    console.error("Error updating viewer:", error);
    showFlashMessage(
      "❌ An error occurred while updating the viewer.",
      "error"
    );
  }

  document.getElementById("chat-context-menu").classList.add("hidden");
}

// Delete Message
async function deleteMessage() {
  if (!selectedMessage) return;

  try {
    const response = await fetch(`/admin/delete-message/${selectedMessage}`, {
      method: "DELETE",
    });
    if (response.ok) {
      showFlashMessage("🗑️ Message deleted!", "success");
      htmx.trigger("#chat-box", "load"); // Refresh chat
    } else {
      showFlashMessage("❌ Failed to delete message.", "error");
    }
  } catch (error) {
    console.error("Error deleting message:", error);
    showFlashMessage(
      "❌ An error occurred while deleting the message.",
      "error"
    );
  }

  document.getElementById("chat-context-menu").classList.add("hidden");
}

// Ban User
async function banUser() {
  if (!selectedUser) return;

  try {
    const response = await fetch(`/admin/ban-user/${selectedUser}`, {
      method: "POST",
    });
    if (response.ok) {
      showFlashMessage("🚨 User banned!", "success");
    } else {
      showFlashMessage("❌ Failed to ban user.", "error");
    }
  } catch (error) {
    console.error("Error banning user:", error);
    showFlashMessage("❌ An error occurred while banning the user.", "error");
  }

  document.getElementById("chat-context-menu").classList.add("hidden");
}

// Timeout User
async function timeoutUser() {
  if (!selectedUser) return;

  try {
    const response = await fetch(`/admin/timeout-user/${selectedUser}`, {
      method: "POST",
    });
    if (response.ok) {
      showFlashMessage("⏳ User timed out!", "success");
    } else {
      showFlashMessage("❌ Failed to timeout user.", "error");
    }
  } catch (error) {
    console.error("Error timing out user:", error);
    showFlashMessage(
      "❌ An error occurred while timing out the user.",
      "error"
    );
  }

  document.getElementById("chat-context-menu").classList.add("hidden");
}

async function triggerButtonAction(action, data) {
  if (!action) {
    console.error("❌ No action specified.");
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
