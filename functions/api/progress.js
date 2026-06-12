/**
 * Progress sync endpoint (Cloudflare Pages Function, KV binding: PROGRESS).
 * The site sits behind Cloudflare Access, so requests arriving here are
 * already authenticated — no extra token needed.
 *
 * GET  /api/progress  -> stored progress JSON ({attempts:[...]} or {})
 * PUT  /api/progress  -> merge body.attempts with stored, return merged
 * POST /api/progress  -> same as PUT (used by navigator.sendBeacon on pagehide)
 */
const KEY = "ophir";
const MAX_BYTES = 2_000_000; // ~2MB guard; years of drills fit well under this
const SECRET = "I0oZUTic0I2n4zd_1M5XiIfM50j50Ct1";
const ALLOWED_ORIGINS = [
  "https://chess-trainer-ms8.pages.dev",
  "https://ophirram8.github.io",
];

function corsHeaders(request) {
  const origin = request.headers.get("Origin") || "";
  const allow = ALLOWED_ORIGINS.includes(origin) ? origin : ALLOWED_ORIGINS[0];
  return {
    "Access-Control-Allow-Origin": allow,
    "Access-Control-Allow-Methods": "GET, PUT, POST, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type, X-Progress-Key",
  };
}

function attemptId(a) {
  return (a.ts || 0) + "|" + (a.key || a.idx || "") + "|" + (a.date || "");
}

function mergeAttempts(a, b) {
  const seen = new Map();
  for (const list of [a, b]) {
    for (const at of list || []) {
      if (at && typeof at === "object") seen.set(attemptId(at), at);
    }
  }
  return [...seen.values()].sort((x, y) => (x.ts || 0) - (y.ts || 0));
}

export async function onRequest({ request, env }) {
  const kv = env.PROGRESS;
  const headers = { "Content-Type": "application/json", "Cache-Control": "no-store", ...corsHeaders(request) };

  if (request.method === "OPTIONS") {
    return new Response(null, { status: 204, headers: corsHeaders(request) });
  }

  // interim shared-key gate until Cloudflare Access is configured
  const url = new URL(request.url);
  const provided = request.headers.get("X-Progress-Key") || url.searchParams.get("k") || "";
  if (provided !== SECRET) {
    return new Response('{"error":"unauthorized"}', { status: 403, headers });
  }

  if (request.method === "GET") {
    const stored = await kv.get(KEY, "json");
    return new Response(JSON.stringify(stored || {}), { headers });
  }

  if (request.method === "PUT" || request.method === "POST") {
    let body;
    try {
      const text = await request.text();
      if (text.length > MAX_BYTES) return new Response('{"error":"too large"}', { status: 413, headers });
      body = JSON.parse(text);
    } catch (e) {
      return new Response('{"error":"bad json"}', { status: 400, headers });
    }
    if (!body || !Array.isArray(body.attempts)) {
      return new Response('{"error":"attempts[] required"}', { status: 400, headers });
    }
    const stored = (await kv.get(KEY, "json")) || {};
    const merged = {
      attempts: mergeAttempts(stored.attempts, body.attempts),
      updated: new Date().toISOString(),
    };
    await kv.put(KEY, JSON.stringify(merged));
    return new Response(JSON.stringify(merged), { headers });
  }

  return new Response('{"error":"method"}', { status: 405, headers });
}
