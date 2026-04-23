// ═══════════════════════════════════════════════════════════════════════════
// api.js — Frontend API Client
// ═══════════════════════════════════════════════════════════════════════════
// API endpoints for frontend.
// Deploy FastAPI backend to Render/Railway/Fly.io or something else and update API_BASE.
// ═══════════════════════════════════════════════════════════════════════════

// ── CONFIGURATION ────────────────────────────────────────────────────────────

/**
 * add per-page this script:
 *   <script>window.API_BASE = 'https://your-backend.onrender.com';</script>
 *   <script src="/js/api.js"></script>
 */

// For local development on Mac/Linux, 127.0.0.1 is more reliable than localhost (which might try IPv6)
const API_BASE = (window.API_BASE || 'http://localhost:8000').replace(/\/$/, '');
/**
 * WebSocket Base URL (derived from API_BASE)
 * Automatically converts http:// to ws:// and https:// to wss://
 */
const WS_BASE = API_BASE.replace(/^http/, 'ws').replace(/\/+$/, '');
// const WS_BASE = API_BASE.replace(/^http/, 'ws');

console.log('[API] Configured endpoints:', { API_BASE, WS_BASE });

// ── SESSION STORAGE KEYS ─────────────────────────────────────────────────────

/**
 * Keys used to persist user state across page navigations
 * Stored in sessionStorage (cleared when browser tab closes)
 */
const KEYS = {
    ADMIN_ID: 'adminId',        // Admin authentication token (the username)
    ADMIN_USERNAME: 'adminUser', // Admin username
    SESSION_ID: 'sessionId',     // Active session database ID
    JOIN_CODE: 'joinCode',      // 6-digit PIN code to join session
    USER_ID: 'userId',        // Player's user ID (returned on join)
    TEAM_NAME: 'teamName',      // Player's team name
    ROUND_ID: 'roundId',       // Current round database ID
    ROUND_NUM: 'roundNum',      // Current round number (1-based)
};

// ── HELPER FUNCTIONS ─────────────────────────────────────────────────────────

async function apiFetch(path, options = {}) {
    const url = API_BASE + path;
    const adminId = sessionStorage.getItem(KEYS.ADMIN_ID);

    const defaults = {
        headers: {
            'Content-Type': 'application/json',
        },
    };

    if (adminId) {
        defaults.headers['admin-id'] = adminId;
    }

    const merged = { ...defaults, ...options };
    merged.headers = { ...defaults.headers, ...options.headers };

    // Auto-stringify body if it's an object
    if (merged.body && typeof merged.body !== 'string' && !(merged.body instanceof FormData)) {
        merged.body = JSON.stringify(merged.body);
    }
// ... (log lines removed for brevity in snippet)
    try {
        const res = await fetch(url, merged);
        if (!res.ok) {
            let detail = res.statusText;
            try {
                const errorData = await res.json();
                detail = errorData.detail || detail;
            } catch (_) {}
            throw new Error(detail);
        }
        if (res.status === 204) return null;
        return await res.json();
    } catch (error) {
        console.error('[API] Request failed:', error);
        throw error;
    }
}

// ── AUTH API ─────────────────────────────────────────────────────────────────

const Auth = {
    register(username, password) {
        return apiFetch('/api/admin/auth/register', {
            method: 'POST',
            body: { username, password }
        });
    },
    async login(username, password) {
        const res = await apiFetch('/api/admin/auth/login', {
            method: 'POST',
            body: { username, password }
        });
        if (res && res.admin_token) {
            sessionStorage.setItem(KEYS.ADMIN_ID, res.admin_token);
            sessionStorage.setItem(KEYS.ADMIN_USERNAME, res.username);
        }
        return res;
    },
    logout() {
        sessionStorage.removeItem(KEYS.ADMIN_ID);
        sessionStorage.removeItem(KEYS.ADMIN_USERNAME);
    }
};

// ── SESSION API ──────────────────────────────────────────────────────────────

const Sessions = {
    create(data) {
        const payload = {
            admin_id: sessionStorage.getItem(KEYS.ADMIN_ID),
            game_name: data.gameName || 'Naujas žaidimas',
            start_day: data.startDay || 1,
            duration_days: data.numRounds || 5,
            bandwidth: data.bandwidth || 50,
            start_budget: data.startBudget || 10000,
            penalty_k: data.penaltyK || 0.5,
            penalty_b: data.penaltyB || 5.0,
            pro_rata_enabled: data.proRata !== undefined ? data.proRata : true,
            battery_max_mwh: data.maxPower || 100,
            battery_initial_mwh: data.initialPower || 20,
            battery_efficiency_charge: (data.efficiency || 90) / 100,
            battery_efficiency_discharge: (data.efficiency || 90) / 100,
            penalty_price: data.penaltyPrice || 150,
            base_demand_mw: data.baseDemand || 500,
            max_wind_mw: data.maxWind || 1000,
            max_solar_mw: data.maxSolar || 1000,
            max_demand_mw: data.maxDemand || 1000,
            forecast_error_margin: 0.15
        };
        return apiFetch('/api/sessions/', {
            method: 'POST',
            body: payload
        });
    },
    getMy() {
        return apiFetch('/api/sessions/my');
    },
    get(id) {
        return apiFetch(`/api/sessions/${id}`);
    },
    getByPin(pin) {
        return apiFetch(`/api/sessions/pin/${pin}`);
    },
    getForecast(sessionId, roundId) {
        return apiFetch(`/api/sessions/${sessionId}/round/${roundId}/forecast`);
    },
    delete(sessionId) {
        return apiFetch(`/api/sessions/${sessionId}`, { method: 'DELETE' });
    },
};

