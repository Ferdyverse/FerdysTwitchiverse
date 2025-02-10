// topbar.js
const lastFollowerElement = document.getElementById("last-follower");
const lastSubscriberElement = document.getElementById("last-subscriber");
const customMessageElement = document.getElementById("cm_scrolling");

export function updateScrollingMessage(message) {
  customMessageElement.style.setProperty("--message-length", message.length);
  customMessageElement.textContent = message;
}

export function updateTopBar(section, content) {
  switch (section) {
    case "follower":
      lastFollowerElement.innerHTML = `<strong><i class="fa fa-user"></i>Last Follower</strong><span>${content}</span>`;
      animateTopBar(section);
      break;
    case "subscriber":
      lastSubscriberElement.innerHTML = `<strong><i class="fa fa-star"></i>Last Subscriber</strong><span>${content}</span>`;
      animateTopBar(section);
      break;
    case "message":
      customMessageElement.innerHTML = `${content}`;
      break;
    default:
      console.warn(`Unknown section: ${section}`);
  }
}

export function animateTopBar(section) {
  const element = section === "follower" ? lastFollowerElement : lastSubscriberElement;
  gsap.fromTo(
    element,
    { opacity: 0, y: -10 },
    { opacity: 1, y: 0, duration: 0.5 }
  );
}
