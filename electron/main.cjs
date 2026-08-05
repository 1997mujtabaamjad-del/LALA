'use strict';

const { app, BrowserWindow, ipcMain, session, Tray, Menu, nativeImage } = require('electron');
const path = require('path');

const Store = require('./store.cjs');
const actions = require('./actions.cjs');
const asr = require('./asr.cjs');

let store = null;
let mainWindow = null;
let tray = null;
let isQuitting = false;

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
    backgroundColor: '#0b1020',
    title: 'LALA — Voice Command Assistant',
    icon: path.join(__dirname, '..', 'assets', 'icon.png'),
    show: false,
    webPreferences: {
      preload: path.join(__dirname, 'preload.cjs'),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: false
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

  ipcMain.handle('settings:get', () => store.getSettings());
  ipcMain.handle('settings:save', (_e, patch) => store.saveSettings(patch));

  // ---- Action execution ----------------------------------------------------
  ipcMain.handle('actions:execute', async (_e, action, ctx) => {
    try {
      return await actions.execute(action, ctx || {}, { win: mainWindow });
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
        text = await asr.transcribeCloud(Buffer.from(payload.recBytes), payload.recMime, settings);
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
  ipcMain.handle('wake:stop', () => {
    asr.wakeStop();
    return { ok: true };
  });
}

app.whenReady().then(() => {
  store = new Store(app.getPath('userData'));
  asr.init({ userDataDir: app.getPath('userData'), win: () => mainWindow });

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
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') app.quit();
});
