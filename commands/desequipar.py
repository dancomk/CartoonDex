import discord
from discord import app_commands
from discord.ext import commands
import asyncpg

class Desequipar(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.pool: asyncpg.Pool = bot.pool

    @app_commands.command(
        name="desequipar",
        description="Remove uma moldura específica de uma das suas cartas!"
    )
    @app_commands.describe(
        carta_id="O ID da carta da qual você deseja remover a moldura.",
        moldura_id="O ID da moldura específica que você deseja remover desta carta."
    )
    async def desequipar(self, interaction: discord.Interaction, carta_id: str, moldura_id: str):
        await interaction.response.defer(ephemeral=False)
        
        user_id = interaction.user.id
        str_user_id = str(user_id)

        async with self.pool.acquire() as conn:
            async with conn.transaction():
                carta_usuario = await conn.fetchrow("""
                    SELECT carta_id, moldura_id, skin_id 
                    FROM inventario_cartas 
                    WHERE membro_id = $1 AND carta_id = $2 AND moldura_id = $3
                    LIMIT 1
                """, str_user_id, carta_id, moldura_id)

                if not carta_usuario:
                    return await interaction.followup.send(
                        f"❌ Você não possui a carta `{carta_id}` com a moldura `{moldura_id}` equipada.", 
                        ephemeral=True
                    )

                # Remove a moldura
                await conn.execute("""
                    UPDATE inventario_cartas 
                    SET moldura_id = NULL 
                    WHERE membro_id = $1 AND carta_id = $2 AND moldura_id = $3
                """, str_user_id, carta_id, moldura_id)

                # Devolve o item ao estoque
                await conn.execute("""
                    INSERT INTO inventario_molduras (membro_id, moldura_id, quantidade)
                    VALUES ($1, $2, 1)
                    ON CONFLICT (membro_id, moldura_id) 
                    DO UPDATE SET quantidade = inventario_molduras.quantidade + 1
                """, user_id, moldura_id)

        dados_carta_global = self.bot.dex.get(carta_id)
        nome_carta = dados_carta_global['nome'] if dados_carta_global else carta_id

        embed = discord.Embed(
            title="✨ Moldura Removida!",
            description=f"{interaction.user.mention} removeu a moldura **{moldura_id}** da carta **{nome_carta}**! Ela retornou ao seu inventário.",
            color=discord.Color.from_rgb(255, 255, 255)
        )
        
        if dados_carta_global and hasattr(self.bot, "gerar_url_carta"):
            dados_para_url = {
                "carta_id": carta_id,
                "skin_id": carta_usuario["skin_id"],
                "moldura_id": None
            }
            url_limpa = self.bot.gerar_url_carta(dados_para_url)
            embed.set_image(url=url_limpa)

        embed.set_footer(text="CartoonDex • Cosméticos")
        await interaction.followup.send(embed=embed)


async def setup(bot):
    await bot.add_cog(Desequipar(bot))