/**
 * Ola Support Intelligence — Pure Masking Module (mask.js)
 * Unit-testable pure functions for PII sanitization.
 * Never leaks customer contact details or credit data into DOM or exports.
 */

// Indian Mobile Numbers: +91 or 0 prefix, starts with 6,7,8,9, 10 digits total
const INDIAN_PHONE_REGEX = /(\+91[\-\s]?|0)?[6-9]\d{4}[\-\s]?\d{5}\b/g;

// Standard email patterns
const EMAIL_REGEX = /\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b/g;

// Card number patterns (13-19 digits, optional spaces or dashes)
const CARD_REGEX = /\b(\d{4}[\-\s]?){3,4}\d{1,4}\b/g;

export function maskPhoneNumbers(text) {
  if (!text || typeof text !== "string") return "";
  return text.replace(INDIAN_PHONE_REGEX, "[PHONE_MASKED]");
}

export function maskEmails(text) {
  if (!text || typeof text !== "string") return "";
  return text.replace(EMAIL_REGEX, "[EMAIL_MASKED]");
}

export function maskCardNumbers(text) {
  if (!text || typeof text !== "string") return "";
  return text.replace(CARD_REGEX, "[CARD_MASKED]");
}

export function formatCustomerInitials(fullName) {
  if (!fullName || typeof fullName !== "string") return "Customer";
  const parts = fullName.trim().split(/\s+/);
  if (parts.length === 0 || !parts[0]) return "Customer";
  if (parts.length === 1) return parts[0][0].toUpperCase() + ".";
  return parts.map(p => p[0].toUpperCase() + ".").join(" ");
}

export function maskAllPII(text) {
  if (!text || typeof text !== "string") return "";
  let sanitized = maskPhoneNumbers(text);
  sanitized = maskEmails(sanitized);
  sanitized = maskCardNumbers(sanitized);
  return sanitized;
}
