from typing import Dict, Set
from fastapi.websockets import WebSocket
import asyncio

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[WebSocket, str] = {}
        self.typing_users: Set[str] = set()
        self.typing_tasks: Dict[str, asyncio.Task] = {}

    async def connect(self, websocket: WebSocket, username: str):
        await websocket.accept()
        self.active_connections[websocket] = username

    def disconnect(self, websocket: WebSocket):
        username = self.active_connections.pop(websocket, None)
        if username in self.typing_users:
            self.typing_users.remove(username)
            self._cancel_typing_task(username)
            asyncio.create_task(self._broadcast_typing_status())

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            await connection.send_text(message)

    async def send_private_message(self, sender: str, receiver: str, message: str):
        for connection, username in self.active_connections.items():
            if username == receiver:
                await connection.send_text(f"Mensagem privada de {sender}: {message}")
                break

    async def typing_notification(self, username: str):
        # Cancelar task anterior se existir
        self._cancel_typing_task(username)
        
        # Adicionar usuário aos que estão digitando
        if username not in self.typing_users:
            self.typing_users.add(username)
            await self._broadcast_typing_status()
        
        # Criar task para remover após 3 segundos de inatividade
        self.typing_tasks[username] = asyncio.create_task(
            self._remove_typing_after_delay(username)
        )

    def _cancel_typing_task(self, username: str):
        if username in self.typing_tasks:
            self.typing_tasks[username].cancel()
            del self.typing_tasks[username]

    async def _remove_typing_after_delay(self, username: str, delay: int = 2):
        try:
            await asyncio.sleep(delay)
            if username in self.typing_users:
                self.typing_users.remove(username)
                await self._broadcast_typing_status()
        except asyncio.CancelledError:
            pass

    async def _broadcast_typing_status(self):
        if self.typing_users:
            users = ", ".join(self.typing_users)
            message = f"/typing:{users}"
        else:
            message = "/stop-typing"
        
        for connection in self.active_connections:
            await connection.send_text(message)