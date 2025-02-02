const lastFollowerElement = document.getElementById("last-follower");
const lastSubscriberElement = document.getElementById("last-subscriber");
const customMessageElement = document.getElementById("cm_scrolling");
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

// Function to animate top bar updates
function animateTopBar(section) {
    const element = section === "follower" ? lastFollowerElement : lastSubscriberElement;
    gsap.fromTo(
        element,
        { opacity: 0, y: -10 },
        { opacity: 1, y: 0, duration: 0.5 }
    );
}

function updateGoal(text, current, goal) {
    const goalBox = document.getElementById('goal-box');
    const progressBar = document.getElementById('goal-bar');
    const goalText = goalBox.querySelector('span');

    // If there is valid data, update the goal and show the box
    if (current !== null && goal !== null) {
        const percentage = Math.min((current / goal) * 100, 100); // Cap at 100%
        progressBar.style.width = percentage + '%'; // Update progress bar width
        goalText.textContent = `${text} ${current} / ${goal}`; // Update text
        goalBox.classList.remove('hidden'); // Show the goal box
    } else {
        // Hide the goal box if no valid data
        goalBox.classList.add('hidden');
    }
}

// Function to add an icon dynamically
function addIcon(iconID, iconClass) {
    const iconContainer = document.getElementById('dynamic-icons');

    // Create a new icon element
    const newIcon = document.createElement('i');
    newIcon.id = `${iconID}`;
    newIcon.className = `fa ${iconClass}`; // Font Awesome icon class

    // Append the icon to the container
    iconContainer.appendChild(newIcon);
}

// Function to remove an icon by its class
function removeIcon(iconID) {
    const iconContainer = document.getElementById('dynamic-icons');
    const icons = iconContainer.querySelectorAll(`i[id="${iconID}"]`);

    // Remove each matching icon
    icons.forEach((icon) => iconContainer.removeChild(icon));
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

function showHTML(html, lifetime) {
    console.log(html);

    const htmlElement = document.createElement("div");
    htmlElement.className = "raw";
    htmlElement.style.opacity = "0";
    htmlElement.style.transition = "opacity 0.5s ease-in-out"; // Smooth fade-in transition
    htmlElement.innerHTML = html;

    // Append element first
    overlayElement.appendChild(htmlElement);

    // Ensure the browser registers the element before applying fade-in
    setTimeout(() => {
        htmlElement.style.opacity = "1"; // Trigger fade-in
    }, 50); // Small delay ensures CSS transition applies

    // If a lifetime is set, schedule fade-out and removal
    if (lifetime > 0) {
        setTimeout(() => {
            htmlElement.style.opacity = "0"; // Trigger fade-out

            setTimeout(() => {
                htmlElement.remove(); // Remove after fade-out
            }, 500); // Match fade-out duration
        }, lifetime);
    }
}

function triggerStarExplosion(x, y) {
    // Create the big rotating star
    const bigStar = document.createElement("i");
    bigStar.className = "fa fa-poo big-star";
    bigStar.style.position = "absolute";
    bigStar.style.left = `${x - 25}px`; // Adjust for center alignment
    bigStar.style.top = `${y - 25}px`;
    bigStar.style.fontSize = "50px";
    bigStar.style.color = "#7e5210ec";
    bigStar.style.opacity = "1";
    bigStar.style.transformOrigin = "center";
    overlayElement.appendChild(bigStar);

    // ✅ Rotate and scale the big star
    setTimeout(() => {
        bigStar.style.transform = "scale(1.5) rotate(360deg)"; // Grow and rotate
    }, 50);

    setTimeout(() => {
        bigStar.style.opacity = "0";
        bigStar.style.transform = "scale(0.5) rotate(720deg)"; // Shrink while rotating more
    }, 800);

    // Remove the big star after fading out
    setTimeout(() => {
        bigStar.remove();
    }, 1200);

    // ✅ Spawn mini stars **exactly from the center of the big star**
    setTimeout(() => {
        const numParticles = 30; // More stars for better explosion effect
        for (let i = 0; i < numParticles; i++) {
            createMiniStar(x, y);
        }
    }, 200);
}

// ✅ Function to create mini stars that fly outward
function createMiniStar(x, y) {
    const star = document.createElement("i");
    star.className = "fa fa-poo mini-star";
    star.style.position = "absolute";
    star.style.left = `${x}px`;
    star.style.top = `${y}px`;
    star.style.fontSize = "40px";
    star.style.color = getRandomColor();
    star.style.opacity = "1";
    overlayElement.appendChild(star);

    // Random explosion direction
    const angle = Math.random() * 2 * Math.PI;
    const distance = Math.random() * 180 + 80; // **Increased explosion radius**

    const newX = x + Math.cos(angle) * distance;
    const newY = y + Math.sin(angle) * distance;

    // Apply explosion outward effect
    setTimeout(() => {
        star.style.transform = `translate(${newX - x}px, ${newY - y}px) scale(1.5) rotate(${Math.random() * 360}deg)`;
    }, 100);

    // ✅ Apply raining effect (fall down after explosion)
    setTimeout(() => {
        const fallDistance = Math.random() * 200 + 100; // Random fall distance
        star.style.transition = "transform 1s linear, opacity 1s ease-out";
        star.style.transform = `translate(${newX - x}px, ${newY - y + fallDistance}px) scale(0.8) rotate(${Math.random() * 180}deg)`;
        star.style.opacity = "0";
    }, 600);

    // Remove after animation
    setTimeout(() => {
        star.remove();
    }, 1600);
}

function getRandomColor() {
    const colors = ["#FFD700", "#FFA500", "#FF4500", "#FFFF00", "#FF69B4"];
    return colors[Math.floor(Math.random() * colors.length)];
}

// Fetch initial data for the top bar
fetch("/overlay-data")
    .then((response) => response.json())
    .then((data) => {
        updateTopBar("follower", data.last_follower || "None");
        updateTopBar("subscriber", data.last_subscriber || "None");
        if (data.goal_text != "None") {
            updateGoal(data.goal_text, data.goal_current, data.goal_target);
        } else {
            updateGoal(null, null, null);
        }

    })
    .catch((error) => {
        console.error("Failed to fetch overlay data:", error);
        updateTopBar("message", "Failed to fetch initial data");
    });
