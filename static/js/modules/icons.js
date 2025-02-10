// icons.js
export function addIcon(iconID, iconClass) {
    const iconContainer = document.getElementById('dynamic-icons');
    const newIcon = document.createElement('i');
    newIcon.id = `${iconID}`;
    newIcon.className = `fa ${iconClass}`;
    iconContainer.appendChild(newIcon);
}

export function removeIcon(iconID) {
    const iconContainer = document.getElementById('dynamic-icons');
    const icons = iconContainer.querySelectorAll(`i[id="${iconID}"]`);
    icons.forEach((icon) => iconContainer.removeChild(icon));
}
