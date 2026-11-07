# Corrected code_chat_hero.html

Copy this to `ui/code_chat_hero.html`

```html
<!DOCTYPE html>
<html class="dark" lang="en">
<head>
  <meta charset="utf-8"/>
  <meta content="width=device-width, initial-scale=1.0" name="viewport"/>
  <meta content="web_standard" name="shell-type"/>
  <title>Ola Support Intelligence</title>
  
  <!-- Fonts -->
  <link href="https://fonts.googleapis.com" rel="preconnect"/>
  <link crossorigin="" href="https://fonts.gstatic.com" rel="preconnect"/>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet"/>
  <link href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:opsz,wght,FILL,GRAD@20..48,100..700,0..1,-50..200" rel="stylesheet"/>
  <link href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:wght,FILL@100..700,0..1&display=swap" rel="stylesheet"/>
  
  <!-- Tailwind CSS -->
  <script src="https://cdn.tailwindcss.com?plugins=forms,container-queries"></script>
  <script id="tailwind-config">
    tailwind.config = {
      darkMode: "class",
      theme: {
        extend: {
          colors: {
            "surface-container-highest": "#31353f",
            "secondary-fixed-dim": "#4edea3",
            "on-background": "#dfe2f0",
            "surface-dim": "#0f131d",
            "surface-variant": "#31353f",
            "tertiary-container": "#ffd0ce",
            "inverse-on-surface": "#2c303b",
            "surface-container-lowest": "#0a0e17",
            "surface-container-low": "#171c25",
            "on-primary-container": "#006a70",
            "primary": "#e0fdff",
            "on-secondary-fixed-variant": "#005236",
            "on-surface": "#dfe2f0",
            "tertiary-fixed": "#ffdad8",
            "on-error": "#690005",
            "on-error-container": "#ffdad6",
            "primary-fixed-dim": "#00dce6",
            "surface-container-high": "#262a34",
            "background": "#0f131d",
            "on-surface-variant": "#b9cacb",
            "on-tertiary-fixed-variant": "#881d24",
            "secondary-fixed": "#6ffbbe",
            "inverse-surface": "#dfe2f0",
            "secondary-container": "#00a572",
            "error": "#ffb4ab",
            "surface-tint": "#00dce6",
            "on-tertiary-container": "#aa373b",
            "surface-container": "#1b2029",
            "tertiary-fixed-dim": "#ffb3b0",
            "on-secondary-container": "#00311f",
            "on-tertiary": "#670211",
            "error-container": "#93000a",
            "inverse-primary": "#00696f",
            "on-secondary": "#003824",
            "on-primary-fixed": "#002022",
            "primary-container": "#00f2fe",
            "on-primary": "#00373a",
            "on-secondary-fixed": "#002113",
            "outline": "#849495",
            "on-tertiary-fixed": "#410006",
            "surface-bright": "#353944",
            "secondary": "#4edea3",
            "surface": "#0f131d",
            "outline-variant": "#3a494b",
            "on-primary-fixed-variant": "#004f53",
            "primary-fixed": "#6ff6ff",
            "tertiary": "#fff5f4"
          },
          borderRadius: {
            DEFAULT: "0.25rem",
            lg: "0.5rem",
            xl: "0.75rem"
          }
        }
      }
    }
  </script>
  
  <!-- Three.js - Single import -->
  <script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>
  
  <!-- External CSS -->
  <link href="../static/css/tokens.css" rel="stylesheet"/>
  <link href="../static/css/base.css" rel="stylesheet"/>
  <link href="../static/css/components.css" rel="stylesheet"/>
  <link href="../static/css/hero-animation.css" rel="stylesheet"/>
  
  <!-- Base styles for Three.js container -->
  <style>
    @layer base {
      html, body { margin: 0; padding: 0; }
      body { overscroll-behavior: none; }
      main > :first-child { margin-top: 0 !important; }
      main > :last-child { margin-bottom: 0 !important; }
    }
    ::-webkit-scrollbar { display: none; }
  </style>
</head>
<body>
  <div class="w-full h-full bg-transparent">
    <!-- Three.js Hero Animation Canvas -->
    <div id="threejs-container-ANIMATION_34" class="threejs-hero-canvas"></div>
    
    <!-- Hero Content -->
    <div class="text-center px-4 py-8">
      <h1 class="hero-title">How can I help?</h1>
      <p class="hero-subtitle mt-3">Ask any official ride policy question or enter a ticket ID to inspect.</p>
    </div>
    
    <!-- Hero Search Composer -->
    <div class="hero-search-composer">
      <div class="hero-search-glow-border">
        <div class="hero-search-inner">
          <!-- Mode Selector Button -->
          <button class="hero-search-mode-btn" type="button" aria-haspopup="listbox" aria-expanded="false">
            <span class="mode-icon" aria-hidden="true">🤖</span>
            <span class="sparkle-icon" aria-hidden="true">✨</span>
            <span class="mode-label">Help Desk</span>
            <span class="material-symbols-outlined dropdown-icon" aria-hidden="true">arrow_drop_down</span>
          </button>
          
          <!-- Search Input -->
          <input 
            class="hero-search-input" 
            placeholder="Enter your inquiry or ticket ID (e.g. TKT-0007)..." 
            type="text"
            aria-label="Search or enter ticket ID"
          />
          
          <!-- Submit Button -->
          <button class="hero-search-submit" type="submit" aria-label="Submit inquiry">
            <span class="material-symbols-outlined submit-icon" aria-hidden="true">send</span>
            <span class="submit-text">Ask</span>
          </button>
        </div>
      </div>
    </div>
    
    <!-- Navigation Drawer Toggle (if needed) -->
    <button 
      class="fixed bottom-6 right-6 z-50 p-3 rounded-xl bg-gradient-to-r from-cyan-500/20 via-purple-500/20 to-pink-500/20 text-cyan-300 shadow-[0_0_20px_rgba(0,242,254,0.3)] hover:from-cyan-500/30 hover:to-pink-500/30 transition-all"
      onclick="toggleNavDrawer()"
      aria-label="Toggle navigation"
    >
      <span class="material-symbols-outlined text-[24px]">menu</span>
    </button>
  </div>

  <!-- Three.js Custom Element Definition -->
  <script>
    // Navigation Drawer State Management
    let isNavDrawerOpen = false;

    function setDrawerState(open) {
      isNavDrawerOpen = open;
      const drawer = document.getElementById('nav-sidebar-drawer');
      const workspace = document.getElementById('main-content-workspace');
      const statusPill = document.getElementById('rail-status-pill');
      const searchBar = document.getElementById('rail-search-bar');
      const searchMini = document.getElementById('rail-search-mini');
      const sectionLabel = document.getElementById('rail-section-label');
      const operationalContext = document.getElementById('rail-operational-context');
      const railLabels = document.querySelectorAll('.rail-label');

      if (!drawer || !workspace) return;

      if (isNavDrawerOpen) {
        drawer.style.width = '240px';
        workspace.style.paddingLeft = '240px';
        if (statusPill) statusPill.classList.remove('hidden');
        if (searchBar) searchBar.classList.remove('hidden');
        if (searchMini) searchMini.classList.add('hidden');
        if (sectionLabel) sectionLabel.classList.remove('hidden');
        if (operationalContext) {
          operationalContext.classList.remove('hidden');
          operationalContext.classList.add('flex');
        }
        railLabels.forEach(el => el.classList.remove('hidden'));
      } else {
        drawer.style.width = '64px';
        workspace.style.paddingLeft = '64px';
        if (statusPill) statusPill.classList.add('hidden');
        if (searchBar) searchBar.classList.add('hidden');
        if (searchMini) searchMini.classList.remove('hidden');
        if (sectionLabel) sectionLabel.classList.add('hidden');
        if (operationalContext) {
          operationalContext.classList.add('hidden');
          operationalContext.classList.remove('flex');
        }
        railLabels.forEach(el => el.classList.add('hidden'));
      }
    }

    function toggleNavDrawer() {
      setDrawerState(!isNavDrawerOpen);
    }

    function closeNavDrawer() {
      setDrawerState(false);
    }

    // Keyboard shortcut support (Escape closes drawer)
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape' && isNavDrawerOpen) {
        closeNavDrawer();
      }
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'b') {
        e.preventDefault();
        toggleNavDrawer();
      }
    });

    // Custom element runner for threejs-scene
    class ThreejsSceneElement extends HTMLElement {
      connectedCallback() {
        const container = this;
        const width = container.clientWidth || window.innerWidth;
        const height = container.clientHeight || window.innerHeight;

        const scene = new THREE.Scene();
        const camera = new THREE.PerspectiveCamera(45, width / height, 0.1, 1000);
        camera.position.z = 6;

        const renderer = new THREE.WebGLRenderer({ 
          alpha: true, 
          antialias: true, 
          powerPreference: "high-performance" 
        });
        renderer.setSize(width, height);
        renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
        renderer.toneMapping = THREE.ACESFilmicToneMapping;
        renderer.toneMappingExposure = 1.3;
        container.appendChild(renderer.domElement);

        const mainGroup = new THREE.Group();
        scene.add(mainGroup);

        // Vibrant multi-chromatic light setup
        const lightCyan = new THREE.PointLight(0x00f2fe, 3.5, 20);
        lightCyan.position.set(4, 3, 4);
        scene.add(lightCyan);

        const lightMagenta = new THREE.PointLight(0xf43f5e, 4.0, 20);
        lightMagenta.position.set(-4, -3, 3);
        scene.add(lightMagenta);

        const lightPurple = new THREE.PointLight(0xa855f7, 3.0, 18);
        lightPurple.position.set(0, 4, -3);
        scene.add(lightPurple);

        const lightGold = new THREE.PointLight(0xfbbf24, 3.0, 16);
        lightGold.position.set(0, -4, 4);
        scene.add(lightGold);

        const ambientLight = new THREE.AmbientLight(0x18182f, 1.8);
        scene.add(ambientLight);

        // 1. Inner Luminous Core Sphere (Dynamic Color Shift)
        const coreGeo = new THREE.SphereGeometry(0.75, 64, 64);
        const coreMat = new THREE.MeshPhongMaterial({
          color: 0xffffff,
          emissive: 0x00f2fe,
          emissiveIntensity: 1.1,
          shininess: 100,
          specular: 0xffffff,
          transparent: true,
          opacity: 0.96
        });
        const coreMesh = new THREE.Mesh(coreGeo, coreMat);
        mainGroup.add(coreMesh);

        // 2. Glassmorphic Outer Energy Sphere with Chromatic Transmission
        const glassGeo = new THREE.SphereGeometry(1.08, 64, 64);
        const glassMat = new THREE.MeshPhysicalMaterial({
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
        const glassMesh = new THREE.Mesh(glassGeo, glassMat);
        mainGroup.add(glassMesh);

        // 3. Dual Nested Wireframe Geometries for holographic depth
        const wireGeo1 = new THREE.IcosahedronGeometry(0.92, 2);
        const wireMat1 = new THREE.MeshBasicMaterial({
          color: 0x38bdf8,
          wireframe: true,
          transparent: true,
          opacity: 0.45,
          blending: THREE.AdditiveBlending
        });
        const wireMesh1 = new THREE.Mesh(wireGeo1, wireMat1);
        mainGroup.add(wireMesh1);

        const wireGeo2 = new THREE.DodecahedronGeometry(1.2, 1);
        const wireMat2 = new THREE.MeshBasicMaterial({
          color: 0xf43f5e,
          wireframe: true,
          transparent: true,
          opacity: 0.25,
          blending: THREE.AdditiveBlending
        });
        const wireMesh2 = new THREE.Mesh(wireGeo2, wireMat2);
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

        // Ring 1: Neon Cyan
        const ring1 = createOrbitalRing(1.68, 0.024, Math.PI / 2.3, 0.35, 0, 0x00f2fe, 0x00f2fe, 0.9);
        // Ring 2: Vivid Pink / Magenta
        const ring2 = createOrbitalRing(1.92, 0.020, -Math.PI / 2.7, -0.4, 0.4, 0xf43f5e, 0xf43f5e, 0.85);
        // Ring 3: Electric Violet / Purple
        const ring3 = createOrbitalRing(2.18, 0.016, Math.PI / 1.75, 0.75, -0.3, 0xa855f7, 0xa855f7, 0.8);
        // Ring 4: Radiant Golden Amber
        const ring4 = createOrbitalRing(2.42, 0.014, -Math.PI / 3.4, 0.5, 0.8, 0xfbbf24, 0xf59e0b, 0.75);

        mainGroup.add(ring1);
        mainGroup.add(ring2);
        mainGroup.add(ring3);
        mainGroup.add(ring4);

        // 5. Glowing Satellite Nodes on each ring
        const createNode = (colorHex) => {
          const nodeGeo = new THREE.SphereGeometry(0.075, 32, 32);
          const nodeMat = new THREE.MeshBasicMaterial({ color: colorHex });
          return new THREE.Mesh(nodeGeo, nodeMat);
        };

        const node1 = createNode(0x38bdf8); // Cyan
        const node2 = createNode(0xfb7185); // Rose
        const node3 = createNode(0xc084fc); // Purple
        const node4 = createNode(0xfde047); // Gold

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
          new THREE.Color(0x00f2fe), // Cyan
          new THREE.Color(0xf43f5e), // Pink
          new THREE.Color(0xa855f7), // Purple
          new THREE.Color(0xfbbf24), // Amber
          new THREE.Color(0x34d399), // Emerald
          new THREE.Color(0xffffff)  // Sparkle White
        ];

        for (let i = 0; i < particleCount; i++) {
          const theta = Math.random() * Math.PI * 2;
          const phi = Math.acos(2 * Math.random() - 1);
          const r = 1.35 + Math.random() * 1.8;

          particlePositions[i * 3] = r * Math.sin(phi) * Math.cos(theta);
          particlePositions[i * 3 + 1] = r * Math.sin(phi) * Math.sin(theta);
          particlePositions[i * 3 + 2] = r * Math.cos(phi);

          const selectedCol = pColors[Math.floor(Math.random() * pColors.length)];
          particleColors[i * 3] = selectedCol.r;
          particleColors[i * 3 + 1] = selectedCol.g;
          particleColors[i * 3 + 2] = selectedCol.b;
        }

        particleGeometry.setAttribute('position', new THREE.BufferAttribute(particlePositions, 3));
        particleGeometry.setAttribute('color', new THREE.BufferAttribute(particleColors, 3));

        const particleMaterial = new THREE.PointsMaterial({
          size: 0.05,
          vertexColors: true,
          transparent: true,
          opacity: 0.85,
          blending: THREE.AdditiveBlending
        });

        const particles = new THREE.Points(particleGeometry, particleMaterial);
        mainGroup.add(particles);

        // Interactive State variables for Hover & Click reactivity
        let isHovered = false;
        let hoverTransition = 0; // 0 to 1
        let clickImpulse = 0; // decays over time
        let speedMultiplier = 1.0;

        // Mouse & Raycasting setup
        const raycaster = new THREE.Raycaster();
        const mouse = new THREE.Vector2(-999, -999);
        let targetMouseX = 0;
        let targetMouseY = 0;
        let currentMouseX = 0;
        let currentMouseY = 0;

        // Container interactive cursor style
        container.style.cursor = 'pointer';

        const onPointerMove = (event) => {
          const rect = container.getBoundingClientRect();
          const rawX = (event.clientX - rect.left) / rect.width * 2 - 1;
          const rawY = -((event.clientY - rect.top) / rect.height * 2 - 1);
          mouse.x = rawX;
          mouse.y = rawY;

          targetMouseX = rawX * 0.55;
          targetMouseY = rawY * 0.55;

          // Raycast against core and glass outer orb
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
          clickImpulse = 1.8; // Trigger rapid shockwave and supercharged pulse
        };

        window.addEventListener('mousemove', onPointerMove);
        container.addEventListener('pointerdown', onPointerDown);
        container.addEventListener('pointerleave', onPointerLeave);

        // Animation Loop
        let clock = new THREE.Clock();
        let accumulatedTime = 0;

        function animate() {
          requestAnimationFrame(animate);
          const delta = Math.min(clock.getDelta(), 0.1);

          // Smoothly blend hover state: 0 (idle) -> 1 (hovered)
          hoverTransition += ((isHovered ? 1.0 : 0.0) - hoverTransition) * 0.08;

          // Decay click impulse
          clickImpulse = Math.max(0, clickImpulse - delta * 2.2);

          // Calculate dynamic speed multiplier (idle ~1.0, hover ~2.4, click burst up to ~4.5)
          const targetSpeed = 1.0 + (hoverTransition * 1.6) + (clickImpulse * 2.5);
          speedMultiplier += (targetSpeed - speedMultiplier) * 0.12;
          accumulatedTime += delta * speedMultiplier;

          const t = accumulatedTime;

          // Levitation motion with dynamic frequency
          mainGroup.position.y = Math.sin(t * 1.4) * (0.09 + hoverTransition * 0.05);

          // Smooth mouse inertia tracking
          currentMouseX += (targetMouseX - currentMouseX) * 0.07;
          currentMouseY += (targetMouseY - currentMouseY) * 0.07;
          mainGroup.rotation.y = t * 0.22 + currentMouseX;
          mainGroup.rotation.x = currentMouseY;

          // Pulsing frequency increases rapidly on hover & click
          // Base pulse frequency 2.5, accelerated up to 7.0+ on hover/burst
          const pulseFreq = 2.6 + hoverTransition * 3.5 + clickImpulse * 4.5;
          const pulseAmp = 0.06 + hoverTransition * 0.08 + clickImpulse * 0.12;
          const pulse = Math.sin(t * pulseFreq) * pulseAmp + (1.0 + hoverTransition * 0.1 + clickImpulse * 0.18);

          coreMesh.scale.set(pulse, pulse, pulse);
          glassMesh.scale.set(1.0 + (pulse - 1.0) * 0.55, 1.0 + (pulse - 1.0) * 0.55, 1.0 + (pulse - 1.0) * 0.55);

          // Core brightness and glow intensity surge on hover/click
          const baseEmissive = 1.0 + Math.sin(t * pulseFreq) * 0.4;
          coreMat.emissiveIntensity = baseEmissive + hoverTransition * 0.8 + clickImpulse * 1.5;

          // Dynamic rapid hue shifting faster on hover
          const hue = (t * (0.07 + hoverTransition * 0.1 + clickImpulse * 0.2)) % 1;
          coreMat.emissive.setHSL(hue, 0.95, 0.55);

          // Flare point lights on hover/burst
          lightCyan.intensity = 3.5 + hoverTransition * 2.0 + clickImpulse * 3.5;
          lightMagenta.intensity = 4.0 + hoverTransition * 2.2 + clickImpulse * 3.8;

          // Counter rotate nested wireframes at accelerated spin
          wireMesh1.rotation.y = -t * 0.55;
          wireMesh1.rotation.z = t * 0.35;
          wireMesh2.rotation.x = t * 0.42;
          wireMesh2.rotation.y = -t * 0.28;
          glassMesh.rotation.y = t * 0.16;

          // Multi-axis orbital rings spin dynamically faster
          ring1.rotation.z = t * 0.65;
          ring2.rotation.z = -t * 0.55;
          ring3.rotation.z = t * 0.45;
          ring4.rotation.z = -t * 0.38;

          // Orbital Satellite nodes
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

          // Particles rotate and scale slightly with energy surge
          particles.rotation.y = t * 0.12;
          particles.rotation.x = Math.sin(t * 0.3) * 0.08;
          particleMaterial.size = 0.05 + hoverTransition * 0.02 + clickImpulse * 0.035;

          renderer.render(scene, camera);
        }

        animate();

        const handleResize = () => {
          const w = container.clientWidth || window.innerWidth;
          const h = container.clientHeight || window.innerHeight;
          camera.aspect = w / h;
          camera.updateProjectionMatrix();
          renderer.setSize(w, h);
          renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
        };

        window.addEventListener('resize', handleResize);
      }
    }

    if (!customElements.get('threejs-scene')) {
      customElements.define('threejs-scene', ThreejsSceneElement);
    }
  </script>
</body>
</html>
