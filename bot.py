import os
import discord
import random
import unicodedata
import asyncio
import aiohttp
import logging
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv

# Importações do sistema do bot
from systems.database import conectar
from systems.gerar_carta import (
    carregar_e_gerar_todas_as_cartas, 
    obter_bytes_carta, 
    obter_bytes_carta_spawn
)

# ====================================================================
# CONFIGURAÇÃO DE LOGS ESTRUTURADOS
# ====================================================================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger("CartoonDex.Main")

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
GITHUB_BASE = os.getenv("GITHUB_BASE")

DEV_GUILD_ID = os.getenv("DEV_GUILD_ID")
bot_developer_ids = [int(uid.strip()) for uid in os.getenv("DEVELOPER_IDS", "").split(",") if uid.strip()]

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

bot.current_spawn = {}
bot.tentativas_erradas = {}
bot.contador_mensagens = {}

spawn_lock = asyncio.Lock()
bot.spawn_lock = spawn_lock

# --- CACHES GLOBAIS ---
bot.dex = []
bot.loja_molduras = {}
bot.loja_itens = {}
bot.servidor_config = {}  # Cache para não sobrecarregar o Neon a cada mensagem enviada
bot.aiohttp_session = None 


def normalizar(texto: str):
    return unicodedata.normalize("NFKD", texto).encode("ASCII", "ignore").decode().lower()


def limpar_dex(dex):
    box_dex = str(dex).replace("#", "")
    return box_dex.zfill(4)


