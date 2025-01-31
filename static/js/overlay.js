const backendURL = "http://localhost:8000";  // FastAPI backend URL
const canvas = document.getElementById("spaceCanvas");
const ctx = canvas.getContext("2d");

let spaceObjects = [];

// ✅ Fetch and create clickable objects
async function loadClickableObjects() {
    try {
        const response = await fetch(`${backendURL}/get-clickable-objects`);
        const objects = await response.json();

        console.log("🎯 Clickable objects received:", objects);

        // Only create elements if they don't already exist
        for (const [id, obj] of Object.entries(objects)) {
            if (!document.getElementById(id)) {
                createClickableElement(id, obj);
            }
        }
    } catch (error) {
        console.error("❌ Error loading clickable objects:", error);
    }
}

// ✅ Function to create a new clickable element with FIXED position
function createClickableElement(id, obj) {
    const container = document.getElementById("overlay");

    const element = document.createElement("div");
    element.id = id;
    element.classList.add("clickable");
    element.style.position = "fixed"; // ✅ Ensures the position does not change
    element.style.left = `${obj.x}px`;
    element.style.top = `${obj.y}px`;
    element.style.width = `${obj.width}px`;
    element.style.height = `${obj.height}px`;
    element.style.overflow = "hidden";

    if (obj.iconClass) {
        const icon = document.createElement("i");
        icon.className = `fa ${obj.iconClass}`;
        element.appendChild(icon);
    } else if (obj.html) {
        element.innerHTML = obj.html;
    } else {
        element.style.backgroundColor = 'red';
    }

    container.appendChild(element);
    console.log(`✅ Clickable element created: ${id}`);
}

// ✅ Function to remove an element from the overlay
function removeClickableElement(id) {
    const element = document.getElementById(id);
    if (element) {
        element.remove();
        console.log(`🗑️ Removed clickable element: ${id}`);
    }
}

// ✅ Load initial objects when overlay loads
window.onload = loadClickableObjects;
