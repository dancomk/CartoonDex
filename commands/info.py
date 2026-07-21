import discord
from discord import app_commands
from discord.ext import commands
import asyncpg
import string
from .embed import embed_info_carta, embed_info_instancia

# --- SISTEMA DE TRADUÇÃO DO ID GLOBAL HASH ---
ALFABETO = string.digits + string.ascii_uppercase
PRIMO_INVERSO = 1438994323  # Inverso modular de 41359727 sob o módulo 36^6
MODULO = 36**6

def codigo_aleatorio_para_numero(codigo: str) -> int:
    """Decodifica o hash de 6 dígitos de volta para o ID SERIAL numérico do banco."""
    if len(codigo) != 6:
        return None
    try:
        embaralhado = 0
        for char in codigo.upper():
            embaralhado = embaralhado * 36 + ALFABETO.index(char)
        num = (embaralhado * PRIMO_INVERSO) % MODULO
        return num
    except ValueError:
        return None

def numero_para_codigo_aleatorio_local(num: int) -> str:
    """Embaralha o ID SERIAL único do banco em um hash de 6 dígitos."""
    PRIMO = 41359727
    if not num: return "000000"
    embaralhado = (num * PRIMO) % (36**6)
    codigo = ""
    for _ in range(6):
        embaralhado, resto = divmod(embaralhado, 36)
        codigo = ALFABETO[resto] + codigo
    return codigo


class InfoCarta(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.pool: asyncpg.Pool = bot.pool

    @app_commands.command(
        name="info",
        description="Veja as informações detalhadas de uma carta ou entrada geral da Dex."
    )
    @app_commands.describe(busca="O número da Dex, nome, apelido, ID global (#A1W8F7) ou ID pessoal (ex: 12)")
    async def info(self, interaction: discord.Interaction, busca: str):
        await interaction.response.defer()
        user_id = interaction.user.id
        str_user_id = str(user_id)
        termo = busca.strip()
        termo_limpo = termo.lstrip('#')

        async with self.pool.acquire() as conn:
            # ==========================================
            # CANAL 1: BUSCA POR ID GLOBAL (HASH DE 6 DÍGITOS)
            # ==========================================
            if len(termo_limpo) == 6 and not termo_limpo.isdigit():
                serial_id = codigo_aleatorio_para_numero(termo_limpo)
                if serial_id:
                    # Usamos uma CTE para enumerar todas as cartas do dono e descobrir o ID Pessoal exato daquela instância
                    instancia = await conn.fetchrow("""
                        WITH inventario_enumerado AS (
                            SELECT i.id, i.numero_dex, i.skin_id, i.moldura_id, i.nivel, i.membro_id, i.data_global,
                                   ROW_NUMBER() OVER(ORDER BY i.data_pessoal ASC, i.id ASC) as id_pessoal_calculado
                            FROM inventario_cartas i
                            WHERE i.membro_id = (SELECT membro_id FROM inventario_cartas WHERE id = $1)
                        )
                        SELECT ie.*, d.nome, d.skin_nome, d.raridade, d.origem, d.hp, d.ataque_1_nome, d.ataque_2_nome
                        FROM inventario_enumerado ie
                        JOIN dex d ON d.numero_dex = ie.numero_dex AND d.skin_id = ie.skin_id
                        WHERE ie.id = $1;
                    """, serial_id)
                    
                    if instancia:
                        embed = embed_info_instancia(
                            instancia=instancia, 
                            id_pessoal=instancia["id_pessoal_calculado"], 
                            id_global=termo_limpo.upper()
                        )
                        return await interaction.followup.send(embed=embed)

            # ==========================================
            # CANAL 2: BUSCA POR ID PESSOAL (INTEIRO INFORMADO)
            # ==========================================
            if termo_limpo.isdigit() and len(termo_limpo) <= 5:
                id_pessoal_alvo = int(termo_limpo)
                
                # Puxa todas as cartas do usuário por ordem de obtenção tradicional
                cartas_usuario = await conn.fetch("""
                    SELECT i.id, i.numero_dex, i.skin_id, i.moldura_id, i.nivel, i.membro_id, i.data_global,
                           d.nome, d.skin_nome, d.raridade, d.origem, d.hp, d.ataque_1_nome, d.ataque_2_nome
                    FROM inventario_cartas i
                    JOIN dex d ON d.numero_dex = i.numero_dex AND d.skin_id = i.skin_id
                    WHERE i.membro_id = $1
                    ORDER BY i.data_pessoal ASC, i.id ASC;
                """, str_user_id)
                
                if 0 < id_pessoal_alvo <= len(cartas_usuario):
                    instancia = cartas_usuario[id_pessoal_alvo - 1]
                    hash_global = numero_para_codigo_aleatorio_local(instancia["id"])
                    
                    embed = embed_info_instancia(
                        instancia=instancia, 
                        id_pessoal=id_pessoal_alvo, 
                        id_global=hash_global
                    )
                    return await interaction.followup.send(embed=embed)

            # ==========================================
            # CANAL 3: BUSCA GENERALIZADA DA DEX (ENTRADA GLOBAL)
            # ==========================================
            if termo_limpo.isdigit():
                numero_buscado = termo_limpo.zfill(4) if len(termo_limpo) < 4 else termo_limpo
                rows_dex = await conn.fetch("""
                    SELECT * FROM dex WHERE numero_dex = $1 ORDER BY skin_id ASC;
                """, numero_buscado)
            else:
                rows_dex = await conn.fetch("""
                    SELECT * FROM dex 
                    WHERE LOWER(nome) = LOWER($1) 
                       OR LOWER(skin_nome) = LOWER($1) 
                       OR LOWER($1) = ANY(SELECT LOWER(unnest(aliases)))
                    ORDER BY skin_id ASC;
                """, termo)

            if not rows_dex:
                return await interaction.followup.send(
                    f"❌ Nenhuma carta correspondente a **{busca}** foi encontrada na Dex ou no inventário.",
                    ephemeral=True
                )

            carta_base = rows_dex[0]
            skins_existentes = {
                row["skin_id"]: (row["skin_nome"] if row["skin_nome"] is not None else "Padrão") 
                for row in rows_dex
            }
            
            lista_numero_dex = carta_base["numero_dex"]
            rows_inv = await conn.fetch("""
                SELECT skin_id, COUNT(*) as qtd
                FROM inventario_cartas
                WHERE membro_id = $1 AND numero_dex = $2
                GROUP BY skin_id;
            """, str_user_id, lista_numero_dex)
            
            skins_do_usuario = {row["skin_id"]: row["qtd"] for row in rows_inv}

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


async def setup(bot):
    await bot.add_cog(InfoCarta(bot))