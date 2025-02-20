// modal.js

function openGenericModal(modalId) {
  document.getElementById(modalId).classList.remove("hidden");
}

function closeGenericModal(modalId) {
  document.getElementById(modalId).classList.add("hidden");
}

export { openGenericModal, closeGenericModal };
