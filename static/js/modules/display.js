// display.js
export function showHTML(html, lifetime) {
  const overlayElement = document.getElementById("overlay");
  const htmlElement = document.createElement("div");
  htmlElement.className = "raw";
  htmlElement.style.opacity = "0";
  htmlElement.style.transition = "opacity 0.5s ease-in-out";
  htmlElement.innerHTML = html;
  overlayElement.appendChild(htmlElement);
  setTimeout(() => {
    htmlElement.style.opacity = "1";
  }, 50);
  if (lifetime > 0) {
    setTimeout(() => {
      htmlElement.style.opacity = "0";
      setTimeout(() => {
        htmlElement.remove();
      }, 500);
    }, lifetime);
  }
}

export function showURL(baseUrl, params, duration) {
  const url = new URL(baseUrl, window.location.origin);
  Object.keys(params).forEach((key) =>
    url.searchParams.append(key, params[key])
  );

  const container = document.createElement("div");
  container.style.position = "fixed";
  container.style.top = "0";
  container.style.left = "0";
  container.style.width = "100vw";
  container.style.height = "100vh";
  container.style.backgroundColor = "black";
  container.style.zIndex = "9999";
  container.style.overflow = "hidden";
  container.style.display = "flex";
  container.style.alignItems = "center";
  container.style.justifyContent = "center";
  container.style.color = "white";
  container.style.opacity = "0";
  container.style.transition = "opacity 2s ease-in-out";
  container.innerHTML = "<p>Loading...</p>";

  document.body.appendChild(container);
  setTimeout(() => {
    container.style.opacity = "1";
  }, 10);

  fetch(url)
    .then((response) => response.text())
    .then((html) => {
      Object.entries(params).forEach(([key, value]) => {
        const regex = new RegExp(`\\[${key.toUpperCase()}\\]`, "g");
        html = html.replace(regex, value);
      });
      container.innerHTML = html;
      container.querySelectorAll("script").forEach((script) => {
        const newScript = document.createElement("script");
        newScript.textContent = script.textContent;
        document.body.appendChild(newScript);
        document.body.removeChild(newScript);
      });
    })
    .catch((error) => {
      console.error("Error loading content:", error);
      container.innerHTML = "<p>Error loading content.</p>";
    });

  setTimeout(() => {
    container.style.opacity = "0";
    setTimeout(() => {
      container.remove();
    }, 1000);
  }, duration - 1000);
}

export function createTodo(id, text, user) {
  const todo = document.createElement("div");
  todo.classList.add("todo");
  if (id == "todo-1") {
    id = "todo-" + Math.floor(Math.random() * 20);
  }
  todo.id = id;
  todo.innerHTML = `<h1>Erledige mich!</h1><p>${text}</p><span class="todo-user">${user}</span><span class="todo-id">#${id}</span>`;

  let screenWidth = 1080;

  const container = document.getElementById("todoContainer");
  container.appendChild(todo);

  // Show animation (pop-in effect)
  gsap.to(todo, {
    opacity: 1,
    scale: 1,
    rotate: 0,
    duration: 0.8,
    ease: "back.out(1.7)",
  });

  // Wobble effect after appearing
  gsap.fromTo(
    todo,
    { y: -20, rotate: -5 },
    { y: 0, rotate: 0, duration: 1.2, ease: "elastic.out(1, 0.5)" }
  );

  // Wait 3 seconds, then move left but leave ~20px visible
  gsap.delayedCall(3, () => {
    let currentX = gsap.getProperty(todo, "x"); // Get current position
    let randomOffsetY = Math.random() * 40; // More varied Y offset
    let randomRotation = Math.random() * 25; // More rotation for a natural look
    let targetX = -screenWidth + Math.random() * 5; // Ensures ~20px stays visible

    gsap.to(todo, {
      x: targetX, // Moves to the left but leaves part visible
      y: randomOffsetY, // Stacks dynamically
      rotate: randomRotation,
      duration: 1.5,
      ease: "power3.out",
    });
  });
}

export function showTodo(id) {
  const todo = document.getElementById(id);
  if (!todo) return; // If the ID is not found, do nothing

  gsap.to(todo, {
    x: "0%",
    y: "0%",
    rotate: 0, // Resets rotation
    duration: 1.2,
    ease: "power3.out",
  });
}

export function removeTodo(id) {
  const todo = document.getElementById(id);
  if (!todo) return; // If the ID is not found, do nothing

  gsap.to(todo, {
    scale: 0,
    rotation: 720, // Spins before disappearing
    opacity: 0,
    duration: 1,
    ease: "power4.in",
    onComplete: () => {
      todo.remove(); // Removes the element from the DOM
    },
  });
}
