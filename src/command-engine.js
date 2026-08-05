/**
 * LALA command matching engine.
 *
 * Shared between the Electron renderer and the pure browser version.
 * Pure functions, no DOM — also unit-tested from Node.
 */

/** Lowercase, strip punctuation, collapse whitespace. */
export function normalize(text) {
  return String(text || '')
    .toLowerCase()
    .replace(/[^\p{L}\p{N}\s]/gu, ' ')
    .replace(/\s+/g, ' ')
    .trim();
}

/**
 * Compile a phrase pattern like "set volume to <n> percent"
 * into a regex plus a list of capture names.
 */
export function compilePattern(phrase) {
  const params = [];
  // Split wildcards out FIRST, then normalize the literal parts individually
  // (normalize would otherwise strip the <> brackets).
  const parts = String(phrase || '').toLowerCase().split(/<([^>]+)>/);
  const escaped = parts
    .map((part, i) => {
      if (i % 2 === 1) {
        params.push(part.trim());
        return '(.+?)';
      }
      return normalize(part).replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    })
    .filter((s) => s.length > 0)
    .join('\\s+');
  return { regex: new RegExp(`^${escaped}$`), params };
}

/**
 * Match normalized/ raw transcript text against a list of commands.
 * Each command: { phrases: string[], action: object, ... }
 * Returns { command, params, phrase } or null.
 *
 * Exact (wildcard-free) phrases win over wildcard patterns.
 */
export function matchCommand(commands, text) {
  const norm = normalize(text);
  if (!norm) return null;

  // Pass 1: exact matches.
  for (const command of commands) {
    for (const phrase of command.phrases || []) {
      if (!phrase.includes('<') && normalize(phrase) === norm) {
        return { command, params: {}, phrase };
      }
    }
  }

  // Pass 2: wildcard matches.
  for (const command of commands) {
    for (const phrase of command.phrases || []) {
      if (!phrase.includes('<')) continue;
      const { regex, params } = compilePattern(phrase);
      const m = norm.match(regex);
      if (m) {
        const values = {};
        params.forEach((p, i) => {
          values[p] = m[i + 1].trim();
        });
        return { command, params: values, phrase };
      }
    }
  }

  return null;
}

/**
 * Fill "{name}" placeholders in a template string.
 * `encode` is applied to each inserted value (e.g. encodeURIComponent for URLs).
 */
export function fillTemplate(template, params, encode = (v) => v) {
  if (typeof template !== 'string') return template;
  return template.replace(/\{(\w+)\}/g, (_, key) =>
    params && params[key] !== undefined ? encode(params[key]) : ''
  );
}

/**
 * Detect the wake word ("hey LALA", "ok LALA", "LALA", even "hey la la" from
 * a fuzzy recognizer) in normalized or raw text.
 * Returns { wake, rest } where `rest` is the remaining command text.
 */
export function detectWakeWord(text) {
  const norm = normalize(text);
  const re = /(?:^|\s)(?:hey|ok|okay|hello|hi)?\s*(?:laala|lala|la la)(?=\s|$)/;
  const m = norm.match(re);
  if (!m) return { wake: false, rest: norm };
  const rest = (norm.slice(0, m.index) + ' ' + norm.slice(m.index + m[0].length))
    .replace(/\s+/g, ' ')
    .trim();
  return { wake: true, rest };
}
