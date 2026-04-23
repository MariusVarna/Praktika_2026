// ═══════════════════════════════════════════════════════════════════════════
// api.js — Frontend API Client
// ═══════════════════════════════════════════════════════════════════════════

// ── CONFIGURATION ────────────────────────────────────────────────────────────

const API_BASE = (window.CONFIG?.API_BASE || 'http://localhost:8000').replace(/\/$/, '');
const WS_BASE = (window.CONFIG?.WS_BASE || API_BASE.replace(/^http/, 'ws')).replace(/\/+$/, '');

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

// ── ERROR HANDLING ───────────────────────────────────────────────────────────

/**
 * Custom API Error class for better error handling
 */
class APIError extends Error {
    constructor(message, status, code) {
        super(message);
        this.name = 'APIError';
        this.status = status;
        this.code = code;
    }
    
    /**
     * Check if error is a network/connection issue
     */
    isNetworkError() {
        return this.status === 0;
    }
    
    /**
     * Check if error is authentication-related
     */
    isAuthError() {
        return this.status === 401 || this.status === 403;
    }
    
    /**
     * Check if error is a validation error
     */
    isValidationError() {
        return this.status === 422;
    }
    
    /**
     * Get user-friendly error message in Lithuanian
     */
    getUserMessage() {
        if (this.isNetworkError()) {
            return 'Nėra interneto ryšio. Patikrinkite savo prijungimą.';
        }
        
        if (this.isAuthError()) {
            return 'Prisijungimo sesija baigėsi. Prašome prisijungti iš naujo.';
        }
        
        if (this.status === 404) {
            return 'Nerasta. Patikrinkite įvestus duomenis.';
        }
        
        if (this.status >= 500) {
            return 'Serverio klaida. Bandykite dar kartą vėliau.';
        }
        
        return this.message;
    }
}

// ── HELPER FUNCTIONS ─────────────────────────────────────────────────────────

/**
 * IMPROVED: Enhanced error handling with APIError class
 */
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

    try {
        const res = await fetch(url, merged);
        
        if (!res.ok) {
            let detail = res.statusText;
            let errorCode = 'UNKNOWN_ERROR';
            
            try {
                const errorData = await res.json();
                detail = errorData.detail || detail;
                errorCode = errorData.code || errorCode;
            } catch (_) {
                // Response wasn't JSON
            }
            
            throw new APIError(detail, res.status, errorCode);
        }
        
        if (res.status === 204) return null;
        return await res.json();
        
    } catch (error) {
        // If it's already an APIError, just re-throw
        if (error instanceof APIError) {
            console.error('[API] Request failed:', error.message, `(${error.status})`);
            throw error;
        }
        
        // Network errors (no connection, CORS, etc.)
        if (error.name === 'TypeError' && error.message.includes('fetch')) {
            console.error('[API] Network error:', error);
            throw new APIError(
                'Nepavyko prisijungti prie serverio',
                0,
                'NETWORK_ERROR'
            );
        }
        
        // Other errors
        console.error('[API] Unexpected error:', error);
        throw new APIError(error.message, 0, 'UNKNOWN_ERROR');
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
    addExtraRound(sessionId) {
        return apiFetch(`/api/admin/sessions/${sessionId}/add_round`, { method: 'POST' });
    },
    endSession(sessionId) {
        return apiFetch(`/api/admin/sessions/${sessionId}/end`, { method: 'POST' });
    },
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
     * @param {string} password - Optional team password
     * 
     * @returns {Promise<object>} User and team information
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
     * 
     * @returns {Promise<object>} Submission confirmation
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
 * Open a WebSocket connection with automatic reconnection
 * 
 * @param {number} sessionId - Session database ID
 * @param {object} handlers - Event handlers
 * @param {function} handlers.onOpen - Called when connection opens
 * @param {function} handlers.onMessage - Called on incoming message (parsed JSON)
 * @param {function} handlers.onClose - Called when connection closes
 * @param {function} handlers.onError - Called on connection error
 * @param {function} handlers.onMaxRetriesReached - Called when reconnection fails
 * @param {number} retryCount - Current retry attempt (internal use)
 * 
 * @returns {WebSocket} WebSocket instance
 */
function openSessionWS(sessionId, handlers = {}, retryCount = 0) {
    const wsUrl = `${WS_BASE}/ws/session/${sessionId}`;
    const maxRetries = 5;
    const baseDelay = 1000; // 1 second
    const maxDelay = 30000; // 30 seconds
    
    console.log(`[WebSocket] Connecting to: ${wsUrl} (attempt ${retryCount + 1})`);

    const ws = new WebSocket(wsUrl);

    ws.onopen = () => {
        console.log('[WebSocket] Connected successfully');
        retryCount = 0; // Reset retry count on successful connection
        handlers.onOpen?.();
    };

    ws.onclose = (event) => {
        console.log('[WebSocket] Disconnected:', event.code, event.reason);
        handlers.onClose?.(event);
        
        // Attempt reconnection with exponential backoff
        if (retryCount < maxRetries) {
            const delay = Math.min(baseDelay * Math.pow(2, retryCount), maxDelay);
            console.log(`[WebSocket] Reconnecting in ${delay}ms... (${retryCount + 1}/${maxRetries})`);
            
            setTimeout(() => {
                openSessionWS(sessionId, handlers, retryCount + 1);
            }, delay);
        } else {
            console.error('[WebSocket] Max reconnection attempts reached');
            if (handlers.onMaxRetriesReached) {
                handlers.onMaxRetriesReached();
            }
        }
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
            // Still call handler with raw data
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
window.APIError = APIError; // ADDED: Export APIError class

// Log successful initialization
console.log('[API] Client initialized successfully');
console.log('[API] Available modules:', {
    API: Object.keys(window.API),
    WS: Object.keys(window.WS),
    AppState: Object.keys(window.AppState),
    KEYS: Object.keys(window.KEYS)
});
