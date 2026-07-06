import discord
from discord import app_commands
from discord.ext import commands
import asyncpg
from .embed import embed_info_carta

class InfoCarta(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.pool: asyncpg.Pool = bot.pool

    @app_commands.command(
        name="info",
        description="Veja as informações detalhadas de uma carta pelo número ou nome."
    )
    @app_commands.describe(busca="O número da Dex (ex: 0001) ou o nome do personagem (ex: aespa)")
    async def info(self, interaction: discord.Interaction, busca: str):
        await interaction.response.defer()
        user_id = interaction.user.id
        str_user_id = str(user_id)  # inventario_cartas usa VARCHAR(50) para membro_id
        termo = busca.strip()

        try:
            async with self.pool.acquire() as conn:
                termo_limpo = termo.lstrip('#')

                # 1. Busca na tabela dex mapeando as colunas reais corrigidas (skin_nome)
                if termo_limpo.isdigit():
                    numero_buscado = termo_limpo.zfill(4) if len(termo_limpo) < 4 else termo_limpo
                    
                    rows_dex = await conn.fetch("""
                        SELECT carta_id, numero_dex, skin_id, nome, skin_nome, aliases, 
                               origem, colecao, raridade, hp, ataque_1_nome, ataque_1_dano, 
                               ataque_1_descricao, ataque_2_nome, ataque_2_dano, ataque_2_descricao
                        FROM dex
                        WHERE numero_dex = $1
                        ORDER BY skin_id ASC;
                    """, numero_buscado)
                else:
                    nome_para_busca = self.bot.normalizar(termo)
                    
                    rows_dex = await conn.fetch("""
                        SELECT carta_id, numero_dex, skin_id, nome, skin_nome, aliases, 
                               origem, colecao, raridade, hp, ataque_1_nome, ataque_1_dano, 
                               ataque_1_descricao, ataque_2_nome, ataque_2_dano, ataque_2_descricao
                        FROM dex
                        WHERE LOWER(nome) = LOWER($1) OR $1 = ANY(
                            SELECT LOWER(unnest(aliases))
                        )
                        ORDER BY skin_id ASC;
                    """, nome_para_busca)

                if not rows_dex:
                    await interaction.followup.send(
                        f"❌ Nenhuma carta correspondente a **{busca}** foi encontrada na Dex.",
                        ephemeral=True
                    )
                    return

                # Coleta todos os carta_id encontrados para buscar as cópias do usuário
                lista_cartas_ids = [row["carta_id"] for row in rows_dex]

                # 2. Busca no inventario_cartas correspondente
                rows_inv = await conn.fetch("""
                    SELECT carta_id, quantidade
                    FROM inventario_cartas
                    WHERE membro_id = $1 AND carta_id = ANY($2);
                """, str_user_id, lista_cartas_ids)

            # 3. Processamento de dados para o Embed externo
            carta_base = rows_dex[0]
            
            skins_existentes = {
                row["skin_id"]: (row["skin_nome"] if row["skin_nome"] is not None else "Padrão") 
                for row in rows_dex
            }
            
            skins_do_usuario = {row["carta_id"]: row["quantidade"] for row in rows_inv}

            # Envia todos os parâmetros solicitados estruturados para o gerador visual de layouts
            embed = embed_info_carta(
                carta_nome=carta_base["nome"],
                numero_dex=carta_base["numero_dex"],
                raridade=carta_base["raridade"],
                origem=carta_base["origem"],
                colecao=carta_base["colecao"],
                hp=carta_base["hp"],
                skins_do_personagem=skins_existentes,
                skins_usuario=skins_do_usuario,
                carta_base=carta_base,
                url_carta_func=getattr(self.bot, "url_carta", None)
            )

            await interaction.followup.send(embed=embed)

        except Exception as e:
            print(f"Erro crítico no comando info: {e}")
            await interaction.followup.send("⚠️ Ocorreu um erro interno ao processar a busca.", ephemeral=True)

async def setup(bot):
    await bot.add_cog(InfoCarta(bot))