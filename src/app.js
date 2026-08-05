/**
 * LALA — Voice Command Assistant
 * Renderer / browser app. Works in two modes:
 *
 *  - Desktop (Electron): `window.lala` bridge is present. Push-to-talk with
 *    Space or the orb; audio is transcribed by the main process using either
 *    the offline Vosk engine or the OpenAI Whisper API. Full system control.
 *
 *  - Browser: uses the Web Speech API for free continuous listening.
 *    Desktop-only actions show a friendly hint instead.
 */

import { matchCommand, normalize, fillTemplate, detectWakeWord } from './command-engine.js';
import { createWebSpeech } from './web-speech.js';
import { createWakeListener } from './wakeword.js';
import { startStreamCapture, startBargeMonitor } from './streamrecorder.js';
import { applyDelta, finalizeToolCalls } from './stream.js';

const desktop = typeof window.lala !== 'undefined';
const $ = (sel) => document.querySelector(sel);
const $$ = (sel) => Array.from(document.querySelectorAll(sel));

const DEFAULT_SETTINGS = {
  engine: 'auto',
  openaiKey: '',
  deepgramKey: '',
  chatModel: 'gpt-4o-mini',
  whisperModel: 'whisper-1',
  language: 'en-US',
  voiceResponses: true,
  continuous: true,
  wakeWord: true,
  continuousConversation: true,
  useBrain: true,
  brainUrl: 'http://127.0.0.1:8420',
  saveRecordings: true,
  preferSilero: true,
  elevenlabsKey: '',
  hwAccel: true,
  lightsProvider: 'auto',
  hueIp: '',
  hueKey: '',
  haUrl: '',
  haToken: '',
  wledIp: ''
};

const JOKES = [
  'Why do programmers prefer dark mode? Because light attracts bugs.',
  'I told my computer I needed a break, and it said: no problem, I’ll go to sleep.',
  'Why did the developer go broke? Because he used up all his cache.',
  'There are only 10 kinds of people: those who understand binary and those who don’t.',
  'I would tell you a UDP joke, but you might not get it.'
];

const GUIDE_TIPS = [
  'Say “Hey Laala” and wait for the beep, then speak your request.',
  'Or hold Space — or tap the mic — and release when you’re done.',
  'You can interrupt me any time; just start talking and I’ll stop.',
  'After I answer, keep talking — I listen on until you pause, or say “stop listening”.',
  'Try things like “open youtube”, “weather in hyderabad”, “add meeting tomorrow at 3 pm”, or “lights to warm”.',
  'Say “help” for my full command list, and “user guide” to hear this again.'
];

const CONFIRM_WORDS = ['confirm', 'yes', 'do it', 'proceed', 'go ahead'];
const CANCEL_WORDS = ['cancel', 'no', 'stop', 'nevermind', 'never mind', 'abort'];

const state = {
  settings: { ...DEFAULT_SETTINGS },
  defaults: [],
  custom: [],
  status: null,
  listening: false,
  dictation: false,
  dictBuf: [],
  pending: null, // action awaiting confirmation
  lastTranscript: '',
  webSpeech: null,
  pttActive: false,
  wakeListener: null,
  bargeMon: null,
  demoRunning: false,
  followHold: false, // set after “stop listening” until the next wake
  recentChat: []     // last turns, fed to the in-app tool-calling loop
};

/* ---------------------------------------------------------------- utils */

function toast(message, kind = '') {
  const el = $('#toast');
  el.textContent = message;
  el.className = `toast ${kind}`.trim();
  clearTimeout(el._t);
  el._t = setTimeout(() => el.classList.add('hidden'), 4200);
}

function addLog(who, text) {
  const log = $('#log');
  const entry = document.createElement('div');
  entry.className = `log-entry ${who}`;
  const tag = document.createElement('span');
  tag.className = 'who';
  tag.textContent = who === 'you' ? 'YOU' : who === 'lala' ? 'LALA' : 'SYS';
  const body = document.createElement('span');
  body.textContent = text;
  entry.append(tag, body);
  log.prepend(entry);
  while (log.children.length > 60) log.removeChild(log.lastChild);
}

function setStatusLine(text) {
  $('#status-line').textContent = text;
}

function setChipState(text) {
  $('#chip-state').textContent = text;
}

function showInterim(text) {
  const el = $('#interim');
  if (!text) { el.classList.add('hidden'); return; }
  el.textContent = `“${text}”`;
  el.classList.remove('hidden');
}

function showResponse(text) {
  const el = $('#response');
  if (!text) { el.classList.add('hidden'); return; }
  el.textContent = text;
  el.classList.remove('hidden');
}

function allCommands() {
  return [...state.custom, ...state.defaults];
}

/* ------------------------------------------------------------------ TTS */

let preferredVoice = null;

function pickVoice() {
  const voices = speechSynthesis.getVoices();
  preferredVoice =
    voices.find((v) => /en/i.test(v.lang) && /female|samantha|zira|google us english/i.test(v.name)) ||
    voices.find((v) => /^en/i.test(v.lang)) ||
    voices[0] || null;
}

if ('speechSynthesis' in window) {
  pickVoice();
  speechSynthesis.onvoiceschanged = pickVoice;
}

function speak(text, { cancel = true } = {}) {
  if (!state.settings.voiceResponses || !text) return;
  if (!('speechSynthesis' in window)) return;
  if (cancel) speechSynthesis.cancel();
  const utter = new SpeechSynthesisUtterance(text);
  if (preferredVoice) utter.voice = preferredVoice;
  utter.rate = 1.03;
  speechSynthesis.speak(utter);
  armBargeMonitor(); // mic stays open while she talks
}

function respond(text, { silent = false } = {}) {
  if (!text) return;
  state.recentChat.push({ role: 'assistant', content: text });
  if (state.recentChat.length > 20) state.recentChat = state.recentChat.slice(-20);
  addLog('lala', text);
  showResponse(text);
  if (!silent) speak(text);
}

/* ------------------------------------------------- listening orb visuals */

function setOrbMode(mode) {
  const orb = $('#orb');
  orb.classList.toggle('listening', mode === 'listening');
  orb.classList.toggle('recording', mode === 'recording');
}

/* ------------------------------------------------------ transcript flow */

async function handleTranscript(rawText) {
  const text = String(rawText || '').trim();
  if (!text) return;

  state.lastTranscript = text;
  state.recentChat.push({ role: 'user', content: text });
  if (state.recentChat.length > 20) state.recentChat = state.recentChat.slice(-20);
  addLog('you', text);
  showInterim('');

  // 1) A destructive action is waiting for confirmation.
  if (state.pending) {
    const norm = normalize(text);
    if (CONFIRM_WORDS.some((w) => norm.includes(w))) return confirmPending(true);
    if (CANCEL_WORDS.some((w) => norm.includes(w))) return confirmPending(false);
    respond('Say “confirm” to proceed or “cancel” to abort.');
    return;
  }

  // 2) Dictation mode swallows everything until the stop phrase.
  if (state.dictation) {
    const stopMatch = matchCommand(allCommands(), text);
    if (stopMatch && stopMatch.command.action?.type === 'dictation' && stopMatch.command.action.op === 'stop') {
      return endDictation();
    }
    state.dictBuf.push(text);
    setStatusLine(`Dictating: ${state.dictBuf.length} sentence(s)…`);
    return;
  }

  // 3) Normal command matching.
  const match = matchCommand(allCommands(), text);
  if (!match) {
    // 3a) Agentic + streaming: tokens speak sentence-by-sentence while the
    //     model keeps generating; tool rounds run silently in between.
    //     Barge-in aborts the fetch (cancels generation) + queued TTS.
    state.abortCtl = new AbortController();
    let streamed = '';
    const toolReply = await llmToolLoopStream(text, (tok) => {
      streamed += tok;
      showResponse(streamed);
      const parts = streamed.split(/(?<=[.!?])\s+/);
      if (parts.length > 1) {
        parts.slice(0, -1).forEach((s) => speak(s, { cancel: false }));
        streamed = parts[parts.length - 1];
      }
    }, state.abortCtl.signal);
    state.abortCtl = null;
    if (toolReply) {
      if (streamed.trim()) speak(streamed, { cancel: false });
      respond(toolReply, { silent: true });
      return;
    }
    // 3b) Then the Python brain; then a polite miss.
    const brain = await askBrain(text);
    if (brain) {
      respond(brain);
      return;
    }
    respond('Sorry, I didn’t recognize that command. Say “help” to see what I understand. (Tip: run `python -m assistant --serve` to give me a brain.)');
    return;
  }

  await runMatch(match);
}

