import express from "express";
import http from "http";
import { Server } from "socket.io";

const app = express();
app.use(express.json());
app.use(express.static('public', {
  setHeaders: (res) => {
    res.set('Access-Control-Allow-Origin', '*');
    res.set('Cross-Origin-Resource-Policy', 'cross-origin');
  }
}));

const server = http.createServer(app);
const io = new Server(server, {
  cors: {
    origin: "*",
    methods: ["GET", "POST"],
    credentials: true
  },
  transports: ['websocket', 'polling']
});

// ======= DEFINING METHODS ======
io.on("connection", socket => {
  console.log("Connected:", socket.id);

  socket.on("join-room", (room, playerName: string) => {
    socket.join(room);
    if (playerName) {
      (socket as any).playerName = playerName;
    }
    socket.to(room).emit("user-joined", socket.id);
  });

  socket.on("broadcast-player-info", (data: { name: string; id: number }) => {
    // Broadcast to all others in the room
    socket.to('test-room').emit("broadcast-player-info", {
      socketId: socket.id,
      name: data.name,
      id: data.id
    });
    console.log(`[Server] Broadcasting player info: ${data.name} (ID: ${data.id}) from ${socket.id}`);
  });

  socket.on("player-info", (data: { to: string; name: string; id: number }) => {
    // Send player info to specific peer
    io.to(data.to).emit("player-info", {
      from: socket.id,
      name: data.name,
      id: data.id
    });
    console.log(`[Server] Sending player info: ${data.name} (ID: ${data.id}) from ${socket.id} to ${data.to}`);
  });

  socket.on("signal", ({ to, data }) => {
    io.to(to).emit("signal", {
      from: socket.id,
      data
    });
  });

  socket.on("disconnecting", () => {
    console.log("Disconnected:", socket.id);
    console.log("Broadcasting disconnect now");
    socket.rooms.forEach(room => {
      if (room !== socket.id) {
        io.in(room).emit("user-disconnected", {  // io.in includes the sender
          socketId: socket.id,
          playerName: (socket as any).playerName
        });
        console.log(`[Server] Notified room ${room} that ${socket.id} left`);
      }
    });

    socket.emit("user-disconnected", {
      socketId: socket.id,
      playerName: (socket as any).playerName
    });
  });
});

app.post("/disconnect-player", (req, res) => {
  const { name } = req.body;
  console.log(`[POST] /disconnect-player received disconnect signal for: ${name}`)

  if (!name) {
    res.status(400).json({ error: "Missing player name" });
    return;
  }

  // Find the socket for this player name and disconnect it
  let found = false;
  io.sockets.sockets.forEach(socket => {
    if ((socket as any).playerName === name) {
      socket.disconnect(true);
      found = true;
    }
  });

  if (found) {
    res.json({ success: true, message: `Disconnected ${name}` });
  } else {
    res.status(404).json({ error: `Player ${name} not found` });
  }
});

// Listen on :: (IPv6) which also accepts IPv4 connections
server.listen(3001, "::", () => {
  console.log("Signaling server on 3001 (IPv4 and IPv6)");
});

process.on('SIGINT', async () => {
  console.log('[Server] Shutting down...');

  // 1. First broadcast disconnect to everyone BEFORE closing anything
  io.sockets.sockets.forEach(socket => {
    const playerName = (socket as any).playerName;
    if (playerName) {
      socket.rooms.forEach(room => {
        if (room !== socket.id) {
          socket.to(room).emit("user-disconnected", {
            socketId: socket.id,
            playerName: playerName
          });
        }
      });
    }
  });

  // 2. Give it a moment to flush before shutting down
  await new Promise(resolve => setTimeout(resolve, 500));

  // 3. NOW close everything
  io.close();
  server.close();
  process.exit(0);
});
