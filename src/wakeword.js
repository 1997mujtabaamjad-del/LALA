/**
 * Renderer-side continuous mic capture for the wake word ("Hey Laala").
 *
 * Uses a ScriptProcessor to pull mono audio, downsamples it to 16 kHz
 * Int16 PCM and streams it into the Electron main process (Vosk).
 * After the wake word is heard, a simple energy VAD detects end-of-speech
 * and asks the main process for the finalized command text.
 */

const TARGET_RATE = 16000;
const SPEECH_RMS = 0.012;      // RMS above which a frame counts as speech
const MIN_SPEECH_MS = 250;     // speech needed before we may endpoint
const SILENCE_MS = 1000;       // silence after speech that ends the command
const MAX_COMMAND_MS = 10000;  // hard cap on command capture

export function createWakeListener({ onWake, onPartial, onCommand, onBarge, canBarge,
  continuous, onFollowEnd, followWindowMs = 8000 }) {
  let ctx = null;
  let source = null;
  let processor = null;
  let mute = null;
  let stream = null;

  let mode = 'idle'; // 'idle' | 'wake-wait' | 'command'
  let accum = [];
  let feeding = false;
  let speechMs = 0;
  let silenceMs = 0;
  let startedAt = 0;
  let bargeMs = 0;
  let followIdle = false; // in follow-up window, waiting for speech

  const BARGE_RMS = 0.05;   // louder than idle noise; must beat TTS bleed
  const BARGE_MS = 200;

  async function start(desktopBridge) {
    stream = await navigator.mediaDevices.getUserMedia({
      audio: { echoCancellation: true, noiseSuppression: true, autoGainControl: false }
    });
    const Ctx = window.AudioContext || window.webkitAudioContext;
    ctx = new Ctx();
    await desktopBridge.wakeStart();

    source = ctx.createMediaStreamSource(stream);
    processor = ctx.createScriptProcessor(2048, 1, 1);
    mute = ctx.createGain();
    mute.gain.value = 0; // keep the graph alive without speaker feedback
    source.connect(processor);
    processor.connect(mute);
    mute.connect(ctx.destination);

    mode = 'wake-wait';

    processor.onaudioprocess = (event) => {
      const input = event.inputBuffer.getChannelData(0);
      const cbMs = (input.length / ctx.sampleRate) * 1000;

      // Energy tracking (command capture phase)
      let sum = 0;
      for (let i = 0; i < input.length; i++) sum += input[i] * input[i];
      const rms = Math.sqrt(sum / input.length);

      // Downsample to 16k by averaging.
      const ratio = ctx.sampleRate / TARGET_RATE;
      const outLen = Math.floor(input.length / ratio);
      for (let i = 0; i < outLen; i++) {
        let s = 0;
        const from = Math.floor(i * ratio);
        const to = Math.max(from + 1, Math.floor((i + 1) * ratio));
        for (let j = from; j < to; j++) s += input[j];
        const avg = s / (to - from);
        accum.push(Math.max(-32768, Math.min(32767, Math.round(avg * 32767))));
      }

      maybeFeedAndEndpoint(rms, cbMs, desktopBridge);
    };
  }

  function maybeFeedAndEndpoint(rms, cbMs, bridge) {
    // Flush PCM in ~0.2 s chunks.
    if (accum.length >= 3200 && !feeding) {
      const chunk = accum;
      accum = [];
      const pcm = Int16Array.from(chunk).buffer;
      feeding = true;
      bridge
        .wakeFeed(pcm)
        .then((res) => {
          feeding = false;
          if (!res || !res.ok) return;
          if (res.wake) {
            mode = 'command';
            startedAt = performance.now();
            speechMs = 0;
            silenceMs = 0;
            onWake && onWake();
          } else if (mode === 'command' && res.partial) {
            onPartial && onPartial(res.partial);
          }
        })
        .catch(() => { feeding = false; });
    }

    // Barge-in: user talks over LALA's voice → stop TTS, capture the command.
    if (mode === 'wake-wait' && canBarge && canBarge()) {
      if (rms > BARGE_RMS) {
        bargeMs += cbMs;
      } else {
        bargeMs = 0;
      }
      if (bargeMs >= BARGE_MS) {
        bargeMs = 0;
        mode = 'command';
        startedAt = performance.now();
        speechMs = cbMs;
        silenceMs = 0;
        bridge.wakeBarge().catch(() => {});
        onBarge && onBarge();
      }
    } else if (mode !== 'command') {
      bargeMs = 0;
    }

    if (mode === 'command') {
      if (rms > SPEECH_RMS) {
        speechMs += cbMs;
        silenceMs = 0;
      } else {
        silenceMs += cbMs;
      }
      const elapsed = performance.now() - startedAt;

      // Continuous conversation: follow-up window with no speech → back to wake.
      if (followIdle && speechMs === 0 && elapsed > followWindowMs) {
        followIdle = false;
        mode = 'wake-wait';
        bridge.wakeReset().catch(() => {});
        onFollowEnd && onFollowEnd();
        return;
      }

      if ((speechMs >= MIN_SPEECH_MS && silenceMs >= SILENCE_MS) || elapsed > MAX_COMMAND_MS) {
        const wantFollow = !!(continuous && continuous());
        followIdle = wantFollow;
        mode = wantFollow ? 'command' : 'wake-wait';
        startedAt = performance.now();
        speechMs = 0;
        silenceMs = 0;
        bridge
          .wakeFinish()
          .then((res) => {
            if (res && res.ok && res.text) onCommand && onCommand(res.text);
          })
          .catch(() => {});
      }
    }
  }

  function stop(bridge) {
    mode = 'idle';
    accum = [];
    if (processor) {
      processor.onaudioprocess = null;
      processor.disconnect();
      processor = null;
    }
    if (mute) { mute.disconnect(); mute = null; }
    if (source) { source.disconnect(); source = null; }
    if (stream) {
      stream.getTracks().forEach((t) => t.stop());
      stream = null;
    }
    if (ctx) {
      ctx.close().catch(() => {});
      ctx = null;
    }
    bridge && bridge.wakeStop().catch(() => {});
  }

  function getMode() {
    return mode;
  }

  return { start, stop, getMode };
}
