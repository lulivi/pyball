const CACHE_NAME = 'pyball-__VERSION__';

// Page shells + manifests + icons: safe to fetch with the default cache mode.
const PRECACHE_SHELLS = [
    '/match',
    '/manage',
    '/manifest-match.json',
    '/manifest-manage.json',
    '/icons/icon-192.png',
    '/icons/icon-512.png',
];

// Every static ES module. These are public (no auth) and unhashed, so they can be
// enumerated literally. Precaching them means an offline reopen still boots the app
// even right after a release swapped CACHE_NAME and dropped the previous cache.
const PRECACHE_ASSETS = [
    '/js/api.js',
    '/js/store.js',
    '/js/match/main.js',
    '/js/match/state.js',
    '/js/match/actions.js',
    '/js/match/views.js',
    '/js/manage/main.js',
    '/js/manage/views.js',
    '/js/manage/players.js',
    '/js/manage/signup-codes.js',
];

// allSettled: an auth-gated shell that can't be fetched yet (no cookie set) must not
// break the whole install — it falls back to being cached on first successful online
// fetch. Assets are fetched with cache:'reload' so a deploy can't seed the new cache
// with an HTTP-cached stale module.
self.addEventListener('install', event => {
    event.waitUntil(
        caches.open(CACHE_NAME).then(cache => Promise.allSettled([
            ...PRECACHE_SHELLS.map(url => cache.add(url)),
            ...PRECACHE_ASSETS.map(async url => {
                const response = await fetch(url, { cache: 'reload' });
                if (response.ok) await cache.put(url, response);
            }),
        ]))
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
