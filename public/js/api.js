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

//const API_BASE = window.API_BASE || 'http://localhost:8000';
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
    ADMIN_ID: 'adminId',       // Admin authentication token (returned on session create)
    SESSION_ID: 'sessionId',     // Active session database ID
    JOIN_CODE: 'joinCode',      // 6-digit PIN code to join session
    USER_ID: 'userId',        // Player's user ID (returned on join)
    // TEAM_ID: 'teamId',       // Player's team ID
    TEAM_NAME: 'teamName',      // Player's team name
    ROUND_ID: 'roundId',       // Current round database ID
    ROUND_NUM: 'roundNum',      // Current round number (1-based)
};

// ── HELPER FUNCTIONS ─────────────────────────────────────────────────────────

/**
 * Generic fetch wrapper with error handling
 * 
 * @param {string} path - API endpoint path (something like '/api/sessions/')
 * @param {object} options - Fetch options (method, body, headers)
 * @returns {Promise<object|null>} Parsed JSON response or null for 204
 * @throws {Error} With error message from API or generic error
 */
async function apiFetch(path, options = {}) {
    const url = API_BASE + path;

    const defaults = {
        headers: {
            'Content-Type': 'application/json',
        },
    };

    const merged = { ...defaults, ...options };

    // Auto-stringify body if it's an object
    if (merged.body && typeof merged.body !== 'string') {
        merged.body = JSON.stringify(merged.body);
    }

    console.log(`[API] ${merged.method || 'GET'} ${path}`, merged.body ? JSON.parse(merged.body) : '');

    try {
        const res = await fetch(url, merged);

        // Handle errors
        if (!res.ok) {
            let detail = res.statusText;
            try {
                const errorData = await res.json();
                detail = errorData.detail || detail;
            } catch (_) {
                // If response isn't JSON, use statusText
            }
            console.error(`[API] Error ${res.status}:`, detail);
            throw new Error(detail);
        }

        // Handle no-content responses
        if (res.status === 204) {
            console.log('[API] 204 No Content');
            return null;
        }

        const data = await res.json();
        console.log('[API] Response:', data);
        return data;

    } catch (error) {
        console.error('[API] Request failed:', error);
        throw error;
    }
}

// ── SESSION API ──────────────────────────────────────────────────────────────

/**
 * Session Management Endpoints
 * Handle creation, deletion, and querying of game sessions
 */
const Sessions = {

    /**
     * Create a new game session
     * 
     * POST /api/sessions/
     * 
     * @param {object} payload - Session configuration
     * @param {string} payload.gameName - Display name for the game
     * @param {number} payload.startDay - Starting day number
     * @param {number} payload.numRounds - Total number of rounds
     * @param {number} payload.maxPower - Battery capacity (MW)
     * @param {number} payload.bandwidth - Bandwidth (MW)
     * @param {number} payload.efficiency - Battery efficiency (%)
     * @param {number} payload.penaltyPrice - Penalty for incorrect bids ($/MWh)
     * 
     * @returns {Promise<object>} Session object with generated PIN code
     * 
     * Format:
     *   const session = await Sessions.create({
     *     gameName: "El marketo por favor",
     *     startDay: 1,
     *     numRounds: 5,
     *     maxPower: 100,
     *     bandwidth: 50,
     *     efficiency: 90,
     *     penaltyPrice: 150
     *   });
     *   console.log('Session PIN:', session.pin);
     */
    create(payload) {
        return apiFetch('/api/sessions/', {
            method: 'POST',
            body: payload
        });
    },

    /**
     * Get market forecast for a specific round
     * 
     * GET /api/sessions/{sessionId}/round/{roundId}/forecast
     * 
     * @param {number} sessionId - Session database ID
     * @param {number} roundId - Round number
     * 
     * @returns {Promise<object>} Forecast data with 24 hourly prices
     * 
     * Format:
     *   {
     *     marketPrice: 70,
     *     demand: 500,
     *     weather: "Giedra",
     *     hourlyPrices: [65.2, 63.8, ...] // 24 values
     *   }
     */
    getForecast(sessionId, roundId) {
        return apiFetch(`/api/sessions/${sessionId}/round/${roundId}/forecast`);
    },

    /**
     * Delete/archive a session
     * 
     * DELETE /api/sessions/{sessionId}?admin_id={adminId}
     * 
     * @param {number} sessionId - Session database ID
     * @param {string} adminId - Admin authentication token
     * 
     * @returns {Promise<null>} 204 No Content on success
     * 
     * Note: Requires admin_id for authorization
     */
    delete(sessionId, adminId) {
        return apiFetch(
            `/api/sessions/${sessionId}?admin_id=${encodeURIComponent(adminId)}`,
            { method: 'DELETE' }
        );
    },
};

