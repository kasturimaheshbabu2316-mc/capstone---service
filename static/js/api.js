/**
 * Ola Support Intelligence — API Client Module (api.js)
 * Strict relative routes: /ask, /health, /tickets.
 * Zero leaks of URLs, ports, stack traces, or internal patterns.
 */

const ENDPOINT_ASK = "/ask";
const ENDPOINT_HEALTH = "/health";
const ENDPOINT_TICKETS = "/tickets";

/**
 * Checks service health and readiness state with latency calculation.
 */
export async function checkHealth() {
  const t0 = performance.now();
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), 6000);

  try {
    const res = await fetch(ENDPOINT_HEALTH, {
      method: "GET",
      headers: { "Accept": "application/json" },
      signal: controller.signal,
    });
    clearTimeout(timeoutId);
    const latencyMs = Math.round(performance.now() - t0);

    if (res.ok) {
      const data = await res.json().catch(() => ({}));
      const isWaking = data && data.kb_ready === false;
      return {
        online: !isWaking,
        waking: isWaking,
        status: isWaking ? "Waking up" : "Online",
        latencyMs,
      };
    } else if (res.status === 503) {
      return { online: false, waking: true, status: "Waking up", latencyMs };
    }
    return { online: false, waking: false, status: "Offline", latencyMs };
  } catch (err) {
    clearTimeout(timeoutId);
    const latencyMs = Math.round(performance.now() - t0);
    return { online: false, waking: false, status: "Offline", latencyMs };
  }
}

/**
 * Queries the unified support pipeline via POST /ask.
 */
export async function sendQuery(question, sessionId) {
  const t0 = performance.now();
  const controller = new AbortController();
  // 90s timeout for cold start / heavy operations
  const timeoutId = setTimeout(() => controller.abort(), 90000);

  try {
    const res = await fetch(ENDPOINT_ASK, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Accept": "application/json",
      },
      body: JSON.stringify({
        question: question,
        session_id: sessionId || "web_session",
      }),
      signal: controller.signal,
    });
    clearTimeout(timeoutId);
    const latencyMs = Math.round(performance.now() - t0);

    if (res.ok) {
      const data = await res.json();
      return {
        is_error: false,
        status_code: 200,
        data: data.data || data,
        ticket: data.ticket || (data.data && data.data.ticket),
        sources: data.sources || (data.data && data.data.sources) || [],
        grounded: data.grounded ?? (data.data && data.data.grounded) ?? false,
        review_status: data.review_status || (data.data && data.data.review_status),
        latency_ms: data.latency_ms || latencyMs,
        cache_hit: data.cache_hit || false,
      };
    }

    // Granular, safe error handling (never apologize, never expose internals)
    let errorDetail = "";
    try {
      const errJson = await res.json();
      errorDetail = errJson.message || errJson.detail || "";
    } catch {
      // Ignore JSON parse errors on non-200
    }

    if (res.status === 400) {
      return {
        is_error: true,
        status_code: 400,
        title: "Request Blocked",
        message: "This request was blocked by the safety policy. Rephrase your question.",
        latency_ms: latencyMs,
      };
    }

    if (res.status === 413) {
      return {
        is_error: true,
        status_code: 413,
        title: "Question Too Long",
        message: "Your question is too long. Keep it under 2,000 tokens.",
        latency_ms: latencyMs,
      };
    }

    if (res.status === 503) {
      return {
        is_error: true,
        status_code: 503,
        title: "Desk Initializing",
        message: "The desk is warming up. Trying again.",
        latency_ms: latencyMs,
        waking: true,
      };
    }

    // Default 500 or other errors
    return {
      is_error: true,
      status_code: res.status || 500,
      title: "Service Notice",
      message: "Something went wrong on our side. Try again in a moment.",
      latency_ms: latencyMs,
    };
  } catch (err) {
    clearTimeout(timeoutId);
    const latencyMs = Math.round(performance.now() - t0);
    return {
      is_error: true,
      status_code: 503,
      title: "Service Offline",
      message: "Something went wrong on our side. Try again in a moment.",
      latency_ms: latencyMs,
    };
  }
}

/**
 * Fetches tickets directory from /tickets if available.
 */
export async function fetchTickets() {
  try {
    const res = await fetch(ENDPOINT_TICKETS, {
      method: "GET",
      headers: { "Accept": "application/json" },
    });
    if (res.ok) {
      return await res.json();
    }
  } catch {
    // Graceful fallback to embedded local tickets
  }
  return null;
}
