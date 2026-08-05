'use strict';

/**
 * ASR (speech recognition) engine manager.
 *
 * Two engines:
 *  - "offline": Vosk (npm optional dependency) + a small English model that is
 *    downloaded on demand into the userData folder.
 *  - "cloud":   OpenAI Whisper API — audio recorded in the renderer is sent
 *    here and transcribed with the user's API key.
 */

const fs = require('fs');
const path = require('path');
const https = require('https');
const { URL } = require('url');

const MODEL_NAME = 'vosk-model-small-en-us-0.15';
const MODEL_URL = `https://alphacephei.com/vosk/models/${MODEL_NAME}.zip`;

let vosk = null;
let voskModel = null;
let modelDir = null;
let getWin = null;

const state = {
  voskInstalled: false,
  modelReady: false,
  downloading: false
};

function init({ userDataDir, win }) {
  getWin = win;
  modelDir = path.join(userDataDir, 'models', MODEL_NAME);
  try {
    vosk = require('vosk');
    vosk.setLogLevel(0);
    state.voskInstalled = true;
  } catch {
    state.voskInstalled = false;
  }
  refreshModelReady();
}

function refreshModelReady() {
  state.modelReady = state.voskInstalled && fs.existsSync(path.join(modelDir, 'am', 'final.mdl'));
}

function status() {
  refreshModelReady();
  return { ...state, wakeAvailable: state.voskInstalled && state.modelReady, modelDir };
}

// ---------------------------------------------------------------------------
// Continuous wake-word stream ("Hey LALA")
//
// The renderer feeds 16 kHz PCM chunks while the mic is open. A long-lived
// Vosk recognizer looks for the wake word; once heard, it switches to command
// capture until the renderer detects end-of-speech and calls wakeFinish.
// ---------------------------------------------------------------------------

let wakeRec = null;
let wakeMode = 'idle'; // 'idle' | 'wake-wait' | 'command'
let commandText = '';

function normalizeLite(text) {
  return String(text || '').toLowerCase().replace(/[^a-z0-9 ]+/g, ' ').replace(/\s+/g, ' ').trim();
}

function wakeLooksLike(text) {
  return /(?:^|\s)(?:hey|ok|okay|hello|hi)?\s*(?:laala|lala|la\s+la)(?=\s|$)/.test(normalizeLite(text));
}

function wakeStart() {
  refreshModelReady();
  if (!state.voskInstalled || !state.modelReady) {
    throw new Error('Wake word needs the offline engine — install vosk and download the model first.');
  }
  wakeStop();
  wakeRec = new vosk.Recognizer({ model: getModel(), sampleRate: 16000 });
  wakeMode = 'wake-wait';
  commandText = '';
}

/** Feed a raw 16 kHz mono Int16 PCM chunk. Returns { wake, partial, text }. */
function wakeFeed(pcmBuffer) {
  if (!wakeRec || wakeMode === 'idle') return { wake: false, partial: '' };
  const isFinal = wakeRec.acceptWaveForm(Buffer.from(pcmBuffer));
  const text = isFinal
    ? JSON.parse(wakeRec.finalResult()).text
    : JSON.parse(wakeRec.partialResult()).partial || '';

  if (wakeMode === 'wake-wait') {
    if (wakeLooksLike(text)) {
      wakeMode = 'command';
      commandText = '';
      // Drop any words spoken after the wake word in the same burst.
      const { rest } = splitWake(text);
      if (rest) commandText = rest + ' ';
      wakeRec.reset();
      return { wake: true, partial: '' };
    }
    return { wake: false, partial: '' };
  }

  // Command capture mode: accumulate finalized speech.
  if (isFinal && text) commandText += text + ' ';
  return { wake: false, partial: isFinal ? '' : text };
}

function splitWake(text) {
  const norm = normalizeLite(text);
  const m = norm.match(/(?:^|\s)(?:hey|ok|okay|hello|hi)?\s*(?:laala|lala|la\s+la)(?=\s|$)/);
  if (!m) return { wake: false, rest: '' };
  const rest = (norm.slice(m.index + m[0].length)).trim();
  return { wake: true, rest };
}

/**
 * Barge-in: the user started talking while LALA speaks. Flip the wake stream
 * into command-capture mode so their sentence becomes the next command.
 */
function wakeBarge() {
  if (wakeRec && wakeMode === 'wake-wait') {
    wakeMode = 'command';
    commandText = '';
    return true;
  }
  return false;
}

/** End-of-speech detected by the renderer: return the full command text. */
function wakeFinish() {
  if (!wakeRec || wakeMode !== 'command') {
    wakeMode = wakeRec ? 'wake-wait' : 'idle';
    return { text: '' };
  }
  const tail = JSON.parse(wakeRec.finalResult()).text || '';
  const full = (commandText + ' ' + tail).replace(/\s+/g, ' ').trim();
  wakeRec.reset();
  commandText = '';
  wakeMode = 'wake-wait';
  return { text: full };
}

/**
 * After a command (or a timed-out follow-up window), drop back to wake-wait.
 */
