'use strict';

const fs = require('fs');
const path = require('path');

/**
 * Tiny JSON file store living in Electron's userData directory.
 */
class Store {
  constructor(dir) {
    this.dir = dir;
    fs.mkdirSync(dir, { recursive: true });
    this.settingsFile = path.join(dir, 'lala-settings.json');
    this.commandsFile = path.join(dir, 'lala-commands.json');
    this.defaultsFile = path.join(__dirname, '..', 'src', 'commands-default.json');
  }

  _read(file, fallback) {
    try {
      return JSON.parse(fs.readFileSync(file, 'utf8'));
    } catch {
      return fallback;
    }
  }

  _write(file, value) {
    fs.writeFileSync(file, JSON.stringify(value, null, 2), 'utf8');
  }

  getSettings() {
    return this._read(this.settingsFile, {});
  }

  saveSettings(patch) {
    const next = { ...this.getSettings(), ...patch };
    this._write(this.settingsFile, next);
    return next;
  }

  getCustomCommands() {
    return this._read(this.commandsFile, []);
  }

  saveCustomCommands(custom) {
    const arr = Array.isArray(custom) ? custom : [];
    this._write(this.commandsFile, arr);
    return arr;
  }

  getDefaultCommands() {
    return this._read(this.defaultsFile, []);
  }
}

module.exports = Store;
