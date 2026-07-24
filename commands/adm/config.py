import discord
from discord import app_commands
from discord.ext import commands
import asyncpg
import logging
from adm.embed_adm import embed_sucesso_monitoramento, embed_sucesso_spawn, embed_config_info

logger = logging.getLogger("CartoonDex.ConfigAdmin")


class ConfigAdmin(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.pool: asyncpg.Pool = bot.pool

    def apenas_administradores():
        """Verificador customizado que aceita administradores nativos ou o cargo configurado."""
        async def predicate(interaction: discord.Interaction) -> bool:
            # 1. Se for administrador nativo do servidor, sempre permite
            if interaction.user.guild_permissions.administrator:
                return True
            
            # 2. Se não, busca nas configurações salvas se existe um cargo ADM definido
            servidor_id = interaction.guild.id
            config_local = interaction.client.servidor_config.get(servidor_id, {})
            cargo_adm_id = config_local.get("cargo_adm_id")

            if cargo_adm_id:
                # Checa se o usuário possui o cargo na lista de cargos dele
                return any(role.id == cargo_adm_id for role in interaction.user.roles)

            return False
        return app_commands.check(predicate)

    async def _garantir_cache(self, servidor_id: int, conn):
        """Helper para garantir que o servidor tenha um registro no banco e no cache."""
        if servidor_id not in self.bot.servidor_config:
            row = await conn.fetchrow(
                "SELECT canal_spawn_id, canais_monitorados, cargo_adm_id FROM config_servidores WHERE servidor_id = $1", 
                servidor_id
            )
            if row:
                self.bot.servidor_config[servidor_id] = {
                    "canal_spawn_id": row["canal_spawn_id"],
                    "canais_monitorados": row["canais_monitorados"] or [],
                    "cargo_adm_id": row["cargo_adm_id"]
                }
            else:
                await conn.execute("INSERT INTO config_servidores (servidor_id) VALUES ($1) ON CONFLICT DO NOTHING", servidor_id)
                self.bot.servidor_config[servidor_id] = {"canal_spawn_id": None, "canais_monitorados": [], "cargo_adm_id": None}

    @app_commands.command(name="config_cargos", description="[ADM] Define um cargo que terá permissão de gerenciar o bot.")
    @apenas_administradores()
    @app_commands.describe(cargo="Escolha o cargo que poderá usar os comandos administrativos. Deixe em branco para resetar.")
    async def config_cargos(self, interaction: discord.Interaction, cargo: discord.Role = None):
        await interaction.response.defer(ephemeral=True)
        servidor_id = interaction.guild.id
        cargo_id = cargo.id if cargo else None

        try:
            async with self.pool.acquire() as conn:
                await self._garantir_cache(servidor_id, conn)

                # Atualiza no Neon usando config_servidores
                await conn.execute("""
                    UPDATE config_servidores 
                    SET cargo_adm_id = $2 
                    WHERE servidor_id = $1
                """, servidor_id, cargo_id)

                # Atualiza a memória RAM do bot
                self.bot.servidor_config[servidor_id]["cargo_adm_id"] = cargo_id

            if cargo:
                await interaction.followup.send(f"✅ Sucesso! Membros com o cargo {cargo.mention} agora também podem configurar o bot.", ephemeral=True)
            else:
                await interaction.followup.send("✅ Configuração resetada! Apenas administradores nativos do servidor podem configurar o bot agora.", ephemeral=True)

        except Exception as e:
            logger.error(f"Erro no /config_cargos: {e}")
            await interaction.followup.send("⚠️ Erro ao salvar o cargo administrativo no banco Neon.", ephemeral=True)

    @app_commands.command(name="config_chats", description="[ADM] Adiciona ou remove um canal da lista de monitoramento.")
    @apenas_administradores()
    async def config_chats(self, interaction: discord.Interaction, canal: discord.TextChannel):
        await interaction.response.defer(ephemeral=True)
        servidor_id = interaction.guild.id

        try:
            async with self.pool.acquire() as conn:
                await self._garantir_cache(servidor_id, conn)
                canais_atuais = list(self.bot.servidor_config[servidor_id]["canais_monitorados"])

                if canal.id in canais_atuais:
                    canais_atuais.remove(canal.id)
                    adicionado = False
                else:
                    canais_atuais.append(canal.id)
                    adicionado = True

                await conn.execute("""
                    UPDATE config_servidores 
                    SET canais_monitorados = $2 
                    WHERE servidor_id = $1
                """, servidor_id, canais_atuais)

                self.bot.servidor_config[servidor_id]["canais_monitorados"] = canais_atuais

            resposta = embed_sucesso_monitoramento(canal.mention, adicionado)
            await interaction.followup.send(content=resposta if isinstance(resposta, str) else None, embed=resposta if isinstance(resposta, discord.Embed) else None, ephemeral=True)

        except Exception as e:
            logger.error(f"Erro no /config_chats: {e}")
            await interaction.followup.send("⚠️ Erro ao atualizar os canais monitorados no banco Neon.", ephemeral=True)

    @app_commands.command(name="config_spawn", description="[ADM] Configura o canal principal para spawn de cartas.")
    @apenas_administradores()
    async def config_spawn(self, interaction: discord.Interaction, canal: discord.TextChannel):
        await interaction.response.defer(ephemeral=True)
        servidor_id = interaction.guild.id

        try:
            async with self.pool.acquire() as conn:
                await self._garantir_cache(servidor_id, conn)

                await conn.execute("""
                    UPDATE config_servidores 
                    SET canal_spawn_id = $2 
                    WHERE servidor_id = $1
                """, servidor_id, canal.id)

                self.bot.servidor_config[servidor_id]["canal_spawn_id"] = canal.id

            resposta = embed_sucesso_spawn(canal.mention)
            await interaction.followup.send(content=resposta if isinstance(resposta, str) else None, embed=resposta if isinstance(resposta, discord.Embed) else None, ephemeral=True)

        except Exception as e:
            logger.error(f"Erro no /config_spawn: {e}")
            await interaction.followup.send("⚠️ Erro ao salvar o canal de spawn no banco Neon.", ephemeral=True)

    @app_commands.command(name="config_info", description="[ADM] Exibe o painel com as configurações atuais de canais.")
    @apenas_administradores()
    async def config_info(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        servidor_id = interaction.guild.id

        try:
            async with self.pool.acquire() as conn:
                await self._garantir_cache(servidor_id, conn)

            config_local = self.bot.servidor_config[servidor_id]
            canal_spawn = config_local.get("canal_spawn_id")
            canais_monitorados = config_local.get("canais_monitorados", [])

            embed = embed_config_info(canal_spawn, canais_monitorados)
            await interaction.followup.send(embed=embed, ephemeral=True)

        except Exception as e:
            logger.error(f"Erro no /config_info: {e}")
            await interaction.followup.send("⚠️ Erro ao carregar as informações de configuração.", ephemeral=True)


async def setup(bot):
    await bot.add_cog(ConfigAdmin(bot))