/**
 * Ask the local Python assistant (assistant/server.py) anything.
 * Connection-refused fails instantly, so this is cheap when it's not running.
 */
/* ------------------------------------------------- LLM tool calling (agentic) */

const LAALA_PERSONA =
  'You are Laala, the user\'s warm, upbeat voice companion: friendly, a little ' +
  'playful, genuinely helpful. Replies are spoken aloud — keep them to 1-3 ' +
  'sentences unless asked for detail. Use the provided tools whenever a request ' +
  'needs live data or an action, then answer naturally from the tool results.';

const TOOLS_JS = [
  { type: 'function', function: { name: 'get_weather', description: 'Current weather + 3-day outlook for a city, or the user\'s location if omitted.', parameters: { type: 'object', properties: { city: { type: 'string' } }, required: [] } } },
  { type: 'function', function: { name: 'web_search', description: 'Look up a fact online; returns a short answer.', parameters: { type: 'object', properties: { query: { type: 'string' } }, required: ['query'] } } },
  { type: 'function', function: { name: 'control_lights', description: 'Control smart lights.', parameters: { type: 'object', properties: { op: { type: 'string', enum: ['on', 'off', 'set', 'color'] }, value: { type: 'integer' }, color: { type: 'string' } }, required: ['op'] } } },
  { type: 'function', function: { name: 'calendar_add', description: 'Add a calendar event.', parameters: { type: 'object', properties: { title: { type: 'string' }, when_text: { type: 'string' } }, required: ['title', 'when_text'] } } },
  { type: 'function', function: { name: 'calendar_list', description: 'List upcoming calendar events.', parameters: { type: 'object', properties: {} } } },
  { type: 'function', function: { name: 'open_app', description: 'Launch a desktop app by name.', parameters: { type: 'object', properties: { name: { type: 'string' } }, required: ['name'] } } },
  { type: 'function', function: { name: 'open_url', description: 'Open a website.', parameters: { type: 'object', properties: { url: { type: 'string' } }, required: ['url'] } } },
  { type: 'function', function: { name: 'play_music', description: 'Play music via YouTube search.', parameters: { type: 'object', properties: { query: { type: 'string' } }, required: ['query'] } } },
  { type: 'function', function: { name: 'get_time', description: 'Current local time.', parameters: { type: 'object', properties: {} } } },
  { type: 'function', function: { name: 'get_date', description: 'Today\'s date.', parameters: { type: 'object', properties: {} } } }
];

async function runTool(name, args) {
  try {
    switch (name) {
      case 'get_weather': {
        const t = await fetchWeather(args.city || '');
        return t || 'Weather unavailable.';
      }
      case 'web_search':
        return (await fetchDdg(args.query)) || 'No instant answer found.';
      case 'calendar_list': {
        const events = desktop ? await window.lala.getCalendar()
          : JSON.parse(localStorage.getItem('lala.calendar') || '[]');
        const upcoming = events.map((e) => ({ ...e, ts: Date.parse(e.when) }))
          .filter((e) => e.ts > Date.now() - 3600e3).sort((a, b) => a.ts - b.ts).slice(0, 5);
        return upcoming.length
          ? 'Upcoming: ' + upcoming.map((e) => `${e.title} — ${new Date(e.ts).toLocaleString([], { weekday: 'short', hour: '2-digit', minute: '2-digit' })}`).join('; ')
          : 'The calendar is clear.';
      }
      case 'calendar_add': {
        const when = calParseWhen(args.when_text || '');
        if (!when) return 'Could not parse a time — ask the user for e.g. "tomorrow at 3pm".';
        const ev = { id: `ev${Date.now()}`, when: when.toISOString(), title: args.title || 'event' };
        if (desktop) await window.lala.addCalendar(ev);
        else {
          const arr = JSON.parse(localStorage.getItem('lala.calendar') || '[]');
          arr.push(ev);
          localStorage.setItem('lala.calendar', JSON.stringify(arr));
        }
        return `Added '${ev.title}' for ${when.toDateString()} ${when.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}.`;
      }
      case 'get_time':
        return new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
      case 'get_date':
        return new Date().toLocaleDateString([], { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' });
      case 'play_music':
      case 'open_url': {
        const url = name === 'play_music'
          ? `https://www.youtube.com/results?search_query=${encodeURIComponent(args.query || '')}`
          : args.url;
        if (desktop) await window.lala.executeAction({ type: 'url', value: url }, {});
        else window.open(url, '_blank', 'noopener');
        return `Opened ${url}.`;
      }
      case 'open_app':
      case 'control_lights': {
        if (!desktop) return 'Needs the desktop app.';
        const act = name === 'open_app'
          ? { type: 'app', value: [args.name, `${args.name}.exe`] }
          : { type: 'lights', op: args.op, value: args.value, color: args.color };
        const r = await window.lala.executeAction(act, {});
        return r.message || 'done';
      }
      default:
        return `Unknown tool: ${name}`;
    }
  } catch (err) {
    return `Tool ${name} failed: ${err.message || err}`;
  }
}

/** Streaming agentic loop: tokens flow out live; tool rounds run silently. */
async function llmToolLoopStream(text, onToken, signal) {
  const key = state.settings.openaiKey;
  if (!key) return null;
  let messages = [
    { role: 'system', content: LAALA_PERSONA },
    ...state.recentChat.slice(-10),
    { role: 'user', content: text }
  ];
  try {
    for (let round = 0; round < 4; round++) {
      const res = await fetch('https://api.openai.com/v1/chat/completions', {
        method: 'POST',
        headers: { Authorization: `Bearer ${key}`, 'content-type': 'application/json' },
        body: JSON.stringify({
          model: state.settings.chatModel || 'gpt-4o-mini',
          messages, tools: TOOLS_JS, stream: true
        }),
        signal
      });
      if (!res.ok || !res.body) return null;
      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buf = '';
      const acc = { toolCalls: new Map() };
      let content = '';
      for (;;) {
        const { done, value } = await reader.read();
        if (done) break;
        buf += decoder.decode(value, { stream: true });
        let idx;
        while ((idx = buf.indexOf('\n')) >= 0) {
          const line = buf.slice(0, idx).trim();
          buf = buf.slice(idx + 1);
          if (!line.startsWith('data:')) continue;
          const payload = line.slice(5).trim();
          if (payload === '[DONE]') continue;
          let j;
          try { j = JSON.parse(payload); } catch { continue; }
          const token = applyDelta(acc, (j.choices && j.choices[0] && j.choices[0].delta) || {});
          if (token) {
            content += token;
            onToken && onToken(token);
          }
        }
      }
      const calls = finalizeToolCalls(acc);
      if (!calls) return content;
      messages.push({ role: 'assistant', tool_calls: calls });
      for (const c of calls) {
        let args = {};
        try { args = JSON.parse(c.function.arguments || '{}'); } catch { /* {} */ }
        addLog('sys', `🔧 ${c.function.name}(${JSON.stringify(args)})`);
        const out = await runTool(c.function.name, args);
        messages.push({ role: 'tool', tool_call_id: c.id || `call_${messages.length}`, content: String(out) });
      }
    }
  } catch { /* offline / blocked → fall through to brain */ }
  return null;
}

/**
 * Ask the local Python assistant (assistant/server.py) anything.
 * Connection-refused fails instantly, so this is cheap when it's not running.
 */
async function askBrain(text) {
  if (state.settings.useBrain === false) return null;
  try {
    const ctl = new AbortController();
    const timer = setTimeout(() => ctl.abort(), 30000);
    const res = await fetch(`${base}/chat`, {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ text }),
      signal: ctl.signal
    });
    clearTimeout(timer);
    if (!res.ok) return null;
    const json = await res.json();
    return json.reply || null;
  } catch {
    return null;
  }
}

