/**
 * Ola Support Intelligence — Tickets Directory Module (tickets.js)
 * Displays masked ticket records with category/status filters and search.
 */

import { fetchTickets } from "./api.js";

// Fallback seed tickets for 100% offline self-containment
const FALLBACK_TICKETS = [
  { ticket_id: "TKT-0001", category: "Billing", status: "Resolved", resolution_time_hours: 4.2, days_since_created: 2, escalated: false, escalation_score: 0.0000, risk_level: "Normal" },
  { ticket_id: "TKT-0002", category: "Technical Issue", status: "In Progress", resolution_time_hours: 12.0, days_since_created: 8, escalated: false, escalation_score: 0.1067, risk_level: "Normal" },
  { ticket_id: "TKT-0003", category: "Account Access", status: "Closed", resolution_time_hours: 2.5, days_since_created: 14, escalated: false, escalation_score: 0.0000, risk_level: "Normal" },
  { ticket_id: "TKT-0004", category: "Product Defect", status: "Escalated", resolution_time_hours: 36.0, days_since_created: 18, escalated: true, escalation_score: 0.8400, risk_level: "High Risk" },
  { ticket_id: "TKT-0005", category: "General Inquiry", status: "Open", resolution_time_hours: 8.0, days_since_created: 1, escalated: false, escalation_score: 0.0133, risk_level: "Normal" },
  { ticket_id: "TKT-0006", category: "Billing", status: "Resolved", resolution_time_hours: 3.1, days_since_created: 5, escalated: false, escalation_score: 0.0000, risk_level: "Normal" },
  { ticket_id: "TKT-0007", category: "Billing", status: "Escalated", resolution_time_hours: 18.0, days_since_created: 12, escalated: true, escalation_score: 0.7600, risk_level: "High Risk" },
  { ticket_id: "TKT-0008", category: "Technical Issue", status: "In Progress", resolution_time_hours: 15.5, days_since_created: 6, escalated: false, escalation_score: 0.0800, risk_level: "Normal" },
  { ticket_id: "TKT-0009", category: "Product Defect", status: "Open", resolution_time_hours: 24.0, days_since_created: 3, escalated: false, escalation_score: 0.0400, risk_level: "Normal" },
  { ticket_id: "TKT-0010", category: "Account Access", status: "Resolved", resolution_time_hours: 1.8, days_since_created: 9, escalated: false, escalation_score: 0.0000, risk_level: "Normal" },
  { ticket_id: "TKT-0011", category: "General Inquiry", status: "Closed", resolution_time_hours: 5.0, days_since_created: 21, escalated: false, escalation_score: 0.0000, risk_level: "Normal" },
  { ticket_id: "TKT-0012", category: "Billing", status: "Escalated", resolution_time_hours: 22.0, days_since_created: 15, escalated: true, escalation_score: 0.8000, risk_level: "High Risk" },
];

let cachedTickets = null;

export async function loadTickets() {
  if (cachedTickets) return cachedTickets;
  const remote = await fetchTickets();
  if (remote && Array.isArray(remote) && remote.length > 0) {
    cachedTickets = remote;
  } else {
    cachedTickets = FALLBACK_TICKETS;
  }
  return cachedTickets;
}

export function filterTickets(tickets, { category, status, search }) {
  if (!tickets) return [];
  return tickets.filter(t => {
    if (category && category !== "All" && t.category !== category) return false;
    if (status && status !== "All" && t.status !== status) return false;
    if (search) {
      const q = search.trim().toUpperCase();
      if (!t.ticket_id.toUpperCase().includes(q)) return false;
    }
    return true;
  });
}
