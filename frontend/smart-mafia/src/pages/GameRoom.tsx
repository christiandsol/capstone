import { useState } from 'react';
import imuDiagram from '../assets/IMUdiagram.png';
import { useVoiceRecognition } from '../hooks/useVoiceRecognition';
import { useWebRTC } from '../hooks/useWebRTC';
import { useMediaStream } from '../hooks/useMediaStream';
import { useHeadDetection } from '../hooks/useHeadDetection';
import { useNotifications } from '../hooks/useNotifications';
import { StatusDisplay } from '../components/StatusDisplay';
import { VoiceControls } from '../components/VoiceControls';
import { VideoControls } from '../components/VideoControls';
import { RemoteVideo } from '../components/RemoteVideo';
import type { UseGameSocketReturn } from '../types/game.types';

type GameProps = {
  playerName: string;
  gameSocket: UseGameSocketReturn;
  setStatus: (status: string) => void;
  status: string;
  onWebDisconnect: () => void,
};

const winnerText: Record<string, string> = {
  mafia: "MAFIA WINS!",
  civilians: "CIVILIANS WIN!",
  no_one: "NO ONE WON",
};

export default function GameRoom({ playerName, gameSocket, setStatus, status, onWebDisconnect }: GameProps) {
  const [headPosition, setHeadPosition] = useState("unknown");
  const [isStarted, setIsStarted] = useState(false);
  const [isMuted, setIsMuted] = useState(false);
  const [hasClickedReady, setHasClickedReady] = useState(false);
  const [hasClickedRestart, setHasClickedRestart] = useState(false);

  // Initialize notifications
  const { notify } = useNotifications();

  // Pass notify to useGameSocket
  const {
    role,
    playerId,
    lobbyStatus,
    restartStatus,
    gameOverData,
    deadPlayers,
    sendHeadPosition,
    setCurrentHead,
    sendVoiceCommand,
    sendReady,
    sendRestart
  } = gameSocket;

  // Voice recognition
  const { isListening, start: startVoice, stop: stopVoice } = useVoiceRecognition(
    (code, phrase) => {
      setStatus(`Voice command: ${phrase.toUpperCase()}`);
      sendVoiceCommand(code);
    }
  );

  // Media stream (camera/video)
  const { localVideoRef, localStream, isUsingTestVideo, startCamera, startTestVideo } = useMediaStream(setStatus);

  // Head detection
  useHeadDetection(
    isUsingTestVideo ? { current: null } : localVideoRef,
    (position) => {
      if (!isUsingTestVideo) {
        setCurrentHead(position)
        setHeadPosition(position);
        sendHeadPosition(position);
      }
    }
  );

  // WebRTC peer connections
  const { remoteStreams } = useWebRTC(
    localStream,
    setStatus,
    playerName,
    playerId,
    (disconnectedName) => {
      // Optimistically remove from lobby status display
      if (disconnectedName === '__self__') {
        // if you are the player to disconnect, go back to Lobby page
        console.log("[DISCONNECT] Disconnected from web server, going back to lobby")
        onWebDisconnect();
      }
    }
  );

  // Toggle audio mute/unmute
  const toggleAudio = () => {
    if (localStream) {
      localStream.getAudioTracks().forEach((track: MediaStreamTrack) => {
        track.enabled = !track.enabled;
      });
      const newMutedState = !isMuted;
      setIsMuted(newMutedState);
      setStatus(newMutedState ? 'Microphone OFF' : 'Microphone ON');

      // Show notification
      notify.info(newMutedState ? 'Microphone OFF' : 'Microphone ON');
    }
  };

  const handleStart = async (useTestVideos: boolean) => {
    if (useTestVideos) {
      setHeadPosition("headDown");
      sendHeadPosition("headDown");
      await startTestVideo();
    } else {
      await startCamera();
    }
    setIsStarted(true);
    notify.success('Stream started!');
  };

  const handleReady = () => {
    sendReady();
    setHasClickedReady(true);
    notify.success('Marked as ready!');
  };

  const handleRestart = () => {
    sendRestart();
    setHasClickedRestart(true);
    notify.success('Voted to play again!');
  };

  const gameHasStarted = role !== null && !gameOverData;
  const gameIsOver = gameOverData !== null;

  if (!gameIsOver && (hasClickedReady || hasClickedRestart)) {
    setHasClickedReady(false);
    setHasClickedRestart(false);
  }

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

        {/* Game Over Screen */}
        {gameIsOver && gameOverData && (
          <div style={{
            background: gameOverData.winner === 'mafia' ? '#3d0a0a' : '#0a3d1a',
            padding: '30px',
            borderRadius: '12px',
            marginTop: '20px',
            border: `3px solid ${gameOverData.winner === 'mafia' ? '#8b0a15' : '#00cc00'}`,
            textAlign: 'center'
          }}>
            <h1 style={{
              fontSize: '3rem',
              margin: '0 0 20px 0',
              color: gameOverData.winner === 'mafia' ? '#ff4444' : '#00ff00',
              textShadow: `0 0 20px ${gameOverData.winner === 'mafia' ? '#ff4444' : '#00ff00'}`
            }}>
              {winnerText[gameOverData.winner]}
            </h1>

            <div style={{ marginTop: '20px', fontSize: '18px' }}>
              <p>The Mafia were:</p>
              <div style={{ marginTop: '10px' }}>
                <span style={{ fontWeight: 'bold', fontSize: '20px' }}>
                  {gameOverData.mafia.filter(m => m).join(', ')}
                </span>
              </div>
            </div>

            {restartStatus && (
              <div style={{ marginTop: '30px' }}>
                <h2 style={{ fontSize: '1.5rem', marginBottom: '15px' }}>
                  Play Again?
                </h2>
                <p style={{ fontSize: '18px', marginBottom: '15px' }}>
                  {restartStatus.restart_count}/{restartStatus.total_count} players want to restart
                </p>

                {/* Player restart list */}
                <div style={{ marginTop: '15px', marginBottom: '20px' }}>
                  {Object.entries(restartStatus.players).map(([name, wantsRestart]) => (
                    <div key={name} style={{
                      padding: '8px',
                      marginBottom: '5px',
                      background: wantsRestart ? '#004d00' : '#3a3a3a',
                      borderRadius: '4px',
                      display: 'flex',
                      justifyContent: 'space-between',
                      alignItems: 'center'
                    }}>
                      <span>{name}</span>
                      <span style={{
                        fontSize: '12px',
                        color: wantsRestart ? '#00ff00' : '#888'
                      }}>
                        {wantsRestart ? 'Ready' : 'Waiting...'}
                      </span>
                    </div>
                  ))}
                </div>

                {!hasClickedRestart ? (
                  <button
                    onClick={handleRestart}
                    style={{
                      padding: '15px 40px',
                      fontSize: '22px',
                      fontWeight: 'bold',
                      background: '#00cc00',
                      color: 'white',
                      border: 'none',
                      borderRadius: '8px',
                      cursor: 'pointer',
                      transition: 'background 0.2s'
                    }}
                    onMouseOver={(e) => e.currentTarget.style.background = '#00ff00'}
                    onMouseOut={(e) => e.currentTarget.style.background = '#00cc00'}
                  >
                    PLAY AGAIN
                  </button>
                ) : (
                  <div style={{
                    padding: '15px',
                    background: '#004d00',
                    borderRadius: '8px',
                    fontSize: '18px',
                    color: '#00ff00'
                  }}>
                    Waiting for others to restart...
                  </div>
                )}
              </div>
            )}
          </div>
        )}

        {/* Lobby Status & Voice Commands / Ready Button */}
        {!gameHasStarted && !gameIsOver && lobbyStatus && (
          <div style={{
            background: '#2a2a2a',
            padding: '20px',
            borderRadius: '8px',
            marginTop: '20px',
            border: '2px solid rgb(139, 10, 21)'
          }}>
            <h2 style={{ margin: '0 0 15px 0', color: 'rgb(139, 10, 21)' }}>
              Lobby Status
            </h2>
            <p style={{ fontSize: '18px', margin: '10px 0' }}>
              Players Ready: <strong>{lobbyStatus.ready_count}/{lobbyStatus.total_count}</strong>
            </p>
            <p style={{ fontSize: '14px', color: '#888', margin: '5px 0' }}>
              Minimum players needed: {lobbyStatus.min_players}
            </p>

            {/* Player list */}
            <div style={{ marginTop: '15px' }}>
              <h3 style={{ fontSize: '16px', marginBottom: '10px' }}>Players:</h3>
              {Object.entries(lobbyStatus.players).map(([name, isReady]) => (
                <div key={name} style={{
                  padding: '8px',
                  marginBottom: '5px',
                  background: isReady ? '#004d00' : '#3a3a3a',
                  borderRadius: '4px',
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center'
                }}>
                  <span>{name}</span>
                  <span style={{
                    fontSize: '12px',
                    color: isReady ? '#00ff00' : '#888'
                  }}>
                    {isReady ? 'READY' : 'Waiting...'}
                  </span>
                </div>
              ))}
            </div>

            {/* Voice Controls or Ready Button */}
            {!hasClickedReady ? (
              <>
                {/* Show voice controls if stream is started */}
                {isStarted && (
                  <div style={{ marginTop: '20px' }}>
                    <VoiceControls
                      isListening={isListening}
                      onStart={startVoice}
                      onStop={stopVoice}
                      isMuted={isMuted}
                      onToggleMute={toggleAudio}
                    />
                    <p style={{
                      fontSize: '14px',
                      color: '#ffaa00',
                      marginTop: '10px',
                      textAlign: 'center',
                      fontStyle: 'italic'
                    }}>
                      Say "assign players" to mark yourself ready!
                    </p>
                  </div>
                )}

                {/* Show button if stream not started yet */}
                {!isStarted && (
                  <button
                    onClick={handleReady}
                    style={{
                      marginTop: '20px',
                      padding: '15px 30px',
                      fontSize: '20px',
                      fontWeight: 'bold',
                      background: "rgb(139, 10, 21)",
                      color: 'white',
                      border: 'none',
                      borderRadius: '8px',
                      cursor: 'pointer',
                      width: '100%',
                      transition: 'background 0.2s'
                    }}
                    onMouseOver={(e) => e.currentTarget.style.background = '#b01020'}
                    onMouseOut={(e) => e.currentTarget.style.background = 'rgb(139, 10, 21)'}
                  >
                    READY TO START
                  </button>
                )}
              </>
            ) : (
              <div style={{
                marginTop: '20px',
                padding: '15px',
                background: '#004d00',
                borderRadius: '8px',
                textAlign: 'center',
                fontSize: '18px',
                color: '#00ff00'
              }}>
                You are ready! Waiting for others...
              </div>
            )}
          </div>
        )}

        {/* Voice Controls for Game In Progress */}
        {isStarted && gameHasStarted && !gameIsOver && (
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
        <div style={{ position: "relative", display: "inline-block" }}>
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
          <div
            style={{
              position: "absolute",
              top: "10px",
              right: "10px",
              background: "rgba(0,102,204,0.8)",
              color: "white",
              padding: "4px 8px",
              borderRadius: "4px",
              fontSize: "12px",
              fontWeight: "bold"
            }}
          >
            YOU
          </div>
          {(playerName || playerId !== null) && (
            <div
              style={{
                position: "absolute",
                bottom: 0,
                left: 0,
                right: 0,
                background: "rgba(0, 0, 0, 0.7)",
                color: "white",
                padding: "8px",
                borderRadius: "0 0 8px 8px",
                fontSize: "14px",
                fontWeight: "bold",
                textAlign: "center"
              }}
            >
              {playerName && <div>{playerName}</div>}
              {playerId !== null && <div style={{ fontSize: "12px", opacity: 0.9 }}>ID: {playerId}</div>}
            </div>
          )}
        </div>
        <h2 style={{ marginTop: "40px" }}>
          Other Players ({remoteStreams && remoteStreams.length})
        </h2>
        <div style={{ display: "flex", gap: "15px", flexWrap: "wrap" }}>
          {remoteStreams && remoteStreams.length === 0 ? (
            <p style={{ color: "#888", fontSize: "16px" }}>
              {isStarted ? "No other players yet. Open another tab/device and click Start!" : "Start the stream to connect"}
            </p>
          ) : (
            remoteStreams && remoteStreams.map((streamInfo) => (
              <RemoteVideo
                key={streamInfo.stream.id}
                stream={streamInfo.stream}
                playerName={streamInfo.playerName}
                playerId={streamInfo.playerId}
                isDead={streamInfo.playerName ? deadPlayers.has(streamInfo.playerName) : false}
              />
            ))
          )}
        </div>
      </div>


      <section style={{
        margin: '40px auto 0 auto',
        maxWidth: '1000px',
        background: '#232323',
        borderRadius: '12px',
        boxShadow: '0 2px 12px rgba(0,0,0,0.18)',
        padding: '32px',
        color: '#fff',
        width: 'calc(100% - 40px)',
      }}>
        <h2 style={{ textAlign: 'center', color: '#ffd700', marginBottom: '18px', fontSize: '2rem' }}>Game Controls Guide</h2>
        <div style={{ display: 'flex', flexDirection: 'row', alignItems: 'flex-start', gap: '32px', justifyContent: 'center' }}>
          <div style={{ flex: '0 0 340px', textAlign: 'center' }}>
            <h3 style={{ color: '#ffd700', fontSize: '1.2rem', marginBottom: '12px', textAlign: 'center' }}>Gesture Recognition</h3>

            <img src={imuDiagram} alt="IMU Directions for Voting" style={{ maxWidth: '340px', width: '100%', height: 'auto', borderRadius: '8px', boxShadow: '0 2px 8px rgba(0,0,0,0.12)' }} />
            <div style={{ marginTop: '0.5rem', fontSize: '1.1rem', color: '#ffd700', textAlign: 'center' }}>
              Move your IMU as shown to select the ID of the player you choose
            </div>
          </div>
          <div style={{ flex: '1', minWidth: '260px' }}>
            <h3 style={{ color: '#ffd700', fontSize: '1.2rem', marginBottom: '12px', textAlign: 'center' }}>Voice Commands</h3>
            <table style={{ width: '100%', background: '#181818', borderRadius: '8px', borderCollapse: 'collapse', fontSize: '1.05rem', color: '#fff', boxShadow: '0 1px 4px rgba(0,0,0,0.10)' }}>
              <thead>
                <tr style={{ background: '#333' }}>
                  <th style={{ padding: '10px', borderRadius: '8px 0 0 0' }}>Command</th>
                  <th style={{ padding: '10px', borderRadius: '0 8px 0 0' }}>Functionality</th>
                </tr>
              </thead>
              <tbody>
                <tr>
                  <td style={{ padding: '10px', color: '#ffd700' }}> "assign players"</td>
                  <td style={{ padding: '10px' }}>Mark yourself as ready to start the game</td>
                </tr>
                <tr>
                  <td style={{ padding: '10px', color: '#ffd700' }}>"ready to vote"</td>
                  <td style={{ padding: '10px' }}>Mark yourself as ready to vote for Mafia</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </section>
    </div>
  );
}
