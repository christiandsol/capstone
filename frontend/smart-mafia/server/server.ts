import express from "express";
import http from "http";
import { Server } from "socket.io";

const app = express();

app.use(express.json())

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

  socket.on("join-room", room => {
    socket.join(room);
    socket.to(room).emit("user-joined", socket.id);
    console.log(`Socket ${socket.id} joined room: ${room}`);
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

  socket.on("disconnect", () => {
    console.log("Disconnected:", socket.id);
  });
});

// Listen on :: (IPv6) which also accepts IPv4 connections
server.listen(3001, "::", () => {
  console.log("Signaling server on 3001 (IPv4 and IPv6)");
});
