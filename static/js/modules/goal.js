// goal.js
export function updateGoal(text, current, goal) {
    const goalBox = document.getElementById('goal-box');
    const progressBar = document.getElementById('goal-bar');
    const goalText = goalBox.querySelector('span');

    console.info(`Update Goal | current: ${current}, goal: ${goal}`)

    if (current !== null && goal != 0) {
        const percentage = Math.min((current / goal) * 100, 100);
        progressBar.style.width = percentage + '%';
        goalText.textContent = `${text} ${current} / ${goal}`;
        goalBox.classList.remove('hidden');
    } else {
        goalBox.classList.add('hidden');
    }
}
