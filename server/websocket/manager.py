from typing import List, Dict
from fastapi.websockets import WebSocket

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[WebSocket, str] = {}

    async def connect(self, websocket: WebSocket, username: str):
        await websocket.accept()
        self.active_connections[websocket] = username

    def disconnect(self, websocket: WebSocket):
        self.active_connections.pop(websocket, None)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            await connection.send_text(message)

    async def list_users(self):
        return list(self.active_connections.values())
    
    async def send_private_message(self, sender: str, receiver: str, message: str):
        for connection, username in self.active_connections.items():
            if username == receiver:
                await connection.send_text(f"Mensagem privada de {sender}: {message}")
                break

    async def typing_notification(self, username: str):
        for connection in self.active_connections:
            await connection.send_text(f"{username} está digitando...")
            



