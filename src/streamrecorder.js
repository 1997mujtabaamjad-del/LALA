/**
 * Live 16 kHz capture for push-to-talk: streams downsampled Int16 chunks out
 * as they arrive (for streaming STT partials) and returns the complete
 * utterance PCM on stop.
 */

const TARGET_RATE = 16000;

export async function startStreamCapture({ onChunk }) {
  const stream = await navigator.mediaDevices.getUserMedia({
    audio: { echoCancellation: true, noiseSuppression: true, autoGainControl: true }
  });
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

  processor.onaudioprocess = (event) => {
    const input = event.inputBuffer.getChannelData(0);
    const ratio = ctx.sampleRate / TARGET_RATE;
    const outLen = Math.floor(input.length / ratio);
    for (let i = 0; i < outLen; i++) {
      let sum = 0;
      const from = Math.floor(i * ratio);
      const to = Math.max(from + 1, Math.floor((i + 1) * ratio));
      for (let j = from; j < to; j++) sum += input[j];
      const avg = sum / (to - from);
      const v = Math.max(-32768, Math.min(32767, Math.round(avg * 32767)));
      pending.push(v);
      total.push(v);
    }
    if (pending.length >= 3200 && onChunk) { // ~0.2 s chunks
      const chunk = Int16Array.from(pending).buffer;
      pending = [];
      onChunk(chunk);
    }
  };

  return {
    async stop() {
      processor.onaudioprocess = null;
      processor.disconnect();
      mute.disconnect();
      source.disconnect();
      stream.getTracks().forEach((t) => t.stop());
      ctx.close().catch(() => {});
      if (pending.length && onChunk) onChunk(Int16Array.from(pending).buffer);
      return { pcm: Int16Array.from(total).buffer };
    }
  };
}
