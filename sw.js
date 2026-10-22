// Jewolingo service worker — offline app shell.
// Bump CACHE_VERSION on every deploy so clients pick the new build up.
const CACHE_VERSION = 'jw-v58';
const SHELL = 'shell-' + CACHE_VERSION;
// Deliberately NOT versioned: fonts do not change between builds, and
// tying them to CACHE_VERSION would re-download ~550KB on every deploy.
// v2 = the self-hosted files in fonts/; activate drops v1 (Google Fonts).
const FONTS = 'jw-fonts-v2';

// The two entries a navigation is served from are REQUIRED: if either fails,
// install fails and the previous version — with its complete shell — stays in
// charge, rather than activating a shell with no page in it (a blank offline
// launch until the next deploy). They are fetched with a version query so a
// CDN edge still holding the old HTML cannot be stored as the new shell.
const REQUIRED = ['./', './index.html'];

const SHELL_FILES = [
  './',
  './index.html',
  './manifest.webmanifest',
  './data/annotations.json',
  './icons/icon-180.png',
  './icons/icon-192.png',
  './icons/icon-512.png',
  './icons/icon-512-maskable.png'
];

// Precached at install, so the very first offline launch has the real faces.
const FONT_FILES = [
  './fonts/frl-hebrew.woff2',
  './fonts/frl-latin.woff2',
  './fonts/ss4-latin.woff2',
  './fonts/ss4-latin-ext.woff2',
  './fonts/ss4-italic-latin.woff2',
  './fonts/ss4-italic-latin-ext.woff2',
  './fonts/gveret-hebrew.woff2',
  './fonts/gveret-latin.woff2'
];

self.addEventListener('install', function (e) {
  e.waitUntil(Promise.all([
    caches.open(SHELL)
      .then(function (c) { return Promise.all(SHELL_FILES.map(function (u) {
        if (REQUIRED.indexOf(u) !== -1) {
          return fetch(new Request(u + '?v=' + CACHE_VERSION, { cache: 'reload' }))
            .then(function (res) {
              if (!res.ok) throw new Error('shell ' + u + ' ' + res.status);
              return c.put(u, res);
            });
        }
        // Everything else is optional: one 404 must not fail the install.
        return c.add(new Request(u, { cache: 'reload' })).catch(function () {});
      })); }),
    // Fonts: only fetch what the unversioned cache does not already hold.
    caches.open(FONTS)
      .then(function (c) { return Promise.all(FONT_FILES.map(function (u) {
        return c.match(u).then(function (hit) {
          return hit || c.add(new Request(u, { cache: 'reload' })).catch(function () {});
        });
      })); })
  ]).then(function () { return self.skipWaiting(); }));
});

self.addEventListener('activate', function (e) {
  e.waitUntil(
    caches.keys()
      .then(function (keys) {
        return Promise.all(keys
          .filter(function (k) { return k !== SHELL && k !== FONTS; })
          .map(function (k) { return caches.delete(k); }));
      })
      .then(function () { return self.clients.claim(); })
  );
});

self.addEventListener('message', function (e) {
  if (e.data === 'skipWaiting') self.skipWaiting();
});

self.addEventListener('fetch', function (e) {
  const req = e.request;
  if (req.method !== 'GET') return;
  const url = new URL(req.url);

  // Never cache the Anthropic API (Sicha): always live, never stored.
  if (url.hostname === 'api.anthropic.com') return;

  // Navigations: serve the cached shell so the app opens with no network.
  if (req.mode === 'navigate') {
    e.respondWith(
      caches.match('./index.html').then(function (hit) {
        return hit || fetch(req).then(function (res) {
          // Heal a shell that lost its page: store the app page when the
          // network serves it, so the next offline launch works again.
          if (res && res.ok && !res.redirected && /\/(index\.html)?$/.test(url.pathname)) {
            const copy = res.clone();
            caches.open(SHELL).then(function (c) { c.put('./index.html', copy); });
          }
          return res;
        }).catch(function () { return caches.match('./'); });
      })
    );
    return;
  }

  // Same-origin assets (fonts included): cache-first, fall back to network.
  if (url.origin === self.location.origin) {
    const store = url.pathname.indexOf('/fonts/') !== -1 ? FONTS : SHELL;
    e.respondWith(
      caches.match(req).then(function (hit) {
        return hit || fetch(req).then(function (res) {
          if (res && res.status === 200) {
            const copy = res.clone();
            caches.open(store).then(function (c) { c.put(req, copy); });
          }
          return res;
        });
      })
    );
  }
});
