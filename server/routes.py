import json
import traceback
from fastapi import APIRouter, HTTPException, Request, Query
import os
import asyncpg
from fastapi.responses import JSONResponse

# Import your database and utility functions
from server.database.database import (
    get_last_messages,
    get_user_id_by_username,
    save_private_message,
    get_private_messages_history,
    get_user_contacts_from_db,
    get_db_connection,
)

from server.models.models import TokenResponse, UserCreate, UserLogin
from server.utils.auth import verificar_token
from server.utils.utils import create_access_token, hash_password, verify_password

router = APIRouter()

# ✅ Helper to extract authenticated username or raise HTTPException
async def get_authenticated_username(request: Request) -> str:
    auth_response = await get_current_user(request)
    if isinstance(auth_response, JSONResponse):
        raise HTTPException(status_code=auth_response.status_code, detail=auth_response.body.decode())

    username = auth_response.get("username")
    if not username:
        raise HTTPException(status_code=500, detail="Erro interno ao obter nome de usuário autenticado.")
    return username


@router.post("/users/")
async def create_user(user: UserCreate):
    conn = await get_db_connection()
    try:
        hashed_password = hash_password(user.password)
        await conn.execute(
            "INSERT INTO users (username, password) VALUES ($1, $2)",
            user.username, hashed_password
        )
        return {"message": "Usuário criado com sucesso!"}
    except asyncpg.UniqueViolationError:
        raise HTTPException(status_code=400, detail="Usuário já existe.")
    except Exception as e:
        print("Erro na criação de usuário:")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Erro interno: {str(e)}")
    finally:
        await conn.close()


@router.post("/login/", response_model=TokenResponse)
async def login(user: UserLogin):
    conn = await get_db_connection()
    try:
        user_data = await conn.fetchrow(
            "SELECT * FROM users WHERE username = $1", user.username
        )

        if not user_data or not verify_password(user.password, user_data["password"]):
            raise HTTPException(status_code=400, detail="Usuário ou senha incorretos.")

        token = create_access_token(data={"sub": user_data["username"]})
        response = JSONResponse(content={"message": "Login bem-sucedido."})
        response.set_cookie(key="access_token", value=f"Bearer {token}", httponly=True)
        return response
    except Exception as e:
        print("Erro durante o login:", traceback.format_exc())
        raise HTTPException(status_code=500, detail="Erro interno ao fazer login.")
    finally:
        await conn.close()


@router.get("/users/me")
async def get_current_user(request: Request):
    token = request.cookies.get("access_token")
    if not token:
        return JSONResponse(status_code=401, content={"detail": "Não autenticado"})

    try:
        token = token.replace("Bearer ", "")
        payload = verificar_token(token)
        return {"username": payload.get("sub")}
    except Exception as e:
        print(f"Erro na verificação do token em /users/me: {e}")
        return JSONResponse(status_code=401, content={"detail": "Token inválido ou expirado"})


@router.get("/users/search")
async def search_users(q: str = Query(..., min_length=2, max_length=50), request: Request = None):
    current_username = await get_authenticated_username(request)

    conn = await get_db_connection()
    try:
        users = await conn.fetch(
            "SELECT username FROM users WHERE username ILIKE $1 AND username != $2 LIMIT 10",
            f"{q}%", current_username
        )
        return [dict(user) for user in users]
    finally:
        await conn.close()


@router.get("/messages")
async def get_messages(request: Request):
    await get_authenticated_username(request)
    return await get_last_messages()


@router.get("/messages/private")
async def get_private_messages(with_user: str = Query(..., min_length=1), request: Request = None):
    current_username = await get_authenticated_username(request)

    messages = await get_private_messages_history(current_username, with_user)

    if not messages and not await get_user_id_by_username(with_user):
        raise HTTPException(status_code=404, detail=f"Usuário '{with_user}' não encontrado.")

    return messages


@router.get("/users/contacts")
async def get_user_contacts(request: Request):
    current_username = await get_authenticated_username(request)
    return await get_user_contacts_from_db(current_username)


@router.post("/logout")
async def logout():
    response = JSONResponse(content={"message": "Logout bem-sucedido"})
    response.delete_cookie("access_token")
    return response