/** Fill wildcard params into the action and response templates. */
function hydrate(action, response, params) {
  const act = JSON.parse(JSON.stringify(action));
  const encode = act.type === 'url' ? encodeURIComponent : (v) => v;
  for (const [key, value] of Object.entries(act)) {
    if (typeof value === 'string') act[key] = fillTemplate(value, params, encode);
  }
  const filledResponse = fillTemplate(response || '', params);
  return { act, filledResponse };
}

async function runMatch(match) {
  const { command, params } = match;
  let { act, filledResponse } = hydrate(command.action, command.response, params);

  // Renderer-side special cases --------------------------------------------

  if (act.type === 'quiet') {
    if ('speechSynthesis' in window) speechSynthesis.cancel();
    addLog('lala', '🤐 Going quiet.');
    return;
  }

  if (act.type === 'end-conversation') {
    state.followHold = true;
    respond('Okay — I’ll wait for the wake word.');
    return;
  }

  if (act.type === 'coin') {
    respond(Math.random() < 0.5 ? 'Heads!' : 'Tails!');
    return;
  }

  if (act.type === 'dice') {
    respond(`You rolled a ${1 + Math.floor(Math.random() * 6)}.`);
    return;
  }

  if (act.type === 'joke') {
    respond(JOKES[Math.floor(Math.random() * JOKES.length)]);
    return;
  }

  if (act.type === 'guide') {
    // LLM-generated when the Python brain is reachable; static tips otherwise.
    const brain = await askBrain('user guide');
    respond(brain || 'Here’s how to talk to me. ' + GUIDE_TIPS.join(' '));
    return;
  }

  if (act.type === 'dictation') {
    if (act.op === 'start') return startDictation();
    return endDictation();
  }

  if (act.type === 'help') {
    switchTab('help');
    respond('Here’s everything I understand — it’s on the Help tab.');
    return;
  }

  if (act.type === 'volume' && act.op === 'set') {
    const n = parseInt(act.value, 10);
    if (Number.isNaN(n)) {
      respond('How many percent? Try “set volume to 40 percent”.');
      return;
    }
    act.value = n;
  }

  // Dispatch ----------------------------------------------------------------
  if (desktop) {
    setChipState('working…');
    const result = await window.lala.executeAction(act, {
      lastText: state.lastTranscript,
      confirmed: false
    });
    setChipState('idle');
    handleResult(result, act, filledResponse);
  } else {
    browserExecute(act, filledResponse);
  }
}

function handleResult(result, act, fallbackResponse) {
  if (!result) return;

  if (result.needsConfirm) {
    state.pending = act;
    $('#confirm-text').textContent = result.message;
    $('#confirm-card').classList.remove('hidden');
    respond(result.message);
    return;
  }

  if (result.payload?.type === 'help') {
    switchTab('help');
    respond('Here’s everything I understand — it’s on the Help tab.');
    return;
  }

  respond(result.message || fallbackResponse || 'Done.');
}

function confirmPending(confirmed) {
  const act = state.pending;
  state.pending = null;
  $('#confirm-card').classList.add('hidden');
  if (!confirmed) {
    respond('Okay, cancelled.');
    return;
  }
  if (desktop) {
    window.lala.executeAction(act, { confirmed: true }).then((r) => handleResult(r, act, ''));
  } else {
    respond('That needs the desktop app.');
  }
}

/* ------------------------------------------------- browser-mode fallback */

async function fetchWeather(city) {
  try {
    if (city) {
      const g = await fetch(`https://geocoding-api.open-meteo.com/v1/search?name=${encodeURIComponent(city)}&count=1`);
      const gj = await g.json();
      const place = (gj.results || [])[0];
      if (!place) return null;
      const r = await fetch(`https://api.open-meteo.com/v1/forecast?latitude=${place.latitude}&longitude=${place.longitude}&current=temperature_2m,apparent_temperature,relative_humidity_2m,weather_code,wind_speed_10m&daily=weather_code,temperature_2m_max,temperature_2m_min&forecast_days=3&timezone=auto`);
      const j = await r.json();
      const c = j.current;
      const words = { 0: 'clear skies', 1: 'mostly clear', 2: 'partly cloudy', 3: 'overcast', 45: 'foggy', 51: 'light drizzle', 61: 'light rain', 63: 'rain', 65: 'heavy rain', 71: 'light snow', 73: 'snow', 80: 'rain showers', 95: 'thunderstorms' };
      const outlook = forecastLine(j.daily || {});
      return `It's ${Math.round(c.temperature_2m)}°C in ${place.name}, ${words[c.weather_code] || 'cloudy'}, feels like ${Math.round(c.apparent_temperature)}°, humidity ${c.relative_humidity_2m}%.` +
        (outlook ? ` Ahead: ${outlook}` : '');
    }
    const r = await fetch('https://wttr.in/?format=j1');
    const j = await r.json();
    return `It's ${j.current_condition[0].temp_C}°C in ${j.nearest_area[0].areaName[0].value}, humidity ${j.current_condition[0].humidity}%.`;
  } catch {
    return null;
  }
}

function forecastLine(daily) {
  const names = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];
  const words = { 0: 'clear', 1: 'mostly clear', 2: 'partly cloudy', 3: 'overcast', 61: 'light rain', 63: 'rain', 95: 'thunderstorms' };
  const parts = [];
  const n = Math.min(3, (daily.time || []).length);
  for (let i = 0; i < n; i++) {
    const label = i === 0 ? 'Today' : i === 1 ? 'Tomorrow' : names[new Date(daily.time[i]).getDay()];
    parts.push(`${label}: ${words[daily.weather_code[i]] || 'cloudy'}, ${Math.round(daily.temperature_2m_min[i])}–${Math.round(daily.temperature_2m_max[i])}°`);
  }
  return parts.length ? parts.join('; ') + '.' : '';
}

async function fetchWikiResults(query) {
  try {
    const r = await fetch(`https://en.wikipedia.org/w/api.php?action=opensearch&search=${encodeURIComponent(query)}&limit=3&format=json&origin=*`);
    const [, titles, , urls] = await r.json();
    return titles.map((t, i) => ({ title: t, url: urls[i] }));
  } catch {
    return [];
  }
}

function buildIcs(events) {
  const pad = (n) => String(n).padStart(2, '0');
  const lines = ['BEGIN:VCALENDAR', 'VERSION:2.0', 'PRODID:-//LALA//voice calendar//EN'];
  for (const e of events) {
    const d = new Date(e.when);
    if (Number.isNaN(d.getTime())) continue;
    lines.push('BEGIN:VEVENT',
      `UID:${e.id || 'ev'}@lala`,
      `DTSTART:${d.getFullYear()}${pad(d.getMonth() + 1)}${pad(d.getDate())}T${pad(d.getHours())}${pad(d.getMinutes())}00`,
      `SUMMARY:${e.title || 'event'}`,
      'END:VEVENT');
  }
  lines.push('END:VCALENDAR');
  return lines.join('\r\n') + '\r\n';
}

