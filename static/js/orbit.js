/**
 * 3D Holographic Orbit Singleton Controller (Three.js)
 * Persistent UI epicenter for Ola Support Intelligence Operations Desk.
 * Strictly maintains one WebGLRenderer, one Scene, and one Canvas instance.
 */

export const Orbit = (() => {
  let instance = null;
  let container = null;
  let canvas = null;
  let renderer = null;
  let scene = null;
  let camera = null;
  let mainGroup = null;

  // Lights
  let lightCyan, lightMagenta, lightPurple, lightGold, ambientLight;

  // Meshes & Materials
  let coreMesh, coreMat;
  let glassMesh, glassMat;
  let wireMesh1, wireMat1;
  let wireMesh2, wireMat2;
  let ring1, ring2, ring3, ring4;
  let node1, node2, node3, node4;
  let particles, particleMaterial;

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
    const initialW = rect.width > 0 ? rect.width : 280;
    const initialH = rect.height > 0 ? rect.height : 280;

    scene = new THREE.Scene();
    camera = new THREE.PerspectiveCamera(45, initialW / initialH, 0.1, 1000);
    camera.position.z = 5.5;

    try {
      renderer = new THREE.WebGLRenderer({
        alpha: true,
        antialias: true,
        preserveDrawingBuffer: true,
        powerPreference: "high-performance"
      });
    } catch (err) {
      console.error("[Orbit] WebGLRenderer creation failure:", err);
      return null;
    }

    renderer.setSize(initialW, initialH, false);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
    if (THREE.ACESFilmicToneMapping) {
      renderer.toneMapping = THREE.ACESFilmicToneMapping;
      renderer.toneMappingExposure = 1.3;
    }

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
    mainGroup.scale.set(1.10, 1.10, 1.10);
    scene.add(mainGroup);

    // Multi-chromatic light rig
    lightCyan = new THREE.PointLight(0x00f2fe, 3.5, 20);
    lightCyan.position.set(4, 3, 4);
    scene.add(lightCyan);

    lightMagenta = new THREE.PointLight(0xf43f5e, 4.0, 20);
    lightMagenta.position.set(-4, -3, 3);
    scene.add(lightMagenta);

    lightPurple = new THREE.PointLight(0xa855f7, 3.0, 18);
    lightPurple.position.set(0, 4, -3);
    scene.add(lightPurple);

    lightGold = new THREE.PointLight(0xfbbf24, 3.0, 16);
    lightGold.position.set(0, -4, 4);
    scene.add(lightGold);

    ambientLight = new THREE.AmbientLight(0x18182f, 1.8);
    scene.add(ambientLight);

    // 1. Inner Luminous Core Sphere
    const coreGeo = new THREE.SphereGeometry(0.75, 64, 64);
    coreMat = new THREE.MeshPhongMaterial({
      color: 0xffffff,
      emissive: 0x00f2fe,
      emissiveIntensity: 1.1,
      shininess: 100,
      specular: 0xffffff,
      transparent: true,
      opacity: 0.96
    });
    coreMesh = new THREE.Mesh(coreGeo, coreMat);
    mainGroup.add(coreMesh);

    // 2. Glassmorphic Outer Energy Sphere with Transmission
    const glassGeo = new THREE.SphereGeometry(1.08, 64, 64);
    glassMat = new THREE.MeshPhysicalMaterial({
      color: 0x8b5cf6,
      transmission: 0.88,
      opacity: 1.0,
      transparent: true,
      roughness: 0.06,
      metalness: 0.15,
      ior: 1.48,
      reflectivity: 0.95,
      clearcoat: 1.0,
      clearcoatRoughness: 0.04
    });
    glassMesh = new THREE.Mesh(glassGeo, glassMat);
    mainGroup.add(glassMesh);

    // 3. Dual Nested Holographic Wireframe Geometries
    const wireGeo1 = new THREE.IcosahedronGeometry(0.92, 2);
    wireMat1 = new THREE.MeshBasicMaterial({
      color: 0x38bdf8,
      wireframe: true,
      transparent: true,
      opacity: 0.45,
      blending: THREE.AdditiveBlending
    });
    wireMesh1 = new THREE.Mesh(wireGeo1, wireMat1);
    mainGroup.add(wireMesh1);

    const wireGeo2 = new THREE.DodecahedronGeometry(1.2, 1);
    wireMat2 = new THREE.MeshBasicMaterial({
      color: 0xf43f5e,
      wireframe: true,
      transparent: true,
      opacity: 0.25,
      blending: THREE.AdditiveBlending
    });
    wireMesh2 = new THREE.Mesh(wireGeo2, wireMat2);
    mainGroup.add(wireMesh2);

    // 4. Vibrant Multi-Colored Orbital Rings
    const createOrbitalRing = (radius, tubeRadius, rx, ry, rz, colorHex, emissiveHex, opacity) => {
      const ringGeo = new THREE.TorusGeometry(radius, tubeRadius, 28, 160);
      const ringMat = new THREE.MeshStandardMaterial({
        color: colorHex,
        emissive: emissiveHex,
        emissiveIntensity: 0.9,
        roughness: 0.15,
        metalness: 0.85,
        transparent: true,
        opacity: opacity
      });
      const ring = new THREE.Mesh(ringGeo, ringMat);
      ring.rotation.set(rx, ry, rz);
      return ring;
    };

    ring1 = createOrbitalRing(1.68, 0.024, Math.PI / 2.3, 0.35, 0, 0x00f2fe, 0x00f2fe, 0.9);
    ring2 = createOrbitalRing(1.92, 0.020, -Math.PI / 2.7, -0.4, 0.4, 0xf43f5e, 0xf43f5e, 0.85);
    ring3 = createOrbitalRing(2.18, 0.016, Math.PI / 1.75, 0.75, -0.3, 0xa855f7, 0xa855f7, 0.8);
    ring4 = createOrbitalRing(2.42, 0.014, -Math.PI / 3.4, 0.5, 0.8, 0xfbbf24, 0xf59e0b, 0.75);

    mainGroup.add(ring1);
    mainGroup.add(ring2);
    mainGroup.add(ring3);
    mainGroup.add(ring4);

    // 5. Glowing Satellite Nodes
    const createNode = (colorHex) => {
      const nodeGeo = new THREE.SphereGeometry(0.075, 32, 32);
      const nodeMat = new THREE.MeshBasicMaterial({ color: colorHex });
      return new THREE.Mesh(nodeGeo, nodeMat);
    };

    node1 = createNode(0x38bdf8);
    node2 = createNode(0xfb7185);
    node3 = createNode(0xc084fc);
    node4 = createNode(0xfde047);

    mainGroup.add(node1);
    mainGroup.add(node2);
    mainGroup.add(node3);
    mainGroup.add(node4);

    // 6. Multi-chromatic Ambient Particle Swarm
    const particleCount = 360;
    const particleGeometry = new THREE.BufferGeometry();
    const particlePositions = new Float32Array(particleCount * 3);
    const particleColors = new Float32Array(particleCount * 3);

    const pColors = [
      new THREE.Color(0x00f2fe),
      new THREE.Color(0xf43f5e),
      new THREE.Color(0xa855f7),
      new THREE.Color(0xfbbf24),
      new THREE.Color(0x34d399),
      new THREE.Color(0xffffff)
    ];

    for (let i = 0; i < particleCount; i++) {
      const theta = Math.random() * Math.PI * 2;
      const phi = Math.acos(2 * Math.random() - 1);
      const r = 1.1 + Math.random() * 1.35;

      particlePositions[i * 3] = r * Math.sin(phi) * Math.cos(theta);
      particlePositions[i * 3 + 1] = r * Math.sin(phi) * Math.sin(theta);
      particlePositions[i * 3 + 2] = r * Math.cos(phi);

      const selectedCol = pColors[Math.floor(Math.random() * pColors.length)];
      particleColors[i * 3] = selectedCol.r;
      particleColors[i * 3 + 1] = selectedCol.g;
      particleColors[i * 3 + 2] = selectedCol.b;
    }

    particleGeometry.setAttribute("position", new THREE.BufferAttribute(particlePositions, 3));
    particleGeometry.setAttribute("color", new THREE.BufferAttribute(particleColors, 3));

    particleMaterial = new THREE.PointsMaterial({
      size: 0.05,
      vertexColors: true,
      transparent: true,
      opacity: 0.85,
      blending: THREE.AdditiveBlending
    });

    particles = new THREE.Points(particleGeometry, particleMaterial);
    mainGroup.add(particles);

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
      const intersects = raycaster.intersectObjects([coreMesh, glassMesh, ring1, ring2, ring3, ring4]);
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
        expand();
        const chatPill = document.getElementById("pill-chat") || document.getElementById("rail-nav-chat");
        if (chatPill) chatPill.click();
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
      handleResize: forceResize,
      pulse: (val) => burst(val || 2.0),
      triggerReasoning: (active) => setMode(active ? "thinking" : "idle"),
      get isDocked() { return isDockedState; },
      get currentMode() { return currentMode; },
      get canvas() { return canvas; },
      get renderer() { return renderer; },
      get scene() { return scene; },
      get camera() { return camera; }
    };

    window.__ORBIT__ = instance;
    window.__threeCore = instance;

    // Listen for custom bus events
    window.addEventListener("orbit:mode", (e) => {
      if (e.detail) setMode(e.detail);
    });

    return instance;
  }

  function handleResizeDimensions(w, h) {
    if (w <= 0 || h <= 0 || !renderer || !camera) return;
    camera.aspect = w / h;
    camera.updateProjectionMatrix();
    renderer.setSize(w, h, false);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
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

  function burst(intensity = 2.2) {
    clickImpulse = intensity;
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
      if (coreMat) coreMat.emissiveIntensity = 2.2;
    } else if (mode === "alert") {
      targetSpeed = 2.2;
      clickImpulse = 1.6;
      if (coreMat) {
        coreMat.emissive.setHex(0xf43f5e);
        coreMat.emissiveIntensity = 2.4;
      }
      alertTimer = setTimeout(() => {
        setMode("idle");
      }, 1500);
    } else if (mode === "docked") {
      isDockedState = true;
      targetSpeed = 0.8;
    } else {
      // "idle"
      targetSpeed = 1.0;
      isDockedState = false;
      const curTheme = document.documentElement.getAttribute("data-theme") || "dark";
      setTheme(curTheme);
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
    if (transitionTimer) clearTimeout(transitionTimer);
    transitionTimer = setTimeout(() => {
      forceResize();
    }, 380);
  }

  function expand() {
    isDockedState = false;
    const stage = document.getElementById("chat-orbit-header-stage");
    if (stage) {
      stage.classList.remove("orbit-stage-docked");
      stage.classList.add("orbit-stage-expanded");
    }
    setMode("idle");
    if (transitionTimer) clearTimeout(transitionTimer);
    transitionTimer = setTimeout(() => {
      forceResize();
    }, 380);
  }

  function setTheme(theme) {
    if (!particleMaterial || !wireMat1 || !wireMat2 || !coreMat || !ambientLight) return;
    const isLight = theme === "light";
    if (isLight) {
      particleMaterial.blending = THREE.NormalBlending;
      particleMaterial.opacity = 0.95;
      particleMaterial.size = 0.055;
      particleMaterial.needsUpdate = true;

      wireMat1.blending = THREE.NormalBlending;
      wireMat1.color.setHex(0x0284c7);
      wireMat1.opacity = 0.75;
      wireMat1.needsUpdate = true;

      wireMat2.blending = THREE.NormalBlending;
      wireMat2.color.setHex(0xe11d48);
      wireMat2.opacity = 0.65;
      wireMat2.needsUpdate = true;

      coreMat.emissive.setHex(0x0284c7);
      coreMat.emissiveIntensity = 0.8;
      coreMat.color.setHex(0xf0f9ff);
      coreMat.needsUpdate = true;

      ambientLight.color.setHex(0x94a3b8);
      ambientLight.intensity = 2.4;

      if (lightCyan) {
        lightCyan.intensity = 4.0;
        lightCyan.color.setHex(0x0284c7);
      }
      if (lightMagenta) {
        lightMagenta.intensity = 4.2;
        lightMagenta.color.setHex(0xe11d48);
      }
    } else {
      particleMaterial.blending = THREE.AdditiveBlending;
      particleMaterial.opacity = 0.85;
      particleMaterial.size = 0.05;
      particleMaterial.needsUpdate = true;

      wireMat1.blending = THREE.AdditiveBlending;
      wireMat1.color.setHex(0x38bdf8);
      wireMat1.opacity = 0.45;
      wireMat1.needsUpdate = true;

      wireMat2.blending = THREE.AdditiveBlending;
      wireMat2.color.setHex(0xf43f5e);
      wireMat2.opacity = 0.25;
      wireMat2.needsUpdate = true;

      coreMat.emissiveIntensity = 1.1;
      coreMat.color.setHex(0xffffff);
      coreMat.needsUpdate = true;

      ambientLight.color.setHex(0x18182f);
      ambientLight.intensity = 1.8;

      if (lightCyan) {
        lightCyan.intensity = 3.5;
        lightCyan.color.setHex(0x00f2fe);
      }
      if (lightMagenta) {
        lightMagenta.intensity = 4.0;
        lightMagenta.color.setHex(0xf43f5e);
      }
    }
  }

  function animate() {
    if (!isRunning || isContextLost) return;
    animId = requestAnimationFrame(animate);

    // Delta clamp at 0.05 prevents time spikes after inactive frames
    const delta = Math.min(clock.getDelta(), 0.05);

    hoverTransition += ((isHovered ? 1.0 : 0.0) - hoverTransition) * 0.08;
    clickImpulse = Math.max(0, clickImpulse - delta * 2.2);

    const calcSpeed = currentMode === "thinking"
      ? 2.8
      : currentMode === "docked"
        ? 0.8
        : 1.0 + (hoverTransition * 1.6) + (clickImpulse * 2.5);

    speedMultiplier += (calcSpeed - speedMultiplier) * 0.12;
    accumulatedTime += delta * speedMultiplier;

    const t = accumulatedTime;

    // Levitation motion
    mainGroup.position.y = Math.sin(t * 1.4) * (0.09 + hoverTransition * 0.05);

    // Mouse inertia tracking
    currentMouseX += (targetMouseX - currentMouseX) * 0.07;
    currentMouseY += (targetMouseY - currentMouseY) * 0.07;
    mainGroup.rotation.y = t * 0.22 + currentMouseX;
    mainGroup.rotation.x = currentMouseY;

    // Pulsing frequency
    const pulseFreq = 2.6 + hoverTransition * 3.5 + clickImpulse * 4.5;
    const pulseAmp = 0.06 + hoverTransition * 0.08 + clickImpulse * 0.12;
    const pulse = Math.sin(t * pulseFreq) * pulseAmp + (1.0 + hoverTransition * 0.1 + clickImpulse * 0.18);

    coreMesh.scale.set(pulse, pulse, pulse);
    glassMesh.scale.set(1.0 + (pulse - 1.0) * 0.55, 1.0 + (pulse - 1.0) * 0.55, 1.0 + (pulse - 1.0) * 0.55);

    // Core emissive intensity
    const baseEmissive = 1.0 + Math.sin(t * pulseFreq) * 0.4;
    if (currentMode !== "alert") {
      coreMat.emissiveIntensity = baseEmissive + hoverTransition * 0.8 + clickImpulse * 1.5;
      const hue = (t * (0.07 + hoverTransition * 0.1 + clickImpulse * 0.2)) % 1;
      coreMat.emissive.setHSL(hue, 0.95, 0.55);
    }

    // Flare point lights on hover/surge
    if (lightCyan && lightMagenta) {
      lightCyan.intensity = 3.5 + hoverTransition * 2.0 + clickImpulse * 3.5;
      lightMagenta.intensity = 4.0 + hoverTransition * 2.2 + clickImpulse * 3.8;
    }

    // Counter rotate nested wireframes
    wireMesh1.rotation.y = -t * 0.55;
    wireMesh1.rotation.z = t * 0.35;
    wireMesh2.rotation.x = t * 0.42;
    wireMesh2.rotation.y = -t * 0.28;
    glassMesh.rotation.y = t * 0.16;

    // Multi-axis orbital rings spin
    ring1.rotation.z = t * 0.65;
    ring2.rotation.z = -t * 0.55;
    ring3.rotation.z = t * 0.45;
    ring4.rotation.z = -t * 0.38;

    // Satellite nodes
    const s1 = t * 1.3;
    node1.position.set(
      Math.cos(s1) * 1.68,
      Math.sin(s1) * 1.68 * Math.sin(ring1.rotation.x),
      Math.sin(s1) * 1.68 * Math.cos(ring1.rotation.x)
    );

    const s2 = -t * 1.15 + 1.5;
    node2.position.set(
      Math.cos(s2) * 1.92,
      Math.sin(s2) * 1.92 * Math.sin(ring2.rotation.x),
      Math.sin(s2) * 1.92 * Math.cos(ring2.rotation.x)
    );

    const s3 = t * 0.95 + 2.8;
    node3.position.set(
      Math.cos(s3) * 2.18,
      Math.sin(s3) * 2.18 * Math.sin(ring3.rotation.x),
      Math.sin(s3) * 2.18 * Math.cos(ring3.rotation.x)
    );

    const s4 = -t * 0.8 + 4.2;
    node4.position.set(
      Math.cos(s4) * 2.42,
      Math.sin(s4) * 2.42 * Math.sin(ring4.rotation.x),
      Math.sin(s4) * 2.42 * Math.cos(ring4.rotation.x)
    );

    // Particles rotate
    particles.rotation.y = t * 0.12;
    particles.rotation.x = Math.sin(t * 0.3) * 0.08;
    particleMaterial.size = 0.05 + hoverTransition * 0.02 + clickImpulse * 0.035;

    renderer.render(scene, camera);
  }

  function destroy() {
    pause();
    if (resizeObserver) {
      resizeObserver.disconnect();
      resizeObserver = null;
    }
    if (canvas && canvas.parentNode) {
      canvas.parentNode.removeChild(canvas);
    }
    if (renderer) {
      renderer.dispose();
      renderer = null;
    }
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
    handleResize: forceResize,
    pulse: (val) => burst(val || 2.0),
    triggerReasoning: (active) => setMode(active ? "thinking" : "idle"),
    get isDocked() { return isDockedState; },
    get currentMode() { return currentMode; },
    get canvas() { return canvas; },
    get renderer() { return renderer; },
    get scene() { return scene; },
    get camera() { return camera; }
  };

  if (typeof window !== "undefined") {
    window.Orbit = publicAPI;
    window.__threeCore = publicAPI;
  }

  return publicAPI;
})();
