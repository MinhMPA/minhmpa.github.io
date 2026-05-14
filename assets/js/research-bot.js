// research-bot.js
// Deterministic, zero-fee FAQ matcher for the Contact page widget.
// Pure functions (normalize, isBlocked, answerQuestion) are unit-tested
// under node --test. init() wires the matcher to DOM nodes rendered by
// the Hugo shortcode (research-bot.html); it is a no-op under Node.

export const THRESHOLD = 20;
export const MIN_TOKEN_LENGTH = 3;

export const EMPTY_INPUT =
  "Please ask a question about Minh Nguyen's research, publications, software, or collaboration interests.";

export const FALLBACK =
  "I can answer basic questions about Minh Nguyen's public research profile, including research interests, publications, software, talks, and collaboration interests. I do not have enough information in the public homepage data to answer that specific question. You're welcome to email me directly — the address is above.";

export const BLOCKLIST = [
  "ignore previous instructions",
  "system prompt",
  "developer message",
  "api key",
  "password",
  "secret",
  "private notes",
  "private phone number",
  "personal address",
  "medical",
  "financial",
  "political",
];

/**
 * Normalize free-form text for matching.
 * - lowercase
 * - replace any char that is not a unicode letter/number/hyphen/whitespace with a space
 * - collapse runs of whitespace
 * - trim
 */
export function normalize(text) {
  if (text == null) return "";
  const lowered = String(text).toLowerCase();
  const cleaned = lowered.replace(/[^\p{L}\p{N}\s-]/gu, " ");
  return cleaned.replace(/\s+/g, " ").trim();
}

/**
 * Return true if the already-normalized question contains any blocklist
 * pattern as a substring. Patterns are compared in their original form
 * (lowercase, no punctuation), which is consistent with normalize().
 */
export function isBlocked(normalizedQuestion) {
  if (!normalizedQuestion) return false;
  for (const pattern of BLOCKLIST) {
    if (normalizedQuestion.includes(pattern)) return true;
  }
  return false;
}

function tokenize(normalized) {
  if (!normalized) return [];
  return normalized.split(/\s+/).filter((t) => t.length >= MIN_TOKEN_LENGTH);
}

function entryTokenSet(entry) {
  const tokens = new Set();
  const sources = [
    ...(entry.questions || []),
    ...(entry.keywords || []),
  ];
  for (const s of sources) {
    for (const t of tokenize(normalize(s))) tokens.add(t);
  }
  return tokens;
}

/**
 * Score a single entry against a normalized question q.
 */
function scoreEntry(q, entry) {
  let score = 0;

  for (const candidate of entry.questions || []) {
    const c = normalize(candidate);
    if (!c) continue;
    if (q === c) {
      score += 100;
    } else if (q.includes(c) || c.includes(q)) {
      score += 40;
    }
  }

  for (const k of entry.keywords || []) {
    const nk = normalize(k);
    if (!nk) continue;
    if (q.includes(nk)) score += 30;
  }

  const qTokens = new Set(tokenize(q));
  const eTokens = entryTokenSet(entry);
  let overlap = 0;
  for (const t of qTokens) {
    if (eTokens.has(t)) overlap += 1;
  }
  score += 5 * overlap;

  return score;
}

/**
 * Match a question against a list of FAQ entries.
 * Returns:
 *   { empty: true }                                    on null/empty input
 *   null                                               on blocklist hit or low-confidence
 *   { answer, sourceId, url? }                         on a confident match
 */
export function answerQuestion(question, faq) {
  if (question == null) return { empty: true };
  if (typeof question !== "string") return { empty: true };
  if (question.trim() === "") return { empty: true };

  const q = normalize(question);
  if (q === "") return { empty: true };

  if (isBlocked(q)) return null;
  if (!Array.isArray(faq) || faq.length === 0) return null;

  let best = null;
  let bestScore = 0;
  for (const entry of faq) {
    const s = scoreEntry(q, entry);
    if (s > bestScore) {
      bestScore = s;
      best = entry;
    }
  }

  if (best && bestScore >= THRESHOLD) {
    const result = { answer: best.answer, sourceId: best.id };
    if (best.url) result.url = best.url;
    return result;
  }
  return null;
}

/**
 * DOM init. Safe to call when DOM nodes are missing — returns silently.
 * Reads FAQ JSON from <script type="application/json" id="research-bot-faq">.
 */
export function init({ rootSelector = "#research-bot" } = {}) {
  if (typeof document === "undefined") return;
  const root = document.querySelector(rootSelector);
  if (!root) return;

  const form = document.getElementById("research-bot-form");
  const input = document.getElementById("research-bot-input");
  const answer = document.getElementById("research-bot-answer");
  if (!form || !input || !answer) return;

  const faqScript = document.getElementById("research-bot-faq");
  let faq = [];
  if (faqScript && faqScript.textContent) {
    try {
      faq = JSON.parse(faqScript.textContent);
    } catch (_err) {
      faq = [];
    }
  }

  form.addEventListener("submit", (evt) => {
    evt.preventDefault();
    // Clear previous answer container children.
    while (answer.firstChild) answer.removeChild(answer.firstChild);

    const value = input.value;
    const result = answerQuestion(value, faq);

    if (result && result.empty) {
      answer.textContent = EMPTY_INPUT;
    } else if (result === null) {
      answer.textContent = FALLBACK;
    } else {
      answer.textContent = result.answer;
      if (result.url) {
        answer.appendChild(document.createTextNode(" "));
        const link = document.createElement("a");
        link.href = result.url;
        link.textContent = "Learn more →";
        answer.appendChild(link);
      }
    }

    try {
      answer.focus();
    } catch (_err) {
      // ignore focus failures
    }
  });
}

// Auto-init in browser only. Guarded so importing under Node is a no-op.
if (typeof document !== "undefined" && document.getElementById("research-bot")) {
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", () => init());
  } else {
    init();
  }
}
