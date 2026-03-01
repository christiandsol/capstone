import { useState } from 'react';
// import { API_CONFIG } from '../config/api.config';
import GameRoom from './GameRoom';

type RpiProps = {
  playerName: string;
};


export default function Rpi({ playerName }: RpiProps) {
  const [ip_addr, setIP] = useState<string>("");
  const [page, setPage] = useState<string>("rpi");
  return (
    <div>
      {page == "rpi" &&
        <>
          <input
            type="text"
            placeholder="Enter your raspberry pi's IP here"
            value={ip_addr}
            onChange={(e) => setIP(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") { connectRpi(ip_addr, playerName); setPage('game') }
            }}
            style={{
              width: "100%",
              padding: "15px",
              borderRadius: "5px",
              marginBottom: "20px",
              border: "none",
              fontSize: "1.2rem",
              boxSizing: "border-box",
            }}
          />
          <button
            onClick={() => { connectRpi(ip_addr, playerName); setPage('game') }}
            style={{
              width: "100%",
              padding: "15px",
              borderRadius: "5px",
              border: "none",
              backgroundColor: "#8b0a15",
              color: "white",
              fontSize: "1.2rem",
              fontWeight: "bold",
              cursor: "pointer",
              boxShadow: "0 5px 20px rgba(230, 57, 70, 0.6)",
              transition: "all 0.3s ease",
            }}
            onMouseOver={(e) =>
              ((e.target as HTMLButtonElement).style.transform = "scale(1.05)")
            }
            onMouseOut={(e) =>
              ((e.target as HTMLButtonElement).style.transform = "scale(1)")
            }
          >
            Join Game
          </button>
        </>
      }

      {page === 'game' && <GameRoom playerName={playerName} />}
    </div >
  );
}
