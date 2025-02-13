// Open Modal (Add/Edit)
function openModal(isEdit = false, buttonId = null, label = "", action = "show_icon", data = "{}") {
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

    const url = isEdit ? `/admin/buttons/update/${buttonId}` : "/admin/buttons/add/";
    const method = isEdit ? "PUT" : "POST";

    await fetch(url, { method, headers: { "Content-Type": "application/json" }, body: JSON.stringify(jsonData) });

    closeModal();
    htmx.ajax("GET", "/admin/buttons", { target: "#button-container", swap: "innerHTML" });
}

// Delete Confirmation
async function confirmDelete(buttonId) {
    if (!confirm("Are you sure?")) return;
    await fetch(`/admin/buttons/remove/${buttonId}`, { method: "DELETE" });
    htmx.ajax("GET", "/admin/buttons", { target: "#button-container", swap: "innerHTML" });
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

document.body.addEventListener("htmx:afterSwap", function (event) {
    if (event.detail.target.id === "chat-box") {
        scrollChatToBottom();
    }
});

document.addEventListener("DOMContentLoaded", function () {
    rebindButtons();
    scrollChatToBottom();
});

let selectedMessage = null;
let selectedUser = null;

/**
 * Show context menu on message right-click
 */
document.addEventListener("DOMContentLoaded", function () {
    document.getElementById("chat-box").addEventListener("contextmenu", function (event) {
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
async function deleteMessage() {
    if (!selectedMessage) return;
    await fetch(`/admin/delete-message/${selectedMessage}`, { method: "DELETE" });
    alert("🗑️ Message deleted!");
    document.getElementById("chat-context-menu").classList.add("hidden");
    htmx.trigger("#chat-box", "load"); // Refresh chat
}

async function banUser() {
    if (!selectedUser) return;
    await fetch(`/admin/ban-user/${selectedUser}`, { method: "POST" });
    alert("🚨 User banned!");
    document.getElementById("chat-context-menu").classList.add("hidden");
}

async function timeoutUser() {
    if (!selectedUser) return;
    await fetch(`/admin/timeout-user/${selectedUser}`, { method: "POST" });
    alert("⏳ User timed out!");
    document.getElementById("chat-context-menu").classList.add("hidden");
}

async function updateViewer() {
    if (!selectedUser) return;
    await fetch(`/admin/update-viewer/${selectedUser}`, { method: "POST" });
    alert("🔄 Viewer updated!");
    document.getElementById("chat-context-menu").classList.add("hidden");
}