function wakeReset() {
  if (wakeRec) {
    try { wakeRec.reset(); } catch { /* not critical */ }
    wakeMode = 'wake-wait';
    commandText = '';
  }
}

function wakeStop() {
  if (wakeRec) {
    try { wakeRec.free(); } catch { /* already freed */ }
  }
  wakeRec = null;
  wakeMode = 'idle';
  commandText = '';
}

function getModel() {
  if (!voskModel) {
    voskModel = new vosk.Model(modelDir);
  }
  return voskModel;
}

/**
 * Transcribe raw 16-bit PCM, mono, 16 kHz bytes (no WAV header).
 */
async function transcribeOffline(pcmBuffer) {
  if (!state.voskInstalled) {
    throw new Error('Offline engine not installed. Run "npm install vosk" and restart LALA.');
  }
  refreshModelReady();
  if (!state.modelReady) {
    throw new Error('Offline model not downloaded yet — use the button in Settings.');
  }
  const recognizer = new vosk.Recognizer({ model: getModel(), sampleRate: 16000 });
  recognizer.acceptWaveForm(Buffer.from(pcmBuffer));
  const result = JSON.parse(recognizer.finalResult());
  recognizer.free();
  return result.text || '';
}

/**
 * Transcribe via the OpenAI Whisper API. Accepts any container the renderer
 * recorded (typically audio/webm).
 */
async function transcribeCloud(buffer, mime, settings) {
  if (!settings.openaiKey) {
    throw new Error('Add your OpenAI API key in Settings to use cloud recognition.');
  }
  const form = new FormData();
  form.append('file', new Blob([buffer], { type: mime || 'audio/webm' }), 'lala-recording.webm');
  form.append('model', settings.whisperModel || 'whisper-1');
  const lang = String(settings.language || '').split('-')[0];
  if (lang) form.append('language', lang);

  const res = await fetch('https://api.openai.com/v1/audio/transcriptions', {
    method: 'POST',
    headers: { Authorization: `Bearer ${settings.openaiKey}` },
    body: form
  });

  if (!res.ok) {
    let message = `HTTP ${res.status}`;
    try {
      const body = await res.json();
      if (body && body.error && body.error.message) message = body.error.message;
    } catch { /* ignore parse errors */ }
    throw new Error(`Whisper API error: ${message}`);
  }

  const json = await res.json();
  return json.text || '';
}

function sendProgress(payload) {
  const win = getWin && getWin();
  if (win && !win.isDestroyed()) win.webContents.send('asr:progress', payload);
}

/**
 * Download + extract the small English Vosk model (~40 MB).
 */
function downloadModel() {
  return new Promise((resolve, reject) => {
    if (state.downloading) {
      reject(new Error('A download is already in progress.'));
      return;
    }
    refreshModelReady();
    if (state.modelReady) {
      resolve(true);
      return;
    }

    state.downloading = true;
    const modelsRoot = path.dirname(modelDir);
    fs.mkdirSync(modelsRoot, { recursive: true });
    const zipPath = path.join(modelsRoot, `${MODEL_NAME}.zip`);
    const file = fs.createWriteStream(zipPath);

    let received = 0;
    let total = 0;
    let lastPct = -1;

    const get = (url, redirectsLeft) => {
      https.get(url, { headers: { 'User-Agent': 'LALA' } }, (res) => {
        if ([301, 302, 303, 307, 308].includes(res.statusCode) && res.headers.location && redirectsLeft > 0) {
          res.resume();
          get(new URL(res.headers.location, url).toString(), redirectsLeft - 1);
          return;
        }
        if (res.statusCode !== 200) {
          res.resume();
          state.downloading = false;
          reject(new Error(`Model download failed: HTTP ${res.statusCode}`));
          return;
        }
        total = parseInt(res.headers['content-length'] || '0', 10);
        res.on('data', (chunk) => {
          received += chunk.length;
          if (total > 0) {
            const pct = Math.min(100, Math.floor((received / total) * 100));
            if (pct !== lastPct) {
              lastPct = pct;
              sendProgress({ status: 'downloading', pct });
            }
          }
        });
        res.pipe(file);
        file.on('finish', async () => {
          file.close();
          try {
            sendProgress({ status: 'extracting', pct: 100 });
            const extract = require('extract-zip');
            await extract(zipPath, { dir: modelsRoot });
            try { fs.unlinkSync(zipPath); } catch { /* not critical */ }
            refreshModelReady();
            state.downloading = false;
            sendProgress({ status: 'done', pct: 100 });
            resolve(true);
          } catch (err) {
            state.downloading = false;
            reject(err);
          }
        });
      }).on('error', (err) => {
        state.downloading = false;
        reject(err);
      });
    };

    get(MODEL_URL, 5);
  });
}

module.exports = {
  init,
  status,
  transcribeOffline,
  transcribeCloud,
  downloadModel,
  wakeStart,
  wakeFeed,
  wakeFinish,
  wakeBarge,
  wakeReset,
  wakeStop
};
