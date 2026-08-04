#!/usr/bin/env node
/**
 * Zero-dependency static server for LALA's web mode.
 * Serves the `src/` folder so you can try LALA in a browser
 * (Web Speech API) without installing Electron.
 */

import { createServer } from 'node:http';
import { readFile } from 'node:fs/promises';
import { extname, join, normalize } from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = join(fileURLToPath(new URL('..', import.meta.url)), 'src');
const PORT = Number(process.env.PORT || 4173);
const HOST = process.env.HOST || '0.0.0.0';

const MIME = {
  '.html': 'text/html; charset=utf-8',
  '.js': 'text/javascript; charset=utf-8',
  '.mjs': 'text/javascript; charset=utf-8',
  '.css': 'text/css; charset=utf-8',
  '.json': 'application/json; charset=utf-8',
  '.svg': 'image/svg+xml',
  '.png': 'image/png',
  '.jpg': 'image/jpeg',
  '.ico': 'image/x-icon',
  '.woff2': 'font/woff2'
};

const server = createServer(async (req, res) => {
  try {
    const urlPath = decodeURIComponent(new URL(req.url, 'http://localhost').pathname);
    if (urlPath === '/healthz') {
      res.writeHead(200, { 'content-type': 'text/plain' });
      res.end('ok');
      return;
    }

    const rel = urlPath === '/' ? 'index.html' : urlPath.replace(/^\/+/, '');
    const file = normalize(join(ROOT, rel));
    if (!file.startsWith(ROOT)) {
      res.writeHead(403);
      res.end('Forbidden');
      return;
    }

    const data = await readFile(file);
    res.writeHead(200, {
      'content-type': MIME[extname(file).toLowerCase()] || 'application/octet-stream',
      'cache-control': 'no-store'
    });
    res.end(data);
  } catch {
    res.writeHead(404, { 'content-type': 'text/plain' });
    res.end('Not found');
  }
});

server.listen(PORT, HOST, () => {
  console.log(`LALA web preview running at http://${HOST}:${PORT}`);
});
