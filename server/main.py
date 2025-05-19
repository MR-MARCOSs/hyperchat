from fastapi import FastAPI, WebSocket, File, UploadFile
import os
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
            if data == "/typing":
                await manager.typing_notification(username)

            
            if data.startswith("@"):  # Mensagem privada
                parts = data.split(" ", 2)
                if len(parts) >= 3:
                    receiver, private_msg = parts[1], parts[2]
                    await manager.send_private_message(username, receiver, private_msg)
                else:
                    await websocket.send_text("Formato inválido. Use: @destinatario mensagem")
            else:  # Mensagem pública
                save_message(username, data)
                await manager.broadcast(f"{username}: {data}")
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        await manager.broadcast(f"{username} saiu do chat.")

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@app.post("/upload/")
async def upload_file(file: UploadFile = File(...)):
    file_path = os.path.join(UPLOAD_DIR, file.filename)
    with open(file_path, "wb") as f:
        f.write(await file.read())
    return {"filename": file.filename, "message": "Arquivo enviado com sucesso!"}