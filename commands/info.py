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
    @app_commands.describe(busca="O número da Dex (ex: 3) ou o nome do personagem (ex: Ametista)")
    async def info(self, interaction: discord.Interaction, busca: str):
        await interaction.response.defer()
        user_id = interaction.user.id
        termo = busca.strip()

        try:
            async with self.pool.acquire() as conn:
                termo_limpo = termo.lstrip('#')

                # Busca por número (Removido o 'id' do SELECT)
                if termo_limpo.isdigit():
                    numero_buscado = int(termo_limpo)
                    rows_dex = await conn.fetch("""
                        SELECT dex, nome, skin_id, skin, raridade, descricao
                        FROM dex
                        WHERE CAST(dex AS INTEGER) = $1
                        ORDER BY skin_id ASC;
                    """, numero_buscado)
                    
                # Busca por nome ou aliases (Removido o 'id' do SELECT)
                else:
                    nome_para_busca = termo.lower()
                    rows_dex = await conn.fetch("""
                        SELECT dex, nome, skin_id, skin, raridade, descricao
                        FROM dex
                        WHERE LOWER(nome) = $1 OR $1 = ANY(aliases)
                        ORDER BY skin_id ASC;
                    """, nome_para_busca)

                if not rows_dex:
                    await interaction.followup.send(
                        f"❌ Nenhuma carta correspondente a **{busca}** foi encontrada na Dex.",
                        ephemeral=True
                    )
                    return

                dex_id_encontrado = rows_dex[0]["dex"]
                
                # ALTERAÇÃO: Agora busca o inventário direto por dex e skin_id, sem precisar de JOIN
                rows_inv = await conn.fetch("""
                    SELECT skin_id, quantidade
                    FROM inventario
                    WHERE dex = $1 AND user_id = $2;
                """, dex_id_encontrado, user_id)

            carta_base = rows_dex[0]
            
            skins_existentes = {
                row["skin_id"]: (row["skin"] if row["skin"] is not None else "Padrão") 
                for row in rows_dex
            }
            skins_do_usuario = {row["skin_id"]: row["quantidade"] for row in rows_inv}

            # Envia todos os parâmetros solicitados para o gerador de layouts
            embed = embed_info_carta(
                carta_nome=carta_base["nome"],
                dex_formatado=self.bot.limpar_dex(carta_base["dex"]),
                raridade=carta_base["raridade"],
                descricao=carta_base["descricao"], 
                skins_do_personagem=skins_existentes,
                skins_usuario=skins_do_usuario,
                carta_base=carta_base,
                url_carta_func=self.bot.url_carta
            )

            await interaction.followup.send(embed=embed)

        except Exception as e:
            print(f"Erro crítico no comando info: {e}")
            await interaction.followup.send("⚠️ Ocorreu um erro interno ao processar a busca.", ephemeral=True)

async def setup(bot):
    await bot.add_cog(InfoCarta(bot))