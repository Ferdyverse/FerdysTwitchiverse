// chat.js
/*
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
*/


export function updateChat(messages) {
    const chatContainer = document.getElementById("chat-container");

    // Entferne vorherigen Cursor
    removeCursor();

    // Stelle sicher, dass maximal 5 Nachrichten angezeigt werden
    while (messages.length > 20) {
        messages.shift();
    }

    // Nachrichten, die bereits existieren, nicht neu rendern
    chatContainer.innerHTML = "";

    // Alle vorherigen Nachrichten einfach einfügen
    for (let i = 0; i < messages.length - 1; i++) {
        const chatMessage = document.createElement("div");
        chatMessage.className = "chat-message";
        chatMessage.innerHTML = `<span class="chat-user">${messages[i].user}:</span> <span class="chat-text">${messages[i].message}</span>`;
        chatContainer.appendChild(chatMessage);
    }

    // Die letzte Nachricht tippen
    if (messages.length > 0) {
        const lastMsg = messages[messages.length - 1];

        const chatMessage = document.createElement("div");
        chatMessage.className = "chat-message";
        chatMessage.innerHTML = `<span class="chat-user">${lastMsg.user}:</span> <span class="chat-text"></span>`;

        chatContainer.appendChild(chatMessage);
        chatContainer.scrollTop = chatContainer.scrollHeight;

        // Starte die Tipp-Animation nur für die letzte Nachricht
        typeMessage(chatMessage.querySelector(".chat-text"), lastMsg.message, () => {
            addCursor(); // Cursor erst hinzufügen, wenn das Tippen fertig ist
        });
    }
}

// Funktion für den Tipp-Effekt
function typeMessage(element, message, callback, speed = 50) {
    let i = 0;
    function typeNextChar() {
        if (i < message.length) {
            element.textContent += message[i];
            i++;
            setTimeout(typeNextChar, speed);
        } else if (callback) {
            callback(); // Führe Callback aus, wenn fertig getippt
        }
    }
    typeNextChar();
}

// Fügt den blinkenden Cursor in einer neuen Zeile hinzu
function addCursor() {
    const chatContainer = document.getElementById("chat-container");

    // Cursor entfernen, falls er schon existiert
    removeCursor();

    const cursorLine = document.createElement("div");
    cursorLine.className = "chat-cursor";
    chatContainer.appendChild(cursorLine);
}

// Entfernt den Cursor, falls er schon existiert
function removeCursor() {
    const existingCursor = document.querySelector(".chat-cursor");
    if (existingCursor) {
        existingCursor.remove();
    }
}
