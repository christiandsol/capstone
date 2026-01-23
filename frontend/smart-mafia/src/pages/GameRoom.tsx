import { useEffect, useRef, useState } from "react";
import io from "socket.io-client";

const sendHeadPositionToServer = (newHeadPosition) => {

}

function Game() {
  const localVideoRef = useRef(null);
  const canvasRef = useRef(null);
  const socketRef = useRef();
  const localStreamRef = useRef();
  const peerRefs = useRef({});
  const animationFrameRef = useRef();
  const [remoteStreams, setRemoteStreams] = useState([]);
  const [status, setStatus] = useState("Click 'Start' to begin");
  const [isStarted, setIsStarted] = useState(false);
  const [useTestVideos, setUseTestVideos] = useState(false);
  const [headPosition, setHeadPosition] = useState("unknown");

  // Determine video per tab (for testing only)
  const getTabVideo = () => {
    const existing = sessionStorage.getItem("tabVideo");
    if (existing) return existing;

    const videoFile = Math.random() < 0.5 ? "/vid1.mp4" : "/vid2.mp4";
    sessionStorage.setItem("tabVideo", videoFile);
    console.log("Selected test video:", videoFile);
    return videoFile;
  };

  const startStream = async () => {
    try {
      if (useTestVideos) {
        await startTestVideoStream();
      } else {
        await startRealCameraStream();
      }
    } catch (error) {
      console.error("Setup error:", error);
      setStatus(`Error: ${error.message}`);
    }
  };

  const startRealCameraStream = async () => {
    setStatus("Requesting camera access...");

    try {
      // Request real webcam
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { width: 640, height: 480 },
        audio: false
      });

      console.log("Camera stream obtained:", stream.getTracks());

      localVideoRef.current.srcObject = stream;
      localStreamRef.current = stream;

      setStatus("Camera connected! Connecting to server...");
      setIsStarted(true);

      connectToServer();

      // Start MediaPipe head detection
      startHeadDetection(localVideoRef.current);

    } catch (error) {
      if (error.name === "NotAllowedError") {
        setStatus("Error: Camera access denied. Please allow camera access and try again.");
      } else if (error.name === "NotFoundError") {
        setStatus("Error: No camera found. Connect a camera and try again.");
      } else {
        setStatus(`Error: ${error.message}`);
      }
      throw error;
    }
  };

  const startTestVideoStream = async () => {
    const videoFile = getTabVideo();
    setStatus(`Loading ${videoFile}...`);

    const video = document.createElement("video");
    video.src = videoFile;
    video.loop = true;
    video.muted = true;
    video.playsInline = true;
    video.style.display = "none";
    document.body.appendChild(video);

    await new Promise((resolve, reject) => {
      video.onloadedmetadata = resolve;
      video.onerror = () => reject(new Error(`Failed to load ${videoFile}`));
      setTimeout(() => reject(new Error("Video load timeout")), 10000);
    });

    setStatus("Playing video...");
    await video.play();

    setStatus("Setting up canvas capture...");

    const canvas = document.createElement("canvas");
    canvas.width = 640; //hardcoded
    canvas.height = 480; //hardcoded
    canvasRef.current = canvas;

    const ctx = canvas.getContext("2d");

    const drawFrame = () => {
      if (video.paused || video.ended) return;
      ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
      animationFrameRef.current = requestAnimationFrame(drawFrame);
    };
    drawFrame();

    const stream = canvas.captureStream(30);
    localVideoRef.current.srcObject = stream;
    localStreamRef.current = stream;

    setIsStarted(true);
    connectToServer();
  };

  const connectToServer = () => {
    setStatus("Connecting to server...");
    socketRef.current = io("http://163.192.0.247:3001");

    socketRef.current.on("connect", () => {
      console.log("Connected to signaling server");
      socketRef.current.emit("join-room", "test-room");
      setStatus("Connected! Waiting for other players...");
    });

    socketRef.current.on("connect_error", (error) => {
      console.error("Socket connection error:", error);
      setStatus("Error: Cannot connect to server. Is it running on port 3001?");
    });

    setupSignaling();
  };

  const startHeadDetection = async (videoElement) => {
    // Dynamically load MediaPipe FaceMesh
    const script = document.createElement("script");
    script.src = "https://cdn.jsdelivr.net/npm/@mediapipe/face_mesh/face_mesh.js";
    document.head.appendChild(script);

    script.onload = async () => {
      const FaceMesh = window.FaceMesh;

      const faceMesh = new FaceMesh({
        locateFile: (file) => {
          return `https://cdn.jsdelivr.net/npm/@mediapipe/face_mesh/${file}`;
        }
      });

      faceMesh.setOptions({
        maxNumFaces: 1,
        refineLandmarks: true,
        minDetectionConfidence: 0.5,
        minTrackingConfidence: 0.5
      });

      faceMesh.onResults((results) => {
        if (results.multiFaceLandmarks && results.multiFaceLandmarks.length > 0) {
          const landmarks = results.multiFaceLandmarks[0];

          // Landmark indices (same as your Python code)
          const NOSE = 1;
          const CHIN = 152;
          const FOREHEAD = 10;

          const nose = landmarks[NOSE];
          const chin = landmarks[CHIN];
          const forehead = landmarks[FOREHEAD];

          const headHeight = chin.y - forehead.y;
          const nosePosRelative = nose.y - forehead.y;

          let newHeadPosition;
          if (nosePosRelative < headHeight * 0.666666) {
            newHeadPosition = "headUp";
          } else {
            newHeadPosition = "headDown";
          }

          if (newHeadPosition !== headPosition) {
            setHeadPosition(newHeadPosition);
            console.log("Head position changed:", newHeadPosition);

            // TODO: Send to your game server
            // sendHeadPositionToServer(newHeadPosition);
          }
        } else {
          if (headPosition !== "headDown") {
            setHeadPosition("headDown");
            console.log("No face detected - head down");
          }
        }
      });

      // Process video frames
      const detectFrame = async () => {
        if (videoElement && videoElement.readyState === 4) {
          await faceMesh.send({ image: videoElement });
        }
        requestAnimationFrame(detectFrame);
      };
      detectFrame();
    };
  };

  const setupSignaling = () => {
    const createPeer = (otherId) => {
      console.log(`Creating peer connection for ${otherId}`);
      const peer = new RTCPeerConnection({
        iceServers: [{ urls: "stun:stun.l.google.com:19302" }],
      });

      if (localStreamRef.current) {
        localStreamRef.current.getTracks().forEach((track) => {
          console.log(`Adding ${track.kind} track to peer ${otherId}`);
          peer.addTrack(track, localStreamRef.current);
        });
      }

      peer.ontrack = (event) => {
        console.log(`Received remote track from ${otherId}:`, event.track.kind);
        const remoteStream = event.streams[0];
        setRemoteStreams((prev) => {
          if (prev.some((s) => s.id === remoteStream.id)) return prev;
          console.log(`Adding remote stream: ${remoteStream.id}`);
          return [...prev, remoteStream];
        });
      };

      peer.onicecandidate = (e) => {
        if (e.candidate) {
          socketRef.current.emit("signal", { to: otherId, data: e.candidate });
        }
      };

      peer.onconnectionstatechange = () => {
        console.log(`Peer ${otherId} state: ${peer.connectionState}`);
        if (peer.connectionState === "connected") {
          setStatus("Connected to other player!");
        }
      };

      peerRefs.current[otherId] = peer;
      return peer;
    };

    socketRef.current.on("user-joined", async (id) => {
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
        socketRef.current.emit("signal", { to: id, data: offer });
      } catch (error) {
        console.error("Error creating offer:", error);
      }
    });

    socketRef.current.on("signal", async ({ from, data }) => {
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
          socketRef.current.emit("signal", { to: from, data: answer });
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
      if (animationFrameRef.current) {
        cancelAnimationFrame(animationFrameRef.current);
      }
      if (socketRef.current) {
        socketRef.current.disconnect();
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
        {headPosition !== "unknown" && (
          <div style={{ marginTop: "10px", color: headPosition === "headUp" ? "#00ff00" : "#ff6600" }}>
            <strong>Head Position:</strong> {headPosition === "headUp" ? "UP ⬆️" : "DOWN ⬇️"}
          </div>
        )}
      </div>

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
            onMouseOver={(e) => e.target.style.background = "#0052a3"}
            onMouseOut={(e) => e.target.style.background = "#0066cc"}
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

function RemoteVideo({ stream }) {
  const ref = useRef(null);

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

