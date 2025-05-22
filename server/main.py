from typing import List
import asyncpg
from fastapi import FastAPI, HTTPException, Query, WebSocket, File, UploadFile, Request, Depends
from fastapi.responses import HTMLResponse, JSONResponse # Import JSONResponse7
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import os
import json # Importar json7
import datetime # Importar datetime7
import traceback # Importar traceback7

from fastapi.websockets import WebSocketDisconnect
# Importar funções do database e manager7
from server.database.userData import setup_database
# Importar get_db_connection e funções de salvar/buscar mensagens7
from server.database.database import get_db_connection, save_message, get_last_messages, save_private_message, get_user_id_by_username
from server.utils.auth import verificar_token
from server.websocket.manager import ConnectionManager
from server.routes import router

# Initialize FastAPI app7
app = FastAPI()

# Setup database (assuming this creates tables if they don't exist)7
setup_database(app) # Assuming this function exists and works7

# Mount static files (CSS, JS, etc.)7
app.mount("/static", StaticFiles(directory="static"), name="static")

# Directory for uploaded files7
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True) # Ensure the directory exists7
# Mount the uploads directory to serve files7
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")


# Configure templates7
templates = Jinja2Templates(directory="templates")

# Include the router from routes.py7
app.include_router(router)


# --- HTTP Routes ---7

@app.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    return templates.TemplateResponse("register.html", {"request": request})

