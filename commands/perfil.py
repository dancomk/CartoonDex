import os
import io
import aiohttp
import discord
from discord import app_commands
from discord.ext import commands
from PIL import Image, ImageDraw, ImageFont, ImageOps

class Perfil(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # Função auxiliar para desenhar texto com o tracking (-50) do Photoshop traduzido para pixels
    def draw_text_with_tracking(self, draw, position, text, font, fill, tracking):
        x, y = position
        for char in text:
            draw.text((x, y), char, font=font, fill=fill)
            char_width = draw.textlength(char, font=font)
            x += char_width + tracking
        return x

    @app_commands.command(name="perfil", description="Exibe seu perfil personalizado do CartoonDex!")
    async def perfil(self, interaction: discord.Interaction):
        await interaction.response.defer()

        user_id = interaction.user.id
        avatar_url = interaction.user.display_avatar.with_format("png").url

        # 1. BUSCA DADOS NO BANCO (Neon DB)
        async with self.bot.pool.acquire() as conn:
            user_data = await conn.fetchrow("""
                INSERT INTO usuarios (user_id, apelido, biscoitos, carta_favorita, cor_estrutura, fundo_equipado)
                VALUES ($1, $2, 0, NULL, '#2b2b5f', 'praia-dia')
                ON CONFLICT (user_id) DO UPDATE SET user_id = usuarios.user_id
                RETURNING apelido, biscoitos, carta_favorita, cor_estrutura, fundo_equipado
            """, user_id, interaction.user.display_name)
            
            # Conta quantas linhas o usuário tem no inventário (Total de cartas)
            total_cartas = await conn.fetchval("SELECT COUNT(*) FROM inventario WHERE user_id = $1", user_id) or 0
            
            # Conta quantas cartas diferentes (DISTINCT dex) o usuário possui
            cartas_unicas = await conn.fetchval("SELECT COUNT(DISTINCT dex) FROM inventario WHERE user_id = $1", user_id) or 0
            total_global_dex = 25 

        nome_exibido = user_data["apelido"]
        biscoitos = user_data["biscoitos"]
        carta_fav = user_data["carta_favorita"]
        hex_cor = user_data["cor_estrutura"] or '#2b2b5f'
        fundo = user_data["fundo_equipado"] or "praia-dia"

        # Converte a cor Hex do banco para uma tupla RGB que o Pillow aceita
        cor_rgb = tuple(int(hex_cor.lstrip('#')[i:i+2], 16) for i in (0, 2, 4))

        github_base = os.getenv("GITHUB_BASE")

        # 2. MAPEAMENTO DOS RECURSOS REMOTOS DO REPOSITÓRIO
        url_cenario = f"{github_base}/assets/perfil/fundo/{fundo}.png"
        url_estrutura = f"{github_base}/assets/perfil/estrutura/estrutura.png"
        url_biscoito_icon = f"{github_base}/assets/icones/biscoito.png"
        
        # Mapeamento das fontes direto do GitHub
        url_font_crewniverse = f"{github_base}/assets/fontes/CREWNIVERSE_FONT.TTF"
        url_font_montserrat = f"{github_base}/assets/fontes/MONTSERRAT-SEMIBOLD.OTF"
        
        # Define qual imagem vai para a moldura da direita
        if carta_fav:
            url_direita_recurso = f"{github_base}/assets/cartas/{carta_fav}/{carta_fav}-0-carta.png"
        else:
            url_direita_recurso = f"{github_base}/assets/perfil/nenhuma-carta-selecionada/padrao.png"

        # 3. DOWNLOAD DOS RECURSOS VIA AIOHTTP (Imagens e Fontes)
        async with aiohttp.ClientSession() as session:
            async with session.get(url_cenario) as r: cenario_bytes = await r.read()
            async with session.get(url_estrutura) as r: estrutura_bytes = await r.read()
            async with session.get(url_biscoito_icon) as r: biscoito_bytes = await r.read()
            async with session.get(url_direita_recurso) as r: direita_bytes = await r.read()
            async with session.get(avatar_url) as r: avatar_bytes = await r.read()
            # Baixando os arquivos de fontes do repositório
            async with session.get(url_font_crewniverse) as r: font_crewniverse_bytes = await r.read()
            async with session.get(url_font_montserrat) as r: font_montserrat_bytes = await r.read()

        # 4. TRATAMENTO E MONTAGEM DE CAMADAS (PILLOW)
        img_perfil = Image.open(io.BytesIO(cenario_bytes)).convert("RGBA").resize((900, 500))
        img_biscoito = Image.open(io.BytesIO(biscoito_bytes)).convert("RGBA").resize((52, 28))
        
        img_estrutura_branca = Image.open(io.BytesIO(estrutura_bytes)).convert("L")
        img_estrutura_colorida = ImageOps.colorize(img_estrutura_branca, black="black", white=cor_rgb).convert("RGBA")
        
        img_avatar = Image.open(io.BytesIO(avatar_bytes)).convert("RGBA").resize((200, 200))
        mascara_avatar = Image.new("L", (200, 200), 0)
        draw_masc = ImageDraw.Draw(mascara_avatar)
        draw_masc.rounded_rectangle([0, 0, 200, 200], radius=20, fill=255)

        img_direita = Image.open(io.BytesIO(direita_bytes)).convert("RGBA").resize((260, 365))
        mascara_direita = Image.new("L", (260, 365), 0)
        draw_dir_masc = ImageDraw.Draw(mascara_direita)
        draw_dir_masc.rounded_rectangle([0, 0, 260, 365], radius=15, fill=255)

        img_perfil.paste(img_estrutura_colorida, (0, 0), img_estrutura_colorida)
        img_perfil.paste(img_avatar, (108, 133), mascara_avatar)
        img_perfil.paste(img_direita, (605, 110), mascara_direita)
        img_perfil.paste(img_biscoito, (108, 385), img_biscoito)

        # 5. CONFIGURAÇÃO DAS FONTES (Carregando os bytes baixados do GitHub)
        try:
            font_crewniverse_p = ImageFont.truetype(io.BytesIO(font_crewniverse_bytes), 16)
            font_crewniverse_m = ImageFont.truetype(io.BytesIO(font_crewniverse_bytes), 22)
            font_crewniverse_g = ImageFont.truetype(io.BytesIO(font_crewniverse_bytes), 42)
            font_montserrat = ImageFont.truetype(io.BytesIO(font_montserrat_bytes), 20)
        except IOError:
            font_crewniverse_p = font_crewniverse_m = font_crewniverse_g = font_montserrat = ImageFont.load_default()

        draw = ImageDraw.Draw(img_perfil)
        tracking_su = -2 

        # TEXTO 1: Header do Topo
        txt_header = "CARTOONDEX - O BOT ORIGINAL DO SERVIDOR  • STEVEN UNIVERSE BR •"
        self.draw_text_with_tracking(draw, (25, 20), txt_header, font_crewniverse_p, (255, 255, 255, 220), tracking_su)

        # TEXTO 2: Apelido do Usuário
        self.draw_text_with_tracking(draw, (108, 275), nome_exibido, font_crewniverse_g, (255, 255, 255), tracking_su)

        # TEXTO 3: TOTAL DE CARTAS
        x_cartas, y_cartas = 108, 335
        self.draw_text_with_tracking(draw, (x_cartas, y_cartas), "TOTAL DE CARTAS: ", font_montserrat, (255, 255, 255), tracking_su)
        largura_txt1 = sum([draw.textlength(c, font_montserrat) + tracking_su for c in "TOTAL DE CARTAS: "])
        self.draw_text_with_tracking(draw, (x_cartas + largura_txt1, y_cartas - 2), str(total_cartas), font_crewniverse_m, (255, 255, 255), tracking_su)

        # TEXTO 4: PROGRESSO DA DEX
        y_dex = 365
        self.draw_text_with_tracking(draw, (x_cartas, y_dex), "PROGRESSO DA DEX: ", font_montserrat, (255, 255, 255), tracking_su)
        largura_txt2 = sum([draw.textlength(c, font_montserrat) + tracking_su for c in "PROGRESSO DA DEX: "])
        self.draw_text_with_tracking(draw, (x_cartas + largura_txt2, y_dex - 2), f"{cartas_unicas}/{total_global_dex}", font_crewniverse_m, (255, 255, 255), tracking_su)

        # TEXTO 5: Saldo de Biscoitos
        x_biscoito, y_biscoito = 170, 387
        str_biscoitos = f"{biscoitos} "
        next_x = self.draw_text_with_tracking(draw, (x_biscoito, y_biscoito - 2), str_biscoitos, font_crewniverse_m, (255, 255, 255), tracking_su)
        self.draw_text_with_tracking(draw, (next_x, y_biscoito), "BISCOITOS GATINHO", font_montserrat, (255, 255, 255), tracking_su)

        # TEXTO 6: Faixa "CARTA DESTAQUE"
        self.draw_text_with_tracking(draw, (625, 432), "CARTA DESTAQUE", font_crewniverse_m, (255, 255, 255), tracking_su)

        # CONDICIONAL DO AVISO
        if not carta_fav:
            subtexto_aviso = "NENHUMA CARTA SELECIONADA"
            largura_aviso = sum([draw.textlength(c, font_crewniverse_p) + tracking_su for c in subtexto_aviso])
            x_centro_aba = 605 + (280 / 2)
            x_aviso = x_centro_aba - (largura_aviso / 2)
            self.draw_text_with_tracking(draw, (x_aviso, 465), subtexto_aviso, font_crewniverse_p, (230, 160, 255), tracking_su)

        # 6. ENVIO DO PRODUTO FINAL
        buffer = io.BytesIO()
        img_perfil.save(buffer, format="PNG")
        buffer.seek(0)

        file = discord.File(fp=buffer, filename="perfil.png")
        await interaction.followup.send(file=file)

async def setup(bot):
    await bot.add_cog(Perfil(bot))