/**
 * Ola Support Intelligence — Live 3D Mascot Controller (static/js/mascots.js)
 * Implements:
 * 1. Mascot State Machine: data-state="idle|thinking|speaking|success|blocked|wave"
 * 2. Pointer Parallax (--rx, --ry, --eye-x, --eye-y) with 60fps rAF smoothing
 * 3. Power-efficient lifecycle: pauses on visibilitychange and IntersectionObserver
 * 4. Dual-theme 3D SVG character rigs: "AI" (Robot) & "Sparky" (Fox/Cat companion)
 * 5. Accessible announcements and reduced-motion fallback
 */

(function (root, factory) {
  if (typeof module === "object" && module.exports) {
    module.exports = factory();
  } else {
    root.OlaMascots = factory();
  }
})(typeof globalThis !== "undefined" ? globalThis : this, function () {
  "use strict";

  const GREETINGS = [
    "Hello! How can I assist with your ride policies today?",
    "Hi there! Ask any ride refund, SLA, or policy question!",
    "Need a policy check or ticket status? Sparky and I are ready!",
    "Welcome! Explore canonical SLAs or check a ticket ID.",
    "Fast resolution & 24/7 SLA intelligence at your service!"
  ];

  /**
   * Generates the complete 3D inline SVG Character Rig.
   * Features:
   * - "AI" Robot: Antenna beacon, visor specular sheen, 3D shaded helmet,
   *   expressive eyes, talking mouth, pulsing reactor core, and robotic arms.
   * - "Sparky" Sidekick: Cute fox/cat with animated ears, wagging bushy tail,
   *   expressive pupils, and magnifying glass.
   * - Open Holographic Book with laser sweep beam (active during 'thinking').
   * - Dynamic 3D CSS layers (translateZ) and floor ambient shadow.
   */
  function getMascotSvgMarkup() {
    return `
      <svg class="mascot-svg-rig" viewBox="0 0 260 140" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
        <defs>
          <filter id="neonBloom" x="-30%" y="-30%" width="160%" height="160%">
            <feGaussianBlur stdDeviation="2" result="blur1"/>
            <feGaussianBlur stdDeviation="5" result="blur2"/>
            <feMerge>
              <feMergeNode in="blur2"/>
              <feMergeNode in="blur1"/>
              <feMergeNode in="SourceGraphic"/>
            </feMerge>
          </filter>

          <!-- Dark Theme: Obsidian Metal & Cyberpunk Neon -->
          <linearGradient id="robotBodyDark" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stop-color="#1e3a5f"/>
            <stop offset="100%" stop-color="#0a1526"/>
          </linearGradient>
          <linearGradient id="sparkyBodyDark" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stop-color="#162e4a"/>
            <stop offset="100%" stop-color="#0b1728"/>
          </linearGradient>

          <!-- Light Theme: Matte Ceramic White & Warm Golden Honey -->
          <linearGradient id="robotBodyLight" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stop-color="#ffffff"/>
            <stop offset="100%" stop-color="#e0e7ff"/>
          </linearGradient>
          <linearGradient id="sparkyBodyLight" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stop-color="#fef3c7"/>
            <stop offset="100%" stop-color="#fde68a"/>
          </linearGradient>
        </defs>

        <!-- Floor Occlusion & Contact Shadow -->
        <ellipse class="mascot-floor-shadow" cx="130" cy="132" rx="75" ry="7"/>

        <!-- ==================== CHARACTER 1: "AI" (ROBOT) ==================== -->
        <g class="character-ai-group">
          <!-- Hover Thruster / Lower Body Shadow -->
          <ellipse class="ai-thruster-glow" cx="80" cy="116" rx="14" ry="4"/>

          <!-- Torso -->
          <rect class="ai-torso-plate" x="62" y="80" width="36" height="30" rx="9"/>
          <!-- Pulsing Chest Core Light -->
          <circle class="ai-chest-core" cx="80" cy="95" r="5.5" filter="url(#neonBloom)"/>
          <circle class="ai-chest-core-inner" cx="80" cy="95" r="2.5" fill="#ffffff"/>

          <!-- Left Arm & Hand -->
          <g class="ai-arm-left">
            <path class="ai-arm-limb-l" d="M62 86 L48 96 L58 106" stroke-width="3.2" stroke-linecap="round" fill="none"/>
            <circle class="ai-hand-dot-l" cx="58" cy="106" r="3.5"/>
          </g>

          <!-- Right Arm & Hand (Waves in wave state, thumbs-up in success, holds book in thinking) -->
          <g class="ai-arm-right">
            <path class="ai-arm-limb-r" d="M98 86 L112 96 L104 106" stroke-width="3.2" stroke-linecap="round" fill="none"/>
            <circle class="ai-hand-dot-r" cx="104" cy="106" r="3.5"/>
            <!-- Thumbs up accessory badge -->
            <path class="ai-thumbs-up-icon" d="M104 101 L104 96 Q107 94 108 97 L108 102 Z" fill="#10b981"/>
          </g>

          <!-- Holographic Open Book (Active in thinking state) -->
          <g class="ai-holo-book">
            <path class="holo-book-cover" d="M60 106 Q80 112 100 106 L102 120 Q80 126 58 120 Z" stroke-width="2"/>
            <path class="holo-book-pages-l" d="M80 108 L60 106 L59 119 L80 122 Z"/>
            <path class="holo-book-pages-r" d="M80 108 L100 106 L101 119 L80 122 Z"/>
            <line class="holo-scan-laser" x1="58" y1="110" x2="102" y2="110" stroke-width="2.2" filter="url(#neonBloom)"/>
          </g>

          <!-- Head Unit (Parallax and 3D Rotation Target) -->
          <g class="ai-head-unit">
            <!-- Antenna with Glowing Beacon -->
            <line class="ai-antenna-mast" x1="80" y1="36" x2="80" y2="47" stroke-width="2.8" stroke-linecap="round"/>
            <circle class="ai-antenna-beacon" cx="80" cy="33" r="4.5" filter="url(#neonBloom)"/>

            <!-- Helmet Box -->
            <rect class="ai-head-helmet" x="55" y="46" width="50" height="36" rx="13" stroke-width="2.2"/>
            <!-- Visor Specular Reflection -->
            <path class="ai-visor-glint" d="M58 50 Q80 45 102 50" stroke="#ffffff" stroke-width="1.6" opacity="0.7" stroke-linecap="round"/>

            <!-- Face Screen & Visor -->
            <rect class="ai-visor-screen" x="61" y="52" width="38" height="24" rx="7"/>

            <!-- Expressive Glowing Eyes -->
            <g class="ai-eyes-group">
              <rect class="ai-eye-left" x="67" y="58" width="8.5" height="10" rx="4.2" filter="url(#neonBloom)"/>
              <rect class="ai-eye-right" x="84.5" y="58" width="8.5" height="10" rx="4.2" filter="url(#neonBloom)"/>
              <circle class="ai-pupil-left" cx="71" cy="62" r="1.8" fill="#ffffff"/>
              <circle class="ai-pupil-right" cx="89" cy="62" r="1.8" fill="#ffffff"/>
            </g>

            <!-- Rosy Cheeks -->
            <ellipse class="ai-blush-left" cx="66" cy="71" rx="3" ry="1.6"/>
            <ellipse class="ai-blush-right" cx="94" cy="71" rx="3" ry="1.6"/>

            <!-- Mouth / Visor Equalizer Waveform -->
            <path class="ai-mouth-curve" d="M75 70 Q80 74 85 70" stroke-width="2.4" stroke-linecap="round" fill="none"/>
            <g class="ai-equalizer-bars">
              <line class="eq-bar bar-1" x1="74" y1="71" x2="74" y2="67" stroke-width="2"/>
              <line class="eq-bar bar-2" x1="77" y1="72" x2="77" y2="65" stroke-width="2"/>
              <line class="eq-bar bar-3" x1="80" y1="73" x2="80" y2="64" stroke-width="2"/>
              <line class="eq-bar bar-4" x1="83" y1="72" x2="83" y2="65" stroke-width="2"/>
              <line class="eq-bar bar-5" x1="86" y1="71" x2="86" y2="67" stroke-width="2"/>
            </g>

            <!-- Guardrail Shield / Stop Hand (Active in 'blocked') -->
            <g class="ai-guard-shield">
              <path class="shield-outline" d="M80 50 L95 56 L95 72 Q80 84 80 84 Q65 72 65 56 Z" stroke-width="2" filter="url(#neonBloom)"/>
              <line x1="73" y1="67" x2="87" y2="67" stroke-width="2.5" stroke-linecap="round"/>
            </g>
          </g>
        </g>

        <!-- ==================== CHARACTER 2: "SPARKY" (COMPANION) ==================== -->
        <g class="character-sparky-group">
          <!-- Bushy Wagging Tail -->
          <g class="sparky-tail-rig">
            <path class="sparky-tail-path" d="M192 104 Q216 92 210 76 Q200 64 192 78" stroke-width="4" stroke-linecap="round" fill="none" filter="url(#neonBloom)"/>
            <circle class="sparky-tail-pom" cx="210" cy="76" r="3.5" filter="url(#neonBloom)"/>
          </g>

          <!-- Body -->
          <ellipse class="sparky-body-shape" cx="178" cy="106" rx="19" ry="15" stroke-width="2.2"/>
          <rect class="sparky-paws-l" x="166" y="115" width="8" height="12" rx="4"/>
          <rect class="sparky-paws-r" x="182" y="115" width="8" height="12" rx="4"/>

          <!-- Collar & Charm -->
          <path class="sparky-collar" d="M168 90 Q178 96 188 90" stroke-width="2.6" fill="none"/>
          <circle class="sparky-collar-tag" cx="178" cy="96" r="3" filter="url(#neonBloom)"/>

          <!-- Head Unit (Bob & Ear Twitch) -->
          <g class="sparky-head-unit">
            <!-- Ears -->
            <g class="sparky-ear-l">
              <path class="ear-shape-l" d="M167 76 Q156 62 165 56 Q174 62 171 74" stroke-width="2" filter="url(#neonBloom)"/>
              <path class="ear-inner-l" d="M167 72 Q161 63 166 60 Q171 63 169 71"/>
            </g>
            <g class="sparky-ear-r">
              <path class="ear-shape-r" d="M189 76 Q200 62 191 56 Q182 62 185 74" stroke-width="2" filter="url(#neonBloom)"/>
              <path class="ear-inner-r" d="M189 72 Q195 63 190 60 Q185 63 187 71"/>
            </g>

            <!-- Face Base -->
            <circle class="sparky-head-sphere" cx="178" cy="80" r="16" stroke-width="2.2" filter="url(#neonBloom)"/>

            <!-- Big Expressive Eyes -->
            <ellipse class="sparky-eye-white-l" cx="172" cy="78" rx="3.5" ry="4.5" fill="#ffffff"/>
            <circle class="sparky-pupil-l" cx="172.5" cy="77.5" r="2.2"/>
            <circle cx="174" cy="76" r="1" fill="#ffffff"/>

            <ellipse class="sparky-eye-white-r" cx="184" cy="78" rx="3.5" ry="4.5" fill="#ffffff"/>
            <circle class="sparky-pupil-r" cx="183.5" cy="77.5" r="2.2"/>
            <circle cx="185" cy="76" r="1" fill="#ffffff"/>

            <!-- Snout & Nose -->
            <ellipse class="sparky-snout" cx="178" cy="86" rx="5.5" ry="3.8"/>
            <polygon class="sparky-nose" points="176.5,85 179.5,85 178,87.5"/>
            <path class="sparky-happy-tongue" d="M176.5,88 Q178,92 179.5,88" stroke="#ff477e" stroke-width="2" fill="#ff477e" stroke-linecap="round"/>

            <!-- Whiskers -->
            <line x1="164" y1="84" x2="157" y2="83" stroke-width="1.2" opacity="0.6"/>
            <line x1="164" y1="87" x2="158" y2="88" stroke-width="1.2" opacity="0.6"/>
            <line x1="192" y1="84" x2="199" y2="83" stroke-width="1.2" opacity="0.6"/>
            <line x1="192" y1="87" x2="198" y2="88" stroke-width="1.2" opacity="0.6"/>
          </g>

          <!-- Magnifying Glass for Investigating (Active in 'thinking') -->
          <g class="sparky-mag-glass">
            <line class="mag-handle" x1="160" y1="104" x2="152" y2="114" stroke-width="2.8" stroke-linecap="round"/>
            <circle class="mag-rim" cx="163" cy="100" r="8" stroke-width="2.4" filter="url(#neonBloom)"/>
            <circle class="mag-lens" cx="163" cy="100" r="6.8" fill="rgba(0, 242, 254, 0.22)"/>
          </g>
        </g>

        <!-- Emerald Sparkle Particles (Active in 'success') -->
        <g class="success-sparkles-group">
          <circle class="sparkle-dot sp-1" cx="80" cy="30" r="2"/>
          <circle class="sparkle-dot sp-2" cx="120" cy="45" r="2.5"/>
          <circle class="sparkle-dot sp-3" cx="140" cy="70" r="1.8"/>
          <circle class="sparkle-dot sp-4" cx="180" cy="35" r="2.2"/>
          <circle class="sparkle-dot sp-5" cx="60" cy="65" r="2"/>
          <circle class="sparkle-dot sp-6" cx="205" cy="95" r="1.8"/>
        </g>
      </svg>
    `;
  }

  /**
   * Builds the interactive Mascot Stage element with a state machine pill and accessibility region.
   * @param {string} initialState - "idle" | "thinking" | "speaking" | "success" | "blocked" | "wave"
   * @param {object} options - Optional configuration { isHero: boolean, speechBubble: boolean }
   */
  function createMascotStage(initialState = "idle", options = {}) {
    const isHero = Boolean(options.isHero);
    const hasBubble = options.speechBubble !== false;

    let bubbleMarkup = "";
    if (hasBubble) {
      const initialGreeting = GREETINGS[Math.floor(Math.random() * GREETINGS.length)];
      bubbleMarkup = `
        <div class="mascot-speech-bubble" id="mascot-speech-bubble" role="status" aria-live="polite">
          <span class="bubble-sparkle">✦</span>
          <span class="bubble-text" id="mascot-bubble-text">${initialGreeting}</span>
        </div>
      `;
    }

    const statePillMarkup = `
      <div class="mascot-state-pill" id="mascot-state-pill" aria-hidden="true">
        <span class="pill-beacon"></span>
        <span class="typing-indicator" id="mascot-typing-indicator">
          <span class="typing-dot dot-1"></span>
          <span class="typing-dot dot-2"></span>
          <span class="typing-dot dot-3"></span>
        </span>
        <span class="pill-label" id="mascot-pill-label">Analyzing your inquiry...</span>
      </div>
    `;

    return `
      <div class="mascot-stage ${isHero ? "mascot-hero-stage" : ""}" data-state="${initialState}" role="region" aria-label="AI and Sparky Assistant">
        <div class="sr-only mascot-live-announcer" aria-live="polite">Assistant is ready.</div>
        ${hasBubble ? bubbleMarkup : ""}
        ${!isHero ? statePillMarkup : ""}
        <div class="mascot-viewport">
          ${getMascotSvgMarkup()}
        </div>
        ${isHero ? '<div class="mascot-hero-caption"><span>AI &amp; Sparky</span> <span class="caption-dot">•</span> <span>Intelligent Support Duo</span></div>' : ""}
      </div>
    `;
  }

  /**
   * Generates a sleek 52px circular glass avatar chip for assistant chat rows.
   * Clean, zero text selection issue, with subtle idle breathing/blink.
   */
  function createChatAvatarChip(character = "ai") {
    const isSparky = character === "sparky";
    return `
      <div class="chat-avatar-chip" title="Ola Support Assistant (AI &amp; Sparky)" aria-hidden="true">
        <svg class="chip-avatar-svg" viewBox="0 0 48 48" fill="none" xmlns="http://www.w3.org/2000/svg">
          <circle cx="24" cy="24" r="22" class="chip-halo-glow"/>
          ${
            isSparky
              ? `<!-- Sparky Chip -->
                <circle cx="24" cy="26" r="14" class="chip-sparky-head"/>
                <path d="M14 18 Q8 8 16 6 Q22 10 20 20" class="chip-sparky-ear"/>
                <path d="M34 18 Q40 8 32 6 Q26 10 28 20" class="chip-sparky-ear"/>
                <circle cx="19" cy="24" r="2" class="chip-pupil"/>
                <circle cx="29" cy="24" r="2" class="chip-pupil"/>
                <ellipse cx="24" cy="30" rx="4" ry="2.5" class="chip-snout"/>
                <polygon points="22.5,29 25.5,29 24,31" class="chip-nose"/>`
              : `<!-- AI Robot Chip -->
                <line x1="24" y1="5" x2="24" y2="12" stroke-width="2" stroke-linecap="round" class="chip-antenna-stem"/>
                <circle cx="24" cy="4" r="3" class="chip-antenna-orb"/>
                <rect x="11" y="12" width="26" height="22" rx="7" class="chip-robot-helm"/>
                <rect x="14" y="15" width="20" height="15" rx="4" class="chip-visor"/>
                <rect x="17" y="19" width="4.5" height="6.5" rx="2.2" class="chip-eye chip-eye-l"/>
                <rect x="26.5" y="19" width="4.5" height="6.5" rx="2.2" class="chip-eye chip-eye-r"/>
                <circle cx="19" cy="21" r="1" fill="#ffffff"/>
                <circle cx="28.5" cy="21" r="1" fill="#ffffff"/>
                <path d="M21 28 Q24 31 27 28" stroke-width="1.8" stroke-linecap="round" fill="none" class="chip-smile"/>`
          }
        </svg>
      </div>
    `;
  }

  /**
   * Sets the mascot state machine state on a given mascot-stage container.
   * @param {Element|string} target - Container element or selector
   * @param {"idle"|"thinking"|"speaking"|"success"|"blocked"|"wave"} state
   * @param {string} customLabel - Optional custom label for thinking state
   */
  function setMascotState(target, state, customLabel) {
    const el = typeof target === "string" ? document.querySelector(target) : target;
    if (!el) return;

    el.setAttribute("data-state", state);

    const labelEl = el.querySelector("#mascot-pill-label");
    if (labelEl && customLabel) {
      labelEl.textContent = customLabel;
    }

    const announcer = el.querySelector(".mascot-live-announcer");
    if (announcer) {
      const descriptions = {
        idle: "Assistant is ready.",
        thinking: customLabel || "Assistant is analyzing policy manuals and ticket data.",
        speaking: "Assistant is answering your inquiry.",
        success: "Inquiry resolved and verified against policy.",
        blocked: "Query triggered system safety guardrail.",
        wave: "Assistant welcomes you."
      };
      announcer.textContent = descriptions[state] || "";
    }
  }

  /**
   * Attaches pointer parallax listeners to a mascot stage.
   * Modifies CSS variables --rx and --ry (clamped to max 8deg).
   */
  function attachPointerParallax(stageEl) {
    if (!stageEl) return;

    let rafId = null;
    let targetRx = 0;
    let targetRy = 0;
    let currentRx = 0;
    let currentRy = 0;

    function onPointerMove(e) {
      const rect = stageEl.getBoundingClientRect();
      const clientX = e.clientX ?? (e.touches && e.touches[0] ? e.touches[0].clientX : rect.left + rect.width / 2);
      const clientY = e.clientY ?? (e.touches && e.touches[0] ? e.touches[0].clientY : rect.top + rect.height / 2);

      const dx = (clientX - (rect.left + rect.width / 2)) / (rect.width / 2);
      const dy = (clientY - (rect.top + rect.height / 2)) / (rect.height / 2);

      targetRx = Math.max(-1, Math.min(1, dx)) * 8; // Max 8deg yaw
      targetRy = Math.max(-1, Math.min(1, dy)) * -6; // Max 6deg pitch

      if (!rafId) {
        rafId = requestAnimationFrame(updateFrame);
      }
    }

    function onPointerLeave() {
      targetRx = 0;
      targetRy = 0;
      if (!rafId) {
        rafId = requestAnimationFrame(updateFrame);
      }
    }

    function updateFrame() {
      currentRx += (targetRx - currentRx) * 0.15;
      currentRy += (targetRy - currentRy) * 0.15;

      stageEl.style.setProperty("--rx", `${currentRx.toFixed(2)}deg`);
      stageEl.style.setProperty("--ry", `${currentRy.toFixed(2)}deg`);
      stageEl.style.setProperty("--eye-x", `${(currentRx * 0.4).toFixed(2)}px`);
      stageEl.style.setProperty("--eye-y", `${(currentRy * -0.4).toFixed(2)}px`);

      if (Math.abs(targetRx - currentRx) > 0.05 || Math.abs(targetRy - currentRy) > 0.05) {
        rafId = requestAnimationFrame(updateFrame);
      } else {
        rafId = null;
      }
    }

    stageEl.addEventListener("mousemove", onPointerMove, { passive: true });
    stageEl.addEventListener("mouseleave", onPointerLeave, { passive: true });
    stageEl.addEventListener("touchmove", onPointerMove, { passive: true });
    stageEl.addEventListener("touchend", onPointerLeave, { passive: true });
  }

  /**
   * Initializes page-wide performance optimizations:
   * - Pauses animations when document is hidden (tab switch)
   * - Sets up click reaction on hero empty-state mascot
   */
  function init() {
    // Visibility change optimization
    document.addEventListener("visibilitychange", () => {
      document.body.classList.toggle("mascots-paused", document.hidden);
    });

    // Wire hero empty-state mascot if present
    const heroStage = document.querySelector(".mascot-hero-stage");
    if (heroStage) {
      attachPointerParallax(heroStage);

      heroStage.addEventListener("click", () => {
        setMascotState(heroStage, "wave");
        const bubble = heroStage.querySelector("#mascot-bubble-text");
        if (bubble) {
          const nextGreeting = GREETINGS[Math.floor(Math.random() * GREETINGS.length)];
          bubble.textContent = nextGreeting;
        }
        setTimeout(() => {
          if (heroStage.getAttribute("data-state") === "wave") {
            setMascotState(heroStage, "idle");
          }
        }, 2800);
      });
    }
  }

  // Auto-init on DOMContentLoaded
  if (typeof document !== "undefined") {
    if (document.readyState === "loading") {
      document.addEventListener("DOMContentLoaded", init);
    } else {
      init();
    }
  }

  return {
    createMascotStage,
    createChatAvatarChip,
    setMascotState,
    attachPointerParallax,
    init
  };
});
