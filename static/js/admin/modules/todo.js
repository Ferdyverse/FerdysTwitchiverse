// 📋 Load ToDos with status filter
function loadTodos(status = null) {
  const url = status ? `/todo/todos?status=${status}` : "/todo/todos";

  htmx.ajax("GET", url, {
    target: "#todo-list",
    swap: "innerHTML",
  });
}
