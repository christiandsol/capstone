export const API_CONFIG = {
    SOCKET_IO_URL: import.meta.env.VITE_SOCKET_IO_URL || undefined,

    GAME_SERVER_HOST:
        import.meta.env.VITE_GAME_SERVER_HOST || window.location.hostname,

    GAME_SERVER_PORT: 5050,
};

console.log('[Config] Environment:', import.meta.env.MODE);
console.log('[Config] Socket.IO URL:', API_CONFIG.SOCKET_IO_URL);
console.log('[Config] Game Server:', `${API_CONFIG.GAME_SERVER_HOST}:${API_CONFIG.GAME_SERVER_PORT}`);
