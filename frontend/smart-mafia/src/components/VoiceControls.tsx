interface VoiceControlsProps {
  isListening: boolean;
  onStart: () => void;
  onStop: () => void;
  isMuted?: boolean;
  onToggleMute?: () => void;
}

export const VoiceControls: React.FC<VoiceControlsProps> = ({
  isListening,
  onStart,
  onStop,
  isMuted = false,
  onToggleMute
}) => {
  return (
    <div style={{ marginBottom: '20px' }}>
      <div style={{ display: 'flex', gap: '10px', marginBottom: '10px' }}>
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
            boxShadow: '0 4px 6px rgba(0,0,0,0.3)',
            flex: 1
          }}
        >
          {isListening ? '🎤 Stop Listening' : '🎤 Start Voice Commands'}
        </button>
        {onToggleMute && (
          <button
            onClick={onToggleMute}
            style={{
              padding: '10px 20px',
              fontSize: '16px',
              background: isMuted ? '#ff6644' : '#4488dd',
              color: 'white',
              border: 'none',
              borderRadius: '8px',
              cursor: 'pointer',
              fontWeight: 'bold',
              boxShadow: '0 4px 6px rgba(0,0,0,0.3)',
              flex: 1
            }}
          >
            {isMuted ? '🔇 Unmute' : '🔊 Mute'}
          </button>
        )}
      </div>
      <div style={{ marginTop: '10px', color: '#888', fontSize: '14px' }}>
        <strong>Voice Commands:</strong> Try saying: "assign players", "ready to vote", "night time"
      </div>
    </div>
  );
};
