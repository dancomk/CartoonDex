import discord
from discord import app_commands
from discord.ext import commands
import asyncpg
import string

from .embed import (
    embed_captura_detalhada,
    embed_sem_carta_ativa
)

from systems.raridades import calcular_biscoitos_ganhos

# --- SISTEMA DE EMBARALHAMENTO DO ID GLOBAL (TCG STYLE) ---
ALFABETO = string.digits + string.ascii_uppercase  # 36 caracteres
PRIMO = 41359727
MODULO = 36**6  # 2.176.782.336 combinações possíveis

def numero_para_codigo_aleatorio(num: int) -> str:
    """Embaralha o ID SERIAL único do banco em um hash de 6 dígitos."""
    embaralhado = (num * PRIMO) % MODULO
    codigo = ""
    for _ in range(6):
        embaralhado, resto = divmod(embaralhado, 36)
        codigo = ALFABETO[resto] + codigo
    return codigo


class Capturar(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.pool: asyncpg.Pool = bot.pool

    @app_commands.command(
        name="capturar",
        description="Capturar a carta ativa tentando adivinhar o nome."
    )
    @app_commands.checks.cooldown(1, 3.0, key=lambda i: i.user.id)
    async def capturar(self, interaction: discord.Interaction, nome: str):
        await interaction.response.defer(ephemeral=False)

        canal = interaction.channel
        user_id = interaction.user.id
        str_user_id = str(user_id)

        bot_current_spawn = self.bot.current_spawn
        bot_tentativas_erradas = self.bot.tentativas_erradas
        bot_spawn_lock = self.bot.spawn_lock

        async with bot_spawn_lock:
            carta = bot_current_spawn.get(canal.id)

            if not carta:
                await interaction.followup.send(
                    embed=embed_sem_carta_ativa()
                )
                return

            nome_user = self.bot.normalizar(nome)
            nome_real = self.bot.normalizar(carta["nome"])
            aliases_reais = [self.bot.normalizar(a) for a in carta.get("aliases", []) if a]

            # Se houver um nome de skin cadastrado no spawn, adicionamos aos aliases válidos de acerto
            if carta.get("skin_nome"):
                nome_skin_real = self.bot.normalizar(carta["skin_nome"])
                if nome_user == nome_skin_real:
                    nome_real = nome_skin_real  # Valida o acerto se digitarem o nome da skin

            if nome_user != nome_real and nome_user not in aliases_reais:
                bot_tentativas_erradas[canal.id] = bot_tentativas_erradas.get(canal.id, 0) + 1
                await interaction.followup.send("❌ Nome incorreto!")

                if bot_tentativas_erradas[canal.id] >= 3 and carta.get("dica"):
                    await canal.send(f"🔎 Dica: {carta['dica']}")
                return

            # Se acertou, limpa imediatamente os caches do canal para evitar capturas duplas
            bot_current_spawn.pop(canal.id, None)
            bot_tentativas_erradas.pop(canal.id, None)

        # Sorteia a recompensa
        biscoitos_ganhos = calcular_biscoitos_ganhos(carta["raridade"])

        # Execução segura no Banco de Dados (Instâncias Únicas)
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                # 1. NOVO INSERT: Sempre insere uma nova linha (Carta Única)
                id_gerado = await conn.fetchval("""
                    INSERT INTO inventario_cartas (membro_id, numero_dex, skin_id, moldura_id)
                    VALUES ($1, $2, $3, NULL)
                    RETURNING id
                """, str_user_id, carta["numero_dex"], carta.get("skin_id", 0))

                # 2. CÁLCULO DO ID PESSOAL: Descobre a posição atual desta carta na mochila do usuário
                id_pessoal = await conn.fetchval("""
                    SELECT COUNT(*) FROM inventario_cartas 
                    WHERE membro_id = $1 AND data_pessoal <= (
                        SELECT data_pessoal FROM inventario_cartas WHERE id = $2
                    )
                """, str_user_id, id_gerado)

                # 3. CONTAGEM COORDENADA: Conta quantas cópias idênticas o jogador possui no total
                qtd_total_repetidas = await conn.fetchval("""
                    SELECT COUNT(*) FROM inventario_cartas 
                    WHERE membro_id = $1 AND numero_dex = $2 AND skin_id = $3
                """, str_user_id, carta["numero_dex"], carta.get("skin_id", 0))

                # Incrementa os biscoitos na tabela de perfis
                await conn.execute("""
                    INSERT INTO perfis (membro_id, biscoitos)
                    VALUES ($1, $2)
                    ON CONFLICT (membro_id)
                    DO UPDATE SET bioscoitos = perfis.biscoitos + $2
                """, user_id, biscoitos_ganhos)

        # Traduz o ID sequencial do banco para o Hash Alfanumérico de 6 dígitos
        id_global_hash = numero_para_codigo_aleatorio(id_gerado)

        # RESOLUÇÃO DO NOME: Se skin_nome não for nulo/vazio, usa apenas ele. Caso contrário, usa o nome base.
        nome_exibicao = carta.get("skin_nome") if carta.get("skin_nome") else carta["nome"]

        # Monta o embed respeitando estritamente a assinatura original do seu embed.py
        embed = embed_captura_detalhada(
            nome=nome_exibicao,
            raridade=carta["raridade"],
            dex=carta["numero_dex"],
            quantidade=qtd_total_repetidas,
            biscoitos_ganhos=biscoitos_ganhos,
            skin=carta.get("skin_id", 0)
        )

        await interaction.followup.send(embed=embed)

    @capturar.error
    async def capturar_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.CommandOnCooldown):
            tempo_restante = round(error.retry_after, 1)
            await interaction.response.send_message(
                f"⏱️ Você está digitando rápido demais! Aguarde **{tempo_restante}s** para tentar capturar novamente.",
                ephemeral=True
            )
        else:
            print(f"Erro no comando capturar: {error}")
            if interaction.response.is_done():
                await interaction.followup.send("❌ Ocorreu um erro interno ao processar sua captura.")
            else:
                await interaction.response.send_message("❌ Ocorreu um erro interno antes de processar o comando.", ephemeral=True)

async def setup(bot):
    await bot.add_cog(Capturar(bot))