function parseIcs(text) {
  const out = [];
  let cur = null;
  for (const raw of text.split(/\r?\n/)) {
    const line = raw.trim();
    if (line === 'BEGIN:VEVENT') cur = {};
    else if (line.startsWith('DTSTART') && cur) {
      const v = line.split(':')[1].split(';').pop();
      const m = v.match(/^(\d{4})(\d{2})(\d{2})T(\d{2})(\d{2})/);
      if (m) cur.when = new Date(+m[1], +m[2] - 1, +m[3], +m[4], +m[5]).toISOString();
    } else if (line.startsWith('SUMMARY:') && cur) cur.title = line.slice(8).trim();
    else if (line === 'END:VEVENT' && cur && cur.when) {
      out.push({ id: `ics${Date.now()}${out.length}`, when: cur.when, title: cur.title || 'event' });
      cur = null;
    }
  }
  return out;
}

async function fetchDdg(query) {
  try {
    const r = await fetch(`https://api.duckduckgo.com/?q=${encodeURIComponent(query)}&format=json&no_html=1&no_redirect=1`);
    const j = await r.json();
    let text = j.AbstractText || j.Answer || '';
    if (!text && (j.RelatedTopics || []).length) text = j.RelatedTopics[0].Text || '';
    return text ? String(text).slice(0, 400) : null;
  } catch {
    return null;
  }
}

function calParseWhen(text) {
  const t = String(text || '').toLowerCase();
  const m = t.match(/\bat\s+(\d{1,2})(?::(\d{2}))?\s*(am|pm)?\b/);
  if (!m) return null;
  let h = parseInt(m[1], 10);
  const min = parseInt(m[2] || '0', 10);
  if (m[3] === 'pm' && h < 12) h += 12;
  const days = { sunday: 0, monday: 1, tuesday: 2, wednesday: 3, thursday: 4, friday: 5, saturday: 6 };
  const now = new Date();
  const day = new Date(now);
  if (t.includes('tomorrow')) day.setDate(day.getDate() + 1);
  else {
    const wd = Object.keys(days).find((d) => new RegExp(`\\b${d}\\b`).test(t));
    if (wd) day.setDate(day.getDate() + ((days[wd] - now.getDay() + 7) % 7 || 7));
  }
  day.setHours(h, min, 0, 0);
  return day;
}

function browserExecute(act, fallbackResponse) {
  switch (act.type) {
    case 'url':
      window.open(act.value, '_blank', 'noopener');
      respond(fallbackResponse || `Opened ${act.value}.`);
      return;
    case 'info': {
      const now = new Date();
      const text = act.kind === 'time'
        ? `It's ${now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}.`
        : `Today is ${now.toLocaleDateString([], { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' })}.`;
      respond(text);
      return;
    }
    case 'speak':
      respond(act.value);
      return;
    case 'weather':
      fetchWeather(act.city || '').then((t) =>
        respond(t || 'I couldn’t reach a weather service right now.'));
      return;
    case 'websearch': {
      const q = act.query || '';
      fetchDdg(q).then((a) => {
        if (a) respond(a);
        else {
          window.open(`https://www.google.com/search?q=${encodeURIComponent(q)}`, '_blank', 'noopener');
          respond('No instant answer — I opened the search results.');
        }
      });
      return;
    }
    case 'calendar': {
      const events = JSON.parse(localStorage.getItem('lala.calendar') || '[]');
      if (act.op === 'list') {
        const upcoming = events
          .map((e) => ({ ...e, ts: Date.parse(e.when) }))
          .filter((e) => e.ts > Date.now() - 3600e3)
          .sort((a, b) => a.ts - b.ts)
          .slice(0, 5);
        respond(upcoming.length
          ? 'Up next: ' + upcoming.map((e) => `${e.title} — ${new Date(e.ts).toLocaleString([], { weekday: 'short', hour: '2-digit', minute: '2-digit' })}`).join('; ') + '.'
          : 'Your calendar is clear — nothing scheduled.');
        return;
      }
      const when = calParseWhen(act.text || '');
      if (!when) {
        respond('I need a time — try “add dentist appointment tomorrow at 3 pm”.');
        return;
      }
      const title = (act.text || '').replace(/\b(?:to|on) my calendar\b/g, '')
        .split(/\b(?:today|tomorrow|tonight|monday|tuesday|wednesday|thursday|friday|saturday|sunday|at)\b/)[0].trim() || 'event';
      events.push({ when: when.toISOString(), title });
      localStorage.setItem('lala.calendar', JSON.stringify(events));
      respond(`Added “${title}” to your calendar.`);
      return;
    }
    case 'lights':
      respond('Smart lights need the desktop app — configure Hue or Home Assistant in its Settings.');
      return;
    case 'clipboard':
      navigator.clipboard
        .writeText(act.value === '$last' ? state.lastTranscript : act.value)
        .then(() => respond('Copied to clipboard.'))
        .catch(() => respond('Clipboard blocked by the browser.', { silent: false }));
      return;
    case 'window':
    case 'quit':
      respond('This is the web preview — download the desktop app to control windows and apps.');
      return;
    default:
      respond(`“${fallbackResponse || act.type}” needs the desktop app. Run \`npm start\` for full system control.`, {});
  }
}

/* ------------------------------------------------------------- dictation */

function startDictation() {
  state.dictation = true;
  state.dictBuf = [];
  $('#dictation-bar').classList.remove('hidden');
  setStatusLine('Dictation running — speak freely.');
  respond('Dictation started. Speak freely — I’ll collect everything until you say “stop dictation”.');
}

async function endDictation() {
  state.dictation = false;
  $('#dictation-bar').classList.add('hidden');
  setStatusLine('');
  const text = state.dictBuf.join(' ');
  state.dictBuf = [];
  if (!text) {
    respond('Dictation stopped — I didn’t catch anything.');
    return;
  }
  addLog('lala', `📝 Dictation: ${text}`);
  try {
    if (desktop) await window.lala.executeAction({ type: 'clipboard', value: text }, {});
    else await navigator.clipboard.writeText(text);
    respond(`Got it — ${text.split(/\s+/).length} words copied to your clipboard.`);
  } catch {
    respond(`Dictation finished: “${text}”`);
  }
}

/* ---------------------------------------------------- desktop push-to-talk */

async function pickEngine() {
  const status = state.status || (await window.lala.asrStatus());
  state.status = status;
  const pref = state.settings.engine;
  if (pref === 'offline') return status.modelReady ? 'offline' : null;
  if (pref === 'cloud') return state.settings.openaiKey ? 'cloud' : null;
  if (pref === 'deepgram') return state.settings.deepgramKey ? 'deepgram' : null;
  // auto
  if (status.modelReady) return 'offline';
  if (state.settings.deepgramKey) return 'deepgram';
  if (state.settings.openaiKey) return 'cloud';
  return null;
}

async function startPTT() {
  if (state.pttActive) return;
  // Push-to-talk is a manual barge-in: stop any ongoing reply first.
  if ('speechSynthesis' in window) speechSynthesis.cancel();
  state.abortCtl?.abort();
  const engine = await pickEngine();
  if (!engine) {
    toast('No speech engine ready — open Settings (download the offline model or add an OpenAI key).', 'warn');
    switchTab('settings');
    return;
  }
  try {
    await window.lala.sttStart();
    state.ptt = await startStreamCapture({
      onChunk: (pcm) => {
        // Streaming STT: live partial transcript while holding Space.
        window.lala.sttFeed(pcm).then((r) => {
          if (r && r.partial) showInterim(r.partial);
        });
      }
    });
  } catch {
    toast('Microphone unavailable — check OS permissions.', 'error');
    return;
  }
  state.pttActive = true;
  state._engine = engine;
  setOrbMode('recording');
  setChipState('listening');
  setStatusLine(engine === 'offline' ? 'Listening (offline)…' : 'Listening (cloud)…');
}

async function endPTT() {
  if (!state.pttActive) return;
  state.pttActive = false;
  const capture = state.ptt;
  state.ptt = null;
  const { pcm } = await capture.stop();
  await finishPTT(pcm);
}

