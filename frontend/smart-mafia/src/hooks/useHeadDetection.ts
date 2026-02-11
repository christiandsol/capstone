import { useEffect, useRef } from 'react';

declare global {
    interface Window {
        FaceMesh: any;
    }
}

const MEDIAPIPE_VERSION = "0.4.1633559619";

export const useHeadDetection = (
    videoRef: React.RefObject<HTMLVideoElement | null>,
    onHeadPositionChange: (position: string) => void
): void => {
    const lastPositionRef = useRef<string>('unknown');
    const rafIdRef = useRef<number | null>(null);
    const faceMeshRef = useRef<any>(null);
    const scriptLoadedRef = useRef<boolean>(false);

    useEffect(() => {
        const video = videoRef.current;
        if (!video) return;

        let cancelled = false;

        const loadScriptIfNeeded = async () => {
            if (window.FaceMesh) return;
            if (scriptLoadedRef.current) return;

            await new Promise<void>((resolve, reject) => {
                const existing = document.querySelector(
                    `script[src*="@mediapipe/face_mesh@${MEDIAPIPE_VERSION}"]`
                );

                if (existing) {
                    resolve();
                    return;
                }

                const script = document.createElement('script');
                script.src = `https://cdn.jsdelivr.net/npm/@mediapipe/face_mesh@${MEDIAPIPE_VERSION}/face_mesh.js`;
                script.async = true;

                script.onload = () => {
                    scriptLoadedRef.current = true;
                    resolve();
                };

                script.onerror = () => reject(new Error("Failed to load FaceMesh script"));

                document.head.appendChild(script);
            });
        };

        const waitForVideoToPlay = async () => {
            if (video.paused) {
                try {
                    await video.play();
                } catch {
                    // autoplay may fail until user gesture
                }
            }

            if (video.videoWidth === 0 || video.videoHeight === 0) {
                await new Promise<void>((resolve) => {
                    video.addEventListener('playing', () => resolve(), { once: true });
                });
            }
        };

        const startDetection = async () => {
            try {
                await loadScriptIfNeeded();
                await waitForVideoToPlay();

                if (cancelled) return;

                const faceMesh = new window.FaceMesh({
                    locateFile: (file: string) =>
                        `https://cdn.jsdelivr.net/npm/@mediapipe/face_mesh@${MEDIAPIPE_VERSION}/${file}`,
                });

                faceMesh.setOptions({
                    maxNumFaces: 1,
                    refineLandmarks: true,
                    minDetectionConfidence: 0.5,
                    minTrackingConfidence: 0.5,
                });

                faceMesh.onResults((results: any) => {
                    if (!results.multiFaceLandmarks?.length) return;

                    const landmarks = results.multiFaceLandmarks[0];

                    const NOSE = 1;
                    const CHIN = 152;
                    const FOREHEAD = 10;

                    const nose = landmarks[NOSE];
                    const chin = landmarks[CHIN];
                    const forehead = landmarks[FOREHEAD];

                    const headHeight = chin.y - forehead.y;
                    const noseRelative = nose.y - forehead.y;

                    const newPosition =
                        noseRelative < headHeight * 0.666 ? 'headUp' : 'headDown';

                    if (newPosition !== lastPositionRef.current) {
                        lastPositionRef.current = newPosition;
                        onHeadPositionChange(newPosition);
                    }
                });

                faceMeshRef.current = faceMesh;

                const detectFrame = async () => {
                    if (cancelled) return;

                    await faceMesh.send({ image: video });
                    rafIdRef.current = requestAnimationFrame(detectFrame);
                };

                detectFrame();
            } catch (err) {
                console.error("FaceMesh initialization failed:", err);
            }
        };

        startDetection();

        return () => {
            cancelled = true;

            if (rafIdRef.current) {
                cancelAnimationFrame(rafIdRef.current);
            }

            if (faceMeshRef.current?.close) {
                faceMeshRef.current.close();
            }
        };
    }, [videoRef, onHeadPositionChange]);
};

