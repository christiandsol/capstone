import { useState } from 'react';
import { useGameSocket } from '../hooks/useGameSocket';
import { useVoiceRecognition } from '../hooks/useVoiceRecognition';
import { useWebRTC } from '../hooks/useWebRTC';
import { useMediaStream } from '../hooks/useMediaStream';
import { useHeadDetection } from '../hooks/useHeadDetection';
import { StatusDisplay } from '../components/StatusDisplay';
import { VoiceControls } from '../components/VoiceControls';
import { VideoControls } from '../components/VideoControls';
import { RemoteVideo } from '../components/RemoteVideo';

type GameProps = {
  playerName: string;
};


export default function GameRoom({ playerName }: GameProps) {
  const [status, setStatus] = useState("Click 'Start' to begin");
  const [headPosition, setHeadPosition] = useState("unknown");
  const [isStarted, setIsStarted] = useState(false);
  const [isMuted, setIsMuted] = useState(false);

  // Game server connection
  const { role, playerId, sendHeadPosition, sendVoiceCommand } = useGameSocket(setStatus, playerName);

  // Voice recognition
  const { isListening, start: startVoice, stop: stopVoice } = useVoiceRecognition(
    (code, phrase) => {
      setStatus(`Voice command: ${phrase.toUpperCase()}`);
      sendVoiceCommand(code);
    }
  );

  // Media stream (camera/video)
  const { localVideoRef, localStream, startCamera, startTestVideo } = useMediaStream(setStatus);

  // Head detection
  useHeadDetection(localVideoRef, (position) => {
    setHeadPosition(position);
    sendHeadPosition(position);
  });

  // WebRTC peer connections
  const { remoteStreams } = useWebRTC(localStream, setStatus, playerName, playerId);

  // Toggle audio mute/unmute
  const toggleAudio = () => {
  if (localStream) {
    localStream.getAudioTracks().forEach((track: MediaStreamTrack) => {
      track.enabled = !track.enabled;
    });
    const newMutedState = !isMuted;
    setIsMuted(newMutedState);
    setStatus(newMutedState ? 'Microphone OFF' : 'Microphone ON'); 
};}

  const handleStart = async (useTestVideos: boolean) => {
    if (useTestVideos) {
      setHeadPosition("headDown")
      sendHeadPosition("headDown")
      await startTestVideo();
    } else {
      await startCamera();
    }
    setIsStarted(true);
  };

  return (
    <div style={{ padding: "0", fontFamily: "system-ui, sans-serif", background: "#1a1a1a", minHeight: "100vh", color: "white" }}>
      {/* Game Room Heading */}
      <div style={{ 
        textAlign: 'center', 
        padding: '20px 20px 20px 20px',
        background: 'linear-gradient(180deg, #2a2a2a, #1a1a1a)',
      }}>
        <h1 style={{ 
          fontSize: '4rem',
          margin: '0 0 10px 0',
          color: '#8b0a15',
          textShadow: '0 0 20px #8b0a15',
          fontFamily: "'Creepster', cursive",
        }}>
          Game Room
        </h1>
      </div>

      <div style={{ padding: "20px" }}>
        <StatusDisplay
          status={status}
          playerName={playerName}
          role={role}
          headPosition={headPosition}
          isListening={isListening}
        />

      {isStarted && (
        <VoiceControls
          isListening={isListening}
          onStart={startVoice}
          onStop={stopVoice}
          isMuted={isMuted}
          onToggleMute={toggleAudio}
        />
      )}

      {!isStarted && (
        <VideoControls onStart={handleStart} />
      )}

      <h2 style={{ marginTop: "30px" }}>
        My Video {sessionStorage.getItem("tabVideo") && `(${sessionStorage.getItem("tabVideo")})`}
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
          remoteStreams.map((streamInfo) => (
            <RemoteVideo 
              key={streamInfo.stream.id} 
              stream={streamInfo.stream}
              playerName={streamInfo.playerName}
              playerId={streamInfo.playerId}
            />
          ))
        )}
      </div>
      </div>
    </div>
  );
}
