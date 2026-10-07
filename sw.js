// PPI 상승률 계산기 - 오프라인 지원용 서비스 워커
// 화면 파일을 바꾸면 VERSION 숫자를 올려야 휴대폰에 새 버전이 확실히 반영돼요.
const VERSION = 'ppi-shell-v2';
const FONT_CACHE = 'ppi-fonts-v1';
const SHELL = [
  './',
  './index.html',
  './manifest.webmanifest',
  './icons/icon-192.png',
  './icons/icon-512.png',
  './icons/icon-maskable-512.png',
  './icons/apple-touch-icon.png',
];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(VERSION).then((cache) => cache.addAll(SHELL)).then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(keys.filter((k) => k !== VERSION && k !== FONT_CACHE).map((k) => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

// 화면과 data.csv는 인터넷이 되면 항상 최신으로, 안 되면 저장해 둔 것으로
async function networkFirst(request) {
  const cache = await caches.open(VERSION);
  try {
    // navigate 요청은 옵션을 붙여 다시 만들 수 없어서 주소로 새로 요청해요
    const fresh = await fetch(request.url, { cache: 'no-cache', credentials: 'same-origin' });
    if (fresh.ok) cache.put(request, fresh.clone());
    return fresh;
  } catch (err) {
    const cached = await cache.match(request, { ignoreSearch: true });
    if (cached) return cached;
    if (request.mode === 'navigate') {
      const shell = await cache.match('./index.html');
      if (shell) return shell;
    }
    throw err;
  }
}

async function cacheFirst(request, cacheName) {
  const cache = await caches.open(cacheName);
  const cached = await cache.match(request);
  if (cached) return cached;
  const fresh = await fetch(request);
  if (fresh.ok || fresh.type === 'opaque') cache.put(request, fresh.clone());
  return fresh;
}

self.addEventListener('fetch', (event) => {
  const req = event.request;
  if (req.method !== 'GET') return;
  const url = new URL(req.url);

  if (url.origin === self.location.origin) {
    const path = url.pathname;
    if (req.mode === 'navigate' || path.endsWith('/data.csv') || path.endsWith('/index.html') || path.endsWith('/')) {
      event.respondWith(networkFirst(req));
    } else {
      event.respondWith(cacheFirst(req, VERSION));
    }
    return;
  }

  if (url.hostname === 'fonts.googleapis.com' || url.hostname === 'fonts.gstatic.com') {
    event.respondWith(cacheFirst(req, FONT_CACHE));
  }
});
