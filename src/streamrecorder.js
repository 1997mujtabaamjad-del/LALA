/**
 * Live 16 kHz capture for push-to-talk AND barge-in cycles.
 *
 * - streams downsampled Int16 chunks out as they arrive (streaming STT)
 * - returns the complete utterance PCM on stop()
 * - `autoStop` mode: energy endpointing (speech → 1 s silence) stops by
 *   itself and hands the PCM to `onAutoStop` — used for barge-in cycles
 *
 * Also exports `startBargeMonitor`: keeps the mic open during TTS and fires
 * `onSpeech` the instant the user starts talking (sustained 250 ms).
 */

const TARGET_RATE = 16000;
const SPEECH_RMS = 0.012;
const BARGE_RMS = 0.05; // louder than speaker bleed

async function openMic() {
  return navigator.mediaDevices.getUserMedia({
    audio: { echoCancellation: true, noiseSuppression: true, autoGainControl: true }
  });
}

function downsample(input, sampleRate) {
  const ratio = sampleRate / TARGET_RATE;
  const outLen = Math.floor(input.length / ratio);
  const out = new Int16Array(outLen);
  for (let i = 0; i < outLen; i++) {
    let sum = 0;
    const from = Math.floor(i * ratio);
    const to = Math.max(from + 1, Math.floor((i + 1) * ratio));
    for (let j = from; j < to; j++) sum += input[j];
    out[i] = Math.max(-32768, Math.min(32767, Math.round((sum / (to - from)) * 32767)));
  }
  return out;
}

export async function startStreamCapture({ onChunk, autoStop = false, onAutoStop } = {}) {
  const stream = await openMic();
  const Ctx = window.AudioContext || window.webkitAudioContext;
  const ctx = new Ctx();
  const source = ctx.createMediaStreamSource(stream);
  const processor = ctx.createScriptProcessor(2048, 1, 1);
  const mute = ctx.createGain();
  mute.gain.value = 0; // keep the graph alive without speaker feedback
  source.connect(processor);
  processor.connect(mute);
  mute.connect(ctx.destination);

  const total = [];
  let pending = [];
  let speechMs = 0;
  let silenceMs = 0;
  let ended = false;

  function cleanup() {
    processor.onaudioprocess = null;
    processor.disconnect();
    mute.disconnect();
    source.disconnect();
    stream.getTracks().forEach((t) => t.stop());
    ctx.close().catch(() => {});
  }

  processor.onaudioprocess = (event) => {
    if (ended) return;
    const input = event.inputBuffer.getChannelData(0);
    const chunk = downsample(input, ctx.sampleRate);
    for (let i = 0; i < chunk.length; i++) {
      pending.push(chunk[i]);
      total.push(chunk[i]);
    }
    if (pending.length >= 3200 && onChunk) { // ~0.2 s
      const buf = Int16Array.from(pending).buffer;
      pending = [];
      onChunk(buf);
    }

    if (autoStop) {
      let sum = 0;
      for (let i = 0; i < input.length; i++) sum += input[i] * input[i];
      const rms = Math.sqrt(sum / input.length);
      const cbMs = (input.length / ctx.sampleRate) * 1000;
      if (rms > SPEECH_RMS) {
        speechMs += cbMs;
        silenceMs = 0;
      } else {
        silenceMs += cbMs;
      }
      if (speechMs >= 250 && silenceMs >= 1000) {
        ended = true;
        cleanup();
        if (pending.length && onChunk) onChunk(Int16Array.from(pending).buffer);
        onAutoStop && onAutoStop(Int16Array.from(total).buffer);
      }
    }
  };

  return {
    async stop() {
      if (!ended) {
        ended = true;
        cleanup();
        if (pending.length && onChunk) onChunk(Int16Array.from(pending).buffer);
      }
      return { pcm: Int16Array.from(total).buffer };
    }
  };
}

/** Mic stays open during TTS; fires once when the user starts speaking. */
export async function startBargeMonitor({ onSpeech }) {
  const stream = await openMic();
  const Ctx = window.AudioContext || window.webkitAudioContext;
  const ctx = new Ctx();
  const source = ctx.createMediaStreamSource(stream);
  const processor = ctx.createScriptProcessor(2048, 1, 1);
  const mute = ctx.createGain();
  mute.gain.value = 0;
  source.connect(processor);
  processor.connect(mute);
  mute.connect(ctx.destination);

  let sustained = 0;
  let fired = false;

  processor.onaudioprocess = (event) => {
    if (fired) return;
    const input = event.inputBuffer.getChannelData(0);
    let sum = 0;
    for (let i = 0; i < input.length; i++) sum += input[i] * input[i];
    const rms = Math.sqrt(sum / input.length);
    const cbMs = (input.length / ctx.sampleRate) * 1000;
    if (rms > BARGE_RMS) {
      sustained += cbMs;
      if (sustained >= 250) {
        fired = true;
        stop();
        onSpeech && onSpeech();
      }
    } else {
      sustained = 0;
    }
  };

  function stop() {
    processor.onaudioprocess = null;
    processor.disconnect();
    mute.disconnect();
    source.disconnect();
    stream.getTracks().forEach((t) => t.stop());
    ctx.close().catch(() => {});
  }

  return { stop: () => { if (!fired) stop(); }, get fired() { return fired; } };
}
