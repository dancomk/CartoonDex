import os
import io
import json
import requests
import psycopg2
from psycopg2.extras import RealDictCursor
from PIL import Image, ImageDraw, ImageFont

# Cache em memória: { "0001-0": <PIL.Image.Image> }
CARTAS_CACHE = {}

# =============================================================================
# CONFIGURAÇÃO DE BANCO E GITHUB
# =============================================================================
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://neondb_owner:npg_L1GeKJy3SZWx@ep-wild-sea-actyw8rs-pooler.sa-east-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require"
)

# URL Base para baixar as imagens das cartas direto do repositório
GITHUB_RAW_URL = "https://raw.githubusercontent.com/dancomk/CartoonDex/main/assets/cartas"

# Caminho relativo para carregar as fontes que acompanham o bot no projeto
PASTA_RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PASTA_FONTES = os.path.join(PASTA_RAIZ, "assets", "fontes")

FONTE_CREWNIVERSE = os.path.join(PASTA_FONTES, "crewniverse_font.ttf")
FONTE_MONTSERRAT = os.path.join(PASTA_FONTES, "Montserrat-SemiBold.otf")


# =============================================================================
# FUNÇÕES DE DESENHO E FORMATADORAS
# =============================================================================
def desenhar_texto_com_borda(draw, pos, texto, font, fill, stroke_fill, stroke_width, anchor):
    """Desenha o texto aplicando borda/contorno se definido."""
    if not texto:
        return
    if stroke_fill and stroke_width > 0:
        draw.text(
            pos, str(texto), font=font, fill=fill,
            stroke_width=stroke_width, stroke_fill=stroke_fill, anchor=anchor
        )
    else:
        draw.text(pos, str(texto), font=font, fill=fill, anchor=anchor)


def desenhar_icone_custo(draw, x_estrela, y, custo_valor, fonte_estrela, fonte_num):
    """Desenha o símbolo de custo (estrela com borda + sombra + número sobreposto)."""
    if custo_valor is None:
        return

    texto_custo = str(custo_valor)
    texto_estrela = "*"

    COR_AMARELO_ESTRELA = (255, 237, 0)
    COR_LARANJA_BORDA = (225, 97, 50)
    COR_BRANCO = (255, 255, 255)
    COR_PRETO = (0, 0, 0)

    # Sombra da estrela
    draw.text(
        (x_estrela, y + 3), texto_estrela, font=fonte_estrela,
        fill=COR_LARANJA_BORDA, stroke_width=2, stroke_fill=COR_LARANJA_BORDA,
        anchor="ls"
    )

    # Estrela principal
    draw.text(
        (x_estrela, y), texto_estrela, font=fonte_estrela,
        fill=COR_AMARELO_ESTRELA, stroke_width=2, stroke_fill=COR_LARANJA_BORDA,
        anchor="ls"
    )

    # Ajuste para números 1 e 4
    x_num = 208
    if texto_custo in ["1", "4"]:
        x_num -= 1

    # Número centralizado
    draw.text(
        (x_num, y - 5), texto_custo, font=fonte_num,
        fill=COR_BRANCO, stroke_width=2, stroke_fill=COR_PRETO,
        anchor="ms"
    )


def quebrar_texto(texto, font, max_width, draw):
    """Quebra o texto em várias linhas sem cortar palavras."""
    if not texto:
        return []
    palavras = str(texto).split()
    linhas = []
    linha_atual = []

    for palavra in palavras:
        test_line = ' '.join(linha_atual + [palavra])
        bbox = draw.textbbox((0, 0), test_line, font=font)
        w = bbox[2] - bbox[0]
        if w <= max_width:
            linha_atual.append(palavra)
        else:
            if linha_atual:
                linhas.append(' '.join(linha_atual))
            linha_atual = [palavra]

    if linha_atual:
        linhas.append(' '.join(linha_atual))

    return linhas


# =============================================================================
# DOWNLOAD DA IMAGEM BASE (DIRETO DO GITHUB)
# =============================================================================
def baixar_imagem_github(carta_id):
    """Baixa a imagem base da carta diretamente da URL Raw do GitHub."""
    url_github = f"{GITHUB_RAW_URL}/{carta_id}.png"
    try:
        response = requests.get(url_github, timeout=15)
        if response.status_code == 200:
            return Image.open(io.BytesIO(response.content)).convert("RGBA")
        else:
            print(f"⚠️ Imagem '{carta_id}.png' não encontrada no GitHub (HTTP Status: {response.status_code}).")
    except Exception as e:
        print(f"❌ Erro de conexão ao baixar imagem base do GitHub ({carta_id}): {e}")

    return None


