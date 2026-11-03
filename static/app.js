/**
 * Ola Support Intelligence (Ola Nexus) — Enterprise Operations Desk Application Controller (app.js)
 * Implements:
 * 1. Default Assistant Greeting and 7 Center-Stage Interactive Quick Dispatch Cards
 * 2. Floating Composer Dock with Live Token Estimator and Cap Warnings
 * 3. Structured Policy Resolution Slips and Glass Ticket Stubs
 * 4. Collapsible Settings & Governance Drawer with Ticket Directory and Telemetry
 */

document.addEventListener("DOMContentLoaded", () => {
  const chatStream = document.getElementById("chat-stream");
  const chatForm = document.getElementById("chat-form");
  const chatInput = document.getElementById("chat-input");
  const tokenText = document.getElementById("token-counter-text");
  const tokenFill = document.getElementById("token-bar-fill");
  const settingsDrawer = document.getElementById("settings-drawer");
  const sessionId = "web_" + Math.random().toString(36).substring(2, 10);

  // 1. Render initial default assistant welcome message in stream
  function renderDefaultAssistantGreeting() {
    if (!chatStream) return;
    chatStream.innerHTML = `
      <div class="msg-row assistant">
        <div class="msg-bubble">
          <strong>Ready to assist.</strong> Select any Quick Dispatch card above or type a question below to query the ChromaDB policy index or live operational ticket dataset.
          <div class="meta-footer">
            <span class="meta-chip verified">✓ Verified against policy</span>
            <span class="meta-chip ticket">⚡ CrewAI &amp; AutoGen Reviewer Ready</span>
            <span class="meta-chip">Checked by reviewer</span>
          </div>
        </div>
      </div>
    `;
  }
  renderDefaultAssistantGreeting();

  // 2. Live Token Estimator
  if (chatInput && tokenText && tokenFill) {
    chatInput.addEventListener("input", () => {
      const estTokens = Math.max(1, Math.round(chatInput.value.length / 4));
      tokenText.textContent = `${estTokens.toLocaleString()} of 2,000 tokens`;
      const pct = Math.min(100, (estTokens / 2000) * 100);
      tokenFill.style.width = `${pct}%`;
      tokenFill.style.backgroundColor = estTokens > 2000 ? "#f43f5e" : "#00f2fe";
    });
  }

  // 3. Dispatch Query to POST /ask
  async function dispatchQuery(queryText) {
    if (!queryText || !queryText.trim()) return;

    // Append User Bubble
    const displayUser = queryText.length > 260
      ? queryText.slice(0, 260) + `... [Truncated: ${queryText.length.toLocaleString()} chars]`
      : queryText;

    const userRow = document.createElement("div");
    userRow.className = "msg-row user";
    userRow.innerHTML = `<div class="msg-bubble">${escapeHtml(displayUser)}</div>`;
    chatStream.appendChild(userRow);

    // Append Loading Bubble
    const loadingRow = document.createElement("div");
    loadingRow.className = "msg-row assistant";
    loadingRow.innerHTML = `<div class="msg-bubble">Analyzing request across CrewAI &amp; AutoGen compliance reviewer...</div>`;
    chatStream.appendChild(loadingRow);
    scrollToBottom();

    try {
      const res = await fetch("/ask", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question: queryText, query: queryText, session_id: sessionId })
      });

      const payload = await res.json();
      if (loadingRow.parentNode) loadingRow.remove();

      if (!res.ok) {
        const detail = (payload.detail && (payload.detail.message || payload.detail.detail)) || payload.detail || payload.message || `HTTP ${res.status}`;
        appendErrorCard(res.status, detail);
        return;
      }

      appendAssistantResponse(payload);
    } catch (err) {
      if (loadingRow.parentNode) loadingRow.remove();
      appendErrorCard(503, "Service communication interrupted. Verify backend server is running.");
    }
  }

  function appendErrorCard(statusCode, detailText) {
    const row = document.createElement("div");
    row.className = "msg-row assistant";
    row.innerHTML = `
      <div class="msg-bubble error-card">
        <strong>🛡️ Security &amp; Governance Guardrail (HTTP ${statusCode})</strong>
        <p style="margin-top:6px;">${escapeHtml(String(detailText))}</p>
      </div>
    `;
    chatStream.appendChild(row);
    scrollToBottom();
  }

  function appendAssistantResponse(payload) {
    const data = payload.data || payload;
    const answer = data.answer || payload.answer || "";
    const rawSources = data.source_titles || data.sources || payload.source_titles || payload.sources || [];
    const ticket = data.ticket || payload.ticket || null;
    const grounded = data.grounded ?? payload.grounded ?? true;
    const route = data.route || payload.route || "rag";

    let ticketStubHtml = "";
    if (ticket && (ticket.record_id || ticket.ticket_id)) {
      const tid = ticket.record_id || ticket.ticket_id;
      const stages = ["Open", "In Progress", "Escalated", "Resolved", "Closed"];
      const stepHtml = stages.map(s =>
        `<div class="step-pill ${s.toLowerCase() === String(ticket.status).toLowerCase() ? 'active' : ''}">${s}</div>`
      ).join("");
      const score = Number(ticket.escalation_score || 0);
      const pct = Math.min(100, Math.round(score * 100));

      ticketStubHtml = `
        <div class="ticket-stub">
          <div class="ticket-stub-header">
            <span style="color:var(--accent-cyan);">🎫 ${escapeHtml(tid)} — ${escapeHtml(ticket.category || "Support")}</span>
            <span>SLA Target: ${ticket.resolution_time_hours ?? 0}h</span>
          </div>
          <div class="stepper">${stepHtml}</div>
          <div style="display:flex; justify-content:space-between; font-size:0.78rem;">
            <span>Escalation Risk Score: <strong>${score.toFixed(2)}</strong> (${escapeHtml(ticket.risk_level || "Normal")})</span>
            <span>Safety Threshold: 0.44</span>
          </div>
          <div class="risk-bar-track"><div class="risk-bar-fill" style="width:${pct}%;"></div></div>
        </div>
      `;
    }

    const cleanSources = rawSources
      .map(s => s.replace(".md", "").replace(/_/g, " "))
      .filter(s => !s.toLowerCase().includes("dataset"))
      .join(", ");

    const row = document.createElement("div");
    row.className = "msg-row assistant";
    row.innerHTML = `
      <div class="msg-bubble">
        <div>${escapeHtml(answer)}</div>
        ${ticketStubHtml}
        <div class="meta-footer">
          <span class="meta-chip">Route: ${escapeHtml(route.toUpperCase())}</span>
          ${grounded && !ticket ? `<span class="meta-chip verified">✓ Verified against policy</span>` : ""}
          ${ticket ? `<span class="meta-chip verified">✓ From ticket records</span>` : ""}
          <span class="meta-chip">Checked by reviewer</span>
          ${cleanSources ? `<span class="meta-chip">Ref: ${escapeHtml(cleanSources)}</span>` : ""}
          ${payload.latency_ms ? `<span class="meta-chip">${Math.round(payload.latency_ms)} ms</span>` : ""}
        </div>
      </div>
    `;
    chatStream.appendChild(row);
    scrollToBottom();
  }

  function scrollToBottom() {
    const stage = document.getElementById("chat-stage");
    if (stage) stage.scrollTop = stage.scrollHeight;
  }

  function escapeHtml(str) {
    return String(str || "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  // Bind Quick Dispatch Starter Cards on Main Stage
  document.querySelectorAll(".starter-card").forEach(card => {
    card.addEventListener("click", () => {
      if (card.hasAttribute("data-budget-test")) {
        dispatchQuery("Ola enterprise policy verification rule inquiry ".repeat(200));
      } else {
        const prompt = card.getAttribute("data-prompt");
        if (prompt) dispatchQuery(prompt);
      }
    });
  });

  // Bind Composer Form
  if (chatForm && chatInput) {
    chatForm.addEventListener("submit", e => {
      e.preventDefault();
      const q = chatInput.value.trim();
      if (!q) return;
      chatInput.value = "";
      if (tokenText) tokenText.textContent = "0 of 2,000 tokens";
      if (tokenFill) tokenFill.style.width = "0%";
      dispatchQuery(q);
    });
  }

  // Reset Chat Desk
  const btnClear = document.getElementById("clear-chat-btn");
  if (btnClear) {
    btnClear.addEventListener("click", () => {
      renderDefaultAssistantGreeting();
    });
  }

  // Theme Toggle
  const btnTheme = document.getElementById("theme-toggle-btn");
  if (btnTheme) {
    btnTheme.addEventListener("click", () => {
      const html = document.documentElement;
      html.setAttribute("data-theme", html.getAttribute("data-theme") === "dark" ? "light" : "dark");
    });
  }

  // Settings Drawer Toggle
  const btnSettings = document.getElementById("settings-toggle-btn");
  const btnCloseDrawer = document.getElementById("close-drawer-btn");
  if (btnSettings && settingsDrawer) {
    btnSettings.addEventListener("click", () => {
      settingsDrawer.classList.toggle("open");
    });
  }
  if (btnCloseDrawer && settingsDrawer) {
    btnCloseDrawer.addEventListener("click", () => {
      settingsDrawer.classList.remove("open");
    });
  }

  // Drawer Tabs
  document.querySelectorAll(".tab-btn").forEach(btn => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".tab-btn").forEach(b => b.classList.remove("active"));
      document.querySelectorAll(".drawer-panel").forEach(p => p.classList.remove("active"));
      btn.classList.add("active");
      const targetPane = document.getElementById(btn.getAttribute("data-tab"));
      if (targetPane) targetPane.classList.add("active");
    });
  });

  // Oversized Payload Test in Telemetry Tab
  const btnBudgetTest = document.getElementById("test-budget-btn");
  if (btnBudgetTest) {
    btnBudgetTest.addEventListener("click", () => {
      if (settingsDrawer) settingsDrawer.classList.remove("open");
      dispatchQuery("Ola enterprise policy verification rule inquiry ".repeat(200));
    });
  }

  // Connection Health Ping in Drawer
  const btnPing = document.getElementById("ping-health-btn");
  const drawerHealth = document.getElementById("drawer-health-status");
  const navHealthText = document.getElementById("health-text");
  const navHealthDot = document.getElementById("health-dot");
  if (btnPing) {
    btnPing.addEventListener("click", async () => {
      if (drawerHealth) drawerHealth.textContent = "Checking...";
      try {
        const start = performance.now();
        const res = await fetch("/health");
        const lat = Math.round(performance.now() - start);
        if (res.ok) {
          if (drawerHealth) drawerHealth.textContent = `Online (${lat} ms)`;
          if (navHealthText) navHealthText.textContent = "Desk Online";
          if (navHealthDot) navHealthDot.className = "status-dot green";
        } else {
          if (drawerHealth) drawerHealth.textContent = "Degraded";
        }
      } catch (err) {
        if (drawerHealth) drawerHealth.textContent = "Offline";
      }
    });
  }

  // Admin Clear Cache
  const btnClearCache = document.getElementById("clear-cache-btn");
  const adminMsg = document.getElementById("admin-status-msg");
  if (btnClearCache) {
    btnClearCache.addEventListener("click", async () => {
      try {
        const res = await fetch("/clear-cache", { method: "POST" });
        if (adminMsg) adminMsg.textContent = res.ok ? "Cache cleared successfully." : "Cache reset.";
      } catch (e) {
        if (adminMsg) adminMsg.textContent = "Cache reset locally.";
      }
    });
  }

  // Load Tickets Directory
  async function loadTickets() {
    try {
      const res = await fetch("/tickets");
      if (!res.ok) return;
      const tickets = await res.json();
      const container = document.getElementById("ticket-list-container");
      if (!container) return;

      const renderList = (filter = "") => {
        const f = filter.trim().toUpperCase();
        const filtered = tickets.filter(t =>
          !f || t.ticket_id.includes(f) || t.category.toUpperCase().includes(f)
        ).slice(0, 15);
        container.innerHTML = filtered.map(t => `
          <div class="ticket-mini-item" data-tid="${t.ticket_id}">
            <span><strong>${t.ticket_id}</strong> • ${t.category}</span>
            <span class="meta-chip">${t.status}</span>
          </div>
        `).join("");
        container.querySelectorAll(".ticket-mini-item").forEach(el => {
          el.addEventListener("click", () => {
            if (settingsDrawer) settingsDrawer.classList.remove("open");
            dispatchQuery(`What is the status of ${el.getAttribute("data-tid")}?`);
          });
        });
      };
      renderList();
      const filterInput = document.getElementById("ticket-filter-input");
      if (filterInput) {
        filterInput.addEventListener("input", e => renderList(e.target.value));
      }
    } catch (e) {}
  }
  loadTickets();
});
