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
    const processingRef = useRef<boolean>(false);

    useEffect(() => {
        const video = videoRef.current;
        if (!video) {
            console.log("[Detection] No video ref provided");
            return;
        }

        let cancelled = false;

        const loadScriptIfNeeded = async () => {
            if (window.FaceMesh) {
                console.log("[FaceMesh] Already loaded");
                return;
            }
            if (scriptLoadedRef.current) {
                console.log("[FaceMesh] Already loading");
                return;
            }

            console.log("[FaceMesh] Loading script...");

            await new Promise<void>((resolve, reject) => {
                const existing = document.querySelector(
                    `script[src*="@mediapipe/face_mesh@${MEDIAPIPE_VERSION}"]`
                );

                if (existing) {
                    console.log("[FaceMesh] Script already in DOM");
                    resolve();
                    return;
                }

                const script = document.createElement('script');
                script.src = `https://cdn.jsdelivr.net/npm/@mediapipe/face_mesh@${MEDIAPIPE_VERSION}/face_mesh.js`;
                script.async = true;

                script.onload = () => {
                    scriptLoadedRef.current = true;
                    console.log("[FaceMesh] Script loaded successfully");
                    resolve();
                };

                script.onerror = () => {
                    console.error("[FaceMesh] Failed to load script");
                    reject(new Error("Failed to load FaceMesh script"));
                };

                document.head.appendChild(script);
            });
        };

        const waitForVideoToPlay = async () => {
            // Don't request camera - video should already have a stream from useMediaStream

            if (video.paused) {
                try {
                    await video.play();
                    console.log("[Detection] Video playing");
                } catch (err) {
                    console.error("[Detection] Failed to play video:", err);
                    // Don't throw - video might already be playing
                }
            }

            // Wait for video dimensions to be available
            if (video.videoWidth === 0 || video.videoHeight === 0) {
                console.log("[Detection] Waiting for video dimensions...");
                await new Promise<void>((resolve) => {
                    const checkDimensions = () => {
                        if (video.videoWidth > 0 && video.videoHeight > 0) {
                            console.log(`[Detection] Video dimensions: ${video.videoWidth}x${video.videoHeight}`);
                            resolve();
                        } else {
                            setTimeout(checkDimensions, 100);
                        }
                    };
                    checkDimensions();
                });
            }
        };

        const startDetection = async () => {
            try {
                console.log("[Detection] Starting...");

                await loadScriptIfNeeded();
                await waitForVideoToPlay();

                if (cancelled) {
                    console.log("[Detection] Cancelled during setup");
                    return;
                }

                console.log("[Detection] Initializing FaceMesh...");

                const faceMesh = new window.FaceMesh({
                    locateFile: (file: string) => {
                        const url = `https://cdn.jsdelivr.net/npm/@mediapipe/face_mesh@${MEDIAPIPE_VERSION}/${file}`;
                        return url;
                    },
                });

                faceMesh.setOptions({
                    maxNumFaces: 1,
                    refineLandmarks: true,
                    minDetectionConfidence: 0.5,
                    minTrackingConfidence: 0.5,
                });

                faceMesh.onResults((results: any) => {
                    processingRef.current = false;

                    if (!results.multiFaceLandmarks?.length) {
                        return;
                    }

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
                        console.log(`[Head] Position changed: ${newPosition}`);
                        onHeadPositionChange(newPosition);
                    }
                });

                faceMeshRef.current = faceMesh;
                console.log("[Detection] FaceMesh initialized successfully");

                const detectFrame = async () => {
                    if (cancelled) return;

                    // Only process if the previous frame has finished
                    if (processingRef.current) {
                        rafIdRef.current = requestAnimationFrame(detectFrame);
                        return;
                    }

                    processingRef.current = true;

                    try {
                        await faceMesh.send({ image: video });
                    } catch (err) {
                        console.error("[Detection] Error processing frame:", err);
                        processingRef.current = false;
                    }

                    rafIdRef.current = requestAnimationFrame(detectFrame);
                };

                detectFrame();
                console.log("[Detection] Frame detection loop started");
            } catch (err) {
                console.error("[Detection] Initialization failed:", err);
            }
        };

        startDetection();

        return () => {
            console.log("[Detection] Cleaning up...");
            cancelled = true;

            if (rafIdRef.current) {
                cancelAnimationFrame(rafIdRef.current);
            }

            if (faceMeshRef.current?.close) {
                try {
                    faceMeshRef.current.close();
                    console.log("[Detection] FaceMesh closed successfully");
                } catch (err) {
                    console.error("[Detection] Error closing FaceMesh:", err);
                }
            }
        };
    }, [videoRef, onHeadPositionChange]);
};
