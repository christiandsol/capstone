import express from "express";
import http from "http";
import { Server } from "socket.io";
import path from "path";

const app = express();

// Serve static files with CORS headers
app.use(express.static('public', {
  setHeaders: (res) => {
    res.set('Access-Control-Allow-Origin', '*');
    res.set('Cross-Origin-Resource-Policy', 'cross-origin');
  }
}));

const server = http.createServer(app);
const io = new Server(server, {
  cors: { origin: "*" }
});

io.on("connection", socket => {
  console.log("Connected:", socket.id);

  socket.on("join-room", room => {
    socket.join(room);
    socket.to(room).emit("user-joined", socket.id);
  });

  socket.on("signal", ({ to, data }) => {
    io.to(to).emit("signal", {
      from: socket.id,
      data
    });
  });
});

server.listen(3001, () =>
  console.log("Signaling server on 3001")
);

