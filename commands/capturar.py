import discord
from discord import app_commands
from discord.ext import commands
import asyncpg
from .embed import (
    embed_captura_detalhada,
    embed_sem_carta_ativa
)
# IMPORTAÇÃO: Buscando a função do seu novo arquivo em systems
from systems.raridades import calcular_biscoitos_ganhos

class Capturar(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.pool: asyncpg.Pool = bot.pool

    @app_commands.command(
        name="capturar",
        description="Capturar a carta ativa tentando adivinhar o nome."
    )
    # TRAVA ADICIONADA: 1 execução a cada 5.0 segundos por Usuário (per_user=True)
    @app_commands.checks.cooldown(1, 5.0, key=lambda i: i.user.id)
    async def capturar(self, interaction: discord.Interaction, nome: str):
        await interaction.response.defer()

        canal = interaction.channel
        user_id = interaction.user.id

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

            if nome_user != nome_real:
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

        # Salva a captura e a economia no banco de dados
        async with self.pool.acquire() as conn:
            # Salva o personagem no inventário de cartas
            await conn.execute("""
                INSERT INTO inventario (user_id, carta_id, skin, quantidade)
                VALUES ($1, $2, $3, 1)
                ON CONFLICT (user_id, carta_id, skin)
                DO UPDATE SET quantidade = inventario.quantidade + 1
            """, user_id, carta["id"], carta["skin"])

            # ECONOMIA: Salva ou incrementa o saldo de Biscoito Gatinho na tabela usuarios
            await conn.execute("""
                INSERT INTO usuarios (user_id, biscoitos)
                VALUES ($1, $2)
                ON CONFLICT (user_id)
                DO UPDATE SET biscoitos = usuarios.biscoitos + $2
            """, user_id, biscoitos_ganhos)

            # Puxa a quantidade atualizada daquela variação da carta
            qtd = await conn.fetchval("""
                SELECT quantidade
                FROM inventario
                WHERE user_id = $1
                AND carta_id = $2
                AND skin IS NOT DISTINCT FROM $3
            """, user_id, carta["id"], carta["skin"])

        # Monta o embed de sucesso delegando tudo para o seu arquivo externo de embeds
        # Adicionei 'biscoitos_ganhos=biscoitos_ganhos' para você poder usar a informação lá dentro!
        embed = embed_captura_detalhada(
            nome=carta["nome"],
            raridade=carta["raridade"],
            dex=self.bot.limpar_dex(carta["dex"]),
            quantidade=qtd,
            skin=carta["skin"],
            biscoitos_ganhos=biscoitos_ganhos
        )

        await interaction.followup.send(embed=embed)


    # TRATAMENTO DE ERRO: Captura o erro do Cooldown e avisa o usuário de forma amigável
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


async def setup(bot):
    await bot.add_cog(Capturar(bot))