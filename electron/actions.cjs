'use strict';

/**
 * Desktop action executor. Runs in the Electron main process.
 * Every handler returns { ok, message, ... } which the renderer can
 * display and/or speak.
 */

const { shell, clipboard, desktopCapturer, screen, app, BrowserWindow } = require('electron');
const { spawn, execFile } = require('child_process');
const fs = require('fs');
const os = require('os');
const path = require('path');

const PLATFORM = process.platform; // 'win32' | 'darwin' | 'linux'

function ok(message, extra = {}) {
  return { ok: true, message, ...extra };
}

function fail(message) {
  return { ok: false, message };
}

function run(cmd, args, opts = {}) {
  return new Promise((resolve) => {
    try {
      execFile(cmd, args, { timeout: 10000, windowsHide: true, ...opts }, (err, stdout, stderr) => {
        resolve({ err, stdout: String(stdout || ''), stderr: String(stderr || '') });
      });
    } catch (err) {
      resolve({ err, stdout: '', stderr: '' });
    }
  });
}

function spawnTry(cmd, args) {
  return new Promise((resolve) => {
    try {
      const child = spawn(cmd, args, { detached: true, stdio: 'ignore', windowsHide: true });
      child.on('spawn', () => {
        child.unref();
        resolve(true);
      });
      child.on('error', () => resolve(false));
    } catch {
      resolve(false);
    }
  });
}

function normalizeCandidates(value) {
  let cands = value;
  if (typeof value === 'string') cands = [value];
  else if (!Array.isArray(value)) cands = value[PLATFORM] || value.all || [];
  if (typeof cands === 'string') cands = [cands];
  return cands;
}

// ---------------------------------------------------------------------------
// Apps / URLs / shell
// ---------------------------------------------------------------------------

async function launchApp(value) {
  const candidates = normalizeCandidates(value);
  for (const cand of candidates) {
    if (/^[a-z][a-z0-9+.-]*:/i.test(cand)) {
      // URI like https://... or ms-settings: — hand to the OS.
      await shell.openExternal(cand);
      return ok(`Opened ${cand}.`);
    }
    let launched = false;
    if (PLATFORM === 'darwin') launched = await spawnTry('open', ['-a', cand]);
    else launched = await spawnTry(cand, []);
    if (launched) return ok(`Launched ${cand}.`);
  }
  return fail(`Couldn't launch "${candidates.join(' / ')}" on ${PLATFORM}.`);
}

async function runShell(value) {
  const { err } = await run(PLATFORM === 'win32' ? 'cmd.exe' : '/bin/sh',
    PLATFORM === 'win32' ? ['/d', '/s', '/c', value] : ['-c', value]);
  if (err) return fail(`Command failed: ${err.message}`);
  return ok('Command finished.');
}

// ---------------------------------------------------------------------------
// Volume (cross platform)
// ---------------------------------------------------------------------------

const WIN_INPUT_CS = `
using System;
using System.Runtime.InteropServices;
public class LalInput {
  [StructLayout(LayoutKind.Sequential)] struct MOUSEINPUT { public int dx; public int dy; public uint mouseData; public uint dwFlags; public uint time; public IntPtr dwExtraInfo; }
  [StructLayout(LayoutKind.Sequential)] struct KEYBDINPUT { public ushort wVk; public ushort wScan; public uint dwFlags; public uint time; public IntPtr dwExtraInfo; }
  [StructLayout(LayoutKind.Sequential)] struct HARDWAREINPUT { public uint uMsg; public ushort wParamL; public ushort wParamH; }
  [StructLayout(LayoutKind.Explicit)] struct InputUnion { [FieldOffset(0)] public MOUSEINPUT mi; [FieldOffset(0)] public KEYBDINPUT ki; [FieldOffset(0)] public HARDWAREINPUT hi; }
  [StructLayout(LayoutKind.Sequential)] struct INPUT { public uint type; public InputUnion U; }
  [DllImport("user32.dll", SetLastError = true)] static extern uint SendInput(uint nInputs, INPUT[] pInputs, int cbSize);
  public static void Key(ushort vk) {
    INPUT[] ins = new INPUT[2];
    ins[0].type = 1; ins[0].U.ki.wVk = vk;
    ins[1].type = 1; ins[1].U.ki.wVk = vk; ins[1].U.ki.dwFlags = 2;
    SendInput(2, ins, Marshal.SizeOf(typeof(INPUT)));
  }
}`;

