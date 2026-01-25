import { useRef, useState } from 'react';

interface UseMediaStreamReturn {
    localVideoRef: React.RefObject<HTMLVideoElement>;
    localStream: MediaStream | null;
    startCamera: () => Promise<void>;
    startTestVideo: () => Promise<void>;
}

export const useMediaStream = (
    onStatusChange: (status: string) => void
): UseMediaStreamReturn => {
    const localVideoRef = useRef<HTMLVideoElement>(null);
    const [localStream, setLocalStream] = useState<MediaStream | null>(null);
    const canvasRef = useRef<HTMLCanvasElement | null>(null);
    const animationFrameRef = useRef<number | null>(null);

    const startCamera = async (): Promise<void> => {
        onStatusChange('Requesting camera access...');

        try {
            const stream = await navigator.mediaDevices.getUserMedia({
                video: { width: 640, height: 480 },
                audio: false
            });

            console.log('Camera stream obtained:', stream.getTracks());

            if (localVideoRef.current) {
                localVideoRef.current.srcObject = stream;
            }
            setLocalStream(stream);
            onStatusChange('Camera connected!');
        } catch (error) {
            if (error instanceof Error) {
                if (error.name === 'NotAllowedError') {
                    onStatusChange('Error: Camera access denied');
                } else if (error.name === 'NotFoundError') {
                    onStatusChange('Error: No camera found');
                } else {
                    onStatusChange(`Error: ${error.message}`);
                }
            }
            throw error;
        }
    };

    const startTestVideo = async (): Promise<void> => {
        const getTabVideo = (): string => {
            const existing = sessionStorage.getItem('tabVideo');
            if (existing) return existing;

            const videoFile = Math.random() < 0.5 ? '/vid1.mp4' : '/vid2.mp4';
            sessionStorage.setItem('tabVideo', videoFile);
            return videoFile;
        };

        const videoFile = getTabVideo();
        onStatusChange(`Loading ${videoFile}...`);

        const video = document.createElement('video');
        video.src = videoFile;
        video.loop = true;
        video.muted = true;
        video.playsInline = true;
        video.style.display = 'none';
        document.body.appendChild(video);

        await new Promise<void>((resolve, reject) => {
            video.onloadedmetadata = () => resolve();
            video.onerror = () => reject(new Error(`Failed to load ${videoFile}`));
            setTimeout(() => reject(new Error('Video load timeout')), 10000);
        });

        onStatusChange('Playing video...');
        await video.play();

        onStatusChange('Setting up canvas capture...');

        const canvas = document.createElement('canvas');
        canvas.width = 640;
        canvas.height = 480;
        canvasRef.current = canvas;

        const ctx = canvas.getContext('2d');

        const drawFrame = (): void => {
            if (video.paused || video.ended) return;
            if (ctx) {
                ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
            }
            animationFrameRef.current = requestAnimationFrame(drawFrame);
        };
        drawFrame();

        const stream = canvas.captureStream(30);
        if (localVideoRef.current) {
            localVideoRef.current.srcObject = stream;
        }
        setLocalStream(stream);
        onStatusChange('Test video ready!');
    };

    return { localVideoRef, localStream, startCamera, startTestVideo };
};
