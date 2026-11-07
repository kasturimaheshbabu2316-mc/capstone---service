# Hero Animation CSS

This file contains the extracted CSS styles from the inline styles in `ui/code_chat_hero.html`. Copy this to `static/css/hero-animation.css`.

```css
/* ==============================================================================
   Ola Support Intelligence — Hero Animation Styles
   Three.js Canvas Styles for Code Chat Hero Section
   ============================================================================== */

/* Three.js Hero Canvas Container */
.threejs-hero-canvas {
  position: relative;
  width: 100%;
  height: 100%;
  min-height: 400px;
  background: transparent;
  overflow: hidden;
}

.threejs-hero-canvas canvas {
  display: block;
  width: 100%;
  height: 100%;
}

/* Hero Section Typography */
.hero-title {
  font-size: 2.375rem;
  font-weight: 800;
  letter-spacing: -0.025em;
  line-height: 1.1;
  background: linear-gradient(to right, var(--color-highlight), var(--color-fuchsia-flare), var(--color-amber-flare));
  -webkit-background-clip: text;
  background-clip: text;
  color: transparent;
  filter: drop-shadow(0 0 32px rgba(217, 70, 239, 0.45));
}

.hero-subtitle {
  font-size: 0.9375rem;
  line-height: 1.6;
  color: var(--color-ink-secondary);
  max-width: 38ch;
}

@media (min-width: 640px) {
  .hero-title {
    font-size: 2.875rem;
  }
  
  .hero-subtitle {
    font-size: 1rem;
  }
}

/* Hero Search Composer */
.hero-search-composer {
  width: 100%;
  max-width: 48rem;
  padding: 0 var(--space-sm) var(--space-xxl);
}

.hero-search-glow-border {
  border-radius: var(--radius-card);
  background: linear-gradient(to right, 
    var(--color-highlight), 
    var(--color-fuchsia-flare), 
    var(--color-amber-flare)
  );
  padding: 1.5px;
  box-shadow: 
    0 8px 32px rgba(0, 0, 0, 0.8),
    0 0 28px rgba(0, 242, 254, 0.25),
    0 0 40px rgba(217, 70, 239, 0.2);
}

.hero-search-inner {
  display: flex;
  align-items: center;
  gap: var(--space-sm);
  padding: var(--space-sm);
  border-radius: 15px;
  background: rgba(var(--surface-container-lowest), 0.9);
  -webkit-backdrop-filter: blur(40px);
  backdrop-filter: blur(40px);
}

.hero-search-mode-btn {
  display: inline-flex;
  align-items: center;
  gap: var(--space-xxs);
  padding: var(--space-xs) var(--space-sm);
  border-radius: var(--radius-control);
  background: linear-gradient(to right, 
    rgba(var(--color-highlight), 0.15), 
    rgba(168, 85, 247, 0.20), 
    rgba(var(--color-fuchsia-flare), 0.15)
  );
  border: 1px solid rgba(var(--color-highlight), 0.30);
  color: var(--color-highlight);
  font-weight: 600;
  font-size: 0.8125rem;
  transition: all 200ms ease;
  box-shadow: 0 0 12px rgba(0, 242, 254, 0.2);
  white-space: nowrap;
}

.hero-search-mode-btn:hover {
  background: linear-gradient(to right, 
    rgba(var(--color-highlight), 0.25), 
    rgba(var(--color-fuchsia-flare), 0.25)
  );
}

.hero-search-mode-btn .mode-icon {
  font-size: 0.9375rem;
}

.hero-search-mode-btn .sparkle-icon {
  font-size: 0.8125rem;
  color: var(--color-amber-flare);
  text-shadow: 0 0 6px rgba(252, 211, 77, 0.8);
}

.hero-search-mode-btn .mode-label {
  font-weight: 700;
  background: linear-gradient(to right, #67e8f9, #f9a8d4);
  -webkit-background-clip: text;
  background-clip: text;
  color: transparent;
}

.hero-search-mode-btn .dropdown-icon {
  font-size: 1rem;
  color: var(--color-fuchsia-flare);
}

.hero-search-input {
  flex: 1;
  background: transparent;
  padding: var(--space-xs) var(--space-sm);
  font-size: 0.875rem;
  line-height: 1.4;
  color: var(--color-ink);
  border: none;
  outline: none;
  min-width: 0;
}

.hero-search-input::placeholder {
  color: var(--color-ink-muted);
  opacity: 0.6;
}

.hero-search-submit {
  display: inline-flex;
  align-items: center;
  gap: var(--space-xxs);
  padding: var(--space-xs) var(--space-md);
  border-radius: var(--radius-control);
  background: linear-gradient(to right, 
    var(--color-highlight), 
    var(--color-hyper-cyan), 
    var(--color-fuchsia-flare)
  );
  color: #0F172A;
  font-weight: 700;
  font-size: 0.8125rem;
  box-shadow: 
    0 0 20px rgba(0, 242, 254, 0.6),
    0 0 28px rgba(217, 70, 239, 0.5);
  transition: all 200ms ease;
}

.hero-search-submit:hover {
  box-shadow: 
    0 0 24px rgba(0, 242, 254, 0.8),
    0 0 36px rgba(217, 70, 239, 0.7);
  transform: translateY(-1px);
}

.hero-search-submit:active {
  transform: translateY(0);
}

.hero-search-submit .submit-icon {
  font-size: 1rem;
}

.hero-search-submit .submit-text {
  font-weight: 700;
}

/* Three.js Custom Element Styles */
threejs-scene {
  display: block;
  width: 100%;
  height: 100%;
  min-height: 400px;
}

/* Ensure canvas fills container */
threejs-scene canvas {
  display: block;
  width: 100%;
  height: 100%;
}

/* Responsive adjustments */
@media (max-width: 768px) {
  .threejs-hero-canvas {
    min-height: 300px;
  }
  
  .hero-title {
    font-size: 1.875rem;
  }
  
  .hero-subtitle {
    font-size: 0.875rem;
  }
}