// ── ADMIN API ────────────────────────────────────────────────────────────────

const Admin = {
    startSession(sessionId) {
        return apiFetch(`/api/admin/sessions/${sessionId}/start`, { method: 'POST' });
    },
    calculateRound(sessionId, roundId) {
        return apiFetch(`/api/admin/sessions/${sessionId}/round/${roundId}/calculate`, { method: 'POST' });
    },
    nextRound(sessionId) {
        return apiFetch(`/api/admin/sessions/${sessionId}/next`, { method: 'POST' });
    },
    getResults(sessionId, roundId) {
        return apiFetch(`/api/admin/sessions/${sessionId}/round/${roundId}/results`);
    }
};

// ── PLAYER API ───────────────────────────────────────────────────────────────

/**
 * Player Actions Endpoints
 * Handle player joining teams and sessions
 */
const Players = {

    /**
     * Join a session with a 6-digit PIN and team name
     * 
     * POST /api/players/join
     * 
     * @param {string} name - Team name to join/create
     * @param {string} joinCode - 6-digit PIN code
     * 
     * @returns {Promise<object>} User and team information
     * 
     * Request body:
     *   {
     *     "name": "Team Alpha",
     *     "join_code": "123456"
     *   }
     * 
     * Response format:
     *   {
     *     userId: 42,
     *     teamId: "team_123456789",
     *     sessionId: 1,
     *     teamName: "Komanda 1",
     *     balance: 10000,
     *     sessionStatus: "waiting"
     *   }
     * 
     *   - Creates new team if name doesn't exist
     *   - Returns existing team data if name matches
     *   - Generates unique userId for tracking
     * 
     * Errors:
     *   - 404: Invalid PIN code
     *   - 409: Team name already taken (different password)
     */
    join(name, joinCode, password) {
        return apiFetch('/api/players/join', {
            method: 'POST',
            body: {
                name,
                join_code: joinCode,
                password
            }
        });
    },
    getState(playerId) {
        return apiFetch(`/api/players/${playerId}/state`);
    }
};

// ── BIDS API ─────────────────────────────────────────────────────────────────

/**
 * Bidding Endpoints
 * Submit and manage energy trading bids
 */
const Bids = {

    /**
     * Submit all bids for a round (up to 24 hours × 3 bids/hour)
     * 
     * POST /api/bids/?user_id={userId}&round_id={roundId}
     * 
     * @param {number} userId - Player's user ID
     * @param {number} roundId - Round number to submit bids for
     * @param {Array<object>} bidsArray - Array of bid objects
     * @param {number} bidsArray[].hour - Hour of day (0-23)
     * @param {number} bidsArray[].volume_mwh - Energy volume (MW)
     * @param {number} bidsArray[].price - Bid price ($/MWh)
     * @param {string} bidsArray[].bid_type - "buy" or "sell"
     * 
     * @returns {Promise<object>} Submission confirmation
     * 
     * Request example:
     *   [
     *     {hour: 0, volume_mwh: 50, price: 65, bid_type: "buy"},
     *     {hour: 0, volume_mwh: 30, price: 70, bid_type: "buy"},
     *     {hour: 1, volume_mwh: 40, price: 68, bid_type: "sell"}
     *   ]
     * 
     * Response format:
     *   {
     *     success: true,
     *     bidsSubmitted: 72,  // Total count
     *     teamId: "team_123456789"
     *   }
     * 
     *   - Frontend filters to only send bids where price > 0 AND volume > 0
     *   - Multiple bids per hour (up to 3)
     *   - Each bid is stored separately with timestamp
     *   - Requires session.betsOpen = true
     */
    submit(userId, roundId, bidsArray) {
        // Filter out invalid bids before sending
        const cleanBids = bidsArray.filter(b =>
            b.price !== undefined && b.volume_mwh > 0
        );

        return apiFetch(
            `/api/bids/?user_id=${userId}&round_id=${roundId}`,
            {
                method: 'POST',
                body: cleanBids,
            }
        );
    },
};

