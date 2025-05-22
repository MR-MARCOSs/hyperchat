import traceback
from fastapi import APIRouter, HTTPException, Request
from asyncpg import Connection
import os
import asyncpg
from fastapi.responses import JSONResponse
from server.database.database import get_last_messages
from server.models.models import TokenResponse, UserCreate, UserLogin
from server.utils.auth import verificar_token
from server.utils.utils import create_access_token, hash_password, verify_password

router = APIRouter()

async def get_db_connection() -> Connection:
    return await asyncpg.connect(
        user=os.getenv("POSTGRES_USER", "myuser"),
        password=os.getenv("POSTGRES_PASSWORD", "mypassword"),
        database=os.getenv("POSTGRES_DB", "mydatabase"),
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=os.getenv("POSTGRES_PORT", "5432")
    )

@router.post("/users/")
async def create_user(user: UserCreate):
    conn = await get_db_connection()
    try:
        # Tenta inserir o usuário no banco
        hashed_password = hash_password(user.password)
        await conn.execute(
            "INSERT INTO users (username, password) VALUES ($1, $2)",
            user.username, hashed_password
        )
        return {"message": "Usuário criado com sucesso!"}
    except asyncpg.UniqueViolationError:
        raise HTTPException(status_code=400, detail="Usuário já existe.")
    except Exception as e:
        import traceback
        print("Erro no login:")
        traceback.print_exc()  # Mostra o stack trace no terminal
        raise HTTPException(status_code=500, detail=f"Erro interno: {str(e)}")

    finally:
        await conn.close()

@router.post("/login/", response_model=TokenResponse)
async def login(user: UserLogin):
    conn = await get_db_connection()
    try:
        # Busca o usuário no banco de dados
        user_data = await conn.fetchrow(
            "SELECT * FROM users WHERE username = $1", user.username
        )
        
        if not user_data or not verify_password(user.password, user_data["password"]):
            raise HTTPException(status_code=400, detail="Usuário ou senha incorretos.")
        
        # Gera o token
        token = create_access_token(data={"sub": user_data["username"]})
        
        # Define a resposta com o cookie
        response = JSONResponse(content={"message": "Login bem-sucedido."})
        response.set_cookie(key="access_token", value=f"Bearer {token}", httponly=True)
        return response
    
    except Exception as e:
        print("Erro durante o login:", traceback.format_exc())  # Adiciona logs detalhados
        raise HTTPException(status_code=500, detail="Erro interno ao fazer login.")
    
    finally:
        await conn.close()

@router.get("/users/me")
async def get_current_user(request: Request):
    token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(status_code=401, detail="Não autenticado")
    
    token = token.replace("Bearer ", "")
    payload = verificar_token(token)
    
    return {"username": payload.get("sub")}

@router.get("/users/search")
async def search_users(q: str, request: Request):
    # Verificar autenticação
    token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(status_code=401, detail="Não autenticado")
    
    token = token.replace("Bearer ", "")
    payload = verificar_token(token)  # <-- Assign the result here

    conn = await get_db_connection()
    try:
        users = await conn.fetch(
            "SELECT username FROM users WHERE username LIKE $1 AND username != $2 LIMIT 10",
            f"%{q}%", payload.get("sub")  # Now 'payload' is defined
        )
        return [dict(user) for user in users]
    finally:
        await conn.close()


@router.get("/messages")
async def get_messages(request: Request):
    # Verificar autenticação
    token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(status_code=401, detail="Não autenticado")
    
    token = token.replace("Bearer ", "")
    verificar_token(token)
    
    # Retornar últimas mensagens gerais
    return await get_last_messages()

@router.get("/messages/private")
async def get_private_messages(with_user: str, request: Request):
    # Verificar autenticação
    token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(status_code=401, detail="Não autenticado")
    
    token = token.replace("Bearer ", "")
    payload = verificar_token(token)
    current_user = payload.get("sub")
    
    conn = await get_db_connection()
    try:
        messages = await conn.fetch(
            """
            SELECT sender, content, timestamp 
            FROM private_messages 
            WHERE (sender = $1 AND receiver = $2) OR (sender = $2 AND receiver = $1)
            ORDER BY timestamp ASC
            LIMIT 100
            """,
            current_user, with_user
        )
        return [dict(msg) for msg in messages]
    finally:
        await conn.close()

@router.get("/users/contacts")
async def get_user_contacts(request: Request):
    # Verificar autenticação
    token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(status_code=401, detail="Não autenticado")
    
    token = token.replace("Bearer ", "")
    payload = verificar_token(token)
    current_user = payload.get("sub")
    
    conn = await get_db_connection()
    try:
        # Buscar usuários com quem já trocou mensagens
        contacts = await conn.fetch(
            """
            SELECT DISTINCT 
                CASE 
                    WHEN sender = $1 THEN receiver 
                    ELSE sender 
                END as username
            FROM private_messages
            WHERE sender = $1 OR receiver = $1
            """,
            current_user
        )
        return [dict(contact) for contact in contacts]
    finally:
        await conn.close()

@router.post("/logout")
async def logout():
    response = JSONResponse(content={"message": "Logout bem-sucedido"})
    response.delete_cookie("access_token")
    return response