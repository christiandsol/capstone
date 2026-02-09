import { useEffect, useRef, useState } from 'react';
import { API_CONFIG } from '../config/api.config';

interface LobbyStatus {
    ready_count: number;
    total_count: number;
    min_players: number;
    max_players: number;
    players: { [name: string]: boolean };
}

interface RestartStatus {
    restart_count: number;
    total_count: number;
    players: { [name: string]: boolean };
}

interface GameOverData {
    winner: string;
    mafia: string[];
}

interface UseGameSocketReturn {
    role: string | null;
    playerId: number | null;
    lobbyStatus: LobbyStatus | null;
    restartStatus: RestartStatus | null;
    gameOverData: GameOverData | null;
    gameStage: string | null;
    sendHeadPosition: (position: string) => void;
    setCurrentHead: (position: string) => void;
    sendVoiceCommand: (command: number) => void;
    sendReady: () => void;
    sendRestart: () => void;
}

export const useGameSocket = (
    onStatusChange: (status: string) => void,
    playerName: string
): UseGameSocketReturn => {
    const gameSocketRef = useRef<WebSocket | null>(null);
    const currentHeadRef = useRef<string>('headDown');
    const [role, setRole] = useState<string | null>(null);
    const [playerId, setPlayerId] = useState<number | null>(null);
    const [lobbyStatus, setLobbyStatus] = useState<LobbyStatus | null>(null);
    const [restartStatus, setRestartStatus] = useState<RestartStatus | null>(null);
    const [gameOverData, setGameOverData] = useState<GameOverData | null>(null);
    const [gameStage, setGameStage] = useState<string | null>(null);
    const hasSetupRef = useRef(false);
    const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);

    const setCurrentHead = (position: string) => {
        currentHeadRef.current = position;
        // optional: immediately send
        sendHeadPosition(position);
    };


    useEffect(() => {
        let isCurrentConnection = true;

        const connect = () => {
            if (!isCurrentConnection) return;

            const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws';
            const host = API_CONFIG.GAME_SERVER_HOST;
            const port = API_CONFIG.GAME_SERVER_PORT;

            const wsUrl = `${protocol}://${host}${protocol === 'ws' ? `:${port}` : ''}/ws`;

            console.log('[Game] Connecting to:', wsUrl);

            try {
                gameSocketRef.current = new WebSocket(wsUrl);

                gameSocketRef.current.onopen = () => {
                    if (!isCurrentConnection) {
                        gameSocketRef.current?.close();
                        return;
                    }

                    console.log('[Game] Connected to Python game server');
                    onStatusChange('Connected to game server!');

                    if (!hasSetupRef.current) {
                        const setupMsg = { action: 'setup', target: playerName };
                        gameSocketRef.current?.send(JSON.stringify(setupMsg));
                        console.log('[Game] Sent setup signal');
                        hasSetupRef.current = true;
                    }
                };

                gameSocketRef.current.onmessage = (event: MessageEvent) => {
                    const data = JSON.parse(event.data);
                    console.log('[Game] Received:', data);

                    if (data.action === 'id_registered') {
                        console.log(`[Game] Player registered: ${data.player}`);
                        setPlayerId(data.player);
                        onStatusChange(`Registered as Player ${data.player}. Waiting in lobby...`);
                    }

                    if (data.action === 'lobby_status') {
                        setLobbyStatus(data.target);
                        const { ready_count, total_count, min_players } = data.target;
                        onStatusChange(
                            `Lobby: ${ready_count}/${total_count} ready (min: ${min_players})`
                        );
                    }

                    if (data.action === 'restart_status') {
                        setRestartStatus(data.target);
                        const { restart_count, total_count } = data.target;
                        onStatusChange(
                            `Restart: ${restart_count}/${total_count} want to play again`
                        );
                    }

                    if (['mafia', 'doctor', 'civilian'].includes(data.action)) {
                        setRole(data.action);
                        setGameOverData(null); // Reset game over data when new game starts
                        setRestartStatus(null);
                        console.log(`[Game] Role: ${data.action}`);
                        onStatusChange(`You are ${data.player} - Role: ${data.action.toUpperCase()}`);
                    }

                    if (data.action === 'game_over') {
                        setGameOverData(data.target);
                        const winner = data.target.winner === 'mafia' ? 'MAFIA' : 'CIVILIANS';
                        onStatusChange(`GAME OVER! ${winner} WIN!`);
                    }

                    if (data.action === 'game_state') {
                        setGameStage(data.target.state);
                        console.log('[Game] Game stage:', data.target.state);
                    }

                    if (data.action === 'night_result') {
                        console.log('[Game] Night result:', data.target);
                    }

                    if (data.action === 'vote_result') {
                        console.log('[Game] Vote result:', data.target);
                    }

                    if (data.action == 'heads_down') {
                        sendHeadPosition(currentHeadRef.current);
                    }
                };

                gameSocketRef.current.onerror = (error: Event) => {
                    console.error('[Game] WebSocket error:', error);
                    onStatusChange('Error: Failed to connect to game server');
                };

                gameSocketRef.current.onclose = () => {
                    console.log('[Game] Disconnected from game server');
                    gameSocketRef.current = null;
                    onStatusChange('Disconnected from game server');

                    if (isCurrentConnection) {
                        reconnectTimeoutRef.current = setTimeout(() => {
                            console.log('[Game] Attempting to reconnect...');
                            connect();
                        }, 2000);
                    }
                };
            } catch (error) {
                console.error('[Game] Failed to connect:', error);
                const errorMessage = error instanceof Error ? error.message : 'Unknown error';
                onStatusChange(`Error connecting to game server: ${errorMessage}`);
            }
        };

        connect();

        return () => {
            console.log('[Game] Cleaning up connection');
            isCurrentConnection = false;

            if (reconnectTimeoutRef.current) {
                clearTimeout(reconnectTimeoutRef.current);
            }

            if (gameSocketRef.current?.readyState === WebSocket.OPEN) {
                gameSocketRef.current.close();
            }
            gameSocketRef.current = null;
        };
    }, [onStatusChange, playerName]);

    const sendHeadPosition = (position: string) => {
        if (gameSocketRef.current?.readyState === WebSocket.OPEN) {
            gameSocketRef.current.send(JSON.stringify({
                action: position,
                target: null
            }));
            console.log('[Game] Sent head position:', position);
        }
    };

    const sendVoiceCommand = (code: number) => {
        if (gameSocketRef.current?.readyState === WebSocket.OPEN) {
            gameSocketRef.current.send(JSON.stringify({
                action: 'voiceCommand',
                target: code
            }));
            console.log('[Game] Sent voice command code:', code);
        }
    };

    const sendReady = () => {
        if (gameSocketRef.current?.readyState === WebSocket.OPEN) {
            gameSocketRef.current.send(JSON.stringify({
                action: 'ready',
                target: null
            }));
            console.log('[Game] Sent ready signal');
        }
    };

    const sendRestart = () => {
        if (gameSocketRef.current?.readyState === WebSocket.OPEN) {
            gameSocketRef.current.send(JSON.stringify({
                action: 'restart',
                target: null
            }));
            console.log('[Game] Sent restart signal');
        }
    };

    return {
        role,
        playerId,
        lobbyStatus,
        restartStatus,
        gameOverData,
        gameStage,
        sendHeadPosition,
        setCurrentHead,
        sendVoiceCommand,
        sendReady,
        sendRestart
    };
};
