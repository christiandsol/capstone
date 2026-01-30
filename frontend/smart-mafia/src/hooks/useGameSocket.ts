import { useEffect, useRef, useState } from 'react';
import { API_CONFIG } from '../config/api.config';

interface UseGameSocketReturn {
    role: string | null;
    sendHeadPosition: (position: string) => void;
    sendVoiceCommand: (command: number) => void;
}

export const useGameSocket = (
    onStatusChange: (status: string) => void,
    playerName: string
): UseGameSocketReturn => {
    const gameSocketRef = useRef<WebSocket | null>(null);
    const [role, setRole] = useState<string | null>(null);
    const hasSetupRef = useRef(false);
    const reconnectTimeoutRef = useRef<NodeJS.Timeout>(null);

    useEffect(() => {
        let isCurrentConnection = true;

        const connect = () => {
            if (!isCurrentConnection) return;

            const wsUrl = `ws://${API_CONFIG.GAME_SERVER_HOST}:${API_CONFIG.GAME_SERVER_PORT}`;
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

                    if (data.action === 'player_registered') {
                        console.log(`[Game] Player registered: ${data.player}`);
                        onStatusChange(`Registered as ${data.player}. Waiting for role...`);
                    }

                    if (['mafia', 'doctor', 'civilian'].includes(data.action)) {
                        setRole(data.action);
                        console.log(`[Game] Role: ${data.action}`);
                        onStatusChange(`You are ${data.player} - Role: ${data.action.toUpperCase()}`);
                    }

                    if (data.action === 'night_result') {
                        console.log('[Game] Night result:', data.target);
                    }

                    if (data.action === 'vote_result') {
                        console.log('[Game] Vote result:', data.target);
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

    const sendVoiceCommand = (command: number) => {
        if (gameSocketRef.current?.readyState === WebSocket.OPEN) {
            gameSocketRef.current.send(JSON.stringify({
                action: 'targeted',
                target: command
            }));
            console.log('[Game] Sent voice command:', command);
        }
    };

    return { role, sendHeadPosition, sendVoiceCommand };
};