async function finishPTT(pcm) {
  setOrbMode('idle');
  setChipState('thinking…');
  setStatusLine('Transcribing…');
  showInterim('');

  let text = '';
  if (state._engine === 'offline') {
    const r = await window.lala.sttFinish();
    text = (r && r.text) || '';
  } else {
    const result = await window.lala.transcribe({ engine: state._engine, pcm });
    await window.lala.sttFinish();
    if (!result.ok) {
      toast(result.error || 'Transcription failed.', 'error');
      addLog('sys', `ASR error: ${result.error}`);
      setStatusLine('');
      setChipState('idle');
      return;
    }
    text = result.text || '';
  }

  setStatusLine('');
  setChipState('idle');

  if (text) {
    if (state.settings.saveRecordings !== false) {
      window.lala.saveRecording(pcm, text).then((r) => {
        if (r && r.ok) addLog('sys', `🎙 recording saved: ${r.path.split(/[\\/]/).pop()}`);
      }).catch(() => {});
    }
    await handleTranscript(text);
  } else {
    toast('I didn’t catch anything — try again.', 'warn');
  }
}

/* ------------------------------------------------- barge-in (interruption)
 * While TTS plays the mic stays open. If the user starts speaking:
 *   1) playback stops immediately  2) the in-flight generation is aborted
 *   3) a new listening cycle starts (auto-endpointed capture → transcript).
 * The wake stream handles this when armed; this monitor covers the rest. */

async function beginBargeCycle() {
  if (state.pttActive) return;
  const engine = await pickEngine();
  if (!engine) return;
  state._engine = engine;
  setOrbMode('recording');
  setChipState('listening');
  setStatusLine('Yes? I’m listening…');
  await window.lala.sttStart();
  state.pttActive = true;
  state.ptt = await startStreamCapture({
    autoStop: true,
    onChunk: (pcm) => {
      window.lala.sttFeed(pcm).then((r) => {
        if (r && r.partial) showInterim(r.partial);
      });
    },
    onAutoStop: (pcm) => {
      state.pttActive = false;
      state.ptt = null;
      finishPTT(pcm);
    }
  });
}

async function armBargeMonitor() {
  if (!desktop || state.bargeMon || state.wakeListener || state.pttActive) return;
  if (!('speechSynthesis' in window)) return;
  try {
    state.bargeMon = await startBargeMonitor({
      onSpeech: () => {
        // 1) stop playback  2) cancel generation  3) new cycle
        speechSynthesis.cancel();
        state.abortCtl?.abort();
        state.bargeMon = null;
        beginBargeCycle();
      }
    });
    // retire the monitor once the reply finishes speaking
    const poll = setInterval(() => {
      if (!speechSynthesis.speaking && !speechSynthesis.pending) {
        clearInterval(poll);
        state.bargeMon?.stop();
        state.bargeMon = null;
      }
    }, 500);
  } catch { /* mic busy/unavailable — wake-stream barge-in still applies */ }
}

function cancelPTT() {
  if (!state.pttActive) return;
  state.pttActive = false;
  if (state.ptt) {
    state.ptt.stop().catch(() => {});
    state.ptt = null;
  }
  window.lala.sttFinish().catch(() => {});
  setOrbMode('idle');
  setChipState('idle');
  setStatusLine('');
}

/* ------------------------------------------------------------ wake word */

let audioCtx = null;

function beep() {
  try {
    audioCtx = audioCtx || new (window.AudioContext || window.webkitAudioContext)();
    const osc = audioCtx.createOscillator();
    const gain = audioCtx.createGain();
    osc.type = 'sine';
    osc.frequency.value = 880;
    gain.gain.value = 0.12;
    osc.connect(gain).connect(audioCtx.destination);
    osc.start();
    osc.stop(audioCtx.currentTime + 0.15);
  } catch { /* audio not critical */ }
}

function wakeWanted() {
  return state.settings.wakeWord !== false;
}

function updateWakeUI(active) {
  const btn = $('#wake-toggle');
  if (!btn) return;
  btn.classList.toggle('on', active);
  btn.textContent = active ? '👂 “Hey Laala” on' : '👂‍ wake word off';
  btn.title = active ? 'LALA is listening for the wake word (locally)' : 'Click to arm the wake word';
  const orb = $('#orb');
  orb.classList.toggle('wake-armed', active);
}

async function startWake() {
  if (!desktop || state.wakeListener || !wakeWanted()) return;
  state.status = state.status || (await window.lala.asrStatus());
  if (!state.status.wakeAvailable) {
    updateWakeUI(false);
    return;
  }
  try {
    state.wakeListener = createWakeListener({
      onWake: () => {
        state.followHold = false;
        beep();
        setOrbMode('recording');
        setChipState('listening');
        setStatusLine('Yes? Speak your command…');
      },
      onFollowEnd: () => {
        setOrbMode('idle');
        setChipState('idle');
        setStatusLine('Say “Hey Laala” to wake me.');
      },
      continuous: () => state.settings.continuousConversation !== false && !state.followHold,
      onPartial: (t) => showInterim(t),
      onBarge: () => {
        // User talked over LALA: cut her voice, cancel generation, listen.
        state.followHold = false;
        if ('speechSynthesis' in window) speechSynthesis.cancel();
        state.abortCtl?.abort();
        setOrbMode('recording');
        setChipState('listening');
        setStatusLine('Yes? I’m listening…');
      },
      canBarge: () => ('speechSynthesis' in window && speechSynthesis.speaking),
      onCommand: (text) => {
        setOrbMode('idle');
        setChipState('idle');
        showInterim('');
        setStatusLine('Say “Hey Laala” to wake me.');
        handleTranscript(text);
      }
    });
    await state.wakeListener.start(window.lala);
    updateWakeUI(true);
    if (!state.pttActive) setStatusLine('Say “Hey Laala” to wake me.');
    addLog('sys', 'Wake word armed — say “Hey Laala”.');
  } catch (err) {
    state.wakeListener = null;
    updateWakeUI(false);
    toast(`Wake word unavailable: ${err.message || err}`, 'warn');
  }
}

function stopWake() {
  if (!state.wakeListener) return;
  state.wakeListener.stop(window.lala);
  state.wakeListener = null;
  updateWakeUI(false);
  if (!state.pttActive) setStatusLine('');
}

async function toggleWake() {
  const next = !wakeWanted();
  state.settings.wakeWord = next;
  await persistSettings();
  if (next) await startWake();
  else stopWake();
  renderSettingsForm();
}

/* ------------------------------------------------------- browser listening */

function toggleWebListening() {
  if (!state.webSpeech) return;
  if (state.webSpeech.active) {
    state.webSpeech.stop();
    state.listening = false;
    setOrbMode('idle');
    setChipState('idle');
    setStatusLine('');
  } else {
    state.webSpeech.start(state.settings.language);
    state.listening = true;
    setOrbMode('listening');
    setChipState('listening');
    setStatusLine('Listening… speak a command.');
  }
}

function setupWebSpeech() {
  state.webSpeech = createWebSpeech({
    interim: (t) => showInterim(t),
    final: (t) => {
      if (wakeWanted()) {
        const w = detectWakeWord(t);
        if (w.wake) {
          if (w.rest) return handleTranscript(w.rest);
          beep();
          respond('Yes? I’m listening.');
          return;
        }
      }
      handleTranscript(t);
    },
    status: (s) => {
      if (s === 'listening') setChipState('listening');
      else if (!state.pttActive) setChipState('idle');
    },
    error: (msg) => toast(msg, 'error')
  });

  if (!state.webSpeech) {
    toast('This browser has no SpeechRecognition — use Chrome/Edge, or run the desktop app.', 'warn');
    $('#hint').innerHTML = 'Web Speech not available here. Click the suggestion chips below, or run the desktop app.';
    return;
  }

  if (state.settings.continuous) {
    // Browsers like a user gesture before touching the mic: start on first interaction.
    const arm = (e) => {
      // Clicks on the orb are handled by its own handler — don't double-toggle.
      if (e.target && e.target.closest && e.target.closest('#orb')) return;
      if (!state.webSpeech.active && state.settings.continuous) toggleWebListening();
      window.removeEventListener('pointerdown', arm);
      window.removeEventListener('keydown', arm);
    };
    window.addEventListener('pointerdown', arm);
    window.addEventListener('keydown', arm);
    setStatusLine('Click anywhere (or the orb) to start listening.');
  }
}

