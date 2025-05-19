from fastapi import FastAPI, WebSocket
from fastapi.websockets import WebSocketDisconnect
from server.websocket.manager import ConnectionManager
from server.database.database import save_message, get_last_messages

app = FastAPI()

@app.get("/")
async def home():
    return {"message": "HyperChat está no ar!"}

manager = ConnectionManager()

@app.websocket("/ws/{username}")
async def websocket_endpoint(websocket: WebSocket, username: str):
    await manager.connect(websocket, username)
    await manager.broadcast(f"{username} entrou no chat.")
    # Enviar mensagens anteriores ao usuário conectado
    last_messages = get_last_messages()
    for msg in reversed(last_messages):  # Reverter para ordem cronológica
        await websocket.send_text(f"[{msg[2]}] {msg[0]}: {msg[1]}")

    try:
        while True:
            data = await websocket.receive_text()
            save_message(username, data)  # Salvar no banco
            await manager.broadcast(f"{username}: {data}")
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        await manager.broadcast(f"{username} saiu do chat.")