function psScript(body) {
  return `Add-Type -TypeDefinition '${WIN_INPUT_CS}'; ${body}`;
}

async function winVolume(op, pct) {
  const VK_UP = '0xAF';
  const VK_DOWN = '0xAE';
  const VK_MUTE = '0xAD';
  let body;
  if (op === 'up') body = `[LalInput]::Key(${VK_UP})`;
  else if (op === 'down') body = `[LalInput]::Key(${VK_DOWN})`;
  else if (op === 'toggle-mute') body = `[LalInput]::Key(${VK_MUTE})`;
  else if (op === 'set') {
    const ups = Math.max(0, Math.min(50, Math.round(pct / 2)));
    body = `1..50 | ForEach-Object { [LalInput]::Key(${VK_DOWN}) }; 1..${ups} | ForEach-Object { [LalInput]::Key(${VK_UP}) }`;
  } else return fail(`Unknown volume op: ${op}`);

  const { err } = await run('powershell.exe', ['-NoProfile', '-ExecutionPolicy', 'Bypass', '-Command', psScript(body)]);
  if (err) return fail(`Volume control failed: ${err.message}`);
  return ok(op === 'set' ? `Volume set to ${pct}%.` : `Volume ${op}.`);
}

async function linuxVolume(op, pct) {
  const pactlMap = {
    up: ['set-sink-volume', '@DEFAULT_SINK@', '+10%'],
    down: ['set-sink-volume', '@DEFAULT_SINK@', '-10%'],
    'toggle-mute': ['set-sink-mute', '@DEFAULT_SINK@', 'toggle'],
    set: ['set-sink-volume', '@DEFAULT_SINK@', `${pct}%`]
  };
  let r = await run('pactl', pactlMap[op]);
  if (!r.err) return ok(op === 'set' ? `Volume set to ${pct}%.` : `Volume ${op}.`);

  const amixerMap = {
    up: ['sset', 'Master', '10%+'],
    down: ['sset', 'Master', '10%-'],
    'toggle-mute': ['sset', 'Master', 'toggle'],
    set: ['sset', 'Master', `${pct}%`]
  };
  r = await run('amixer', ['-q', ...amixerMap[op]]);
  if (!r.err) return ok(op === 'set' ? `Volume set to ${pct}%.` : `Volume ${op}.`);
  return fail('No volume tool found (need pactl or amixer).');
}

async function macVolume(op, pct) {
  let script;
  if (op === 'up') script = 'set volume output volume ((output volume of (get volume settings)) + 10)';
  else if (op === 'down') script = 'set volume output volume ((output volume of (get volume settings)) - 10)';
  else if (op === 'toggle-mute') script = 'set volume output muted (not (output muted of (get volume settings)))';
  else if (op === 'set') script = `set volume output volume ${pct}`;
  else return fail(`Unknown volume op: ${op}`);
  const { err } = await run('osascript', ['-e', script]);
  if (err) return fail(`Volume control failed: ${err.message}`);
  return ok(op === 'set' ? `Volume set to ${pct}%.` : `Volume ${op}.`);
}

function volume(action) {
  const pct = Math.max(0, Math.min(100, parseInt(action.value, 10) || 0));
  if (PLATFORM === 'win32') return winVolume(action.op, pct);
  if (PLATFORM === 'darwin') return macVolume(action.op, pct);
  return linuxVolume(action.op, pct);
}

// ---------------------------------------------------------------------------
// Brightness (best effort)
// ---------------------------------------------------------------------------

