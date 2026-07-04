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
        # Variáveis para guardar o cache de tudo na memória RAM do Railway
        self.cache_estrutura = None
        self.cache_biscoito = None
        self.cache_padrao = None
        self.cache_fundo_praia = None
        self.cache_font_crewniverse = None
        self.cache_font_montserrat = None

    # Função que roda AUTOMATICAMENTE assim que o bot liga para salvar tudo na RAM
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
                async with session.get(url_font_crewniverse) as r: self.cache_font_crewniverse = await r.read()
                async with session.get(url_font_montserrat) as r: self.cache_font_montserrat = await r.read()
                print("✅ [Perfil] Tudo foi salvo na memória RAM do Railway com sucesso!")
            except Exception as e:
                print(f"❌ [Perfil] Erro ao carregar recursos para a RAM: {e}")

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
            
            total_cartas = await conn.fetchval("SELECT COUNT(*) FROM inventario WHERE user_id = $1", user_id) or 0
            cartas_unicas = await conn.fetchval("SELECT COUNT(DISTINCT dex) FROM inventario WHERE user_id = $1", user_id) or 0
            total_global_dex = await conn.fetchval("SELECT MAX(dex::integer) FROM dex") or 13

        nome_exibido = user_data["apelido"]
        biscoitos = user_data["biscoitos"]
        carta_fav = user_data["carta_favorita"]
        hex_cor = user_data["cor_estrutura"] or '#2b2b5f'
        fundo = user_data["fundo_equipado"] or "praia-dia"

        cor_rgb = tuple(int(hex_cor.lstrip('#')[i:i+2], 16) for i in (0, 2, 4))
        github_base = os.getenv("GITHUB_BASE")

        # 2. DEFINIÇÃO DINÂMICA
        cenario_bytes = None
        if fundo == "praia-dia" and self.cache_fundo_praia:
            cenario_bytes = self.cache_fundo_praia
        else:
            url_cenario = f"{github_base}/assets/perfil/fundo/{fundo}.png"

        direita_bytes = None
        if carta_fav:
            url_direita_recurso = f"{github_base}/assets/cartas/{carta_fav}/{carta_fav}-0-carta.png"

        # 3. ÚNICA REQUISIÇÃO INTERNET OBRIGATÓRIA: O AVATAR DO USUÁRIO
        async with aiohttp.ClientSession() as session:
            async with session.get(avatar_url) as r: avatar_bytes = await r.read()
            
            if not cenario_bytes:
                async with session.get(url_cenario) as r: cenario_bytes = await r.read()
            
            if carta_fav:
                async with session.get(url_direita_recurso) as r: direita_bytes = await r.read()

        if not direita_bytes:
            direita_bytes = self.cache_padrao

        # 4. MONTAGEM DAS CAMADAS COM PILLOW
        try:
            img_perfil = Image.open(io.BytesIO(cenario_bytes)).convert("RGBA").resize((900, 500))
        except Exception:
            return await interaction.followup.send("❌ Erro ao carregar o cenário de fundo.")

        try:
            img_biscoito = Image.open(io.BytesIO(self.cache_biscoito)).convert("RGBA").resize((45, 29))
        except Exception:
            return await interaction.followup.send("❌ Erro ao carregar o ícone do biscoito.")

        try:
            img_estrutura_base = Image.open(io.BytesIO(self.cache_estrutura)).convert("RGBA")
        except Exception:
            return await interaction.followup.send("❌ Erro ao carregar a estrutura do perfil.")

        try:
            img_avatar = Image.open(io.BytesIO(avatar_bytes)).convert("RGBA").resize((200, 200))
        except Exception:
            return await interaction.followup.send("❌ Erro ao processar o seu avatar.")

        try:
            img_direita = Image.open(io.BytesIO(direita_bytes)).convert("RGBA").resize((250, 350))
        except Exception:
            return await interaction.followup.send("❌ Erro ao carregar a imagem da direita.")

        img_cor_solida = Image.new("RGBA", img_estrutura_base.size, cor_rgb)
        img_estrutura_colorida = Image.composite(img_cor_solida, Image.new("RGBA", img_estrutura_base.size, (0, 0, 0, 0)), img_estrutura_base)
        
        mascara_avatar = Image.new("L", (200, 200), 0)
        draw_masc = ImageDraw.Draw(mascara_avatar)
        draw_masc.rounded_rectangle([0, 0, 200, 200], radius=15, fill=255)

        mascara_direita = Image.new("L", (250, 350), 0)
        draw_dir_masc = ImageDraw.Draw(mascara_direita)
        draw_dir_masc.rounded_rectangle([0, 0, 250, 350], radius=15, fill=255)

        img_perfil.paste(img_estrutura_colorida, (0, 0), img_estrutura_colorida)
        img_perfil.paste(img_avatar, (100, 75), mascara_avatar)
        img_perfil.paste(img_direita, (550, 60), mascara_direita)
        img_perfil.paste(img_biscoito, (100, 406), img_biscoito)

        # 5. CARREGAMENTO DAS FONTES DA RAM
        try:
            font_topo_crewniverse = ImageFont.truetype(io.BytesIO(self.cache_font_crewniverse), 12)
            font_topo_montserrat = ImageFont.truetype