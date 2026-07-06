import discord
from discord import app_commands
from discord.ext import commands
import asyncpg

from .embed import (
    embed_captura_detalhada,
    embed_sem_carta_ativa
)

from systems.raridades import calcular_biscoitos_ganhos

class Capturar(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.pool: asyncpg.Pool = bot.pool

    @app_commands.command(
        name="capturar",
        description="Capturar a carta ativa tentando adivinhar o nome."
    )
    # TRAVA: 1 execução a cada 3.0 segundos por Usuário (per_user=True)
    @app_commands.checks.cooldown(1, 3.0, key=lambda i: i.user.id)
    async def capturar(self, interaction: discord.Interaction, nome: str):
        # Configurado como False para exibir os parâmetros digitados nativamente no Discord
        await interaction.response.defer(ephemeral=False)

        canal = interaction.channel
        user_id = interaction.user.id
        str_user_id = str(user_id)  # Necessário pois inventario_cartas usa VARCHAR(50) para membro_id

        # Puxa as referências salvas na instância do bot
        bot_current_spawn = self.bot.current_spawn
        bot_tentativas_erradas = self.bot.tentativas_erradas
        bot_spawn_lock = self.bot.spawn_lock

        async with bot_spawn_lock:
            carta = bot_current_spawn.get(canal.id)

            if not carta:
                await interaction.followup.send(
                    embed=embed_sem_carta_ativa(),
                    ephemeral=True
                )
                return

            nome_user = self.bot.normalizar(nome)
            nome_real = self.bot.normalizar(carta["nome"])
            
            # Puxa os aliases configurados e normaliza todos para validação de acerto alternativa
            aliases_reais = [self.bot.normalizar(a) for a in carta.get("aliases", []) if a]

            if nome_user != nome_real and nome_user not in aliases_reais:
                bot_tentativas_erradas[canal.id] = bot_tentativas_erradas.get(canal.id, 0) + 1
                await interaction.followup.send("❌ Nome incorreto!")

                if bot_tentativas_erradas[canal.id] >= 3 and carta.get("dica"):
                    await canal.send(f"🔎 Dica: {carta['dica']}")
                return

            # Se acertou, remove a carta ativa daquele canal
            bot_current_spawn.pop(canal.id, None)
            bot_tentativas_erradas.pop(canal.id, None)

        # ECONOMIA: Sorteia quantos biscoitos o jogador vai ganhar baseado na raridade
        biscoitos_ganhos = calcular_biscoitos_ganhos(carta["raridade"])

        # Salva a captura e a economia no banco de dados conforme a estrutura real das imagens
        async with self.pool.acquire() as conn:
            # SUPER OTIMIZAÇÃO: Insere ou incrementa baseado no formato exato de inventario_cartas (image_f94fe3.png)
            qtd = await conn.fetchval("""
                INSERT INTO inventario_cartas (membro_id, carta_id, quantidade, moldura_id)
                VALUES ($1, $2, 1, NULL)
                ON CONFLICT (membro_id, carta_id, moldura_id)
                DO UPDATE SET quantidade = inventario_cartas.quantidade + 1
                RETURNING quantidade
            """, str_user_id, carta["carta_id"])

            # ECONOMIA: Salva ou incrementa o saldo na tabela perfis (image_f94fe6.png) onde membro_id é BIGINT
            await conn.execute("""
                INSERT INTO perfis (membro_id, biscoitos)
                VALUES ($1, $2)
                ON CONFLICT (membro_id)
                DO UPDATE SET biscoitos = perfis.biscoitos + $2
            """, user_id, biscoitos_ganhos)

        # Monta o embed delegando a criação visual para a função externa
        embed = embed_captura_detalhada(
            nome=carta["nome"],
            raridade=carta["raridade"],
            carta_id=carta["carta_id"],
            numero_dex=carta["numero_dex"],
            quantidade=qtd,
            skin_id=carta["skin_id"],
            biscoitos_ganhos=biscoitos_ganhos,
            imagem=carta.get("imagem"),
            user_mention=interaction.user.mention
        )

        await interaction.followup.send(embed=embed)


    # TRATAMENTO DE ERRO: Captura o erro do Cooldown usando followup.send de forma correta
    @capturar.error
    async def capturar_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.CommandOnCooldown):
            tempo_restante = round(error.retry_after, 1)
            # Como o erro corta a execução antes do defer(), usamos response.send_message
            await interaction.response.send_message(
                f"⏱️ Você está digitando rápido demais! Aguarde **{tempo_restante}s** para tentar capturar novamente.",
                ephemeral=True
            )
        else:
            print(f"Erro no comando capturar: {error}")


async def setup(bot):
    await bot.add_cog(Capturar(bot))