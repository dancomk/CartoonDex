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
        str_user_id = str(user_id)  # inventario_cartas usa VARCHAR(50) para membro_id

        if not self.bot.dex:
            await interaction.response.send_message(
                "📦 Seu inventário está vazio! Nenhuma carta cadastrada no sistema geral.", ephemeral=True
            )
            return

        async with self.pool.acquire() as conn:
            # Puxa apenas os registros que o usuário possui de fato, agrupados por carta_id
            rows = await conn.fetch("""
                SELECT carta_id, SUM(quantidade) AS total
                FROM inventario_cartas
                WHERE membro_id = $1
                GROUP BY carta_id;
            """, str_user_id)

        if not rows:
            await interaction.response.send_message(
                "📦 Seu inventário está vazio! Você ainda não capturou nenhuma carta.", ephemeral=True
            )
            return

        # Mapeia o inventário do usuário obtido do banco
        inventario_usuario = {row["carta_id"]: row["total"] for row in rows}

        cartas_dict = {}
        total_cartas_absoluto = 0

        # Preenche a estrutura cruzando as chaves que o usuário possui com o cache do bot
        for carta_id, dados in self.bot.dex.items():
            qtd = inventario_usuario.get(carta_id, 0)
            if qtd > 0:
                box = dados["numero_dex"]
                
                if box not in cartas_dict:
                    cartas_dict[box] = {
                        "nome": dados["nome"],
                        "total_usuario": 0,
                        "skins_capturadas": {}
                    }
                
                cartas_dict[box]["total_usuario"] += qtd
                # Modificado para usar a chave skin_nome conforme mapeamento do banco
                cartas_dict[box]["skins_capturadas"][dados["skin_id"]] = (dados.get("skin_nome"), qtd)
                total_cartas_absoluto += qtd

        # Filtra apenas as caixas que o usuário realmente possui cópias
        lista_filtrada = [dex for dex, info in cartas_dict.items() if info["total_usuario"] > 0]
        lista_filtrada.sort()

        if not lista_filtrada:
            await interaction.response.send_message(
                "📦 Seu inventário está vazio! Você ainda não possui cartas válidas.", ephemeral=True
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