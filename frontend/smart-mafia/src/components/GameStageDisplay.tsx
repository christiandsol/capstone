type GameStageDisplayProps = {
  gameStage: string | null;
};

export const GameStageDisplay = ({ gameStage }: GameStageDisplayProps) => {
  if (!gameStage) return null;

  // Map server states to user-friendly messages
  const stageConfig: { [key: string]: { title: string; color: string; bgColor: string; emoji: string } } = {
    'LOBBY': {
      title: 'WAITING FOR PLAYERS',
      color: '#ffaa00',
      bgColor: 'rgba(255, 170, 0, 0.2)',
      emoji: '⏳'
    },
    'HEADSDOWN': {
      title: 'NIGHTTIME - HEADS DOWN',
      color: '#1a1a2e',
      bgColor: 'rgba(26, 26, 46, 0.5)',
      emoji: '🌙'
    },
    'MAFIAVOTE': {
      title: 'NIGHTTIME - MAFIA CHOOSING',
      color: '#8b0a15',
      bgColor: 'rgba(139, 10, 21, 0.3)',
      emoji: '🔪'
    },
    'DOCTORVOTE': {
      title: 'NIGHTTIME - DOCTOR VOTING',
      color: '#0066cc',
      bgColor: 'rgba(0, 102, 204, 0.2)',
      emoji: '⚕️'
    },
    'NARRATE': {
      title: 'DAYTIME - NIGHT RESULTS',
      color: '#ffdd00',
      bgColor: 'rgba(255, 221, 0, 0.2)',
      emoji: '☀️'
    },
    'VOTE': {
      title: 'CAST YOUR VOTE',
      color: '#00ff00',
      bgColor: 'rgba(0, 255, 0, 0.15)',
      emoji: '🗳️'
    },
    'ASSIGN': {
      title: 'ASSIGNING ROLES',
      color: '#9400d3',
      bgColor: 'rgba(148, 0, 211, 0.2)',
      emoji: '🎭'
    }
  };

  const config = stageConfig[gameStage] || {
    title: gameStage,
    color: '#cccccc',
    bgColor: 'rgba(200, 200, 200, 0.1)',
    emoji: '❓'
  };

  return (
    <div
      style={{
        background: config.bgColor,
        border: `3px solid ${config.color}`,
        borderRadius: '12px',
        padding: '20px',
        marginBottom: '20px',
        textAlign: 'center',
        boxShadow: `0 0 15px ${config.color}33`
      }}
    >
      <div
        style={{
          fontSize: '3rem',
          marginBottom: '10px'
        }}
      >
        {config.emoji}
      </div>
      <h2
        style={{
          fontSize: '2rem',
          margin: '0',
          color: config.color,
          fontWeight: 'bold',
          textShadow: `0 0 10px ${config.color}66`,
          letterSpacing: '2px'
        }}
      >
        {config.title}
      </h2>
    </div>
  );
};
