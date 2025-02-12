// === Modal Functions ===
function openModal(
  isEdit = false,
  buttonId = null,
  label = "",
  action = "show_icon",
  data = "{}"
) {
  const modal = document.getElementById("button-modal");
  modal.style.display = "flex";

  const title = document.getElementById("modal-title");
  title.innerText = isEdit ? "Edit Button" : "Add Button";

  // Populate the form with values if editing
  document.getElementById("modal-label").value = label;
  document.getElementById("modal-action").value = action;
  document.getElementById("modal-data").value = JSON.stringify(data, null, 2);

  // Adjust submit function
  document.getElementById("modal-submit").onclick = function () {
    submitButtonForm(isEdit, buttonId);
  };
}

function closeModal() {
  const modal = document.getElementById("button-modal");
  modal.style.display = "none";
}

// === Form Submission ===
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

  try {
    await fetch(url, {
      method: method,
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(jsonData),
    });

    closeModal();
    htmx.ajax("GET", "/admin/buttons", {
      target: "#button-container",
      swap: "innerHTML",
    });
  } catch (error) {
    console.error("Error submitting form:", error);
  }
}

// === Delete Confirmation ===
async function confirmDelete(buttonId) {
  if (!confirm("🚨 Are you sure you want to delete this button?")) return;

  try {
    await fetch(`/admin/buttons/remove/${buttonId}`, { method: "DELETE" });
    htmx.ajax("GET", "/admin/buttons", {
      target: "#button-container",
      swap: "innerHTML",
    });
  } catch (error) {
    console.error("Error deleting button:", error);
  }
}

// === Ensure Buttons Work ===
function rebindButtons() {
  document.querySelectorAll(".main-btn").forEach((button) => {
    button.removeEventListener("click", handleButtonClick);
    button.addEventListener("click", handleButtonClick);
  });
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
