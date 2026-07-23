import discord
from discord import app_commands
from discord.ext import commands
import asyncpg
import string
from typing import Optional

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


class FavoritarCarta(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.pool: asyncpg.Pool = bot.pool

    @app_commands.command(
        name="favoritar",
        description="Defina sua carta favorita para ser exibida no seu perfil."
    )
    @app_commands.describe(
        carta="Favorita uma carta do inventário pelo n° do inventário ou ID global.",
        nenhuma="Selecione esta opção para desfavoritar sua carta favorita atual."
    )
    async def favoritar(
        self, 
        interaction: discord.Interaction, 
        carta: Optional[str] = None, 
        nenhuma: Optional[str] = None
    ):
        await interaction.response.defer()
        
        user_id = interaction.user.id
        str_user_id = str(user_id)

        async with self.pool.acquire() as conn:
            # =================================================================
            # OPÇÃO 1: REMOVER FAVORITA (/favoritar nenhuma:)
            # =================================================================
            if nenhuma is not None or (carta and carta.strip().lower() == "nenhuma"):
                await conn.execute("""
                    INSERT INTO perfis (membro_id, carta_favorita)
                    VALUES ($1, NULL)
                    ON CONFLICT (membro_id) 
                    DO UPDATE SET carta_favorita = NULL;
                """, str_user_id)

                return await interaction.followup.send(
                    "🧹 Sua carta favorita foi removida com sucesso! Agora seu perfil não possui nenhuma carta destacada."
                )

            # Valida se o usuário forneceu o valor no parâmetro 'carta'
            if not carta:
                return await interaction.followup.send(
                    "⚠️ Por favor, informe a carta no parâmetro `/favoritar carta:` ou selecione `/favoritar nenhuma:` para desfavoritar.",
                    ephemeral=True
                )

            termo_limpo = carta.strip().lstrip('#')
            instancia_alvo = None
            id_pessoal_exibicao = None
            id_global_exibicao = None

            # =================================================================
            # BUSCA 1: ID GLOBAL (6 caracteres alfanuméricos)
            # =================================================================
            if len(termo_limpo) == 6 and not termo_limpo.isdigit():
                serial_id = codigo_aleatorio_para_numero(termo_limpo)
                if serial_id:
                    # Restringe obrigatoriamente a busca ao inventário de quem enviou o comando
                    instancia_alvo = await conn.fetchrow("""
                        WITH inventario_enumerado AS (
                            SELECT i.id, i.numero_dex, i.skin_id, i.carta_id, i.membro_id,
                                   ROW_NUMBER() OVER(ORDER BY i.data_pessoal ASC, i.id ASC) as id_pessoal_calculado
                            FROM inventario_cartas i
                            WHERE i.membro_id = $1
                        )
                        SELECT ie.*, d.nome, d.skin_nome
                        FROM inventario_enumerado ie
                        JOIN dex d ON d.carta_id = ie.carta_id
                        WHERE ie.id = $2;
                    """, str_user_id, serial_id)

                    if instancia_alvo:
                        id_pessoal_exibicao = instancia_alvo["id_pessoal_calculado"]
                        id_global_exibicao = termo_limpo.upper()

                if not instancia_alvo:
                    return await interaction.followup.send(
                        f"❌ A carta com ID Global **#{termo_limpo.upper()}** não foi encontrada no **seu inventário**.",
                        ephemeral=True
                    )

            # =================================================================
            # BUSCA 2: ID PESSOAL (Apenas números)
            # =================================================================
            elif termo_limpo.isdigit():
                id_pessoal_alvo = int(termo_limpo)

                cartas_usuario = await conn.fetch("""
                    SELECT i.id, i.numero_dex, i.skin_id, i.carta_id, i.membro_id,
                           d.nome, d.skin_nome
                    FROM inventario_cartas i
                    JOIN dex d ON d.carta_id = i.carta_id
                    WHERE i.membro_id = $1
                    ORDER BY i.data_pessoal ASC, i.id ASC;
                """, str_user_id)

                if 0 < id_pessoal_alvo <= len(cartas_usuario):
                    instancia_alvo = cartas_usuario[id_pessoal_alvo - 1]
                    id_pessoal_exibicao = id_pessoal_alvo
                    id_global_exibicao = numero_para_codigo_aleatorio_local(instancia_alvo["id"])
                else:
                    return await interaction.followup.send(
                        f"❌ Você não possui nenhuma carta na posição **#{id_pessoal_alvo}** do seu inventário.",
                        ephemeral=True
                    )

            else:
                return await interaction.followup.send(
                    "❌ Formato inválido! Digite o número do inventário (ex: `12`) ou o ID Global de 6 caracteres (ex: `#A1W8F7`).",
                    ephemeral=True
                )

            # =================================================================
            # SALVANDO NO PERFIL DO USUÁRIO (Tabela: perfis, Coluna: carta_favorita)
            # =================================================================
            await conn.execute("""
                INSERT INTO perfis (membro_id, carta_favorita)
                VALUES ($1, $2)
                ON CONFLICT (membro_id) 
                DO UPDATE SET carta_favorita = EXCLUDED.carta_favorita;
            """, str_user_id, instancia_alvo["id"])

            nome_carta = instancia_alvo["nome"]
            skin_str = f" ({instancia_alvo['skin_nome']})" if instancia_alvo.get("skin_nome") else ""

            embed = discord.Embed(
                title="⭐ Carta Favoritada!",
                description=(
                    f"A carta **{nome_carta}**{skin_str} foi definida como a sua favorita!\n\n"
                    f"📌 **ID Pessoal:** `#{id_pessoal_exibicao}`\n"
                    f"🌐 **ID Global:** `#{id_global_exibicao}`\n\n"
                    f"Ela será exibida no topo do seu comando `/perfil`."
                ),
                color=discord.Color.gold()
            )

            await interaction.followup.send(embed=embed)


async def setup(bot):
    await bot.add_cog(FavoritarCarta(bot))