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
            customMessageElement.textContent = `${content}`;
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
function showAlertWithGSAP(type, user, additionalInfo) {
    const alertElement = document.createElement("div");
    alertElement.className = `alert ${type}`;
    alertElement.innerHTML = `
        <video autoplay loop muted playsinline class="alert-background">
            <source src="/static/videos/${type}.webm" type="video/webm">
        </video>
        <div class="alert-content">
            <h1>${type === "subscriber"
                ? "New Subscriber!"
                : type === "follower"
                ? "New Follower!"
                : type === "raid"
                ? "Incoming Raid!"
                : "Alert!"}</h1>
            <p>${type === "raid"
                ? `${user} is raiding with ${additionalInfo || 0} viewers!`
                : `${user}`}</p>
        </div>
    `;

    // Append the alert to the overlay
    overlayElement.appendChild(alertElement);

    // Dynamically adjust the font size of the <p> tag
    const alertContent = alertElement.querySelector(".alert-content");
    const paragraph = alertContent.querySelector("p");
    adjustFontSizeToFit(paragraph);

    // Play sound for the alert
    playSoundForAlert(type);

    // Animate the video and text
    gsap.to(alertElement, { opacity: 1, y: 20, duration: 1 }); // Fade in the container
    setTimeout(() => {
        alertContent.style.opacity = 1; // Fade in the text
    }, 2000); // Delay text fade-in by 2 seconds

    // Automatically remove the alert after 6 seconds
    setTimeout(() => {
        gsap.to(alertElement, {
            opacity: 0,
            y: -20,
            duration: 1,
            onComplete: () => alertElement.remove(),
        });
    }, 6000);

    // Cleanup old alerts
    cleanupOldAlerts();
}

function adjustFontSizeToFit(element) {
    const parent = element.parentElement;
    const maxWidth = parent.clientWidth * 0.95; // Use 95% of parent width
    const maxHeight = parent.clientHeight * 0.95; // Use 95% of parent height
    let currentFontSize = parseFloat(window.getComputedStyle(element).fontSize);

    console.log(`Initial font size: ${currentFontSize}px`);
    console.log(`Max Width: ${maxWidth}px`);

    while (currentFontSize > 14) { // Prevent shrinking below 14px
        element.style.fontSize = `${currentFontSize}px`;

        // Force reflow
        const elementWidth = element.scrollWidth;
        const elementHeight = element.scrollHeight;

        console.log(
            `Parent Width: ${maxWidth}, Element Width: ${elementWidth}, Current Font Size: ${currentFontSize}px`
        );

        if (elementWidth <= maxWidth && elementHeight <= maxHeight) {
            break; // Stop resizing when the text fits
        }

        currentFontSize -= 1; // Reduce font size
    }

    console.log(`Final font size: ${Math.max(currentFontSize, 14)}px`);
    element.style.fontSize = `${Math.max(currentFontSize, 14)}px`; // Ensure readability
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
