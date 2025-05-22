import asyncpg
import os
# Importar datetime para usar no timestamp das mensagens salvas
from datetime import datetime, timezone

async def get_db_connection(): # Mova esta função para database.py para centralizar
    return await asyncpg.connect(
        user=os.getenv("POSTGRES_USER", "myuser"),
        password=os.getenv("POSTGRES_PASSWORD", "mypassword"),
        database=os.getenv("POSTGRES_DB", "mydatabase"),
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=os.getenv("POSTGRES_PORT", "5432")
    )

# Função para buscar ID do usuário pelo nome
async def get_user_id_by_username(username: str):
    conn = await get_db_connection()
    try:
        user_id = await conn.fetchval("SELECT id FROM users WHERE username = $1", username)
        return user_id
    finally:
        await conn.close()

# Função para buscar nome do usuário pelo ID
async def get_username_by_user_id(user_id: int):
    conn = await get_db_connection()
    try:
        username = await conn.fetchval("SELECT username FROM users WHERE id = $1", user_id)
        return username
    finally:
        await conn.close()


# Função para salvar mensagens gerais
async def save_message(username: str, content: str):
    conn = await get_db_connection()
    try:
        # Optional: Get user_id if you want to link general messages to users table
        # user_id = await get_user_id_by_username(username)
        await conn.execute(
            "INSERT INTO messages (username, content) VALUES ($1, $2)", # Assuming 'messages' table has username, content, timestamp
            username, content
        )
    except Exception as e:
        print(f"Erro ao salvar mensagem geral: {e}")
    finally:
        await conn.close()

# Função para buscar mensagens gerais
async def get_last_messages(limit: int = 10):
    conn = await get_db_connection()
    try:
        # Ensure columns match your 'messages' table and the frontend expects: username, content, timestamp
        rows = await conn.fetch(
            "SELECT username, content, timestamp FROM messages ORDER BY timestamp DESC LIMIT $1",
            limit
        )
        # Convert rows to list of dicts if necessary (fetch returns list of asyncpg.Record)
        return [dict(row) for row in rows]
    except Exception as e:
        print(f"Erro ao buscar mensagens gerais: {e}")
        return []
    finally:
        await conn.close()


# Função para salvar mensagens privadas (texto ou arquivo)
async def save_private_message(sender_username: str, recipient_username: str, content: str = None, message_type: str = 'text', filename: str = None, file_path: str = None):
    conn = await get_db_connection()
    try:
        sender_id = await get_user_id_by_username(sender_username)
        recipient_id = await get_user_id_by_username(recipient_username)

        if sender_id is None or recipient_id is None:
            print(f"Erro: Remetente '{sender_username}' ou Destinatário '{recipient_username}' não encontrado no banco.")
            return False # Falhou ao encontrar usuários

        # Se for tipo 'file', o content pode ser uma descrição padrão ou null, filename e file_path são essenciais
        if message_type == 'file':
             content = content if content is not None else f"Arquivo: {filename}"


        await conn.execute(
            """
            INSERT INTO private_messages (sender_id, recipient_id, content, type, filename, file_path)
            VALUES ($1, $2, $3, $4, $5, $6)
            """,
            sender_id, recipient_id, content, message_type, filename, file_path
        )
        # print(f"Mensagem privada salva: de {sender_username} para {recipient_username}, Tipo: {message_type}")
        return True
    except Exception as e:
        print(f"Erro ao salvar mensagem privada: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        await conn.close()

# Função para buscar histórico de mensagens privadas
# Usada pelo endpoint REST /messages/private
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

        # Precisa retornar o sender_username, não o ID, para o frontend
        messages_with_username = []
        # Cache usernames to avoid repeated DB lookups for the same ID
        username_cache = {}
        if user1_id: username_cache[user1_id] = user1_username
        if user2_id: username_cache[user2_id] = user2_username


        for row in rows:
            sender_id = row['sender_id']
            # Use cache or fetch if not in cache
            if sender_id not in username_cache:
                 username_cache[sender_id] = await get_username_by_user_id(sender_id)

            message_data = dict(row)
            message_data['sender'] = username_cache.get(sender_id, 'Desconhecido') # Add sender username
            # Remove sender_id as frontend expects 'sender'
            del message_data['sender_id']
            # Optional: Add receiver_id or receiver_username if needed on frontend
            # message_data['receiver_id'] = row['recipient_id']
            # message_data['receiver'] = username_cache.get(row['recipient_id'], 'Desconhecido') # Add receiver username

            messages_with_username.append(message_data)

        return messages_with_username

    except Exception as e:
        print(f"Erro ao buscar histórico de mensagens privadas: {e}")
        import traceback
        traceback.print_exc()
        return []
    finally:
        if conn: await conn.close()

# Função para buscar contatos com quem o usuário já conversou
# Usada pelo endpoint REST /users/contacts
async def get_user_contacts_from_db(current_username: str):
    conn = await get_db_connection()
    try:
        current_user_id = await get_user_id_by_username(current_username)
        if current_user_id is None:
             print(f"Erro: Usuário '{current_username}' não encontrado para buscar contatos.")
             return []

        # SQL to find distinct user IDs who were either sender or recipient with the current user
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

        # Get usernames for the contact IDs
        contact_usernames = []
        for row in rows:
            contact_id = row['contact_id']
            if contact_id: # Ensure contact_id is not None
                username = await get_username_by_user_id(contact_id)
                if username and username != current_username: # Don't include self
                    contact_usernames.append({"username": username})

        return contact_usernames
    except Exception as e:
        print(f"Erro ao buscar contatos do usuário: {e}")
        import traceback
        traceback.print_exc()
        return []
    finally:
        if conn: await conn.close()