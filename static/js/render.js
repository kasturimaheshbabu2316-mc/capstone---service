/**
 * Ola Support Intelligence — DOM Rendering Module (render.js)
 * Clean, safe, zero-leak rendering of policy slips, ticket stubs, and alerts.
 * Strictly uses textContent and safe escaping for untrusted server content.
 */

import { maskAllPII } from "./mask.js";

export function escapeHtml(str) {
  if (!str) return "";
  const div = document.createElement("div");
  div.textContent = str;
  return div.innerHTML;
}

export function cleanSourceName(src) {
  if (!src) return "Official policy";
  if (src.toLowerCase().includes("dataset") || src === "Ola Operational Records") {
    return "Ticket records";
  }
  const clean = src.replace(/\.md$/i, "").replace(/_/g, " ");
  const acronyms = ["SLA", "VIP", "KB", "CSAT"];
  return clean
    .split(" ")
    .map((w, idx) => {
      const upper = w.toUpperCase();
      if (acronyms.includes(upper)) return upper;
      if (idx === 0) return w.charAt(0).toUpperCase() + w.slice(1).toLowerCase();
      return w.toLowerCase();
    })
    .join(" ");
}

/**
 * Renders user message bubble (frosted cyan tint, 150-char compact truncation toggle).
 */
export function createUserMessageElement(text, isRejected = false) {
  const wrapper = document.createElement("div");
  wrapper.className = "msg-user-wrapper";

  const chip = document.createElement("div");
  chip.className = "msg-user" + (isRejected ? " rejected" : "");

  const sanitized = maskAllPII(text);
  const isLong = sanitized.length > 150;

  if (isLong) {
    const preview = sanitized.slice(0, 150).trim();
    const estTokens = Math.max(1, Math.round(sanitized.length / 4));

    const previewDiv = document.createElement("div");
    previewDiv.textContent = `${preview}... (truncated, ${sanitized.length} characters, about ${estTokens} tokens)`;
    chip.appendChild(previewDiv);

    const toggleBtn = document.createElement("button");
    toggleBtn.type = "button";
    toggleBtn.className = "btn-expand-msg";
    toggleBtn.textContent = "Show full message";

    const fullContainer = document.createElement("div");
    fullContainer.className = "full-prompt-container";
    fullContainer.style.display = "none";
    fullContainer.textContent = sanitized;

    toggleBtn.addEventListener("click", () => {
      const isHidden = fullContainer.style.display === "none";
      fullContainer.style.display = isHidden ? "block" : "none";
      toggleBtn.textContent = isHidden ? "Hide full message" : "Show full message";
    });

    chip.appendChild(toggleBtn);
    chip.appendChild(fullContainer);
  } else {
    chip.textContent = sanitized;
  }

  wrapper.appendChild(chip);
  return wrapper;
}

/**
 * Renders verified policy slip (paper-white, perforated edge, Source Serif 4).
 */
export function createPolicySlipElement(data, showSources = true, showReviewBadges = true) {
  const container = document.createElement("div");
  container.className = "policy-slip-container";

  const slip = document.createElement("article");
  slip.className = "policy-slip";

  const header = document.createElement("div");
  header.className = "slip-header";
  header.innerHTML = `<span>POLICY RESOLUTION SLIP</span><span class="tabular-nums">#${Math.floor(1000 + Math.random() * 9000)}</span>`;
  slip.appendChild(header);

  const content = document.createElement("div");
  content.className = "slip-content";
  content.textContent = data.answer || "No specific policy guidelines were found for this inquiry. Please rephrase with specific details.";
  slip.appendChild(content);

  // Metadata chips row
  const metaLine = document.createElement("div");
  metaLine.className = "slip-meta-line";

  // Route Chip
  const routeSpan = document.createElement("span");
  routeSpan.className = "chip-badge chip-route";
  routeSpan.textContent = "Route: Core Desk";
  metaLine.appendChild(routeSpan);

  // Optional Ticket ID chip if attached
  if (data.ticket && (data.ticket.ticket_id || data.ticket.record_id)) {
    const tId = data.ticket.ticket_id || data.ticket.record_id;
    const ticketChip = document.createElement("span");
    ticketChip.className = "chip-badge chip-ticket";
    ticketChip.textContent = `Ticket ID: ${tId}`;
    metaLine.appendChild(ticketChip);
  }

  // Verified Policy Badge
  if (data.grounded && !data.ticket) {
    const verSpan = document.createElement("span");
    verSpan.className = "chip-badge verified-mark";
    verSpan.innerHTML = `
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <polyline points="20 6 9 17 4 12"></polyline>
      </svg>
      <span>Verified against policy</span>
    `;
    metaLine.appendChild(verSpan);
  }

  // Reviewer Approval Badge
  if (showReviewBadges && data.review_status && data.review_status.approved) {
    const revSpan = document.createElement("span");
    revSpan.className = "chip-badge reviewer-mark";
    const isRevised = Boolean(data.review_status.revised);
    revSpan.innerHTML = `
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"></path>
      </svg>
      <span>${isRevised ? "Revised by reviewer" : "Checked by reviewer"}</span>
    `;
    metaLine.appendChild(revSpan);
  }

  // Source Titles
  const displaySources = (data.source_titles && data.source_titles.length)
    ? data.source_titles
    : (data.sources || []);

  if (showSources && displaySources.length > 0) {
    const srcNames = displaySources.map(cleanSourceName).join(", ");
    const srcSpan = document.createElement("span");
    srcSpan.className = "chip-badge";
    srcSpan.textContent = `Reference: ${srcNames}`;
    metaLine.appendChild(srcSpan);
  }

  slip.appendChild(metaLine);
  container.appendChild(slip);

  // Perforated tear line
  const perf = document.createElement("div");
  perf.className = "perforated-edge";
  container.appendChild(perf);

  return container;
}

