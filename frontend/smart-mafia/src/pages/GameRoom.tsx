import { useEffect, useRef, useState } from "react";
import io, { Socket } from "socket.io-client";

// Extend Window interface for MediaPipe
declare global {
  interface Window {
    FaceMesh: any;
    webkitSpeechRecognition: any;
    SpeechRecognition: any;
  }
}

function Game() {
  const localVideoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const socketRef = useRef<Socket | null>(null);
  const localStreamRef = useRef<MediaStream | null>(null);
  const peerRefs = useRef<{ [key: string]: RTCPeerConnection }>({});
  const animationFrameRef = useRef<number | null>(null);
  const [remoteStreams, setRemoteStreams] = useState<MediaStream[]>([]);
  const [status, setStatus] = useState<string>("Click 'Start' to begin");
  const [isStarted, setIsStarted] = useState<boolean>(false);
  const [useTestVideos, setUseTestVideos] = useState<boolean>(false);
  const [headPosition, setHeadPosition] = useState<string>("unknown");
  const [playerId, setPlayerId] = useState<number | null>(null);
  const [role, setRole] = useState<string | null>(null);
  const gameSocketRef = useRef<WebSocket | null>(null);
  const [isListening, setIsListening] = useState<boolean>(false);
  const recognitionRef = useRef<any>(null);

  const getTabVideo = (): string => {
    const existing = sessionStorage.getItem("tabVideo");
    if (existing) return existing;

    const videoFile = Math.random() < 0.5 ? "/vid1.mp4" : "/vid2.mp4";
    sessionStorage.setItem("tabVideo", videoFile);
    console.log("Selected test video:", videoFile);
    return videoFile;
  };

  const startStream = async (): Promise<void> => {
    try {
      if (useTestVideos) {
        await startTestVideoStream();
      } else {
        await startRealCameraStream();
      }
    } catch (error) {
      console.error("Setup error:", error);
      const errorMessage = error instanceof Error ? error.message : "Unknown error";
      setStatus(`Error: ${errorMessage}`);
    }
  };

  const startRealCameraStream = async (): Promise<void> => {
    setStatus("Requesting camera access...");

    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { width: 640, height: 480 },
        audio: false
      });

      console.log("Camera stream obtained:", stream.getTracks());

      if (localVideoRef.current) {
        localVideoRef.current.srcObject = stream;
      }
      localStreamRef.current = stream;

      setStatus("Camera connected! Connecting to server...");
      setIsStarted(true);

      connectToServer();
      startHeadDetection(localVideoRef.current);

    } catch (error) {
      if (error instanceof Error) {
        if (error.name === "NotAllowedError") {
          setStatus("Error: Camera access denied. Please allow camera access and try again.");
        } else if (error.name === "NotFoundError") {
          setStatus("Error: No camera found. Connect a camera and try again.");
        } else {
          setStatus(`Error: ${error.message}`);
        }
      }
      throw error;
    }
  };

  const startTestVideoStream = async (): Promise<void> => {
    const videoFile = getTabVideo();
    setStatus(`Loading ${videoFile}...`);

    const video = document.createElement("video");
    video.src = videoFile;
    video.loop = true;
    video.muted = true;
    video.playsInline = true;
    video.style.display = "none";
    document.body.appendChild(video);

    await new Promise<void>((resolve, reject) => {
      video.onloadedmetadata = () => resolve();
      video.onerror = () => reject(new Error(`Failed to load ${videoFile}`));
      setTimeout(() => reject(new Error("Video load timeout")), 10000);
    });

    setStatus("Playing video...");
    await video.play();

    setStatus("Setting up canvas capture...");

    const canvas = document.createElement("canvas");
    canvas.width = 640;
    canvas.height = 480;
    canvasRef.current = canvas;

    const ctx = canvas.getContext("2d");

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
    localStreamRef.current = stream;

    setIsStarted(true);
    connectToServer();
  };

  const connectToServer = (): void => {
    setStatus("Connecting to servers...");

    // socketRef.current = io("http://163.192.0.247:3001");
    socketRef.current = io();

    socketRef.current.on("connect", () => {
      console.log("[WebRTC] Connected to signaling server");
      socketRef.current?.emit("join-room", "test-room");
      setStatus("Connected to video server! Connecting to game server...");
    });

    socketRef.current.on("connect_error", (error: Error) => {
      console.error("[WebRTC] Socket connection error:", error);
      setStatus("Error: Cannot connect to video server on port 3001");
    });

    setupSignaling();
    connectToGameServer();
  };

  const connectToGameServer = (): void => {
    // const GAME_SERVER_IP = "163.192.0.247";
    const GAME_SERVER_PORT = 5050;

    try {
      // gameSocketRef.current = new WebSocket(`ws://${GAME_SERVER_IP}:${GAME_SERVER_PORT}`);
      gameSocketRef.current = new WebSocket(`ws://${window.location.hostname}:${GAME_SERVER_PORT}`);


      gameSocketRef.current.onopen = () => {
        console.log("[Game] Connected to Python game server");
        setStatus("Connected to game server!");

        const setupMsg = {
          action: "setup",
          target: null
        };
        gameSocketRef.current?.send(JSON.stringify(setupMsg));
        console.log("[Game] Sent setup signal");
      };

      gameSocketRef.current.onmessage = (event: MessageEvent) => {
        const data = JSON.parse(event.data);
        console.log("[Game] Received:", data);

        if (data.action === "player_id") {
          setPlayerId(data.player);
          console.log(`[Game] Assigned Player ID: ${data.player}`);
          setStatus(`You are Player ${data.player}. Waiting for role assignment...`);
        }

        if (data.action === "mafia" || data.action === "doctor" || data.action === "civilian") {
          setRole(data.action);
          console.log(`[Game] Role: ${data.action}`);
          setStatus(`You are Player ${playerId} - Role: ${data.action.toUpperCase()}`);
        }

        if (data.action === "night_result") {
          console.log("[Game] Night result:", data.target);
        }

        if (data.action === "vote_result") {
          console.log("[Game] Vote result:", data.target);
        }
      };

      gameSocketRef.current.onerror = (error: Event) => {
        console.error("[Game] WebSocket error:", error);
        setStatus("Error: Failed to connect to game server");
      };

      gameSocketRef.current.onclose = () => {
        console.log("[Game] Disconnected from game server");
        setStatus("Disconnected from game server");
      };

    } catch (error) {
      console.error("[Game] Failed to connect:", error);
      const errorMessage = error instanceof Error ? error.message : "Unknown error";
      setStatus(`Error connecting to game server: ${errorMessage}`);
    }
  };

  const sendHeadPositionToServer = (position: string): void => {
    if (gameSocketRef.current && gameSocketRef.current.readyState === WebSocket.OPEN) {
      const msg = {
        player: playerId,
        action: position,
        target: null
      };
      gameSocketRef.current.send(JSON.stringify(msg));
      console.log("[Game] Sent head position:", position);
    } else {
      console.warn("[Game] Cannot send head position - not connected");
    }
  };

  const sendVoiceCommand = (command: number): void => {
    if (gameSocketRef.current && gameSocketRef.current.readyState === WebSocket.OPEN) {
      const msg = {
        player: playerId,
        action: "voice_command",
        target: command
      };
      gameSocketRef.current.send(JSON.stringify(msg));
      console.log("[Game] Sent voice command:", command);
    } else {
      console.warn("[Game] Cannot send voice command - not connected");
    }
  };

  const startVoiceRecognition = (): void => {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;

    if (!SpeechRecognition) {
      alert("Speech recognition not supported in this browser. Please use Chrome or Edge.");
      return;
    }

    if (!recognitionRef.current) {
      const recognition = new SpeechRecognition();
      recognition.continuous = true;
      recognition.interimResults = false;
      recognition.lang = 'en-US';

      recognition.onstart = () => {
        setIsListening(true);
        console.log("[Voice] Listening started...");
      };

      recognition.onresult = (event: any) => {
        const last = event.results.length - 1;
        const text = event.results[last][0].transcript.toLowerCase();
        console.log("[Voice] Heard:", text);

        const COMMAND_ALTERNATIVES: { [key: string]: number } = {
          "ready to start": 1,
          "ready start": 1,
          "start game": 1,
          "start": 1,
          "assign players": 2,
          "assign play": 2,
          "find players": 2,
          "sign players": 2,
          "assigned players": 2,
          "ready to vote": 3,
          "navigate to vote": 3,
          "ready to vogt": 3,
          "night time": 4,
          "night times": 4,
          "nite times": 4,
          "nite time": 4
        };

        for (const [phrase, code] of Object.entries(COMMAND_ALTERNATIVES)) {
          if (text.includes(phrase)) {
            console.log(`[Voice] Command matched: "${phrase}" → Code: ${code}`);
            setStatus(`Voice command: ${phrase.toUpperCase()}`);
            sendVoiceCommand(code);
            break;
          }
        }
      };

      recognition.onerror = (event: any) => {
        console.error("[Voice] Error:", event.error);
        if (event.error === 'no-speech') {
          console.log("[Voice] No speech detected, still listening...");
        }
      };

      recognition.onend = () => {
        console.log("[Voice] Recognition ended");
        if (isListening) {
          recognition.start();
        }
      };

      recognitionRef.current = recognition;
    }

    recognitionRef.current.start();
  };

  const stopVoiceRecognition = (): void => {
    if (recognitionRef.current) {
      setIsListening(false);
      recognitionRef.current.stop();
      console.log("[Voice] Stopped listening");
    }
  };

  const startHeadDetection = async (videoElement: HTMLVideoElement | null): Promise<void> => {
    if (!videoElement) return;

    const script = document.createElement("script");
    script.src = "https://cdn.jsdelivr.net/npm/@mediapipe/face_mesh/face_mesh.js";
    document.head.appendChild(script);

    script.onload = async () => {
      const FaceMesh = window.FaceMesh;

      const faceMesh = new FaceMesh({
        locateFile: (file: string) => {
          return `https://cdn.jsdelivr.net/npm/@mediapipe/face_mesh/${file}`;
        }
      });

      faceMesh.setOptions({
        maxNumFaces: 1,
        refineLandmarks: true,
        minDetectionConfidence: 0.5,
        minTrackingConfidence: 0.5
      });

      faceMesh.onResults((results: any) => {
        if (results.multiFaceLandmarks && results.multiFaceLandmarks.length > 0) {
          const landmarks = results.multiFaceLandmarks[0];

          const NOSE = 1;
          const CHIN = 152;
          const FOREHEAD = 10;

          const nose = landmarks[NOSE];
          const chin = landmarks[CHIN];
          const forehead = landmarks[FOREHEAD];

          const headHeight = chin.y - forehead.y;
          const nosePosRelative = nose.y - forehead.y;

          let newHeadPosition: string;
          if (nosePosRelative < headHeight * 0.666666) {
            newHeadPosition = "headUp";
          } else {
            newHeadPosition = "headDown";
          }

          if (newHeadPosition !== headPosition) {
            setHeadPosition(newHeadPosition);
            sendHeadPositionToServer(newHeadPosition);
          }
        } else {
          if (headPosition !== "headDown") {
            setHeadPosition("headDown");
            sendHeadPositionToServer("headDown");
          }
        }
      });

      const detectFrame = async (): Promise<void> => {
        if (videoElement && videoElement.readyState === 4) {
          await faceMesh.send({ image: videoElement });
        }
        requestAnimationFrame(detectFrame);
      };
      detectFrame();
    };
  };

  const setupSignaling = (): void => {
    const createPeer = (otherId: string): RTCPeerConnection => {
      console.log(`Creating peer connection for ${otherId}`);
      const peer = new RTCPeerConnection({
        iceServers: [{ urls: "stun:stun.l.google.com:19302" }],
      });

      if (localStreamRef.current) {
        localStreamRef.current.getTracks().forEach((track: MediaStreamTrack) => {
          console.log(`Adding ${track.kind} track to peer ${otherId}`);
          if (localStreamRef.current) {
            peer.addTrack(track, localStreamRef.current);
          }
        });
      }

      peer.ontrack = (event: RTCTrackEvent) => {
        console.log(`Received remote track from ${otherId}:`, event.track.kind);
        const remoteStream = event.streams[0];
        setRemoteStreams((prev) => {
          if (prev.some((s) => s.id === remoteStream.id)) return prev;
          console.log(`Adding remote stream: ${remoteStream.id}`);
          return [...prev, remoteStream];
        });
      };

      peer.onicecandidate = (e: RTCPeerConnectionIceEvent) => {
        if (e.candidate) {
          socketRef.current?.emit("signal", { to: otherId, data: e.candidate });
        }
      };

      peer.onconnectionstatechange = () => {
        console.log(`Peer ${otherId} state: ${peer.connectionState}`);
        if (peer.connectionState === "connected") {
          console.log("Connected to other player's video!");
        }
      };

      peerRefs.current[otherId] = peer;
      return peer;
    };

    socketRef.current?.on("user-joined", async (id: string) => {
      console.log(`User joined: ${id}`);
      if (!localStreamRef.current) {
        console.error("Local stream not ready!");
        return;
      }

      try {
        const peer = createPeer(id);
        const offer = await peer.createOffer();
        await peer.setLocalDescription(offer);
        console.log("Sending offer to", id);
        socketRef.current?.emit("signal", { to: id, data: offer });
      } catch (error) {
        console.error("Error creating offer:", error);
      }
    });

    socketRef.current?.on("signal", async ({ from, data }: { from: string; data: any }) => {
      console.log(`Signal from ${from}:`, data.type || "ice-candidate");

      if (!localStreamRef.current) {
        console.error("Local stream not ready!");
        return;
      }

      let peer = peerRefs.current[from];
      if (!peer) peer = createPeer(from);

      try {
        if (data.type === "offer") {
          await peer.setRemoteDescription(new RTCSessionDescription(data));
          const answer = await peer.createAnswer();
          await peer.setLocalDescription(answer);
          console.log("Sending answer to", from);
          socketRef.current?.emit("signal", { to: from, data: answer });
        } else if (data.type === "answer") {
          await peer.setRemoteDescription(new RTCSessionDescription(data));
        } else if (data.candidate) {
          await peer.addIceCandidate(new RTCIceCandidate(data));
        }
      } catch (error) {
        console.error("Signal handling error:", error);
      }
    });
  };

  useEffect(() => {
    return () => {
      if (animationFrameRef.current !== null) {
        cancelAnimationFrame(animationFrameRef.current);
      }
      if (socketRef.current) {
        socketRef.current.disconnect();
      }
      if (gameSocketRef.current) {
        gameSocketRef.current.close();
      }
      if (recognitionRef.current) {
        recognitionRef.current.stop();
      }
      Object.values(peerRefs.current).forEach((p) => p.close());
      if (localStreamRef.current) {
        localStreamRef.current.getTracks().forEach((t) => t.stop());
      }
      document.querySelectorAll("video[style*='display: none']").forEach(v => v.remove());
    };
  }, []);

  return (
    <div style={{ padding: "20px", fontFamily: "system-ui, sans-serif", background: "#1a1a1a", minHeight: "100vh", color: "white" }}>
      <div style={{ marginBottom: "20px", padding: "15px", background: "#2a2a2a", borderRadius: "8px", border: "1px solid #444" }}>
        <strong>Status:</strong> {status}
        {playerId && (
          <div style={{ marginTop: "10px", color: "#00aaff" }}>
            <strong>Player ID:</strong> {playerId} | <strong>Role:</strong> {role ? role.toUpperCase() : "waiting..."}
          </div>
        )}
        {headPosition !== "unknown" && (
          <div style={{ marginTop: "10px", color: headPosition === "headUp" ? "#00ff00" : "#ff6600" }}>
            <strong>Head Position:</strong> {headPosition === "headUp" ? "UP ⬆️" : "DOWN ⬇️"}
          </div>
        )}
        {isListening && (
          <div style={{ marginTop: "10px", color: "#ff00ff" }}>
            <strong>🎤 Listening for voice commands...</strong>
          </div>
        )}
      </div>

      {isStarted && (
        <div style={{ marginBottom: "20px" }}>
          <button
            onClick={isListening ? stopVoiceRecognition : startVoiceRecognition}
            style={{
              padding: "10px 20px",
              fontSize: "16px",
              background: isListening ? "#ff4444" : "#44aa44",
              color: "white",
              border: "none",
              borderRadius: "8px",
              cursor: "pointer",
              fontWeight: "bold",
              boxShadow: "0 4px 6px rgba(0,0,0,0.3)"
            }}
          >
            {isListening ? "🎤 Stop Listening" : "🎤 Start Voice Commands"}
          </button>
          <div style={{ marginTop: "10px", color: "#888", fontSize: "14px" }}>
            Say: "assign players", "ready to start", "ready to vote", or "night time"
          </div>
        </div>
      )}

      {!isStarted && (
        <div style={{ marginBottom: "30px" }}>
          <div style={{ marginBottom: "15px" }}>
            <label style={{ display: "flex", alignItems: "center", gap: "10px", cursor: "pointer" }}>
              <input
                type="checkbox"
                checked={useTestVideos}
                onChange={(e) => setUseTestVideos(e.target.checked)}
                style={{ width: "20px", height: "20px", cursor: "pointer" }}
              />
              <span>Use test videos (for solo debugging)</span>
            </label>
          </div>

          <button
            onClick={startStream}
            style={{
              padding: "15px 30px",
              fontSize: "18px",
              background: "#0066cc",
              color: "white",
              border: "none",
              borderRadius: "8px",
              cursor: "pointer",
              fontWeight: "bold",
              boxShadow: "0 4px 6px rgba(0,0,0,0.3)"
            }}
            onMouseOver={(e) => (e.target as HTMLButtonElement).style.background = "#0052a3"}
            onMouseOut={(e) => (e.target as HTMLButtonElement).style.background = "#0066cc"}
          >
            {useTestVideos ? "🎬 Start Test Video" : "🎥 Start Camera"}
          </button>
        </div>
      )}

      <h2 style={{ marginTop: "30px" }}>
        My Video {useTestVideos && `(${sessionStorage.getItem("tabVideo") || "not selected"})`}
      </h2>
      <video
        ref={localVideoRef}
        autoPlay
        playsInline
        muted
        style={{
          width: "320px",
          height: "240px",
          background: "#000",
          border: "3px solid #0066cc",
          borderRadius: "8px",
          boxShadow: "0 4px 12px rgba(0,102,204,0.3)"
        }}
      />

      <h2 style={{ marginTop: "40px" }}>
        Other Players ({remoteStreams.length})
      </h2>
      <div style={{ display: "flex", gap: "15px", flexWrap: "wrap" }}>
        {remoteStreams.length === 0 ? (
          <p style={{ color: "#888", fontSize: "16px" }}>
            {isStarted ? "No other players yet. Open another tab/device and click Start!" : "Start the stream to connect"}
          </p>
        ) : (
          remoteStreams.map((stream) => (
            <RemoteVideo key={stream.id} stream={stream} />
          ))
        )}
      </div>
    </div>
  );
}

function RemoteVideo({ stream }: { stream: MediaStream }) {
  const ref = useRef<HTMLVideoElement>(null);

  useEffect(() => {
    if (ref.current && ref.current.srcObject !== stream) {
      ref.current.srcObject = stream;
      console.log(`Remote video set with stream: ${stream.id}`);
    }
  }, [stream]);

  return (
    <div style={{ position: "relative" }}>
      <video
        ref={ref}
        autoPlay
        playsInline
        style={{
          width: "320px",
          height: "240px",
          background: "#000",
          border: "3px solid #00cc66",
          borderRadius: "8px",
          boxShadow: "0 4px 12px rgba(0,204,102,0.3)"
        }}
      />
      <div style={{
        position: "absolute",
        top: "10px",
        right: "10px",
        background: "rgba(0,204,102,0.8)",
        color: "white",
        padding: "4px 8px",
        borderRadius: "4px",
        fontSize: "12px",
        fontWeight: "bold"
      }}>
        LIVE
      </div>
    </div>
  );
}

export default Game;
