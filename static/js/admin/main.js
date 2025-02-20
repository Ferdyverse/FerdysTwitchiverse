// main.js
// main.js
import { openButtonModal, submitButtonForm } from "./modules/buttonModal.js";
import { showFlashMessage } from "./modules/flashMessage.js";
import { openGenericModal, closeGenericModal } from "./modules/modal.js";
import { sendChatMessage } from "./modules/chat.js";
import {
  deleteMessage,
  banUser,
  timeoutUser,
  updateViewer,
} from "./modules/chatModeration.js";
import { createReward, deleteReward } from "./modules/rewards.js";
import {
  submitScheduledMessage,
  removeScheduledMessage,
} from "./modules/scheduledMessages.js";
import { submitMessagePool, removePoolMessage } from "./modules/messagePool.js";
import { triggerButtonAction } from "./modules/overlayActions.js";
import { initSortable } from "./modules/sortable.js";

window.openButtonModal = openButtonModal;
window.submitButtonForm = submitButtonForm;
window.showFlashMessage = showFlashMessage;
window.openGenericModal = openGenericModal;
window.closeGenericModal = closeGenericModal;
window.sendChatMessage = sendChatMessage;
window.deleteMessage = deleteMessage;
window.banUser = banUser;
window.timeoutUser = timeoutUser;
window.updateViewer = updateViewer;
window.createReward = createReward;
window.deleteReward = deleteReward;
window.submitScheduledMessage = submitScheduledMessage;
window.removeScheduledMessage = removeScheduledMessage;
window.submitMessagePool = submitMessagePool;
window.removePoolMessage = removePoolMessage;
window.triggerButtonAction = triggerButtonAction;
window.initSortable = initSortable;

// Initialize sortable buttons on page load
document.addEventListener("DOMContentLoaded", function () {
  initSortable();
});
