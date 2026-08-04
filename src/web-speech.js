/**
 * Web Speech API adapter — used in browser mode (and the live web preview).
 * Gives continuous listening with interim results, free of charge,
 * but requires a Chromium browser and an internet connection.
 */

export function createWebSpeech(handlers) {
  const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SR) return null;

  const rec = new SR();
  rec.continuous = true;
  rec.interimResults = true;
  rec.maxAlternatives = 1;

  let wantOn = false;

  rec.onresult = (event) => {
    let interim = '';
    for (let i = event.resultIndex; i < event.results.length; i++) {
      const result = event.results[i];
      if (result.isFinal) {
        handlers.final(result[0].transcript);
      } else {
        interim += result[0].transcript;
      }
    }
    if (interim) handlers.interim(interim);
  };

  rec.onend = () => {
    if (wantOn) {
      // Auto-restart to keep listening.
      try { rec.start(); } catch { /* already started */ }
    } else {
      handlers.status('idle');
    }
  };

  rec.onerror = (event) => {
    if (event.error === 'not-allowed' || event.error === 'service-not-allowed') {
      wantOn = false;
      handlers.error('Microphone permission was denied. Allow mic access and try again.');
    } else if (event.error === 'network') {
      handlers.error('Speech service network error — Web Speech needs internet. Switch to the offline engine in the desktop app.');
    } else if (event.error !== 'no-speech' && event.error !== 'aborted') {
      handlers.error(`Speech error: ${event.error}`);
    }
  };

  return {
    start(lang) {
      rec.lang = lang || 'en-US';
      wantOn = true;
      try { rec.start(); } catch { /* already started */ }
      handlers.status('listening');
    },
    stop() {
      wantOn = false;
      try { rec.stop(); } catch { /* not started */ }
      handlers.status('idle');
    },
    get active() {
      return wantOn;
    }
  };
}
