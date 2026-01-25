interface VoiceControlsProps {
  isListening: boolean;
  onStart: () => void;
  onStop: () => void;
}

export const VoiceControls: React.FC<VoiceControlsProps> = ({
  isListening,
  onStart,
  onStop
}) => {
  return (
    <div style={{ marginBottom: '20px' }}>
      <button
        onClick={isListening ? onStop : onStart}
        style={{
          padding: '10px 20px',
          fontSize: '16px',
          background: isListening ? '#ff4444' : '#44aa44',
          color: 'white',
          border: 'none',
          borderRadius: '8px',
          cursor: 'pointer',
          fontWeight: 'bold',
          boxShadow: '0 4px 6px rgba(0,0,0,0.3)'
        }}
      >
        {isListening ? '🎤 Stop Listening' : '🎤 Start Voice Commands'}
      </button>
      <div style={{ marginTop: '10px', color: '#888', fontSize: '14px' }}>
        Say: "assign players", "ready to start", "ready to vote", or "night time"
      </div>
    </div>
  );
};
