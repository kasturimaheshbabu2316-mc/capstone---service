/**
 * Ola Support Intelligence — Main Application Controller (main.js)
 * Enterprise Glassmorphism Architecture:
 * 1. Default Welcome Hero & Interactive Starter Cards on Center Stage
 * 2. Sticky Glass Top Navbar with Segmented Pill Switcher & Theme Toggle
 * 3. Collapsible Glass Settings Drawer & Token-Budgeted Composer
 */

import { state } from "./state.js";
import { checkHealth, sendQuery } from "./api.js";
import { initSettingsSheet, openSettingsSheet } from "./settings.js";
import {
  createUserMessageElement,
  createPolicySlipElement,
  createTicketStubElement,
  createAlertSlipElement,
  createWaitingElement,
} from "./render.js";

const MAX_BUDGET_CAP = 2000;

document.addEventListener("DOMContentLoaded", () => {
  initApp();
});

function initApp() {
  const composerInput = document.getElementById("composerInput") || document.getElementById("chat-input");
  const composerForm = document.getElementById("composerForm") || document.getElementById("chat-form");
  const btnSend = document.getElementById("btnSend") || document.getElementById("send-btn");
  const welcomeBox = document.getElementById("welcomeBox") || document.getElementById("chat-empty-state");

  // Initialize Settings Drawer
  initSettingsSheet((query) => {
    handleUserDispatch(query);
  });

  // Wire up Top Navbar Segmented Switcher
  initNavSwitcher();

  // Wire up Theme Toggle in Navbar
  initThemeToggle();

  // Wire up 2x3 Interactive Starter Cards on Center Stage
  initStarterCards();

  // Composer Textarea Auto-Resize & Live Token Budget Gauge
  if (composerInput) {
    composerInput.addEventListener("input", () => {
      autoResizeTextarea(composerInput);
      updateTokenBudgetGauge(composerInput.value);
    });

    composerInput.addEventListener("keydown", (e) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        composerForm.dispatchEvent(new Event("submit", { cancelable: true }));
      }
    });
  }

  // Composer Form Submit Listener
  if (composerForm) {
    composerForm.addEventListener("submit", (e) => {
      e.preventDefault();
      const rawText = composerInput.value.trim();
      if (!rawText || state.isProcessing) return;

      const tokens = Math.max(1, Math.round(rawText.length / 4));
      if (tokens > MAX_BUDGET_CAP) return;

      composerInput.value = "";
      autoResizeTextarea(composerInput);
      updateTokenBudgetGauge("");
      handleUserDispatch(rawText);
    });
  }

  // Initial Background Health Check
  pollInitialHealth();
}

/**
 * Connects 2x3 Interactive Quick-Action Starter Cards on Center Stage.
 * Clicking immediately dispatches query to /ask without opening settings.
 */
function initStarterCards() {
  const cards = document.querySelectorAll(".starter-card, .glass-card-interactive");
  cards.forEach(card => {
    card.addEventListener("click", () => {
      const q = card.getAttribute("data-query");
      if (q && !state.isProcessing) {
        handleUserDispatch(q);
      }
    });
  });
}

/**
 * Top Navbar Segmented Pill Switcher (Chat Desk | Ticket Directory | Policy Explorer)
 */
function initNavSwitcher() {
  const pillChat = document.getElementById("pillChatDesk") || document.getElementById("pill-chat");
  const pillTickets = document.getElementById("pillTicketDir") || document.getElementById("pill-directory");
  const pillPolicy = document.getElementById("pillPolicyExp") || document.getElementById("pill-policies");
  const pills = [pillChat, pillTickets, pillPolicy].filter(Boolean);

  function setActivePill(activePill) {
    pills.forEach(p => p.classList.remove("active"));
    if (activePill) activePill.classList.add("active");
  }

  if (pillChat) {
    pillChat.addEventListener("click", () => {
      setActivePill(pillChat);
      window.scrollTo({ top: 0, behavior: "smooth" });
    });
  }

  if (pillTickets) {
    pillTickets.addEventListener("click", () => {
      setActivePill(pillTickets);
      openSettingsSheet("tickets");
    });
  }

  if (pillPolicy) {
    pillPolicy.addEventListener("click", () => {
      setActivePill(pillPolicy);
      const composer = document.getElementById("composerInput");
      if (composer) {
        composer.focus();
        composer.placeholder = "Search policy guidelines (e.g. cancellation refund, Sev-1 SLA)...";
      }
    });
  }
}

