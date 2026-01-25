export interface GameState {
    playerId: number | null;
    role: string | null;
    headPosition: string;
    isListening: boolean;
    status: string;
    isStarted: boolean;
}

export interface VoiceCommand {
    phrase: string;
    code: number;
}

export interface SignalData {
    type?: string;
    candidate?: RTCIceCandidate;
}
