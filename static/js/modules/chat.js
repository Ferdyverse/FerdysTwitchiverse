// chat.js
export function updateChat(messages) {
  const chatContainer = document.getElementById("chat-container");
  while (messages.length > 5) {
    messages.shift();
  }
  chatContainer.innerHTML = "";
  messages.forEach((msg) => {
    const chatMessage = document.createElement("div");
    chatMessage.className = "chat-message";
    chatMessage.id = `msg-${msg.id}`;
    chatMessage.innerHTML = `
      <div class="chat-content">
          <p class="chat-user">${msg.user}</p>
          <p class="chat-text">${msg.message}</p>
      </div>
    `;
    chatContainer.appendChild(chatMessage);
    chatContainer.scrollTop = chatContainer.scrollHeight;
    setTimeout(() => {
      chatMessage.style.transition = "opacity 4s ease-out";
      chatMessage.style.opacity = "0";
      setTimeout(() => chatMessage.remove(), 4000);
    }, 15000);
  });
}
