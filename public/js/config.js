// config.js
window.CONFIG = {
    API_BASE: '',
    WS_BASE: '',
    ENV: ''
};
if (window.location.hostname === 'localhost' ||
    window.location.hostname === '127.0.0.1') {
    // Development mode
    window.CONFIG.API_BASE = 'http://localhost:8000';
    window.CONFIG.WS_BASE = 'ws://localhost:8000';
    window.CONFIG.ENV = 'development';
    console.log('[CONFIG] Running in development mode');
} else {
    const BACKEND_URL = 'https://energy-trading-backend-pqde.onrender.com';

    window.CONFIG.API_BASE = BACKEND_URL;
    window.CONFIG.WS_BASE = BACKEND_URL.replace(/^http/, 'wss');
    window.CONFIG.ENV = 'production';
    console.log('[CONFIG] Running in production mode');
}

console.log('[CONFIG] Loaded configuration:', window.CONFIG);