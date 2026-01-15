import { useState } from "react";

type LobbyProps = {
  onStart: (name: string) => void;
  onJoin: (name: string) => void;
};

function Lobby({ onStart, onJoin }: LobbyProps) {
  const [name, setName] = useState("");

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setName(e.target.value);
  };
  return (
    <div>
      <h1>Smart Mafia</h1>
      <input
        type = "text"
        id = "name"
        value={name}
        placeholder = "Enter your name here"
        onChange={handleInputChange}
      />

      <br/>

      <button onClick={() => onJoin(name)}>

        Join Game
        </button>
      <h2>Active Players</h2>

      
      <button onClick={() => onStart(name)}>

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

  return (
    <div style={{ padding: 20 }}>

      //!!!need to implement onJoin!!!
      {page === "lobby" && <Lobby onJoin={()=>{}}onStart={() => setPage("game")} />}
      {page === "game" && <Game />}
    </div>
  );
}
