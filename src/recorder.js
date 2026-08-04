/**
 * Microphone capture for push-to-talk (Electron mode).
 *
 * Produces two representations of the recording:
 *  - blob: the original MediaRecorder output (e.g. audio/webm) for the cloud engine
 *  - pcm:  raw 16-bit mono PCM @ 16 kHz for the offline Vosk engine
 */

let capture = null;

export async function startCapture() {
  if (capture) return capture;

  const stream = await navigator.mediaDevices.getUserMedia({
    audio: { echoCancellation: true, noiseSuppression: true, autoGainControl: true }
  });

  const recorder = new MediaRecorder(stream);
  const chunks = [];
  recorder.ondataavailable = (e) => {
    if (e.data && e.data.size) chunks.push(e.data);
  };

  const stopped = new Promise((resolve) => {
    recorder.onstop = () => resolve();
  });

  recorder.start();
  capture = { stream, recorder, chunks, stopped };
  return capture;
}

export async function stopCapture() {
  const c = capture;
  if (!c) return null;
  capture = null;

  c.recorder.stop();
  await c.stopped;
  c.stream.getTracks().forEach((t) => t.stop());

  const blob = new Blob(c.chunks, { type: c.recorder.mimeType || 'audio/webm' });
  const pcm = await blobToPcm16k(blob).catch(() => null);
  return { blob, pcm, mime: blob.type };
}

export function isCapturing() {
  return !!capture;
}

export function cancelCapture() {
  const c = capture;
  capture = null;
  if (!c) return;
  try { c.recorder.stop(); } catch { /* already stopped */ }
  c.stream.getTracks().forEach((t) => t.stop());
}

/** Decode any browser audio blob and downmix/downsample to 16 kHz mono Int16 PCM. */
async function blobToPcm16k(blob) {
  const arrayBuffer = await blob.arrayBuffer();
  const Ctx = window.AudioContext || window.webkitAudioContext;
  const ctx = new Ctx({ sampleRate: 16000 });
  try {
    const audio = await ctx.decodeAudioData(arrayBuffer);
    const ch0 = audio.getChannelData(0);
    const ch1 = audio.numberOfChannels > 1 ? audio.getChannelData(1) : null;
    const out = new Int16Array(ch0.length);
    for (let i = 0; i < ch0.length; i++) {
      let s = ch0[i];
      if (ch1) s = (s + ch1[i]) / 2;
      out[i] = Math.max(-32768, Math.min(32767, Math.round(s * 32767)));
    }
    return out.buffer;
  } finally {
    ctx.close();
  }
}
