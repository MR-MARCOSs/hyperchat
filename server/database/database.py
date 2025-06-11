import asyncpg
import os
from datetime import datetime, timezone

async def get_db_connection(): 
    return await asyncpg.connect(
        user=os.getenv("POSTGRES_USER", "myuser"),
        password=os.getenv("POSTGRES_PASSWORD", "mypassword"),
        database=os.getenv("POSTGRES_DB", "mydatabase"),
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=os.getenv("POSTGRES_PORT", "5432")
    )


async def get_user_id_by_username(username: str):
    conn = await get_db_connection()
    try:
        user_id = await conn.fetchval("SELECT id FROM users WHERE username = $1", username)
        return user_id
    finally:
        await conn.close()


async def get_username_by_user_id(user_id: int):
    conn = await get_db_connection()
    try:
        username = await conn.fetchval("SELECT username FROM users WHERE id = $1", user_id)
        return username
    finally:
        await conn.close()



async def save_message(username: str, content: str):
    conn = await get_db_connection()
    try:
        
        
        await conn.execute(
            "INSERT INTO messages (username, content) VALUES ($1, $2)", 
            username, content
        )
    except Exception as e:
        print(f"Erro ao salvar mensagem geral: {e}")
    finally:
        await conn.close()


async def get_last_messages(limit: int = 10):
    conn = await get_db_connection()
    try:
        
        rows = await conn.fetch(
            "SELECT username, content, timestamp FROM messages ORDER BY timestamp DESC LIMIT $1",
            limit
        )
        
        return [dict(row) for row in rows]
    except Exception as e:
        print(f"Erro ao buscar mensagens gerais: {e}")
        return []
    finally:
        await conn.close()



async def save_private_message(sender_username: str, recipient_username: str, content: str = None, message_type: str = 'text', filename: str = None, file_path: str = None):
    conn = await get_db_connection()
    try:
        sender_id = await get_user_id_by_username(sender_username)
        recipient_id = await get_user_id_by_username(recipient_username)

        if sender_id is None or recipient_id is None:
            print(f"Erro: Remetente '{sender_username}' ou Destinatário '{recipient_username}' não encontrado no banco.")
            return False 

        
        if message_type == 'file':
             content = content if content is not None else f"Arquivo: {filename}"


        await conn.execute(
            """
            INSERT INTO private_messages (sender_id, recipient_id, content, type, filename, file_path)
            VALUES ($1, $2, $3, $4, $5, $6)
            """,
            sender_id, recipient_id, content, message_type, filename, file_path
        )
        
        return True
    except Exception as e:
        print(f"Erro ao salvar mensagem privada: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        await conn.close()



async def get_private_messages_history(user1_username: str, user2_username: str, limit: int = 100):
    conn = await get_db_connection()
    try:
        user1_id = await get_user_id_by_username(user1_username)
        user2_id = await get_user_id_by_username(user2_username)

        if user1_id is None or user2_id is None:
            print(f"Erro: Usuário '{user1_username}' ou '{user2_username}' não encontrado para histórico privado.")
            return []

        rows = await conn.fetch(
            """
            SELECT sender_id, content, timestamp, type, filename, file_path
            FROM private_messages
            WHERE (sender_id = $1 AND recipient_id = $2) OR (sender_id = $2 AND recipient_id = $1)
            ORDER BY timestamp ASC
            LIMIT $3
            """,
            user1_id, user2_id, limit
        )

        
        messages_with_username = []
        
        username_cache = {}
        if user1_id: username_cache[user1_id] = user1_username
        if user2_id: username_cache[user2_id] = user2_username


        for row in rows:
            sender_id = row['sender_id']
            
            if sender_id not in username_cache:
                 username_cache[sender_id] = await get_username_by_user_id(sender_id)

            message_data = dict(row)
            message_data['sender'] = username_cache.get(sender_id, 'Desconhecido') 
            
            del message_data['sender_id']
            
            
            

            messages_with_username.append(message_data)

        return messages_with_username

    except Exception as e:
        print(f"Erro ao buscar histórico de mensagens privadas: {e}")
        import traceback
        traceback.print_exc()
        return []
    finally:
        if conn: await conn.close()



async def get_user_contacts_from_db(current_username: str):
    conn = await get_db_connection()
    try:
        current_user_id = await get_user_id_by_username(current_username)
        if current_user_id is None:
             print(f"Erro: Usuário '{current_username}' não encontrado para buscar contatos.")
             return []

        
        rows = await conn.fetch(
            """
            SELECT DISTINCT 
                CASE 
                    WHEN sender_id = $1 THEN recipient_id 
                    ELSE sender_id 
                END as contact_id
            FROM private_messages
            WHERE sender_id = $1 OR recipient_id = $1
            """,
            current_user_id
        )

        
        contact_usernames = []
        for row in rows:
            contact_id = row['contact_id']
            if contact_id: 
                username = await get_username_by_user_id(contact_id)
                if username and username != current_username: 
                    contact_usernames.append({"username": username})

        return contact_usernames
    except Exception as e:
        print(f"Erro ao buscar contatos do usuário: {e}")
        import traceback
        traceback.print_exc()
        return []
    finally:
        if conn: await conn.close()