/* --------------------------------------------------------- engine status */

async function refreshEngineChip() {
  if (!desktop) {
    $('#chip-mode').textContent = 'Browser preview';
    $('#chip-engine').textContent = 'Web Speech API';
    return;
  }
  $('#chip-mode').textContent = `Desktop · ${window.lala.platform}`;
  state.status = await window.lala.asrStatus();
  const s = state.status;
  const key = state.settings.openaiKey;
  const dg = state.settings.deepgramKey;
  if (s.modelReady && (key || dg)) $('#chip-engine').textContent = 'Offline + Cloud ready';
  else if (s.modelReady) $('#chip-engine').textContent = 'Offline ready';
  else if (dg) $('#chip-engine').textContent = 'Deepgram ready';
  else if (key) $('#chip-engine').textContent = 'Cloud (Whisper) ready';
  else $('#chip-engine').textContent = 'Engine setup needed';
  renderModelStatus();
}

function renderModelStatus() {
  if (!desktop) return;
  const el = $('#model-status');
  const btn = $('#download-model');
  const s = state.status || {};
  if (!s.voskInstalled) {
    el.textContent = 'Vosk is not installed. Run "npm install vosk" in the project folder and restart LALA to enable offline mode.';
    btn.disabled = true;
    btn.textContent = 'Offline engine not installed';
  } else if (s.modelReady) {
    el.textContent = `Offline model ready (${s.modelDir}).`;
    btn.disabled = true;
    btn.textContent = 'Model downloaded ✓';
  } else {
    el.textContent = 'Offline model not downloaded yet.';
    btn.disabled = false;
    btn.textContent = 'Download model (~40 MB)';
  }
}

/* ----------------------------------------------------------- skills panel */

const LIGHT_COLORS = ['red', 'orange', 'yellow', 'green', 'cyan', 'blue', 'purple', 'pink', 'warm', 'white', 'cool'];
const SWATCH_HEX = {
  red: '#ef4444', orange: '#f97316', yellow: '#eab308', green: '#22c55e',
  cyan: '#06b6d4', blue: '#3b82f6', purple: '#a855f7', pink: '#ec4899',
  warm: '#ffd9a0', white: '#f8fafc', cool: '#bfdbfe'
};

async function skillLights(action) {
  if (desktop) {
    const r = await window.lala.executeAction({ type: 'lights', ...action }, {});
    $('#lights-status').textContent = r.message || '';
  } else {
    $('#lights-status').textContent = 'Lights need the desktop app (Hue / Home Assistant).';
  }
}

async function renderCalendar() {
  const events = desktop
    ? await window.lala.getCalendar()
    : JSON.parse(localStorage.getItem('lala.calendar') || '[]');
  const list = $('#cal-list');
  list.innerHTML = '';
  const sorted = events
    .map((e) => ({ ...e, ts: Date.parse(e.when) }))
    .filter((e) => !Number.isNaN(e.ts))
    .sort((a, b) => a.ts - b.ts);
  if (!sorted.length) {
    const li = document.createElement('li');
    li.className = 'muted';
    li.textContent = 'Nothing scheduled — add one above or say “add … at 3pm”.';
    list.appendChild(li);
    return;
  }
  for (const e of sorted.slice(0, 12)) {
    const li = document.createElement('li');
    li.className = 'cmd-item';
    const left = document.createElement('div');
    const t = document.createElement('div');
    t.className = 'cmd-phrases';
    t.textContent = e.title;
    const when = document.createElement('div');
    when.className = 'cmd-meta';
    when.textContent = new Date(e.ts).toLocaleString([], {
      weekday: 'short', day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit'
    });
    left.append(t, when);
    const del = document.createElement('button');
    del.className = 'cmd-del';
    del.title = 'Delete';
    del.textContent = '✕';
    del.onclick = async () => {
      if (desktop) await window.lala.delCalendar(e.id);
      else {
        const rest = JSON.parse(localStorage.getItem('lala.calendar') || '[]')
          .filter((x) => x.id !== e.id);
        localStorage.setItem('lala.calendar', JSON.stringify(rest));
      }
      renderCalendar();
    };
    li.append(left, del);
    list.appendChild(li);
  }
}

function bindSkills() {
  $('#skill-weather').addEventListener('click', async () => {
    $('#weather-card').textContent = 'Fetching…';
    const t = await fetchWeather($('#skill-city').value.trim());
    $('#weather-card').textContent = t || 'Could not reach a weather service.';
  });
  $('#skill-city').addEventListener('keydown', (e) => {
    if (e.key === 'Enter') $('#skill-weather').click();
  });

  $('#skill-search').addEventListener('click', async () => {
    const q = $('#skill-query').value.trim();
    if (!q) return;
    $('#search-card').textContent = 'Searching…';
    $('#search-links').innerHTML = '';
    const a = await fetchDdg(q);
    $('#search-card').textContent = a || 'No instant answer found.';
    const links = await fetchWikiResults(q);
    for (const l of links) {
      const btn = document.createElement('button');
      btn.className = 'phrase-chip';
      btn.textContent = l.title;
      btn.onclick = () => window.open(l.url, '_blank', 'noopener');
      $('#search-links').appendChild(btn);
    }
  });
  $('#skill-query').addEventListener('keydown', (e) => {
    if (e.key === 'Enter') $('#skill-search').click();
  });

  $('#cal-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    const title = $('#cal-title').value.trim();
    if (!title) return;
    const day = $('#cal-day').value;
    const [hh, mm] = $('#cal-time').value.split(':').map(Number);
    const when = new Date();
    if (/^\d+$/.test(day)) when.setDate(when.getDate() + Number(day));
    else {
      const names = ['sunday', 'monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday'];
      when.setDate(when.getDate() + ((names.indexOf(day) - when.getDay() + 7) % 7 || 7));
    }
    when.setHours(hh, mm, 0, 0);
    const ev = { id: `ev${Date.now()}`, when: when.toISOString(), title };
    if (desktop) await window.lala.addCalendar(ev);
    else {
      const arr = JSON.parse(localStorage.getItem('lala.calendar') || '[]');
      arr.push(ev);
      localStorage.setItem('lala.calendar', JSON.stringify(arr));
    }
    $('#cal-title').value = '';
    renderCalendar();
    toast('Event added.');
  });

  $('#lights-on').addEventListener('click', () => skillLights({ op: 'on' }));
  $('#lights-off').addEventListener('click', () => skillLights({ op: 'off' }));
  $('#lights-bri').addEventListener('change', (e) => skillLights({ op: 'set', value: Number(e.target.value) }));

  const wrap = $('#lights-colors');
  for (const color of LIGHT_COLORS) {
    const b = document.createElement('button');
    b.className = 'swatch';
    b.title = color;
    b.style.background = SWATCH_HEX[color];
    b.onclick = () => skillLights({ op: 'color', color });
    wrap.appendChild(b);
  }

  // Calendar .ics interop (Google / Outlook / Apple)
  $('#cal-export').addEventListener('click', async () => {
    const events = desktop
      ? await window.lala.getCalendar()
      : JSON.parse(localStorage.getItem('lala.calendar') || '[]');
    const blob = new Blob([buildIcs(events)], { type: 'text/calendar' });
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = 'lala-calendar.ics';
    a.click();
    URL.revokeObjectURL(a.href);
    toast('Calendar exported as .ics');
  });
  $('#cal-import').addEventListener('click', () => $('#cal-file').click());
  $('#cal-file').addEventListener('change', async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    const imported = parseIcs(await file.text());
    if (desktop) {
      for (const ev of imported) await window.lala.addCalendar(ev);
    } else {
      const arr = JSON.parse(localStorage.getItem('lala.calendar') || '[]');
      localStorage.setItem('lala.calendar', JSON.stringify([...arr, ...imported]));
    }
    renderCalendar();
    toast(`Imported ${imported.length} event(s).`);
    e.target.value = '';
  });

  // Config sync with the Python brain (one pair of keys, two bodies)
  const SYNC_PAIRS = [
    ['name', 'name'], ['openai_api_key', 'openaiKey'], ['deepgram_api_key', 'deepgramKey'],
    ['elevenlabs_api_key', 'elevenlabsKey'], ['stt_language', 'language'],
    ['save_recordings', 'saveRecordings'], ['continuous_conversation', 'continuousConversation'],
    ['prefer_silero', 'preferSilero'], ['lights_provider', 'lightsProvider'],
    ['hue_ip', 'hueIp'], ['hue_key', 'hueKey'], ['ha_url', 'haUrl'],
    ['ha_token', 'haToken'], ['wled_ip', 'wledIp']
  ];
  $('#brain-pull').addEventListener('click', async () => {
    const base = (state.settings.brainUrl || 'http://127.0.0.1:8420').replace(/\/+$/, '');
    try {
      const res = await fetch(`${base}/config`, { signal: AbortSignal.timeout(3000) });
      const j = await res.json();
      if (!j.ok) throw new Error(j.error || 'bad response');
      for (const [py, js] of SYNC_PAIRS) {
        if (j.config[py] !== undefined) state.settings[js] = j.config[py];
      }
      await persistSettings();
      renderSettingsForm();
      toast('Config pulled from the Python brain.');
    } catch (err) {
      toast(`Brain unreachable — is --serve running? (${err.message})`, 'warn');
    }
  });
  $('#brain-push').addEventListener('click', async () => {
    const base = (state.settings.brainUrl || 'http://127.0.0.1:8420').replace(/\/+$/, '');
    const patch = {};
    for (const [py, js] of SYNC_PAIRS) {
      if (state.settings[js] !== undefined) patch[js] = state.settings[js];
    }
    try {
      const res = await fetch(`${base}/config`, {
        method: 'POST',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify(patch),
        signal: AbortSignal.timeout(3000)
      });
      const j = await res.json();
      toast(j.ok ? `Pushed ${j.saved.length} settings to the brain.` : 'Push failed.', j.ok ? '' : 'error');
    } catch {
      toast('Brain unreachable — is --serve running?', 'warn');
    }
  });

  renderCalendar();
}

