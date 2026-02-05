import { useEffect, useRef } from 'react';

interface RemoteVideoProps {
  stream: MediaStream;
  playerName?: string;
  playerId?: number;
}

export const RemoteVideo: React.FC<RemoteVideoProps> = ({ stream, playerName, playerId }) => {
  const ref = useRef<HTMLVideoElement>(null);

  useEffect(() => {
    if (ref.current && ref.current.srcObject !== stream) {
      ref.current.srcObject = stream;
      console.log(`Remote video set with stream: ${stream.id}`);
    }
  }, [stream]);

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
