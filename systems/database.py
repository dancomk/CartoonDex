import asyncpg
import os
import logging

logger = logging.getLogger("CartoonDex.Database")
pool = None

async def conectar():
    global pool

    if pool is None:
        database_url = os.getenv("DATABASE_URL")
        logger.info("Iniciando conexão com o pool do banco de dados Neon...")

        try:
            pool = await asyncpg.create_pool(
                database_url,
                min_size=1,
                max_size=10
            )
            logger.info("✅ Pool de conexões do Neon estabelecido com sucesso!")
        except Exception as e:
            logger.critical(f"❌ Falha crítica ao conectar no banco Neon: {e}")
            raise e

    return pool