async function brightness(action) {
  const delta = action.op === 'up' ? 10 : -10;
  if (PLATFORM === 'win32') {
    const script = `
$b = (Get-CimInstance -Namespace root/wmi -ClassName WmiMonitorBrightness -ErrorAction Stop).CurrentBrightness
$t = [Math]::Max(0, [Math]::Min(100, $b + ${delta}))
Get-CimInstance -Namespace root/wmi -ClassName WmiMonitorBrightnessMethods | Invoke-CimMethod -MethodName WmiSetBrightness -Arguments @{Timeout = 1; Brightness = $t}
Write-Output "brightness $t"`;
    const { err, stdout } = await run('powershell.exe', ['-NoProfile', '-Command', script]);
    if (err) return fail('Brightness control not available on this display.');
    return ok(`Brightness ${stdout.trim() || 'adjusted'}.`);
  }
  if (PLATFORM === 'darwin') {
    const r = await run('brightness', [action.op === 'up' ? '+0.1' : '-0.1']);
    if (r.err) return fail('Install the "brightness" CLI (brew install brightness) to control brightness on macOS.');
    return ok(`Brightness ${action.op}.`);
  }
  let r = await run('brightnessctl', ['set', `${delta > 0 ? '+' : ''}${delta}%`]);
  if (!r.err) return ok(`Brightness ${action.op}.`);
  r = await run('xbacklight', [delta > 0 ? '-inc' : '-dec', '10']);
  if (!r.err) return ok(`Brightness ${action.op}.`);
  return fail('No brightness tool found (need brightnessctl or xbacklight).');
}

// ---------------------------------------------------------------------------
// Screenshot / window / power
// ---------------------------------------------------------------------------

async function screenshot() {
  try {
    const display = screen.getPrimaryDisplay();
    const scaleFactor = display.scaleFactor || 1;
    const width = Math.round(display.size.width * scaleFactor);
    const height = Math.round(display.size.height * scaleFactor);
    const sources = await desktopCapturer.getSources({
      types: ['screen'],
      thumbnailSize: { width, height }
    });
    if (!sources.length) return fail('No screen source available.');
    const source = sources.find((s) => String(s.display_id) === String(display.id)) || sources[0];

    const baseDir = fs.existsSync(path.join(os.homedir(), 'Pictures'))
      ? path.join(os.homedir(), 'Pictures')
      : os.homedir();
    const dir = path.join(baseDir, 'LALA Screenshots');
    fs.mkdirSync(dir, { recursive: true });

    const stamp = new Date().toISOString().replace(/[:.]/g, '-');
    const file = path.join(dir, `lala-screenshot-${stamp}.png`);
    fs.writeFileSync(file, source.thumbnail.toPNG());
    return ok(`Screenshot saved to ${file}.`, { payload: { type: 'screenshot', path: file } });
  } catch (err) {
    return fail(`Screenshot failed: ${err.message}`);
  }
}

function windowOp(op, win) {
  const target = win || BrowserWindow.getAllWindows()[0];
  if (!target) return fail('No LALA window found.');
  if (op === 'minimize') target.minimize();
  else if (op === 'maximize') target.isMaximized() ? target.unmaximize() : target.maximize();
  else if (op === 'restore') target.restore();
  else if (op === 'close') target.close();
  else return fail(`Unknown window op: ${op}`);
  return ok(`Window ${op === 'maximize' ? 'toggled' : op}.`);
}

async function lock() {
  if (PLATFORM === 'win32') {
    await run('rundll32.exe', ['user32.dll,LockWorkStation']);
    return ok('Locking the computer.');
  }
  if (PLATFORM === 'darwin') {
    await run('osascript', ['-e', 'tell application "System Events" to keystroke "q" using {command down, control down}']);
    return ok('Locking the computer.');
  }
  let r = await run('loginctl', ['lock-session']);
  if (r.err) r = await run('xdg-screensaver', ['lock']);
  if (r.err) return fail('Could not lock the session.');
  return ok('Locking the computer.');
}