# =============================================================================
# RENDERIZADOR INDIVIDUAL DE CARTA
# =============================================================================
def renderizar_carta(dados_carta, carta_id):
    """Baixa a arte base do GitHub e aplica os dados do banco sobre ela."""
    img = baixar_imagem_github(carta_id)
    if not img:
        return None

    draw = ImageDraw.Draw(img)

    # Estilo Full Art vs Normal
    full_art_val = dados_carta.get("full_art")
    is_full_art = full_art_val is not None and str(full_art_val).strip().lower() == "sim"

    if is_full_art:
        cor_texto = (0, 0, 0)
        cor_borda = (255, 255, 255)
        espessura_borda = 2
    else:
        cor_texto = (0, 0, 0)
        cor_borda = None
        espessura_borda = 0

    fonte_estrela_custo = ImageFont.truetype(FONTE_CREWNIVERSE, 24)
    fonte_num_custo = ImageFont.truetype(FONTE_CREWNIVERSE, 21)

    # NOME DA CARTA / SKIN
    nome_exibir = dados_carta.get("skin_nome") or dados_carta.get("nome")
    if nome_exibir:
        tamanho_fonte = 28
        fonte_nome = ImageFont.truetype(FONTE_CREWNIVERSE, tamanho_fonte)
        
        while tamanho_fonte > 10:
            bbox = draw.textbbox((0, 0), str(nome_exibir), font=fonte_nome)
            largura = bbox[2] - bbox[0]
            if largura <= 280:
                break
            tamanho_fonte -= 1
            fonte_nome = ImageFont.truetype(FONTE_CREWNIVERSE, tamanho_fonte)

        desenhar_texto_com_borda(draw, (185, 200), nome_exibir, fonte_nome, cor_texto, cor_borda, espessura_borda, anchor="ls")

    # ORIGEM
    origem = dados_carta.get("origem")
    if origem:
        fonte_origem = ImageFont.truetype(FONTE_CREWNIVERSE, 12)
        desenhar_texto_com_borda(draw, (185, 220), origem, fonte_origem, cor_texto, cor_borda, espessura_borda, anchor="ls")

    # VIDA (HP)
    hp = dados_carta.get("hp")
    if hp is not None:
        fonte_vida_rotulo = ImageFont.truetype(FONTE_CREWNIVERSE, 12)
        fonte_vida_num = ImageFont.truetype(FONTE_CREWNIVERSE, 48)

        str_hp = str(hp)
        bbox_num = draw.textbbox((0, 0), str_hp, font=fonte_vida_num)
        largura_num = bbox_num[2] - bbox_num[0]

        desenhar_texto_com_borda(draw, (615, 212), str_hp, fonte_vida_num, cor_texto, cor_borda, espessura_borda, anchor="rs")

        pos_x_vida = 615 - largura_num - 8
        desenhar_texto_com_borda(draw, (pos_x_vida, 218), "VIDA", fonte_vida_rotulo, cor_texto, cor_borda, espessura_borda, anchor="rs")

    # HABILIDADE 1
    hab1 = dados_carta.get("habilidade1") or {}
    if isinstance(hab1, str):
        try:
            hab1 = json.loads(hab1)
        except Exception:
            hab1 = {}

    y_hab1 = 660

    custo1 = hab1.get("custo")
    if custo1 is not None:
        desenhar_icone_custo(draw, 187, y_hab1, custo1, fonte_estrela_custo, fonte_num_custo)

    hab1_nome = hab1.get("nome")
    if hab1_nome:
        fonte_hab = ImageFont.truetype(FONTE_CREWNIVERSE, 21)
        desenhar_texto_com_borda(draw, (240, y_hab1), hab1_nome, fonte_hab, cor_texto, cor_borda, espessura_borda, anchor="ls")

    hab1_dano = hab1.get("dano")
    if hab1_dano is not None:
        fonte_hab = ImageFont.truetype(FONTE_CREWNIVERSE, 21)
        desenhar_texto_com_borda(draw, (615, y_hab1), str(hab1_dano), fonte_hab, cor_texto, cor_borda, espessura_borda, anchor="rs")
        
        if hab1.get("efeito") == "DANO_EM_AREA":
            desenhar_texto_com_borda(draw, (616, y_hab1), "+", fonte_hab, cor_texto, cor_borda, espessura_borda, anchor="ls")

    hab1_desc = hab1.get("descricao")
    if hab1_desc:
        fonte_desc = ImageFont.truetype(FONTE_MONTSERRAT, 16)
        linhas = quebrar_texto(hab1_desc, fonte_desc, 430, draw)
        y_cursor = 680
        for linha in linhas:
            desenhar_texto_com_borda(draw, (185, y_cursor), linha, fonte_desc, cor_texto, cor_borda, espessura_borda, anchor="lt")
            y_cursor += 20

    # HABILIDADE 2
    hab2 = dados_carta.get("habilidade2") or {}
    if isinstance(hab2, str):
        try:
            hab2 = json.loads(hab2)
        except Exception:
            hab2 = {}

    y_hab2 = 775

    custo2 = hab2.get("custo")
    if custo2 is not None:
        desenhar_icone_custo(draw, 187, y_hab2, custo2, fonte_estrela_custo, fonte_num_custo)

    hab2_nome = hab2.get("nome")
    if hab2_nome:
        fonte_hab = ImageFont.truetype(FONTE_CREWNIVERSE, 21)
        desenhar_texto_com_borda(draw, (240, y_hab2), hab2_nome, fonte_hab, cor_texto, cor_borda, espessura_borda, anchor="ls")

    hab2_dano = hab2.get("dano")
    if hab2_dano is not None:
        fonte_hab = ImageFont.truetype(FONTE_CREWNIVERSE, 21)
        desenhar_texto_com_borda(draw, (615, y_hab2), str(hab2_dano), fonte_hab, cor_texto, cor_borda, espessura_borda, anchor="rs")
        
        if hab2.get("efeito") == "DANO_EM_AREA":
            desenhar_texto_com_borda(draw, (616, y_hab2), "+", fonte_hab, cor_texto, cor_borda, espessura_borda, anchor="ls")

    hab2_desc = hab2.get("descricao")
    if hab2_desc:
        fonte_desc = ImageFont.truetype(FONTE_MONTSERRAT, 16)
        linhas = quebrar_texto(hab2_desc, fonte_desc, 430, draw)
        y_cursor = 795
        for linha in linhas:
            desenhar_texto_com_borda(draw, (185, y_cursor), linha, fonte_desc, cor_texto, cor_borda, espessura_borda, anchor="lt")
            y_cursor += 20

    # ARTE: ARTISTA
    artista = dados_carta.get("artista")
    fonte_rodape = ImageFont.truetype(FONTE_CREWNIVERSE, 12)

    nome_artista = str(artista).strip().upper() if artista else "SEM INFORMAÇÕES"
    texto_artista = f"ARTE: {nome_artista}"

    desenhar_texto_com_borda(draw, (185, 915), texto_artista, fonte_rodape, cor_texto, cor_borda, espessura_borda, anchor="ls")

    # ID DA CARTA
    str_carta_id = dados_carta.get("carta_id", carta_id)
    if str_carta_id:
        if not str(str_carta_id).startswith("#"):
            str_carta_id = f"#{str_carta_id}"
        desenhar_texto_com_borda(draw, (615, 915), str_carta_id, fonte_rodape, cor_texto, cor_borda, espessura_borda, anchor="rs")

    return img


