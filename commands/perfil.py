import os
import io
import asyncio
import discord
from discord import app_commands
from discord.ext import commands
from PIL import Image, ImageDraw, ImageFont

class Perfil(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Cache de arquivos brutos na RAM
        self.cache_estrutura = None
        self.cache_biscoito = None
        self.cache_padrao = None
        self.cache_fundo_praia = None
        
        # Cache das fontes prontas
        self.font_topo_crewniverse = None
        self.font_topo_montserrat = None
        self.font_aviso_montserrat = None
        self.font_crewniverse_m = None
        self.font_carta_destaque = None
        self.font_crewniverse_g = None
        self.font_montserrat = None

    async def cog_load(self):
        github_base = os.getenv("GITHUB_BASE")
        url_estrutura = f"{github_base}/assets/perfil/estrutura/estrutura.png"
        url_biscoito_icon = f"{github_base}/assets/icones/biscoito.png"
        url_padrao = f"{github_base}/assets/perfil/nenhuma-carta-selecionada/padrao.png"
        url_fundo_praia = f"{github_base}/assets/perfil/fundo/praia-dia.png"
        url_font_crewniverse = f"{github_base}/assets/fontes/CREWNIVERSE_FONT.TTF"
        url_font_montserrat = f"{github_base}/assets/fontes/MONTSERRAT-SEMIBOLD.OTF"

        session = self.bot.aiohttp_session
        try:
            async with session.get(url_estrutura) as r: self.cache_estrutura = await r.read()
            async with session.get(url_biscoito_icon) as r: self.cache_biscoito = await r.read()
            async with session.get(url_padrao) as r: self.cache_padrao = await r.read()
            async with session.get(url_fundo_praia) as r: self.cache_fundo_praia = await r.read()
            
            font_crewniverse_bytes = await (await session.get(url_font_crewniverse)).read()
            font_montserrat_bytes = await (await session.get(url_font_montserrat)).read()
            
            self.font_topo_crewniverse = ImageFont.truetype(io.BytesIO(font_crewniverse_bytes), 12)
            self.font_topo_montserrat = ImageFont.truetype(io.BytesIO(font_montserrat_bytes), 10)
            self.font_aviso_montserrat = ImageFont.truetype(io.BytesIO(font_montserrat_bytes), 12)
            self.font_crewniverse_m = ImageFont.truetype(io.BytesIO(font_crewniverse_bytes), 18)
            self.font_carta_destaque = ImageFont.truetype(io.BytesIO(font_crewniverse_bytes), 20)
            self.font_crewniverse_g = ImageFont.truetype(io.BytesIO(font_crewniverse_bytes), 28)
            self.font_montserrat = ImageFont.truetype(io.BytesIO(font_montserrat_bytes), 18)
            
            print("✅ [Perfil] Recursos e instâncias de fontes cacheados com sucesso!")
        except Exception as e:
            print(f"❌ [Perfil] Erro ao carregar recursos para a RAM: {e}")
            self.font_topo_crewniverse = self.font_topo_montserrat = self.font_aviso_montserrat = \
            self.font_crewniverse_m = self.font_carta_destaque = self.font_crewniverse_g = \
            self.font_montserrat = ImageFont.load_default()

    def draw_text_with_tracking(self, draw, position, text, font, fill, tracking, stroke_width=0, stroke_fill=None):
        x, y = position
        for char in text:
            draw.text((x, y), char, font=font, fill=fill, stroke_width=stroke_width, stroke_fill=stroke_fill)
            char_width = draw.textlength(char, font=font)
            x += char_width + tracking
        return x

    def _renderizar_imagem_perfil(self, cenario_bytes, avatar_bytes, direita_bytes, moldura_bytes, cor_rgb, nome_exibido, total_cartas, cartas_unicas, total_global_dex, biscoitos, carta_fav):
        img_perfil = Image.open(io.BytesIO(cenario_bytes)).convert("RGBA")
        img_biscoito = Image.open(io.BytesIO(self.cache_biscoito)).convert("RGBA")
        img_estrutura_base = Image.open(io.BytesIO(self.cache_estrutura)).convert("RGBA")
        img_avatar = Image.open(io.BytesIO(avatar_bytes)).convert("RGBA").resize((200, 200))
        
        if carta_fav:
            img_direita = Image.open(io.BytesIO(direita_bytes)).convert("RGBA").resize((250, 350))
        else:
            img_direita = Image.open(io.BytesIO(direita_bytes)).convert("RGBA")

        img_cor_solida = Image.new("RGBA", img_estrutura_base.size, cor_rgb)
        img_estrutura_colorica = Image.composite(img_cor_solida, Image.new("RGBA", img_estrutura_base.size, (0, 0, 0, 0)), img_estrutura_base)
        
        mascara_avatar = Image.new("L", (200, 200), 0)
        ImageDraw.Draw(mascara_avatar).rounded_rectangle([0, 0, 200, 200], radius=15, fill=255)

        mascara_direita = Image.new("L", (250, 350), 0)
        ImageDraw.Draw(mascara_direita).rounded_rectangle([0, 0, 250, 350], radius=15, fill=255)

        img_perfil.paste(img_estrutura_colorica, (0, 0), img_estrutura_colorica)
        img_perfil.paste(img_avatar, (100, 75), mascara_avatar)
        
        img_perfil.paste(img_direita, (550, 60), mascara_direita)
        
        if carta_fav and moldura_bytes:
            img_moldura = Image.open(io.BytesIO(moldura_bytes)).convert("RGBA").resize((250, 350))
            img_perfil.paste(img_moldura, (550, 60), img_moldura)

        img_perfil.paste(img_biscoito, (100, 406), img_biscoito)

        draw = ImageDraw.Draw(img_perfil)
        tracking_dados = 0
        tracking_su = -2
        tracking_topo = 1

        x_topo, y_topo = 25, 20
        texto_su = "CARTOONDEX"
        self.draw_text_with_tracking(draw, (x_topo, y_topo), texto_su, self.font_topo_crewniverse, (255, 255, 255), tracking_topo, stroke_width=2, stroke_fill=cor_rgb)
        largura_su = sum([draw.textlength(c, font=self.font_topo_crewniverse) + tracking_topo for c in texto_su])
        
        texto_resto = " - O BOT ORIGINAL DO SERVIDOR  • STEVEN UNIVERSE BR •"
        self.draw_text_with_tracking(draw, (x_topo + largura_su + 5, y_topo - 1), texto_resto, self.font_topo_montserrat, (255, 255, 255), tracking_topo, stroke_width=2, stroke_fill=cor_rgb)

        self.draw_text_with_tracking(draw, (100, 295), nome_exibido, self.font_crewniverse_g, (255, 255, 255), tracking_su)

        x_cartas