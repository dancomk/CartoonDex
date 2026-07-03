import os
import discord
import random
import unicodedata
import asyncio
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv
from systems.database import conectar

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
GITHUB_BASE = os.getenv("GITHUB_BASE")

DEV_GUILD_ID = os.getenv("DEV_GUILD_ID")
bot_developer_ids = [int(uid.strip()) for uid in os.getenv("DEVELOPER_IDS", "").split(",") if uid.strip()]

SPAWN_CHANNEL_IDS = [1190834586008158330]

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

current_spawn = {}
tentativas_erradas = {}
contador_mensagens = {}

spawn_lock = asyncio.Lock()

bot.dex = []


def normalizar(texto: str):
    return unicodedata.normalize("NFKD", texto).encode("ASCII", "ignore").decode().lower()


def limpar_dex(dex):
    dex = str(dex).replace("#", "")
    return dex.zfill(4)


async def carregar_dex_cache():
    async with bot.pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT id, dex, nome, skin, skin_id, raridade, dica, aliases
            FROM dex
            ORDER BY id
        """)

        bot.dex = [dict(r) for r in rows]

    print(f"Dex carregada: {len(bot.dex)} cartas")


async def buscar_carta_aleatoria():
    if not bot.dex:
        return None

    return random.choice(bot.dex)


def url_preview(carta):
    dex = limpar_dex(carta["dex"])
    skin = carta.get("skin_id", 0)

    return f"{GITHUB_BASE}/assets/spawn/{dex}/{dex}-{skin}-spawn.png"


def url_carta(carta):
    dex = limpar_dex(carta["dex"])
    skin = carta.get("skin_id", 0)

    return f"{GITHUB_BASE}/assets/cartas/{dex}/{dex}-{skin}-carta.png"


async def spawn_personagem(canal):
    carta = await buscar_carta_aleatoria()

    if not carta:
        await canal.send("⚠️ Nenhuma carta encontrada no banco.")
        return False

    current_spawn[canal.id] = carta
    tentativas_erradas[canal.id] = 0

    # IMPORTANTE: Agora buscando do seu arquivo atualizado 'commands/embed.py' no singular!
    from commands.embed import embed_spawn
    embed = embed_spawn(
        nome=carta["nome"],
        raridade=carta["raridade"]
    )

    embed.set_image(url=url_preview(carta))

    await canal.send(embed=embed)

    return True


@bot.event
async def on_ready():
    print(f"Logado como {bot.user}")

    bot.pool = await conectar()

    bot.developer_ids = bot_developer_ids
    bot.spawn_personagem = spawn_personagem
    bot.buscar_carta_aleatoria = buscar_carta_aleatoria
    bot.current_spawn = current_spawn
    bot.tentativas_erradas = tentativas_erradas
    bot.spawn_lock = spawn_lock
    bot.normalizar = normalizar
    bot.url_carta = url_carta
    bot.url_preview = url_preview
    bot.limpar_dex = limpar_dex

    await carregar_dex_cache()

    # --- CARREGAMENTO DINÂMICO DE COGS (INDENTAÇÃO CORRIGIDA) ---
    caminho_commands = os.path.join(os.path.dirname(__file__), "commands")
    
    for raiz, pastas, arquivos in os.walk(caminho_commands):
        for arquivo in arquivos:
            # FILTRO ATUALIZADO: Ignora qualquer arquivo que comece com "embed" (singular)
            if arquivo.endswith(".py") and not arquivo.startswith("__") and not arquivo.startswith("embed"):
                caminho_relativo = os.path.relpath(os.path.join(raiz, arquivo), os.path.dirname(__file__))
                nome_extensao = caminho_relativo.replace(os.sep, ".").removesuffix(".py")
                
                await bot.load_extension(nome_extensao)
                print(f"Extensão carregada: {nome_extensao}")

    # Sincroniza globalmente os comandos da árvore principal (públicos e administradores)
    synced_global = await bot.tree.sync()
    print(f"{len(synced_global)} comandos sincronizados globalmente.")

    # Sincroniza os comandos locais da guilda de testes (tudo dentro da pasta commands/dev/)
    if DEV_GUILD_ID:
        guild_objeto = discord.Object(id=int(DEV_GUILD_ID))
        synced_guild = await bot.tree.sync(guild=guild_objeto)
        print(f"{len(synced_guild)} comandos locais sincronizados no servidor de testes.")
        
    print("Bot pronto.")


@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    if isinstance(error, app_commands.CheckFailure):
        await interaction.response.send_message(
            "❌ Você não tem permissão para executar este comando.", 
            ephemeral=True
        )
    else:
        print(f"Erro em comando: {error}")


@bot.event
async def on_message(message):
    if message.author.bot:
        return

    # canais_monitorados = lista vinda do banco ou bot.spawn_channel_ids
    # canal_spawn_fixo = ID vindo do banco ou bot.canal_spawn_configurado
    canais_monitorados = getattr(bot, "spawn_channel_ids", [])
    canal_spawn_fixo = getattr(bot, "canal_spawn_configurado", None)

    # REGRA 1: Se a lista de monitoramento NÃO estiver vazia, verifica se o canal atual está nela.
    # Se estiver VAZIA, ela monitora qualquer canal do servidor automaticamente.
    deve_monitorar = (not canais_monitorados) or (message.channel.id in canais_monitorados)

    if deve_monitorar:
        contador_mensagens[message.channel.id] = contador_mensagens.get(message.channel.id, 0) + 1

        if contador_mensagens[message.channel.id] >= 15:
            contador_mensagens[message.channel.id] = 0

            if random.random() <= 0.6:
                # REGRA 2: Se houver canal de spawn configurado, manda nele.
                # Se NÃO houver, manda no canal atual (onde a 15ª mensagem caiu).
                if canal_spawn_fixo:
                    canal_destino = bot.get_channel(canal_spawn_fixo) or message.channel
                else:
                    canal_destino = message.channel

                await spawn_personagem(canal_destino)

    await bot.process_commands(message)


bot.run(TOKEN)