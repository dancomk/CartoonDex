import random
import asyncio
import logging
import discord
from discord.ext import commands

logger = logging.getLogger("CartoonDex.Spawn")


class SpawnCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def spawn_personagem(self, canal, interaction: discord.Interaction = None) -> bool:
        """Sorteia e envia um personagem no canal especificado."""
        carta = await self.bot.buscar_carta_aleatoria()

        if not carta:
            msg_erro = "⚠️ Nenhuma carta encontrada no banco de dados."
            if interaction:
                if interaction.response.is_done():
                    await interaction.followup.send(msg_erro, ephemeral=True)
                else:
                    await interaction.response.send_message(msg_erro, ephemeral=True)
            else:
                await canal.send(msg_erro)
            return False

        carta_id = carta.get("carta_id") or f"{self.bot.limpar_dex(carta.get('numero_dex', '0000'))}-{carta.get('skin_id', 0)}"

        self.bot.current_spawn[canal.id] = carta
        self.bot.tentativas_erradas[canal.id] = 0

        from commands.embed import embed_spawn

        buffer_spawn, filename = await asyncio.to_thread(self.bot.obter_bytes_carta_spawn, carta, carta_id)

        if not buffer_spawn:
            logger.error(f"❌ Não foi possível gerar os bytes da carta para o spawn ({carta_id}).")
            return False

        file = discord.File(fp=buffer_spawn, filename=filename)

        embed = embed_spawn(
            nome="?????",
            raridade=carta.get("raridade", "Desconhecida")
        )
        embed.set_image(url=f"attachment://{filename}")

        await canal.send(embed=embed, file=file)
        return True

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """Escuta as mensagens enviadas nos canais para contabilizar e disparar o spawn."""
        if message.author.bot or not message.guild:
            return

        servidor_id = message.guild.id
        if servidor_id not in self.bot.servidor_config:
            await self.bot.obter_canal_spawn(servidor_id)

        config = self.bot.servidor_config.get(servidor_id, {"canal_spawn_id": None, "canais_monitorados": []})
        canal_spawn_id = config.get("canal_spawn_id")
        canais_monitorados = config.get("canais_monitorados", [])

        if canais_monitorados and message.channel.id not in canais_monitorados:
            return

        self.bot.contador_mensagens[message.channel.id] = self.bot.contador_mensagens.get(message.channel.id, 0) + 1

        if self.bot.contador_mensagens[message.channel.id] >= 15:
            self.bot.contador_mensagens[message.channel.id] = 0

            if random.random() <= 0.6:
                canal_destino = self.bot.get_channel(canal_spawn_id) if canal_spawn_id else message.channel
                if canal_destino:
                    await self.spawn_personagem(canal_destino)


async def setup(bot):
    cog = SpawnCog(bot)
    # Mantém compatibilidade com referências legadas caso algum outro módulo chame bot.spawn_personagem
    bot.spawn_personagem = cog.spawn_personagem
    await bot.add_cog(cog)