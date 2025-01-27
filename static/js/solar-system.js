// A final updated version that removes the orbit path lines
// while preserving random tilts, planet textures, and a fully independent star flicker.

import * as THREE from "/static/js/three/three.module.js";
import { OrbitControls } from "/static/js/three/OrbitControls.js";
import { CSS2DRenderer, CSS2DObject } from "/static/js/three/CSS2DRenderer.js";

const planetObjects = [];

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
const sunlight = new THREE.DirectionalLight(0xffcc88, 1.5); // Warm yellow light
sunlight.position.set(100, 100, 100);
scene.add(sunlight);

const ambientLight = new THREE.AmbientLight(0xffffff, 0.5);
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
  const starCount = 1000; // Number of stars
  const positions = new Float32Array(starCount * 3); // Position array
  const opacities = new Float32Array(starCount); // Opacity array
  const freqs = new Float32Array(starCount); // Frequencies for twinkling
  const phases = new Float32Array(starCount); // Random phase offsets

  // Initialize positions, opacities, frequencies, and phases
  for (let i = 0; i < starCount; i++) {
    positions[i * 3] = (Math.random() - 0.5) * 1500; // x
    positions[i * 3 + 1] = (Math.random() - 0.5) * 1500; // y
    positions[i * 3 + 2] = (Math.random() - 0.5) * 1500; // z
    opacities[i] = Math.random(); // Initial random opacity
    freqs[i] = 0.5 + Math.random() * 2.0; // Random twinkling frequency
    phases[i] = Math.random() * Math.PI * 2; // Random phase offset
  }

  const starGeometry = new THREE.BufferGeometry();
  starGeometry.setAttribute("position", new THREE.Float32BufferAttribute(positions, 3));
  starGeometry.setAttribute("opacity", new THREE.Float32BufferAttribute(opacities, 1));

  const starMaterial = new THREE.PointsMaterial({
    size: 4, // Star size
    color: 0xffffff, // White stars
    transparent: true, // Enable transparency
    blending: THREE.AdditiveBlending, // Additive blending for glowing effect
    depthWrite: false, // Prevent stars from being occluded by other objects
    map: new THREE.TextureLoader().load("/static/images/circle.png"), // Texture for stars
  });

  // Modify shaders to include the opacity attribute
  starMaterial.onBeforeCompile = (shader) => {
    shader.vertexShader = `
      attribute float opacity;
      varying float vOpacity;
      ${shader.vertexShader.replace(
        "void main() {",
        "void main() { vOpacity = opacity;"
      )}
    `;
    shader.fragmentShader = `
      varying float vOpacity;
      ${shader.fragmentShader.replace(
        "vec4 diffuseColor = vec4( diffuse, opacity );",
        "vec4 diffuseColor = vec4( diffuse, vOpacity );"
      )}
    `;
  };

  const stars = new THREE.Points(starGeometry, starMaterial);
  scene.add(stars);

  let startTime = performance.now();

  // Twinkle function to update opacity
  function twinkleStars() {
    const elapsed = (performance.now() - startTime) * 0.001; // Time in seconds
    const opacitiesArray = starGeometry.attributes.opacity.array;

    for (let i = 0; i < starCount; i++) {
      const sinVal = Math.sin(freqs[i] * elapsed + phases[i]) * 0.5 + 0.5; // Smooth sine wave
      opacitiesArray[i] = sinVal; // Update opacity dynamically
    }

    // Ensure the attribute is marked for an update
    starGeometry.attributes.opacity.needsUpdate = true;
  }

  return twinkleStars;
}

/* ------------------ PLANET TEXTURE GENERATION ------------------ */
function generateRandomPlanetTexture() {
  const canvas = document.createElement("canvas");
  canvas.width = 512;
  canvas.height = 512;
  const ctx = canvas.getContext("2d");

  // Create a darker radial gradient for the base color
  const gradient = ctx.createRadialGradient(256, 256, 50, 256, 256, 256);
  const color1 = `hsl(${Math.random() * 360}, 50%, 20%)`; // Dark base color
  const color2 = `hsl(${Math.random() * 360}, 40%, 10%)`; // Even darker edge color

  gradient.addColorStop(0, color1);
  gradient.addColorStop(1, color2);
  ctx.fillStyle = gradient;
  ctx.fillRect(0, 0, 512, 512);

  // Add random noise for surface details
  const imageData = ctx.getImageData(0, 0, canvas.width, canvas.height);
  for (let i = 0; i < imageData.data.length; i += 4) {
    const random = Math.random() * 50; // Subtle noise for darker textures
    imageData.data[i] = (imageData.data[i] + random) / 2; // Red
    imageData.data[i + 1] = (imageData.data[i + 1] + random) / 2; // Green
    imageData.data[i + 2] = (imageData.data[i + 2] + random) / 2; // Blue
  }
  ctx.putImageData(imageData, 0, 0);

  // Add craters or surface patterns
  for (let i = 0; i < 10; i++) {
    const x = Math.random() * 512;
    const y = Math.random() * 512;
    const radius = Math.random() * 50 + 10;

    ctx.beginPath();
    ctx.arc(x, y, radius, 0, Math.PI * 2);
    ctx.fillStyle = `rgba(0, 0, 0, ${Math.random() * 0.5})`; // Darker craters
    ctx.fill();

    ctx.strokeStyle = `rgba(255, 255, 255, ${Math.random() * 0.2})`; // Subtle highlights
    ctx.lineWidth = 1.5;
    ctx.stroke();
  }

  return new THREE.CanvasTexture(canvas); // Return as a texture for Three.js
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
  const scaleFactor = 0.5;

  planetsData.forEach((data) => {
    const planetTexture = generateRandomPlanetTexture();

    const planetSize = Math.sqrt(data.raid_size) * 1.5;

    const planetGeometry = new THREE.SphereGeometry(planetSize, 64, 64);
    const planetMaterial = new THREE.MeshStandardMaterial({
      map: planetTexture, // Use generated texture
      bumpMap: planetTexture, // Use the same texture for bump mapping
      bumpScale: 0.2, // Adjust bump intensity
      metalness: 0.2,
      roughness: 1.0,
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
      speed: 0.001 + Math.random() * 0.002, // Random orbital speed
    });
  });
}

function animatePlanets() {
  planetObjects.forEach((obj) => {
    // Update planet position based on orbital angle
    obj.angle += obj.speed; // Increment angle by speed
    const x = Math.cos(obj.angle) * obj.distance;
    const z = Math.sin(obj.angle) * obj.distance;
    obj.mesh.position.set(x, 0, z);

    // Rotate the planet on its axis
    obj.mesh.rotation.y += 0.002; // Adjust rotational speed as needed
  });
}
// Animation loop
function animate() {
  requestAnimationFrame(animate);

  // Animate planets
  animatePlanets();

  // Twinkle stars
  twinkleStars();

  // Update controls
  controls.update();

  // Render the scene and labels
  renderer.render(scene, camera);
  labelRenderer.render(scene, camera);
}

// Initialize stars and planets
const twinkleStars = createStars(); // Create stars and get the twinkle function
fetchPlanets(); // Fetch and create planets

// Start the animation
animate();
