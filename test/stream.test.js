import test from 'node:test';
import assert from 'node:assert/strict';

import { applyDelta, finalizeToolCalls } from '../src/stream.js';

test('content deltas pass through as tokens', () => {
  const acc = { toolCalls: new Map() };
  assert.equal(applyDelta(acc, { content: 'Hel' }), 'Hel');
  assert.equal(applyDelta(acc, { content: 'lo' }), 'lo');
  assert.equal(finalizeToolCalls(acc), null);
});

test('tool_call fragments accumulate across deltas', () => {
  const acc = { toolCalls: new Map() };
  applyDelta(acc, { tool_calls: [{ index: 0, id: 'call_1', function: { name: 'get_weather', arguments: '' } }] });
  applyDelta(acc, { tool_calls: [{ index: 0, function: { arguments: '{"ci' } }] });
  applyDelta(acc, { tool_calls: [{ index: 0, function: { arguments: 'ty": "Hyderabad"}' } }] });
  const calls = finalizeToolCalls(acc);
  assert.equal(calls.length, 1);
  assert.equal(calls[0].id, 'call_1');
  assert.equal(calls[0].function.name, 'get_weather');
  assert.deepEqual(JSON.parse(calls[0].function.arguments), { city: 'Hyderabad' });
});

test('multiple parallel tool slots', () => {
  const acc = { toolCalls: new Map() };
  applyDelta(acc, { tool_calls: [{ index: 0, id: 'a', function: { name: 'get_time', arguments: '{}' } }] });
  applyDelta(acc, { tool_calls: [{ index: 1, id: 'b', function: { name: 'get_date', arguments: '{}' } }] });
  assert.equal(finalizeToolCalls(acc).length, 2);
});
