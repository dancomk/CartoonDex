import discord
from discord import app_commands
from discord.ext import commands
import math
import asyncpg
from .embed import embed_dex
from utils import formatar_lista_cartas

ITENS_POR_PAGINA = 10

class DexView(discord.ui.View):
    def __init__(self, author_id, lista_ids, dados_cartas, total_paginas, cog):
        super().__init__(timeout=180)
        self.author_id = author_id
        self.lista_ids = lista_ids
        self.dados_cartas = dados_cartas
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
        embed = embed_dex(descricao, self.pagina_atual, self.total_paginas, len(self.lista_ids))
        self.atualizar_botoes()
        await interaction.response.edit_message(embed=embed, view=self)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.author_id:
            await interaction.response.send_message(
                "Você não pode usar os botões da dex de outra pessoa.", ephemeral=True
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


class Dex(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.pool: asyncpg.Pool = bot.pool

    @app_commands.command(name="dex", description="Ver a lista completa de cartas do bot.")
    async def dex(self, interaction: discord.Interaction):
        user_id = interaction.user.id
        str_user_id = str(user_id)  # inventario_cartas usa VARCHAR(50) para membro_id

        # ULTRA OTIMIZAÇÃO: Usamos o cache bot.dex para obter a lista de cartas globais cadastrados
        # e buscamos no banco apenas o inventário do membro específico.
        if not self.bot.dex:
            await interaction.response.send_message(
                "⚠️ Nenhuma carta cadastrada no sistema geral da Dex.", ephemeral=True
            )
            return

        async with self.pool.acquire() as conn:
            # Puxa apenas o inventário de cartas do jogador
            rows = await conn.fetch("""
                SELECT carta_id, SUM(quantidade) AS total
                FROM inventario_cartas
                WHERE membro_id = $1
                GROUP BY carta_id;
            """, str_user_id)
        
        # Mapeia as quantidades obtidas pelo usuário para cruzamento ágil
        inventario_usuario = {row["carta_id"]: row["total"] for row in rows}

        cartas_dict = {}
        # Reconstrói a estrutura esperada utilizando os dados em memória (bot.dex) sincronizados com o banco
        for carta_id, dados in self.bot.dex.items():
            box = dados["numero_dex"]
            
            if box not in cartas_dict:
                cartas_dict[box] = {
                    "nome": dados["nome"],
                    "total_usuario": 0,
                    "skins_capturadas": {}
                }
            
            qtd = inventario_usuario.get(carta_id, 0)
            if qtd > 0:
                cartas_dict[box]["total_usuario"] += qtd
                # CORREÇÃO: Alterado de dados.get("skin_name") para dados.get("skin_nome")
                cartas_dict[box]["skins_capturadas"][dados["skin_id"]] = (dados.get("skin_nome"), qtd)

        lista_completa = sorted(list(cartas_dict.keys()))

        total_paginas = math.ceil(len(lista_completa) / ITENS_POR_PAGINA)
        view = DexView(user_id, lista_completa, cartas_dict, total_paginas, self)
        
        descricao = self.montar_descricao(lista_completa, cartas_dict, 1)
        embed = embed_dex(descricao, 1, total_paginas, len(lista_completa))

        await interaction.response.send_message(embed=embed, view=view)

    def montar_descricao(self, lista_ids, cartas_dict, pagina):
        return formatar_lista_cartas(lista_ids, cartas_dict, pagina, tipo_comando="dex")


async def setup(bot):
    await bot.add_cog(Dex(bot))