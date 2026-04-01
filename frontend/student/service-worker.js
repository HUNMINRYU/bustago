// BUSTAGO Service Worker - Offline Cache

var CACHE_NAME = 'bustago-v1';
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
