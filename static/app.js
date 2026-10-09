/**
 * Ola Nexus Support Agent — Interactive Glassmorphism Client
 * Supports both Live WebSocket (/ws/chat) and HTTP REST (/ask) protocols.
 */

document.addEventListener('DOMContentLoaded', () => {
  // Elements
  const chatMessages = document.getElementById('chatMessages');
  const chatForm = document.getElementById('chatForm');
  const queryInput = document.getElementById('queryInput');
  const tokenCountEl = document.getElementById('tokenCount');
  const tokenIndicatorEl = document.getElementById('tokenIndicator');
  const btnSend = document.getElementById('btnSend');

  // HUD Elements
  const metricTrace = document.getElementById('metricTrace');
  const metricLatency = document.getElementById('metricLatency');
  const metricSession = document.getElementById('metricSession');
  const metricCache = document.getElementById('metricCache');
  const cacheBadge = document.getElementById('cacheBadge');
  const riskBadge = document.getElementById('riskBadge');
  const gaugeFill = document.getElementById('gaugeFill');
  const scoreVal = document.getElementById('scoreVal');
  const ticketVal = document.getElementById('ticketVal');
  const groundedBadge = document.getElementById('groundedBadge');
  const sourcesList = document.getElementById('sourcesList');

  // Modals
  const modalTickets = document.getElementById('modalTickets');
  const modalIngest = document.getElementById('modalIngest');
  const modalSpecs = document.getElementById('modalSpecs');

  const btnOpenTickets = document.getElementById('btnOpenTickets');
  const btnCloseTickets = document.getElementById('btnCloseTickets');
  const btnOpenIngest = document.getElementById('btnOpenIngest');
  const btnCloseIngest = document.getElementById('btnCloseIngest');
  const btnCancelIngest = document.getElementById('btnCancelIngest');
  const btnOpenSpecs = document.getElementById('btnOpenSpecs');
  const btnCloseSpecs = document.getElementById('btnCloseSpecs');

  const ticketsTbody = document.getElementById('ticketsTbody');
  const ticketSearchInput = document.getElementById('ticketSearchInput');
  const statusFilter = document.getElementById('statusFilter');

  const ingestForm = document.getElementById('ingestForm');
  const docIdInput = document.getElementById('docIdInput');
  const docTextInput = document.getElementById('docTextInput');
  const ingestResult = document.getElementById('ingestResult');

  // Session ID
  let currentSessionId = 'session_' + Math.random().toString(36).substring(2, 9);
  metricSession.textContent = currentSessionId;

  // WebSocket Connection
  let ws = null;
  let wsConnected = false;

  function initWebSocket() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws/chat`;

    try {
      ws = new WebSocket(wsUrl);

      ws.onopen = () => {
        wsConnected = true;
      };

      ws.onmessage = (event) => {
        try {
          const payload = JSON.parse(event.data);
          handleWebSocketMessage(payload);
        } catch (e) {
          console.error('Failed to parse WebSocket JSON:', e);
        }
      };

      ws.onclose = () => {
        wsConnected = false;
        // Auto-reconnect after 2 seconds
        setTimeout(initWebSocket, 2000);
      };

      ws.onerror = () => {
        wsConnected = false;
      };
    } catch (e) {
      console.warn('WebSocket init error, falling back to HTTP:', e);
      wsConnected = false;
    }
  }

  initWebSocket();

  // Token count estimator
  queryInput.addEventListener('input', () => {
    const text = queryInput.value;
    const estTokens = Math.ceil(text.length / 4);
    tokenCountEl.textContent = estTokens;

    if (estTokens > 2000) {
      tokenIndicatorEl.className = 'token-budget-indicator danger';
    } else if (estTokens > 1600) {
      tokenIndicatorEl.className = 'token-budget-indicator warning';
    } else {
      tokenIndicatorEl.className = 'token-budget-indicator';
    }
  });

  // Prompt chips click
  document.querySelectorAll('.prompt-chip').forEach(chip => {
    chip.addEventListener('click', () => {
      let q = chip.getAttribute('data-query');
      if (q === 'BUDGET_CAP_TEST') {
        q = 'Ola enterprise policy verification rule inquiry '.repeat(200);
      }
      queryInput.value = q;
      queryInput.dispatchEvent(new Event('input'));
      chatForm.dispatchEvent(new Event('submit'));
    });
  });

  // Chat Submission
  chatForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const query = queryInput.value.trim();
    if (!query) return;

    const protocolChoice = document.querySelector('input[name="protocol"]:checked').value;

    // Append User Message to UI
    appendUserMessage(query);
    queryInput.value = '';
    queryInput.dispatchEvent(new Event('input'));

    // Loading indicator
    const loadingRow = appendLoadingIndicator();

    if (protocolChoice === 'ws' && wsConnected && ws.readyState === WebSocket.OPEN) {
      // Send via WebSocket
      ws.send(query);
    } else {
      // Send via HTTP REST
      await sendHttpRequest(query, loadingRow);
    }
  });

  // HTTP Request Handler
  async function sendHttpRequest(query, loadingRow) {
    const t0 = performance.now();
    try {
      const resp = await fetch('/ask', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          query: query,
          session_id: currentSessionId
        })
      });

      const t1 = performance.now();
      const elapsed = (t1 - t0).toFixed(1);

      loadingRow.remove();

      if (!resp.ok) {
        const errJson = await resp.json().catch(() => ({ detail: 'Unknown error' }));
        appendErrorMessage(errJson.detail || `HTTP Error ${resp.status}`, resp.status);
        updateHudForError(resp.status, elapsed);
        return;
      }

      const resData = await resp.json();
      appendAssistantMessage(resData.data, resData.trace_id, resData.latency_ms);
      updateHud(resData);

    } catch (err) {
      loadingRow.remove();
      appendErrorMessage(err.message || 'Network error occurred', 500);
    }
  }

  // WebSocket Message Handler
  function handleWebSocketMessage(msg) {
    const loading = document.getElementById('activeLoadingBubble');
    if (loading) loading.remove();

    if (msg.type === 'error') {
      appendErrorMessage(msg.detail, 400);
      updateHudForError(400, msg.latency_ms || 0.0);
      return;
    }

    if (msg.type === 'response') {
      const data = msg.data;
      appendAssistantMessage(data, 'ws-stream-' + Math.random().toString(36).substring(2, 7), msg.latency_ms);
      updateHud({
        trace_id: 'ws-stream',
        data: data,
        latency_ms: msg.latency_ms,
        cache_hit: false,
        guardrail_flags: {}
      });
    }
  }

  // UI Appends
  function appendUserMessage(text) {
    const row = document.createElement('div');
    row.className = 'message-row user';
    row.innerHTML = `
      <div class="avatar-box user-avatar">YOU</div>
      <div class="bubble-card user-bubble">
        <div class="bubble-header">
          <span class="sender-name">User</span>
          <span class="timestamp-tag">${new Date().toLocaleTimeString()}</span>
        </div>
        <div class="bubble-content">
          <p>${escapeHtml(text)}</p>
        </div>
      </div>
    `;
    chatMessages.appendChild(row);
    scrollToBottom();
  }

  function appendLoadingIndicator() {
    const row = document.createElement('div');
    row.className = 'message-row assistant';
    row.id = 'activeLoadingBubble';
    row.innerHTML = `
      <div class="avatar-box ai-avatar">
        <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 14 14"/></svg>
      </div>
      <div class="bubble-card ai-bubble">
        <div class="bubble-header">
          <span class="sender-name">Ola Nexus Intelligence</span>
          <span class="timestamp-tag">Processing Crew...</span>
        </div>
        <div class="bubble-content">
          <p class="loading-subtext">
            Evaluating policy retrieval, escalation scoring, and AutoGen compliance review...
          </p>
        </div>
      </div>
    `;
    chatMessages.appendChild(row);
    scrollToBottom();
    return row;
  }

  function appendAssistantMessage(data, traceId, latencyMs) {
    const row = document.createElement('div');
    row.className = 'message-row assistant';

    let metaHtml = '';
    if (data.ticket_id) {
      metaHtml += `<span class="meta-pill ticket">Ticket: ${data.ticket_id}</span>`;
      metaHtml += `<span class="meta-pill">Escalation Score: ${Number(data.escalation_score).toFixed(4)}</span>`;
    }
    if (data.grounded) {
      metaHtml += `<span class="meta-pill grounded">✓ Grounded Policy</span>`;
    }
    if (data.sources && data.sources.length) {
      metaHtml += `<span class="meta-pill">Sources: ${data.sources.join(', ')}</span>`;
    }
    if (latencyMs) {
      metaHtml += `<span class="meta-pill">${latencyMs} ms</span>`;
    }

    row.innerHTML = `
      <div class="avatar-box ai-avatar">
        <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/></svg>
      </div>
      <div class="bubble-card ai-bubble">
        <div class="bubble-header">
          <span class="sender-name">Ola Nexus Intelligence</span>
          <span class="timestamp-tag">${new Date().toLocaleTimeString()}</span>
        </div>
        <div class="bubble-content">
          <p>${formatMarkdown(data.answer)}</p>
          ${metaHtml ? `<div class="bubble-meta-footer">${metaHtml}</div>` : ''}
        </div>
      </div>
    `;
    chatMessages.appendChild(row);
    scrollToBottom();
  }

  function appendErrorMessage(errorDetail, statusCode) {
    const row = document.createElement('div');
    row.className = 'message-row assistant';
    row.innerHTML = `
      <div class="avatar-box ai-avatar danger-border">
        <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>
      </div>
      <div class="bubble-card ai-bubble danger-card">
        <div class="bubble-header">
          <span class="sender-name danger-text">Security / Governance Guardrail Triggered</span>
          <span class="timestamp-tag">Status ${statusCode}</span>
        </div>
        <div class="bubble-content">
          <p class="error-detail-text">${escapeHtml(errorDetail)}</p>
          <div class="bubble-meta-footer">
            <span class="meta-pill blocked">BLOCKED BY GATEWAY</span>
            <span class="meta-pill">HTTP ${statusCode}</span>
          </div>
        </div>
      </div>
    `;
    chatMessages.appendChild(row);
    scrollToBottom();
  }

  // HUD Update
  function updateHud(res) {
    metricTrace.textContent = res.trace_id || '--';
    metricLatency.textContent = (res.latency_ms || 0.0) + ' ms';
    metricSession.textContent = currentSessionId;

    if (res.cache_hit) {
      metricCache.textContent = 'CACHE HIT (0 LLM Calls)';
      cacheBadge.textContent = 'CACHE HIT';
      cacheBadge.className = 'hud-badge badge-hit';
    } else {
      metricCache.textContent = 'CACHE MISS (Evaluated)';
      cacheBadge.textContent = 'CACHE MISS';
      cacheBadge.className = 'hud-badge badge-miss';
    }

    const data = res.data;
    if (data) {
      // Escalation Risk Score
      const esc = data.escalation_score || 0.0;
      scoreVal.textContent = esc.toFixed(4);
      ticketVal.textContent = data.ticket_id || 'None';

      const pct = Math.min(100, Math.round(esc * 100));
      gaugeFill.style.width = pct + '%';

      if (esc >= 0.4400) {
        riskBadge.textContent = 'HIGH RISK';
        riskBadge.className = 'hud-badge badge-danger';
      } else if (esc > 0.2) {
        riskBadge.textContent = 'ELEVATED';
        riskBadge.className = 'hud-badge badge-warn';
      } else {
        riskBadge.textContent = data.ticket_id ? 'NORMAL' : 'N/A';
        riskBadge.className = data.ticket_id ? 'hud-badge badge-pass' : 'hud-badge badge-neutral';
      }

      // Groundedness
      if (data.grounded) {
        groundedBadge.textContent = 'GROUNDED';
        groundedBadge.className = 'hud-badge badge-pass';
      } else {
        groundedBadge.textContent = 'REFUSAL / N/A';
        groundedBadge.className = 'hud-badge badge-warn';
      }

      // Sources
      sourcesList.innerHTML = '';
      if (data.sources && data.sources.length) {
        data.sources.forEach(src => {
          const item = document.createElement('div');
          item.className = 'source-item';
          item.innerHTML = `<span class="doc-bullet">📄</span><span>${escapeHtml(src)}</span>`;
          sourcesList.appendChild(item);
        });
      } else {
        sourcesList.innerHTML = '<div class="no-sources-msg">No internal policies cited.</div>';
      }
    }
  }

  function updateHudForError(status, elapsed) {
    metricLatency.textContent = elapsed + ' ms';
    cacheBadge.textContent = 'REJECTED';
    cacheBadge.className = 'hud-badge badge-danger';
    metricCache.textContent = `Gate Rejected (${status})`;
  }

  function scrollToBottom() {
    chatMessages.scrollTop = chatMessages.scrollHeight;
  }

  function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }

  function formatMarkdown(text) {
    if (!text) return '';
    return text
      .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
      .replace(/\*(.*?)\*/g, '<em>$1</em>')
      .replace(/`(.*?)`/g, '<code class="inline-code">$1</code>');
  }

  // Modals Event Handlers
  btnOpenTickets.addEventListener('click', () => {
    modalTickets.classList.remove('hidden');
    loadTicketsTable();
  });
  btnCloseTickets.addEventListener('click', () => modalTickets.classList.add('hidden'));

  btnOpenIngest.addEventListener('click', () => modalIngest.classList.remove('hidden'));
  btnCloseIngest.addEventListener('click', () => modalIngest.classList.add('hidden'));
  btnCancelIngest.addEventListener('click', () => modalIngest.classList.add('hidden'));

  btnOpenSpecs.addEventListener('click', () => modalSpecs.classList.remove('hidden'));
  btnCloseSpecs.addEventListener('click', () => modalSpecs.classList.add('hidden'));

  // Close modals clicking outside dialog
  window.addEventListener('click', (e) => {
    if (e.target === modalTickets) modalTickets.classList.add('hidden');
    if (e.target === modalIngest) modalIngest.classList.add('hidden');
    if (e.target === modalSpecs) modalSpecs.classList.add('hidden');
  });

  // Ticket Explorer Data Generator (Deterministic Seed 42 Simulation)
  const syntheticTickets = generateSyntheticTickets();

  function generateSyntheticTickets() {
    // Exact seed-42 distribution representation
    const categories = ['Billing', 'Technical Issue', 'Account Access', 'Product Defect', 'General Inquiry'];
    const statuses = ['Open', 'In Progress', 'Escalated', 'Resolved', 'Closed'];
    const list = [];

    // First 15 representative tickets from dataset
    const samples = [
      { id: 'TKT-0001', cat: 'Billing', st: 'In Progress', res: 4.8, days: 5, esc: false },
      { id: 'TKT-0002', cat: 'Technical Issue', st: 'Open', res: 18.2, days: 12, esc: false },
      { id: 'TKT-0003', cat: 'Account Access', st: 'Resolved', res: 1.5, days: 22, esc: false },
      { id: 'TKT-0004', cat: 'Product Defect', st: 'Escalated', res: 36.4, days: 8, esc: true },
      { id: 'TKT-0005', cat: 'General Inquiry', st: 'Closed', res: 2.1, days: 19, esc: false },
      { id: 'TKT-0006', cat: 'Billing', st: 'Open', res: 12.0, days: 3, esc: false },
      { id: 'TKT-0007', cat: 'Technical Issue', st: 'Escalated', res: 42.5, days: 14, esc: true },
      { id: 'TKT-0008', cat: 'Account Access', st: 'In Progress', res: 8.4, days: 9, esc: false },
      { id: 'TKT-0009', cat: 'Billing', st: 'Resolved', res: 3.2, days: 28, esc: false },
      { id: 'TKT-0010', cat: 'Product Defect', st: 'Open', res: 24.0, days: 16, esc: true },
      { id: 'TKT-0011', cat: 'General Inquiry', st: 'Closed', res: 1.0, days: 7, esc: false },
      { id: 'TKT-0012', cat: 'Billing', st: 'In Progress', res: 9.6, days: 4, esc: false },
      { id: 'TKT-0013', cat: 'Technical Issue', st: 'Escalated', res: 54.0, days: 21, esc: true },
      { id: 'TKT-0014', cat: 'Account Access', st: 'Open', res: 14.5, days: 11, esc: false },
      { id: 'TKT-0015', cat: 'Product Defect', st: 'Resolved', res: 6.0, days: 25, esc: false },
    ];

    return samples.map(item => {
      const recency = (item.st === 'Resolved' || item.st === 'Closed') ? 0.0 : (item.days / 30.0);
      const score = 0.6 * (item.esc ? 1.0 : 0.0) + 0.4 * recency;
      return { ...item, score: score };
    });
  }

  function loadTicketsTable() {
    renderTickets(syntheticTickets);
  }

  function renderTickets(tickets) {
    ticketsTbody.innerHTML = '';
    tickets.forEach(t => {
      const tr = document.createElement('tr');
      const isHigh = t.score >= 0.4400;
      tr.innerHTML = `
        <td class="ticket-id-cell">${t.id}</td>
        <td>${t.cat}</td>
        <td><span class="meta-pill ${t.st === 'Escalated' ? 'blocked' : ''}">${t.st}</span></td>
        <td>${t.res.toFixed(1)} h</td>
        <td>${t.days}d ago</td>
        <td>${t.esc ? '⚡ Yes' : 'No'}</td>
        <td class="ticket-score-cell ${isHigh ? 'danger' : ''}">${t.score.toFixed(4)}</td>
        <td><button type="button" class="table-btn" data-tid="${t.id}">Query</button></td>
      `;
      ticketsTbody.appendChild(tr);
    });

    ticketsTbody.querySelectorAll('.table-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        const tid = btn.getAttribute('data-tid');
        modalTickets.classList.add('hidden');
        queryInput.value = `What is the status of ${tid}?`;
        queryInput.dispatchEvent(new Event('input'));
        chatForm.dispatchEvent(new Event('submit'));
      });
    });
  }

  // Ticket Search & Filter
  ticketSearchInput.addEventListener('input', filterTicketsList);
  statusFilter.addEventListener('change', filterTicketsList);

  function filterTicketsList() {
    const q = ticketSearchInput.value.toLowerCase();
    const st = statusFilter.value;
    const filtered = syntheticTickets.filter(t => {
      const matchQ = t.id.toLowerCase().includes(q) || t.cat.toLowerCase().includes(q);
      const matchSt = st === 'ALL' || t.st === st;
      return matchQ && matchSt;
    });
    renderTickets(filtered);
  }

  // Document Ingestion Form
  ingestForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const docId = docIdInput.value.trim();
    const text = docTextInput.value.trim();

    ingestResult.classList.remove('hidden');
    ingestResult.className = 'ingest-result-box';
    ingestResult.textContent = 'Indexing into Chroma collections and invalidating cache...';

    try {
      const res = await fetch('/add-document', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ doc_id: docId, text: text })
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: 'Failed' }));
        throw new Error(err.detail || 'Ingestion failed');
      }

      const resData = await res.json();
      ingestResult.className = 'ingest-result-box success';
      ingestResult.innerHTML = `
        <strong>✓ Document Indexed Successfully!</strong><br>
        • Doc ID: <code>${resData.doc_id}</code><br>
        • Chunks Indexed: <code>${resData.chunks_indexed}</code><br>
        • Cache Invalidated Entries: <code>${resData.cache_invalidated_entries}</code>
      `;

      // Clear input
      docTextInput.value = '';
      docIdInput.value = '';
    } catch (err) {
      ingestResult.className = 'ingest-result-box error';
      ingestResult.textContent = 'Error: ' + err.message;
    }
  });
});
