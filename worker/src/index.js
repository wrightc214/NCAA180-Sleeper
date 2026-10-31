// NCAA 180 push store -- Cloudflare Worker + D1 (todo-pwa.md).
// Stores anonymous push subscriptions and what each device follows. It never sends pushes:
// GitHub Actions does that (scripts/notify.py), because the free Worker plan caps one request
// at 50 outbound calls and 10 ms of CPU.
//
// Public (called by the site, reports/assets/app.js):
//   POST /subscribe    {subscription: {endpoint, keys: {p256dh, auth}}, follows: [{kind, key}], test}
//   POST /unsubscribe  {endpoint}
//   GET  /health
// Admin (Authorization: Bearer ADMIN_TOKEN; called by GitHub Actions only):
//   GET  /admin/devices          every device with its follows
//   POST /admin/prune {ids: []}  delete devices the push services reported as gone
//
// Bindings (worker/wrangler.toml): DB (D1). Secret: ADMIN_TOKEN. Var: ALLOWED_ORIGINS (comma list).

const KINDS = new Set(["team", "league", "event"]);
const MAX_FOLLOWS = 60;
const MAX_BODY = 16 * 1024;

export default {
  async fetch(req, env) {
    const url = new URL(req.url);
    const cors = corsHeaders(req, env);
    if (req.method === "OPTIONS") return new Response(null, { status: 204, headers: cors });
    try {
      if (url.pathname === "/health") return json({ ok: true }, 200, cors);
      if (url.pathname === "/subscribe" && req.method === "POST") return json(await subscribe(req, env), 200, cors);
      if (url.pathname === "/unsubscribe" && req.method === "POST") return json(await unsubscribe(req, env), 200, cors);
      if (url.pathname.startsWith("/admin/")) {
        if (!authorized(req, env)) return json({ error: "unauthorized" }, 401);
        if (url.pathname === "/admin/devices" && req.method === "GET") return json(await devices(env), 200);
        if (url.pathname === "/admin/prune" && req.method === "POST") return json(await prune(req, env), 200);
      }
      return json({ error: "not found" }, 404, cors);
    } catch (e) {
      const status = e instanceof BadRequest ? 400 : 500;
      return json({ error: status === 400 ? e.message : "server error" }, status, cors);
    }
  },
};

class BadRequest extends Error {}

function json(body, status, headers = {}) {
  return new Response(JSON.stringify(body), { status, headers: { "content-type": "application/json", ...headers } });
}

function corsHeaders(req, env) {
  const origin = req.headers.get("Origin") || "";
  const allowed = (env.ALLOWED_ORIGINS || "").split(",").map((s) => s.trim()).filter(Boolean);
  if (!allowed.includes(origin)) return {};
  return {
    "Access-Control-Allow-Origin": origin,
    "Access-Control-Allow-Methods": "POST, GET, OPTIONS",
    "Access-Control-Allow-Headers": "content-type",
    "Vary": "Origin",
  };
}

function authorized(req, env) {
  const h = req.headers.get("Authorization") || "";
  const token = env.ADMIN_TOKEN || "";
  if (!token || h.length !== token.length + 7) return false;
  // constant-time compare
  let diff = 0;
  const want = "Bearer " + token;
  for (let i = 0; i < want.length; i++) diff |= want.charCodeAt(i) ^ h.charCodeAt(i);
  return diff === 0;
}

async function readJson(req) {
  const text = await req.text();
  if (text.length > MAX_BODY) throw new BadRequest("body too large");
  try {
    return JSON.parse(text);
  } catch {
    throw new BadRequest("bad json");
  }
}

async function sha256(s) {
  const buf = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(s));
  return [...new Uint8Array(buf)].map((b) => b.toString(16).padStart(2, "0")).join("");
}

function validEndpoint(e) {
  try {
    const u = new URL(e);
    return u.protocol === "https:" && e.length <= 1024;
  } catch {
    return false;
  }
}

function cleanFollows(list) {
  if (!Array.isArray(list)) throw new BadRequest("follows must be a list");
  if (list.length > MAX_FOLLOWS) throw new BadRequest(`at most ${MAX_FOLLOWS} follows`);
  const seen = new Set();
  const out = [];
  for (const f of list) {
    const kind = String(f && f.kind || "");
    const key = String(f && f.key || "").trim();
    if (!KINDS.has(kind) || !key || key.length > 64) throw new BadRequest("bad follow");
    const k = kind + "\u0000" + key;
    if (!seen.has(k)) { seen.add(k); out.push({ kind, key }); }
  }
  return out;
}

async function subscribe(req, env) {
  const body = await readJson(req);
  const sub = body.subscription || {};
  const keys = sub.keys || {};
  if (!validEndpoint(sub.endpoint)) throw new BadRequest("bad endpoint");
  if (!keys.p256dh || !keys.auth || String(keys.p256dh).length > 200 || String(keys.auth).length > 100)
    throw new BadRequest("bad keys");
  const follows = cleanFollows(body.follows || []);
  const id = await sha256(sub.endpoint);
  const now = new Date().toISOString();
  const stmts = [
    env.DB.prepare(
      `INSERT INTO devices (id, endpoint, p256dh, auth, is_test, created, last_seen)
       VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?6)
       ON CONFLICT(id) DO UPDATE SET p256dh = ?3, auth = ?4, is_test = ?5, last_seen = ?6`
    ).bind(id, sub.endpoint, String(keys.p256dh), String(keys.auth), body.test ? 1 : 0, now),
    env.DB.prepare("DELETE FROM follows WHERE device_id = ?1").bind(id),
    ...follows.map((f) => env.DB.prepare("INSERT INTO follows (device_id, kind, key) VALUES (?1, ?2, ?3)").bind(id, f.kind, f.key)),
  ];
  await env.DB.batch(stmts);
  return { ok: true, follows: follows.length };
}

async function unsubscribe(req, env) {
  const body = await readJson(req);
  if (!validEndpoint(body.endpoint)) throw new BadRequest("bad endpoint");
  const id = await sha256(body.endpoint);
  await env.DB.batch([
    env.DB.prepare("DELETE FROM follows WHERE device_id = ?1").bind(id),
    env.DB.prepare("DELETE FROM devices WHERE id = ?1").bind(id),
  ]);
  return { ok: true };
}

async function devices(env) {
  const [d, f] = await env.DB.batch([
    env.DB.prepare("SELECT id, endpoint, p256dh, auth, is_test FROM devices"),
    env.DB.prepare("SELECT device_id, kind, key FROM follows"),
  ]);
  const byId = new Map(d.results.map((r) => [r.id, { ...r, is_test: !!r.is_test, follows: [] }]));
  for (const r of f.results) {
    const dev = byId.get(r.device_id);
    if (dev) dev.follows.push({ kind: r.kind, key: r.key });
  }
  return { devices: [...byId.values()] };
}

async function prune(req, env) {
  const body = await readJson(req);
  const ids = Array.isArray(body.ids) ? body.ids.filter((x) => typeof x === "string").slice(0, 500) : [];
  if (!ids.length) return { ok: true, pruned: 0 };
  await env.DB.batch(ids.flatMap((id) => [
    env.DB.prepare("DELETE FROM follows WHERE device_id = ?1").bind(id),
    env.DB.prepare("DELETE FROM devices WHERE id = ?1").bind(id),
  ]));
  return { ok: true, pruned: ids.length };
}
