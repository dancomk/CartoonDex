import asyncpg
import os

pool = None

async def conectar():
    global pool

    if pool is None:
        database_url = os.getenv("DATABASE_URL")

        pool = await asyncpg.create_pool(
            database_url,
            min_size=1,
            max_size=10
        )

    return pool