/**
 * Navbar Theme Toggle (Dark Slate-Navy vs Frosted Light)
 */
function initThemeToggle() {
  const btnToggle = document.getElementById("btnThemeToggle") || document.getElementById("theme-toggle-btn");
  if (!btnToggle) return;

  btnToggle.addEventListener("click", () => {
    const current = document.documentElement.getAttribute("data-theme") || "dark";
    const next = current === "dark" ? "light" : "dark";
    state.updatePreference("theme", next);
    document.documentElement.setAttribute("data-theme", next);

    const prefSelect = document.getElementById("prefTheme");
    if (prefSelect) prefSelect.value = next;
  });
}

/**
 * Textarea vertical auto-sizing up to max height
 */
function autoResizeTextarea(textarea) {
  textarea.style.height = "auto";
  const newHeight = Math.min(160, Math.max(38, textarea.scrollHeight));
  textarea.style.height = `${newHeight}px`;
}

/**
 * Live token meter listener (characters / 4 heuristic)
 */
function updateTokenBudgetGauge(text) {
  const gaugeProgress = document.getElementById("tokenGaugeProgress") || document.getElementById("token-bar-fill");
  const gaugeCount = document.getElementById("tokenGaugeCount") || document.getElementById("token-counter-text");
  const gaugeWarning = document.getElementById("tokenGaugeWarning");
  const btnSend = document.getElementById("btnSend") || document.getElementById("send-btn");

  const charCount = text ? text.length : 0;
  const estimatedTokens = charCount > 0 ? Math.max(1, Math.round(charCount / 4)) : 0;
  const pct = Math.min(100, (estimatedTokens / MAX_BUDGET_CAP) * 100);

  if (gaugeProgress) {
    gaugeProgress.style.width = `${pct}%`;
    gaugeProgress.classList.toggle("limit-near", estimatedTokens >= 1600 && estimatedTokens <= MAX_BUDGET_CAP);
    gaugeProgress.classList.toggle("limit-exceeded", estimatedTokens > MAX_BUDGET_CAP);
  }

  if (gaugeCount) {
    gaugeCount.textContent = `${estimatedTokens.toLocaleString()} of ${MAX_BUDGET_CAP.toLocaleString()} tokens`;
  }

  if (estimatedTokens > MAX_BUDGET_CAP) {
    if (gaugeWarning) gaugeWarning.textContent = "Shorten your question to under 2,000 tokens.";
    if (btnSend) btnSend.disabled = true;
  } else {
    if (gaugeWarning) gaugeWarning.textContent = "";
    if (btnSend) btnSend.disabled = estimatedTokens === 0 || state.isProcessing;
  }
}

/**
 * Dispatches query through unified pipeline with duplicate click debounce and history hygiene.
 */
