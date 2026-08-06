'use strict';

const { app, BrowserWindow, ipcMain, session, Tray, Menu, nativeImage } = require('electron');
const path = require('path');
const { spawn } = require('child_process');
const http = require('http');
const fs = require('fs');

const Store = require('./store.cjs');
const actions = require('./actions.cjs');
const asr = require('./asr.cjs');
const vad = require('./vad.cjs');

let store = null;
let mainWindow = null;
let tray = null;
let isQuitting = false;
let brainChild = null; // python brain we started ourselves (killed on quit)

// ---------------------------------------------------------------------------
// Self-contained desktop app: if the Python brain (:8420) isn't running,
// start it from the local .venv so `npm start` / LALA-APP.bat is all you need.
// ---------------------------------------------------------------------------

function brainUp() {
  return new Promise((resolve) => {
    const req = http.get('http://127.0.0.1:8420/status', (res) => {
      res.resume();
      resolve(true);
    });
    req.on('error', () => resolve(false));
    req.setTimeout(1200, () => {
      req.destroy();
      resolve(false);
    });
  });
}

async function ensureBrain() {
  if (await brainUp()) return; // browser app or --serve already running
  const root = path.join(__dirname, '..');
  const py = process.platform === 'win32'
    ? path.join(root, '.venv', 'Scripts', 'python.exe')
    : path.join(root, '.venv', 'bin', 'python');
  if (!fs.existsSync(py)) return; // no venv → commands-only mode
  brainChild = spawn(py, ['-m', 'assistant', '--serve'], {
    cwd: root,
    stdio: 'ignore'
  });
  brainChild.on('error', () => { brainChild = null; });
  for (let i = 0; i < 25 && !(await brainUp()); i++) {
    await new Promise((r) => setTimeout(r, 300));
  }
}

// GPU hardware acceleration for the UI (Chromium). Applies before any window
// is created; toggle lives in Settings → General. Default: on.
try {
  const early = new Store(app.getPath('userData')).getSettings();
  if (early.hwAccel === false) app.disableHardwareAcceleration();
} catch { /* keep acceleration on */ }

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1240,
    height: 820,
    minWidth: 940,
    minHeight: 620,
    backgroundColor: '#050507',
    title: 'LALA — Voice Command Assistant',
    icon: path.join(__dirname, '..', 'assets', 'icon.png'),
    show: false,
    webPreferences: {
      preload: path.join(__dirname, 'preload.cjs'),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: true, // hardened: preload only uses the contextBridge API
      webSecurity: true
    }
  });

  mainWindow.loadFile(path.join(__dirname, '..', 'src', 'index.html'));
  mainWindow.once('ready-to-show', () => mainWindow.show());

  if (process.argv.includes('--dev')) {
    mainWindow.webContents.openDevTools({ mode: 'detach' });
  }

  // Minimize-to-tray instead of quitting.
  mainWindow.on('close', (event) => {
    if (!isQuitting) {
      event.preventDefault();
      mainWindow.hide();
      if (process.platform === 'darwin') app.dock && app.dock.hide();
    }
  });

  mainWindow.on('closed', () => {
    mainWindow = null;
  });
}

function createTray() {
  const icon = nativeImage
    .createFromPath(path.join(__dirname, '..', 'assets', 'tray.png'))
    .resize({ width: 22, height: 22 });
  tray = new Tray(icon);
  tray.setToolTip('LALA — say “Hey LALA”');

  const rebuild = () => {
    const template = [
      {
        label: 'Show LALA',
        click: () => {
          if (mainWindow) {
            if (process.platform === 'darwin') app.dock && app.dock.show();
            mainWindow.show();
            mainWindow.focus();
          } else {
            createWindow();
          }
        }
      },
      {
        label: `Wake word: ${store.getSettings().wakeWord === false ? 'off' : 'on'}`,
        click: () => {
          const cur = store.getSettings().wakeWord !== false;
          store.saveSettings({ wakeWord: !cur });
          if (mainWindow) {
            mainWindow.webContents.send('settings:wake-changed', !cur);
            mainWindow.show();
            mainWindow.focus();
          }
        }
      },
      { type: 'separator' },
      {
        label: 'Quit LALA',
        click: () => {
          isQuitting = true;
          app.quit();
        }
      }
    ];
    tray.setContextMenu(Menu.buildFromTemplate(template));
  };

  rebuild();
  tray.on('click', () => {
    if (mainWindow) mainWindow.show();
    else createWindow();
  });
  tray._rebuild = rebuild;
}

