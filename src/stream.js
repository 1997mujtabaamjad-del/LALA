/**
 * Pure streaming helpers (unit-tested): OpenAI SSE delta application and
 * tool-call fragment accumulation, shared by the in-app agentic loop.
 */

/** Apply one chat-completion delta. Returns the content token (may be ''). */
export function applyDelta(acc, delta) {
  let token = '';
  if (delta && delta.content) token = delta.content;
  for (const tc of (delta && delta.tool_calls) || []) {
    const key = tc.index ?? acc.toolCalls.size;
    let slot = acc.toolCalls.get(key);
    if (!slot) {
      slot = { id: null, type: 'function', function: { name: '', arguments: '' } };
      acc.toolCalls.set(key, slot);
    }
    if (tc.id) slot.id = tc.id;
    const fn = tc.function || {};
    if (fn.name) slot.function.name = fn.name;
    if (fn.arguments) slot.function.arguments += fn.arguments;
  }
  return token;
}

/** Finalized tool_calls array, or null when the round was pure content. */
export function finalizeToolCalls(acc) {
  if (!acc.toolCalls.size) return null;
  return [...acc.toolCalls.values()];
}