async function sleep() {
  if (PLATFORM === 'win32') {
    await run('rundll32.exe', ['powrprof.dll,SetSuspendState', '0,1,0']);
    return ok('Going to sleep.');
  }
  if (PLATFORM === 'darwin') {
    await run('pmset', ['sleepnow']);
    return ok('Going to sleep.');
  }
  const r = await run('systemctl', ['suspend']);
  if (r.err) return fail('Could not suspend (systemctl unavailable).');
  return ok('Going to sleep.');
}

async function power(kind) {
  // Confirmation is enforced before we get here (ctx.confirmed).
  if (PLATFORM === 'win32') {
    const flag = kind === 'shutdown' ? '/s' : '/r';
    await run('shutdown.exe', [flag, '/t', '15', '/c', 'LALA is powering off — run "shutdown /a" to cancel.']);
    return ok(`${kind === 'shutdown' ? 'Shutting down' : 'Restarting'} in 15 seconds. Say nothing — you can cancel with "shutdown /a".`);
  }
  if (PLATFORM === 'darwin') {
    await run('osascript', ['-e', `tell application "System Events" to ${kind}`]);
    return ok(kind === 'shutdown' ? 'Shutting down.' : 'Restarting.');
  }
  let r = await run('shutdown', [kind === 'shutdown' ? '-h' : '-r', '+1', 'LALA is powering off — run "shutdown -c" to cancel.']);
  if (r.err) r = await run('systemctl', [kind === 'shutdown' ? 'poweroff' : 'reboot']);
  if (r.err) return fail('Could not start shutdown/restart.');
  return ok(kind === 'shutdown' ? 'Shutting down in 1 minute.' : 'Restarting in 1 minute.');
}

// ---------------------------------------------------------------------------
// Weather / web search / calendar / smart lights
// ---------------------------------------------------------------------------

const WMO = {
  0: 'clear skies', 1: 'mostly clear', 2: 'partly cloudy', 3: 'overcast',
  45: 'foggy', 48: 'foggy', 51: 'light drizzle', 53: 'drizzle', 55: 'heavy drizzle',
  61: 'light rain', 63: 'rain', 65: 'heavy rain', 71: 'light snow', 73: 'snow',
  75: 'heavy snow', 80: 'rain showers', 82: 'violent showers', 95: 'thunderstorms',
  96: 'thunderstorms with hail', 99: 'thunderstorms with hail'
};

async function weatherSummary(city) {
  try {
    if (city) {
      const g = await fetch(`https://geocoding-api.open-meteo.com/v1/search?name=${encodeURIComponent(city)}&count=1`);
      const gj = await g.json();
      const place = (gj.results || [])[0];
      if (!place) return null;
      const r = await fetch(`https://api.open-meteo.com/v1/forecast?latitude=${place.latitude}&longitude=${place.longitude}&current=temperature_2m,apparent_temperature,relative_humidity_2m,weather_code,wind_speed_10m`);
      const j = await r.json();
      const c = j.current;
      return `It's ${Math.round(c.temperature_2m)}°C in ${place.name}, ${WMO[c.weather_code] || 'cloudy'}, feels like ${Math.round(c.apparent_temperature)}°, wind ${Math.round(c.wind_speed_10m)} km/h, humidity ${c.relative_humidity_2m}%.`;
    }
    const r = await fetch('https://wttr.in/?format=j1');
    const j = await r.json();
    const cur = j.current_condition[0];
    const place = j.nearest_area[0].areaName[0].value;
    return `It's ${cur.temp_C}°C in ${place}, ${cur.weatherDesc[0].value.toLowerCase()}, humidity ${cur.humidity}%.`;
  } catch {
    return null;
  }
}

async function ddgAnswer(query) {
  try {
    const r = await fetch(`https://api.duckduckgo.com/?q=${encodeURIComponent(query)}&format=json&no_html=1&no_redirect=1`);
    const j = await r.json();
    let text = j.AbstractText || j.Answer || '';
    if (!text && (j.RelatedTopics || []).length) text = j.RelatedTopics[0].Text || '';
    text = String(text || '').trim();
    return text ? text.slice(0, 400) : null;
  } catch {
    return null;
  }
}