/**
 * Renders physical Glass Ticket Stub Card.
 */
export function createTicketStubElement(ticket) {
  const container = document.createElement("div");
  container.className = "ticket-stub-container";

  const stub = document.createElement("article");
  stub.className = "ticket-stub";

  const ticketId = ticket.ticket_id || ticket.record_id || "TKT-0000";
  const category = ticket.category || "General Support";
  const status = ticket.status || "Open";
  const resHours = ticket.resolution_time_hours || 12.0;
  const ageDays = ticket.days_since_created || 0;
  const escScore = typeof ticket.escalation_score === "number" ? ticket.escalation_score : 0.0;
  const isHighRisk = escScore >= 0.44;

  stub.setAttribute(
    "aria-label",
    `Ticket ${ticketId}, category ${category}, current status is ${status}. Resolution target is ${resHours} hours, age is ${ageDays} days. Escalation risk is ${escScore.toFixed(2)}, ${isHighRisk ? "exceeding safety threshold" : "within standard limits"}.`
  );

  // 1. Header
  const header = document.createElement("div");
  header.className = "stub-header";
  header.innerHTML = `
    <span class="stub-id tabular-nums">${escapeHtml(ticketId)}</span>
    <span class="stub-category">${escapeHtml(category)}</span>
  `;
  stub.appendChild(header);

  // 2. 5-Step Horizontal Status Progression Track
  const track = document.createElement("div");
  track.className = "status-track";

  const stages = ["Open", "In Progress", "Escalated", "Resolved", "Closed"];
  const currentIdx = stages.findIndex(s => s.toLowerCase() === status.toLowerCase());
  const activeIdx = currentIdx >= 0 ? currentIdx : 0;

  stages.forEach((stageName, idx) => {
    const step = document.createElement("div");
    let stateClass = "";
    if (idx < activeIdx) stateClass = " passed";
    else if (idx === activeIdx) stateClass = " lit";
    step.className = `track-step${stateClass}`;

    step.innerHTML = `
      <div class="step-marker"></div>
      <div class="step-name">${stageName}</div>
    `;
    track.appendChild(step);
  });
  stub.appendChild(track);

  // 3. Metrics Grid
  const metrics = document.createElement("div");
  metrics.className = "stub-metrics";
  metrics.innerHTML = `
    <div class="metric-card">
      <div class="metric-label">Time to resolve</div>
      <div class="metric-value tabular-nums">${resHours} h</div>
    </div>
    <div class="metric-card">
      <div class="metric-label">Ticket age</div>
      <div class="metric-value tabular-nums">${ageDays} d</div>
    </div>
    <div class="metric-card">
      <div class="metric-label">Priority risk</div>
      <div class="metric-value">${isHighRisk ? "High risk" : "Standard"}</div>
    </div>
  `;
  stub.appendChild(metrics);

  // 4. Escalation Risk Gauge with 0.44 threshold
  const meterBox = document.createElement("div");
  meterBox.className = "meter-box";

  const meterHeader = document.createElement("div");
  meterHeader.className = "meter-header";
  meterHeader.innerHTML = `
    <span>Escalation Risk Gauge</span>
    <span class="tabular-nums" style="font-weight:700;">${escScore.toFixed(2)}</span>
  `;
  meterBox.appendChild(meterHeader);

  const gauge = document.createElement("div");
  gauge.className = "meter-gauge";

  // Threshold indicator line at 44%
  const threshLine = document.createElement("div");
  threshLine.className = "meter-threshold-line";
  threshLine.style.left = "44%";
  threshLine.title = "Escalation threshold (0.44)";
  gauge.appendChild(threshLine);

  // 10 Segments
  const filledCount = Math.round(escScore * 10);
  for (let i = 0; i < 10; i++) {
    const block = document.createElement("div");
    let blockClass = "gauge-block";
    if (i < filledCount) {
      blockClass += isHighRisk ? " alert" : " filled";
    }
    block.className = blockClass;
    gauge.appendChild(block);
  }
  meterBox.appendChild(gauge);

  const threshLabel = document.createElement("div");
  threshLabel.className = "meter-threshold-label";
  threshLabel.textContent = `Safety threshold at 0.44 ${isHighRisk ? "• Exceeded" : "• Nominal"}`;
  meterBox.appendChild(threshLabel);

  stub.appendChild(meterBox);

  // 5. Verification & Source Tags
  const metaLine = document.createElement("div");
  metaLine.className = "slip-meta-line";
  metaLine.innerHTML = `
    <span class="chip-badge">From ticket records</span>
    <span class="chip-badge reviewer-mark">
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"></path>
      </svg>
      <span>Checked by reviewer</span>
    </span>
  `;
  stub.appendChild(metaLine);

  // 6. Recommendation Banner
  const recBanner = document.createElement("div");
  recBanner.className = `recommendation-banner ${isHighRisk ? "escalate" : "standard"}`;
  recBanner.textContent = isHighRisk
    ? "Recommendation: Escalate to a senior agent immediately"
    : "Recommendation: Follow standard resolution timeline";
  stub.appendChild(recBanner);

  container.appendChild(stub);

  // Perforated Tear Line
  const perf = document.createElement("div");
  perf.className = "perforated-edge";
  container.appendChild(perf);

  return container;
}

