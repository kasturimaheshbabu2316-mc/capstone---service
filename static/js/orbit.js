/**
 * 3D Holographic Orbit Singleton Controller (Three.js)
 * Persistent UI epicenter for Ola Support Intelligence Operations Desk.
 * Enhanced with PBR materials, post-processing, physics-based particles, and realistic lighting.
 */

export const Orbit = (() => {
  let instance = null;
  let container = null;
  let canvas = null;
  let renderer = null;
  let scene = null;
  let camera = null;
  let mainGroup = null;

  // Post-processing
  let composer = null;
  let renderPass = null;
  let bloomPass = null;

  // Lights
  let lightCyan, lightMagenta, lightPurple, lightGold, ambientLight;
  let hemiLight, dirLight;

  // Meshes & Materials
  let coreMesh, coreMat;
  let glassMesh, glassMat;
  let glassShellMesh, glassShellMat;
  let wireMesh1, wireMat1;
  let wireMesh2, wireMat2;
  let ring1, ring2, ring3, ring4;
  let ring1Mat, ring2Mat, ring3Mat, ring4Mat;
  let node1, node2, node3, node4;
  let nodeMats = [];
  const R1 = 1.42;
  const R2 = 1.62;
  const R3 = 1.84;
  const R4 = 2.04;
  let particles, particleMaterial;
  let particlePositions, particleVelocities, particleLifetimes, particleSizes, particleColors;
  const particleCount = 500;

  // Particle colors - initialized lazily after THREE is available
  let pColors = null;

  function ensurePColors() {
    if (!pColors && typeof THREE !== "undefined") {
      pColors = [
        0x00f2fe), // cyan
        0xf43f5e), // rose
        0xa855f7), // purple
        0xfbbf24), // gold
        0x34d399), // emerald
        0xffffff)  // white
      ];
    }
    return pColors;
  }

  // Energy field effect
  let energyFieldMesh, energyFieldMat;
  let energyFieldGeom;

  // Animation & Timing
  let clock = null;
  let animId = null;
  let accumulatedTime = 0;
  let isRunning = false;
  let isContextLost = false;

  // Interaction & Modes
  let isHovered = false;
  let hoverTransition = 0;
  let clickImpulse = 0;
  let speedMultiplier = 1.0;
  let targetSpeed = 1.0;
  let currentMode = "idle"; // "idle" | "thinking" | "alert" | "docked"
  let alertTimer = null;
  let isDockedState = false;

  // Raycasting & Pointer tracking
  let raycaster = null;
  let mouse = null;
  let targetMouseX = 0;
  let targetMouseY = 0;
  let currentMouseX = 0;
  let currentMouseY = 0;

  // Observers
  let resizeObserver = null;
  let transitionTimer = null;

  // Performance monitoring
  let frameCount = 0;
  let lastFpsUpdate = 0;
  let currentFps = 60;

  function init(containerEl) {
    if (window.__ORBIT__) {
      return window.__ORBIT__;
    }
    if (!containerEl) {
      containerEl = document.getElementById("threejs-container-ANIMATION_34");
    }
    if (!containerEl) {
      console.warn("[Orbit] Mounting container not found.");
      return null;
    }
    if (typeof THREE === "undefined") {
      console.error("[Orbit] THREE library is not loaded.");
      return null;
    }

    container = containerEl;
    clock = new THREE.Clock();

    const rect = container.getBoundingClientRect();
    const initialW = rect.width > 0 ? rect.width : 270;
    const initialH = rect.height > 0 ? rect.height : 270;

    scene = new THREE.Scene();
    camera = new THREE.PerspectiveCamera(45, initialW / initialH, 0.1, 1000);
    camera.position.z = 5.6;

    try {
      renderer = new THREE.WebGLRenderer({
        alpha: true,
        antialias: true,
        preserveDrawingBuffer: true,
        powerPreference: "high-performance",
        logarithmicDepthBuffer: true
      });
    } catch (err) {
      console.error("[Orbit] WebGLRenderer creation failure:", err);
      return null;
    }

    renderer.setSize(initialW, initialH, false);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
    if (THREE.ACESFilmicToneMapping) {
      renderer.toneMapping = THREE.ACESFilmicToneMapping;
      renderer.toneMappingExposure = 1.2;
    }
    renderer.outputColorSpace = THREE.SRGBColorSpace;
    renderer.physicallyCorrectLights = true;

    canvas = renderer.domElement;
    canvas.style.display = "block";
    canvas.style.width = "100%";
    canvas.style.height = "100%";
    canvas.style.position = "absolute";
    canvas.style.top = "0";
    canvas.style.left = "0";

    container.innerHTML = "";
    container.appendChild(canvas);

    // Setup Scene Graph
    mainGroup = new THREE.Group();
    mainGroup.scale.set(1.0, 1.0, 1.0);
    scene.add(mainGroup);

    // Initialize post-processing
    initPostProcessing();

    // Build the holographic core
    buildHolographicCore();

    // Pointer Raycasting Setup
    raycaster = new THREE.Raycaster();
    mouse = new THREE.Vector2(-999, -999);
    container.style.cursor = "pointer";

    const onPointerMove = (event) => {
      if (isDockedState) return;
      const r = container.getBoundingClientRect();
      if (r.width <= 0 || r.height <= 0) return;
      const rawX = ((event.clientX - r.left) / r.width) * 2 - 1;
      const rawY = -(((event.clientY - r.top) / r.height) * 2 - 1);
      mouse.x = rawX;
      mouse.y = rawY;
      targetMouseX = rawX * 0.55;
      targetMouseY = rawY * 0.55;

      raycaster.setFromCamera(mouse, camera);
      const intersects = raycaster.intersectObjects([coreMesh, glassMesh, glassShellMesh, ring1, ring2, ring3, ring4, node1, node2, node3, node4], true);
      isHovered = (intersects.length > 0) || (Math.sqrt(rawX * rawX + rawY * rawY) < 0.65);
    };

    const onPointerLeave = () => {
      isHovered = false;
      mouse.x = -999;
      mouse.y = -999;
      targetMouseX = 0;
      targetMouseY = 0;
    };

    const onPointerDown = () => {
      burst(2.2);
      if (isDockedState) {
        if (typeof window.showView === "function") {
          window.showView("chat");
        } else {
          const chatPill = document.getElementById("pill-chat") || document.getElementById("rail-nav-chat");
          if (chatPill) {
            chatPill.click();
          } else {
            expand();
          }
        }
      } else {
        const chatInput = document.getElementById("chat-input");
        if (chatInput) chatInput.focus();
      }
    };

    window.addEventListener("mousemove", onPointerMove, { passive: true });
    container.addEventListener("pointerdown", onPointerDown);
    container.addEventListener("pointerleave", onPointerLeave);

    // WebGL Context Lost & Restored
    canvas.addEventListener("webglcontextlost", (event) => {
      event.preventDefault();
      console.warn("[Orbit] WebGL context lost; halting render loop.");
      isContextLost = true;
      pause();
    }, false);

    canvas.addEventListener("webglcontextrestored", () => {
      console.info("[Orbit] WebGL context restored; resuming renderer.");
      isContextLost = false;
      resume();
      forceResize();
    }, false);

    // Document Visibility Change (Background Tab Pause)
    document.addEventListener("visibilitychange", () => {
      if (document.hidden) {
        pause();
      } else {
        resume();
        forceResize();
      }
    });

    // ResizeObserver on container with getBoundingClientRect()
    if (typeof ResizeObserver !== "undefined") {
      resizeObserver = new ResizeObserver((entries) => {
        for (const entry of entries) {
          const cr = entry.contentRect;
          const w = cr && cr.width > 0 ? cr.width : container.clientWidth;
          const h = cr && cr.height > 0 ? cr.height : container.clientHeight;
          if (w > 0 && h > 0) {
            handleResizeDimensions(w, h);
          }
        }
      });
      resizeObserver.observe(container);
    }

    // Attach transitionend listener on stage wrapper for post-transition resize
    const stageWrapper = document.getElementById("chat-orbit-header-stage");
    if (stageWrapper) {
      stageWrapper.addEventListener("transitionend", () => {
        requestAnimationFrame(() => forceResize());
      });
    }

    // Apply current theme palette
    const initialTheme = document.documentElement.getAttribute("data-theme") || "dark";
    setTheme(initialTheme);

    // Start Animation Loop
    isRunning = true;
    animate();

    instance = {
      init,
      pause,
      resume,
      setMode,
      burst,
      dock,
      expand,
      destroy,
      setTheme,
      forceResize,
      assertIntegrity,
      handleResize: forceResize,
      pulse: (val) => burst(val || 2.0),
      triggerReasoning: (active) => setMode(active ? "thinking" : "idle"),
      get isDocked() { return isDockedState; },
      get currentMode() { return currentMode; },
      get canvas() { return canvas; },
      get renderer() { return renderer; },
      get scene() { return scene; },
      get camera() { return camera; },
      get composer() { return composer; }
    };

    window.__ORBIT__ = instance;
    window.__threeCore = instance;

    // Listen for custom bus events
    window.addEventListener("orbit:mode", (e) => {
      if (e.detail) setMode(e.detail);
    });

    return instance;
  }

  function initPostProcessing() {
    // Post-processing disabled for now to avoid WebGL feedback loop issues
    // Can be re-enabled once proper multi-pass rendering is set up
    composer = null;
  }

  function buildHolographicCore() {
    // =====================================================================
    // LIGHTING RIG - Multi-source with IBL-style environment
    // =====================================================================

    // Main colored point lights
    lightCyan = new THREE.PointLight(0x00f2fe, 4.0, 25);
    lightCyan.position.set(5, 4, 5);
    lightCyan.decay = 1.8;
    scene.add(lightCyan);

    lightMagenta = new THREE.PointLight(0xf43f5e, 4.5, 25);
    lightMagenta.position.set(-5, -4, 4);
    lightMagenta.decay = 1.8;
    scene.add(lightMagenta);

    lightPurple = new THREE.PointLight(0xa855f7, 3.5, 22);
    lightPurple.position.set(0, 5, -4);
    lightPurple.decay = 1.8;
    scene.add(lightPurple);

    lightGold = new THREE.PointLight(0xfbbf24, 3.5, 20);
    lightGold.position.set(0, -5, 5);
    lightGold.decay = 1.8;
    scene.add(lightGold);

    // Hemisphere light for ambient fill
    hemiLight = new THREE.HemisphereLight(0x00f2fe, 0x1a1a3e, 1.5);
    scene.add(hemiLight);

    // Directional key light
    dirLight = new THREE.DirectionalLight(0xffffff, 0.8);
    dirLight.position.set(3, 5, 4);
    scene.add(dirLight);

    // Ambient base
    ambientLight = new THREE.AmbientLight(0x18182f, 2.0);
    scene.add(ambientLight);

    // =====================================================================
    // 1. INNER LUMINOUS CORE - Emissive plasma sphere
    // =====================================================================
    const coreGeo = new THREE.SphereGeometry(0.72, 64, 64);
    coreMat = new THREE.MeshStandardMaterial({
      color: 0xffffff),
      emissive: 0x00f2fe),
      emissiveIntensity: 1.5,
      metalness: 0.0,
      roughness: 0.1,
      transparent: true,
      opacity: 0.98,
      side: THREE.DoubleSide
    });
    coreMesh = new THREE.Mesh(coreGeo, coreMat);
    mainGroup.add(coreMesh);

    // Core inner glow shell
    const coreGlowGeo = new THREE.SphereGeometry(0.78, 32, 32);
    const coreGlowMat = new THREE.MeshBasicMaterial({
      color: 0x00f2fe),
      transparent: true,
      opacity: 0.15,
      side: THREE.BackSide,
      blending: THREE.AdditiveBlending,
      depthWrite: false
    });
    const coreGlowMesh = new THREE.Mesh(coreGlowGeo, coreGlowMat);
    coreMesh.add(coreGlowMesh);
    coreMesh.userData.glowShell = coreGlowMesh;

    // =====================================================================
    // 2. GLASSMORPHIC OUTER ENERGY SHELL - Physical transmission
    // =====================================================================
    const glassGeo = new THREE.SphereGeometry(1.02, 64, 64);
    glassMat = new THREE.MeshPhysicalMaterial({
      color: 0x8b5cf6),
      transmission: 0.92,
      opacity: 1.0,
      transparent: true,
      roughness: 0.03,
      metalness: 0.08,
      ior: 1.52,
      clearcoat: 1.0,
      clearcoatRoughness: 0.02
    });
    glassMesh = new THREE.Mesh(glassGeo, glassMat);
    mainGroup.add(glassMesh);

    // Outer glass shell for refraction highlights
    const glassShellGeo = new THREE.SphereGeometry(1.08, 64, 64);
    glassShellMat = new THREE.MeshPhysicalMaterial({
      color: 0xffffff),
      transmission: 0.98,
      opacity: 0.3,
      transparent: true,
      roughness: 0.0,
      metalness: 0.0,
      ior: 1.05,
      clearcoat: 1.0,
      clearcoatRoughness: 0.0,
      side: THREE.BackSide,
      blending: THREE.AdditiveBlending,
      depthWrite: false
    });
    glassShellMesh = new THREE.Mesh(glassShellGeo, glassShellMat);
    mainGroup.add(glassShellMesh);

    // =====================================================================
    // 3. DUAL NESTED HOLOGRAPHIC WIREFRAMES
    // =====================================================================
    const wireGeo1 = new THREE.IcosahedronGeometry(0.88, 2);
    wireMat1 = new THREE.MeshBasicMaterial({
      color: 0x38bdf8),
      wireframe: true,
      transparent: true,
      opacity: 0.5,
      blending: THREE.AdditiveBlending,
      depthWrite: false
    });
    wireMesh1 = new THREE.Mesh(wireGeo1, wireMat1);
    mainGroup.add(wireMesh1);

    const wireGeo2 = new THREE.DodecahedronGeometry(1.14, 1);
    wireMat2 = new THREE.MeshBasicMaterial({
      color: 0xf43f5e),
      wireframe: true,
      transparent: true,
      opacity: 0.3,
      blending: THREE.AdditiveBlending,
      depthWrite: false
    });
    wireMesh2 = new THREE.Mesh(wireGeo2, wireMat2);
    mainGroup.add(wireMesh2);

    // =====================================================================
    // 4. VIBRANT MULTI-COLORED ORBITAL RINGS (PBR)
    // =====================================================================
    const createOrbitalRing = (radius, tubeRadius, rx, ry, rz, colorHex, emissiveHex, opacity, roughness = 0.1) => {
      const ringGeo = new THREE.TorusGeometry(radius, tubeRadius, 32, 180);
      const ringMat = new THREE.MeshStandardMaterial({
        color: new THREE.Color(colorHex),
        emissive: new THREE.Color(emissiveHex),
        emissiveIntensity: 1.2,
        roughness: roughness,
        metalness: 0.9,
        transparent: true,
        opacity: opacity
      });
      const ring = new THREE.Mesh(ringGeo, ringMat);
      ring.rotation.set(rx, ry, rz);
      ring.castShadow = true;
      ring.receiveShadow = true;
      return { mesh: ring, material: ringMat };
    };

    const ring1Data = createOrbitalRing(R1, 0.022, Math.PI / 5.5, 0.25, 0, 0x00f2fe, 0x00f2fe, 0.95);
    const ring2Data = createOrbitalRing(R2, 0.019, -Math.PI / 5.5, -0.25, 0.35, 0xf43f5e, 0xf43f5e, 0.9);
    const ring3Data = createOrbitalRing(R3, 0.016, Math.PI / 5.0, -0.35, -0.25, 0xa855f7, 0xa855f7, 0.85);
    const ring4Data = createOrbitalRing(R4, 0.014, -Math.PI / 5.0, 0.35, 0.45, 0xfbbf24, 0xf59e0b, 0.8);

    ring1 = ring1Data.mesh; ring1Mat = ring1Data.material;
    ring2 = ring2Data.mesh; ring2Mat = ring2Data.material;
    ring3 = ring3Data.mesh; ring3Mat = ring3Data.material;
    ring4 = ring4Data.mesh; ring4Mat = ring4Data.material;

    mainGroup.add(ring1, ring2, ring3, ring4);

    // =====================================================================
    // 5. GLOWING SATELLITE NODES (PBR spheres)
    // =====================================================================
    const createNode = (colorHex, emissiveHex) => {
      const nodeGeo = new THREE.SphereGeometry(0.07, 32, 32);
      const nodeMat = new THREE.MeshStandardMaterial({
        color: new THREE.Color(colorHex),
        emissive: new THREE.Color(emissiveHex),
        emissiveIntensity: 2.0,
        roughness: 0.0,
        metalness: 1.0,
        transparent: true,
        opacity: 1.0
      });
      const node = new THREE.Mesh(nodeGeo, nodeMat);
      node.castShadow = true;
      return { mesh: node, material: nodeMat };
    };

    const node1Data = createNode(0x38bdf8, 0x00f2fe);
    const node2Data = createNode(0xfb7185, 0xf43f5e);
    const node3Data = createNode(0xc084fc, 0xa855f7);
    const node4Data = createNode(0xfde047, 0xfbbf24);

    node1 = node1Data.mesh; nodeMats.push(node1Data.material);
    node2 = node2Data.mesh; nodeMats.push(node2Data.material);
    node3 = node3Data.mesh; nodeMats.push(node3Data.material);
    node4 = node4Data.mesh; nodeMats.push(node4Data.material);

    ring1.add(node1);
    ring2.add(node2);
    ring3.add(node3);
    ring4.add(node4);

    // Node trail effects
    node1.userData.trail = [];
    node2.userData.trail = [];
    node3.userData.trail = [];
    node4.userData.trail = [];

    // =====================================================================
    // 6. ENERGY FIELD - Volumetric sphere with noise
    // =====================================================================
    energyFieldGeom = new THREE.SphereGeometry(2.3, 48, 48);
    energyFieldMat = new THREE.MeshBasicMaterial({
      color: 0x00f2fe),
      transparent: true,
      opacity: 0.03,
      side: THREE.BackSide,
      blending: THREE.AdditiveBlending,
      depthWrite: false
    });
    energyFieldMesh = new THREE.Mesh(energyFieldGeom, energyFieldMat);
    mainGroup.add(energyFieldMesh);

    // =====================================================================
    // 7. MULTI-CHROMATIC AMBIENT PARTICLE SWARM (Physics-based)
    // =====================================================================
    const particleGeometry = new THREE.BufferGeometry();
    particlePositions = new Float32Array(particleCount * 3);
    particleVelocities = new Float32Array(particleCount * 3);
    particleLifetimes = new Float32Array(particleCount);
    particleSizes = new Float32Array(particleCount);
    particleColors = new Float32Array(particleCount * 3);

    for (let i = 0; i < particleCount; i++) {
      resetParticle(i);
    }

    particleGeometry.setAttribute("position", new THREE.BufferAttribute(particlePositions, 3));
    particleGeometry.setAttribute("color", new THREE.BufferAttribute(particleColors, 3));
    particleGeometry.setAttribute("size", new THREE.BufferAttribute(particleSizes, 1));
    particleGeometry.setAttribute("lifetime", new THREE.BufferAttribute(particleLifetimes, 1));

    particleMaterial = new THREE.PointsMaterial({
      size: 0.05,
      vertexColors: true,
      transparent: true,
      opacity: 0.9,
      sizeAttenuation: true,
      blending: THREE.AdditiveBlending,
      depthWrite: false,
      color: 0xffffff
    });

    particles = new THREE.Points(particleGeometry, particleMaterial);
    mainGroup.add(particles);
  }

  function resetParticle(i) {
    // Spherical distribution around core
    const theta = Math.random() * Math.PI * 2;
    const phi = Math.acos(2 * Math.random() - 1);
    const r = 0.95 + Math.random() * 1.35;

    particlePositions[i * 3] = r * Math.sin(phi) * Math.cos(theta);
    particlePositions[i * 3 + 1] = r * Math.sin(phi) * Math.sin(theta);
    particlePositions[i * 3 + 2] = r * Math.cos(phi);

    // Orbital velocity
    const orbitalSpeed = 0.008 + Math.random() * 0.012;
    const tangent = new THREE.Vector3(
      -Math.sin(theta),
      Math.cos(theta),
      0
    ).multiplyScalar(orbitalSpeed);

    // Add radial component
    const radial = new THREE.Vector3(
      particlePositions[i * 3],
      particlePositions[i * 3 + 1],
      particlePositions[i * 3 + 2]
    ).normalize().multiplyScalar((Math.random() - 0.5) * 0.003);

    particleVelocities[i * 3] = tangent.x + radial.x;
    particleVelocities[i * 3 + 1] = tangent.y + radial.y;
    particleVelocities[i * 3 + 2] = tangent.z + radial.z;

    particleLifetimes[i] = Math.random();
    particleSizes[i] = 0.035 + Math.random() * 0.025;

    const colors = ensurePColors();
    if (colors) {
      const selectedCol = colors[Math.floor(Math.random() * colors.length)];
      particleColors[i * 3] = selectedCol.r;
      particleColors[i * 3 + 1] = selectedCol.g;
      particleColors[i * 3 + 2] = selectedCol.b;
    }
  }

  function updateParticles(delta) {
    if (!particles || !particlePositions) return;

    const positions = particlePositions;
    const velocities = particleVelocities;
    const lifetimes = particleLifetimes;
    const sizes = particleSizes;
    const colors = particleColors;

    const time = accumulatedTime;

    for (let i = 0; i < particleCount; i++) {
      // Update position with velocity
      positions[i * 3] += velocities[i * 3] * delta * 60 * speedMultiplier;
      positions[i * 3 + 1] += velocities[i * 3 + 1] * delta * 60 * speedMultiplier;
      positions[i * 3 + 2] += velocities[i * 3 + 2] * delta * 60 * speedMultiplier;

      // Apply central gravity
      const dx = positions[i * 3];
      const dy = positions[i * 3 + 1];
      const dz = positions[i * 3 + 2];
      const dist = Math.sqrt(dx * dx + dy * dy + dz * dz);

      if (dist > 0) {
        const gravity = 0.0008 * speedMultiplier;
        velocities[i * 3] -= dx / dist * gravity;
        velocities[i * 3 + 1] -= dy / dist * gravity;
        velocities[i * 3 + 2] -= dz / dist * gravity;
      }

      // Orbital force
      const orbitalForce = 0.0003;
      velocities[i * 3] += -dy * orbitalForce;
      velocities[i * 3 + 1] += dx * orbitalForce;

      // Lifetime pulse
      lifetimes[i] += delta * 0.15;
      if (lifetimes[i] > 1) lifetimes[i] -= 1;

      // Size pulsation
      const pulsePhase = (lifetimes[i] * Math.PI * 2) + (i * 0.1);
      sizes[i] = (0.035 + Math.sin(pulsePhase) * 0.015) * (0.8 + hoverTransition * 0.4 + clickImpulse * 0.5);

      // Color shift based on mode
      if (currentMode === "alert") {
        const alertFactor = Math.sin(time * 8) * 0.5 + 0.5;
        colors[i * 3] = THREE.MathUtils.lerp(colors[i * 3], 1.0, alertFactor * 0.3);
        colors[i * 3 + 1] = THREE.MathUtils.lerp(colors[i * 3 + 1], 0.2, alertFactor * 0.3);
      } else if (currentMode === "thinking") {
        const thinkFactor = Math.sin(time * 4) * 0.5 + 0.5;
        colors[i * 3] = THREE.MathUtils.lerp(colors[i * 3], 0.0, thinkFactor * 0.2);
        colors[i * 3 + 1] = THREE.MathUtils.lerp(colors[i * 3 + 1], 1.0, thinkFactor * 0.2);
      }

      // Respawn if too far or too close
      if (dist > 3.5 || dist < 0.7) {
        resetParticle(i);
      }
    }

    particles.geometry.attributes.position.needsUpdate = true;
    particles.geometry.attributes.size.needsUpdate = true;
    particles.geometry.attributes.color.needsUpdate = true;
  }

  function handleResizeDimensions(w, h) {
    if (w <= 0 || h <= 0 || !renderer || !camera) return;
    camera.aspect = w / h;
    camera.updateProjectionMatrix();
    renderer.setSize(w, h, false);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
    if (composer) {
      composer.setSize(w, h);
    }
    if (!isRunning && renderer && scene) {
      renderer.render(scene, camera);
    }
  }

  function forceResize() {
    if (!container) return;
    const rect = container.getBoundingClientRect();
    const w = rect.width;
    const h = rect.height;
    if (w > 0 && h > 0) {
      handleResizeDimensions(w, h);
    }
  }

  function pause() {
    if (animId) {
      cancelAnimationFrame(animId);
      animId = null;
    }
    isRunning = false;
    if (clock) clock.stop();
  }

  function resume() {
    if (isContextLost) return;
    if (isRunning && animId) return;
    if (animId) {
      cancelAnimationFrame(animId);
      animId = null;
    }
    isRunning = true;
    if (clock) clock.start();
    if (renderer && scene && camera) {
      renderer.render(scene, camera);
    }
    animate();
  }

  function assertIntegrity() {
    if (!container || !renderer || !renderer.domElement) return;
    if (!renderer.domElement.isConnected) {
      console.warn("[Orbit Guard] WebGL canvas was disconnected from DOM. Re-attaching...");
      container.innerHTML = "";
      container.appendChild(renderer.domElement);
    }
    const rect = container.getBoundingClientRect();
    if (rect.width > 0 && rect.height > 0) {
      const curW = renderer.domElement.clientWidth;
      const curH = renderer.domElement.clientHeight;
      if (curW !== Math.round(rect.width) || curH !== Math.round(rect.height)) {
        forceResize();
      }
    }
  }

  function burst(intensity = 2.2) {
    clickImpulse = intensity;
    // Also pulse all rings
    if (ring1Mat) ring1Mat.emissiveIntensity = 2.5;
    if (ring2Mat) ring2Mat.emissiveIntensity = 2.5;
    if (ring3Mat) ring3Mat.emissiveIntensity = 2.5;
    if (ring4Mat) ring4Mat.emissiveIntensity = 2.5;
    if (coreMat) coreMat.emissiveIntensity = 3.0;
  }

  function setMode(mode) {
    currentMode = mode;
    if (alertTimer) {
      clearTimeout(alertTimer);
      alertTimer = null;
    }

    if (mode === "thinking") {
      targetSpeed = 2.8;
      clickImpulse = 1.4;
      if (coreMat) {
        coreMat.emissiveIntensity = 2.5;
        coreMat.emissive = 0x00f2fe);
      }
      if (bloomPass) {
        bloomPass.strength = 1.0;
        bloomPass.radius = 0.6;
        bloomPass.threshold = 0.7;
      }
    } else if (mode === "alert") {
      targetSpeed = 2.2;
      clickImpulse = 1.6;
      if (coreMat) {
        coreMat.emissive = 0xf43f5e);
        coreMat.emissiveIntensity = 3.0;
      }
      if (bloomPass) {
        bloomPass.strength = 1.4;
        bloomPass.radius = 0.8;
        bloomPass.threshold = 0.5;
      }
      if (lightCyan) lightCyan.color.set(0xf43f5e);
      if (lightMagenta) lightMagenta.color.set(0xf43f5e);
      alertTimer = setTimeout(() => {
        setMode("idle");
      }, 1500);
    } else if (mode === "docked") {
      isDockedState = true;
      targetSpeed = 0.6;
      if (bloomPass) {
        bloomPass.strength = 0.3;
        bloomPass.radius = 0.3;
      }
    } else {
      // "idle"
      targetSpeed = 1.0;
      isDockedState = false;
      const curTheme = document.documentElement.getAttribute("data-theme") || "dark";
      setTheme(curTheme);
      if (bloomPass) {
        bloomPass.strength = 0.6;
        bloomPass.radius = 0.4;
        bloomPass.threshold = 0.85;
      }
    }
  }

  function dock() {
    isDockedState = true;
    const stage = document.getElementById("chat-orbit-header-stage");
    if (stage) {
      stage.classList.remove("orbit-stage-expanded");
      stage.classList.add("orbit-stage-docked");
    }
    setMode("docked");
    forceResize();
    resume();
    if (transitionTimer) clearTimeout(transitionTimer);
    transitionTimer = setTimeout(() => {
      forceResize();
    }, 380);
  }

  function expand() {
    if (window.appState && window.appState.activeView && window.appState.activeView !== "chat") {
      console.debug("[Orbit] expand() ignored: activeView is", window.appState.activeView);
      return;
    }
    isDockedState = false;
    const stage = document.getElementById("chat-orbit-header-stage");
    if (stage) {
      stage.classList.remove("orbit-stage-docked");
      stage.classList.add("orbit-stage-expanded");
    }
    setMode("idle");
    resume();
    if (transitionTimer) clearTimeout(transitionTimer);
    transitionTimer = setTimeout(() => {
      forceResize();
      resume();
      assertIntegrity();
    }, 450);
  }

  function setTheme(theme) {
    if (!particleMaterial || !wireMat1 || !wireMat2 || !coreMat || !ambientLight ||
        !glassMat || !glassShellMat || !ring1Mat || !ring2Mat || !ring3Mat || !ring4Mat) return;

    const isLight = theme === "light";

    if (isLight) {
      // Light theme - matte ceramic with subtle colors
      particleMaterial.blending = THREE.NormalBlending;
      particleMaterial.opacity = 0.7;
      particleMaterial.size = 0.05;
      particleMaterial.needsUpdate = true;

      wireMat1.blending = THREE.NormalBlending;
      wireMat1.color.set(0x0284c7);
      wireMat1.opacity = 0.6;
      wireMat1.needsUpdate = true;

      wireMat2.blending = THREE.NormalBlending;
      wireMat2.color.set(0xe11d48);
      wireMat2.opacity = 0.4;
      wireMat2.needsUpdate = true;

      coreMat.emissive.set(0x0284c7);
      coreMat.emissiveIntensity = 1.2;
      coreMat.color.set(0xf0f9ff);
      coreMat.transmission = 0.4;
      coreMat.needsUpdate = true;

      glassMat.color.set(0x7c3aed);
      glassMat.transmission = 0.95;
      glassMat.roughness = 0.02;
      glassMat.metalness = 0.05;
      glassMat.iridescence = 0.4;
      glassMat.needsUpdate = true;

      glassShellMat.opacity = 0.2;
      glassShellMat.needsUpdate = true;

      // Rings - softer for light theme
      ring1Mat.color.set(0x0284c7); ring1Mat.emissive.set(0x0284c7); ring1Mat.opacity = 0.8; ring1Mat.roughness = 0.15; ring1Mat.needsUpdate = true;
      ring2Mat.color.set(0xe11d48); ring2Mat.emissive.set(0xe11d48); ring2Mat.opacity = 0.75; ring2Mat.roughness = 0.15; ring2Mat.needsUpdate = true;
      ring3Mat.color.set(0x7c3aed); ring3Mat.emissive.set(0x7c3aed); ring3Mat.opacity = 0.7; ring3Mat.roughness = 0.15; ring3Mat.needsUpdate = true;
      ring4Mat.color.set(0xca8a04); ring4Mat.emissive.set(0xca8a04); ring4Mat.opacity = 0.65; ring4Mat.roughness = 0.15; ring4Mat.needsUpdate = true;

      // Nodes
      nodeMats[0].color.set(0x0284c7); nodeMats[0].emissive.set(0x0284c7); nodeMats[0].needsUpdate = true;
      nodeMats[1].color.set(0xe11d48); nodeMats[1].emissive.set(0xe11d48); nodeMats[1].needsUpdate = true;
      nodeMats[2].color.set(0x7c3aed); nodeMats[2].emissive.set(0x7c3aed); nodeMats[2].needsUpdate = true;
      nodeMats[3].color.set(0xca8a04); nodeMats[3].emissive.set(0xca8a04); nodeMats[3].needsUpdate = true;

      ambientLight.color.set(0x94a3b8);
      ambientLight.intensity = 2.8;

      if (lightCyan) { lightCyan.intensity = 4.5; lightCyan.color.set(0x0284c7); }
      if (lightMagenta) { lightMagenta.intensity = 4.8; lightMagenta.color.set(0xe11d48); }
      if (lightPurple) { lightPurple.intensity = 4.0; lightPurple.color.set(0x7c3aed); }
      if (lightGold) { lightGold.intensity = 3.8; lightGold.color.set(0xca8a04); }
      if (hemiLight) { hemiLight.color.set(0x0284c7); hemiLight.groundColor= 0x1a1a3e); hemiLight.intensity = 1.8; }
      if (dirLight) { dirLight.intensity = 1.0; dirLight.color.set(0xffffff); }

      energyFieldMat.color.set(0x0284c7);
      energyFieldMat.opacity = 0.02;
      energyFieldMat.needsUpdate = true;

    } else {
      // Dark theme - cyberpunk neon
      particleMaterial.blending = THREE.AdditiveBlending;
      particleMaterial.opacity = 0.9;
      particleMaterial.size = 0.045;
      particleMaterial.needsUpdate = true;

      wireMat1.blending = THREE.AdditiveBlending;
      wireMat1.color.set(0x38bdf8);
      wireMat1.opacity = 0.5;
      wireMat1.needsUpdate = true;

      wireMat2.blending = THREE.AdditiveBlending;
      wireMat2.color.set(0xf43f5e);
      wireMat2.opacity = 0.3;
      wireMat2.needsUpdate = true;

      coreMat.emissiveIntensity = 1.8;
      coreMat.color.set(0xffffff);
      coreMat.transmission = 0.3;
      coreMat.needsUpdate = true;

      glassMat.color.set(0x8b5cf6);
      glassMat.transmission = 0.92;
      glassMat.roughness = 0.03;
      glassMat.metalness = 0.08;
      glassMat.iridescence = 0.6;
      glassMat.needsUpdate = true;

      glassShellMat.opacity = 0.3;
      glassShellMat.needsUpdate = true;

      // Rings - vibrant neon
      ring1Mat.color.set(0x00f2fe); ring1Mat.emissive.set(0x00f2fe); ring1Mat.opacity = 0.95; ring1Mat.roughness = 0.1; ring1Mat.needsUpdate = true;
      ring2Mat.color.set(0xf43f5e); ring2Mat.emissive.set(0xf43f5e); ring2Mat.opacity = 0.9; ring2Mat.roughness = 0.1; ring2Mat.needsUpdate = true;
      ring3Mat.color.set(0xa855f7); ring3Mat.emissive.set(0xa855f7); ring3Mat.opacity = 0.85; ring3Mat.roughness = 0.1; ring3Mat.needsUpdate = true;
      ring4Mat.color.set(0xfbbf24); ring4Mat.emissive.set(0xf59e0b); ring4Mat.opacity = 0.8; ring4Mat.roughness = 0.1; ring4Mat.needsUpdate = true;

      // Nodes
      nodeMats[0].color.set(0x38bdf8); nodeMats[0].emissive.set(0x00f2fe); nodeMats[0].needsUpdate = true;
      nodeMats[1].color.set(0xfb7185); nodeMats[1].emissive.set(0xf43f5e); nodeMats[1].needsUpdate = true;
      nodeMats[2].color.set(0xc084fc); nodeMats[2].emissive.set(0xa855f7); nodeMats[2].needsUpdate = true;
      nodeMats[3].color.set(0xfde047); nodeMats[3].emissive.set(0xfbbf24); nodeMats[3].needsUpdate = true;

      ambientLight.color.set(0x18182f);
      ambientLight.intensity = 2.0;

      if (lightCyan) { lightCyan.intensity = 4.0; lightCyan.color.set(0x00f2fe); }
      if (lightMagenta) { lightMagenta.intensity = 4.5; lightMagenta.color.set(0xf43f5e); }
      if (lightPurple) { lightPurple.intensity = 3.8; lightPurple.color.set(0xa855f7); }
      if (lightGold) { lightGold.intensity = 3.5; lightGold.color.set(0xfbbf24); }
      if (hemiLight) { hemiLight.color.set(0x00f2fe); hemiLight.groundColor= 0x1a1a3e); hemiLight.intensity = 1.5; }
      if (dirLight) { dirLight.intensity = 0.8; dirLight.color.set(0xffffff); }

      energyFieldMat.color.set(0x00f2fe);
      energyFieldMat.opacity = 0.04;
      energyFieldMat.needsUpdate = true;
    }
  }

  function animate() {
    if (!isRunning || isContextLost) return;
    animId = requestAnimationFrame(animate);

    const delta = Math.min(clock.getDelta(), 0.05);

    // FPS counter
    frameCount++;
    const now = performance.now();
    if (now - lastFpsUpdate > 1000) {
      currentFps = Math.round(frameCount * 1000 / (now - lastFpsUpdate));
      frameCount = 0;
      lastFpsUpdate = now;
    }

    hoverTransition += ((isHovered ? 1.0 : 0.0) - hoverTransition) * 0.08;
    clickImpulse = Math.max(0, clickImpulse - delta * 2.2);
    speedMultiplier += (targetSpeed - speedMultiplier) * 0.12;
    accumulatedTime += delta * speedMultiplier;

    const t = accumulatedTime;

    // =====================================================================
    // CORE ANIMATIONS
    // =====================================================================

    // Levitation breathing
    mainGroup.position.y = Math.sin(t * 1.3) * (0.1 + hoverTransition * 0.06 + clickImpulse * 0.08);

    // Mouse inertia tracking
    currentMouseX += (targetMouseX - currentMouseX) * 0.06;
    currentMouseY += (targetMouseY - currentMouseY) * 0.06;
    mainGroup.rotation.y = t * 0.18 + currentMouseX;
    mainGroup.rotation.x = currentMouseY * 0.5;

    // Core pulsation - complex multi-frequency
    const pulseFreq = 2.4 + hoverTransition * 3.0 + clickImpulse * 4.0;
    const pulseAmp = 0.07 + hoverTransition * 0.1 + clickImpulse * 0.15;
    const pulse = Math.sin(t * pulseFreq) * pulseAmp + (1.0 + hoverTransition * 0.12 + clickImpulse * 0.2);

    coreMesh.scale.set(pulse, pulse, pulse);
    glassMesh.scale.set(1.0 + (pulse - 1.0) * 0.5, 1.0 + (pulse - 1.0) * 0.5, 1.0 + (pulse - 1.0) * 0.5);
    glassShellMesh.scale.set(1.0 + (pulse - 1.0) * 0.3, 1.0 + (pulse - 1.0) * 0.3, 1.0 + (pulse - 1.0) * 0.3);

    // Core emissive intensity and hue cycling
    if (currentMode !== "alert") {
      const baseEmissive = 1.2 + Math.sin(t * pulseFreq) * 0.5;
      coreMat.emissiveIntensity = baseEmissive + hoverTransition * 1.0 + clickImpulse * 2.0;
      const hue = (t * (0.05 + hoverTransition * 0.08 + clickImpulse * 0.15)) % 1;
      coreMat.emissive.setHSL(hue, 0.95, 0.6);
    }

    // Core glow shell pulse
    if (coreMesh.userData.glowShell) {
      coreMesh.userData.glowShell.scale.setScalar(1.0 + Math.sin(t * 3) * 0.15);
      coreMesh.userData.glowShell.material.opacity = 0.1 + Math.sin(t * 2.5) * 0.08 + hoverTransition * 0.15;
    }

    // Flare point lights on hover/surge
    if (lightCyan && lightMagenta && currentMode !== "alert") {
      lightCyan.intensity = 4.0 + hoverTransition * 2.5 + clickImpulse * 4.0;
      lightMagenta.intensity = 4.5 + hoverTransition * 2.8 + clickImpulse * 4.5;
      lightPurple.intensity = 3.5 + hoverTransition * 2.0 + clickImpulse * 3.5;
      lightGold.intensity = 3.5 + hoverTransition * 2.0 + clickImpulse * 3.5;
    }

    // Wireframe counter-rotation
    wireMesh1.rotation.y = -t * 0.45;
    wireMesh1.rotation.z = t * 0.3;
    wireMesh2.rotation.x = t * 0.35;
    wireMesh2.rotation.y = -t * 0.25;
    glassMesh.rotation.y = t * 0.12;
    glassShellMesh.rotation.y = -t * 0.08;

    // Ring rotations with varying speeds
    ring1.rotation.z = t * 0.55;
    ring2.rotation.z = -t * 0.45;
    ring3.rotation.z = t * 0.38;
    ring4.rotation.z = -t * 0.32;

    // Ring wobble
    ring1.rotation.x = Math.sin(t * 0.7) * 0.08;
    ring2.rotation.x = Math.sin(t * 0.9 + 1) * 0.06;
    ring3.rotation.x = Math.sin(t * 1.1 + 2) * 0.05;
    ring4.rotation.x = Math.sin(t * 0.8 + 3) * 0.04;

    // Ring emissive pulse
    const ringPulse = 1.0 + Math.sin(t * 3.5) * 0.3 + hoverTransition * 0.4 + clickImpulse * 0.6;
    if (ring1Mat) ring1Mat.emissiveIntensity = ringPulse * 1.2;
    if (ring2Mat) ring2Mat.emissiveIntensity = ringPulse * 1.1;
    if (ring3Mat) ring3Mat.emissiveIntensity = ringPulse * 1.0;
    if (ring4Mat) ring4Mat.emissiveIntensity = ringPulse * 0.9;

    // Satellite nodes orbital motion with easing
    const s1 = t * 1.2;
    node1.position.set(Math.cos(s1) * R1, Math.sin(s1) * R1, Math.sin(t * 0.5) * 0.15);

    const s2 = -t * 1.05 + 1.5;
    node2.position.set(Math.cos(s2) * R2, Math.sin(s2) * R2, Math.cos(t * 0.7) * 0.12);

    const s3 = t * 0.88 + 2.8;
    node3.position.set(Math.cos(s3) * R3, Math.sin(s3) * R3, Math.sin(t * 0.6 + 1) * 0.1);

    const s4 = -t * 0.72 + 4.2;
    node4.position.set(Math.cos(s4) * R4, Math.sin(s4) * R4, Math.cos(t * 0.8 + 2) * 0.08);

    // Node emissive pulse
    nodeMats.forEach((mat, i) => {
      const nodePulse = 2.0 + Math.sin(t * (4 + i) + i) * 0.5 + hoverTransition * 0.8;
      mat.emissiveIntensity = nodePulse;
    });

    // Energy field expansion
    if (energyFieldMesh) {
      const fieldScale = 1.0 + Math.sin(t * 0.8) * 0.1 + hoverTransition * 0.15;
      energyFieldMesh.scale.setScalar(fieldScale);
      energyFieldMesh.rotation.y = t * 0.05;
      energyFieldMesh.rotation.x = t * 0.03;
      energyFieldMat.opacity = 0.03 + Math.sin(t * 1.5) * 0.015 + hoverTransition * 0.03;
    }

    // Update physics-based particles
    updateParticles(delta);

    // Particle system rotation
    particles.rotation.y = t * 0.08;
    particles.rotation.x = Math.sin(t * 0.25) * 0.06;

    // Render with post-processing or direct
    if (composer && bloomPass) {
      composer.render();
    } else if (renderer && scene && camera) {
      renderer.render(scene, camera);
    }
  }

  function destroy() {
    pause();
    if (resizeObserver) {
      resizeObserver.disconnect();
      resizeObserver = null;
    }
    if (composer) {
      // dispose passes
      if (renderPass) renderPass.dispose();
      if (bloomPass) bloomPass.dispose();
      composer.dispose();
      composer = null;
    }
    if (canvas && canvas.parentNode) {
      canvas.parentNode.removeChild(canvas);
    }
    if (renderer) {
      renderer.dispose();
      renderer = null;
    }
    // Dispose geometries and materials
    [coreMesh, glassMesh, glassShellMesh, wireMesh1, wireMesh2,
     ring1, ring2, ring3, ring4, node1, node2, node3, node4,
     particles, energyFieldMesh].forEach(obj => {
      if (obj) {
        if (obj.geometry) obj.geometry.dispose();
        if (obj.material) {
          if (Array.isArray(obj.material)) {
            obj.material.forEach(m => m.dispose());
          } else {
            obj.material.dispose();
          }
        }
      }
    });
    window.__ORBIT__ = null;
    instance = null;
  }

  const publicAPI = {
    init,
    pause,
    resume,
    setMode,
    burst,
    dock,
    expand,
    destroy,
    setTheme,
    forceResize,
    assertIntegrity,
    handleResize: forceResize,
    pulse: (val) => burst(val || 2.0),
    triggerReasoning: (active) => setMode(active ? "thinking" : "idle"),
    get isDocked() { return isDockedState; },
    get currentMode() { return currentMode; },
    get canvas() { return canvas; },
    get renderer() { return renderer; },
    get scene() { return scene; },
    get camera() { return camera; },
    get composer() { return composer; },
    get fps() { return currentFps; }
  };

  if (typeof window !== "undefined") {
    window.Orbit = publicAPI;
    window.__threeCore = publicAPI;

    // Click docked orbit to return smoothly to Chat Desk
    const setupOrbitClick = () => {
      const stage = document.getElementById("chat-orbit-header-stage");
      if (stage && !stage._hasDockClick) {
        stage._hasDockClick = true;
        stage.addEventListener("click", () => {
          if (stage.classList.contains("orbit-stage-docked")) {
            if (typeof window.showView === "function") {
              window.showView("chat");
            }
          }
        });
      }
    };
    if (document.readyState === "loading") {
      document.addEventListener("DOMContentLoaded", setupOrbitClick);
    } else {
      setupOrbitClick();
    }
  }

  return publicAPI;
})();