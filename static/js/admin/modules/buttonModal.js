// buttonModal.js
import { showFlashMessage } from "./flashMessage.js";
import { closeGenericModal } from "./modal.js";

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
  document.getElementById("modal-label").value = isEdit ? label : "";
  document.getElementById("modal-action").value = isEdit ? action : "";
  document.getElementById("modal-data").value = isEdit
    ? JSON.stringify(data, null, 2)
    : "{}";

  setTimeout(() => {
    const submitButton = document.getElementById("modal-submit");
    if (submitButton) {
      submitButton.setAttribute("data-button-id", isEdit ? buttonId : "null");
    } else {
      console.error("❌ Error: 'modal-submit' button not found!");
    }
  }, 50);
}

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
    prompt: promptChecked,
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

export { openButtonModal, submitButtonForm };
