
export const emptyGSReturn = {
    role: null,
    playerId: null,
    lobbyStatus: null,
    restartStatus: null,
    gameOverData: null,
    deadPlayers: new Set(),
    // No-op functions (they do nothing when called)
    sendHeadPosition: () => { },
    setCurrentHead: () => { },
    sendVoiceCommand: () => { },
    sendReady: () => { },
    sendRestart: () => { },
};
