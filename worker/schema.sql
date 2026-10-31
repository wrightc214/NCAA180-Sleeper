-- NCAA 180 push store (Cloudflare D1). Anonymous: no names, no accounts.
-- devices: one row per browser push subscription (id = SHA-256 of the endpoint).
CREATE TABLE IF NOT EXISTS devices (
  id         TEXT PRIMARY KEY,
  endpoint   TEXT NOT NULL UNIQUE,
  p256dh     TEXT NOT NULL,
  auth       TEXT NOT NULL,
  is_test    INTEGER NOT NULL DEFAULT 0,
  created    TEXT NOT NULL,
  last_seen  TEXT NOT NULL
);
-- follows: kind = team (key "Big Sky:6" = league short name + roster ID), league (short name), event (key from config/push.json).
CREATE TABLE IF NOT EXISTS follows (
  device_id  TEXT NOT NULL REFERENCES devices(id) ON DELETE CASCADE,
  kind       TEXT NOT NULL CHECK (kind IN ('team', 'league', 'event')),
  key        TEXT NOT NULL,
  PRIMARY KEY (device_id, kind, key)
);
CREATE INDEX IF NOT EXISTS follows_kind_key ON follows (kind, key);
