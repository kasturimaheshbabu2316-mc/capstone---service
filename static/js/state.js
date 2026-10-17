/**
 * Ola Support Intelligence — Application State Module (state.js)
 * Manages reactive state, context hygiene (500-char cap, rejected exclusions),
 * and safe localStorage preferences.
 */

function generateSessionId() {
  return "web_" + Math.random().toString(16).substring(2, 10);
}

const STORAGE_KEY = "ola_desk_prefs_v1";

function loadSavedPreferences() {
  const defaults = {
    theme: "light",
    density: "normal",
    reducedMotion: false,
    textSize: "normal",
    showSources: true,
    showReviewBadges: true,
    truncationLength: 300,
  };

  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (raw) {
      const parsed = JSON.parse(raw);
      return { ...defaults, ...parsed };
    }
  } catch {
    // localStorage may be disabled or blocked
  }
  return defaults;
}

function savePreferences(prefs) {
  try {
    // Strictly save only non-sensitive visual and chat preferences
    const safePrefs = {
      theme: prefs.theme,
      density: prefs.density,
      reducedMotion: prefs.reducedMotion,
      textSize: prefs.textSize,
      showSources: prefs.showSources,
      showReviewBadges: prefs.showReviewBadges,
      truncationLength: prefs.truncationLength,
    };
    localStorage.setItem(STORAGE_KEY, JSON.stringify(safePrefs));
  } catch {
    // Silently handle storage failures
  }
}

export class AppState {
  constructor() {
    this.sessionId = generateSessionId();
    this.preferences = loadSavedPreferences();
    this.isProcessing = false;
    this.lastSubmittedQuery = "";
    this.firstQuerySent = false;

    // Visual chat list for UI display
    this.chatMessages = [];

    // Clean conversational context (capped at 500 chars, zero rejected entries)
    this.contextHistory = [];

    // In-memory admin session (never in localStorage)
    this.adminToken = null;
    this.adminAuthenticated = false;
  }

  resetConversation() {
    this.sessionId = generateSessionId();
    this.chatMessages = [];
    this.contextHistory = [];
    this.firstQuerySent = false;
    this.lastSubmittedQuery = "";
  }

  addVisualMessage(message) {
    this.chatMessages.push(message);
  }

  addValidContext(role, content) {
    if (!content || typeof content !== "string") return;
    const capped = content.trim().slice(0, 500);
    this.contextHistory.push({ role, content: capped });
  }

  updatePreference(key, value) {
    this.preferences[key] = value;
    savePreferences(this.preferences);
  }
}

export const state = new AppState();
