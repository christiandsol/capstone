import { useEffect, useRef, useState } from 'react';
import io, { Socket } from 'socket.io-client';
import { API_CONFIG } from '../config/api.config';

interface RemoteStreamWithInfo {
    stream: MediaStream;
    playerName?: string;
    playerId?: number;
    socketId: string;
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
    const socketToStreamRef = useRef<{ [socketId: string]: MediaStream }>({});

    useEffect(() => {
        if (!localStream) return;

        console.log('[WebRTC] Connecting to Socket.IO:', API_CONFIG.SOCKET_IO_URL || 'Nginx proxy');
        socketRef.current = io(API_CONFIG.SOCKET_IO_URL);

        socketRef.current.on('connect', () => {
            console.log('[WebRTC] Connected to signaling server, socket ID:', socketRef.current?.id);
            socketRef.current?.emit('join-room', 'test-room');
            onStatusChange('Connected to video server!');
        });

        socketRef.current.on('connect_error', (error: Error) => {
            console.error('[WebRTC] Connection error:', error);
            onStatusChange('Error: Cannot connect to video server');
        });

        const createPeer = (otherId: string, isInitiator: boolean): RTCPeerConnection => {
            console.log(`[Peer] Creating peer connection for ${otherId} (initiator: ${isInitiator})`);

            if (peerRefs.current[otherId]) {
                console.log(`[Peer] Peer connection already exists for ${otherId}`);
                return peerRefs.current[otherId];
            }

            const peer = new RTCPeerConnection({
                iceServers: [
                    { urls: 'stun:stun.l.google.com:19302' },
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

            // Add local tracks
            localStream.getTracks().forEach((track: MediaStreamTrack) => {
                console.log(`[Peer] Adding ${track.kind} track to peer ${otherId}`);
                peer.addTrack(track, localStream);
            });

            // Handle incoming tracks
            peer.ontrack = (event: RTCTrackEvent) => {
                console.log(`[Peer] Received remote ${event.track.kind} track from ${otherId}`);
                const remoteStream = event.streams[0];

                if (!remoteStream) {
                    console.warn(`[Peer] No stream associated with track from ${otherId}`);
                    return;
                }

                // Store the mapping of socket ID to stream
                socketToStreamRef.current[otherId] = remoteStream;

                const playerInfo = playerInfoMapRef.current[otherId];

                setRemoteStreams((prev) => {
                    // Check if we already have this stream
                    const existing = prev.find((s) => s.socketId === otherId);

                    if (existing) {
                        console.log(`[Peer] Stream from ${otherId} already exists, updating info`);
                        return prev.map((s) =>
                            s.socketId === otherId
                                ? { ...s, playerName: playerInfo?.name, playerId: playerInfo?.id }
                                : s
                        );
                    }

                    const updated = [
                        ...prev,
                        {
                            stream: remoteStream,
                            socketId: otherId,
                            playerName: playerInfo?.name,
                            playerId: playerInfo?.id,
                        },
                    ];
                    console.log(`[Peer] Added remote stream from ${otherId}. Total streams: ${updated.length}`);
                    return updated;
                });
            };

            peer.onicecandidate = (e: RTCPeerConnectionIceEvent) => {
                if (e.candidate) {
                    console.log(`[ICE] Sending ICE candidate to ${otherId}`);
                    socketRef.current?.emit('signal', { to: otherId, data: e.candidate });
                }
            };

            peer.onconnectionstatechange = () => {
                console.log(`[Peer] Connection state with ${otherId}: ${peer.connectionState}`);

                if (peer.connectionState === 'failed' || peer.connectionState === 'disconnected') {
                    console.log(`[Peer] Connection failed/disconnected with ${otherId}, will attempt to reconnect`);
                }
            };

            peerRefs.current[otherId] = peer;
            return peer;
        };

        const removeRemoteStreamsForSocketId = (socketId: string) => {
            console.log(`[Cleanup] Removing streams for socket: ${socketId}`);

            setRemoteStreams((prev) => {
                const next = prev.filter((streamInfo) => {
                    if (streamInfo.socketId === socketId) {
                        console.log(`[Cleanup] Removing stream from ${socketId}`);
                        streamInfo.stream.getTracks().forEach((track) => {
                            console.log(`[Cleanup] Stopping ${track.kind} track`);
                            track.stop();
                        });
                        delete socketToStreamRef.current[socketId];
                        return false;
                    }
                    return true;
                });

                console.log(`[Cleanup] Streams remaining: ${next.length}`);
                return next;
            });
        };

        const closePeerConnection = (socketId: string) => {
            console.log(`[Cleanup] Closing peer connection for socket: ${socketId}`);
            const peer = peerRefs.current[socketId];
            if (peer) {
                peer.close();
                delete peerRefs.current[socketId];
            }
            delete playerInfoMapRef.current[socketId];
        };

        // Listen for user joined
        socketRef.current.on('user-joined', async (id: string) => {
            console.log(`[Signal] User joined: ${id}`);

            try {
                const peer = createPeer(id, true);
                const offer = await peer.createOffer();
                await peer.setLocalDescription(offer);
                console.log(`[Signal] Sending offer to ${id}`);
                socketRef.current?.emit('signal', { to: id, data: offer });
            } catch (error) {
                console.error('[Signal] Error creating offer:', error);
            }
        });

        // Listen for player info (direct message)
        socketRef.current.on('player-info', (data: { from?: string; name: string; id: number }) => {
            const socketId = data.from;
            if (!socketId) return;

            console.log(`[Info] Received player info: ${data.name} (ID: ${data.id}) from ${socketId}`);
            playerInfoMapRef.current[socketId] = { name: data.name, id: data.id };

            // Update any existing streams for this socket
            setRemoteStreams((prev) => {
                return prev.map((streamInfo) => {
                    if (streamInfo.socketId === socketId) {
                        return {
                            ...streamInfo,
                            playerName: data.name,
                            playerId: data.id,
                        };
                    }
                    return streamInfo;
                });
            });
        });

        // Listen for broadcast player info
        socketRef.current.on('broadcast-player-info', (data: { socketId: string; name: string; id: number }) => {
            console.log(`[Info] Received broadcast player info: ${data.name} (ID: ${data.id}) from ${data.socketId}`);
            playerInfoMapRef.current[data.socketId] = { name: data.name, id: data.id };

            // Update any existing streams for this socket
            setRemoteStreams((prev) => {
                return prev.map((streamInfo) => {
                    if (streamInfo.socketId === data.socketId) {
                        return {
                            ...streamInfo,
                            playerName: data.name,
                            playerId: data.id,
                        };
                    }
                    return streamInfo;
                });
            });
        });

        // Listen for user disconnect
        socketRef.current.on('user-disconnected', (socketId: string) => {
            console.log(`[Disconnect] User disconnected: ${socketId}`);
            removeRemoteStreamsForSocketId(socketId);
            closePeerConnection(socketId);
        });

        // Listen for signals
        socketRef.current.on('signal', async ({ from, data }: { from: string; data: any }) => {
            console.log(`[Signal] Received signal from ${from}, type: ${data.type || 'ice-candidate'}`);

            let peer = peerRefs.current[from];
            const isNewPeer = !peer;

            if (!peer) {
                peer = createPeer(from, false);
            }

            try {
                if (data.type === 'offer') {
                    console.log(`[Signal] Processing offer from ${from}`);
                    await peer.setRemoteDescription(new RTCSessionDescription(data));
                    const answer = await peer.createAnswer();
                    await peer.setLocalDescription(answer);
                    console.log(`[Signal] Sending answer to ${from}`);
                    socketRef.current?.emit('signal', { to: from, data: answer });
                } else if (data.type === 'answer') {
                    console.log(`[Signal] Processing answer from ${from}`);
                    await peer.setRemoteDescription(new RTCSessionDescription(data));
                } else if (data.candidate) {
                    console.log(`[Signal] Adding ICE candidate from ${from}`);
                    await peer.addIceCandidate(new RTCIceCandidate(data));
                }
            } catch (error) {
                console.error('[Signal] Error handling signal:', error);
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
