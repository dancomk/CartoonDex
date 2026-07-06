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

    @app_commands.command(name="spawn", description="[DEV] Força o disparo do spawn automático do bot.")
    @app_commands.guilds(discord.Object(id=guild_id_int)) if guild_id_int else app_commands.guilds()
    @apenas_desenvolvedores()
    async def spawn(self, interaction: discord.Interaction):
        # Damos o defer privado para evitar o timeout de 3 segundos no Discord
        await interaction.response.defer(ephemeral=True)

        try:
            # Roda diretamente a função nativa e oficial que o bot.py executa após contar as mensagens
            sucesso = await self.bot.spawn_personagem(interaction.channel)

            if sucesso:
                await interaction.followup.send("✅ Spawn automático disparado e enviado no canal com sucesso!")
            else:
                await interaction.followup.send("❌ A função de spawn do bot retornou FALSO (verifique as condições no bot.py).")

        except Exception as e:
            print(f"❌ Erro ao invocar o spawn automático do bot: {e}")
            await interaction.followup.send(f"❌ Erro crítico ao rodar o spawn do bot.py: {e}")

async def setup(bot):
    await bot.add_cog(SpawnDev(bot))