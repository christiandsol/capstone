const isDevelopment = import.meta.env.MODE === 'development';

export const API_CONFIG = {
    // Socket.IO (WebRTC signaling)
    // Production: uses Nginx proxy (no URL)
    // Development: connects directly to remote server
    SOCKET_IO_URL: isDevelopment
        ? 'http://163.192.0.247:3001'
        : undefined,

    // Python WebSocket (game server)
    GAME_SERVER_HOST: isDevelopment
        ? '163.192.0.247'
        : window.location.hostname,

    GAME_SERVER_PORT: 5050,
};

console.log('[Config] Environment:', import.meta.env.MODE);
console.log('[Config] Socket.IO URL:', API_CONFIG.SOCKET_IO_URL);
console.log('[Config] Game Server:', `${API_CONFIG.GAME_SERVER_HOST}:${API_CONFIG.GAME_SERVER_PORT}`);
