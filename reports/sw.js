// NCAA 180 service worker (todo-pwa.md): offline shell + push notifications.
// Scope: reports/ (this file's folder). Bump VERSION when the caching rules change; pages and
// data are never cached forever (network first), so ordinary deploys need no bump.
const VERSION = "v1";
const SHELL = "ncaa180-shell-" + VERSION;
const DATA = "ncaa180-data-" + VERSION;
const PRECACHE = ["index.html", "app.html", "assets/app.js", "assets/icons/icon-192.png", "manifest.webmanifest"];

self.addEventListener("install", (e) => {
  e.waitUntil(caches.open(SHELL).then((c) => c.addAll(PRECACHE)).then(() => self.skipWaiting()));
});

self.addEventListener("activate", (e) => {
  e.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(keys.filter((k) => k !== SHELL && k !== DATA).map((k) => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", (e) => {
  const req = e.request;
  if (req.method !== "GET") return;
  const url = new URL(req.url);
  // Never touch other sites: live Sleeper / ESPN calls, the push store, fonts CDN handle themselves.
  if (url.origin !== self.location.origin) return;
  const isImage = /\.(png|jpe?g|svg|webp|gif)$/i.test(url.pathname);
  if (isImage) {
    // Logos and icons: cache first (they rarely change), refresh in the background.
    e.respondWith(
      caches.open(SHELL).then(async (c) => {
        const hit = await c.match(req);
        const net = fetch(req).then((r) => { if (r.ok) c.put(req, r.clone()); return r; }).catch(() => hit);
        return hit || net;
      })
    );
    return;
  }
  // Pages, scripts, styles, data: network first so numbers are always current; last good copy offline.
  e.respondWith(
    fetch(req)
      .then((r) => {
        if (r.ok) { const copy = r.clone(); caches.open(DATA).then((c) => c.put(req, copy)); }
        return r;
      })
      .catch(async () => (await caches.match(req)) || (req.mode === "navigate" ? caches.match("index.html") : Response.error()))
  );
});

// ---- push ----
self.addEventListener("push", (e) => {
  let d = {};
  try { d = e.data ? e.data.json() : {}; } catch { d = { title: "NCAA 180", body: e.data ? e.data.text() : "" }; }
  e.waitUntil(
    self.registration.showNotification(d.title || "NCAA 180", {
      body: d.body || "",
      tag: d.tag || undefined,
      icon: "assets/icons/icon-192.png",
      badge: "assets/icons/badge-96.png",
      data: { url: d.url || "index.html" },
    })
  );
});

self.addEventListener("notificationclick", (e) => {
  e.notification.close();
  const target = new URL(e.notification.data && e.notification.data.url || "index.html", self.registration.scope).href;
  e.waitUntil(
    self.clients.matchAll({ type: "window", includeUncontrolled: true }).then((list) => {
      for (const c of list) {
        if (c.url.startsWith(self.registration.scope) && "focus" in c) { c.navigate(target); return c.focus(); }
      }
      return self.clients.openWindow(target);
    })
  );
});
