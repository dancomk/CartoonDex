import math
import string
from enum import Enum
from typing import Optional

import asyncpg
import discord
from discord import app_commands
from discord.ext import commands

from .embed_inventario import (
    embed_inventario_cartas,
    embed_inventario_molduras,
    embed_inventario_itens
)

ITENS_POR_PAGINA = 10

# --- SISTEMA DE EMBARALHAMENTO DO ID GLOBAL (TCG STYLE) ---
ALFABETO = string.digits + string.ascii_uppercase
PRIMO = 41359727
MODULO = 36**6


def numero_para_codigo_aleatorio(num: int) -> str:
    """Embaralha o ID SERIAL único do banco em um hash de 6 dígitos."""
    if not num:
        return "000000"
    embaralhado = (num * PRIMO) % MODULO
    codigo = ""
    for _ in range(6):
        embaralhado, resto = divmod(embaralhado, 36)
        codigo = ALFABETO[resto] + codigo
    return codigo


class TipoInventario(Enum):
    cartas = "cartas"
    molduras = "molduras"
    itens = "itens"


class OrdenacaoCartas(Enum):
    recentes = "recentes"
    dex = "dex"


class InventarioView(discord.ui.View):
    def __init__(self, author_id, categoria, dados_gerais, total_paginas, cog, extra_info=0, ordenacao=None, str_user_id=None):
        super().__init__(timeout=180)
        self.author_id = author_id
        self.categoria = categoria
        self.dados_gerais = dados_gerais  # Rows do banco
        self.total_paginas = total_paginas
        self.pagina_atual = 1
        self.cog = cog
        self.extra_info = extra_info      # Total absoluto
        self.ordenacao = ordenacao        # Estado do filtro de cartas ou de molduras
        self.str_user_id = str_user_id    # VARCHAR(50) do membro_id
        self.direcao_recentes = "DESC"    # Padrão: Mais novas no topo
        
        # Ajusta visibilidade e estilos dos botões especiais baseado na categoria ativa
        if self.categoria == TipoInventario.cartas.value:
            self.btn_filtro_molduras.disabled = True
            self.btn_filtro_molduras.style = discord.ButtonStyle.gray
            if self.ordenacao != OrdenacaoCartas.recentes.value:
                self.btn_inverter.disabled = True
                self.btn_inverter.style = discord.ButtonStyle.gray
        elif self.categoria == TipoInventario.molduras.value:
            self.btn_inverter.disabled = True
            self.btn_inverter.style = discord.ButtonStyle.gray
            if self.ordenacao == "raridade":
                self.btn_filtro_molduras.label = "✨ Raridade"
            elif self.ordenacao == "alfabetica":
                self.btn_filtro_molduras.label = "🔤 Nome (A-Z)"
            else:
                self.btn_filtro_molduras.label = "⏱️ Recentes"
        else:
            self.btn_inverter.disabled = True
            self.btn_inverter.style = discord.ButtonStyle.gray
            self.btn_filtro_molduras.disabled = True
            self.btn_filtro_molduras.style = discord.ButtonStyle.gray

        self.atualizar_botoes()

    def atualizar_botoes(self):
        is_paginado = self.total_paginas > 1
        self.btn_primeira.disabled = not is_paginado or self.pagina_atual == 1
        self.btn_anterior.disabled = not is_paginado or self.pagina_atual == 1
        self.btn_proxima.disabled = not is_paginado or self.pagina_atual == self.total_paginas
        self.btn_ultima.disabled = not is_paginado or self.pagina_atual == self.total_paginas

    async def atualizar_embed(self, interaction: discord.Interaction):
        self.atualizar_botoes()
        
        inicio = (self.pagina_atual - 1) * ITENS_POR_PAGINA
        fim = inicio + ITENS_POR_PAGINA
        fatia = self.dados_gerais[inicio:fim]
        
        if self.categoria == TipoInventario.cartas.value:
            embed = embed_inventario_cartas(
                fatia_cartas=fatia, 
                pagina_atual=self.pagina_atual, 
                total_paginas=self.total_paginas, 
                total_cartas=self.extra_info, 
                ordenacao=self.ordenacao,
                inicio_fria=inicio + 1,
                direcao=self.direcao_recentes,
                bot=self.cog.bot
            )
        elif self.categoria == TipoInventario.molduras.value:
            embed = embed_inventario_molduras(fatia, self.pagina_atual, self.total_paginas, self.extra_info, self.ordenacao)
        else:
            embed = embed_inventario_itens(fatia, self.pagina_atual, self.total_paginas, self.extra_info)

        await interaction.response.edit_message(embed=embed, view=self)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.author_id:
            await interaction.response.send_message(
                "❌ Não podes usar os botões do inventário de outra pessoa.", ephemeral=True
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

    @discord.ui.button(label="🔄 Inverter", style=discord.ButtonStyle.gray)
    async def btn_inverter(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.categoria != TipoInventario.cartas.value or self.ordenacao != OrdenacaoCartas.recentes.value:
            return

        self.direcao_recentes = "ASC" if self.direcao_recentes == "DESC" else "DESC"
        self.dados_gerais.reverse()
        self.pagina_atual = 1
        await self.atualizar_embed(interaction)

    @discord.ui.button(label="⏱️ Recentes", style=discord.ButtonStyle.gray)
    async def btn_filtro_molduras(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.categoria != TipoInventario.molduras.value:
            return

        if self.ordenacao == "recentes":
            self.ordenacao = "raridade"
            button.label = "✨ Raridade"
        elif self.ordenacao == "raridade":
            self.ordenacao = "alfabetica"
            button.label = "🔤 Nome (A-Z)"
        else:
            self.ordenacao = "recentes"
            button.label = "⏱️ Recentes"

        async with self.cog.pool.acquire() as conn:
            if self.ordenacao == "raridade":
                query = """
                    SELECT im.*, m.nome, m.raridade 
                    FROM inventario_molduras im
                    JOIN molduras m ON im.moldura_id = m.id
                    WHERE im.membro_id = $1
                    ORDER BY m.raridade_ordem DESC, im.adquirido_em DESC;
                """
            elif self.ordenacao == "alfabetica":
                query = """
                    SELECT im.*, m.nome, m.raridade 
                    FROM inventario_molduras im
                    JOIN molduras m ON im.moldura_id = m.id
                    WHERE im.membro_id = $1
                    ORDER BY m.nome ASC;
                """
            else:
                query = """
                    SELECT im.*, m.nome, m.raridade 
                    FROM inventario_molduras im
                    JOIN molduras m ON im.moldura_id = m.id
                    WHERE im.membro_id = $1
                    ORDER BY im.adquirido_em DESC;
                """
            rows = await conn.fetch(query, self.str_user_id)

        self.dados_gerais = [dict(r) for r in rows]
        self.pagina_atual = 1
        await self.atualizar_embed(interaction)


class Inventario(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.pool: asyncpg.Pool = bot.pool

    @app_commands.command(name="inventario", description="Acesse seu inventário de cartas, molduras ou itens.")
    @app_commands.describe(
        categoria="O que você deseja visualizar?",
        ordenar="Como deseja ordenar (apenas para cartas)?"
    )
    async def inventario(
        self, 
        interaction: discord.Interaction, 
        categoria: TipoInventario, 
        ordenar: Optional[OrdenacaoCartas] = None
    ):
        await interaction.response.defer()
        user_id = interaction.user.id
        str_user_id = str(user_id)

        ordem_selecionada = ordenar.value if ordenar else OrdenacaoCartas.recentes.value

        async with self.pool.acquire() as conn:
            if categoria == TipoInventario.cartas:
                if ordem_selecionada == OrdenacaoCartas.dex.value:
                    query = """
                        SELECT i.*, d.nome, d.skin_nome 
                        FROM inventario_cartas i
                        JOIN dex d ON i.carta_id = d.carta_id
                        WHERE i.membro_id = $1
                        ORDER BY i.numero_dex ASC, i.skin_id ASC, i.data_pessoal ASC;
                    """
                else:
                    query = """
                        SELECT i.*, d.nome, d.skin_nome 
                        FROM inventario_cartas i
                        JOIN dex d ON i.carta_id = d.carta_id
                        WHERE i.membro_id = $1
                        ORDER BY i.data_pessoal DESC, i.id DESC;
                    """
                rows = await conn.fetch(query, str_user_id)

            elif categoria == TipoInventario.molduras:
                query = """
                    SELECT im.*, m.nome, m.raridade 
                    FROM inventario_molduras im
                    JOIN molduras m ON im.moldura_id = m.id
                    WHERE im.membro_id = $1
                    ORDER BY im.adquirido_em DESC;
                """
                rows = await conn.fetch(query, str_user_id)

            else:
                query = """
                    SELECT * FROM inventario_itens
                    WHERE membro_id = $1;
                """
                rows = await conn.fetch(query, str_user_id)

        dados = [dict(r) for r in rows]
        total_itens = len(dados)

        if total_itens == 0:
            return await interaction.followup.send(
                f"📦 Seu inventário de **{categoria.value}** está vazio.",
                ephemeral=True
            )

        total_paginas = math.ceil(total_itens / ITENS_POR_PAGINA)
        view = InventarioView(
            author_id=user_id, 
            categoria=categoria.value, 
            dados_gerais=dados, 
            total_paginas=total_paginas, 
            cog=self, 
            extra_info=total_itens, 
            ordenacao=ordem_selecionada if categoria == TipoInventario.cartas else "recentes",
            str_user_id=str_user_id
        )

        fatia = dados[0:ITENS_POR_PAGINA]

        if categoria == TipoInventario.cartas:
            embed = embed_inventario_cartas(
                fatia_cartas=fatia, 
                pagina_atual=1, 
                total_paginas=total_paginas, 
                total_cartas=total_itens, 
                ordenacao=ordem_selecionada,
                inicio_fria=1,
                direcao="DESC",
                bot=self.bot
            )
        elif categoria == TipoInventario.molduras:
            embed = embed_inventario_molduras(fatia, 1, total_paginas, total_itens, "recentes")
        else:
            embed = embed_inventario_itens(fatia, 1, total_paginas, total_itens)

        await interaction.followup.send(embed=embed, view=view)


async def setup(bot):
    await bot.add_cog(Inventario(bot))