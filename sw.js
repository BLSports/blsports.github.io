// Service Worker der Sport-Radar-App (iPhone-Homescreen / PWA).
// - Seite: zuerst Netz (immer aktuelle Analysen), offline die zuletzt geladene Version.
// - Schriften, Icons, Wappen: aus dem Cache (ändern sich praktisch nie).
// - Live-/Daten-Abrufe (raw.githubusercontent, ESPN): nie cachen.
const VERSION = 'sr-v1';
const SHELL = 'shell-' + VERSION;
const RUNTIME = 'runtime-' + VERSION;
const SHELL_FILES = ['./', 'manifest.webmanifest', 'icons/apple-touch-icon.png', 'icons/icon-192.png'];
const MAX_RUNTIME = 300;

self.addEventListener('install', e => {
  e.waitUntil(caches.open(SHELL).then(c => c.addAll(SHELL_FILES)).then(() => self.skipWaiting()));
});

self.addEventListener('activate', e => {
  e.waitUntil(caches.keys()
    .then(keys => Promise.all(keys.filter(k => k !== SHELL && k !== RUNTIME).map(k => caches.delete(k))))
    .then(() => self.clients.claim()));
});

async function trim(cache) {
  const keys = await cache.keys();
  for (let i = 0; i < keys.length - MAX_RUNTIME; i++) await cache.delete(keys[i]);
}

async function seite(req) {
  const cache = await caches.open(SHELL);
  const u = new URL(req.url);
  const key = u.origin + u.pathname;  // ohne ?v=… / ?source=app
  try {
    const ctl = new AbortController();
    const t = setTimeout(() => ctl.abort(), 8000);
    const res = await fetch(req, { cache: 'no-store', signal: ctl.signal });
    clearTimeout(t);
    if (res.ok) await cache.put(key, res.clone());
    return res;
  } catch (err) {
    const hit = (await cache.match(key)) || (await cache.match('./'));
    if (hit) return hit;
    throw err;
  }
}

async function ausCache(req) {
  const cache = await caches.open(RUNTIME);
  const hit = await cache.match(req);
  if (hit) return hit;
  const res = await fetch(req);
  if (res.ok || res.type === 'opaque') { await cache.put(req, res.clone()); trim(cache); }
  return res;
}

self.addEventListener('fetch', e => {
  const req = e.request;
  if (req.method !== 'GET') return;
  const url = new URL(req.url);
  if (req.mode === 'navigate' && url.origin === location.origin) { e.respondWith(seite(req)); return; }
  if (url.hostname === 'raw.githubusercontent.com' || url.hostname.endsWith('espn.com')) return;
  if (url.hostname.startsWith('fonts.g') || req.destination === 'image' ||
      (url.origin === location.origin && url.pathname.includes('/icons/'))) {
    e.respondWith(ausCache(req).catch(() => fetch(req)));
  }
});