/* ------------------------------------------------------------- demo mode */

const delay = (ms) => new Promise((r) => setTimeout(r, ms));

async function waitSilence(timeoutMs = 5000) {
  if (!('speechSynthesis' in window) || !state.settings.voiceResponses) return delay(700);
  await delay(200);
  const t0 = Date.now();
  while ((speechSynthesis.speaking || speechSynthesis.pending) && Date.now() - t0 < timeoutMs) {
    await delay(120);
  }
}

const DEMO_SCRIPT = [
  'hey laala',
  'what time is it',
  'weather in hyderabad',
  'add demo meeting tomorrow at 10am',
  'lights to blue',
  'flip a coin',
  'tell me a joke',
  'stop listening'
];

async function runDemo() {
  if (state.demoRunning) return;
  state.demoRunning = true;
  const btn = $('#demo-btn');
  btn.disabled = true;
  btn.textContent = '● demo running…';
  try {
    for (const text of DEMO_SCRIPT) {
      setOrbMode('listening');
      showInterim(text);
      await delay(900);
      showInterim('');
      if (text === 'hey laala') {
        addLog('you', text);
        beep();
        respond('Yes? I’m listening…');
      } else {
        await handleTranscript(text);
      }
      setOrbMode('idle');
      await waitSilence();
      await delay(350);
    }
    respond('That’s LALA — say “Hey Laala”, or click the orb, to try it yourself!');
  } finally {
    state.demoRunning = false;
    btn.disabled = false;
    btn.textContent = '▶ Run demo';
    setOrbMode('idle');
  }
}

/* ------------------------------------------------------------ UI binding */

function switchTab(name) {
  $$('.tab').forEach((t) => t.classList.toggle('active', t.dataset.tab === name));
  $$('.tabpane').forEach((p) => p.classList.toggle('active', p.id === `tab-${name}`));
}

function renderCommands() {
  const list = $('#cmd-list');
  list.innerHTML = '';
  if (!state.custom.length) {
    const li = document.createElement('li');
    li.className = 'muted';
    li.textContent = 'No custom commands yet — add one above.';
    list.appendChild(li);
  }
  for (const cmd of state.custom) {
    const li = document.createElement('li');
    li.className = 'cmd-item';
    const left = document.createElement('div');
    const phrases = document.createElement('div');
    phrases.className = 'cmd-phrases';
    phrases.textContent = cmd.phrases.join(' · ');
    const meta = document.createElement('div');
    meta.className = 'cmd-meta';
    const v = cmd.action?.value;
    meta.textContent = `${cmd.action?.type}${typeof v === 'string' ? ` → ${v.length > 60 ? v.slice(0, 60) + '…' : v}` : ''}`;
    left.append(phrases, meta);
    const del = document.createElement('button');
    del.className = 'cmd-del';
    del.title = 'Delete';
    del.textContent = '✕';
    del.onclick = async () => {
      state.custom = state.custom.filter((c) => c.id !== cmd.id);
      await persistCustom();
      renderCommands();
      renderHelp();
    };
    li.append(left, del);
    list.appendChild(li);
  }
}

function renderHelp() {
  const wrap = $('#help-list');
  wrap.innerHTML = '';

  const groups = [
    { title: 'Your commands', cmds: state.custom },
    { title: 'Built-in commands', cmds: state.defaults }
  ];

  for (const group of groups) {
    if (!group.cmds.length) continue;
    const g = document.createElement('div');
    g.className = 'help-group';
    const h = document.createElement('h4');
    h.textContent = group.title;
    g.appendChild(h);
    for (const cmd of group.cmds) {
      const row = document.createElement('div');
      row.className = 'help-row';
      const desc = document.createElement('span');
      desc.className = 'desc';
      desc.textContent = cmd.description || cmd.id;
      row.appendChild(desc);
      for (const phrase of cmd.phrases) {
        const chip = document.createElement('button');
        chip.className = 'phrase-chip';
        chip.textContent = phrase;
        chip.title = 'Click to run this command';
        chip.onclick = () => handleTranscript(phrase.replace(/<[^>]+>/g, 'something'));
        row.appendChild(chip);
      }
      g.appendChild(row);
    }
    wrap.appendChild(g);
  }
}

function renderSettingsForm() {
  const s = state.settings;
  $$('input[name="engine"]').forEach((r) => { r.checked = r.value === s.engine; });
  $('#openai-key').value = s.openaiKey || '';
  $('#deepgram-key').value = s.deepgramKey || '';
  $('#whisper-model').value = s.whisperModel || 'whisper-1';
  $('#language').value = s.language || 'en-US';
  $('#voice-responses').checked = !!s.voiceResponses;
  $('#continuous').checked = !!s.continuous;
  $('#wake-word').checked = wakeWanted();
  $('#use-brain').checked = s.useBrain !== false;
  $('#brain-url').value = s.brainUrl || 'http://127.0.0.1:8420';
  $('#hw-accel').checked = s.hwAccel !== false;
  $('#save-recordings').checked = s.saveRecordings !== false;
  $('#continuous-conversation').checked = s.continuousConversation !== false;
  $('#lights-provider').value = s.lightsProvider || 'auto';
  $('#hue-ip').value = s.hueIp || '';
  $('#hue-key').value = s.hueKey || '';
  $('#ha-url').value = s.haUrl || '';
  $('#ha-token').value = s.haToken || '';
  $('#wled-ip').value = s.wledIp || '';
  $('#wake-wrap').classList.toggle('hidden', !desktop);
  $('#hwaccel-wrap').classList.toggle('hidden', !desktop);
  $('#contconv-wrap').classList.toggle('hidden', !desktop);
  $('#continuous-wrap').classList.toggle('hidden', desktop);
  if (!desktop) {
    $('#offline-section').classList.add('hidden');
    $('#download-model').classList.add('hidden');
  }
}

