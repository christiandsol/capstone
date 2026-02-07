import { useEffect, useRef, useState } from 'react';
import io, { Socket } from 'socket.io-client';
import { API_CONFIG } from '../config/api.config';

interface RemoteStreamWithInfo {
    stream: MediaStream;
    playerName?: string;
    playerId?: number;
}

interface UseWebRTCReturn {
    remoteStreams: RemoteStreamWithInfo[];
}

export const useWebRTC = (
    localStream: MediaStream | null,
    onStatusChange: (status: string) => void,
    playerName: string,
    playerId: number | null
): UseWebRTCReturn => {
    const socketRef = useRef<Socket | null>(null);
    const peerRefs = useRef<{ [key: string]: RTCPeerConnection }>({});
    const [remoteStreams, setRemoteStreams] = useState<RemoteStreamWithInfo[]>([]);
    const playerInfoMapRef = useRef<{ [socketId: string]: { name: string; id: number } }>({});
    const streamToSocketIdRef = useRef<{ [streamId: string]: string }>({});

    useEffect(() => {
        if (!localStream) return;

        console.log('[WebRTC] Connecting to Socket.IO:', API_CONFIG.SOCKET_IO_URL || 'Nginx proxy');
        socketRef.current = io(API_CONFIG.SOCKET_IO_URL);

        socketRef.current.on('connect', () => {
            console.log('[WebRTC] Connected to signaling server');
            socketRef.current?.emit('join-room', 'test-room');

            // Send player info when connecting
            if (playerId !== null) {
                socketRef.current?.emit('broadcast-player-info', {
                    name: playerName,
                    id: playerId
                });
                console.log(`[WebRTC] Sent player info: ${playerName} (ID: ${playerId})`);
            }

            onStatusChange('Connected to video server!');
        });

        socketRef.current.on('connect_error', (error: Error) => {
            console.error('[WebRTC] Connection error:', error);
            onStatusChange('Error: Cannot connect to video server');
        });

        const createPeer = (otherId: string): RTCPeerConnection => {
            console.log(`Creating peer connection for ${otherId}`);
            const peer = new RTCPeerConnection({
                iceServers: [{ urls: 'stun:stun.l.google.com:19302' },
                {
                    urls: "stun:stun.relay.metered.ca:80",
                },
                {
                    urls: "turn:global.relay.metered.ca:80",
                    username: "a295d4459b9a0d892de6c1e1",
                    credential: "th2z+Q12WSG6RIbU",
                },
                {
                    urls: "turn:global.relay.metered.ca:80?transport=tcp",
                    username: "a295d4459b9a0d892de6c1e1",
                    credential: "th2z+Q12WSG6RIbU",
                },
                {
                    urls: "turn:global.relay.metered.ca:443",
                    username: "a295d4459b9a0d892de6c1e1",
                    credential: "th2z+Q12WSG6RIbU",
                },
                {
                    urls: "turns:global.relay.metered.ca:443?transport=tcp",
                    username: "a295d4459b9a0d892de6c1e1",
                    credential: "th2z+Q12WSG6RIbU",
                },
                ],

            });

            localStream.getTracks().forEach((track: MediaStreamTrack) => {
                console.log(`Adding ${track.kind} track to peer ${otherId}`);
                peer.addTrack(track, localStream);
            });

            peer.ontrack = (event: RTCTrackEvent) => {
                console.log(`Received remote track from ${otherId}`);
                const remoteStream = event.streams[0];
                const playerInfo = playerInfoMapRef.current[otherId];

                // Store mapping of stream ID to socket ID
                streamToSocketIdRef.current[remoteStream.id] = otherId;

                setRemoteStreams((prev) => {
                    if (prev.some((s) => s.stream.id === remoteStream.id)) return prev;
                    const updated = [...prev, {
                        stream: remoteStream,
                        playerName: playerInfo?.name,
                        playerId: playerInfo?.id
                    }];
                    console.log(`[DEBUG] Added remote stream from ${otherId}. Total streams: ${updated.length}`);
                    return updated;
                });
            };

            peer.onicecandidate = (e: RTCPeerConnectionIceEvent) => {
                if (e.candidate) {
                    socketRef.current?.emit('signal', { to: otherId, data: e.candidate });
                }
            };

            peer.onconnectionstatechange = () => {
                console.log(`Peer ${otherId} state: ${peer.connectionState}`);
            };

            peerRefs.current[otherId] = peer;
            return peer;
        };

        const removeRemoteStreamsForSocketId = (socketId: string) => {
            console.log(`[DEBUG] Attempting to remove streams for socket: ${socketId}`);

            setRemoteStreams((prev) => {
                console.log(`[DEBUG] Before removal - Total streams: ${prev.length}`);

                const next = prev.filter((streamInfo) => {
                    const streamSocketId = streamToSocketIdRef.current[streamInfo.stream.id];

                    if (streamSocketId === socketId) {
                        console.log(`[DEBUG] Removing stream ${streamInfo.stream.id} (socket: ${socketId})`);
                        // Stop all tracks in this stream
                        streamInfo.stream.getTracks().forEach((track) => {
                            console.log(`[DEBUG] Stopping ${track.kind} track`);
                            track.stop();
                        });
                        delete streamToSocketIdRef.current[streamInfo.stream.id];
                        return false;
                    }
                    return true;
                });

                console.log(`[DEBUG] After removal - Total streams: ${next.length}`);
                return next;
            });
        };

        const closePeerConnection = (socketId: string) => {
            console.log(`[DEBUG] Closing peer connection for socket: ${socketId}`);
            const peer = peerRefs.current[socketId];
            if (peer) {
                peer.close();
                delete peerRefs.current[socketId];
                console.log(`[DEBUG] Peer connection closed and removed`);
            }
            delete playerInfoMapRef.current[socketId];
        };

        socketRef.current.on('user-joined', async (id: string) => {
            console.log(`User joined: ${id}`);

            // Send player info to the new peer
            if (playerId !== null) {
                socketRef.current?.emit('player-info', {
                    to: id,
                    name: playerName,
                    id: playerId
                });
            }

            try {
                const peer = createPeer(id);
                const offer = await peer.createOffer();
                await peer.setLocalDescription(offer);
                socketRef.current?.emit('signal', { to: id, data: offer });
            } catch (error) {
                console.error('Error creating offer:', error);
            }
        });

        // Listen for player info from others
        socketRef.current.on('player-info', (data: { from?: string; name: string; id: number }) => {
            const socketId = data.from;
            if (socketId) {
                playerInfoMapRef.current[socketId] = { name: data.name, id: data.id };
                console.log(`[WebRTC] Received player info: ${data.name} (ID: ${data.id}) from ${socketId}`);

                // Update existing streams that match this socket ID
                setRemoteStreams((prev) => {
                    return prev.map((streamInfo) => {
                        const streamSocketId = streamToSocketIdRef.current[streamInfo.stream.id];
                        if (streamSocketId === socketId && !streamInfo.playerName) {
                            return { ...streamInfo, playerName: data.name, playerId: data.id };
                        }
                        return streamInfo;
                    });
                });
            }
        });

        // Listen for broadcast player info
        socketRef.current.on('broadcast-player-info', (data: { socketId: string; name: string; id: number }) => {
            playerInfoMapRef.current[data.socketId] = { name: data.name, id: data.id };
            console.log(`[WebRTC] Received broadcast player info: ${data.name} (ID: ${data.id}) from ${data.socketId}`);

            // Update existing streams that match this socket ID
            setRemoteStreams((prev) => {
                return prev.map((streamInfo) => {
                    const streamSocketId = streamToSocketIdRef.current[streamInfo.stream.id];
                    if (streamSocketId === data.socketId && !streamInfo.playerName) {
                        return { ...streamInfo, playerName: data.name, playerId: data.id };
                    }
                    return streamInfo;
                });
            });
        });

        // Listen for user disconnect
        socketRef.current.on('user-disconnected', async (socketId: string) => {
            console.log(`[WEBRTC DISCONNECT] Received user-disconnected for socket: ${socketId}`);
            removeRemoteStreamsForSocketId(socketId);
            closePeerConnection(socketId);
        });

        socketRef.current.on('signal', async ({ from, data }: { from: string; data: any }) => {
            console.log(`Signal from ${from}:`, data.type || 'ice-candidate');

            let peer = peerRefs.current[from];
            if (!peer) peer = createPeer(from);

            try {
                if (data.type === 'offer') {
                    await peer.setRemoteDescription(new RTCSessionDescription(data));
                    const answer = await peer.createAnswer();
                    await peer.setLocalDescription(answer);
                    socketRef.current?.emit('signal', { to: from, data: answer });
                } else if (data.type === 'answer') {
                    await peer.setRemoteDescription(new RTCSessionDescription(data));
                } else if (data.candidate) {
                    await peer.addIceCandidate(new RTCIceCandidate(data));
                }
            } catch (error) {
                console.error('Signal handling error:', error);
            }
        });

        return () => {
            console.log('[WebRTC] Cleaning up');
            socketRef.current?.disconnect();
            Object.values(peerRefs.current).forEach((p) => p.close());
        };
    }, [localStream, onStatusChange, playerName, playerId]);

    return { remoteStreams };
};
