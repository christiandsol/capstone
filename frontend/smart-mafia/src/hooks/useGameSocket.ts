import { useEffect, useRef, useState } from 'react';
import { API_CONFIG } from '../config/api.config';

interface UseGameSocketReturn {
    playerId: number | null;
    role: string | null;
    sendHeadPosition: (position: string) => void;
    sendVoiceCommand: (command: number) => void;
}

export const useGameSocket = (
    onStatusChange: (status: string) => void
): UseGameSocketReturn => {
    const gameSocketRef = useRef<WebSocket | null>(null);
    const [playerId, setPlayerId] = useState<number | null>(null);
    const [role, setRole] = useState<string | null>(null);

    useEffect(() => {
        // if (gameSocketRef.current) return;
        const wsUrl = `ws://${API_CONFIG.GAME_SERVER_HOST}:${API_CONFIG.GAME_SERVER_PORT}`;
        console.log('[Game] Connecting to:', wsUrl);

        try {
            gameSocketRef.current = new WebSocket(wsUrl);

            gameSocketRef.current.onopen = () => {
                console.log('[Game] Connected to Python game server');
                onStatusChange('Connected to game server!');

                const setupMsg = { action: 'setup', target: null };
                gameSocketRef.current?.send(JSON.stringify(setupMsg));
                console.log('[Game] Sent setup signal');
            };

            gameSocketRef.current.onmessage = (event: MessageEvent) => {
                const data = JSON.parse(event.data);
                console.log('[Game] Received:', data);

                if (data.action === 'player_id') {
                    setPlayerId(data.player);
                    console.log(`[Game] Assigned Player ID: ${data.player}`);
                    onStatusChange(`You are Player ${data.player}. Waiting for role assignment...`);
                }

                if (['mafia', 'doctor', 'civilian'].includes(data.action)) {
                    setRole(data.action);
                    console.log(`[Game] Role: ${data.action}`);
                    onStatusChange(`You are Player ${data.player} - Role: ${data.action.toUpperCase()}`);
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
            };
        } catch (error) {
            console.error('[Game] Failed to connect:', error);
            const errorMessage = error instanceof Error ? error.message : 'Unknown error';
            onStatusChange(`Error connecting to game server: ${errorMessage}`);
        }

        return () => {
            gameSocketRef.current?.close();
        };
    }, [onStatusChange]);

    const sendHeadPosition = (position: string) => {
        if (gameSocketRef.current?.readyState === WebSocket.OPEN) {
            gameSocketRef.current.send(JSON.stringify({
                player: playerId,
                action: position,
                target: null
            }));
            console.log('[Game] Sent head position:', position);
        }
    };

    const sendVoiceCommand = (command: number) => {
        if (gameSocketRef.current?.readyState === WebSocket.OPEN) {
            gameSocketRef.current.send(JSON.stringify({
                player: playerId,
                action: 'voice_command',
                target: command
            }));
            console.log('[Game] Sent voice command:', command);
        }
    };

    return { playerId, role, sendHeadPosition, sendVoiceCommand };
};
