from fastapi import FastAPI, WebSocket
from fastapi.websockets import WebSocketDisconnect
from server.websocket.manager import ConnectionManager

app = FastAPI()

@app.get("/")
async def home():
    return {"message": "HyperChat está no ar!"}

manager = ConnectionManager()

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            await manager.broadcast(f"Nova mensagem: {data}")
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        await manager.broadcast("Um usuário saiu do chat.")
