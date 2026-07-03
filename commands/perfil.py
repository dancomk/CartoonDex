import discord
from discord import app_commands
from discord.ext import commands
import asyncpg

# IMPORTAÇÃO CENTRALIZADA: Mantendo o padrão de isolar layouts visuais
from .embed import embed_perfil_provisorio

class Perfil(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.pool: asyncpg.Pool = bot.pool

    async def puxar_dados_perfil(self, user_id: int):
        """Puxa o saldo, total de cartas e progresso da Dex do jogador."""
        async with self.pool.acquire() as conn:
            # 1. Puxa o saldo de Biscoitos Gatinho
            biscoitos = await conn.fetchval(
                "SELECT biscoitos FROM usuarios WHERE user_id = $1", 
                user_id
            ) or 0

            # 2. Puxa o total absoluto de cartas (soma de todas as quantidades)
            total_cartas = await conn.fetchval(
                "SELECT COALESCE(SUM(quantidade), 0) FROM inventario WHERE user_id = $1", 
                user_id
            )

            # 3. Conta quantos códigos 'dex' ÚNICOS o usuário tem
            dex_desbloqueada = await conn.fetchval(
                "SELECT COUNT(DISTINCT dex) FROM inventario WHERE user_id = $1", 
                user_id
            )

            # 4. Puxa o total de códigos 'dex' ÚNICOS cadastrados no jogo inteiro
            total_cartas_jogo = await conn.fetchval(
                "SELECT COUNT(DISTINCT dex) FROM dex"
            ) or 0

        return {
            "biscoitos": biscoitos,
            "total_cartas": total_cartas,
            "dex_desbloqueada": dex_desbloqueada,
            "total_cartas_jogo": total_cartas_jogo
        }

    @app_commands.command(
        name="perfil",
        description="Visualizar suas estatísticas, saldo e progresso da Dex no CartoonDex."
    )
    async def perfil(self, interaction: discord.Interaction):
        await interaction.response.defer()
        
        user = interaction.user
        
        # Chama a função interna para buscar os dados do banco Neon
        dados = await self.puxar_dados_perfil(user.id)
        
        # Monta o embed chamando a função externa centralizada
        embed = embed_perfil_provisorio(
            user_name=user.display_name,
            avatar_url=user.display_avatar.url,
            biscoitos=dados["biscoitos"],
            total_cartas=dados["total_cartas"],
            dex_desbloqueada=dados["dex_desbloqueada"],
            total_cartas_jogo=dados["total_cartas_jogo"]
        )

        await interaction.followup.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Perfil(bot))