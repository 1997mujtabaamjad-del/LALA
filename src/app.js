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
import { startCapture, stopCapture, cancelCapture, isCapturing } from './recorder.js';

const desktop = typeof window.lala !== 'undefined';
const $ = (sel) => document.querySelector(sel);
const $$ = (sel) => Array.from(document.querySelectorAll(sel));

const DEFAULT_SETTINGS = {
  engine: 'auto',
  openaiKey: '',
  whisperModel: 'whisper-1',
  language: 'en-US',
  voiceResponses: true,
  continuous: true,
  wakeWord: true,
  continuousConversation: true,
  useBrain: true,
  brainUrl: 'http://127.0.0.1:8420',
  hwAccel: true,
  lightsProvider: 'auto',
  hueIp: '',
  hueKey: '',
  haUrl: '',
  haToken: ''
};

const JOKES = [
  'Why do programmers prefer dark mode? Because light attracts bugs.',
  'I told my computer I needed a break, and it said: no problem, I’ll go to sleep.',
  'Why did the developer go broke? Because he used up all his cache.',
  'There are only 10 kinds of people: those who understand binary and those who don’t.',
  'I would tell you a UDP joke, but you might not get it.'
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
  followHold: false // set after “stop listening” until the next wake
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

function speak(text) {
  if (!state.settings.voiceResponses || !text) return;
  if (!('speechSynthesis' in window)) return;
  speechSynthesis.cancel();
  const utter = new SpeechSynthesisUtterance(text);
  if (preferredVoice) utter.voice = preferredVoice;
  utter.rate = 1.03;
  speechSynthesis.speak(utter);
}

function respond(text, { silent = false } = {}) {
  if (!text) return;
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
    // 3b) Not a command → ask the Python brain (LLM + memory) if it's running.
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
async function askBrain(text) {
  if (state.settings.useBrain === false) return null;
  const base = (state.settings.brainUrl || 'http://127.0.0.1:8420').replace(/\/+$/, '');
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
      const r = await fetch(`https://api.open-meteo.com/v1/forecast?latitude=${place.latitude}&longitude=${place.longitude}&current=temperature_2m,apparent_temperature,relative_humidity_2m,weather_code,wind_speed_10m`);
      const c = (await r.json()).current;
      const words = { 0: 'clear skies', 1: 'mostly clear', 2: 'partly cloudy', 3: 'overcast', 61: 'light rain', 63: 'rain', 95: 'thunderstorms' };
      return `It's ${Math.round(c.temperature_2m)}°C in ${place.name}, ${words[c.weather_code] || 'cloudy'}, feels like ${Math.round(c.apparent_temperature)}°, humidity ${c.relative_humidity_2m}%.`;
    }
    const r = await fetch('https://wttr.in/?format=j1');
    const j = await r.json();
    return `It's ${j.current_condition[0].temp_C}°C in ${j.nearest_area[0].areaName[0].value}, humidity ${j.current_condition[0].humidity}%.`;
  } catch {
    return null;
  }
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
  // auto
  if (status.modelReady) return 'offline';
  if (state.settings.openaiKey) return 'cloud';
  return null;
}

async function startPTT() {
  if (state.pttActive) return;
  // Push-to-talk is a manual barge-in: stop any ongoing reply first.
  if ('speechSynthesis' in window) speechSynthesis.cancel();
  const engine = await pickEngine();
  if (!engine) {
    toast('No speech engine ready — open Settings (download the offline model or add an OpenAI key).', 'warn');
    switchTab('settings');
    return;
  }
  try {
    await startCapture();
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
  setOrbMode('idle');
  setChipState('thinking…');
  setStatusLine('Transcribing…');

  const rec = await stopCapture();
  if (!rec || rec.blob.size < 200) {
    setStatusLine('');
    setChipState('idle');
    return;
  }

  const payload = {
    engine: state._engine,
    recBytes: await rec.blob.arrayBuffer(),
    recMime: rec.mime,
    pcm: rec.pcm
  };

  const result = await window.lala.transcribe(payload);
  setStatusLine('');
  setChipState('idle');

  if (!result.ok) {
    toast(result.error || 'Transcription failed.', 'error');
    addLog('sys', `ASR error: ${result.error}`);
    return;
  }
  if (result.text) await handleTranscript(result.text);
  else toast('I didn’t catch anything — try again.', 'warn');
}

function cancelPTT() {
  if (!state.pttActive) return;
  state.pttActive = false;
  cancelCapture();
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
        // User talked over LALA: cut her voice, listen to them instead.
        state.followHold = false;
        if ('speechSynthesis' in window) speechSynthesis.cancel();
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
  if (s.modelReady && key) $('#chip-engine').textContent = 'Offline + Cloud ready';
  else if (s.modelReady) $('#chip-engine').textContent = 'Offline ready';
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
    const a = await fetchDdg(q);
    $('#search-card').textContent = a || 'No instant answer found.';
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

  renderCalendar();
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
  $('#whisper-model').value = s.whisperModel || 'whisper-1';
  $('#language').value = s.language || 'en-US';
  $('#voice-responses').checked = !!s.voiceResponses;
  $('#continuous').checked = !!s.continuous;
  $('#wake-word').checked = wakeWanted();
  $('#use-brain').checked = s.useBrain !== false;
  $('#brain-url').value = s.brainUrl || 'http://127.0.0.1:8420';
  $('#hw-accel').checked = s.hwAccel !== false;
  $('#continuous-conversation').checked = s.continuousConversation !== false;
  $('#lights-provider').value = s.lightsProvider || 'auto';
  $('#hue-ip').value = s.hueIp || '';
  $('#hue-key').value = s.hueKey || '';
  $('#ha-url').value = s.haUrl || '';
  $('#ha-token').value = s.haToken || '';
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
    state.settings.whisperModel = $('#whisper-model').value;
    state.settings.language = $('#language').value;
    state.settings.voiceResponses = $('#voice-responses').checked;
    state.settings.continuous = $('#continuous').checked;
    state.settings.wakeWord = $('#wake-word').checked;
    state.settings.continuousConversation = $('#continuous-conversation').checked;
    state.settings.useBrain = $('#use-brain').checked;
    state.settings.brainUrl = $('#brain-url').value.trim() || 'http://127.0.0.1:8420';
    state.settings.hwAccel = $('#hw-accel').checked;
    state.settings.lightsProvider = $('#lights-provider').value;
    state.settings.hueIp = $('#hue-ip').value.trim();
    state.settings.hueKey = $('#hue-key').value.trim();
    state.settings.haUrl = $('#ha-url').value.trim();
    state.settings.haToken = $('#ha-token').value.trim();
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