const CAL_DAYS = { sunday: 0, monday: 1, tuesday: 2, wednesday: 3, thursday: 4, friday: 5, saturday: 6 };

function parseCalendarWhen(text) {
  const t = String(text || '').toLowerCase();
  const m = t.match(/\bat\s+(\d{1,2})(?::(\d{2}))?\s*(am|pm)?\b/);
  if (!m) return null;
  let h = parseInt(m[1], 10);
  const min = parseInt(m[2] || '0', 10);
  if (m[3] === 'pm' && h < 12) h += 12;
  const now = new Date();
  let day = new Date(now);
  if (t.includes('tomorrow')) day.setDate(day.getDate() + 1);
  else {
    const wd = Object.keys(CAL_DAYS).find((d) => new RegExp(`\\b${d}\\b`).test(t));
    if (wd) {
      const delta = (CAL_DAYS[wd] - now.getDay() + 7) % 7 || 7;
      day.setDate(day.getDate() + delta);
    }
  }
  day.setHours(h, min, 0, 0);
  return day;
}

function calendar(action, store) {
  if (action.op === 'add') {
    const events = store.getCalendar();
    events.push({ id: `ev${events.length}${Date.now()}`, when: action.when, title: action.title });
    store.saveCalendar(events);
    return 'Saved to your calendar.';
  }
  const now = Date.now();
  const events = store.getCalendar()
    .map((e) => ({ ...e, ts: Date.parse(e.when) }))
    .filter((e) => !Number.isNaN(e.ts) && e.ts > now - 3600e3)
    .sort((a, b) => a.ts - b.ts)
    .slice(0, 5);
  if (!events.length) return 'Your calendar is clear — nothing scheduled.';
  const lines = events.map((e) => {
    const d = new Date(e.ts);
    return `${e.title} — ${d.toLocaleString([], { weekday: 'short', hour: '2-digit', minute: '2-digit' })}`;
  });
  return `Up next: ${lines.join('; ')}.`;
}

const LIGHT_HUE = { red: 0, orange: 7000, yellow: 12000, green: 25000, cyan: 32000, blue: 46000, purple: 50000, pink: 56000 };
const LIGHT_CT = { warm: 500, white: 370, cool: 200 };

function huePayload(action) {
  if (action.op === 'on') return { on: true };
  if (action.op === 'off') return { on: false };
  if (action.op === 'set') return { on: true, bri: Math.round(Math.max(1, Math.min(100, action.value)) * 254 / 100) };
  if (action.op === 'color') {
    if (LIGHT_CT[action.color]) return { on: true, ct: LIGHT_CT[action.color] };
    if (LIGHT_HUE[action.color]) return { on: true, hue: LIGHT_HUE[action.color], sat: 254 };
  }
  return { on: true };
}