@app.get("/login-page", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.get("/home", response_class=HTMLResponse)
async def get_home(request: Request):
    token = request.cookies.get("access_token")

    # If no token, redirect to login page7
    if not token:
        # Use TemplateResponse to render login.html7
        return templates.TemplateResponse("login.html", {"request": request})

    try:
        # Remove "Bearer " prefix7
        token = token.replace("Bearer ", "")
        # Verify token - this function should raise exception if invalid/expired7
        payload = verificar_token(token)
        # If token is valid, render home page7
        return templates.TemplateResponse("index.html", {"request": request})

    except Exception as e:
        # If token verification fails (invalid, expired, etc.), print error and redirect to login7
        print(f"Token verification failed for /home: {e}")
        # Use TemplateResponse to render login.html7
        return templates.TemplateResponse("login.html", {"request": request})


# --- WebSocket Manager Instance ---7
manager = ConnectionManager()


# --- WebSocket Endpoint (Consolidated) ---7

@app.websocket("/ws/{username}")
async def websocket_endpoint(websocket: WebSocket, username: str):
    # Optional: Verify token here as well, or rely on the HTTP /home check7
    # If the user refreshed or navigated directly, this might be the first check.7
    # You'd need to access the cookie here too.7
    # For simplicity in this example, we rely on the /home check first,7
    # but a more robust app might require re-auth via WS or a short-lived token.7
    # For now, let's assume the user accessing /home was already authenticated.7

    # Connect the user via the manager7
    await manager.connect(websocket, username)
    print(f"WebSocket connected: {username}")

    # Send a broadcast notification that user joined (plain text)7
    await manager.broadcast(f"{username} entrou no chat.")

    # Optional: Send general chat history here on initial connection7
    # This is redundant if loadGeneralChat in JS fetches via REST,7
    # but can provide initial messages faster.7
    # last_messages = await get_last_messages()7
    # for msg in reversed(last_messages):7
    #      # Ensure format matches frontend text parsing7
    #     await websocket.send_text(f"[{msg['timestamp']}] {msg['username']}: {msg['content']}")7


    try:
        # Main loop to receive messages from this WebSocket7
        while True:
            data = await websocket.receive_text()
            # print(f"Received from {username}: {data}") # Debug print7

            try:
                # --- Attempt to parse as JSON ---7
                message = json.loads(data)
                # print(f"Parsed JSON message from {username}: {message}") # Debug7

                message_type = message.get('type')

                # --- Handle Private Text Message ---7
                if message_type == 'private' and message.get('recipient') and message.get('content') is not None:
                    recipient_username = message['recipient']
                    content = str(message['content']) # Ensure content is string7

                    # Save the message to the private messages table7
                    save_success = await save_private_message(username, recipient_username, content=content, message_type='text')

                    if save_success:
                         # Get the timestamp from the database insertion (better than local time)7
                         # Or just use current time if DB doesn't return it easily on INSERT7
                         timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat() # Use ISO format for JS7

                         # Prepare message in JSON format for sending via WS7
                         ws_message = {
                             "type": "private",
                             "sender": username,
                             "receiver": recipient_username,
                             "content": content,
                             "timestamp": timestamp
                         }
                         ws_message_json = json.dumps(ws_message)

                         # Send to the sender's WebSocket (so they see their own message)7
                         await manager.send_personal_message(ws_message_json, websocket)

                         # Find recipient's WebSocket and send the message7
                         recipient_ws = manager.get_websocket_by_username(recipient_username)
                         if recipient_ws:
                             await manager.send_personal_message(ws_message_json, recipient_ws)
                             # print(f"Sent private text message from {username} to {recipient_username}") # Debug7
                         else:
                             # Optional: Notify sender if recipient is offline7
                             await manager.send_personal_message(f"Usuário '{recipient_username}' está offline.", websocket)
                             # print(f"Recipient {recipient_username} is offline, cannot send private message.") # Debug7

                    else:
                         # save_private_message returned False (user not found or DB error)7
                         await manager.send_personal_message("Erro ao enviar mensagem privada. Usuário pode não existir ou erro interno.", websocket)
                         print(f"Failed to save/send private message from {username} to {recipient_username}")


                # --- Handle File Message (JSON sent by frontend AFTER upload) ---7
                # The frontend sends this JSON after a successful HTTP /upload/7
                elif message_type == 'file' and message.get('filename') and message.get('path'):
                    recipient_username = message.get('receiver') # Could be null for general chat7
                    filename = message['filename']
                    file_path = message['path'] # This should be the public path, e.g., /uploads/filename.ext7

                    # Determine if it's a general or private file7
                    is_general_file = (recipient_username is None or recipient_username == 'general')

                    if is_general_file:
                        # --- General File Message ---7
                        # Save information about the file in the general chat history7
                        # You might need to adapt save_message or create a new function7
                        # For simplicity, let's save a text message indicating the file7
                        # IDEAL: Adapt 'messages' table to support file type or create a new general_files table7
                         content_text = f"Arquivo '{filename}' enviado. Disponível em: {file_path}"
                         await save_message(username, content_text) # Saves to general messages table7

                         # Broadcast the file message in JSON format to all connected users7
                         timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
                         ws_message = {
                             "type": "file",
                             "sender": username,
                             "receiver": None, # Indicate general chat7
                             "filename": filename,
                             "path": file_path,
                             "timestamp": timestamp
                         }
                         await manager.broadcast(json.dumps(ws_message))
                         # print(f"Broadcasted general file from {username}: {filename}") # Debug7


                    elif recipient_username:
                        # --- Private File Message ---7
                        # Save to the private messages table with type 'file'7
                        save_success = await save_private_message(
                            sender_username=username,
                            recipient_username=recipient_username,
                            content=f"Arquivo: {filename}", # Optional text content for DB7
                            message_type='file',
                            filename=filename,
                            file_path=file_path
                        )

                        if save_success:
                            timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
                            ws_message = {
                                "type": "file", # Type for the frontend7
                                "sender": username,
                                "receiver": recipient_username,
                                "filename": filename,
                                "path": file_path, # Public path7
                                "timestamp": timestamp
                            }
                            ws_message_json = json.dumps(ws_message)

                            # Send to sender and recipient7
                            await manager.send_personal_message(ws_message_json, websocket)
                            recipient_ws = manager.get_websocket_by_username(recipient_username)
                            if recipient_ws:
                                await manager.send_personal_message(ws_message_json, recipient_ws)
                                # print(f"Sent private file message from {username} to {recipient_username}: {filename}") # Debug7
                            else:
                                await manager.send_personal_message(f"Usuário '{recipient_username}' está offline.", websocket)
                                # print(f"Recipient {recipient_username} is offline for file message.") # Debug7
                        else:
                             await manager.send_personal_message("Erro ao enviar arquivo privado. Usuário pode não existir ou erro interno.", websocket)
                             print(f"Failed to save/send private file from {username} to {recipient_username}")

                    else:
                        print(f"Mensagem de arquivo JSON com receiver inválido/ausente de {username}: {message}")
                        await manager.send_personal_message("Erro no formato da mensagem de arquivo.", websocket)


                # --- Handle Private Typing Notification (Optional JSON) ---7
                # If frontend also sends JSON like { type: 'typing_private', recipient: 'user', status: true }7
                # elif message_type == 'typing_private' and message.get('recipient') and message.get('status') is not None:7
                #      recipient_username = message['recipient']7
                #      status = bool(message['status'])7
                #      await manager.notify_typing_private(username, recipient_username, status) # Needs implementation in Manager7
                #      print(f"{username} is typing private to {recipient_username}: {status}") # Debug7


                # --- Handle Unknown JSON Type ---7
                else:
                    print(f"Mensagem JSON de tipo desconhecido recebida de {username}: {message}")
                    await manager.send_personal_message("Formato de mensagem desconhecido.", websocket)


            except json.JSONDecodeError:
                # --- Handle Plain Text (General Chat or Commands) ---7
                # print(f"Received plain text from {username}: {data}") # Debug7

                # Handle /typing command for general chat7
                if data == "/typing":
                    await manager.typing_notification(username) # Manager broadcasts "X está digitando..."7
                    # print(f"{username} sent /typing command.") # Debug7
                    # No need to save or broadcast /typing itself as a chat message7
                    continue # Go to the next message7


                # Handle /stop-typing command (if frontend sends it explicitly)7
                # elif data == "/stop-typing":7
                #      # Remove user from typing list directly and broadcast status7
                #      if username in manager.typing_users:7
                #          manager.typing_users.remove(username)7
                #          manager._cancel_typing_task(username) # Cancel any pending timeout task7
                #          await manager._broadcast_typing_status()7
                #      continue7


                # If it's not a known command or JSON, treat as a general text message7
                content = data.strip() # Remove leading/trailing whitespace7
                if content: # Only process non-empty messages7
                    # Save the general text message to the general messages table7
                    await save_message(username, content)
                    # print(f"Saved general text message from {username}.") # Debug7

                    # Broadcast the general message to all connected users (as plain text)7
                    # Format the message as the frontend expects for general chat history/updates7
                    timestamp = datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%d %H:%M:%S') # Format as your previous timestamp7
                    broadcast_message_text = f"[{timestamp}] {username}: {content}"
                    await manager.broadcast(broadcast_message_text)
                    # print(f"Broadcasted general text message from {username}.") # Debug7
                else:
                     # print(f"Received empty plain text message from {username}. Ignoring.") # Debug7
                     pass # Ignore empty messages7


            except WebSocketDisconnect:
                 # This exception is caught by the main outer block7
                raise # Re-raise to be caught outside the while loop7


            except Exception as e:
                # Catch any other unexpected errors during message processing7
                print(f"Erro durante o processamento da mensagem WS de {username}: {e}")
                traceback.print_exc() # Print the full traceback for debugging7
                # Attempt to send an error message back to the user7
                try:
                    await manager.send_personal_message(f"Erro interno do servidor ao processar sua mensagem: {e}", websocket)
                except:
                    # If sending error message fails, just pass7
                    pass


    except WebSocketDisconnect:
        # This block is reached when the WebSocket connection is closed7
        # The disconnect method in manager removes the user7
        disconnected_username = manager.active_connections.get(websocket, username) # Get username before removing7
        manager.disconnect(websocket)
        print(f"WebSocket disconnected: {disconnected_username}")
        # Broadcast a message that user left (plain text)7
        await manager.broadcast(f"{disconnected_username} saiu do chat.")

    except Exception as e:
        # Catch any unexpected errors outside the message processing loop7
        print(f"Erro inesperado na conexão WS de {username}: {e}")
        traceback.print_exc()
        # Ensure user is disconnected by the manager in case of error7
        manager.disconnect(websocket)
        try:
             await websocket.close(code=1011) # Internal Error7
        except:
             pass # WebSocket might already be closed7


# --- Remove the old private chat WS endpoint ---7
# @app.websocket("/private/{user1}/{user2}")7
# async def private_chat_endpoint(websocket: WebSocket, user1: str, user2: str):7
#     # This endpoint is now deprecated and removed7
#     pass7

# ... your other endpoints like /users/search and /upload/ which are included via router ...7

# The /users/search and /upload/ endpoints are already defined in your routes.py7
# and main.py respectively, and included via app.include_router(router) or defined directly.7
# Ensure the /users/search in routes.py returns [{'username': '...'}] format.7
# Ensure the /upload/ in main.py saves files and returns {'filename': '...'} format.7