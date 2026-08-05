import test from 'node:test';
import assert from 'node:assert/strict';

import { normalize, matchCommand, fillTemplate, compilePattern, detectWakeWord } from '../src/command-engine.js';

const commands = [
  {
    id: 'open-youtube',
    phrases: ['open youtube', 'launch youtube'],
    action: { type: 'url', value: 'https://www.youtube.com' }
  },
  {
    id: 'volume-set',
    phrases: ['set volume to <n> percent', 'volume <n> percent'],
    action: { type: 'volume', op: 'set', value: '{n}' }
  },
  {
    id: 'search',
    phrases: ['search for <query>', 'google <query>'],
    action: { type: 'url', value: 'https://www.google.com/search?q={query}' }
  },
  {
    id: 'help',
    phrases: ['help', 'what can i say'],
    action: { type: 'help' }
  }
];

test('normalize strips punctuation and lowercases', () => {
  assert.equal(normalize('  Open, YouTube!!  '), 'open youtube');
  assert.equal(normalize("What's the TIME?"), 'what s the time');
  assert.equal(normalize(''), '');
});

test('exact phrase match', () => {
  const m = matchCommand(commands, 'Open YouTube!');
  assert.ok(m);
  assert.equal(m.command.id, 'open-youtube');
});

test('exact match on second alias', () => {
  const m = matchCommand(commands, 'launch youtube');
  assert.equal(m.command.id, 'open-youtube');
});

test('wildcard match captures params', () => {
  const m = matchCommand(commands, 'search for lofi beats to study');
  assert.equal(m.command.id, 'search');
  assert.equal(m.params.query, 'lofi beats to study');
});

test('wildcard set volume captures number', () => {
  const m = matchCommand(commands, 'set volume to 40 percent');
  assert.equal(m.command.id, 'volume-set');
  assert.equal(m.params.n, '40');
});

test('fillTemplate substitutes and encodes', () => {
  const url = fillTemplate('https://x.com/search?q={query}', { query: 'daft punk & live' }, encodeURIComponent);
  assert.equal(url, 'https://x.com/search?q=daft%20punk%20%26%20live');
});

test('fillTemplate leaves unknown placeholders empty', () => {
  assert.equal(fillTemplate('a {missing} b', {}), 'a  b');
});

test('no match returns null', () => {
  assert.equal(matchCommand(commands, 'fly to the moon'), null);
  assert.equal(matchCommand(commands, ''), null);
});

test('exact matches take priority over wildcards', () => {
  const m = matchCommand(commands, 'help');
  assert.equal(m.command.id, 'help');
});

test('compilePattern escapes regex metacharacters', () => {
  const { regex } = compilePattern('open c++ (ide)');
  assert.ok(regex.test('open c ide')); // punctuation stripped by normalize
});

test('wake word with trailing command', () => {
  const r = detectWakeWord('hey LALA, open youtube');
  assert.equal(r.wake, true);
  assert.equal(r.rest, 'open youtube');
});

test('wake word alone', () => {
  const r = detectWakeWord('ok lala');
  assert.equal(r.wake, true);
  assert.equal(r.rest, '');
});

test('fuzzy "la la" from a rough recognizer counts as wake', () => {
  const r = detectWakeWord('hey la la what time is it');
  assert.equal(r.wake, true);
  assert.equal(r.rest, 'what time is it');
});

test('"hey laala" is the default wake phrase', () => {
  const r = detectWakeWord('hey laala, open youtube');
  assert.equal(r.wake, true);
  assert.equal(r.rest, 'open youtube');
});

test('no wake word leaves text untouched', () => {
  const r = detectWakeWord('open youtube');
  assert.equal(r.wake, false);
  assert.equal(r.rest, 'open youtube');
});

test('word containing lala does not trigger', () => {
  assert.equal(detectWakeWord('call lalaland').wake, false);
});
