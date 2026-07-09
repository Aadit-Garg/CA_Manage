/**
 * Sumit n Garg & Associates — Service Worker
 *
 * Cache-first for static assets, network-first for HTML pages.
 * Cache versioning via CACHE_VERSION for easy updates.
 */

const CACHE_VERSION = 'ca-manage-v2';
const STATIC_CACHE = `${CACHE_VERSION}-static`;
const DYNAMIC_CACHE = `${CACHE_VERSION}-dynamic`;

// Static assets to pre-cache on install
const STATIC_ASSETS = [
    '/static/css/app.css',
    '/static/js/app.js',
    '/static/icons/icon-192x192.png',
    '/static/icons/icon-512x512.png',
    'https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css',
    'https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.min.css',
    'https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js',
];


// ── Install: Pre-cache static assets ────────────────────────────
self.addEventListener('install', (event) => {
    console.log('[Service Worker] Installing...');
    event.waitUntil(
        caches.open(STATIC_CACHE).then((cache) => {
            console.log('[Service Worker] Pre-caching static assets');
            return cache.addAll(STATIC_ASSETS);
        })
    );
    // Activate immediately
    self.skipWaiting();
});


// ── Activate: Clean old caches ──────────────────────────────────
self.addEventListener('activate', (event) => {
    console.log('[Service Worker] Activating...');
    event.waitUntil(
        caches.keys().then((keys) => {
            return Promise.all(
                keys
                    .filter((key) => key !== STATIC_CACHE && key !== DYNAMIC_CACHE)
                    .map((key) => {
                        console.log('[Service Worker] Removing old cache:', key);
                        return caches.delete(key);
                    })
            );
        })
    );
    // Take control of all clients immediately
    self.clients.claim();
});


// ── Fetch: Strategy-based caching ───────────────────────────────
self.addEventListener('fetch', (event) => {
    const { request } = event;
    const url = new URL(request.url);

    // Skip non-GET requests
    if (request.method !== 'GET') return;

    // Bypass cache for localhost development
    if (url.hostname === 'localhost' || url.hostname === '127.0.0.1') {
        return;
    }

    // Skip chrome-extension and other non-http(s) requests
    if (!url.protocol.startsWith('http')) return;

    // Skip file downloads to prevent Service Worker blob interception issues
    if (url.pathname.includes('export') || url.pathname.includes('download') || url.pathname.includes('import-template')) {
        return;
    }

    // Strategy: Cache-first for static assets
    if (isStaticAsset(url)) {
        event.respondWith(cacheFirst(request));
        return;
    }

    // Strategy: Network-first for HTML / API
    if (request.headers.get('accept')?.includes('text/html')) {
        event.respondWith(networkFirst(request));
        return;
    }

    // Default: Network with cache fallback
    event.respondWith(networkFirst(request));
});


// ── Cache-first strategy ────────────────────────────────────────
async function cacheFirst(request) {
    const cached = await caches.match(request);
    if (cached) return cached;

    try {
        const response = await fetch(request);
        if (response.ok) {
            const cache = await caches.open(STATIC_CACHE);
            cache.put(request, response.clone());
        }
        return response;
    } catch (error) {
        // Return a basic offline response
        return new Response('Offline', {
            status: 503,
            statusText: 'Service Unavailable',
        });
    }
}


// ── Network-first strategy ──────────────────────────────────────
async function networkFirst(request) {
    try {
        const response = await fetch(request);
        if (response.ok) {
            const cache = await caches.open(DYNAMIC_CACHE);
            cache.put(request, response.clone());
        }
        return response;
    } catch (error) {
        const cached = await caches.match(request);
        if (cached) return cached;

        // Offline fallback for HTML pages
        if (request.headers.get('accept')?.includes('text/html')) {
            return new Response(
                `<!DOCTYPE html>
                <html>
                <head>
                    <meta charset="utf-8">
                    <meta name="viewport" content="width=device-width, initial-scale=1">
                    <title>Offline — Sumit n Garg & Associates</title>
                    <style>
                        body { font-family: 'Inter', sans-serif; display: flex; align-items: center; justify-content: center; min-height: 100vh; margin: 0; background: #f1f5f9; color: #1e293b; }
                        .offline { text-align: center; padding: 24px; }
                        .offline h1 { font-size: 2rem; color: #1a365d; }
                        .offline p { color: #64748b; margin: 16px 0; }
                        .offline button { background: #1a365d; color: white; border: none; padding: 12px 24px; border-radius: 8px; font-size: 1rem; cursor: pointer; }
                    </style>
                </head>
                <body>
                    <div class="offline">
                        <h1>You're Offline</h1>
                        <p>Please check your internet connection and try again.</p>
                        <button onclick="location.reload()">Retry</button>
                    </div>
                </body>
                </html>`,
                { headers: { 'Content-Type': 'text/html' } }
            );
        }

        return new Response('Offline', { status: 503 });
    }
}


// ── Helper: Identify static assets ──────────────────────────────
function isStaticAsset(url) {
    const staticExtensions = ['.css', '.js', '.svg', '.png', '.jpg', '.jpeg', '.gif', '.webp', '.woff', '.woff2', '.ttf', '.eot'];
    return staticExtensions.some((ext) => url.pathname.endsWith(ext)) ||
           url.hostname.includes('cdn.jsdelivr.net') ||
           url.hostname.includes('fonts.googleapis.com') ||
           url.hostname.includes('fonts.gstatic.com');
}

// ── Web Push Notifications ──────────────────────────────────────
self.addEventListener('push', function(event) {
    console.log('[Service Worker] Push Received.');
    let data = { title: 'Sumit n Garg & Associates', body: 'New notification', url: '/' };
    if (event.data) {
        try {
            data = event.data.json();
        } catch (e) {
            data.body = event.data.text();
        }
    }

    const title = data.title;
    const options = {
        body: data.body,
        icon: '/static/icons/icon-192x192.png',
        badge: '/static/icons/icon-192x192.png',
        data: {
            url: data.url
        }
    };

    event.waitUntil(self.registration.showNotification(title, options));
});

self.addEventListener('notificationclick', function(event) {
    console.log('[Service Worker] Notification click Received.');
    event.notification.close();
    
    if(event.notification.data && event.notification.data.url) {
        event.waitUntil(
            clients.openWindow(event.notification.data.url)
        );
    }
});