async function handleUserDispatch(queryText) {
  if (!queryText || state.isProcessing) return;

  const chatContainer = document.getElementById("chatMessages") || document.getElementById("chat-stream");
  const welcomeBox = document.getElementById("welcomeBox") || document.getElementById("chat-empty-state");
  const btnSend = document.getElementById("btnSend") || document.getElementById("send-btn");

  // Prevent duplicate double submission within same run
  if (state.lastSubmittedQuery === queryText && state.isProcessing) {
    return;
  }

  state.isProcessing = true;
  state.lastSubmittedQuery = queryText;
  if (btnSend) btnSend.disabled = true;

  // Smoothly hide welcome hero card on first query
  if (!state.firstQuerySent) {
    state.firstQuerySent = true;
    if (welcomeBox) welcomeBox.style.display = "none";
  }

  // Create conversational turn container
  const turnEl = document.createElement("div");
  turnEl.className = "chat-turn";

  // 1. Render User Message Bubble
  const userChip = createUserMessageElement(queryText);
  turnEl.appendChild(userChip);
  chatContainer.appendChild(turnEl);
  scrollToBottom();

  // 2. Render Waiting Placeholder
  const waitingEl = createWaitingElement(false);
  turnEl.appendChild(waitingEl);
  scrollToBottom();

  // 3. Dispatch to API
  const result = await sendQuery(queryText, state.sessionId);

  // Remove waiting element
  if (waitingEl.parentNode) {
    waitingEl.parentNode.removeChild(waitingEl);
  }

  // 4. Handle Result with Strict History Hygiene
  if (result.is_error) {
    // Mark user message as rejected visually
    const userChipInner = userChip.querySelector(".msg-user");
    if (userChipInner) userChipInner.classList.add("rejected");

    // Render Alert Card
    const alertSlip = createAlertSlipElement(
      result.title || "Service Notice",
      result.message || "Something went wrong on our side. Try again in a moment.",
      result.status_code || 500
    );
    turnEl.appendChild(alertSlip);

    // Save in visual chat history for export
    state.addVisualMessage({
      role: "user",
      content: queryText,
      rejected: true,
    });
    state.addVisualMessage({
      role: "assistant",
      content: result.message,
      is_error: true,
    });

    // NOTE: Rejected turns are NEVER added to state.contextHistory!
  } else {
    // Determine whether to display a Ticket Stub or Policy Slip
    const ticketObj = result.ticket || (result.data && result.data.ticket);
    let answerText = "";

    if (ticketObj) {
      const ticketStub = createTicketStubElement(ticketObj);
      turnEl.appendChild(ticketStub);
      answerText = `Ticket ${ticketObj.ticket_id || ticketObj.record_id}: Status ${ticketObj.status}.`;
    } else {
      const policySlip = createPolicySlipElement(
        result.data || result,
        state.preferences.showSources,
        state.preferences.showReviewBadges
      );
      turnEl.appendChild(policySlip);
      answerText = (result.data && result.data.answer) || result.answer || "";
    }

    // Save in visual chat history
    state.addVisualMessage({
      role: "user",
      content: queryText,
      rejected: false,
    });
    state.addVisualMessage({
      role: "assistant",
      content: answerText,
      is_error: false,
    });

    // Context Hygiene: Add to conversation memory context capped at 500 chars
    state.addValidContext("user", queryText);
    state.addValidContext("assistant", answerText);
  }

  state.isProcessing = false;
  state.lastSubmittedQuery = "";
  if (btnSend) btnSend.disabled = false;
  scrollToBottom();
}

/**
 * Smoothly scrolls conversation view to latest message and answer
 */
function scrollToBottom() {
  window.requestAnimationFrame(() => {
    window.scrollTo({
      top: document.body.scrollHeight,
      behavior: state.preferences.reducedMotion ? "auto" : "smooth",
    });
  });
}

/**
 * Polls backend health on page load
 */
async function pollInitialHealth() {
  const headerChip = document.getElementById("headerStatusText") || document.getElementById("health-text");
  const headerDot = document.getElementById("headerStatusDot") || document.getElementById("health-dot");

  const h = await checkHealth();
  if (headerChip) headerChip.textContent = h.online ? "System Active" : h.status;
  if (headerDot) {
    headerDot.className = "status-dot " + (h.online ? "online" : h.waking ? "waking" : "offline");
  }

  if (h.waking || !h.online) {
    let elapsed = 0;
    const interval = setInterval(async () => {
      elapsed += 5;
      const retryHealth = await checkHealth();
      if (retryHealth.online || elapsed >= 90) {
        clearInterval(interval);
        if (headerChip) headerChip.textContent = retryHealth.online ? "System Active" : retryHealth.status;
        if (headerDot) {
          headerDot.className = "status-dot " + (retryHealth.online ? "online" : "offline");
        }
      }
    }, 5000);
  }
}
