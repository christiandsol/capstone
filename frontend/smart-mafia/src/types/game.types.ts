// export interface GameState {
//     playerId: number | null;
//     role: string | null;
//     headPosition: string;
//     isListening: boolean;
//     status: string;
//     isStarted: boolean;
// }

export interface LobbyStatus {
    ready_count: number;
    total_count: number;
    min_players: number;
    max_players: number;
    players: { [name: string]: boolean };
}

export interface RestartStatus {
    restart_count: number;
    total_count: number;
    players: { [name: string]: boolean };
}

export interface GameOverData {
    winner: string;
    mafia: string[];
}


export interface UseGameSocketReturn {
    role: string | null;
    playerId: number | null;
    lobbyStatus: LobbyStatus | null;
    restartStatus: RestartStatus | null;
    gameOverData: GameOverData | null;
    deadPlayers: Set<string>;
    sendHeadPosition: (position: string) => void;
    setCurrentHead: (position: string) => void;
    sendVoiceCommand: (command: number) => void;
    sendReady: () => void;
    sendRestart: () => void;
}

export interface VoiceCommand {
    phrase: string;
    code: number;
}

export interface SignalData {
    type?: string;
    candidate?: RTCIceCandidate;
}
