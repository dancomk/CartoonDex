import os
import random
import asyncio
import logging
from pathlib import Path
from typing import Optional

import discord
import aiohttp
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv

# Importações essenciais do sistema
from systems.database import conectar
from systems.gerar_cartas import obter_bytes_carta, gerar_carta_individual

# ====================================================================
# LOGS E CONFIGURAÇÕES
# ====================================================================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger("CartoonDex.Main")

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
DEV_GUILD_ID = os.getenv("DEV_GUILD_ID")
DEVELOPER_IDS = [
    int(uid.strip()) 
    for uid in os.getenv("DEVELOPER_IDS", "").split(",") 
    if uid.strip()
]


# ====================================================================
# CLASSE DO BOT
# ====================================================================
class CartoonDexBot(commands.Bot):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.pool = None
        self.aiohttp_session = None
        self.developer_ids = DEVELOPER_IDS
        
        # Estado Global
        self.current_spawn = {}
        self.tentativas_erradas = {}
        self.contador_mensagens = {}
        self.spawn_lock = asyncio.Lock()
        
        # Travas por servidor & Caches em RAM
        self.config_locks = {}
        self.dex = {}
        self.loja_molduras = {}
        self.loja_itens = {}
        self.servidor_config = {}

    async def setup_hook(self):
        """Inicialização única: Banco, HTTP, Caches, Cogs e Sync da Tree."""
        logger.info("⚙️ Iniciando setup_hook (recursos e conexões)...")

        # 1. Banco de Dados e HTTP
        self.pool = await conectar()
        self.aiohttp_session = aiohttp.ClientSession()

        # 2. Caches Iniciais
        await self._carregar_dex_cache()
        await self._carregar_lojas_cache()

        # 3. Aquecimento em segundo plano
        asyncio.create_task(self._aquecer_cache_cartas_bg())

        # 4. Carregamento de Cogs/Comandos
        base_dir = Path(__file__).parent
        for pasta in ["commands", "cogs"]:
            caminho_pasta = base_dir / pasta
            if not caminho_pasta.exists():
                continue
                
            for arquivo in caminho_pasta.rglob("*.py"):
                if arquivo.name.startswith(("_", "embed")):
                    continue
                
                # Transforma o caminho do arquivo no formato de modulo python: cogs.admin
                extensao = arquivo.relative_to(base_dir).with_suffix("").as_posix().replace("/", ".")
                try:
                    await self.load_extension(extensao)
                    logger.info(f"Extensão carregada: {extensao}")
                except Exception as e:
                    logger.error(f"❌ Falha ao carregar a extensão {extensao}: {e}")

        # 5. Sincronização dos Comandos Slash
        try:
            synced = await self.tree.sync()
            logger.info(f"✅ {len(synced)} comandos sincronizados globalmente.")
            
            if DEV_GUILD_ID:
                guild = discord.Object(id=int(DEV_GUILD_ID))
                synced_dev = await self.tree.sync(guild=guild)
                logger.info(f"✅ {len(synced_dev)} comandos sincronizados no servidor Dev.")
        except Exception as e:
            logger.error(f"Erro ao sincronizar comandos: {e}")

    async def close(self):
        """Finalização segura do bot ao encerrar o processo (SIGTERM / SIGINT)."""
        logger.info("👋 Fechando conexões antes de desligar...")
        if self.aiohttp_session and not self.aiohttp_session.closed:
            await self.aiohttp_session.close()
        if self.pool:
            await self.pool.close()
        await super().close()
        logger.info("🛑 Bot desligado com sucesso.")

    # ================================================================
    # UTILITÁRIOS E CACHES
    # ================================================================
    async def obter_canal_spawn(self, servidor_id: int) -> Optional[int]:
        """Obtém canal de spawn com cache e proteção de concorrência."""
        if servidor_id in self.servidor_config:
            return self.servidor_config[servidor_id].get("canal_spawn_id")

        lock = self.config_locks.setdefault(servidor_id, asyncio.Lock())

        async with lock:
            # Re-checagem pós-lock
            if servidor_id in self.servidor_config:
                return self.servidor_config[servidor_id].get("canal_spawn_id")

            try:
                async with self.pool.acquire() as conn:
                    row = await conn.fetchrow(
                        "SELECT canal_spawn_id, canais_monitorados, cargo_adm_id FROM config_servidores WHERE servidor_id = $1", 
                        servidor_id
                    )
                    if row:
                        self.servidor_config[servidor_id] = {
                            "canal_spawn_id": row["canal_spawn_id"],
                            "canais_monitorados": row["canais_monitorados"] or [],
                            "cargo_adm_id": row["cargo_adm_id"]
                        }
                        return row["canal_spawn_id"]
            except Exception as e:
                logger.error(f"Erro ao buscar config do servidor {servidor_id}: {e}")
            
            return None

    def buscar_carta_aleatoria(self) -> Optional[dict]:
        """Sorteia uma carta da Dex em memória."""
        return random.choice(list(self.dex.values())) if self.dex else None

    async def _carregar_dex_cache(self):
        try:
            async with self.pool.acquire() as conn:
                rows = await conn.fetch("""
                    SELECT carta_id, numero_dex, nome, skin_nome, skin_id, raridade, aliases, origem, hp, full_art, artista, habilidade1, habilidade2
                    FROM dex ORDER BY numero_dex ASC, skin_id ASC
                """)
                self.dex = {r["carta_id"]: dict(r) for r in rows}
            logger.info(f"✅ Dex carregada: {len(self.dex)} cartas em memória.")
        except Exception as e:
            logger.error(f"❌ Erro ao carregar Dex: {e}")

    async def _carregar_lojas_cache(self):
        try:
            async with self.pool.acquire() as conn:
                molduras = await conn.fetch("SELECT moldura_id, nome, preco, raridade FROM loja_molduras")
                itens = await conn.fetch("SELECT item_nome, nome, preco, descricao FROM loja_itens")
                self.loja_molduras = {r["moldura_id"]: dict(r) for r in molduras}
                self.loja_itens = {r["item_nome"]: dict(r) for r in itens}
            logger.info(f"✅ Loja em cache: {len(self.loja_molduras)} molduras, {len(self.loja_itens)} itens.")
        except Exception as e:
            logger.error(f"❌ Erro ao carregar Loja: {e}")

    async def _aquecer_cache_cartas_bg(self):
        """Pré-gera imagens de cartas em segundo plano."""
        logger.info("🎨 Gerando cartas em segundo plano...")
        geradas = 0
        for carta in list(self.dex.values()):
            carta_id = carta.get("carta_id")
            if carta_id and not obter_bytes_carta(carta_id)[0]:
                await asyncio.to_thread(gerar_carta_individual, carta)
                geradas += 1
                await asyncio.sleep(0.1)
        logger.info(f"✅ Geração concluída! {geradas} novas cartas salvas.")


# ====================================================================
# INICIALIZAÇÃO
# ====================================================================
intents = discord.Intents.default()
intents.message_content = True

bot = CartoonDexBot(command_prefix="!", intents=intents)


@bot.event
async def on_ready():
    logger.info(f"🚀 {bot.user} está online e operacional!")


@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    if isinstance(error, app_commands.CheckFailure):
        msg = "❌ Você não tem permissão para executar este comando."
    elif isinstance(error, app_commands.CommandOnCooldown):
        msg = f"⏳ Aguarde {error.retry_after:.1f}s para usar o comando novamente."
    else:
        logger.error(f"Erro em /{interaction.command.name if interaction.command else 'comando'}: {error}")
        msg = "⚠️ Ocorreu um erro ao processar o comando."

    try:
        if interaction.response.is_done():
            await interaction.followup.send(msg, ephemeral=True)
        else:
            await interaction.response.send_message(msg, ephemeral=True)
    except Exception:
        pass


bot.run(TOKEN)