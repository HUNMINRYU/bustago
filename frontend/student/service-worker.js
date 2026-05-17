// BUSTAGO Service Worker - Offline Cache
//
// CACHE_NAME 갱신 규칙 (2026-05-17 진단 CL-4):
//   정적 자산(index.html / style.css / app.js / shared/api.js / manifest.json) 변경 시 반드시 버전 증가.
//   activate 핸들러가 이전 캐시를 자동 삭제하므로 사용자 측에서는 자동 갱신됨.
//   versions: v1 (초기), v2-demo (2026-05-21 시연 직전 베이스라인)

var CACHE_NAME = 'bustago-v2-demo';
var CACHE_URLS = [
  'index.html',
  'style.css',
  'app.js',
  '../shared/api.js',
  'manifest.json'
];

// Install: cache static assets
self.addEventListener('install', function (event) {
  event.waitUntil(
    caches.open(CACHE_NAME).then(function (cache) {
      return cache.addAll(CACHE_URLS);
    })
  );
  self.skipWaiting();
});

// Activate: clean old caches
self.addEventListener('activate', function (event) {
  event.waitUntil(
    caches.keys().then(function (names) {
      return Promise.all(
        names.filter(function (name) { return name !== CACHE_NAME; })
             .map(function (name) { return caches.delete(name); })
      );
    })
  );
  self.clients.claim();
});

// Fetch: network first, cache fallback
self.addEventListener('fetch', function (event) {
  // Only cache GET requests
  if (event.request.method !== 'GET') return;

  // For API calls: network only (don't cache dynamic data)
  if (event.request.url.includes('/api/')) {
    event.respondWith(
      fetch(event.request).catch(function () {
        return new Response(
          JSON.stringify({ status: 'error', message: 'offline' }),
          { headers: { 'Content-Type': 'application/json' } }
        );
      })
    );
    return;
  }

  // For static assets: network first, fallback to cache
  event.respondWith(
    fetch(event.request).then(function (response) {
      var clone = response.clone();
      caches.open(CACHE_NAME).then(function (cache) {
        cache.put(event.request, clone);
      });
      return response;
    }).catch(function () {
      return caches.match(event.request);
    })
  );
});
