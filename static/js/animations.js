const lastFollowerElement = document.getElementById("last-follower");
const lastSubscriberElement = document.getElementById("last-subscriber");
const customMessageElement = document.getElementById("custom-message");
const overlayElement = document.getElementById("overlay");

// Function to update scrolling messages
function updateScrollingMessage(message) {
    customMessageElement.style.setProperty("--message-length", message.length);
    customMessageElement.textContent = message;
}

// Function to update specific sections of the top bar
function updateTopBar(section, content) {
    const element = section === "follower" ? lastFollowerElement : lastSubscriberElement;

    switch (section) {
        case "follower":
            lastFollowerElement.textContent = `Last Follower: ${content}`;
            animateTopBar(section);
            break;
        case "subscriber":
            lastSubscriberElement.textContent = `Last Subscriber: ${content}`;
            animateTopBar(section);
            break;
        case "message":
            customMessageElement.textContent = `Message: ${content}`;
            break;
        default:
            console.warn(`Unknown section: ${section}`);
    }
}

// Function to animate top bar updates
function animateTopBar(section) {
    const element = section === "follower" ? lastFollowerElement : lastSubscriberElement;
    gsap.fromTo(
        element,
        { opacity: 0, y: -10 },
        { opacity: 1, y: 0, duration: 0.5 }
    );
}

// Function to play alert sounds
function playSoundForAlert(type) {
    const audio = new Audio(
        type === "subscriber"
            ? "/static/sounds/subscriber.mp3"
            : "/static/sounds/follower.mp3"
    );
    audio.play();
}

// Function to display alerts with GSAP animation
function showAlertWithGSAP(type, user) {
    const alertElement = document.createElement("div");
    alertElement.className = `alert ${type}`;
    alertElement.innerHTML = `
        <h1>${type === "subscriber" ? "New Subscriber!" : type === "follower" ? "New Follower!" : "Alert!"}</h1>
        <p>${user ? `${user} just ${type}!` : "Action triggered!"}</p>
    `;
    overlayElement.appendChild(alertElement);

    // Play sound for the alert
    playSoundForAlert(type);

    // Animate with GSAP
    gsap.to(alertElement, { opacity: 1, y: 20, duration: 1 });
    setTimeout(() => {
        gsap.to(alertElement, {
            opacity: 0,
            y: -20,
            duration: 1,
            onComplete: () => alertElement.remove(),
        });
    }, 4000); // Keep visible for 4 seconds

    // Cleanup old alerts
    cleanupOldAlerts();
}

// Function to limit the number of visible alerts
function cleanupOldAlerts() {
    const alerts = overlayElement.querySelectorAll(".alert");
    if (alerts.length > 5) {
        alerts[0].remove(); // Remove the oldest alert
    }
}

// Fetch initial data for the top bar
fetch("/overlay-data")
    .then((response) => response.json())
    .then((data) => {
        updateTopBar("follower", data.last_follower || "None");
        updateTopBar("subscriber", data.last_subscriber || "None");
    })
    .catch((error) => {
        console.error("Failed to fetch overlay data:", error);
        updateTopBar("message", "Failed to fetch initial data");
    });
