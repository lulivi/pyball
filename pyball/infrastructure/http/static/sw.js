const CACHE_NAME = 'pyball-__VERSION__';
const PRECACHE = [
    '/match',
    '/manage',
    '/manifest-match.json',
    '/manifest-manage.json',
    '/icons/icon-192.png',
    '/icons/icon-512.png',
];

// Precache the page shells so offline fallback works from the very first launch,
// not only after a successful online visit. allSettled: an auth-gated page that
// can't be fetched yet (no cookie set) must not break the whole install — it
// falls back to being cached on first successful online fetch instead.
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
                    // Exact match first; ignoreSearch as a fallback in case the
                    // navigation URL picked up query params the cached entry lacks.
                    const cached = await cache.match(event.request)
                        || await cache.match(event.request, { ignoreSearch: true });
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
