interface StatusDisplayProps {
  status: string;
  playerId: number | null;
  role: string | null;
  headPosition: string;
  isListening: boolean;
}

export const StatusDisplay: React.FC<StatusDisplayProps> = ({
  status,
  playerId,
  role,
  headPosition,
  isListening
}) => {
  return (
    <div style={{ marginBottom: '20px', padding: '15px', background: '#2a2a2a', borderRadius: '8px', border: '1px solid #444' }}>
      <strong>Status:</strong> {status}
      <div style={{ marginTop: '5px', fontSize: '12px', color: '#666' }}>
        Env: {import.meta.env.MODE}
      </div>

      {playerId && (
        <div style={{ marginTop: '10px', color: '#00aaff' }}>
          <strong>Player ID:</strong> {playerId} | <strong>Role:</strong> {role ? role.toUpperCase() : 'waiting...'}
        </div>
      )}

      {headPosition !== 'unknown' && (
        <div style={{ marginTop: '10px', color: headPosition === 'headUp' ? '#00ff00' : '#ff6600' }}>
          <strong>Head Position:</strong> {headPosition === 'headUp' ? 'UP ⬆️' : 'DOWN ⬇️'}
        </div>
      )}

      {isListening && (
        <div style={{ marginTop: '10px', color: '#ff00ff' }}>
          <strong>🎤 Listening for voice commands...</strong>
        </div>
      )}
    </div>
  );
};
