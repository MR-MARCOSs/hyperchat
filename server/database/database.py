import asyncpg
import os

async def save_message(username: str, content: str):
    conn = await asyncpg.connect(
        user=os.getenv("POSTGRES_USER", "myuser"),
        password=os.getenv("POSTGRES_PASSWORD", "mypassword"),
        database=os.getenv("POSTGRES_DB", "mydatabase"),
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=os.getenv("POSTGRES_PORT", "5432")
    )
    try:
        await conn.execute(
            "INSERT INTO messages (username, content) VALUES ($1, $2)",
            username, content
        )
    except Exception as e:
        print(f"Erro ao salvar mensagem: {e}")
    finally:
        await conn.close()

async def get_last_messages(limit: int = 10):
    conn = await asyncpg.connect(
        user=os.getenv("POSTGRES_USER", "myuser"),
        password=os.getenv("POSTGRES_PASSWORD", "mypassword"),
        database=os.getenv("POSTGRES_DB", "mydatabase"),
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=os.getenv("POSTGRES_PORT", "5432")
    )
    try:
        rows = await conn.fetch(
            "SELECT username, content, timestamp FROM messages ORDER BY timestamp DESC LIMIT $1",
            limit
        )
        return rows
    except Exception as e:
        print(f"Erro ao buscar mensagens: {e}")
        return []
    finally:
        await conn.close()