async def carregar_dex_cache():
    try:
        async with bot.pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT carta_id, numero_dex, nome, skin_nome, skin_id, raridade, aliases, origem, hp, full_art, artista, habilidade1, habilidade2
                FROM dex
                ORDER BY numero_dex ASC, skin_id ASC
            """)
            # Mapeia as linhas recuperadas do Neon para o cache global do bot
            bot.dex = {r["carta_id"]: dict(r) for r in rows}
        logger.info(f"✅ Dex carregada em cache: {len(bot.dex)} cartas.")
    except Exception as e:
        logger.error(f"❌ Erro ao carregar cache da Dex no banco Neon: {e}")
        bot.dex = {}


async def carregar_lojas_cache():
    try:
        async with bot.pool.acquire() as conn:
            molduras_rows = await conn.fetch("SELECT moldura_id, nome, preco, raridade FROM loja_molduras")
            bot.loja_molduras = {r["moldura_id"]: dict(r) for r in molduras_rows}
            
            itens_rows = await conn.fetch("SELECT item_nome, nome, preco, descricao FROM loja_itens")
            bot.loja_itens = {r["item_nome"]: dict(r) for r in itens_rows}
            
        logger.info(f"✅ Cache da Loja carregado: {len(bot.loja_molduras)} molduras e {len(bot.loja_itens)} itens.")
    except Exception as e:
        logger.error(f"❌ Erro ao carregar tabelas de loja para o cache: {e}")


async def obter_canal_spawn(servidor_id: int):
    """Busca as configurações do servidor usando cache para máxima performance."""
    if servidor_id in bot.servidor_config:
        return bot.servidor_config[servidor_id].get("canal_spawn_id")

    try:
        async with bot.pool.acquire() as conn:
            row = await conn.fetchrow("SELECT canal_spawn_id, canais_monitorados, cargo_adm_id FROM config_servidores WHERE servidor_id = $1", servidor_id)
            if row:
                bot.servidor_config[servidor_id] = {
                    "canal_spawn_id": row["canal_spawn_id"],
                    "canais_monitorados": row["canais_monitorados"] or [],
                    "cargo_adm_id": row["cargo_adm_id"]
                }
                return row["canal_spawn_id"]
    except Exception as e:
        logger.error(f"Erro ao buscar configuração do servidor {servidor_id}: {e}")
    
    return None

async def buscar_carta_aleatoria():
    if not bot.dex:
        logger.warning("Tentativa de buscar carta aleatória, mas o cache da Dex está vazio!")
        return None
    
    # Seleciona aleatoriamente um valor da lista de dicionários da Dex
    chave_sorteada = random.choice(list(bot.dex.keys()))
    return bot.dex[chave_sorteada]


def url_carta(carta):
    dex = limpar_dex(carta.get("numero_dex", "0000"))
    skin = carta.get("skin_id", 0)
    return f"{GITHUB_BASE}/assets/cartas/{dex}/{dex}-{skin}-carta.png"


def url_moldura(moldura_id):
    return f"{GITHUB_BASE}/assets/molduras/{moldura_id}.png"


async def spawn_personagem(canal, interaction: discord.Interaction = None):
    carta = await buscar_carta_aleatoria()

    if not carta:
        msg_erro = "⚠️ Nenhuma carta encontrada no banco de dados."
        if interaction:
            if interaction.response.is_done():
                await interaction.followup.send(msg_erro, ephemeral=True)
            else:
                await interaction.response.send_message(msg_erro, ephemeral=True)
        else:
            await canal.send(msg_erro)
        return False

    carta_id = carta.get("carta_id") or f"{limpar_dex(carta.get('numero_dex', '0000'))}-{carta.get('skin_id', 0)}"

    bot.current_spawn[canal.id] = carta
    bot.tentativas_erradas[canal.id] = 0

    from commands.embed import embed_spawn
    
    # Renderiza a carta dinamicamente substituindo o nome por '?????' (eh_spawn=True)
    buffer_spawn, filename = await asyncio.to_thread(obter_bytes_carta_spawn, carta, carta_id)

    if not buffer_spawn:
        logger.error(f"❌ Não foi possível gerar os bytes da carta para o spawn ({carta_id}).")
        return False

    file = discord.File(fp=buffer_spawn, filename=filename)

    # Cria o Embed omitindo o nome real do personagem
    embed = embed_spawn(
        nome="?????",
        raridade=carta.get("raridade", "Desconhecida")
    )
    embed.set_image(url=f"attachment://{filename}")

    await canal.send(embed=embed, file=file)
    return True


@bot.event
async def on_ready():
    logger.info(f"Logado como {bot.user}")

    bot.pool = await conectar()
    bot.aiohttp_session = aiohttp.ClientSession() 
    
    bot.developer_ids = bot_developer_ids
    bot.spawn_personagem = spawn_personagem
    bot.buscar_carta_aleatoria = buscar_carta_aleatoria
    bot.normalizar = normalizar
    bot.url_carta = url_carta
    bot.url_moldura = url_moldura
    bot.limpar_dex = limpar_dex
    bot.obter_canal_spawn = obter_canal_spawn
    
    # Injeta as funções de ler buffers da memória RAM nas propriedades do bot
    bot.obter_bytes_carta = obter_bytes_carta
    bot.obter_bytes_carta_spawn = obter_bytes_carta_spawn

    # Caches do banco de dados
    await carregar_dex_cache()
    await carregar_lojas_cache()
    
    # Carrega e renderiza todas as cartas na RAM sem travar o loop de eventos
    logger.info("🎨 Iniciando geração de cartas na memória RAM...")
    await asyncio.to_thread(carregar_e_gerar_todas_as_cartas)
    
    # --- CARREGAMENTO DINÂMICO DE COGS ---
    caminho_commands = os.path.join(os.path.dirname(__file__), "commands")
    
    for raiz, pastas, arquivos in os.walk(caminho_commands):
        for arquivo in arquivos:
            if arquivo.endswith(".py") and not arquivo.startswith("__") and not arquivo.startswith("embed"):
                caminho_relativo = os.path.relpath(os.path.join(raiz, arquivo), os.path.dirname(__file__))
                nome_extensao = caminho_relativo.replace(os.sep, ".").removesuffix(".py")
                
                try:
                    await bot.load_extension(nome_extensao)
                    logger.info(f"Extensão carregada: {nome_extensao}")
                except Exception as e:
                    logger.error(f"❌ Falha ao carregar a extensão {nome_extensao}: {e}")

    try:
        synced_global = await bot.tree.sync()
        logger.info(f"{len(synced_global)} comandos sincronizados globalmente.")
    except Exception as e:
        logger.error(f"Erro na sincronização global de comandos: {e}")

    if DEV_GUILD_ID:
        try:
            guild_objeto = discord.Object(id=int(DEV_GUILD_ID))
            synced_guild = await bot.tree.sync(guild=guild_objeto)
            logger.info(f"{len(synced_guild)} comandos locais sincronizados no servidor de testes.")
        except Exception as e:
            logger.error(f"Erro na sincronização local do servidor de testes: {e}")
        
    logger.info("🚀 CartoonDex está 100% pronto para os membros!")


async def close():
    logger.info("Fechando sessões e pools de memória...")
    if bot.aiohttp_session:
        await bot.aiohttp_session.close()
    if bot.pool:
        await bot.pool.close()
    await super(commands.Bot, bot).close()

bot.close = close


@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    if isinstance(error, app_commands.CheckFailure):
        await interaction.response.send_message(
            "❌ Você não tem permissão para executar este comando.", 
            ephemeral=True
        )
    elif isinstance(error, app_commands.CommandOnCooldown):
        await interaction.followup.send(
            f"⏳ Você está em cooldown! Tente novamente em {error.retry_after:.2f}s.",
            ephemeral=True
        )
    else:
        logger.error(f"Erro inesperado no comando /{interaction.command.name if interaction.command else 'desconhecido'}: {error}")
        try:
            msg_erro = "⚠️ Ocorreu um erro interno ao processar este comando."
            if interaction.response.is_done():
                await interaction.followup.send(msg_erro, ephemeral=True)
            else:
                await interaction.response.send_message(msg_erro, ephemeral=True)
        except Exception:
            pass

@bot.event
async def on_message(message):
    if message.author.bot or not message.guild:
        return

    servidor_id = message.guild.id
    if servidor_id not in bot.servidor_config:
        await bot.obter_canal_spawn(servidor_id)

    config = bot.servidor_config.get(servidor_id, {"canal_spawn_id": None, "canais_monitorados": []})
    canal_spawn_id = config.get("canal_spawn_id")
    canais_monitorados = config.get("canais_monitorados", [])

    if canais_monitorados and message.channel.id not in canais_monitorados:
        return

    bot.contador_mensagens[message.channel.id] = bot.contador_mensagens.get(message.channel.id, 0) + 1

    if bot.contador_mensagens[message.channel.id] >= 15:
        bot.contador_mensagens[message.channel.id] = 0

        if random.random() <= 0.6:
            canal_destino = bot.get_channel(canal_spawn_id) if canal_spawn_id else message.channel
            if canal_destino:
                await spawn_personagem(canal_destino)

    await bot.process_commands(message)


bot.run(TOKEN)