import os
import unicodedata

GITHUB_BASE = os.getenv("GITHUB_BASE", "")


def normalizar(texto: str) -> str:
    """Remove acentos, caracteres especiais e converte texto para minúsculas."""
    if not texto:
        return ""
    return unicodedata.normalize("NFKD", texto).encode("ASCII", "ignore").decode().lower()


def limpar_dex(dex) -> str:
    """Formata o número da Dex removendo '#' e garantindo 4 dígitos no padrão 0001."""
    box_dex = str(dex).replace("#", "")
    return box_dex.zfill(4)


def url_carta(carta: dict, github_base: str = None) -> str:
    """Gera a URL pública da imagem da carta hospedada no GitHub."""
    base = github_base or GITHUB_BASE
    dex = limpar_dex(carta.get("numero_dex", "0000"))
    skin = carta.get("skin_id", 0)
    return f"{base}/assets/cartas/{dex}/{dex}-{skin}-carta.png"


def url_moldura(moldura_id: int, github_base: str = None) -> str:
    """Gera a URL pública da moldura hospedada no GitHub."""
    base = github_base or GITHUB_BASE
    return f"{base}/assets/molduras/{moldura_id}.png"


def formatar_lista_cartas(lista_ids, cartas_dict, pagina, tipo_comando, itens_por_pagina=10):
    """Gera a listagem formatada de cartas para ser exibida nos Embeds de Dex e Inventário."""
    inicio = (pagina - 1) * itens_por_pagina
    fim = inicio + itens_por_pagina
    ids_pagina = lista_ids[inicio:fim]

    linhas = []
    for dex in ids_pagina:
        data = cartas_dict[dex]
        total = data["total_usuario"]

        # Garante que o número da dex tenha apenas um '#' no começo
        dex_limpa = str(dex).replace("#", "")
        tag_dex = f"#{dex_limpa}"

        # Se o usuário não tem a carta
        if total == 0:
            if tipo_comando == "dex":
                linhas.append(f"`{tag_dex}` - ????")
            continue

        # Se o usuário tem a carta (válido para inventário e dex)
        linhas.append(f"`{tag_dex}` - **{data['nome']}** ({total})")

        # Gerencia as skins
        skins = data["skins_capturadas"]
        for skin_id in sorted(skins.keys()):
            skin_nome, qtd = skins[skin_id]
            
            if skin_nome in ("Padrão", None) and len(skins) == 1:
                continue
            
            linhas.append(f"> *{skin_nome}* ({qtd})")

    return "\n".join(linhas).strip()