// ── ADMIN API ────────────────────────────────────────────────────────────────

/**
 * Admin Control Endpoints
 * Manage game flow: start session, calculate rounds, advance to next round
 * All endpoints require admin_id for authorization
 */
const Admin = {

    /**
     * Start the game session (creates round 1)
     * 
     * POST /api/admin/sessions/{sessionId}/start?admin_id={adminId}
     * 
     * @param {number} sessionId - Session database ID
     * @param {string} adminId - Admin authentication token
     * 
     * @returns {Promise<object>} Updated session with status='active'
     * 
     *   - Sets session.status = 'active'
     *   - Sets session.currentRound = 1
     *   - Broadcasts WebSocket update to all connected clients
     */
    startSession(sessionId, adminId) {
        return apiFetch(
            `/api/admin/sessions/${sessionId}/start?admin_id=${encodeURIComponent(adminId)}`,
            { method: 'POST' }
        );
    },

    /**
     * End bidding and calculate results for a round
     * 
     * POST /api/admin/sessions/{sessionId}/round/{roundId}/calculate?admin_id={adminId}
     * 
     * @param {number} sessionId - Session database ID
     * @param {number} roundId - Round number to calculate
     * @param {string} adminId - Admin authentication token
     * 
     * @returns {Promise<object>} Calculation results with transactions and balances
     * 
     * Response format:
     *   {
     *     success: true,
     *     results: {
     *       clearingPrice: 68.5,
     *       transactions: [{teamId, teamName, type, mw, price, profit}, ...],
     *       teamBalances: {teamId: newBalance, ...}
     *     }
     *   }
     * 
     *   - Matches all team bids to market prices
     *   - Calculates clearing prices per hour
     *   - Updates team balances based on trades
     *   - Records all transactions
     *   - Closes betting (betsOpen = false)
     */
    calculateRound(sessionId, roundId, adminId) {
        return apiFetch(
            `/api/admin/sessions/${sessionId}/round/${roundId}/calculate?admin_id=${encodeURIComponent(adminId)}`,
            { method: 'POST' }
        );
    },

    /**
     * Advance to the next round
     * 
     * POST /api/admin/sessions/{sessionId}/next?admin_id={adminId}
     * 
     * @param {number} sessionId - Session database ID
     * @param {string} adminId - Admin authentication token
     * 
     * @returns {Promise<object>} New round info
     * 
     * Response format:
     *   {
     *     success: true,
     *     newRound: 2,
     *     newDay: 2
     *   }
     * 
     *   - Increments session.currentRound
     *   - Updates session.currentDay
     *   - Sets roundStarted = false
     *   - Generates new market conditions (price, demand, weather)
     *   - Broadcasts update via WebSocket
     */
    nextRound(sessionId, adminId) {
        return apiFetch(
            `/api/admin/sessions/${sessionId}/next?admin_id=${encodeURIComponent(adminId)}`,
            { method: 'POST' }
        );
    },
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
    join(name, joinCode) {
        return apiFetch('/api/players/join', {
            method: 'POST',
            body: {
                name,
                join_code: joinCode
            }
        });
    },
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
            b.price > 0 && b.volume_mwh > 0
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
