const CACHE_NAME = 'pyball-__VERSION__';
const PRECACHE = [
    '/manifest-match.json',
    '/manifest-manage.json',
    '/icons/icon-192.png',
    '/icons/icon-512.png',
];

// Precache public assets only; auth-gated pages are cached on first successful
// fetch. allSettled: one failed entry must not break the whole install.
self.addEventListener('install', event => {
    event.waitUntil(
        caches.open(CACHE_NAME).then(cache =>
            Promise.allSettled(PRECACHE.map(url => cache.add(url)))
        )
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
    const url = new URL(event.request.url);
    if (url.pathname.startsWith('/api/')) return;

    const isNavigation = event.request.mode === 'navigate'
        || url.pathname === '/match' || url.pathname === '/manage';

    if (isNavigation) {
        // Network-first: fresh UI after deploys, cache fallback offline.
        event.respondWith(
            caches.open(CACHE_NAME).then(async cache => {
                try {
                    const response = await fetch(event.request);
                    if (response.ok) cache.put(event.request, response.clone());
                    return response;
                } catch {
                    const cached = await cache.match(event.request);
                    return cached || new Response('Offline', { status: 503 });
                }
            })
        );
        return;
    }

    // Static assets: cache-first.
    event.respondWith(
        caches.open(CACHE_NAME).then(async cache => {
            const cached = await cache.match(event.request);
            if (cached) return cached;
            const response = await fetch(event.request);
            if (response.ok) cache.put(event.request, response.clone());
            return response;
        }).catch(() => new Response('Offline', { status: 503 }))
    );
});
