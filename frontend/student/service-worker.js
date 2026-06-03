// BUSTAGO Service Worker
// 오프라인 캐시 + 설치형 PWA 동작에 사용됨
// 정적 자산은 cache-first, 외부 폰트는 network-first 전략으로 처리됨
// 캐시 갱신 시 CACHE 버전을 올리면 자동으로 이전 캐시가 폐기됨

const CACHE = 'bustago-v3';

// 오프라인에서도 동작해야 하는 핵심 자산 목록 — install 시 사전 캐시됨
const ASSETS = [
  'index.html',
  'style.css',
  'app.js',
  'data.js',
  '../shared/api.js',
  'manifest.json',
];

// install — 핵심 자산을 미리 캐시하는 데 사용됨
self.addEventListener('install', (e) => {
  e.waitUntil(caches.open(CACHE).then((c) => c.addAll(ASSETS)));
  self.skipWaiting();
});

// activate — 이전 버전 캐시를 정리하는 데 사용됨
self.addEventListener('activate', (e) => {
  e.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k)))
    )
  );
  self.clients.claim();
});

// fetch — 모든 GET 요청을 가로채 캐시/네트워크 전략을 선택하는 데 사용됨
self.addEventListener('fetch', (e) => {
  const req = e.request;
  if (req.method !== 'GET') return;

  // 폰트/외부 리소스: network-first
  if (req.url.startsWith('https://fonts.')) {
    e.respondWith(
      fetch(req).then((res) => {
        const copy = res.clone();
        caches.open(CACHE).then((c) => c.put(req, copy));
        return res;
      }).catch(() => caches.match(req))
    );
    return;
  }

  // 정적 자산: cache-first
  e.respondWith(
    caches.match(req).then((cached) =>
      cached ||
      fetch(req).then((res) => {
        if (res.ok && new URL(req.url).origin === location.origin) {
          const copy = res.clone();
          caches.open(CACHE).then((c) => c.put(req, copy));
        }
        return res;
      }).catch(() => cached)
    )
  );
});
