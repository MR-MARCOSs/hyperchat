import os
import asyncpg
from fastapi import FastAPI

async def create_user_table():
    conn = None
    try:
        conn = await asyncpg.connect(
            user=os.getenv("POSTGRES_USER", "myuser"),
            password=os.getenv("POSTGRES_PASSWORD", "mypassword"),
            database=os.getenv("POSTGRES_DB", "mydatabase"),
            host=os.getenv("POSTGRES_HOST", "localhost"),
            port=os.getenv("POSTGRES_PORT", "5432")
        )
        
        table_exists = await conn.fetchval(
            "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'users')"
        )
        
        if not table_exists:
            await conn.execute('''
                CREATE TABLE users (
                    id SERIAL PRIMARY KEY,
                    username VARCHAR(50) UNIQUE NOT NULL,
                    password VARCHAR(255) NOT NULL,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                )
            ''')
            print("Tabela 'users' criada com sucesso!")
        else:
            print("Tabela 'users' já existe. Nenhuma ação necessária.")
    except Exception as e:
        print(f"Erro ao criar tabela: {e}")
    finally:
        if conn:
            await conn.close()

async def create_message_table():
    conn = None
    try:
        conn = await asyncpg.connect(
            user=os.getenv("POSTGRES_USER", "myuser"),
            password=os.getenv("POSTGRES_PASSWORD", "mypassword"),
            database=os.getenv("POSTGRES_DB", "mydatabase"),
            host=os.getenv("POSTGRES_HOST", "localhost"),
            port=os.getenv("POSTGRES_PORT", "5432")
        )
        
        table_exists = await conn.fetchval(
            "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'messages')"
        )
        
        if not table_exists:
            await conn.execute('''
                CREATE TABLE messages (
                    id SERIAL PRIMARY KEY,
                    username VARCHAR(50) NOT NULL,
                    content TEXT NOT NULL,
                    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                )
            ''')
            print("Tabela 'messages' criada com sucesso!")
        else:
            print("Tabela 'messages' já existe.")
    except Exception as e:
        print(f"Erro ao criar tabela de mensagens: {e}")
    finally:
        if conn:
            await conn.close()

async def create_private_message_table():
    conn = None
    try:
        conn = await asyncpg.connect(
            user=os.getenv("POSTGRES_USER", "myuser"),
            password=os.getenv("POSTGRES_PASSWORD", "mypassword"),
            database=os.getenv("POSTGRES_DB", "mydatabase"),
            host=os.getenv("POSTGRES_HOST", "localhost"),
            port=os.getenv("POSTGRES_PORT", "5432")
        )

        table_exists = await conn.fetchval(
            "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'private_messages')"
        )

        if not table_exists:
            await conn.execute('''
                CREATE TABLE private_messages (
    id SERIAL PRIMARY KEY,
    sender_id INTEGER NOT NULL REFERENCES users(id),
    recipient_id INTEGER NOT NULL REFERENCES users(id),
    content TEXT,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    type VARCHAR(50) DEFAULT 'text', -- 'text' or 'file'
    filename VARCHAR(255),          -- only if type is 'file'
    file_path VARCHAR(255)          -- only if type is 'file'
);
            ''')
            print("Tabela 'private_messages' criada com sucesso!")
        else:
            print("Tabela 'private_messages' já existe.")
    except Exception as e:
        print(f"Erro ao criar tabela de mensagens privadas: {e}")
    finally:
        if conn:
            await conn.close()

def setup_database(app: FastAPI):
    @app.on_event("startup")
    async def startup_db():
        await create_user_table()
        await create_message_table()
        await create_private_message_table()