// ── WEBSOCKET CLIENT ─────────────────────────────────────────────────────────

/**
 * Open a WebSocket connection for real-time session updates
 * 
 * WebSocket URL: ws://backend/ws/session/{sessionId}
 * 
 * @param {number} sessionId - Session database ID
 * @param {object} handlers - Event handlers
 * @param {function} handlers.onOpen - Called when connection opens
 * @param {function} handlers.onMessage - Called on incoming message (parsed JSON)
 * @param {function} handlers.onClose - Called when connection closes
 * @param {function} handlers.onError - Called on connection error
 * 
 * @returns {WebSocket} WebSocket instance
 * 
 * Message Types (Server → Client):
 * 
 *   1. Session Update
 *      {
 *        type: "session_update",
 *        data: {
 *          status: "active",
 *          currentRound: 2,
 *          betsOpen: true,
 *          roundStarted: true
 *        }
 *      }
 * 
 *   2. Team Joined
 *      {
 *        type: "team_joined",
 *        data: {
 *          teamId: "team_123",
 *          teamName: "Komanda 1",
 *          totalTeams: 5
 *        }
 *      }
 * 
 *   3. Bids Updated
 *      {
 *        type: "bids_updated",
 *        data: {
 *          teamId: "team_123",
 *          round: 1,
 *          submitted: true
 *        }
 *      }
 * 
 *   4. Round Started
 *      {
 *        type: "round_started",
 *        data: {
 *          round: 2,
 *          day: 2
 *        }
 *      }
 * 
 *   5. Round Ended
 *      {
 *        type: "round_ended",
 *        data: {
 *          round: 1,
 *          results: { /* calculation results *\/ }
 *        }
 *      }
 * 
 * Example usage:
 *   const ws = openSessionWS(sessionId, {
 *     onOpen: () => console.log('Connected'),
 *     onMessage: (data) => {
 *       if (data.type === 'session_update') {
 *         updateUI(data.data);
 *       }
 *     },
 *     onClose: () => console.log('Disconnected'),
 *     onError: (e) => console.error('WS Error:', e)
 *   });
 */
function openSessionWS(sessionId, handlers = {}) {
    const wsUrl = `${WS_BASE}/ws/session/${sessionId}`;
    console.log('[WebSocket] Connecting to:', wsUrl);

    const ws = new WebSocket(wsUrl);

    ws.onopen = () => {
        console.log('[WebSocket] Connected');
        handlers.onOpen?.();
    };

    ws.onclose = () => {
        console.log('[WebSocket] Disconnected');
        handlers.onClose?.();
    };

    ws.onerror = (e) => {
        console.error('[WebSocket] Error:', e);
        handlers.onError?.(e);
    };

    ws.onmessage = (event) => {
        try {
            const data = JSON.parse(event.data);
            console.log('[WebSocket] Message:', data);
            handlers.onMessage?.(data);
        } catch (error) {
            console.error('[WebSocket] Failed to parse message:', event.data);
            handlers.onMessage?.(event.data);
        }
    };

    return ws;
}

// ── LOCAL STATE HELPERS ──────────────────────────────────────────────────────

/**
 * SessionStorage helper for managing user state
 * State persists across page navigations but clears on tab close
 */
const State = {

    /**
     * Get a value from sessionStorage
     * @param {string} key - Storage key
     * @returns {string|null}
     */
    get(key) {
        return sessionStorage.getItem(key);
    },

    /**
     * Set a value in sessionStorage
     * @param {string} key - Storage key
     * @param {string} val - Value to store
     */
    set(key, val) {
        sessionStorage.setItem(key, val);
    },

    /**
     * Remove a value from sessionStorage
     * @param {string} key - Storage key
     */
    remove(key) {
        sessionStorage.removeItem(key);
    },

    /**
     * Get an integer value from sessionStorage
     * @param {string} key - Storage key
     * @returns {number|null} Parsed integer or null
     */
    getInt(key) {
        const v = sessionStorage.getItem(key);
        return v ? parseInt(v, 10) : null;
    },

    /**
     * Clear all authentication-related state
     * Called on logout or session end
     */
    clearAuth() {
        Object.values(KEYS).forEach(k => sessionStorage.removeItem(k));
    },
};

// ── GLOBAL EXPORTS ───────────────────────────────────────────────────────────

/**
 * Expose all API clients and utilities globally
 * Allows usage in plain HTML scripts without module imports
 */
window.API = {
    Auth,
    Sessions,
    Admin,
    Players,
    Bids
};

window.WS = {
    open: openSessionWS
};

window.AppState = State;
window.KEYS = KEYS;

// Log successful initialization
console.log('[API] Client initialized successfully');
console.log('[API] Available modules:', {
    API: Object.keys(window.API),
    WS: Object.keys(window.WS),
    AppState: Object.keys(window.AppState),
    KEYS: Object.keys(window.KEYS)
});