# =============================================================================
# INICIALIZAÇÃO E CARREGAMENTO GERAL NA RAM
# =============================================================================
def carregar_e_gerar_todas_as_cartas():
    """Conecta no Neon, baixa as imagens base do GitHub e pré-carrega tudo na memória RAM."""
    global CARTAS_CACHE
    print("🔄 [MEMÓRIA] Conectando ao Neon para carregar os registros de cartas...")
    
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        cursor.execute("SELECT * FROM dex;")
        todas_cartas = cursor.fetchall()
        
        cursor.close()
        conn.close()

        print(f"📥 {len(todas_cartas)} registro(s) obtido(s) do banco de dados.")

        for dados in todas_cartas:
            carta_id = dados.get("carta_id")
            if not carta_id:
                continue

            print(f"  ├─ Baixando base e gerando '{carta_id}' via GitHub...")
            imagem_gerada = renderizar_carta(dados, carta_id)

            if imagem_gerada:
                CARTAS_CACHE[carta_id] = imagem_gerada
                print(f"  └─ ✅ Carta '{carta_id}' pronta na memória RAM!")

        print(f"⚡ [MEMÓRIA] Concluído com sucesso! {len(CARTAS_CACHE)} carta(s) prontas no cache de RAM.")

    except Exception as e:
        print(f"❌ Erro ao inicializar cartas na memória: {e}")


def obter_bytes_carta(carta_id):
    """
    Retorna uma tupla com (buffer_io, "xxxx-x.png") extraída da memória RAM.
    """
    imagem = CARTAS_CACHE.get(carta_id)
    if not imagem:
        return None, None

    buffer = io.BytesIO()
    imagem.save(buffer, format="PNG")
    buffer.seek(0)
    
    nome_arquivo = f"{carta_id}.png"
    return buffer, nome_arquivo