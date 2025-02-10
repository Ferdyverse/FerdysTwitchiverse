// stars.js
export function triggerStarExplosion(x, y) {
  const overlayElement = document.getElementById("overlay");
  const bigStar = document.createElement("i");
  bigStar.className = "fa fa-poo big-star";
  bigStar.style.position = "absolute";
  bigStar.style.left = `${x - 25}px`;
  bigStar.style.top = `${y - 25}px`;
  bigStar.style.fontSize = "50px";
  bigStar.style.color = "#7e5210ec";
  bigStar.style.opacity = "1";
  bigStar.style.transformOrigin = "center";
  overlayElement.appendChild(bigStar);

  setTimeout(() => {
    bigStar.style.transform = "scale(1.5) rotate(360deg)";
  }, 50);
  setTimeout(() => {
    bigStar.style.opacity = "0";
    bigStar.style.transform = "scale(0.5) rotate(720deg)";
  }, 800);
  setTimeout(() => {
    bigStar.remove();
  }, 1200);
  setTimeout(() => {
    const numParticles = 30;
    for (let i = 0; i < numParticles; i++) {
      createMiniStar(x, y);
    }
  }, 200);
}

export function createMiniStar(x, y) {
  const overlayElement = document.getElementById("overlay");
  const star = document.createElement("i");
  star.className = "fa fa-poo mini-star";
  star.style.position = "absolute";
  star.style.left = `${x}px`;
  star.style.top = `${y}px`;
  star.style.fontSize = "40px";
  star.style.color = getRandomColor();
  star.style.opacity = "1";
  overlayElement.appendChild(star);

  const angle = Math.random() * 2 * Math.PI;
  const distance = Math.random() * 180 + 80;
  const newX = x + Math.cos(angle) * distance;
  const newY = y + Math.sin(angle) * distance;

  setTimeout(() => {
    star.style.transform = `translate(${newX - x}px, ${newY - y}px) scale(1.5) rotate(${Math.random() * 360}deg)`;
  }, 100);

  setTimeout(() => {
    const fallDistance = Math.random() * 200 + 100;
    star.style.transition = "transform 1s linear, opacity 1s ease-out";
    star.style.transform = `translate(${newX - x}px, ${newY - y + fallDistance}px) scale(0.8) rotate(${Math.random() * 180}deg)`;
    star.style.opacity = "0";
  }, 600);

  setTimeout(() => {
    star.remove();
  }, 1600);
}

export function getRandomColor() {
  const colors = ["#FFD700", "#FFA500", "#FF4500", "#FFFF00", "#FF69B4"];
  return colors[Math.floor(Math.random() * colors.length)];
}
