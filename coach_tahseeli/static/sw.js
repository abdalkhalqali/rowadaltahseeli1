// Service Worker — رواد التحصيلي
const CACHE_NAME = 'rowad-tahseeli-v1';

// الملفات التي تُحفظ للعمل بدون إنترنت
const STATIC_ASSETS = [
  '/',
  '/static/css/style.css',
  '/static/js/main.js',
  '/static/icons/icon-192x192.png',
  '/static/icons/icon-512x512.png',
  '/offline'
];

// ── التثبيت ──
self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME).then(cache => {
      return cache.addAll(STATIC_ASSETS).catch(() => {});
    })
  );
  self.skipWaiting();
});

// ── التفعيل: حذف الـ cache القديم ──
self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(keys =>
      Promise.all(
        keys.filter(k => k !== CACHE_NAME).map(k => caches.delete(k))
      )
    )
  );
  self.clients.claim();
});

// ── معالجة الطلبات: network-first ──
self.addEventListener('fetch', event => {
  // تجاهل طلبات غير GET وطلبات API والـ admin
  if (
    event.request.method !== 'GET' ||
    event.request.url.includes('/admin') ||
    event.request.url.includes('/api/')
  ) return;

  event.respondWith(
    fetch(event.request)
      .then(response => {
        // نسخ للـ cache إن كان الرد صحيحاً
        if (response && response.status === 200 && response.type === 'basic') {
          const clone = response.clone();
          caches.open(CACHE_NAME).then(cache => cache.put(event.request, clone));
        }
        return response;
      })
      .catch(() => {
        // بدون إنترنت — ابحث في الـ cache
        return caches.match(event.request).then(cached => {
          return cached || caches.match('/offline');
        });
      })
  );
});
