const CACHE_NAME = 'pyball-__PYBALL_SLUG__-v3';
const STATIC_ASSETS = ['__PYBALL_BASE__/match', '__PYBALL_BASE__/manage', '__PYBALL_BASE__/manifest-match.json', '__PYBALL_BASE__/manifest-manage.json', '__PYBALL_BASE__/icons/icon-192.png', '__PYBALL_BASE__/icons/icon-512.png'];

self.addEventListener('install', event => {
    event.waitUntil(
        caches.open(CACHE_NAME).then(cache => cache.addAll(STATIC_ASSETS))
    );
    self.skipWaiting();
});

self.addEventListener('activate', event => {
    event.waitUntil(
        caches.keys().then(keys =>
            Promise.all(keys.filter(k => k !== CACHE_NAME).map(k => caches.delete(k)))
        )
    );
    self.clients.claim();
});

self.addEventListener('fetch', event => {
    if (event.request.method !== 'GET') return;
    if (new URL(event.request.url).pathname.startsWith('__PYBALL_BASE__/api/')) return;

    event.respondWith(
        caches.open(CACHE_NAME).then(cache =>
            cache.match(event.request).then(cached => {
                const networkFetch = fetch(event.request)
                    .then(response => {
                        if (response.ok) cache.put(event.request, response.clone());
                        return response;
                    })
                    .catch(() => cached || new Response('Offline', { status: 503 }));
                return cached || networkFetch;
            })
        ).catch(() => new Response('Service Unavailable', { status: 503 }))
    );
});
