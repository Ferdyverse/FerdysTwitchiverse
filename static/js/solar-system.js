// A more cartoonish version of the solar system with vibrant colors and a playful design

import * as THREE from "/static/js/three/three.module.js";
import { OrbitControls } from "/static/js/three/OrbitControls.js";
import { CSS2DRenderer, CSS2DObject } from "/static/js/three/CSS2DRenderer.js";

// Create the renderer
const renderer = new THREE.WebGLRenderer({ antialias: true });
renderer.setSize(1920, 1080); // Full HD resolution
renderer.setClearColor(0xa0d2eb); // Cartoonish sky blue background
document.body.appendChild(renderer.domElement);

// Create the CSS2DRenderer for labels
const labelRenderer = new CSS2DRenderer();
labelRenderer.setSize(1920, 1080);
labelRenderer.domElement.style.position = "absolute";
labelRenderer.domElement.style.top = "0";
labelRenderer.domElement.style.pointerEvents = "none";
document.body.appendChild(labelRenderer.domElement);

// Scene + Camera
const scene = new THREE.Scene();
const camera = new THREE.PerspectiveCamera(60, 1920 / 1080, 0.1, 2000);
camera.position.set(0, 300, 600);
camera.lookAt(0, 0, 0);
scene.add(camera);

// Orbit Controls
const controls = new OrbitControls(camera, renderer.domElement);
controls.enableDamping = true;
controls.dampingFactor = 0.05;
controls.minDistance = 100;
controls.maxDistance = 1000;
controls.maxPolarAngle = Math.PI / 2;

// Lights
const sunLight = new THREE.PointLight(0xffcc00, 2, 1000);
sunLight.position.set(0, 0, 0);
scene.add(sunLight);

const ambientLight = new THREE.AmbientLight(0xffffff, 1.5);
scene.add(ambientLight);

// Generate a cartoonish sun texture
function generateCartoonSunTexture() {
  const canvas = document.createElement("canvas");
  canvas.width = 512;
  canvas.height = 512;
  const ctx = canvas.getContext("2d");

  // Create a radial gradient for the sun's base
  const gradient = ctx.createRadialGradient(256, 256, 50, 256, 256, 256);
  gradient.addColorStop(0, "hsl(50, 100%, 80%)");
  gradient.addColorStop(0.6, "hsl(40, 100%, 60%)");
  gradient.addColorStop(1, "hsl(30, 100%, 40%)");
  ctx.fillStyle = gradient;
  ctx.fillRect(0, 0, 512, 512);

  // Add swirling patterns
  for (let i = 0; i < 8; i++) {
    ctx.beginPath();
    ctx.arc(
      Math.random() * 512,
      Math.random() * 512,
      Math.random() * 50 + 20,
      0,
      Math.PI * 2
    );
    ctx.fillStyle = `hsl(${Math.random() * 20 + 30}, 100%, ${Math.random() * 40 + 40}%)`;
    ctx.fill();
  }

  // Add radiating lines for a cartoonish effect
  for (let i = 0; i < 12; i++) {
    ctx.beginPath();
    ctx.moveTo(256, 256);
    const angle = (Math.PI * 2 * i) / 12;
    const x = 256 + Math.cos(angle) * 300;
    const y = 256 + Math.sin(angle) * 300;
    ctx.lineTo(x, y);
    ctx.lineWidth = Math.random() * 10 + 5;
    ctx.strokeStyle = `hsl(50, 100%, ${Math.random() * 30 + 50}%)`;
    ctx.stroke();
  }

  return new THREE.CanvasTexture(canvas);
}

// Sun
const sunGeometry = new THREE.SphereGeometry(50, 32, 32);
const sunMaterial = new THREE.MeshStandardMaterial({
  map: generateCartoonSunTexture(),
  emissive: 0xffcc00,
  emissiveIntensity: 2,
  roughness: 0.3,
  metalness: 0.5,
});
const sun = new THREE.Mesh(sunGeometry, sunMaterial);
scene.add(sun);

// Add a glowing halo around the sun
const sunHaloGeometry = new THREE.SphereGeometry(60, 32, 32);
const sunHaloMaterial = new THREE.MeshBasicMaterial({
  color: 0xffcc00,
  transparent: true,
  opacity: 0.5,
  blending: THREE.AdditiveBlending,
});
const sunHalo = new THREE.Mesh(sunHaloGeometry, sunHaloMaterial);
scene.add(sunHalo);

