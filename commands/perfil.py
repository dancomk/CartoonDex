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
                INSERT INTO usuarios (id, apelido, biscoitos, carta_favorita, cor_estrutura, fundo_equipado)
                VALUES ($1, $2, 0, NULL, '#9C27B0', 'praia-dia')
                ON CONFLICT (id) DO UPDATE SET id = usuarios.id
                RETURNING apelido, biscoitos, carta_favorita, cor_estrutura, fundo_equipado
            """, user_id, interaction.user.display_name)
            
            total_cartas = await conn.fetchval("SELECT COUNT(*) FROM inventario WHERE usuario_id = $1", user_id) or 0
            cartas_unicas = await conn.fetchval("SELECT COUNT(DISTINCT dex) FROM inventario WHERE usuario_id = $1", user_id) or 0
            total_global_dex = 25 

        nome_exibido = user_data["apelido"]
        biscoitos = user_data["biscoitos"]
        carta_fav = user_data["carta_favorita"]
        hex_cor = user_data["cor_estrutura"]
        fundo = user_data["fundo_equipado"] or "praia-dia" # Fallback dinâmico usando o padrão slug

        # Converte a cor Hex do banco para uma tupla RGB que o Pillow aceita
        cor_rgb = tuple(int(hex_cor.lstrip('#')[i:i+2], 16) for i in (0, 2, 4))

        github_base = os.getenv("GITHUB_BASE")

        # 2. MAPEAMENTO DAS NOVAS PASTAS DO REPOSITÓRIO
        url_cenario = f"{github_base}/assets/perfil/fundo/{fundo}.png"
        url_estrutura = f"{github_base}/assets/perfil/estrutura/estrutura.png"
        url_biscoito_icon = f"{github_base}/assets/icones/biscoito.png" # Caminho isolado global de ícones
        
        # Define qual imagem vai para a moldura da direita
        if carta_fav:
            url_direita_recurso = f"{github_base}/assets/cartas/{carta_fav}/{carta_fav}-0-carta.png"
        else:
            url_direita_recurso = f"{github_base}/assets/perfil/nenhuma-carta-selecionada/padrao.png"

        # 3. DOWNLOAD DOS RECURSOS VIA AIOHTTP
        async with aiohttp.ClientSession() as session:
            async with session.get(url_cenario) as r: cenario_bytes = await r.read()
            async with session.get(url_estrutura) as r: estrutura_bytes = await r.read()
            async with session.get(url_biscoito_icon) as r: biscoito_bytes = await r.read()
            async with session.get(url_direita_recurso) as r: direita_bytes = await r.read()
            async with session.get(avatar_url) as r: avatar_bytes = await r.read()

        # 4. TRATAMENTO E MONTAGEM DE CAMADAS (PILLOW)
        img_perfil = Image.open(io.BytesIO(cenario_bytes)).convert("RGBA").resize((900, 500))
        img_biscoito = Image.open(io.BytesIO(biscoito_bytes)).convert("RGBA").resize((52, 28))
        
        # MÁGICA DE COLORAÇÃO: Tinge o arquivo 'estrutura.png' (que deve ser branco) com o RGB do banco
        img_estrutura_branca = Image.open(io.BytesIO(estrutura_bytes)).convert("L") # Abre em tons de cinza/máscara
        img_estrutura_colorida = ImageOps.colorize(img_estrutura_branca, black="black", white=cor_rgb).convert("RGBA")
        
        # Cortando o Avatar em Quadrado Arredondado para encaixar no frame esquerdo
        img_avatar = Image.open(io.BytesIO(avatar_bytes)).convert("RGBA").resize((200, 200))
        mascara_avatar = Image.new("L", (200, 200), 0)
        draw_masc = ImageDraw.Draw(mascara_avatar)
        draw_masc.rounded_rectangle([0, 0, 200, 200], radius=20, fill=255)

        # Cortando a Carta / Imagem Branca da direita com bordas arredondadas
        img_direita = Image.open(io.BytesIO(direita_bytes)).convert("RGBA").resize((260, 365))
        mascara_direita = Image.new("L", (260, 365), 0)
        draw_dir_masc = ImageDraw.Draw(mascara_direita)
        draw_dir_masc.rounded_rectangle([0, 0, 260, 365], radius=15, fill=255)

        # Colando tudo na imagem de fundo na ordem correta de camadas
        img_perfil.paste(img_estrutura_colorida, (0, 0), img_estrutura_colorida)
        img_perfil.paste(img_avatar, (108, 133), mascara_avatar)
        img_perfil.paste(img_direita, (605, 110), mascara_direita)
        img_perfil.paste(img_biscoito, (108, 385), img_biscoito)

        # 5. CONFIGURAÇÃO DAS FONTES (Arquivos locais na pasta 'fonts/')
        try:
            font_crewniverse_p = ImageFont.truetype("fonts/crewniverse.ttf", 16)
            font_crewniverse_m = ImageFont.truetype("fonts/crewniverse.ttf", 22)
            font_crewniverse_g = ImageFont.truetype("fonts/crewniverse.ttf", 42)
            font_montserrat = ImageFont.truetype("fonts/Montserrat-SemiBold.ttf", 20)
        except IOError:
            font_crewniverse_p = font_crewniverse_m = font_crewniverse_g = font_montserrat = ImageFont.load_default()

        draw = ImageDraw.Draw(img_perfil)
        tracking_su = -2 # Ajuste fino para simular o -50 de tracking do Photoshop

        # TEXTO 1: Header do Topo (Crewniverse)
        txt_header = "CARTOONDEX - O BOT ORIGINAL DO SERVIDOR  • STEVEN UNIVERSE BR •"
        self.draw_text_with_tracking(draw, (25, 20), txt_header, font_crewniverse_p, (255, 255, 255, 220), tracking_su)

        # TEXTO 2: Apelido do Usuário (Crewniverse)
        self.draw_text_with_tracking(draw, (108, 275), nome_exibido, font_crewniverse_g, (255, 255, 255), tracking_su)

        # TEXTO 3: TOTAL DE CARTAS (Montserrat + Número em Crewniverse)
        x_cartas, y_cartas = 108, 335
        self.draw_text_with_tracking(draw, (x_cartas, y_cartas), "TOTAL DE CARTAS: ", font_montserrat, (255, 255, 255), tracking_su)
        largura_txt1 = sum([draw.textlength(c, font=font_montserrat) + tracking_su for c in "TOTAL DE CARTAS: "])
        self.draw_text_with_tracking(draw, (x_cartas + largura_txt1, y_cartas - 2), str(total_cartas), font=font_crewniverse_m, (255, 255, 255), tracking_su)

        # TEXTO 4: PROGRESSO DA DEX (Montserrat + Fração em Crewniverse)
        y_dex = 365
        self.draw_text_with_tracking(draw, (x_cartas, y_dex), "PROGRESSO DA DEX: ", font_montserrat, (255, 255, 255), tracking_su)
        largura_txt2 = sum([draw.textlength(c, font=font_montserrat) + tracking_su for c in "PROGRESSO DA DEX: "])
        self.draw_text_with_tracking(draw, (x_cartas + largura_txt2, y_dex - 2), f"{cartas_unicas}/{total_global_dex}", font=font_crewniverse_m, (255, 255, 255), tracking_su)

        # TEXTO 5: Saldo de Biscoitos (Número em Crewniverse + Texto em Montserrat)
        x_biscoito, y_biscoito = 170, 387
        str_biscoitos = f"{biscoitos} "
        next_x = self.draw_text_with_tracking(draw, (x_biscoito, y_biscoito - 2), str_biscoitos, font=font_crewniverse_m, (255, 255, 255), tracking_su)
        self.draw_text_with_tracking(draw, (next_x, y_biscoito), "BISCOITOS GATINHO", font=font_montserrat, (255, 255, 255), tracking_su)

        # TEXTO 6: Faixa "CARTA DESTAQUE" (Crewniverse)
        self.draw_text_with_tracking(draw, (625, 432), "CARTA DESTAQUE", font=font_crewniverse_m, (255, 255, 255), tracking_su)

        # CONDICIONAL DO AVISO: Se não houver carta favorita, centraliza o aviso rosa abaixo da moldura
        if not carta_fav:
            subtexto_aviso = "NENHUMA CARTA SELECIONADA"
            largura_aviso = sum([draw.textlength(c, font=font_crewniverse_p) + tracking_su for c in subtexto_aviso])
            x_centro_aba = 605 + (280 / 2)
            x_aviso = x_centro_aba - (largura_aviso / 2)
            
            # Pinta o aviso com uma cor suave que combine com a identidade do servidor
            self.draw_text_with_tracking(draw, (x_aviso, 465), subtexto_aviso, font=font_crewniverse_p, (230, 160, 255), tracking_su)

        # 6. ENVIO DO PRODUTO FINAL
        buffer = io.BytesIO()
        img_perfil.save(buffer, format="PNG")
        buffer.seek(0)

        file = discord.File(fp=buffer, filename="perfil.png")
        await interaction.followup.send(file=file)

async def setup(bot):
    await bot.add_cog(Perfil(bot))