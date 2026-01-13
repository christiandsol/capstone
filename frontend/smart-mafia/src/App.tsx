import { useState } from "react";

function Lobby({ onStart }: { onStart: () => void }) {
  return (
    <div>
      <h1>Smart Mafia</h1>
      <button onClick={onStart}>Join Game</button>
    </div>
  );
}

function Game() {
  return (
    <div>
      <h1>🎭 Game Room</h1>
      <p>Video grid will go here</p>
    </div>
  );
}

export default function App() {
  const [page, setPage] = useState<"lobby" | "game">("lobby");

  return (
    <div style={{ padding: 20 }}>
      {page === "lobby" && <Lobby onStart={() => setPage("game")} />}
      {page === "game" && <Game />}
    </div>
  );
}
