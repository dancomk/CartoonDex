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
    def draw_text_with_tracking(self, draw, position, text, font, fill, tracking, stroke_width=0, stroke_fill=None):
        x, y = position
        for char in text:
            draw.text((x, y), char, font=font, fill=fill, stroke_width=stroke_width, stroke_fill=stroke_fill)
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
        try:
            img_perfil = Image.open(io.BytesIO(cenario_bytes)).convert("RGBA").resize((900, 500))
        except Exception:
            return await interaction.followup.send(f"❌ Erro ao carregar o cenário de fundo: `{url_cenario}`. Verifique se o arquivo existe no GitHub.")

        try:
            # Redimensionamento do ícone do biscoito para 45x29 pixels conforme solicitado
            img_biscoito = Image.open(io.BytesIO(biscoito_bytes)).convert("RGBA").resize((45, 29))
        except Exception:
            return await interaction.followup.send(f"❌ Erro ao carregar o ícone do biscoito: `{url_biscoito_icon}`.")

        try:
            img_estrutura_base = Image.open(io.BytesIO(estrutura_bytes)).convert("RGBA")
        except Exception:
            return await interaction.followup.send(f"❌ Erro ao carregar a estrutura do perfil: `{url_estrutura}`.")

        try:
            img_avatar = Image.open(io.BytesIO(avatar_bytes)).convert("RGBA").resize((200, 200))
        except Exception:
            return await interaction.followup.send("❌ Erro ao processar o seu avatar do Discord. Tente novamente.")

        try:
            img_direita = Image.open(io.BytesIO(direita_bytes)).convert("RGBA").resize((260, 365))
        except Exception:
            return await interaction.followup.send(f"❌ Erro ao carregar a imagem da direita (carta ou padrão): `{url_direita_recurso}`.")

        # Criação da estrutura colorida usando máscara alfa para colorir apenas o desenho
        img_cor_solida = Image.new("RGBA", img_estrutura_base.size, cor_rgb)
        img_estrutura_colorida = Image.composite(img_cor_solida, Image.new("RGBA", img_estrutura_base.size, (0, 0, 0, 0)), img_estrutura_base)
        
        mascara_avatar = Image.new("L", (200, 200), 0)
        draw_masc = ImageDraw.Draw(mascara_avatar)
        draw_masc.rounded_rectangle([0, 0, 200, 200], radius=15, fill=255)

        mascara_direita = Image.new("L", (260, 365), 0)
        draw_dir_masc = ImageDraw.Draw(mascara_direita)
        draw_dir_masc.rounded_rectangle([0, 0, 260, 365], radius=15, fill=255)

        img_perfil.paste(img_estrutura_colorida, (0, 0), img_estrutura_colorida)
        img_perfil.paste(img_avatar, (100, 75), mascara_avatar)
        img_perfil.paste(img_direita, (605, 110), mascara_direita)
        # Reposicionamento do ícone de biscoito para x=100 y=406
        img_perfil.paste(img_biscoito, (100, 406), img_biscoito)

        # 5. CONFIGURAÇÃO DAS FONTES (Carregando os bytes baixados do GitHub)
        try:
            # Fontes do topo com tamanhos corrigidos: crewniverse 10 e montserrat 12
            font_topo_crewniverse = ImageFont.truetype(io.BytesIO(font_crewniverse_bytes), 10)
            font_topo_montserrat = ImageFont.truetype(io.BytesIO(font_montserrat_bytes), 12)
            
            # Ajustes gerais de tamanho solicitados: Nome para 28, estáticos para 18, dinâmicos para 18
            font_crewniverse_p = ImageFont.truetype(io.BytesIO(font_crewniverse_bytes), 16)
            font_crewniverse_m = ImageFont.truetype(io.BytesIO(font_crewniverse_bytes), 18)
            font_crewniverse_g = ImageFont.truetype(io.BytesIO(font_crewniverse_bytes), 28)
            font_montserrat = ImageFont.truetype(io.BytesIO(font_montserrat_bytes), 18)
        except IOError:
            font_topo_crewniverse = font_topo_montserrat = font_crewniverse_p = font_crewniverse_m = font_crewniverse_g = font_montserrat = ImageFont.load_default()

        draw = ImageDraw.Draw(img_perfil)
        
        # Rastreamentos distintos (tracking_topo mudado para -1)
        tracking_su = -2
        tracking_topo = -1

        # Cabeçalho do topo reposicionado para x=25 y=20 com tracking -1
        x_topo, y_topo = 25, 20
        texto_su = "CARTOONDEX"
        self.draw_text_with_tracking(draw, (x_topo, y_topo), texto_su, font_topo_crewniverse, (255, 255, 255), tracking_topo, stroke_width=2, stroke_fill=cor_rgb)
        largura_su = sum([draw.textlength(c, font=font_topo_crewniverse) + tracking_topo for c in texto_su])
        
        texto_resto = " - O BOT ORIGINAL DO SERVIDOR  • STEVEN UNIVERSE BR •"
        self.draw_text_with_tracking(draw, (x_topo + largura_su + 5, y_topo - 1), texto_resto, font_topo_montserrat, (255, 255, 255), tracking_topo, stroke_width=2, stroke_fill=cor_rgb)

        # TEXTO 2: Apelido do Usuário reposicionado para x=100 y=295 (tamanho 28)
        self.draw_text_with_tracking(draw, (100, 295), nome_exibido, font_crewniverse_g, (255, 255, 255), tracking_su)

        # TEXTO 3: TOTAL DE CARTAS reposicionado para x=100 y=340
        x_cartas, y_cartas = 100, 340
        self.draw_text_with_tracking(draw, (x_cartas, y_cartas), "TOTAL DE CARTAS: ", font_montserrat, (255, 255, 255), tracking_su)
        largura_txt1 = sum([draw.textlength(c, font_montserrat) + tracking_su for c in "TOTAL DE CARTAS: "])
        self.draw_text_with_tracking(draw, (x_cartas + largura_txt1, y_cartas - 2), str(total_cartas), font_crewniverse_m, (255, 255, 255), tracking_su)

        # TEXTO 4: PROGRESSO DA DEX reposicionado para x=100 y=360
        y_dex = 360
        self.draw_text_with_tracking(draw, (x_cartas, y_dex), "PROGRESSO DA DEX: ", font_montserrat, (255, 255, 255), tracking_su)
        largura_txt2 = sum([draw.textlength(c, font_montserrat) + tracking_su for c in "PROGRESSO DA DEX: "])
        self.draw_text_with_tracking(draw, (x_cartas + largura_txt2, y_dex - 2), f"{cartas_unicas}/{total_global_dex}", font_crewniverse_m, (255, 255, 255), tracking_su)

        # TEXTO 5: Saldo de Biscoitos reposicionado para x=150 y=410
        x_biscoito, y_biscoito = 150, 410
        str_biscoitos = f"{biscoitos} "
        next_x = self.draw_text_with_tracking(draw, (x_biscoito, y_biscoito - 2), str_biscoitos, font_crewniverse_m, (255, 255, 255), tracking_su)
        
        # Condicional gramatical: se 0 ou 1 fica no singular, caso contrário plural
        texto_biscoito_sufixo = "BISCOITO GATINHO" if biscoitos in (0, 1) else "BISCOITOS GATINHO"
        self.draw_text_with_tracking(draw, (next_x, y_biscoito), texto_biscoito_sufixo, font_montserrat, (255, 255, 255), tracking_su)

        # TEXTO 6: Faixa "CARTA DESTAQUE"
        self.draw_text_with_tracking(draw, (625, 432), "CARTA DESTAQUE", font_crewniverse_m, (255, 255, 255), tracking_su)

        # CONDICIONAL DO AVISO
        if not carta_fav:
            subtexto_aviso = "NENHUMA CARTA SELECIONADA"
            largura_aviso = sum([draw.textlength(c, font=font_crewniverse_p) + tracking_su for c in subtexto_aviso])
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