/* ------------------ CARTOONISH PLANET TEXTURES ------------------ */
function generateCartoonPlanetTexture() {
  const canvas = document.createElement("canvas");
  canvas.width = 256;
  canvas.height = 256;
  const ctx = canvas.getContext("2d");

  // Gradient background to simulate planet surface
  const gradient = ctx.createRadialGradient(128, 128, 30, 128, 128, 128);
  gradient.addColorStop(0, `hsl(${Math.random() * 360}, 100%, 50%)`);
  gradient.addColorStop(1, `hsl(${Math.random() * 360}, 80%, 30%)`);
  ctx.fillStyle = gradient;
  ctx.fillRect(0, 0, 256, 256);

  // Add craters to the surface
  for (let i = 0; i < 6; i++) {
    ctx.beginPath();
    const x = Math.random() * 256;
    const y = Math.random() * 256;
    const radius = Math.random() * 30 + 10;
    ctx.arc(x, y, radius, 0, Math.PI * 2);
    ctx.fillStyle = `hsl(${Math.random() * 360}, 40%, 20%)`;
    ctx.fill();

    // Inner shadow for depth
    ctx.beginPath();
    ctx.arc(x, y, radius * 0.6, 0, Math.PI * 2);
    ctx.fillStyle = `hsl(${Math.random() * 360}, 30%, 10%)`;
    ctx.fill();
  }

  // Add stripes for a cartoony effect
  for (let i = 0; i < 4; i++) {
    ctx.beginPath();
    ctx.moveTo(0, Math.random() * 256);
    ctx.lineTo(256, Math.random() * 256);
    ctx.lineWidth = Math.random() * 10 + 5;
    ctx.strokeStyle = `hsl(${Math.random() * 360}, 90%, 70%)`;
    ctx.stroke();
  }

  return new THREE.CanvasTexture(canvas);
}

/* ------------------ FETCH & CREATE PLANETS ------------------ */
async function fetchPlanets() {
  try {
    const response = await fetch("/planets");
    const planetsData = await response.json();
    createPlanets(planetsData);
  } catch (error) {
    console.error("Failed to fetch planets:", error);
  }
}

function createPlanets(planetsData) {
  const planetObjects = [];
  const scaleFactor = 0.8;

  planetsData.forEach((data) => {
    const planetTexture = generateCartoonPlanetTexture();

    const planetSize = Math.sqrt(data.raid_size) * 3;
    const planetGeometry = new THREE.SphereGeometry(planetSize, 32, 32);
    const planetMaterial = new THREE.MeshStandardMaterial({
      map: planetTexture,
      roughness: 0.4,
      metalness: 0.3,
    });
    const planet = new THREE.Mesh(planetGeometry, planetMaterial);

    // Label
    const labelDiv = document.createElement("div");
    labelDiv.className = "planet-label";
    labelDiv.textContent = data.raider_name;
    labelDiv.style.color = "black";
    labelDiv.style.textShadow = "0 0 5px white";

    const label = new CSS2DObject(labelDiv);
    label.position.set(0, planetSize + 2, 0);
    planet.add(label);

    // Scale distance
    const adjustedDistance = data.distance * scaleFactor;

    const tiltX = Math.random() * 0.8 - 0.4;
    const tiltZ = Math.random() * 0.8 - 0.4;

    // Create a group for tilt
    const group = new THREE.Group();
    group.rotation.x = tiltX;
    group.rotation.z = tiltZ;
    scene.add(group);

    // Place planet in XY-plane
    const angle = data.angle;
    const x = Math.cos(angle) * adjustedDistance;
    const z = Math.sin(angle) * adjustedDistance;
    planet.position.set(x, 0, z);

    group.add(planet);

    // Save planet data for animation
    planetObjects.push({
      mesh: planet,
      group,
      angle,
      distance: adjustedDistance,
      tiltX,
      tiltZ,
      speed: 0.0005 + Math.random() * 0.0015,
    });
  });

  animatePlanets(planetObjects);
}

function animatePlanets(planetObjects) {
  function animate() {
    requestAnimationFrame(animate);

    planetObjects.forEach((obj) => {
      obj.angle += obj.speed;
      const x = Math.cos(obj.angle) * obj.distance;
      const z = Math.sin(obj.angle) * obj.distance;
      obj.mesh.position.set(x, 0, z);
    });

    controls.update();

    renderer.render(scene, camera);
    labelRenderer.render(scene, camera);
  }

  animate();
}

// Fetch planets and start the system
fetchPlanets();
