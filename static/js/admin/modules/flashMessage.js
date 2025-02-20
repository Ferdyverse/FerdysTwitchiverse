// flashMessage.js

function showFlashMessage(message, type = "info") {
  const flashMessage = document.getElementById("flash-message");
  const flashText = document.getElementById("flash-message-text");

  flashText.innerText = message;
  flashMessage.classList.remove("hidden");
  flashMessage.style.opacity = "1";

  let colorClass = "bg-blue-600";
  if (type === "success") colorClass = "bg-green-600";
  if (type === "error") colorClass = "bg-red-600";

  flashMessage.firstElementChild.className = `text-white text-lg px-6 py-3 rounded-lg shadow-lg ${colorClass}`;

  setTimeout(() => {
    flashMessage.style.opacity = "0";
    setTimeout(() => flashMessage.classList.add("hidden"), 500);
  }, 3000);
}

export { showFlashMessage };
