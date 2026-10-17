/**
 * Ola Support Intelligence — Main Application Controller (main.js)
 * Orchestrates user interactions, live token budgeting, API dispatches,
 * and seamless scroll choreography.
 */

import { state } from "./state.js";
import { checkHealth, sendQuery } from "./api.js";
import { initSettingsSheet } from "./settings.js";
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
  const composerInput = document.getElementById("composerInput");
  const composerForm = document.getElementById("composerForm");
  const btnSend = document.getElementById("btnSend");
  const chatMessages = document.getElementById("chatMessages");
  const welcomeBox = document.getElementById("welcomeBox");

  // Initialize Settings Drawer
  initSettingsSheet((query) => {
    handleUserDispatch(query);
  });

  // Suggestion Chips Click
  document.querySelectorAll(".suggestion-chip").forEach(chip => {
    chip.addEventListener("click", () => {
      const q = chip.getAttribute("data-query");
      if (q) handleUserDispatch(q);
    });
  });

  // Composer Textarea Auto-Resize & Token Gauge
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

  // Form Submit Listener
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
 * Textarea vertical auto-sizing up to max height
 */
function autoResizeTextarea(textarea) {
  textarea.style.height = "auto";
  const newHeight = Math.min(160, Math.max(36, textarea.scrollHeight));
  textarea.style.height = `${newHeight}px`;
}

/**
 * Live token meter listener (characters / 4 heuristic)
 */
function updateTokenBudgetGauge(text) {
  const gaugeProgress = document.getElementById("tokenGaugeProgress");
  const gaugeCount = document.getElementById("tokenGaugeCount");
  const gaugeWarning = document.getElementById("tokenGaugeWarning");
  const btnSend = document.getElementById("btnSend");

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

  const chatContainer = document.getElementById("chatMessages");
  const welcomeBox = document.getElementById("welcomeBox");
  const btnSend = document.getElementById("btnSend");

  // Prevent duplicate double submission within same run
  if (state.lastSubmittedQuery === queryText && state.isProcessing) {
    return;
  }

  state.isProcessing = true;
  state.lastSubmittedQuery = queryText;
  if (btnSend) btnSend.disabled = true;

  // Hide welcome box on first query
  if (!state.firstQuerySent) {
    state.firstQuerySent = true;
    if (welcomeBox) welcomeBox.style.display = "none";
  }

  // Create conversational turn container
  const turnEl = document.createElement("div");
  turnEl.className = "chat-turn";

  // 1. Render User Message Chip
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

    // Render Alert Slip
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
 * Polls backend health on page load with up to 90s retries for cold start
 */
async function pollInitialHealth() {
  const headerChip = document.getElementById("headerStatusText");
  const headerDot = document.getElementById("headerStatusDot");

  const h = await checkHealth();
  if (headerChip) headerChip.textContent = h.status;
  if (headerDot) {
    headerDot.className = "status-dot " + (h.online ? "online" : h.waking ? "waking" : "offline");
  }

  // If cold-starting (Render free tier), retry every 5s up to 90s
  if (h.waking || !h.online) {
    let elapsed = 0;
    const interval = setInterval(async () => {
      elapsed += 5;
      const retryHealth = await checkHealth();
      if (retryHealth.online || elapsed >= 90) {
        clearInterval(interval);
        if (headerChip) headerChip.textContent = retryHealth.status;
        if (headerDot) {
          headerDot.className = "status-dot " + (retryHealth.online ? "online" : "offline");
        }
      }
    }, 5000);
  }
}
