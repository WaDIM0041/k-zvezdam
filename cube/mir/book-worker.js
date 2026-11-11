var BOOK_CACHE = 'kzvezdam-book-v1';
self.addEventListener('install', function (event) { event.waitUntil(self.skipWaiting()); });
self.addEventListener('activate', function (event) { event.waitUntil(self.clients.claim()); });
self.addEventListener('fetch', function (event) {
  if (event.request.method !== 'GET' || new URL(event.request.url).origin !== self.location.origin) return;
  event.respondWith(fetch(event.request).catch(async function () {
    var cache = await caches.open(BOOK_CACHE);
    var saved = await cache.match(event.request, {ignoreSearch: true});
    if (!saved && event.request.mode === 'navigate') {
      var url = new URL(event.request.url);
      url.pathname = url.pathname.replace(/\/$/, '') + '/';
      saved = await cache.match(url.href, {ignoreSearch: true});
    }
    return saved || new Response('Эта страница ещё не сохранена. Подключитесь к интернету и сохраните книгу.', {status: 503, headers: {'Content-Type': 'text/plain; charset=utf-8'}});
  }));
});
