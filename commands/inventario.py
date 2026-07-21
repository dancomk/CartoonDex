import discord
from discord import app_commands
from discord.ext import commands
import math
import asyncpg
import string
from enum import Enum

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
            # Atualiza o rótulo inicial baseado no filtro de entrada
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

    @discord.ui.button(label="↕️", style=discord.ButtonStyle.success)
    async def btn_inverter(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Alterna a direção de busca das cartas recentes (DESC <-> ASC)."""
        self.direcao_recentes = "ASC" if self.direcao_recentes == "DESC" else "DESC"
        
        async with self.cog.pool.acquire() as conn:
            if self.direcao_recentes == "DESC":
                self.dados_gerais = await conn.fetch("""
                    SELECT id, numero_dex, skin_id, moldura_id, nivel 
                    FROM inventario_cartas WHERE membro_id = $1 ORDER BY data_pessoal DESC, id DESC;
                """, self.str_user_id)
            else:
                self.dados_gerais = await conn.fetch("""
                    SELECT id, numero_dex, skin_id, moldura_id, nivel 
                    FROM inventario_cartas WHERE membro_id = $1 ORDER BY data_pessoal ASC, id ASC;
                """, self.str_user_id)
        
        self.pagina_atual = 1
        await self.atualizar_embed(interaction)

    @discord.ui.button(label="⏱️ Recentes", style=discord.ButtonStyle.primary)
    async def btn_filtro_molduras(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Alterna ciclicamente entre: recentes -> raridade -> alfabetica."""
        async with self.cog.pool.acquire() as conn:
            if self.ordenacao == "recentes":
                self.ordenacao = "raridade"
                button.label = "✨ Raridade"
                self.dados_gerais = await conn.fetch("""
                    SELECT im.moldura_id, im.quantidade, im.data_pessoal, lm.nome, lm.raridade
                    FROM inventario_molduras im
                    JOIN loja_molduras lm ON im.moldura_id = lm.moldura_id
                    WHERE im.membro_id = $1
                    ORDER BY 
                        CASE LOWER(lm.raridade)
                            WHEN 'lendaria' THEN 1
                            WHEN 'epica'    THEN 2
                            WHEN 'rara'     THEN 3
                            WHEN 'comum'    THEN 4
                            ELSE 5
                        END ASC,
                        lm.nome ASC;
                """, self.str_user_id)
            elif self.ordenacao == "raridade":
                self.ordenacao = "alfabetica"
                button.label = "🔤 Nome (A-Z)"
                self.dados_gerais = await conn.fetch("""
                    SELECT im.moldura_id, im.quantidade, im.data_pessoal, lm.nome, lm.raridade
                    FROM inventario_molduras im
                    JOIN loja_molduras lm ON im.moldura_id = lm.moldura_id
                    WHERE im.membro_id = $1
                    ORDER BY lm.nome ASC;
                """, self.str_user_id)
            else:
                self.ordenacao = "recentes"
                button.label = "⏱️ Recentes"
                self.dados_gerais = await conn.fetch("""
                    SELECT im.moldura_id, im.quantidade, im.data_pessoal, lm.nome, lm.raridade
                    FROM inventario_molduras im
                    JOIN loja_molduras lm ON im.moldura_id = lm.moldura_id
                    WHERE im.membro_id = $1
                    ORDER BY im.data_pessoal DESC;
                """, self.str_user_id)

        self.pagina_atual = 1
        await self.atualizar_embed(interaction)


class Inventario(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.pool: asyncpg.Pool = bot.pool

    @app_commands.command(name="inventario", description="Exibe as tuas cartas, molduras ou itens adquiridos!")
    @app_commands.describe(
        categoria="Escolhe qual a categoria do teu inventário desejas visualizar.",
        organizar="Como deseja ordenar suas cartas (Apenas se escolher a categoria Cartas)."
    )
    @app_commands.choices(
        categoria=[
            app_commands.Choice(name="🃏 Cartas", value=TipoInventario.cartas.value),
            app_commands.Choice(name="🖼️ Molduras", value=TipoInventario.molduras.value),
            app_commands.Choice(name="🎒 Itens", value=TipoInventario.itens.value)
        ],
        organizar=[
            app_commands.Choice(name="⏱️ Recentes (Carta Única)", value=OrdenacaoCartas.recentes.value),
            app_commands.Choice(name="🔢 Número da Dex (Agrupado)", value=OrdenacaoCartas.dex.value)
        ]
    )
    async def inventario(self, interaction: discord.Interaction, categoria: str, organizar: str = "recentes"):
        await interaction.response.defer(ephemeral=False)
        
        user_id = interaction.user.id
        str_user_id = str(user_id)

        if categoria == TipoInventario.cartas.value:
            await self._processar_cartas(interaction, str_user_id, user_id, organizar)
        elif categoria == TipoInventario.molduras.value:
            await self._processar_molduras(interaction, str_user_id, user_id)
        elif categoria == TipoInventario.itens.value:
            await self._processar_itens(interaction, str_user_id, user_id)

    async def _processar_cartas(self, interaction: discord.Interaction, str_user_id: str, user_id: int, ordenar: str):
        async with self.pool.acquire() as conn:
            if ordenar == OrdenacaoCartas.recentes.value:
                rows = await conn.fetch("""
                    SELECT id, numero_dex, skin_id, moldura_id, nivel 
                    FROM inventario_cartas WHERE membro_id = $1 ORDER BY data_pessoal DESC, id DESC;
                """, str_user_id)
                
                if not rows:
                    return await interaction.followup.send("📦 O teu inventário de cartas está vazio!", ephemeral=True)
                
                total_cartas_absoluto = len(rows)
                total_paginas = math.ceil(total_cartas_absoluto / ITENS_POR_PAGINA)
                
            else:
                rows = await conn.fetch("""
                    SELECT numero_dex, skin_id, moldura_id, nivel, COUNT(*) as quantidade, SUM(COUNT(*)) OVER() as total_absoluto
                    FROM inventario_cartas WHERE membro_id = $1
                    GROUP BY numero_dex, skin_id, moldura_id, nivel ORDER BY numero_dex ASC;
                """, str_user_id)
                
                if not rows:
                    return await interaction.followup.send("📦 O teu inventário de cartas está vazio!", ephemeral=True)
                
                total_cartas_absoluto = rows[0]["total_absoluto"]
                total_paginas = math.ceil(len(rows) / ITENS_POR_PAGINA)

        view = InventarioView(
            author_id=user_id, 
            categoria=TipoInventario.cartas.value, 
            dados_gerais=rows, 
            total_paginas=total_paginas, 
            cog=self, 
            extra_info=total_cartas_absoluto,
            ordenacao=ordenar,
            str_user_id=str_user_id
        )
        
        fatia_inicial = rows[0:ITENS_POR_PAGINA]
        embed = embed_inventario_cartas(
            fatia_cartas=fatia_inicial, 
            pagina_atual=1, 
            total_paginas=total_paginas, 
            total_cartas=total_cartas_absoluto, 
            ordenacao=ordenar,
            inicio_fria=1, 
            direcao="DESC",
            bot=self.bot
        )
        await interaction.followup.send(embed=embed, view=view)

    async def _processar_molduras(self, interaction: discord.Interaction, str_user_id: str, user_id: int):
        async with self.pool.acquire() as conn:
            # Padrão Inicial: Ordem de Compra (Mais recentes primeiro através de data_pessoal)
            rows = await conn.fetch("""
                SELECT im.moldura_id, im.quantidade, im.data_pessoal, lm.nome, lm.raridade
                FROM inventario_molduras im
                JOIN loja_molduras lm ON im.moldura_id = lm.moldura_id
                WHERE im.membro_id = $1 
                ORDER BY im.data_pessoal DESC;
            """, str_user_id)

        if not rows:
            return await interaction.followup.send("📦 Não possuis nenhuma moldura cosmética.", ephemeral=True)

        total_molduras = len(rows)
        total_paginas = math.ceil(total_molduras / ITENS_POR_PAGINA)
        
        view = InventarioView(
            author_id=user_id,
            categoria=TipoInventario.molduras.value,
            dados_gerais=rows,
            total_paginas=total_paginas,
            cog=self,
            extra_info=total_molduras,
            ordenacao="recentes",
            str_user_id=str_user_id
        )
        
        fatia_inicial = rows[0:ITENS_POR_PAGINA]
        embed = embed_inventario_molduras(fatia_inicial, 1, total_paginas, total_molduras, "recentes")
        await interaction.followup.send(embed=embed, view=view)

    async def _processar_itens(self, interaction: discord.Interaction, str_user_id: str, user_id: int):
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT item_id, quantidade FROM inventario_itens WHERE membro_id = $1 ORDER BY item_id ASC
            """, str_user_id)

        if not rows:
            return await interaction.followup.send("📦 O teu inventário de itens está vazio.", ephemeral=True)

        embed = embed_inventario_itens(rows)
        await interaction.followup.send(embed=embed)


async def setup(bot):
    await bot.add_cog(Inventario(bot))