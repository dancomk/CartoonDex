import discord
from discord import app_commands
from discord.ext import commands
import asyncpg
import aiohttp

class Equipar(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.pool: asyncpg.Pool = bot.pool

    async def verificar_imagem_online(self, url: str) -> bool:
        """Faz uma checagem rápida no cabeçalho da imagem para ver se ela existe (Status 200)."""
        if not url or not url.startswith("http"):
            return False
        try:
            async with aiohttp.ClientSession() as session:
                async with session.head(url, timeout=2.0) as response:
                    return response.status == 200
        except Exception:
            return False

    @app_commands.command(
        name="equipar",
        description="Equipa uma moldura cosmética em uma das suas cartas e consome 1x do estoque!"
    )
    @app_commands.describe(
        carta_id="O ID da carta que vai receber a moldura.",
        moldura_id="O nome/ID da moldura que você quer usar."
    )
    async def equipar(self, interaction: discord.Interaction, carta_id: str, moldura_id: str):
        # 1. Deixamos o defer como PÚBLICO (False) para que o resultado final apareça para todos
        await interaction.response.defer(ephemeral=False)
        
        user_id = interaction.user.id
        str_user_id = str(user_id)

        # 2. VERIFICAÇÃO DE SEGURANÇA: A imagem da moldura existe no repositório?
        url_moldura = f"https://raw.githubusercontent.com/seu-usuario/seu-repo/main/molduras/{moldura_id}.png"
        
        imagem_valida = await self.verificar_imagem_online(url_moldura)
        if not imagem_valida:
            return await interaction.followup.send(
                f"⚠️ **Erro Técnico:** A imagem para a moldura `{moldura_id}` não foi encontrada no servidor "
                f"ou está com o link quebrado (Erro 404). Por segurança, a ação foi cancelada.",
                ephemeral=True
            )

        # 3. Transação no Banco de Dados: Verifica posses, consome e atualiza
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                # Verifica se o jogador tem a moldura no inventário de cosméticos
                tem_moldura = await conn.fetchval("""
                    SELECT quantidade FROM inventario_molduras WHERE membro_id = $1 AND moldura_id = $2
                """, user_id, moldura_id)

                if not tem_moldura or tem_moldura <= 0:
                    return await interaction.followup.send(
                        f"❌ Você não possui a moldura `{moldura_id}` no seu inventário.", ephemeral=True
                    )

                # Verifica se o jogador possui a carta base no inventário sem moldura
                carta_usuario = await conn.fetchrow("""
                    SELECT carta_id, quantidade, skin_id 
                    FROM inventario_cartas 
                    WHERE membro_id = $1 AND carta_id = $2 AND moldura_id IS NULL 
                    LIMIT 1
                """, str_user_id, carta_id)

                if not carta_usuario or carta_usuario["quantidade"] <= 0:
                    return await interaction.followup.send(
                        f"❌ Você não possui a carta `{carta_id}` sem moldura no seu inventário.", ephemeral=True
                    )

                # AÇÃO A: Aplica a moldura na carta específica
                await conn.execute("""
                    UPDATE inventario_cartas 
                    SET moldura_id = $1 
                    WHERE membro_id = $2 AND carta_id = $3 AND moldura_id IS NULL
                """, moldura_id, str_user_id, carta_id)

                # AÇÃO B: Desconta 1 do estoque de molduras consumíveis do usuário
                await conn.execute("""
                    UPDATE inventario_molduras 
                    SET quantidade = quantidade - 1 
                    WHERE membro_id = $1 AND moldura_id = $2
                """, user_id, moldura_id)

        # 4. Busca as informações da carta que estão armazenadas na memória do bot para gerar a URL da foto
        dados_carta_global = self.bot.dex.get(carta_id)
        
        # 5. Montagem do Retorno de Sucesso (PÚBLICO)
        embed = discord.Embed(
            title="🖼️ Moldura Equipada!",
            description=f"{interaction.user.mention} aplicou com sucesso a moldura **{moldura_id}** na sua carta **{dados_carta_global['nome'] if dados_carta_global else carta_id}**!",
            color=discord.Color.from_rgb(255, 255, 255)
        )

        # 6. Injeção da Arte
        if dados_carta_global:
            dados_para_url = {
                "carta_id": carta_id,
                "skin_id": carta_usuario["skin_id"],
                "moldura_id": moldura_id
            }
            if hasattr(self.bot, "gerar_url_carta"):
                url_final_imagem = self.bot.gerar_url_carta(dados_para_url)
                embed.set_image(url=url_final_imagem)

        await interaction.followup.send(embed=embed)


async def setup(bot):
    await bot.add_cog(Equipar(bot))