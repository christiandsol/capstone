import express from "express";
import http from "http";
import { Server } from "socket.io";

const app = express();

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

io.on("connection", socket => {
  console.log("Connected:", socket.id);
  
  socket.on("join-room", room => {
    socket.join(room);
    socket.to(room).emit("user-joined", socket.id);
    console.log(`Socket ${socket.id} joined room: ${room}`);
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
