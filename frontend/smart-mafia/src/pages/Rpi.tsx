import { useState } from 'react';
import { API_CONFIG } from '../config/api.config';
import GameRoom from './GameRoom';

type RpiProps = {
  playerName: string;
};

const RPI_PORT = 8000;

const connectRpi = async (ip_addr: string, playerName: string): Promissee<bool> => {
  console.log(`player name: ${playerName}`)
  // const resolvedIp = ip_addr;
  // NOTE: HERE uncomment the resolved IP line if you don't want to use raspberry pi and you are debugging
  const resolvedIp = import.meta.env.DEV
    ? "127.0.0.1"
    : ip_addr;

  const rpi_url = `http://${resolvedIp}:${RPI_PORT}/api/${playerName}`
  console.log(`[RPI_CONNECT] Raspberry pi connect signal sent out to: ${rpi_url}`)
  try {
    const res = await fetch(rpi_url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ip: ip_addr, playerName })
    });
    if (!res.ok) {
      throw new Error(`Error trying to connect to server, [STATUS CODE: ] ${res.status}`)
    }
    return res.ok
  } catch (error) {
    throw new Error(`Error trying to connect to server, could not get result`)
  }
  return false
};

export default function Rpi({ playerName }) {
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
