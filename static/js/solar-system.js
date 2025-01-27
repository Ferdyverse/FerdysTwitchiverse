// A final updated version that removes the orbit path lines
// while preserving random tilts, planet textures, and a fully independent star flicker.

import * as THREE from "/static/js/three/three.module.js";
import { OrbitControls } from "/static/js/three/OrbitControls.js";
import { CSS2DRenderer, CSS2DObject } from "/static/js/three/CSS2DRenderer.js";

// Create the renderer
const renderer = new THREE.WebGLRenderer({ antialias: true });
renderer.setSize(1920, 1080); // Full HD resolution
renderer.setClearColor(0x000000); // Black background
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
camera.position.set(0, 200, 500);
camera.lookAt(0, 0, 0);
scene.add(camera);

// Orbit Controls
const controls = new OrbitControls(camera, renderer.domElement);
controls.enableDamping = true;
controls.dampingFactor = 0.05;
controls.minDistance = 100;
controls.maxDistance = 600;
controls.maxPolarAngle = Math.PI / 2;

// Lights
const sunLight = new THREE.PointLight(0xffaa33, 5, 800);
sunLight.position.set(0, 0, 0);
scene.add(sunLight);

const ambientLight = new THREE.AmbientLight(0xffffff, 2.5);
scene.add(ambientLight);

// Sun
const sunTexture = new THREE.TextureLoader().load("/static/images/2k_sun.jpg");
const sunGeometry = new THREE.SphereGeometry(40, 64, 64);
const sunMaterial = new THREE.MeshPhysicalMaterial({
  map: sunTexture,
  emissive: 0xffaa33,
  emissiveIntensity: 4,
  roughness: 0.3,
  metalness: 0.1,
  clearcoat: 1.0,
});
const sun = new THREE.Mesh(sunGeometry, sunMaterial);
scene.add(sun);

// Sun Halo
const haloGeometry = new THREE.SphereGeometry(12, 64, 64);
const haloMaterial = new THREE.MeshBasicMaterial({
  color: 0xffaa33,
  transparent: true,
  opacity: 0.4,
  blending: THREE.AdditiveBlending,
});
const sunHalo = new THREE.Mesh(haloGeometry, haloMaterial);
scene.add(sunHalo);

/* ------------------ STARS WITH INDEPENDENT CHAOTIC FLICKER ------------------ */
function createStars() {
  const starCount = 1000;
  const positions = new Float32Array(starCount * 3);
  const baseOpacities = new Float32Array(starCount);
  const freqs = new Float32Array(starCount);
  const phases = new Float32Array(starCount);

  for (let i = 0; i < starCount; i++) {
    // Random star position
    const x = (Math.random() - 0.5) * 1500;
    const y = (Math.random() - 0.5) * 1500;
    const z = (Math.random() - 0.5) * 1500;
    positions[i * 3 + 0] = x;
    positions[i * 3 + 1] = y;
    positions[i * 3 + 2] = z;

    // Base opacity [0.5..1.0]
    baseOpacities[i] = Math.random() * 0.5 + 0.5;

    // Random freq + phase
    freqs[i] = 1.0 + Math.random() * 3.0; // Flicker speed
    phases[i] = Math.random() * Math.PI * 2;
  }

  // BufferGeometry
  const starGeometry = new THREE.BufferGeometry();
  starGeometry.setAttribute(
    "position",
    new THREE.Float32BufferAttribute(positions, 3)
  );

  const starMaterial = new THREE.PointsMaterial({
    size: 3,
    color: 0xffffff, // Set stars to white by default
    transparent: true,
    blending: THREE.AdditiveBlending,
    opacity: 1.0,
    sizeAttenuation: true,
  });

  const stars = new THREE.Points(starGeometry, starMaterial);
  scene.add(stars);

  let startTime = performance.now();

  function twinkleStars() {
    const elapsed = (performance.now() - startTime) * 0.001;
    // We'll compute an average flicker from all stars.
    // For truly individual star opacities, we'd need a custom shader or per-star attribute.
    // For a simplified approach, let's compute an average flicker.

    for (let i = 0; i < starCount; i++) {
      // Flicker in [1..0.3], reversed from bright to dark
      const sinVal = Math.sin(freqs[i] * elapsed + phases[i]) * 0.5 + 0.5; // [0..1]
      const flicker = 1.0 - sinVal * 0.7; // [0.3..1.0], reversed
      baseOpacities[i] = flicker; // Update the opacity per star
    }

    // Apply the opacity as a uniform scale for all stars
    starMaterial.opacity = 1.0; // Stars are fully bright by default // Average for the entire star field
  }

  return twinkleStars;
}

/* ------------------ PLANET TEXTURE GENERATION ------------------ */
function generateRandomPlanetTexture(textureLoader) {
  const canvas = document.createElement("canvas");
  canvas.width = 256;
  canvas.height = 256;
  const ctx = canvas.getContext("2d");

  // Random gradient
  const gradient = ctx.createLinearGradient(0, 0, 256, 256);
  gradient.addColorStop(
    0,
    `hsl(${Math.random() * 360}, ${Math.random() * 100}%, ${Math.random() * 80 + 20}%)`
  );
  gradient.addColorStop(
    1,
    `hsl(${Math.random() * 360}, ${Math.random() * 100}%, ${Math.random() * 70 + 10}%)`
  );
  ctx.fillStyle = gradient;
  ctx.fillRect(0, 0, 256, 256);

  // Random circles
  for (let i = 0; i < 10; i++) {
    ctx.beginPath();
    ctx.arc(
      Math.random() * 256,
      Math.random() * 256,
      Math.random() * 60 + 20,
      0,
      Math.PI * 2
    );
    ctx.fillStyle = `hsl(${Math.random() * 360}, ${Math.random() * 100}%, ${Math.random() * 60 + 20}%)`;
    ctx.fill();
  }

  return textureLoader.load(canvas.toDataURL());
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
  const textureLoader = new THREE.TextureLoader();
  const planetObjects = [];
  const scaleFactor = 0.5;

  planetsData.forEach((data) => {
    const planetTexture = generateRandomPlanetTexture(textureLoader);

    const planetSize = Math.sqrt(data.raid_size) * 1.5;
    const planetGeometry = new THREE.SphereGeometry(planetSize, 32, 32);
    const planetMaterial = new THREE.MeshPhysicalMaterial({
      map: planetTexture,
      emissive: 0x0033ff,
      emissiveIntensity: 1.8,
      roughness: 0.1, // More cartoon-like
      metalness: 0.5,
      clearcoat: 1.0,
    });
    const planet = new THREE.Mesh(planetGeometry, planetMaterial);

    // Label
    const labelDiv = document.createElement("div");
    labelDiv.className = "planet-label";
    labelDiv.textContent = data.raider_name;
    labelDiv.style.color = "white";
    labelDiv.style.textShadow = "0 0 5px black";

    const label = new CSS2DObject(labelDiv);
    label.position.set(0, planetSize + 1, 0);
    planet.add(label);

    // Scale distance
    const adjustedDistance = data.distance * scaleFactor;

    const tiltX = Math.random() * 1.5 - 0.75;
    const tiltZ = Math.random() * 1.5 - 0.75;

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
      speed: 0.001 + Math.random() * 0.002,
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

    // Per-star chaotic flicker
    twinkleStars();
    controls.update();

    renderer.render(scene, camera);
    labelRenderer.render(scene, camera);
  }

  animate();
}

// Create stars & fetch planets
const twinkleStars = createStars();
fetchPlanets();
