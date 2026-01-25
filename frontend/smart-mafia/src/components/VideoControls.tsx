import { useState } from 'react';

interface VideoControlsProps {
  onStart: (useTestVideos: boolean) => Promise<void>;
}

export const VideoControls: React.FC<VideoControlsProps> = ({ onStart }) => {
  const [useTestVideos, setUseTestVideos] = useState(false);

  return (
    <div style={{ marginBottom: '30px' }}>
      <div style={{ marginBottom: '15px' }}>
        <label style={{ display: 'flex', alignItems: 'center', gap: '10px', cursor: 'pointer' }}>
          <input
            type="checkbox"
            checked={useTestVideos}
            onChange={(e) => setUseTestVideos(e.target.checked)}
            style={{ width: '20px', height: '20px', cursor: 'pointer' }}
          />
          <span>Use test videos (for solo debugging)</span>
        </label>
      </div>

      <button
        onClick={() => onStart(useTestVideos)}
        style={{
          padding: '15px 30px',
          fontSize: '18px',
          background: '#0066cc',
          color: 'white',
          border: 'none',
          borderRadius: '8px',
          cursor: 'pointer',
          fontWeight: 'bold',
          boxShadow: '0 4px 6px rgba(0,0,0,0.3)'
        }}
        onMouseOver={(e) => (e.target as HTMLButtonElement).style.background = '#0052a3'}
        onMouseOut={(e) => (e.target as HTMLButtonElement).style.background = '#0066cc'}
      >
        {useTestVideos ? '🎬 Start Test Video' : '🎥 Start Camera'}
      </button>
    </div>
  );
};
