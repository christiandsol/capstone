import { useEffect, useRef } from 'react';

interface RemoteVideoProps {
  stream: MediaStream;
  playerName?: string;
  playerId?: number;
}

export const RemoteVideo: React.FC<RemoteVideoProps> = ({ stream, playerName, playerId }) => {
  const ref = useRef<HTMLVideoElement>(null);

  useEffect(() => {
    const video = ref.current;
    if (!video) {
      console.log(`[RemoteVideo] No video ref for ${playerName}`);
      return;
    }

    console.log(`[RemoteVideo] Setting stream for ${playerName}:`, {
      streamId: stream.id,
      tracks: stream.getTracks().map(t => `${t.kind}(${t.enabled})`).join(', ')
    });

    // Always set srcObject, don't compare
    video.srcObject = stream;

    // Log when stream actually plays
    const handlePlaying = () => {
      console.log(`[RemoteVideo] VIDEO PLAYING: ${playerName} - ${video.videoWidth}x${video.videoHeight}`);
    };

    const handleLoadedMetadata = () => {
      console.log(`[RemoteVideo] Metadata loaded for ${playerName}`);
    };

    const handleError = (e: ErrorEvent) => {
      console.error(`[RemoteVideo] Error for ${playerName}:`, e);
    };

    const handleCanPlay = () => {
      console.log(`[RemoteVideo] Can play: ${playerName}`);
    };

    video.addEventListener('playing', handlePlaying);
    video.addEventListener('loadedmetadata', handleLoadedMetadata);
    video.addEventListener('error', handleError);
    video.addEventListener('canplay', handleCanPlay);

    // Explicitly call play
    video.play().catch(err => {
      console.error(`[RemoteVideo] Play failed for ${playerName}:`, err);
    });

    return () => {
      video.removeEventListener('playing', handlePlaying);
      video.removeEventListener('loadedmetadata', handleLoadedMetadata);
      video.removeEventListener('error', handleError);
      video.removeEventListener('canplay', handleCanPlay);
    };
  }, [stream, playerName]);

  return (
    <div style={{ position: 'relative' }}>
      <video
        ref={ref}
        autoPlay
        playsInline
        style={{
          width: '320px',
          height: '240px',
          background: '#000',
          border: '3px solid #00cc66',
          borderRadius: '8px',
          boxShadow: '0 4px 12px rgba(0,204,102,0.3)'
        }}
      />
      <div
        style={{
          position: 'absolute',
          top: '10px',
          right: '10px',
          background: 'rgba(0,204,102,0.8)',
          color: 'white',
          padding: '4px 8px',
          borderRadius: '4px',
          fontSize: '12px',
          fontWeight: 'bold'
        }}
      >
        LIVE
      </div>
      {(playerName || playerId) && (
        <div
          style={{
            position: 'absolute',
            bottom: '0',
            left: '0',
            right: '0',
            background: 'rgba(0, 0, 0, 0.7)',
            color: 'white',
            padding: '8px',
            borderRadius: '0 0 8px 8px',
            fontSize: '14px',
            fontWeight: 'bold',
            textAlign: 'center'
          }}
        >
          {playerName && <div>{playerName}</div>}
          {playerId && <div style={{ fontSize: '12px', opacity: 0.9 }}>ID: {playerId}</div>}
        </div>
      )}
    </div>
  );
};
