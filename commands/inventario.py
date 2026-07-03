import discord
from discord import app_commands
from discord.ext import commands
import math
import asyncpg
from .embed import embed_inventario
from utils import formatar_lista_cartas

ITENS_POR_PAGINA = 10

class InventarioView(discord.ui.View):
    def __init__(self, author_id, lista_ids, dados_cartas, total_cartas_absoluto, total_paginas, cog):
        super().__init__(timeout=180)
        self.author_id = author_id
        self.lista_ids = lista_ids
        self.dados_cartas = dados_cartas
        self.total_cartas_absoluto = total_cartas_absoluto
        self.total_paginas = total_paginas
        self.pagina_atual = 1
        self.cog = cog
        self.atualizar_botoes()

    def atualizar_botoes(self):
        self.btn_primeira.disabled = self.pagina_atual == 1
        self.btn_anterior.disabled = self.pagina_atual == 1
        self.btn_proxima.disabled = self.pagina_atual == self.total_paginas
        self.btn_ultima.disabled = self.pagina_atual == self.total_paginas

    async def atualizar_embed(self, interaction: discord.Interaction):
        descricao = self.cog.montar_descricao(self.lista_ids, self.dados_cartas, self.pagina_atual)
        embed = embed_inventario(descricao, self.pagina_atual, self.total_paginas, self.total_cartas_absoluto)
        self.atualizar_botoes()
        await interaction.response.edit_message(embed=embed, view=self)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.author_id:
            await interaction.response.send_message(
                "Você não pode usar os botões do inventário de outra pessoa.", ephemeral=True
            )
            return False
        return True

    @discord.ui.button(label="⏮️", style=discord.ButtonStyle.blurple)
    async def btn_primeira(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.pagina_atual = 1
        await self.atualizar_embed(interaction)

    @discord.ui.button(label="◀️", style=discord.ButtonStyle.blurple)
    async def btn_anterior(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.pagina_atual > 1:
            self.pagina_atual -= 1
        await self.atualizar_embed(interaction)

    @discord.ui.button(label="▶️", style=discord.ButtonStyle.blurple)
    async def btn_proxima(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.pagina_atual < self.total_paginas:
            self.pagina_atual += 1
        await self.atualizar_embed(interaction)

    @discord.ui.button(label="⏭️", style=discord.ButtonStyle.blurple)
    async def btn_ultima(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.pagina_atual = self.total_paginas
        await self.atualizar_embed(interaction)


class Inventario(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.pool: asyncpg.Pool = bot.pool

    @app_commands.command(name="inventario", description="Ver as cartas que você já coletou.")
    async def inventario(self, interaction: discord.Interaction):
        user_id = interaction.user.id

        async with self.pool.acquire() as conn:
            # ALTERAÇÃO: O JOIN agora cruza as tabelas usando dex e skin_id diretamente
            rows = await conn.fetch("""
                SELECT d.dex, d.nome, d.skin_id, d.skin, COALESCE(i.quantidade, 0) AS quantidade
                FROM dex d
                LEFT JOIN inventario i ON i.dex = d.dex AND i.skin_id = d.skin_id AND i.user_id = $1
                ORDER BY d.dex ASC, d.skin_id ASC;
            """, user_id)

        cartas_dict = {}
        total_cartas_absoluto = 0

        for row in rows:
            box = row["dex"]
            if box not in cartas_dict:
                cartas_dict[box] = {"nome": row["nome"], "total_usuario": 0, "skins_capturadas": {}}
            
            qtd = row["quantidade"]
            if qtd > 0:
                cartas_dict[box]["total_usuario"] += qtd
                cartas_dict[box]["skins_capturadas"][row["skin_id"]] = (row["skin"], qtd)
                total_cartas_absoluto += qtd

        lista_filtrada = [dex for dex, info in cartas_dict.items() if info["total_usuario"] > 0]
        lista_filtrada.sort()

        if not lista_filtrada:
            await interaction.response.send_message(
                "📦 Seu inventário está vazio! Você ainda não capturou nenhuma carta.", ephemeral=True
            )
            return

        total_paginas = math.ceil(len(lista_filtrada) / ITENS_POR_PAGINA)
        view = InventarioView(user_id, lista_filtrada, cartas_dict, total_cartas_absoluto, total_paginas, self)
        
        descricao = self.montar_descricao(lista_filtrada, cartas_dict, 1)
        embed = embed_inventario(descricao, 1, total_paginas, total_cartas_absoluto)

        await interaction.response.send_message(embed=embed, view=view)

    def montar_descricao(self, lista_ids, cartas_dict, pagina):
        return formatar_lista_cartas(lista_ids, cartas_dict, pagina, tipo_comando="inventario")


async def setup(bot):
    await bot.add_cog(Inventario(bot))