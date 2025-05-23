from fastapi import FastAPI, WebSocket, Request
from fastapi.responses import HTMLResponse 
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import os
import json 
import datetime 
import traceback 

from fastapi.websockets import WebSocketDisconnect
from server.database.userData import setup_database
from server.database.database import get_db_connection, save_message, get_last_messages, save_private_message, get_user_id_by_username
from server.utils.auth import verificar_token
from server.websocket.manager import ConnectionManager
from server.routes import router

app = FastAPI()
setup_database(app) 

app.mount("/static", StaticFiles(directory="static"), name="static")
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True) 
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")

templates = Jinja2Templates(directory="templates")
app.include_router(router)

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
        return templates.TemplateResponse("login.html", {"request": request})
    
    try:
        token = token.replace("Bearer ", "")
        payload = verificar_token(token)
        return templates.TemplateResponse("index.html", {"request": request})

    except Exception as e:
        print(f"Token verification failed for /home: {e}")
        return templates.TemplateResponse("login.html", {"request": request})

manager = ConnectionManager()

@app.websocket("/ws/{username}")
async def websocket_endpoint(websocket: WebSocket, username: str):

    await manager.connect(websocket, username)
    print(f"WebSocket connected: {username}")
    await manager.broadcast(f"{username} entrou no chat.")

    try:
        while True:
            data = await websocket.receive_text()

            try:
                message = json.loads(data)
                message_type = message.get('type')

                if message_type == 'private' and message.get('recipient') and message.get('content') is not None:
                    recipient_username = message['recipient']
                    content = str(message['content'])   
                    save_success = await save_private_message(username, recipient_username, content=content, message_type='text')

                    if save_success:                        
                         timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()  
                         ws_message = {
                             "type": "private",
                             "sender": username,
                             "receiver": recipient_username,
                             "content": content,
                             "timestamp": timestamp
                         }
                         ws_message_json = json.dumps(ws_message)
                         await manager.send_personal_message(ws_message_json, websocket)
                         recipient_ws = manager.get_websocket_by_username(recipient_username)
                         if recipient_ws:
                             await manager.send_personal_message(ws_message_json, recipient_ws)
                         else:
                             await manager.send_personal_message(f"Usuário '{recipient_username}' está offline.", websocket)
                    else: 
                         await manager.send_personal_message("Erro ao enviar mensagem privada. Usuário pode não existir ou erro interno.", websocket)
                         print(f"Failed to save/send private message from {username} to {recipient_username}")

                elif message_type == 'file' and message.get('filename') and message.get('path'):
                    recipient_username = message.get('receiver') 
                    filename = message['filename']
                    file_path = message['path']   
                    is_general_file = (recipient_username is None or recipient_username == 'general')

                    if is_general_file:
                         content_text = f"Arquivo '{filename}' enviado. Disponível em: {file_path}"
                         await save_message(username, content_text) 
           
                         timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
                         ws_message = {
                             "type": "file",
                             "sender": username,
                             "receiver": None, 
                             "filename": filename,
                             "path": file_path,
                             "timestamp": timestamp
                         }
                         await manager.broadcast(json.dumps(ws_message))

                    elif recipient_username:
                        save_success = await save_private_message(
                            sender_username=username,
                            recipient_username=recipient_username,
                            content=f"Arquivo: {filename}", 
                            message_type='file',
                            filename=filename,
                            file_path=file_path
                        )

                        if save_success:
                            timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
                            ws_message = {
                                "type": "file", 
                                "sender": username,
                                "receiver": recipient_username,
                                "filename": filename,
                                "path": file_path, 
                                "timestamp": timestamp
                            }
                            ws_message_json = json.dumps(ws_message)

                            await manager.send_personal_message(ws_message_json, websocket)
                            recipient_ws = manager.get_websocket_by_username(recipient_username)
                            if recipient_ws:
                                await manager.send_personal_message(ws_message_json, recipient_ws)
                            else:
                                await manager.send_personal_message(f"Usuário '{recipient_username}' está offline.", websocket)  
                        else:
                             await manager.send_personal_message("Erro ao enviar arquivo privado. Usuário pode não existir ou erro interno.", websocket)
                             print(f"Failed to save/send private file from {username} to {recipient_username}")

                    else:
                        print(f"Mensagem de arquivo JSON com receiver inválido/ausente de {username}: {message}")
                        await manager.send_personal_message("Erro no formato da mensagem de arquivo.", websocket)
                
                else:
                    print(f"Mensagem JSON de tipo desconhecido recebida de {username}: {message}")
                    await manager.send_personal_message("Formato de mensagem desconhecido.", websocket)

            except json.JSONDecodeError: 
                if data == "/typing":
                    await manager.typing_notification(username) 
                    continue 

                content = data.strip() 
                if content: 
                    await save_message(username, content)
                    timestamp = datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%d %H:%M:%S') 
                    broadcast_message_text = f"[{timestamp}] {username}: {content}"
                    await manager.broadcast(broadcast_message_text)
                    
                else:
                     pass 
            except WebSocketDisconnect:
                raise 
            except Exception as e:
                print(f"Erro durante o processamento da mensagem WS de {username}: {e}")
                traceback.print_exc() 
                try:
                    await manager.send_personal_message(f"Erro interno do servidor ao processar sua mensagem: {e}", websocket)
                except:
                    pass

    except WebSocketDisconnect:
        disconnected_username = manager.active_connections.get(websocket, username) 
        manager.disconnect(websocket)
        print(f"WebSocket disconnected: {disconnected_username}")
        await manager.broadcast(f"{disconnected_username} saiu do chat.")
    except Exception as e:
        print(f"Erro inesperado na conexão WS de {username}: {e}")
        traceback.print_exc()
        manager.disconnect(websocket)
        try:
             await websocket.close(code=1011) 
        except:
             pass 













