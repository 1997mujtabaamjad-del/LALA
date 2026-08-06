'use strict';
/**
 * Optional neural VAD inside the desktop app.
 * Enable with:  npm i onnxruntime-node
 * and a model at <userData>/models/silero_vad.onnx
 * (copy it from a Python install: .venv/.../silero_vad/data/silero_vad.onnx)
 * Falls back to the renderer's energy VAD when unavailable.
 */

const fs = require('fs');
const path = require('path');

let ort = null;
let session = null;
let stateBuf = null;
let pending = [];
let ready = false;

async function init(userData) {
  try {
    ort = require('onnxruntime-node');
  } catch {
    return false;
  }
  const model = path.join(userData, 'models', 'silero_vad.onnx');
  if (!fs.existsSync(model)) return false;
  try {
    session = await ort.InferenceSession.create(model, { executionProviders: ['cpu'] });
    stateBuf = new Float32Array(2 * 128);
    ready = true;
  } catch {
    ready = false;
  }
  return ready;
}

function status() {
  return { ready, hasOrt: !!ort };
}

/** pcmInt16: Int16Array chunk @16k → max speech probability (or null). */
async function speech(pcmInt16) {
  if (!ready) return null;
  for (let i = 0; i < pcmInt16.length; i++) pending.push(pcmInt16[i] / 32768);
  let p = 0;
  while (pending.length >= 512) {
    const x = Float32Array.from(pending.slice(0, 512));
    pending = pending.slice(512);
    const feeds = {
      input: new ort.Tensor('float32', x, [1, 512]),
      state: new ort.Tensor('float32', stateBuf, [2, 1, 128]),
      sr: new ort.Tensor('int64', BigInt64Array.from([16000n]), [])
    };
    const out = await session.run(feeds);
    stateBuf = out.stateN.data;
    p = Math.max(p, out.output.data[0]);
  }
  return p;
}

module.exports = { init, status, speech };