async function controlLights(settings, action) {
  const payload = huePayload(action);
  const provider =
    settings.lightsProvider === 'hue' || (settings.lightsProvider !== 'homeassistant' && settings.hueIp && settings.hueKey)
      ? 'hue'
      : settings.haUrl && settings.haToken ? 'homeassistant' : null;
  try {
    if (provider === 'hue') {
      const r = await fetch(`http://${settings.hueIp}/api/${settings.hueKey}/groups/0/action`, {
        method: 'PUT',
        body: JSON.stringify(payload)
      });
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
    } else if (provider === 'homeassistant') {
      const on = payload.on !== false;
      const body = on ? (payload.bri ? { brightness: payload.bri } : {}) : {};
      const r = await fetch(`${settings.haUrl.replace(/\/+$/, '')}/api/services/light/${on ? 'turn_on' : 'turn_off'}`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${settings.haToken}`, 'Content-Type': 'application/json' },
        body: JSON.stringify(body)
      });
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
    } else {
      return 'No smart-light provider configured — add Hue or Home Assistant details in Settings.';
    }
  } catch (err) {
    return `Lights unreachable: ${err.message}`;
  }
  return { on: 'Lights on.', off: 'Lights off.', set: `Lights set to ${action.value}%.`, color: `Lights set to ${action.color}.` }[action.op] || 'Lights updated.';
}

// ---------------------------------------------------------------------------
// Misc
// ---------------------------------------------------------------------------

function info(kind) {
  const now = new Date();
  if (kind === 'time') {
    const t = now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    return ok(`It's ${t}.`);
  }
  if (kind === 'date') {
    const d = now.toLocaleDateString([], { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' });
    return ok(`Today is ${d}.`);
  }
  return fail(`Unknown info kind: ${kind}`);
}

// ---------------------------------------------------------------------------
// Dispatcher
// ---------------------------------------------------------------------------

async function execute(action, ctx, deps = {}) {
  if (!action || typeof action.type !== 'string') return fail('Malformed action.');

  switch (action.type) {
    case 'url':
      await shell.openExternal(action.value);
      return ok(action.response || `Opened ${action.value}.`);

    case 'app':
      return launchApp(action.value);

    case 'shell':
      return runShell(action.value);

    case 'volume':
      return volume(action);

    case 'brightness':
      return brightness(action);

    case 'screenshot':
      return screenshot();

    case 'window':
      return windowOp(action.op, deps.win);

    case 'quit':
      setTimeout(() => app.quit(), 400);
      return ok('Goodbye! Shutting down LALA.');

    case 'info':
      return info(action.kind);

    case 'speak':
      return ok(action.value || '');

    case 'quiet':
      return ok('Going quiet.');

    case 'clipboard': {
      const text = action.value === '$last' ? (ctx.lastText || '') : (action.value || '');
      if (!text) return fail('Nothing to copy yet.');
      clipboard.writeText(text);
      return ok('Copied to clipboard.');
    }

    case 'dictation':
      return ok(action.op === 'start' ? 'Dictation started — speak freely, then say "stop dictation".' : 'Dictation stopped.');

    case 'weather': {
      const text = await weatherSummary(action.city || '');
      return ok(text || "I couldn't reach a weather service right now.");
    }

    case 'websearch': {
      const q = action.query || action.value || '';
      const answer = await ddgAnswer(q);
      if (answer) return ok(answer);
      await shell.openExternal(`https://www.google.com/search?q=${encodeURIComponent(q)}`);
      return ok('No instant answer — I opened the search results.');
    }

    case 'calendar': {
      if (!deps.store) return fail('Calendar unavailable.');
      if (action.op === 'list') return ok(calendar(action, deps.store));
      const when = parseCalendarWhen(action.text || '');
      if (!when) {
        return ok('I need a time — try “add dentist appointment tomorrow at 3 pm”.');
      }
      const title = (action.text || '')
        .replace(/\b(?:to|on) my calendar\b/g, '')
        .split(/\b(?:today|tomorrow|tonight|monday|tuesday|wednesday|thursday|friday|saturday|sunday|at)\b/)[0]
        .trim() || 'event';
      return ok(calendar({ op: 'add', when: when.toISOString(), title }, deps.store));
    }

    case 'lights': {
      const settings = deps.store ? deps.store.getSettings() : {};
      return ok(await controlLights(settings, action));
    }

    case 'help':
      return ok('Here is everything I understand.', { payload: { type: 'help' } });

    case 'lock':
      return lock();

    case 'sleep':
      return sleep();

    case 'shutdown':
    case 'restart':
      if (!ctx.confirmed) {
        return {
          ok: true,
          needsConfirm: true,
          message: `${action.type === 'shutdown' ? 'Shut down' : 'Restart'} the computer? Say "confirm" to proceed or "cancel" to abort.`
        };
      }
      return power(action.type);

    default:
      return fail(`Unknown action type: ${action.type}`);
  }
}

module.exports = { execute };
