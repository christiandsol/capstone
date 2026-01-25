import { useEffect, useRef } from 'react';

interface RemoteVideoProps {
  stream: MediaStream;
}

export const RemoteVideo: React.FC<RemoteVideoProps> = ({ stream }) => {
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
    </div>
  );
};
