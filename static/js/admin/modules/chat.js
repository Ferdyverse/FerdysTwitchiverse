// chat.js
import { showFlashMessage } from "./flashMessage.js";

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
      messageInput.value = "";
    } else {
      showFlashMessage("❌ Failed to send message", "error");
    }
  } catch (error) {
    console.error("❌ Error sending chat message:", error);
    showFlashMessage("❌ Error sending message", "error");
  }
}

export { sendChatMessage };
