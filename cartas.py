import os
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise ValueError("DATABASE_URL não encontrada no .env ou nas Environment Variables")


def get_conn():
    return psycopg2.connect(DATABASE_URL, sslmode="require")


def carregar_dex():
    conn = get_conn()

    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT * FROM dex ORDER BY id ASC;")
            rows = cur.fetchall()
            return [dict(r) for r in rows]

    finally:
        conn.close()


dex = carregar_dex()