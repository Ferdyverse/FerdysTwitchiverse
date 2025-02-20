// sortable.js

function initSortable() {
  const btnContainer = document.getElementById("button-container");

  if (!btnContainer) {
    console.error("❌ #button-container not found!");
    return;
  }

  new Sortable(btnContainer, {
    animation: 150,
    ghostClass: "dragging",
    chosenClass: "chosen",
    dragClass: "drag",
    handle: ".drag-handle",
    filter: ".no-drag",
    onEnd: function (evt) {
      const buttons = [...btnContainer.querySelectorAll(".draggable")];

      const orderedButtons = buttons.map((button, index) => ({
        id: button.getAttribute("data-id"),
        position: index,
      }));

      fetch("/admin/buttons/reorder", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(orderedButtons),
      }).then((response) => {
        if (response.ok) {
          console.log("✅ Button order saved!");
        } else {
          console.error("❌ Failed to save button order");
        }
      });
    },
  });

  console.log("✅ Sortable initialized successfully!");
}

export { initSortable };