/**
 * Renders Guardrail Alert Card for HTTP 400 (Prompt Injection) & 413 (Payload Budget).
 */
export function createAlertSlipElement(title, message, statusCode) {
  const container = document.createElement("div");
  container.className = "alert-slip-container";

  const slip = document.createElement("div");
  slip.className = "alert-slip";

  const headerRow = document.createElement("div");
  headerRow.className = "alert-header-row";

  const titleEl = document.createElement("div");
  titleEl.className = "alert-title";
  titleEl.innerHTML = `
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
      <circle cx="12" cy="12" r="10"></circle>
      <line x1="12" y1="8" x2="12" y2="12"></line>
      <line x1="12" y1="16" x2="12.01" y2="16"></line>
    </svg>
    <span>${escapeHtml(title)}</span>
  `;
  headerRow.appendChild(titleEl);

  const codeBadge = document.createElement("span");
  codeBadge.className = "alert-code-badge tabular-nums";
  codeBadge.textContent = statusCode === 400
    ? "HTTP 400 - Guardrail Block"
    : statusCode === 413
    ? "HTTP 413 - Payload Budget Exceeded"
    : `HTTP ${statusCode}`;
  headerRow.appendChild(codeBadge);

  slip.appendChild(headerRow);

  const msgEl = document.createElement("div");
  msgEl.className = "alert-message";
  msgEl.textContent = message;
  slip.appendChild(msgEl);

  container.appendChild(slip);
  return container;
}

/**
 * Creates waiting placeholder.
 */
export function createWaitingElement(isWaking = false) {
  const el = document.createElement("div");
  el.className = "msg-waiting";
  el.setAttribute("aria-live", "polite");

  const spinner = document.createElement("div");
  spinner.className = "waiting-spinner";
  el.appendChild(spinner);

  const text = document.createElement("span");
  text.textContent = isWaking
    ? "Waking up the support desk, this can take up to a minute..."
    : "Looking up official guidelines and records...";
  el.appendChild(text);

  return el;
}
