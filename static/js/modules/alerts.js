// alerts.js
export function playSoundForAlert(file) {
  const audio = new Audio(`/static/sounds/${file}`);
  audio.play();
}

export function adjustFontSizeToFit(element) {
  const parent = element.parentElement;
  const maxWidth = parent.clientWidth * 0.95;
  const maxHeight = parent.clientHeight * 0.95;
  let currentFontSize = parseFloat(window.getComputedStyle(element).fontSize);

  while (currentFontSize > 14) {
    element.style.fontSize = `${currentFontSize}px`;
    const elementWidth = element.scrollWidth;
    const elementHeight = element.scrollHeight;

    if (elementWidth <= maxWidth && elementHeight <= maxHeight) {
      break;
    }
    currentFontSize -= 1;
  }

  element.style.fontSize = `${Math.max(currentFontSize, 14)}px`;
}

export function cleanupOldAlerts() {
  const overlayElement = document.getElementById("overlay");
  const alerts = overlayElement.querySelectorAll(".alert");
  if (alerts.length > 5) {
    alerts[0].remove();
  }
}

export function showAlertWithGSAP(type, user, additionalInfo) {
  const overlayElement = document.getElementById("overlay");
  const alertElement = document.createElement("div");
  alertElement.className = `alert ${type}`;
  alertElement.innerHTML = `
      <video autoplay loop muted playsinline class="alert-background">
          <source src="/static/videos/${type}.webm" type="video/webm">
      </video>
      <div class="alert-content">
          <h1>${
            type === "follower"
              ? "New Follower!"
              : type === "raid"
              ? "Incoming Raid!"
              : "Alert!"
          }</h1>
          <p>${user}</p>
      </div>
  `;

  overlayElement.appendChild(alertElement);
  const alertContent = alertElement.querySelector(".alert-content");
  const paragraph = alertContent.querySelector("p");
  adjustFontSizeToFit(paragraph);
  playSoundForAlert(`${type}.mp3`);
  gsap.to(alertElement, { opacity: 1, y: 20, duration: 1 });
  setTimeout(() => {
    alertContent.style.opacity = 1;
  }, 2000);
  setTimeout(() => {
    gsap.to(alertElement, {
      opacity: 0,
      y: -20,
      duration: 1,
      onComplete: () => alertElement.remove(),
    });
  }, 6000);
  cleanupOldAlerts();
}

export function showSubBanner(user) {
  const overlayElement = document.getElementById("overlay");
  const subBanner = document.createElement("div");
  subBanner.className = "box";
  overlayElement.appendChild(subBanner);
  subBanner.innerHTML = `<div class="content"><p>${user}</p></div>`;
  playSoundForAlert("subscriber.mp3");
  setTimeout(() => {
    subBanner.remove();
  }, 6000);
}

export function startAdCountdown(duration, startTime) {
  const countdownElement = document.getElementById("ad-countdown");

  let remainingTime = duration - (Math.floor(Date.now() / 1000) - startTime);
  countdownElement.style.display = "block"; // Show countdown

  const interval = setInterval(() => {
    if (remainingTime <= 0) {
      clearInterval(interval);
      countdownElement.style.display = "none"; // Hide countdown
    } else {
      countdownElement.innerText = `Ad break in: ${remainingTime}s`;
      remainingTime--;
    }
  }, 1000);
}

export function playTTS(file) {
  playSoundForAlert(`tts/${file}`);
}
