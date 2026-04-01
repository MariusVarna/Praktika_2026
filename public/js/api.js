// api.js — Shared API + WebSocket client
// ── CONFIG ────────────────────────────────────────────────────
// FastAPI backend URL.
// For local testing:  http://localhost:8000
// For real testing...: https://backend-url.com  ( Render / Railway / Fly.io, etc. etc. )
const API_BASE = window.API_BASE || 'http://localhost:8000';
const WS_BASE = API_BASE.replace(/^http/, 'ws');


/*
In each HTML page, before api.js
<script>window.API\_BASE = 'https://backend-url.com';</script>
<script src="/js/api.js"></script>
*/
// ── SESSION STORAGE KEYS ──────────────────────────────────────
// Used across pages to persist identity between navigations.
const KEYS = {
  ADMIN_ID:   'adminId',       // string — the admin_id token used to create the session
  SESSION_ID: 'sessionId',     // int    — DB id of the active session
  JOIN_CODE:  'joinCode',      // string — 6-char join code shown to players
  USER_ID:    'userId',        // int    — DB id of the current player
  TEAM_NAME:  'teamName',      // string — display name
  ROUND_ID:   'roundId',       // int    — current round DB id
  ROUND_NUM:  'roundNum',      // int    — round number (1-based)
};
// ── HELPERS ───────────────────────────────────────────────────
async function apiFetch(path, options = {}) {
  const url = API_BASE + path;
  const defaults = {
    headers: { 'Content-Type': 'application/json' },
  };
  const merged = { ...defaults, ...options };
  if (merged.body && typeof merged.body !== 'string') {
    merged.body = JSON.stringify(merged.body);
  }
  const res = await fetch(url, merged);
  if (!res.ok) {
    let detail = res.statusText;
    try { detail = (await res.json()).detail || detail; } catch(_) {}
    throw new Error(detail);
  }
  if (res.status === 204) return null;
  return res.json();
}
// ── SESSION API ───────────────────────────────────────────────
const Sessions = {
  /* Admin creates a new game session */
  create(payload) {
    return apiFetch('/api/sessions/', { method: 'POST', body: payload });
  },
  /* Get forecast for a round */
  getForecast(sessionId, roundId) {
    return apiFetch(`/api/sessions/${sessionId}/round/${roundId}/forecast`);
  },
  /* Delete a session */
  delete(sessionId, adminId) {
    return apiFetch(`/api/sessions/${sessionId}?admin_id=${encodeURIComponent(adminId)}`, { method: 'DELETE' });
  },
};
// ── ADMIN API ─────────────────────────────────────────────────
const Admin = {
  /* Start the session, creates round 1 */
  startSession(sessionId, adminId) {
    return apiFetch(`/api/admin/sessions/${sessionId}/start?admin_id=${encodeURIComponent(adminId)}`, { method: 'POST' });
  },
  /* End bidding and calculate results for a round */
  calculateRound(sessionId, roundId, adminId) {
    return apiFetch(`/api/admin/sessions/${sessionId}/round/${roundId}/calculate?admin_id=${encodeURIComponent(adminId)}`, { method: 'POST' });
  },
  /* Advance to the next round */
  nextRound(sessionId, adminId) {
    return apiFetch(`/api/admin/sessions/${sessionId}/next?admin_id=${encodeURIComponent(adminId)}`, { method: 'POST' });
  },
};
// ── PLAYER API ────────────────────────────────────────────────
const Players = {
  /* Join a session with a 6-char code and a team name */
  join(name, joinCode) {
    return apiFetch('/api/players/join', { method: 'POST', body: { name, join_code: joinCode } });
  },
};
// ── BIDS API ──────────────────────────────────────────────────
const Bids = {
  /**
   * Submit all 24 bids for a round.
   * bidsArray: [{hour, volume_mwh, price, bid_type}, ...]
   * Only rows where price > 0 AND volume > 0 are sent.
   */
  submit(userId, roundId, bidsArray) {
    const clean = bidsArray.filter(b => b.price > 0 && b.volume_mwh > 0);
    return apiFetch(`/api/bids/?user_id=${userId}&round_id=${roundId}`, {
      method: 'POST',
      body: clean,
    });
  },
};
// ── WEBSOCKET ─────────────────────────────────────────────────
/*
 * Opens a WebSocket for a given session_id.
 * handlers: { onOpen, onMessage(data), onClose, onError }
 * Returns the WebSocket instance.
 */
function openSessionWS(sessionId, handlers = {}) {
  const ws = new WebSocket(`${WS_BASE}/ws/session/${sessionId}`);
  ws.onopen    = () => handlers.onOpen?.();
  ws.onclose   = () => handlers.onClose?.();
  ws.onerror   = (e) => handlers.onError?.(e);
  ws.onmessage = (e) => {
    try { handlers.onMessage?.(JSON.parse(e.data)); }
    catch(_) { handlers.onMessage?.(e.data); }
  };
  return ws;
}
// ── LOCAL STATE HELPERS ─────────────────────────
const State = {
  get(key)        { return sessionStorage.getItem(key); },
  set(key, val)   { sessionStorage.setItem(key, val); },
  remove(key)     { sessionStorage.removeItem(key); },
  getInt(key)     { const v = sessionStorage.getItem(key); return v ? parseInt(v, 10) : null; },
  clearAuth()     { Object.values(KEYS).forEach(k => sessionStorage.removeItem(k)); },
};
// Expose everything globally so plain HTML scripts can use them
window.API      = { Sessions, Admin, Players, Bids };
window.WS       = { open: openSessionWS };
window.AppState = State;
window.KEYS     = KEYS;