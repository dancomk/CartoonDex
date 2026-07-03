import discord
from discord import app_commands
from discord.ext import commands
import asyncpg

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

            # 3. Conta quantos códigos 'dex' ÚNICOS o usuário tem (Adendo das Skins resolvido)
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
        
        # Chama a função interna para buscar os dados corrigidos do banco Neon
        dados = await self.puxar_dados_perfil(user.id)
        
        # Formatação do plural dos biscoitos
        texto_biscoitos = f"{dados['biscoitos']} Biscoito Gatinho" if dados['biscoitos'] <= 1 else f"{dados['biscoitos']} Biscoitos Gatinho"

        # Criamos um embed tradicional provisório (Passo 1) para testar os números
        embed = discord.Embed(
            title=f"📋 Perfil de Treinador - {user.display_name}",
            color=discord.Color.from_rgb(255, 255, 255)
        )
        embed.set_thumbnail(url=user.display_avatar.url)
        
        embed.add_field(
            name="💰 Economia", 
            value=f"**Saldo:** {texto_biscoitos}", 
            inline=False
        )
        embed.add_field(
            name="🎴 Coleção", 
            value=f"**Total de Cartas:** {dados['total_cartas']}\n**Progresso da Dex:** {dados['dex_desbloqueada']}/{dados['total_cartas_jogo']}", 
            inline=False
        )
        
        embed.set_footer(text="Em breve: Cartão de Perfil em Imagem estilo Poketwo! 🚀")

        await interaction.followup.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Perfil(bot))