function registerIpc() {
  // ---- Commands & settings -------------------------------------------------
  ipcMain.handle('commands:get', () => ({
    defaults: store.getDefaultCommands(),
    custom: store.getCustomCommands()
  }));
  ipcMain.handle('commands:saveCustom', (_e, custom) => store.saveCustomCommands(custom));

  ipcMain.handle('calendar:get', () => store.getCalendar());
  ipcMain.handle('calendar:add', (_e, event) => {
    const events = store.getCalendar();
    events.push(event);
    return store.saveCalendar(events);
  });
  ipcMain.handle('calendar:del', (_e, id) =>
    store.saveCalendar(store.getCalendar().filter((e) => e.id !== id)));

  ipcMain.handle('settings:get', () => store.getSettings());
  ipcMain.handle('settings:save', (_e, patch) => store.saveSettings(patch));

  // ---- Action execution ----------------------------------------------------
  ipcMain.handle('actions:execute', async (_e, action, ctx) => {
    try {
      return await actions.execute(action, ctx || {}, { win: mainWindow, store });
    } catch (err) {
      return { ok: false, message: `Action failed: ${err.message || err}` };
    }
  });

  // ---- Speech recognition --------------------------------------------------
  ipcMain.handle('asr:status', () => asr.status());

  ipcMain.handle('asr:transcribe', async (_e, payload) => {
    try {
      const settings = store.getSettings();
      let text = '';
      if (payload.engine === 'cloud') {
        const bytes = payload.recBytes
          ? Buffer.from(payload.recBytes)
          : asr.pcmToWav(Buffer.from(payload.pcm));
        text = await asr.transcribeCloud(bytes, payload.recMime || 'audio/wav', settings);
      } else if (payload.engine === 'deepgram') {
        text = await asr.transcribeDeepgram(Buffer.from(payload.pcm), settings);
      } else if (payload.engine === 'offline') {
        text = await asr.transcribeOffline(Buffer.from(payload.pcm));
      } else {
        return { ok: false, error: 'No speech engine selected. Open Settings and pick one.' };
      }
      return { ok: true, text: String(text || '').trim(), engine: payload.engine };
    } catch (err) {
      return { ok: false, error: String(err.message || err) };
    }
  });

  // ---- Streaming STT (push-to-talk live partials) ---------------------------
  ipcMain.handle('stt:start', () => asr.sttStart());
  ipcMain.handle('stt:feed', (_e, pcm) => asr.sttFeed(Buffer.from(pcm)));
  ipcMain.handle('stt:finish', () => asr.sttFinish());

  // ---- Neural VAD (optional) -------------------------------------------------
  ipcMain.handle('vad:status', () => vad.status());
  ipcMain.handle('vad:speech', async (_e, pcm) => ({ p: await vad.speech(pcm) }));

  // ---- Recording storage ------------------------------------------------------
  ipcMain.handle('rec:save', (_e, { pcm, text }) => {
    try {
      const fs = require('fs');
      const dir = require('path').join(app.getPath('userData'), 'Recordings');
      fs.mkdirSync(dir, { recursive: true });
      const stamp = new Date().toISOString().replace(/[:.]/g, '-');
      const wav = require('path').join(dir, `lala-${stamp}.wav`);
      fs.writeFileSync(wav, asr.pcmToWav(Buffer.from(pcm)));
      fs.writeFileSync(wav.replace(/\.wav$/, '.txt'), text || '');
      return { ok: true, path: wav };
    } catch (err) {
      return { ok: false, error: String(err.message || err) };
    }
  });

  ipcMain.handle('asr:downloadModel', async () => {
    try {
      await asr.downloadModel();
      return { ok: true };
    } catch (err) {
      return { ok: false, error: String(err.message || err) };
    }
  });

  // ---- Wake word stream ------------------------------------------------------
  ipcMain.handle('wake:start', async () => {
    try {
      asr.wakeStart();
      return { ok: true };
    } catch (err) {
      return { ok: false, error: String(err.message || err) };
    }
  });
  ipcMain.handle('wake:feed', (_e, pcm) => {
    try {
      return { ok: true, ...asr.wakeFeed(Buffer.from(pcm)) };
    } catch (err) {
      return { ok: false, error: String(err.message || err) };
    }
  });
  ipcMain.handle('wake:finish', () => {
    try {
      return { ok: true, ...asr.wakeFinish() };
    } catch (err) {
      return { ok: false, error: String(err.message || err) };
    }
  });
  ipcMain.handle('wake:barge', () => {
    try {
      return { ok: true, switched: asr.wakeBarge() };
    } catch (err) {
      return { ok: false, error: String(err.message || err) };
    }
  });
  ipcMain.handle('wake:reset', () => {
    asr.wakeReset();
    return { ok: true };
  });
  ipcMain.handle('wake:stop', () => {
    asr.wakeStop();
    return { ok: true };
  });
}

app.whenReady().then(async () => {
  store = new Store(app.getPath('userData'));
  asr.init({ userDataDir: app.getPath('userData'), win: () => mainWindow });
  vad.init(app.getPath('userData'));
  await ensureBrain(); // start the Python brain if nothing is listening on :8420

  session.defaultSession.setPermissionRequestHandler((_wc, permission, cb) => {
    const allowed = ['media', 'audioCapture', 'microphone', 'clipboard-read', 'clipboard-sanitized-write'];
    cb(allowed.includes(permission));
  });

  registerIpc();
  createWindow();
  createTray();

  app.on('activate', () => {
    if (mainWindow) mainWindow.show();
    else createWindow();
  });
});

app.on('before-quit', () => {
  isQuitting = true;
  if (brainChild) { // stop the brain we started (leave a user's own brain alone)
    try { brainChild.kill(); } catch { /* already gone */ }
    brainChild = null;
  }
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') app.quit();
});
