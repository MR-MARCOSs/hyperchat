from fastapi import FastAPI, HTTPException, WebSocket, File, UploadFile, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import os
from fastapi.websockets import WebSocketDisconnect
from server.database.userData import setup_database
from server.utils.auth import verificar_token
from server.websocket.manager import ConnectionManager
from server.database.database import save_message, get_last_messages
from server.routes import router 


app = FastAPI()
setup_database(app)
# Montar pasta de arquivos estáticos (CSS, JS, etc.)

app.include_router(router)
# Configurar pasta de templates
templates = Jinja2Templates(directory="templates")

app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    return templates.TemplateResponse("register.html", {"request": request})

@app.get("/login-page", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})


@app.get("/home", response_class=HTMLResponse)
async def get_home(request: Request):
    
    token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(status_code=401, detail="Token não encontrado.")

    # Remove o prefixo "Bearer " antes de verificar o token
    token = token.replace("Bearer ", "")
    payload = verificar_token(token)
    return templates.TemplateResponse("index.html", {"request": request})

manager = ConnectionManager()

@app.websocket("/ws/{username}")
async def websocket_endpoint(websocket: WebSocket, username: str):
    await manager.connect(websocket, username)
    await manager.broadcast(f"{username} entrou no chat.")
    
    # Enviar mensagens anteriores
    last_messages = await get_last_messages()
    for msg in reversed(last_messages):  # Exibe na ordem cronológica
        await websocket.send_text(f"[{msg['timestamp']}] {msg['username']}: {msg['content']}")

    try:
        while True:
            data = await websocket.receive_text()
            
            if data == "/typing":
                await manager.typing_notification(username)
                continue
            
            if username in manager.typing_users:
                manager.typing_users.remove(username)
                await manager._broadcast_typing_status()
            
            if data.startswith("@"):
                parts = data.split(" ", 2)
                if len(parts) >= 3:
                    receiver, private_msg = parts[1], parts[2]
                    await manager.send_private_message(username, receiver, private_msg)
                else:
                    await websocket.send_text("Formato inválido. Use: @destinatário mensagem")
            else:
                await save_message(username, data)
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