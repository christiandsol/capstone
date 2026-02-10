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
    sendHeadPosition: (position: string) => void;
    setCurrentHead: (position: string) => void;
    sendVoiceCommand: (command: number) => void;
    sendReady: () => void;
    sendRestart: () => void;
}

type NotifyFunction = (message: string, duration?: number) => string;

export const useGameSocket = (
    onStatusChange: (status: string) => void,
    playerName: string,
    notify?: NotifyFunction,
): UseGameSocketReturn => {
    const gameSocketRef = useRef<WebSocket | null>(null);
    const currentHeadRef = useRef<string>('headDown');
    const [role, setRole] = useState<string | null>(null);
    const [playerId, setPlayerId] = useState<number | null>(null);
    const [lobbyStatus, setLobbyStatus] = useState<LobbyStatus | null>(null);
    const [restartStatus, setRestartStatus] = useState<RestartStatus | null>(null);
    const [gameOverData, setGameOverData] = useState<GameOverData | null>(null);
    const hasSetupRef = useRef(false);
    const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
    const lastStatusRef = useRef<string>('');

    const setCurrentHead = (position: string) => {
        currentHeadRef.current = position;
        sendHeadPosition(position);
    };

    useEffect(() => {
        let isCurrentConnection = true;

        const connect = () => {
            if (!isCurrentConnection) return;

            //const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws'
            const protocol = 'ws';
            const host = API_CONFIG.GAME_SERVER_HOST;
            const port = API_CONFIG.GAME_SERVER_PORT;

            const wsUrl = `${protocol}://${host}:${port}`;

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
                        lastStatusRef.current = `Registered as Player ${data.player}. Waiting in lobby...`;
                        onStatusChange(lastStatusRef.current);
                    }

                    if (data.action === 'lobby_status') {
                        setLobbyStatus(data.target);
                        if (gameOverData) {
                            setGameOverData(null);
                            setRestartStatus(null);
                            setRole(null);
                        }
                        const { ready_count, total_count, min_players } = data.target;
                        // Only update status if we're still in lobby waiting for players
                        if (ready_count < total_count) {
                            const newStatus = `Lobby: ${ready_count}/${total_count} ready (min: ${min_players})`;
                            lastStatusRef.current = newStatus;
                            onStatusChange(newStatus);
                        }
                    }

                    if (data.action === 'restart_status') {
                        setRestartStatus(data.target);
                        const { restart_count, total_count } = data.target;
                        const newStatus = `Restart: ${restart_count}/${total_count} want to play again`;
                        lastStatusRef.current = newStatus;
                        onStatusChange(newStatus);

                        if (restart_count === total_count && total_count > 0) {
                            console.log('[Game] All players agreed to restart!');
                            setGameOverData(null);
                            setRole(null);
                        }
                    }

                    if (data.action === 'disconnect') {
                        const disconnectedPlayer = data.target;
                        console.log(`[Game] Player disconnected: ${disconnectedPlayer}`);
                        // Show notification if notify function is provided
                        if (notify) {
                            notify(`${disconnectedPlayer} disconnected`, 5000);
                        }
                    }

                    if (['mafia', 'doctor', 'civilian'].includes(data.action)) {
                        setRole(data.action);
                        setGameOverData(null);
                        setRestartStatus(null);
                        console.log(`[Game] Role: ${data.action}`);
                        const newStatus = `You are ${data.player} - Role: ${data.action.toUpperCase()}`;
                        lastStatusRef.current = newStatus;
                        onStatusChange(newStatus);
                    }

                    if (data.action === 'heads_down') {
                        console.log("[DEBUG] Moving on to night phase, everyone put head down please")
                        const newStatus = "Moving on to night phase, everyone put head down please";
                        lastStatusRef.current = newStatus;
                        onStatusChange(newStatus);
                    }

                    if (data.action === 'game_over') {
                        setGameOverData(data.target);
                        const game_winner = data.target.winner
                        let phrase: string = "";
                        if (game_winner === "mafia") {
                            phrase = 'THE MAFIA';
                        } else if (game_winner == "no_one") {
                            phrase = "NO ONE"
                        } else {
                            phrase = "THE CIVILIANS"
                        }
                        const newStatus = `GAME OVER! ${phrase} WON!`;
                        lastStatusRef.current = newStatus;
                        onStatusChange(newStatus);
                    }

                    if (data.action === 'night_result') {
                        console.log('[Game] Night result:', data.target);
                        const killed = data.target.killed
                        const saved = data.target.saved
                        let newStatus = "";
                        if (killed != saved) {
                            newStatus = `Mafia killed ${killed} in the night, and no one was there to save them, everyone discuss and say "ready to vote" when you are`
                        } else {
                            newStatus = `Mafia killed ${killed} in the night, and they were SAVED, everyone discuss and say "ready to vote" when you are`
                        }
                        lastStatusRef.current = newStatus;
                        onStatusChange(newStatus);
                    }

                    if (data.action === 'vote_result') {
                        const vote_result = data.target
                        const newStatus = `${vote_result} was voted out`;
                        lastStatusRef.current = newStatus;
                        onStatusChange(newStatus);
                        console.log('[Game] Vote result:', data.target);
                    }

                    if (data.action === 'vote_result_tie') {
                        const vote_result = data.target
                        const newStatus = `Vote result was a tie between ${vote_result}, vote again`;
                        lastStatusRef.current = newStatus;
                        onStatusChange(newStatus);
                        console.log('[Game] Vote result was a tie, vote again:', data.target);
                    }

                    if (data.action === 'day_phase') {
                        console.log('[Game] Day phase started - voting is active');
                        const newStatus = 'Day Phase: Time to vote!';
                        lastStatusRef.current = newStatus;
                        onStatusChange(newStatus);
                    }

                    if (data.action === 'mafia_kill') {
                        const target = data.target;
                        console.log(`[Game] Mafia killed ${target}`);
                        const newStatus = `Doctor, your turn to vote, everyone heads down`;
                        lastStatusRef.current = newStatus;
                        onStatusChange(newStatus);
                    }

                    if (data.action === 'doctor_save') {
                        const target = data.target;
                        console.log(`[Game] Doctor saved ${target}`);
                        const newStatus = `Discussing night results...`;
                        lastStatusRef.current = newStatus;
                        onStatusChange(newStatus);
                    }

                    if (data.action === 'night_phase_kill') {
                        console.log('[Game] Night phase started');
                        const newStatus = 'Night Phase: Mafia is acting... Everyone else heads down';
                        lastStatusRef.current = newStatus;
                        onStatusChange(newStatus);
                    }

                    if (data.action == 'heads_down') {
                        sendHeadPosition(currentHeadRef.current);
                    }
                };

                gameSocketRef.current.onerror = (error: Event) => {
                    console.error('[Game] WebSocket error:', error);
                    const newStatus = 'Error: Failed to connect to game server';
                    lastStatusRef.current = newStatus;
                    onStatusChange(newStatus);
                };

                gameSocketRef.current.onclose = () => {
                    console.log('[Game] Disconnected from game server');
                    gameSocketRef.current = null;
                    const newStatus = 'Disconnected from game server';
                    lastStatusRef.current = newStatus;
                    onStatusChange(newStatus);

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
                const newStatus = `Error connecting to game server: ${errorMessage}`;
                lastStatusRef.current = newStatus;
                onStatusChange(newStatus);
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

    const sendVoiceCommand = (command: number) => {
        if (gameSocketRef.current?.readyState === WebSocket.OPEN) {
            gameSocketRef.current.send(JSON.stringify({
                action: 'control',
                target: command
            }));
            console.log('[Game] Sent voice command:', command);
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
        sendHeadPosition,
        setCurrentHead,
        sendVoiceCommand,
        sendReady,
        sendRestart
    };
};
