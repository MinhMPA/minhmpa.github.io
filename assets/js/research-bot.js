// research-bot.js
// Deterministic, zero-fee FAQ matcher for the Contact page widget.
// Pure functions (normalize, isBlocked, answerQuestion) are unit-tested
// under node --test. init() wires the matcher to DOM nodes rendered by
// the Hugo shortcode (research-bot.html); it is a no-op under Node.

export const THRESHOLD = 20;
export const MIN_TOKEN_LENGTH = 3;

const SCORE_EXACT_QUESTION = 100;
const SCORE_QUESTION_SUBSTRING = 40;
const SCORE_KEYWORD_SUBSTRING = 30;
const SCORE_TOKEN_OVERLAP = 5;
// Hand-authored entries (no source, or source !== 'wiki') get a priority bonus
// so that curator-written entries always win over auto-generated wiki entries
// when both match the same query.
const SCORE_HAND_ENTRY = 50;

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
  let contentScore = 0;

  for (const candidate of entry.questions || []) {
    const c = normalize(candidate);
    if (!c) continue;
    if (q === c) {
      contentScore += SCORE_EXACT_QUESTION;
    } else if (q.includes(c) || c.includes(q)) {
      contentScore += SCORE_QUESTION_SUBSTRING;
    }
  }

  for (const k of entry.keywords || []) {
    const nk = normalize(k);
    if (!nk) continue;
    if (q.includes(nk)) contentScore += SCORE_KEYWORD_SUBSTRING;
  }

  const qTokens = new Set(tokenize(q));
  const eTokens = entryTokenSet(entry);
  let overlap = 0;
  for (const t of qTokens) {
    if (eTokens.has(t)) overlap += 1;
  }
  let score = contentScore + SCORE_TOKEN_OVERLAP * overlap;

  // Hand-authored entries (no source or source !== 'wiki') get a priority
  // bonus when they have genuine question/keyword content overlap, so they
  // always win over auto-generated wiki entries for the same query.
  if (contentScore > 0 && (!entry.source || entry.source !== "wiki")) {
    score += SCORE_HAND_ENTRY;
  }

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
    answer.replaceChildren();

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
