# utils.py

def formatar_lista_cartas(lista_ids, cartas_dict, pagina, tipo_comando, itens_por_pagina=10):
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