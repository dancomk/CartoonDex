# commands/adm/config.py
import discord
from discord import app_commands
from discord.ext import commands
import asyncpg
from .embed_adm import embed_sucesso_monitoramento, embed_sucesso_spawn, embed_config_info

class ConfigAdmin(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.pool: asyncpg.Pool = bot.pool

    def apenas_administradores():
        def predicate(interaction: discord.Interaction) -> bool:
            return interaction.user.guild_permissions.administrator
        return app_commands.check(predicate)

    @app_commands.command(name="config_chats", description="[ADM] Adiciona ou remove um canal da lista de monitoramento.")
    @apenas_administradores()
    async def config_chats(self, interaction: discord.Interaction, canal: discord.TextChannel):
        await interaction.response.defer(ephemeral=True)
        # Sua lógica de banco aqui...
        adicionado = True 
        resposta = embed_sucesso_monitoramento(canal.mention, adicionado)
        await interaction.followup.send(resposta, ephemeral=True)

    @app_commands.command(name="config_spawn", description="[ADM] Configura o canal principal para spawn de cartas.")
    @apenas_administradores()
    async def config_spawn(self, interaction: discord.Interaction, canal: discord.TextChannel):
        await interaction.response.defer(ephemeral=True)
        # Sua lógica de banco aqui...
        resposta = embed_sucesso_spawn(canal.mention)
        await interaction.followup.send(resposta, ephemeral=True)

    @app_commands.command(name="config_info", description="[ADM] Exibe o painel com as configurações atuais de canais.")
    @apenas_administradores()
    async def config_info(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        # Buscando os dados que estão salvos temporariamente na memória do bot
        # (Posteriormente, buscaremos do Banco de Dados aqui)
        canal_spawn = getattr(self.bot, "canal_spawn_configurado", None)
        canais_monitorados = getattr(self.bot, "spawn_channel_ids", [])

        embed = embed_config_info(canal_spawn, canais_monitorados)
        await interaction.followup.send(embed=embed, ephemeral=True)

async def setup(bot):
    await bot.add_cog(ConfigAdmin(bot))