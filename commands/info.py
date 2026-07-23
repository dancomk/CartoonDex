import discord
from discord import app_commands
from discord.ext import commands
import asyncpg
import string
from typing import Optional
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

    def obter_arquivo_carta(self, carta_id: str):
        """Busca o buffer de bytes da imagem gerada e retorna como um discord.File."""
        if hasattr(self.bot, "obter_bytes_carta"):
            buffer, _ = self.bot.obter_bytes_carta(str(carta_id))
            if buffer:
                return discord.File(fp=buffer, filename="carta.png")
        return None

    @app_commands.command(
        name="info",
        description="Veja as informações detalhadas da Dex ou de uma carta do seu inventário."
    )
    @app_commands.describe(
        dex="Pesquise uma carta/personagem pelo nome ou número da Dex.",
        carta="Informações de uma carta única pelo n° do inventário ou ID global."
    )
    async def info(
        self, 
        interaction: discord.Interaction, 
        dex: Optional[str] = None, 
        carta: Optional[str] = None
    ):
        await interaction.response.defer()
        
        # Garante que o usuário enviou pelo menos um parâmetro
        if not dex and not carta:
            return await interaction.followup.send(
                "⚠️ Por favor, escolha e preencha uma das opções: `/info dex:` ou `/info carta:`.",
                ephemeral=True
            )

        user_id = interaction.user.id
        str_user_id = str(user_id)

        async with self.pool.acquire() as conn:
            # =================================================================
            # OPÇÃO 1: BUSCA POR CARTA ÚNICA (/info carta:) -> ID Pessoal ou Global
            # =================================================================
            if carta:
                termo_limpo = carta.strip().lstrip('#')

                # --- 1A: ID GLOBAL (6 caracteres alfanuméricos) ---
                if len(termo_limpo) == 6 and not termo_limpo.isdigit():
                    serial_id = codigo_aleatorio_para_numero(termo_limpo)
                    if serial_id:
                        instancia = await conn.fetchrow("""
                            WITH inventario_enumerado AS (
                                SELECT i.id, i.numero_dex, i.skin_id, i.carta_id, i.moldura_id, i.nivel, i.membro_id, i.data_global,
                                       ROW_NUMBER() OVER(ORDER BY i.data_pessoal ASC, i.id ASC) as id_pessoal_calculado
                                FROM inventario_cartas i
                                WHERE i.membro_id = (SELECT membro_id FROM inventario_cartas WHERE id = $1)
                            )
                            SELECT ie.*, d.nome, d.skin_nome, d.raridade, d.origem, d.hp, d.habilidade1, d.habilidade2
                            FROM inventario_enumerado ie
                            JOIN dex d ON d.carta_id = ie.carta_id
                            WHERE ie.id = $1;
                        """, serial_id)
                        
                        if instancia:
                            embed = embed_info_instancia(
                                instancia=instancia, 
                                id_pessoal=instancia["id_pessoal_calculado"], 
                                id_global=termo_limpo.upper()
                            )
                            
                            file_carta = self.obter_arquivo_carta(instancia["carta_id"])
                            if file_carta:
                                embed.set_image(url="attachment://carta.png")
                                return await interaction.followup.send(embed=embed, file=file_carta)
                            
                            return await interaction.followup.send(embed=embed)

                    return await interaction.followup.send(
                        f"❌ Carta com o ID Global **#{termo_limpo.upper()}** não foi encontrada.",
                        ephemeral=True
                    )

                # --- 1B: ID PESSOAL (Apenas números) ---
                elif termo_limpo.isdigit():
                    id_pessoal_alvo = int(termo_limpo)
                    
                    cartas_usuario = await conn.fetch("""
                        SELECT i.id, i.numero_dex, i.skin_id, i.carta_id, i.moldura_id, i.nivel, i.membro_id, i.data_global,
                               d.nome, d.skin_nome, d.raridade, d.origem, d.hp, d.habilidade1, d.habilidade2
                        FROM inventario_cartas i
                        JOIN dex d ON d.carta_id = i.carta_id
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
                        
                        file_carta = self.obter_arquivo_carta(instancia["carta_id"])
                        if file_carta:
                            embed.set_image(url="attachment://carta.png")
                            return await interaction.followup.send(embed=embed, file=file_carta)

                        return await interaction.followup.send(embed=embed)
                    
                    return await interaction.followup.send(
                        f"❌ Você não possui uma carta no nº **{id_pessoal_alvo}** do seu inventário.",
                        ephemeral=True
                    )
                else:
                    return await interaction.followup.send(
                        "❌ Formato inválido para `/info carta:`. Digite apenas o número do inventário ou o ID Global de 6 caracteres (ex: `#A1W8F7`).",
                        ephemeral=True
                    )

            # =================================================================
            # OPÇÃO 2: BUSCA GENERALIZADA DA DEX (/info dex:)
            # =================================================================
            elif dex:
                termo = dex.strip()
                
                # Checa se é número / formato de código da Dex (ex: "1", "0001", "1-1", "0001-1")
                if any(char.isdigit() for char in termo) and not any(char.isalpha() for char in termo):
                    if "-" in termo:
                        partes = termo.split("-", 1)
                        num_dex = partes[0].zfill(4)
                        num_skin = partes[1]
                        carta_id_alvo = f"{num_dex}-{num_skin}"
                    else:
                        num_dex = termo.zfill(4)
                        carta_id_alvo = f"{num_dex}-0"

                    rows_dex = await conn.fetch("""
                        SELECT * FROM dex WHERE carta_id = $1;
                    """, carta_id_alvo)

                    # Se pesquisou uma skin específica que não existe, tenta carregar ao menos a base (skin 0)
                    if not rows_dex and "-" in termo:
                        rows_dex = await conn.fetch("""
                            SELECT * FROM dex WHERE numero_dex = $1 ORDER BY skin_id ASC;
                        """, num_dex)
                else:
                    # Busca por Nome do Personagem, Nome da Skin ou Aliases
                    rows_dex = await conn.fetch("""
                        SELECT * FROM dex 
                        WHERE LOWER(nome) = LOWER($1) 
                           OR LOWER(skin_nome) = LOWER($1) 
                           OR LOWER($1) = ANY(SELECT LOWER(unnest(aliases)))
                        ORDER BY skin_id ASC;
                    """, termo)

                if not rows_dex:
                    return await interaction.followup.send(
                        f"❌ Nenhuma entrada correspondente a **{dex}** foi encontrada na Dex.",
                        ephemeral=True
                    )

                carta_base = rows_dex[0]
                lista_numero_dex = carta_base["numero_dex"]

                # Puxa todas as skins que esse personagem tem
                todas_skins = await conn.fetch("""
                    SELECT skin_id, skin_nome FROM dex WHERE numero_dex = $1 ORDER BY skin_id ASC;
                """, lista_numero_dex)

                skins_existentes = {
                    row["skin_id"]: (row["skin_nome"] if row["skin_nome"] is not None else "Padrão") 
                    for row in todas_skins
                }

                # Conta quantas cartas de cada skin o usuário tem
                rows_inv = await conn.fetch("""
                    SELECT skin_id, COUNT(*) as qtd
                    FROM inventario_cartas
                    WHERE membro_id = $1 AND numero_dex = $2
                    GROUP BY skin_id;
                """, str_user_id, lista_numero_dex)
                
                skins_do_usuario = {row["skin_id"]: row["qtd"] for row in rows_inv}

                # Tenta chamar embed_info_carta com suporte flexível a parâmetros
                dados_embed = {
                    "carta_nome": carta_base["nome"],
                    "numero_dex": carta_base["numero_dex"],
                    "numero": carta_base["numero_dex"],
                    "raridade": carta_base["raridade"],
                    "origem": carta_base["origem"],
                    "colecao": carta_base.get("colecao"),
                    "hp": carta_base["hp"],
                    "skins_do_personagem": skins_existentes,
                    "skins_usuario": skins_do_usuario,
                    "carta_base": carta_base,
                    "url_carta_func": getattr(self.bot, "url_carta", None)
                }

                try:
                    embed = embed_info_carta(**dados_embed)
                except TypeError:
                    # Caso a função embed_info_carta só aceite o dict da carta_base diretamente
                    embed = embed_info_carta(carta_base)

                file_carta = self.obter_arquivo_carta(carta_base["carta_id"])
                if file_carta:
                    embed.set_image(url="attachment://carta.png")
                    await interaction.followup.send(embed=embed, file=file_carta)
                else:
                    await interaction.followup.send(embed=embed)


async def setup(bot):
    await bot.add_cog(InfoCarta(bot))