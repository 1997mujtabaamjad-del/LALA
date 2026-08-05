# LALA — Security model & audit results

## Audited ✅ (2026-08-05)

| Check | Result |
|---|---|
| Secrets in repo (HEAD + full history) | ✅ clean — no API keys/tokens/passwords ever committed (incl. the key once pasted in chat; it was used only as an env var and never written) |
| `npm audit` | ✅ **0 vulnerabilities** |
| Electron `contextIsolation` | ✅ on |
| Electron `nodeIntegration` | ✅ off |
| Electron renderer sandbox | ✅ **on** (hardened this audit) |
| `webSecurity` (same-origin/CSP enforcement) | ✅ on |
| Renderer CSP | ✅ `default-src 'self'` + explicit `connect-src` allow-list (only the APIs the app uses) |
| Preload surface | ✅ minimal `contextBridge` API only; no raw Node exposure |
| Session permissions | ✅ allow-list (mic + clipboard only) |
| Brain server bind | ✅ `127.0.0.1:8420` — localhost only, never LAN/WAN |
| PowerShell volume control | ✅ integer-sanitized (`parseInt`) — no string interpolation of user text |
| App launching | ✅ `spawn` without a shell (no shell-injection surface) |
| ICS / transcript parsing | ✅ data-only parsers, no code execution |
| Dependency supply chain | ✅ lockfile committed; optional heavy deps (vosk, torch) are opt-in |

## By design (accepted risks, user-controlled)

- **Custom "run shell command" actions** execute arbitrary commands — this is the
  product's purpose on the user's own machine, gated behind explicitly creating
  such a command in Settings. Treated like a personal automation tool (cf. Alfred
  with terminal access).
- **Shutdown/restart/lock** voice commands require spoken/typed confirmation.
- **Recordings** (`save_recordings`, default on) store `.wav` + transcript locally
  in the user's own profile directory; disable in Settings for zero retention.
- **Wake-word audio** is processed locally (Vosk/Silero); cloud STT (Deepgram/OpenAI)
  sends audio to the provider only when explicitly configured.

## Dev-only surfaces (not shipped)

- `npm run preview` binds `0.0.0.0` for the Arena live-preview workflow; it is a
  static file server with `no-store` and no write surface. The shipped desktop app
  does not include it.

## Reporting

Found an issue? Open an issue titled `security: …` or contact the maintainer.
Rotate any key you suspect was exposed; keys live only in `assistant/.env`
(gitignored) or the OS profile settings store.
