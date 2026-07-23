import discord

import discord

def embed_inventario_cartas(fatia_cartas, pagina_atual, total_paginas, total_cartas, ordenacao, inicio_fria, direcao, bot):
    """Gera o embed adaptando os índices decrescentes ou crescentes no modo Recentes."""
    from inventario import numero_para_codigo_aleatorio

    lista_texto = ""

    if ordenacao == "recentes":
        x = inicio_fria
        y = min(pagina_atual * 10, total_cartas)
        texto_paginacao = f"Exibindo cartas {x}–{y} de {total_cartas}."

        for i, row in enumerate(fatia_cartas):
            # CÁLCULO DO ID PESSOAL INVERTIDO:
            if direcao == "DESC":
                # Mais novas no topo: a primeira da lista (index 0 da página 1) recebe o número total absoluto
                id_pessoal = total_cartas - (inicio_fria - 1) - i
            else:
                # Mais antigas no topo: a numeração cresce tradicionalmente (1, 2, 3...)
                id_pessoal = inicio_fria + i
                
            id_global_hash = numero_para_codigo_aleatorio(row["id"])
            
            carta_id_chave = f"{row['numero_dex']}-{row['skin_id']}"
            dados_static = bot.dex.get(carta_id_chave)
            
            if dados_static:
                nome_carta = dados_static.get("skin_nome") if dados_static.get("skin_nome") else dados_static["nome"]
            else:
                nome_carta = f"Carta Desconhecida ({row['numero_dex']})"
                
            moldura_txt = f" [{row['moldura_id']}]" if row["moldura_id"] else ""
            lista_texto += f"`[{id_pessoal}]` **{nome_carta}** Lvl {row['nivel']}{moldura_txt} `#{id_global_hash}`\n"

    else:
        # COMPORTAMENTO DEX (Agrupado)
        cartas_na_pagina = sum(row["quantidade"] for row in fatia_cartas)
        x = inicio_fria
        y = x + cartas_na_pagina - 1
        texto_paginacao = f"Exibindo cartas {x}–{y} de {total_cartas}."

        for row in fatia_cartas:
            carta_id_chave = f"{row['numero_dex']}-{row['skin_id']}"
            dados_static = bot.dex.get(carta_id_chave)
            
            if dados_static:
                nome_carta = dados_static.get("skin_nome") if dados_static.get("skin_nome") else dados_static["nome"]
            else:
                nome_carta = f"Carta Desconhecida ({row['numero_dex']})"
                
            moldura_txt = f" [{row['moldura_id']}]" if row["moldura_id"] else ""
            lista_texto += f"`{row['numero_dex']}` **{nome_carta}** Lvl {row['nivel']}{moldura_txt} — **x{row['quantidade']}**\n"

    if total_cartas == 0:
        texto_paginacao = " "

    corpo_embed = (
        f"{texto_paginacao}\n\n"
        f"{lista_texto}\n"
        f"Use **/info (nome/dex)** para ver informações da carta."
    )

    embed = discord.Embed(
        title=f"🃏 Suas Cartas — Página {pagina_atual}/{total_paginas}",
        description=corpo_embed,
        color=discord.Color.from_rgb(255, 255, 255)
    )
    embed.set_footer(text=f"CartoonDex • Ordenado por {ordenacao.upper()} ({direcao})")
    return embed

def embed_inventario_molduras(linhas_molduras, pagina_atual, total_paginas, total_molduras, filtro_atual):
    """Gera o embed do comando /inventario molduras exibindo dados e o tipo de filtro ativo."""
    x = (pagina_atual - 1) * 10 + 1
    y = min(pagina_atual * 10, total_molduras)
    
    if total_molduras == 0:
        x, y = 0, 0

    traducao_filtro = {
        "recentes": "⏱️ Ordem de Compra (Mais recentes primeiro)",
        "raridade": "✨ Raridade (Maior relevância para cima)",
        "alfabetica": "🔤 Ordem Alfabética (A-Z)"
    }
    modo_texto = traducao_filtro.get(filtro_atual, "Filtro Ativo")

    texto_paginacao = f"Exibindo molduras {x}–{y} de {total_molduras}.\n*Filtro: {modo_texto}*"

    lista_texto = ""
    if not linhas_molduras:
        lista_texto = "*Você não possui nenhuma moldura.*\n"
    else:
        for m in linhas_molduras:
            # Mostra o nome limpo extraído da tabela loja_molduras e a raridade correspondente
            lista_texto += f"• **{m['nome']}** (`{m['moldura_id']}`) — [{m['raridade']}] x{m['quantidade']}\n"

    corpo_embed = (
        f"{texto_paginacao}\n\n"
        f"{lista_texto}\n"
        f"Use **/equipar** para aplicar uma moldura cosmética."
    )

    embed = discord.Embed(
        title=f"🖼️ Suas Molduras — Página {pagina_atual}/{total_paginas}",
        description=corpo_embed,
        color=discord.Color.from_rgb(255, 255, 255)
    )
    embed.set_footer(text="CartoonDex • Inventário de Molduras")
    return embed

def embed_inventario_itens(linhas_itens):
    """Gera o embed do comando /inventario itens em página única seguindo o modelo original."""
    total_itens = len(linhas_itens)
    
    # Como itens ficam em página única, exibe de 1 até o total acumulado diretamente
    x = 1 if total_itens > 0 else 0
    y = total_itens

    texto_paginacao = f"Exibindo itens {x}–{y} de {total_itens}."

    lista_texto = ""
    if not linhas_itens:
        lista_texto = "*Seu inventário de itens está vazio.*\n"
    else:
        for i in linhas_itens:
            lista_texto += f"• **{i['item_id']}** — Quantidade: x{i['quantidade']}\n"

    corpo_embed = (
        f"{texto_paginacao}\n\n"
        f"{lista_texto}\n"
        f"Use seus consumíveis e pacotes diretamente pelo chat."
    )

    embed = discord.Embed(
        title="🎒 Seus Itens — Página 1/1",
        description=corpo_embed,
        color=discord.Color.from_rgb(255, 255, 255)
    )
    embed.set_footer(text="CartoonDex • Inventário de Itens")
    return embed