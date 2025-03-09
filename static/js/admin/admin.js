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
  const promptChecked = document.getElementById("modal-prompt").checked;

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

  const response = await fetch("/admin/twitch/reward/create", {
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
  const response = await fetch("/admin/twitch/redemption/fulfill", {
    method: "POST",
    body: JSON.stringify({ reward_id: rewardId, redeem_id: redeemId }),
    headers: { "Content-Type": "application/json" },
  });

  const result = await response.json();
  showFlashMessage(result.message, result.status);

  htmx.ajax("GET", "/admin/twitch/rewards/pending", {
    target: "#pending-rewards",
    swap: "innerHTML",
  });
}

async function cancelRedemption(rewardId, redeemId) {
  const response = await fetch("/admin/twitch/redemption/cancel", {
    method: "POST",
    body: JSON.stringify({ reward_id: rewardId, redeem_id: redeemId }),
    headers: { "Content-Type": "application/json" },
  });

  const result = await response.json();
  showFlashMessage(result.message, result.status);

  htmx.ajax("GET", "/admin/twitch/rewards/pending", {
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
    const response = await fetch(`/admin/twitch/reward/delete/${rewardId}`, {
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

    // Hide context menu
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
        const response = await fetch(`/admin/viewers/update/${selectedUser}`, {
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

async function submitScheduledJob(event) {
    event.preventDefault();

    const jobId = document.getElementById("scheduled-job-id").value;
    const jobType = document.getElementById("scheduled-job-type").value;
    const intervalSeconds = document.getElementById("scheduled-job-interval").value;
    const cronExpression = document.getElementById("scheduled-job-cron").value;
    const payload = document.getElementById("scheduled-job-payload").value;

    const jobData = {
        job_type: jobType,
        interval_seconds: intervalSeconds ? parseInt(intervalSeconds) : null,
        cron_expression: cronExpression || null,
        payload: payload ? JSON.parse(payload) : {}
    };

    const endpoint = jobId ? `/admin/scheduled/jobs/edit/${jobId}` : `/admin/scheduled/jobs/add`;

    const response = await fetch(endpoint, {
        method: jobId ? "POST" : "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(jobData)
    });

    const result = await response.json();

    if (result.success) {
        closeGenericModal('scheduled-jobs-modal');
        resetScheduledJobForm();
        reloadScheduledJobs();
    } else {
        alert("Error saving job: " + (result.error || "Unknown error"));
    }
}

function resetScheduledJobForm() {
  document.getElementById("scheduled-job-id").value = "";
  document.getElementById("scheduled-job-type").value = "";
  document.getElementById("scheduled-job-interval").value = "";
  document.getElementById("scheduled-job-cron").value = "";
  document.getElementById("scheduled-job-payload").value = "";
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
      reloadMessagePool();
    }
  } catch (error) {
    console.error("❌ Failed to delete message from pool:", error);
  }
}

// ✏️ Edit Scheduled Job (Fills the form for editing)
function editScheduledJob(id, jobType, interval, cron, payload) {
    document.getElementById("scheduled-job-id").value = id;
    document.getElementById("scheduled-job-type").value = jobType;
    document.getElementById("scheduled-job-interval").value = interval || "";
    document.getElementById("scheduled-job-cron").value = cron || "";

    // Ensure payload is shown properly (as JSON)
    document.getElementById("scheduled-job-payload").value = payload ? JSON.stringify(payload, null, 2) : "";

    openGenericModal("scheduled-jobs-modal"); // Show modal
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

async function reloadScheduledJobs() {
  try {
    const response = await fetch("/admin/scheduled/jobs");
    const html = await response.text();
    document.getElementById("scheduled-jobs").innerHTML = html;
  } catch (error) {
    console.error("❌ Failed to reload scheduled jobs:", error);
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

function updateClock() {
    const now = new Date();
    const hours = now.getHours().toString().padStart(2, "0");
    const minutes = now.getMinutes().toString().padStart(2, "0");
    const seconds = now.getSeconds().toString().padStart(2, "0");

    const timeString = `${hours}:${minutes}:${seconds}`;
    document.getElementById("overlay-clock").innerText = timeString;
}

// Update clock every second
setInterval(updateClock, 1000);
updateClock();

function sendCommand(endpoint) {
    fetch(`http://localhost:8000${endpoint}`, {
        method: "POST",
    }).then(response => response.json())
      .then(data => console.log("Response:", data))
      .catch(error => console.error("Error:", error));
}

function changeVolume(value) {
    fetch(`http://localhost:8000/spotify/volume/${value}`, {
        method: "POST",
    }).then(response => response.json())
      .then(data => console.log("Volume changed:", data))
      .catch(error => console.error("Error:", error));
}

function togglePlayPause() {
    let btn = document.getElementById("playPauseBtn");
    if (btn.innerText === "▶️") {
        sendCommand('/spotify/play');
        btn.innerText = "⏸";
    } else {
        sendCommand('/spotify/pause');
        btn.innerText = "▶️";
    }
}

function updatePlaybackState() {
    fetch(`http://localhost:8000/spotify/currently-playing`)
        .then(response => response.json())
        .then(data => {
            let btn = document.getElementById("playPauseBtn");
            let volumeSlider = document.getElementById("volume-slider");

            // Update play/pause button
            if (!data.error && data.title) {
                btn.innerText = "⏸"; // If something is playing, show Pause
            } else {
                btn.innerText = "▶️"; // Otherwise, show Play
            }

            // Update volume slider
            if (data.volume !== null && data.volume !== undefined) {
                volumeSlider.value = data.volume;
                console.log(`Volume updated to: ${data.volume}`);
            }
        })
        .catch(error => console.error("Error fetching playback state:", error));
}
updatePlaybackState();
