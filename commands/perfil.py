import os
import io
import aiohttp
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
        
        # Cache das fontes prontas (Instanciadas no tamanho correto)
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

        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(url_estrutura) as r: self.cache_estrutura = await r.read()
                async with session.get(url_biscoito_icon) as r: self.cache_biscoito = await r.read()
                async with session.get(url_padrao) as r: self.cache_padrao = await r.read()
                async with session.get(url_fundo_praia) as r: self.cache_fundo_praia = await r.read()
                
                font_crewniverse_bytes = await (await session.get(url_font_crewniverse)).read()
                font_montserrat_bytes = await (await session.get(url_font_montserrat)).read()
                
                # Instanciando as fontes de forma definitiva na RAM
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
                # Fallback caso falte alguma fonte
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

    @app_commands.command(name="perfil", description="Exibe seu perfil personalizado do CartoonDex!")
    async def perfil(self, interaction: discord.Interaction):
        await interaction.response.defer()

        user_id = interaction.user.id
        avatar_url = interaction.user.display_avatar.with_format("png").url

        # 1. BUSCA OTIMIZADA (3 Queries em 1 só)
        async with self.bot.pool.acquire() as conn:
            db_data = await conn.fetchrow("""
                WITH upsert_user AS (
                    INSERT INTO usuarios (user_id, apelido, biscoitos, carta_favorita, cor_estrutura, fundo_equipado)
                    VALUES ($1, $2, 0, NULL, '#2b2b5f', 'praia-dia')
                    ON CONFLICT (user_id) DO UPDATE SET user_id = usuarios.user_id
                    RETURNING apelido, biscoitos, carta_favorita, cor_estrutura, fundo_equipado
                )
                SELECT 
                    u.apelido, u.biscoitos, u.carta_favorita, u.cor_estrutura, u.fundo_equipado,
                    (SELECT COUNT(*) FROM inventario WHERE user_id = $1) as total_cartas,
                    (SELECT COUNT(DISTINCT dex) FROM inventario WHERE user_id = $1) as cartas_unicas,
                    (SELECT MAX(dex::integer) FROM dex) as total_global_dex
                FROM upsert_user u;
            """, user_id, interaction.user.display_name)

        nome_exibido = db_data["apelido"]
        biscoitos = db_data["biscoitos"]
        carta_fav = db_data["carta_favorita"]
        hex_cor = db_data["cor_estrutura"] or '#2b2b5f'
        fundo = db_data["fundo_equipado"] or "praia-dia"
        total_cartas = db_data["total_cartas"] or 0
        cartas_unicas = db_data["cartas_unicas"] or 0
        total_global_dex = db_data["total_global_dex"] or 13

        cor_rgb = tuple(int(hex_cor.lstrip('#')[i:i+2], 16) for i in (0, 2, 4))
        github_base = os.getenv("GITHUB_BASE")

        # 2. SELEÇÃO FLUIDA DE CENÁRIO
        cenario_bytes = None
        if fundo == "praia-dia" and self.cache_fundo_praia:
            cenario_bytes = self.cache_fundo_praia
        else:
            url_cenario = f"{github_base}/assets/perfil/fundo/{fundo}.png"

        if carta_fav:
            url_direita_recurso = f"{github_base}/assets/cartas/{carta_fav}/{carta_fav}-0-carta.png"

        # 3. REQUISIÇÕES WEB REDUZIDAS
        async with aiohttp.ClientSession() as session:
            avatar_bytes = await (await session.get(avatar_url)).read()
            
            if not cenario_bytes:
                cenario_bytes = await (await session.get(url_cenario)).read()
            
            if carta_fav:
                try:
                    direita_bytes = await (await session.get(url_direita_recurso)).read()
                except Exception:
                    direita_bytes = self.cache_padrao
                    carta_fav = None
            else:
                direita_bytes = self.cache_padrao

        # 4. MONTAGEM DIRETA DAS CAMADAS (Sem resizes desnecessários)
        try:
            img_perfil = Image.open(io.BytesIO(cenario_bytes)).convert("RGBA") # Já está em 900x500
            img_biscoito = Image.open(io.BytesIO(self.cache_biscoito)).convert("RGBA") # Já está no tamanho exato
            img_estrutura_base = Image.open(io.BytesIO(self.cache_estrutura)).convert("RGBA")
            img_avatar = Image.open(io.BytesIO(avatar_bytes)).convert("RGBA").resize((200, 200)) # Obrigatório resize
            
            if carta_fav:
                img_direita = Image.open(io.BytesIO(direita_bytes)).convert("RGBA").resize((250, 350)) # Redimensiona carta
            else:
                img_direita = Image.open(io.BytesIO(direita_bytes)).convert("RGBA") # Padrão já está no tamanho certo
        except Exception:
            return await interaction.followup.send("❌ Erro ao renderizar as camadas do seu Perfil.")

        img_cor_solida = Image.new("RGBA", img_estrutura_base.size, cor_rgb)
        img_estrutura_colorida = Image.composite(img_cor_solida, Image.new("RGBA", img_estrutura_base.size, (0, 0, 0, 0)), img_estrutura_base)
        
        mascara_avatar = Image.new("L", (200, 200), 0)
        ImageDraw.Draw(mascara_avatar).rounded_rectangle([0, 0, 200, 200], radius=15, fill=255)

        mascara_direita = Image.new("L", (250, 350), 0)
        ImageDraw.Draw(mascara_direita).rounded_rectangle([0, 0, 250, 350], radius=15, fill=255)

        img_perfil.paste(img_estrutura_colorida, (0, 0), img_estrutura_colorida)
        img_perfil.paste(img_avatar, (100, 75), mascara_avatar)
        img_perfil.paste(img_direita, (550, 60), mascara_direita)
        img_perfil.paste(img_biscoito, (100, 406), img_biscoito)

        # 5. ESCRITA DOS TEXTOS UTILIZANDO O CACHE
        draw = ImageDraw.Draw(img_perfil)
        
        tracking_dados = 0
        tracking_su = -2
        tracking_topo = 1

        # Cabeçalho Superior Esquerdo (x=25 y=20)
        x_topo, y_topo = 25, 20
        texto_su = "CARTOONDEX"
        self.draw_text_with_tracking(draw, (x_topo, y_topo), texto_su, self.font_topo_crewniverse, (255, 255, 255), tracking_topo, stroke_width=2, stroke_fill=cor_rgb)
        largura_su = sum([draw.textlength(c, font=self.font_topo_crewniverse) + tracking_topo for c in texto_su])
        
        texto_resto = " - O BOT ORIGINAL DO SERVIDOR  • STEVEN UNIVERSE BR •"
        self.draw_text_with_tracking(draw, (x_topo + largura_su + 5, y_topo - 1), texto_resto, self.font_topo_montserrat, (255, 255, 255), tracking_topo, stroke_width=2, stroke_fill=cor_rgb)

        # Apelido
        self.draw_text_with_tracking(draw, (100, 295), nome_exibido, self.font_crewniverse_g, (255, 255, 255), tracking_su)

        # TOTAL DE CARTAS
        x_cartas, y_cartas = 100, 340
        self.draw_text_with_tracking(draw, (x_cartas, y_cartas), "TOTAL DE CARTAS :   ", self.font_montserrat, (255, 255, 255), tracking_dados)
        largura_txt1 = sum([draw.textlength(c, font=self.font_montserrat) + tracking_dados for c in "TOTAL DE CARTAS :   "])
        self.draw_text_with_tracking(draw, (x_cartas + largura_txt1, y_cartas - 2), str(total_cartas), self.font_crewniverse_m, (255, 255, 255), tracking_dados)

        # PROGRESSO DA DEX
        y_dex = 360
        self.draw_text_with_tracking(draw, (x_cartas, y_dex), "PROGRESSO DA DEX :   ", self.font_montserrat, (255, 255, 255), tracking_dados)
        largura_txt2 = sum([draw.textlength(c, font=self.font_montserrat) + tracking_dados for c in "PROGRESSO DA DEX :   "])
        self.draw_text_with_tracking(draw, (x_cartas + largura_txt2, y_dex - 2), f"{cartas_unicas}/{total_global_dex}", self.font_crewniverse_m, (255, 255, 255), tracking_dados)

        # Saldo de Biscoitos
        x_biscoito, y_biscoito = 160, 410
        str_biscoitos = f"{biscoitos}  "
        next_x = self.draw_text_with_tracking(draw, (x_biscoito, y_biscoito - 2), str_biscoitos, self.font_crewniverse_m, (255, 255, 255), tracking_dados)
        
        texto_biscoito_sufixo = "BISCOITO GATINHO" if biscoitos in (0, 1) else "BISCOITOS GATINHO"
        self.draw_text_with_tracking(draw, (next_x, y_biscoito), texto_biscoito_sufixo, self.font_montserrat, (255, 255, 255), tracking_dados)

        # Faixa "CARTA DESTAQUE"
        self.draw_text_with_tracking(draw, (560, 421), "CARTA DESTAQUE", self.font_carta_destaque, (255, 255, 255), 0)

        # Condicional do Aviso
        if not carta_fav:
            subtexto_aviso = "NENHUMA CARTA SELECIONADA"
            self.draw_text_with_tracking(draw, (559, 457), subtexto_aviso, self.font_aviso_montserrat, (255, 255, 255), 1, stroke_width=2, stroke_fill=cor_rgb)

        # 6. ENVIO DO BUFFER
        buffer = io.BytesIO()
        img_perfil.save(buffer, format="PNG")
        buffer.seek(0)

        await interaction.followup.send(file=discord.File(fp=buffer, filename="perfil.png"))

async def setup(bot):
    await bot.add_cog(Perfil(bot))