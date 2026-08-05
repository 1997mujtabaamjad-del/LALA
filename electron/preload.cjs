'use strict';

const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('lala', {
  platform: process.platform,

  // Commands & settings
  getCommands: () => ipcRenderer.invoke('commands:get'),
  saveCustomCommands: (custom) => ipcRenderer.invoke('commands:saveCustom', custom),
  getSettings: () => ipcRenderer.invoke('settings:get'),
  saveSettings: (patch) => ipcRenderer.invoke('settings:save', patch),

  // Actions
  executeAction: (action, ctx) => ipcRenderer.invoke('actions:execute', action, ctx),

  // Speech recognition
  asrStatus: () => ipcRenderer.invoke('asr:status'),
  transcribe: (payload) => ipcRenderer.invoke('asr:transcribe', payload),
  downloadModel: () => ipcRenderer.invoke('asr:downloadModel'),
  onAsrProgress: (cb) => {
    ipcRenderer.on('asr:progress', (_e, data) => cb(data));
  },

  // Wake word stream
  wakeStart: () => ipcRenderer.invoke('wake:start'),
  wakeFeed: (pcm) => ipcRenderer.invoke('wake:feed', pcm),
  wakeFinish: () => ipcRenderer.invoke('wake:finish'),
  wakeBarge: () => ipcRenderer.invoke('wake:barge'),
  wakeStop: () => ipcRenderer.invoke('wake:stop'),
  onWakeSettingChanged: (cb) => {
    ipcRenderer.on('settings:wake-changed', (_e, value) => cb(value));
  }
});
