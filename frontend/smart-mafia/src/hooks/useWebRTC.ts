import { useEffect, useRef, useState } from 'react';
import io, { Socket } from 'socket.io-client';
import { API_CONFIG } from '../config/api.config';

interface UseWebRTCReturn {
    remoteStreams: MediaStream[];
}

export const useWebRTC = (
    localStream: MediaStream | null,
    onStatusChange: (status: string) => void
): UseWebRTCReturn => {
    const socketRef = useRef<Socket | null>(null);
    const peerRefs = useRef<{ [key: string]: RTCPeerConnection }>({});
    const [remoteStreams, setRemoteStreams] = useState<MediaStream[]>([]);

    useEffect(() => {
        if (!localStream) return;

        console.log('[WebRTC] Connecting to Socket.IO:', API_CONFIG.SOCKET_IO_URL || 'Nginx proxy');
        socketRef.current = io(API_CONFIG.SOCKET_IO_URL);

        socketRef.current.on('connect', () => {
            console.log('[WebRTC] Connected to signaling server');
            socketRef.current?.emit('join-room', 'test-room');
            onStatusChange('Connected to video server!');
        });

        socketRef.current.on('connect_error', (error: Error) => {
            console.error('[WebRTC] Connection error:', error);
            onStatusChange('Error: Cannot connect to video server');
        });

        const createPeer = (otherId: string): RTCPeerConnection => {
            console.log(`Creating peer connection for ${otherId}`);
            const peer = new RTCPeerConnection({
                iceServers: [{ urls: 'stun:stun.l.google.com:19302' }],
            });

            localStream.getTracks().forEach((track: MediaStreamTrack) => {
                console.log(`Adding ${track.kind} track to peer ${otherId}`);
                peer.addTrack(track, localStream);
            });

            peer.ontrack = (event: RTCTrackEvent) => {
                console.log(`Received remote track from ${otherId}`);
                const remoteStream = event.streams[0];
                setRemoteStreams((prev) => {
                    if (prev.some((s) => s.id === remoteStream.id)) return prev;
                    return [...prev, remoteStream];
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

        socketRef.current.on('user-joined', async (id: string) => {
            console.log(`User joined: ${id}`);
            try {
                const peer = createPeer(id);
                const offer = await peer.createOffer();
                await peer.setLocalDescription(offer);
                socketRef.current?.emit('signal', { to: id, data: offer });
            } catch (error) {
                console.error('Error creating offer:', error);
            }
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
            socketRef.current?.disconnect();
            Object.values(peerRefs.current).forEach((p) => p.close());
        };
    }, [localStream, onStatusChange]);

    return { remoteStreams };
};
