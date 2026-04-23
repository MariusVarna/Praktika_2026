window.CONFIG = {
    // TODO: Update these URLs to render later
    /*
    API_BASE: 'https://url.onrender.com',
    WS_BASE: 'wss://url.onrender.com',
    ENV: 'production'
    */
    API_BASE: 'http://localhost:8000',
    WS_BASE: 'ws://localhost:8000',
    ENV: 'development'
};

// Auto-detect local development environment
if (window.location.hostname === 'localhost' || 
    window.location.hostname === '127.0.0.1' ||
    window.location.hostname === '') {
    window.CONFIG.API_BASE = 'http://localhost:8000';
    window.CONFIG.WS_BASE = 'ws://localhost:8000';
    window.CONFIG.ENV = 'development';
    console.log('[CONFIG] Running in development mode');
}

console.log('[CONFIG] Loaded configuration:', window.CONFIG);
