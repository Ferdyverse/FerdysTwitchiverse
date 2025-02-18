// main.js
import { updateTopBar } from "./modules/topbar.js";
import { updateGoal } from "./modules/goal.js";
import { addIcon, removeIcon } from "./modules/icons.js";
import { showAlertWithGSAP, showSubBanner } from "./modules/alerts.js";
import {
  showHTML,
  showURL,
  createTodo,
  showTodo,
  removeTodo,
} from "./modules/display.js";
import { triggerStarExplosion } from "./modules/stars.js";
import { updateChat } from "./modules/chat.js";
import {
  createClickableElement,
  removeClickableElement,
} from "./modules/clickables.js";

// Example: Fetch initial data for the top bar and goal
fetch("/overlay-data")
  .then((response) => response.json())
  .then((data) => {
    updateTopBar("follower", data.last_follower || "None");
    updateTopBar("subscriber", data.last_subscriber || "None");
    if (data.goal_text !== "None" && data.goal_target !== 0) {
      updateGoal(data.goal_text, data.goal_current, data.goal_target);
    } else {
      updateGoal(null, null, null);
    }
  })
  .catch((error) => {
    console.error("Failed to fetch overlay data:", error);
    updateTopBar("message", "Failed to fetch initial data");
  });

async function fetchTodos() {
  const response = await fetch("/todo/");
  const todos = await response.json();

  const todoContainer = document.getElementById("todoContainer");
  todoContainer.innerHTML = "";

  todos.forEach((todo) => {
    createTodo(todo.id, todo.text, todo.username);
  });
}

document.addEventListener("click", () => {
  fetchTodos();
  createTodo("todo-1", "Baue eine tolle ToDo Animation!", "Ferdyverse");
});
