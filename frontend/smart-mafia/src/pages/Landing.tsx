import { useState } from "react";

import Rpi from "./Rpi";
import GameRoom from "./GameRoom";
import { useGameSocket } from "../hooks/useGameSocket";
import { useNotifications } from "../hooks/useNotifications";
import type { UseGameSocketReturn } from "../types/game.types";
import { Notification } from "../components/Notifications";
//
// const socket: Socket = io("http://163.192.0.247", {
//   transports: ["websocket"],
// });

type LobbyProps = {
  onStart: () => void;
  players: string[];
  playerName: string;
  setName: (playerName: string) => void;
};

function Lobby({ onStart, playerName, setName }: LobbyProps) {

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        minHeight: "100vh",
        width: "100vw",
        position: "fixed",
        top: 0,
        left: 0,
        background: "linear-gradient(180deg, #1f1f1f, #0a0a0a)",
        color: "white",
        fontFamily: "'Creepster', cursive",
        textAlign: "center",
        padding: "20px",
        boxSizing: "border-box",
      }}
    >
      {/* Title */}
      <h1
        style={{
          fontSize: "5rem",
          marginBottom: "30px",
          color: "#8b0a15",
          textShadow: "0 0 20px #8b0a15",
          margin: "0 0 50px 0",
        }}
      >
        Smart Mafia
      </h1>

      <div
        style={{
          background: "rgba(30,30,30,0.9)",
          padding: "40px",
          borderRadius: "15px",
          boxShadow: "0 0 40px rgba(0,0,0,0.7)",
          width: "100%",
          maxWidth: "400px",
          marginBottom: "30px",
        }}
      >
        <input
          type="text"
          placeholder="Enter your name here"
          value={playerName}
          onChange={(e) => setName(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") onStart();
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
          onClick={onStart}
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
      </div>



    </div>
  );
}


export default function App() {
  const [page, setPage] = useState<"lobby" | "GameRoom">("lobby");
  const [playerName, setName] = useState<string>("");
  const [status, setStatus] = useState("");
  const [shouldConnect, setShouldConnect] = useState<boolean>(false);
  const { notifications, removeNotification, notify } = useNotifications();

  const gameSocket: UseGameSocketReturn = useGameSocket(
    () => setPage("GameRoom"),
    () => setShouldConnect(false),
    shouldConnect,
    setStatus,
    playerName,
    notify.error
  );


  return (
    <div style={{ padding: 20 }}>
      {/* Render all notifications */}
      {notifications.map((notification) => (
        <Notification
          key={notification.id}
          id={notification.id}
          message={notification.message}
          type={notification.type}
          duration={notification.duration}
          onDismiss={removeNotification}
        />
      ))}

      {(page == "lobby") && (
        <Lobby
          onStart={() => {
            if (playerName !== "") {
              setShouldConnect(true);
            }
          }}
          players={["temp string"]}
          playerName={playerName}
          setName={setName}
        />
      )}

      {page === "GameRoom" && <GameRoom
        playerName={playerName} gameSocket={gameSocket} setStatus={setStatus} status={status}
      />}
    </div>
  );
}
