from fastapi import FastAPI, WebSocket, File, UploadFile, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import os
from fastapi.websockets import WebSocketDisconnect
from server.websocket.manager import ConnectionManager
from server.database.database import save_message, get_last_messages

app = FastAPI()

# Montar pasta de arquivos estáticos (CSS, JS, etc.)
app.mount("/static", StaticFiles(directory="static"), name="static")

# Configurar pasta de templates
templates = Jinja2Templates(directory="templates")

@app.get("/", response_class=HTMLResponse)
async def get_home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

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
            
            # Tratar notificação de digitação
            if data == "/typing":
                await manager.typing_notification(username)
                continue
            
            # Quando enviar mensagem real, parar de mostrar "digitando"
            if username in manager.typing_users:
                manager.typing_users.remove(username)
                await manager._broadcast_typing_status()
            
            if data.startswith("@"):  # Mensagem privada
                parts = data.split(" ", 2)
                if len(parts) >= 3:
                    receiver, private_msg = parts[1], parts[2]
                    await manager.send_private_message(username, receiver, private_msg)
                else:
                    await websocket.send_text("Formato inválido. Use: @destinatário mensagem")
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