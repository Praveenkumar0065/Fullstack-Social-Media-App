const CACHE_NAME = "pulsegram-v101";
const ASSETS = ["/", "/manifest.webmanifest", "/icons/icon-192.svg", "/icons/icon-512.svg"];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(ASSETS))
  );
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== CACHE_NAME).map((k) => caches.delete(k)))
    )
  );
  self.clients.claim();
});

self.addEventListener("fetch", (event) => {
  if (event.request.method !== "GET") return;

  const reqUrl = new URL(event.request.url);
  const isSameOrigin = reqUrl.origin === self.location.origin;
  const isApi = reqUrl.pathname.startsWith("/api/");
  const isStaticAsset = /\.(?:js|css|svg|png|jpg|jpeg|gif|webp|ico|woff2?)$/i.test(reqUrl.pathname);
  const isNavigation = event.request.mode === "navigate";

  // Never cache API responses to avoid stale auth/data issues.
  if (isApi) return;

  if (!isSameOrigin) return;

  event.respondWith(
    (isStaticAsset
      ? caches.match(event.request).then((cached) => {
          if (cached) return cached;
          return fetch(event.request).then((response) => {
            const copy = response.clone();
            caches.open(CACHE_NAME).then((cache) => cache.put(event.request, copy));
            return response;
          });
        })
      : fetch(event.request)
          .then((response) => response)
          .catch(() => {
            if (isNavigation) return caches.match("/");
            return caches.match(event.request);
          }))
  );
});