async function persistCustom() {
  if (desktop) await window.lala.saveCustomCommands(state.custom);
  else localStorage.setItem('lala.custom', JSON.stringify(state.custom));
}

async function persistSettings() {
  if (desktop) await window.lala.saveSettings(state.settings);
  else localStorage.setItem('lala.settings', JSON.stringify(state.settings));
}

function bindUI() {
  // Tabs
  $$('.tab').forEach((t) => t.addEventListener('click', () => switchTab(t.dataset.tab)));

  // Wake word toggle
  $('#wake-toggle').addEventListener('click', () => {
    if (!desktop) {
      toast('The wake word runs locally on desktop — this preview uses click-to-listen.', 'warn');
      return;
    }
    toggleWake();
  });

  // Tray menu wake toggle → keep UI in sync
  window.lala?.onWakeSettingChanged?.((value) => {
    state.settings.wakeWord = value;
    renderSettingsForm();
    if (value) startWake();
    else stopWake();
  });

  // Suggestion chips
  $$('.sug').forEach((b) => b.addEventListener('click', () => handleTranscript(b.dataset.say)));
  $('#demo-btn').addEventListener('click', () => runDemo());

  // Orbiting feature nodes — click a capability to run it
  $$('.node').forEach((n) => n.addEventListener('click', () => handleTranscript(n.dataset.say)));

  // Orb
  const orb = $('#orb');
  if (desktop) {
    orb.addEventListener('click', () => (state.pttActive ? endPTT() : startPTT()));
  } else {
    orb.addEventListener('click', () => toggleWebListening());
    $('#hint').innerHTML = 'Click the orb to start/stop listening, or use the suggestion chips below';
  }
  orb.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') orb.click();
  });

  // Push-to-talk with Space (desktop)
  window.addEventListener('keydown', (e) => {
    if (!desktop || e.code !== 'Space') return;
    const target = e.target;
    if (target && target.matches && target.matches('input, textarea, select, [contenteditable]')) return;
    e.preventDefault();
    if (!e.repeat) startPTT();
  });
  window.addEventListener('keyup', (e) => {
    if (!desktop || e.code !== 'Space') return;
    const target = e.target;
    if (target && target.matches && target.matches('input, textarea, select, [contenteditable]')) return;
    e.preventDefault();
    endPTT();
  });
  window.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
      cancelPTT();
      confirmPending(false);
    }
  });

  // Confirm card buttons
  $('#confirm-yes').addEventListener('click', () => confirmPending(true));
  $('#confirm-no').addEventListener('click', () => confirmPending(false));

  // Log
  $('#clear-log').addEventListener('click', () => { $('#log').innerHTML = ''; });

  // Command form
  $('#cmd-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    const phrases = $('#cmd-phrases').value.split(',').map((p) => p.trim().toLowerCase()).filter(Boolean);
    const type = $('#cmd-type').value;
    const value = $('#cmd-value').value.trim();
    const response = $('#cmd-response').value.trim();
    if (!phrases.length || !value) return;
    state.custom.unshift({
      id: `custom-${Date.now()}`,
      description: 'Custom command',
      phrases,
      action: { type, value },
      response: response || `Okay — ${phrases[0]}.`
    });
    await persistCustom();
    renderCommands();
    renderHelp();
    $('#cmd-form').reset();
    toast('Command added.');
  });

  $('#cmd-reset').addEventListener('click', async () => {
    state.custom = [];
    await persistCustom();
    renderCommands();
    renderHelp();
  });

  // Settings
  $('#save-settings').addEventListener('click', async () => {
    state.settings.engine = ($$('input[name="engine"]').find((r) => r.checked) || {}).value || 'auto';
    state.settings.openaiKey = $('#openai-key').value.trim();
    state.settings.deepgramKey = $('#deepgram-key').value.trim();
    state.settings.whisperModel = $('#whisper-model').value;
    state.settings.language = $('#language').value;
    state.settings.voiceResponses = $('#voice-responses').checked;
    state.settings.continuous = $('#continuous').checked;
    state.settings.wakeWord = $('#wake-word').checked;
    state.settings.continuousConversation = $('#continuous-conversation').checked;
    state.settings.useBrain = $('#use-brain').checked;
    state.settings.brainUrl = $('#brain-url').value.trim() || 'http://127.0.0.1:8420';
    state.settings.hwAccel = $('#hw-accel').checked;
    state.settings.saveRecordings = $('#save-recordings').checked;
    state.settings.lightsProvider = $('#lights-provider').value;
    state.settings.hueIp = $('#hue-ip').value.trim();
    state.settings.hueKey = $('#hue-key').value.trim();
    state.settings.haUrl = $('#ha-url').value.trim();
    state.settings.haToken = $('#ha-token').value.trim();
    state.settings.wledIp = $('#wled-ip').value.trim();
    await persistSettings();
    await refreshEngineChip();
    if (desktop) {
      if (wakeWanted() && !state.wakeListener) await startWake();
      else if (!wakeWanted()) stopWake();
    }
    $('#settings-saved').classList.remove('hidden');
    setTimeout(() => $('#settings-saved').classList.add('hidden'), 2000);
  });

  $('#download-model').addEventListener('click', async () => {
    const btn = $('#download-model');
    btn.disabled = true;
    btn.textContent = 'Downloading…';
    $('#model-progress-wrap').classList.remove('hidden');
    const result = await window.lala.downloadModel();
    if (!result.ok) {
      toast(`Model download failed: ${result.error}`, 'error');
      btn.disabled = false;
      btn.textContent = 'Download model (~40 MB)';
    }
    await refreshEngineChip();
  });

  window.lala?.onAsrProgress?.((p) => {
    const bar = $('#model-progress');
    bar.style.width = `${p.pct || 0}%`;
    const btn = $('#download-model');
    if (p.status === 'downloading') btn.textContent = `Downloading… ${p.pct}%`;
    else if (p.status === 'extracting') btn.textContent = 'Extracting…';
  });
}

/* ----------------------------------------------------------------- init */

async function init() {
  if (desktop) {
    const [commands, settings] = await Promise.all([window.lala.getCommands(), window.lala.getSettings()]);
    state.defaults = commands.defaults || [];
    state.custom = commands.custom || [];
    state.settings = { ...DEFAULT_SETTINGS, ...settings };
  } else {
    state.settings = { ...DEFAULT_SETTINGS, ...JSON.parse(localStorage.getItem('lala.settings') || '{}') };
    try {
      const res = await fetch('./commands-default.json');
      state.defaults = await res.json();
    } catch {
      state.defaults = [];
    }
    state.custom = JSON.parse(localStorage.getItem('lala.custom') || '[]');
  }

  bindUI();
  bindSkills();
  renderCommands();
  renderHelp();
  renderSettingsForm();
  await refreshEngineChip();

  if (!desktop) setupWebSpeech();
  else {
    setStatusLine('Hold Space and speak — release to send.');
    addLog('sys', 'LALA desktop ready. Hold Space or click the orb to talk.');
    await startWake();
  }

  switchTab('log');
}

init();
