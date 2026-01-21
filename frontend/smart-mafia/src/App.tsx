import { useState, useEffect } from "react";

//this is the "server" to do actual server:
//const socket = io("http://localhost:3000");\
const channel = new BroadcastChannel("server");

type LobbyProps = {
  onStart: () => void;
  onJoin: (name: string) => void;
  players: string[];
};

function Lobby({ onStart, onJoin, players }: LobbyProps) {
  const [name, setName] = useState("");

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setName(e.target.value);
  };

  return (
    <div>
      <h1>Smart Mafia</h1>

      <input
        type="text"
        id="name"
        value={name}
        placeholder="Enter your name here"
        onChange={handleInputChange}
      />

      <br />

      <button onClick={() => onJoin(name)}>
        Join Game
      </button>

      <h2>Active Players</h2>
      <ul>
        {players.map((p) => (
          <li key={p}>{p}</li>
        ))}
      </ul>

      <button onClick={onStart}>
        Start Game
      </button>
    </div>
  );
}

function Game() {
  return (
    <div>
      <h1>Game Room</h1>
      <p>Video grid will go here</p>
    </div>
  );
}

export default function App() {
  const [page, setPage] = useState<"lobby" | "game">("lobby");
  const [players, setPlayers] = useState<string[]>([]);

  useEffect(() => {
    channel.onmessage = (event) => {
      if (event.data.type === "JOIN") {
        setPlayers((prev) =>
          prev.includes(event.data.name)
            ? prev
            : [...prev, event.data.name]
        );
      }
    };
  }, []);

  const handleJoin = (name: string) => {
    if (!name.trim()) return;

    setPlayers((prev) =>
      prev.includes(name) ? prev : [...prev, name]
    );

    channel.postMessage({
      type: "JOIN",
      name,
    });
  };

  return (
    <div style={{ padding: 20 }}>
      {page === "lobby" && (
        <Lobby
          onJoin={handleJoin}
          onStart={() => setPage("game")}
          players={players}
        />
      )}

      {page === "game" && <Game />}
    </div>
  );
}
