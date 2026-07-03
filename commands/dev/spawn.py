import os
import discord
from discord import app_commands
from discord.ext import commands

DEV_GUILD_ID = os.getenv("DEV_GUILD_ID")
guild_id_int = int(DEV_GUILD_ID) if DEV_GUILD_ID else 0

class SpawnDev(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def apenas_desenvolvedores():
        def predicate(interaction: discord.Interaction) -> bool:
            return interaction.user.id in interaction.client.developer_ids
        return app_commands.check(predicate)

    @app_commands.command(name="spawn", description="[DEV] Spawnar carta manualmente.")
    @app_commands.guilds(discord.Object(id=guild_id_int)) if guild_id_int else app_commands.guilds()
    @apenas_desenvolvedores()
    async def spawn(self, interaction: discord.Interaction):
        # Damos o defer de forma privada para o desenvolvedor para evitar o timeout de 3 segundos
        await interaction.response.defer(ephemeral=True)

        # Executa a função idêntica ao sistema automático contida no bot.py (usando o commands/embed.py global)
        sucesso = await self.bot.spawn_personagem(interaction.channel)

        if sucesso:
            await interaction.followup.send("✅ Spawn enviado com sucesso!")
        else:
            await interaction.followup.send("❌ Falha ao executar o spawn do personagem.")

async def setup(bot):
    await bot.add_cog(SpawnDev(bot))