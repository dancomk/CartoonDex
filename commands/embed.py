import discord

def embed_spawn(nome, raridade):
    """Gera o embed visual quando um personagem surge no chat sem revelar a raridade."""
    embed = discord.Embed(
        title="✨ UMA NOVA CARTA APARECEU! ✨",
        description="Que personagem pode ser? 👀\nUse `/capturar [nome]` para tentar capturar!",
        color=discord.Color.from_rgb(255, 255, 255)
    )
    return embed


def embed_sem_carta_ativa():
    """Gera o embed de aviso quando tentam capturar sem nenhuma carta ativa no canal."""
    embed = discord.Embed(
        title="⚠️ Nenhuma carta ativa",
        description="Não há nenhuma carta disponível para captura neste canal no momento.",
        color=discord.Color.from_rgb(255, 255, 255)
    )
    return embed


def embed_captura_detalhada(nome, raridade, dex, quantidade, biscoitos_ganhos, skin=None):
    """Gera o embed de sucesso após uma captura bem-sucedida."""
    # Formatação do plural composto para a frase
    texto_moeda = f"{biscoitos_ganhos} Biscoito Gatinho" if biscoitos_ganhos <= 1 else f"{biscoitos_ganhos} Biscoitos Gatinho"
    
    # Verifica se é a primeira vez que o usuário consegue essa variação
    if quantidade == 1:
        frase_dex = " Carta adicionada na Dex."
    else:
        frase_dex = ""

    embed = discord.Embed(
        title="🎉 CARTA COLETADA com sucesso! 🎉",
        description=f"Você capturou **{nome}**!{frase_dex} Você ganhou **{texto_moeda}**!",
        color=discord.Color.from_rgb(255, 255, 255)
    )
    return embed


def embed_inventario(descricao_lista, pagina_atual, total_paginas, total_cartas):
    """Gera o embed do comando /inventario com o volume total real acumulado."""
    x = (pagina_atual - 1) * 10 + 1
    
    # Se for a última página, ajustamos o ponteiro visual para bater exatamente com o total absoluto
    if pagina_atual == total_paginas:
        y = total_cartas
    else:
        y = pagina_atual * 10
    
    if total_cartas == 0:
        x, y = 0, 0

    texto_paginacao = f"Exibindo cartas {x}–{y} de {total_cartas}."

    corpo_embed = (
        f"{texto_paginacao}\n\n"
        f"{descricao_lista}\n\n"
        f"Use **/info** para ver informações da carta."
    )

    embed = discord.Embed(
        title=f"📦 Seu Inventário — Página {pagina_atual}/{total_paginas}",
        description=corpo_embed,
        color=discord.Color.from_rgb(255, 255, 255)
    )
    embed.set_footer(text="CartoonDex • Inventário")
    return embed


import discord

import discord

def embed_dex(descricao_lista, pagina_atual, total_paginas, total_cartas):
    """Gera o embed do comando /dex com base no índice de entradas únicas."""
    x = (pagina_atual - 1) * 10 + 1
    y = min(pagina_atual * 10, total_cartas)

    if total_cartas == 0:
        x, y = 0, 0

    texto_paginacao = f"Exibindo cartas {x}–{y} de {total_cartas}."

    corpo_embed = (
        f"{texto_paginacao}\n\n"
        f"{descricao_lista}\n\n"
        f"Use **/info ** para ver informações da carta."
    )

    embed = discord.Embed(
        title=f"📱 Sua Dex — Página {pagina_atual}/{total_paginas}",
        description=corpo_embed,
        color=discord.Color.from_rgb(255, 255, 255)
    )
    embed.set_footer(text="CartoonDex • Dex")
    return embed

def embed_info_carta(carta: dict, skins_do_personagem: dict = None, skins_usuario: dict = None):
    """
    Gera o embed detalhado da carta mapeando diretamente as colunas do banco de dados Neon.
    """
    if skins_do_personagem is None:
        skins_do_personagem = {}
    if skins_usuario is None:
        skins_usuario = {}

    # 1. Trata o nome e ID
    nome_base = carta.get("nome", "Desconhecido")
    skin_nome = carta.get("skin_nome")
    skin_id = carta.get("skin_id", 0)

    # Exibe apenas o nome da skin se for uma variante
    exibir_nome = skin_nome if (skin_id != 0 and skin_nome) else nome_base
    raw_dex = carta.get("numero_dex", "0")
    dex_4digits = str(raw_dex).zfill(4) if isinstance(raw_dex, (int, str)) else "0000"
    carta_id = carta.get("carta_id") or f"{dex_4digits}-{skin_id}"

    # Título no estilo: `#0001-0` - Nome
    embed = discord.Embed(
        title=f"🃏 `#{carta_id}` - {exibir_nome}",
        color=discord.Color.from_rgb(255, 255, 255)
    )
    
    # Imagem anexada via memória RAM
    embed.set_image(url="attachment://carta.png")

    # 2. Raridade, Origem e Coleção mapeados da tabela 'dex'
    raridade = carta.get("raridade", "Comum")
    origem = carta.get("origem", "Desconhecida")
    colecao = carta.get("colecao", "Base")
    
    embed.add_field(name="✨ Raridade", value=f"**{raridade}**", inline=True)
    embed.add_field(name="📺 Origem", value=f"**{origem}**", inline=True)
    embed.add_field(name="📚 Coleção", value=f"**{colecao}**", inline=True)
    
    # Artista (Se preenchido no banco)
    artista = carta.get("artista")
    if artista:
        embed.add_field(name="🎨 Artista", value=f"**{artista}**", inline=True)
    
    # 3. Descrição
    descricao = carta.get("descricao")
    texto_descricao = descricao if (descricao and descricao.strip()) else "Não encontrada ou não adicionada."
    embed.add_field(name="📖 Descrição", value=texto_descricao, inline=False)
    
    # 4. Variações de Skins com código Inline
    if skins_do_personagem:
        texto_skins = ""
        for s_id, s_nome in skins_do_personagem.items():
            cod_skin = f"`{dex_4digits}-{s_id}`"
            
            # Se for a skin 0 (base), exibe o nome base do personagem
            nome_skin_exibicao = nome_base if str(s_id) == "0" or s_id == 0 else s_nome
            if s_id in skins_usuario:
                qtd = skins_usuario[s_id]
                texto_skins += f"{cod_skin} - ✅ **{nome_skin_exibicao}** *(Possui: {qtd}x)*\n"
            else:
                texto_skins += f"{cod_skin} - 🔒 *{nome_skin_exibicao}* *(Não coletada)*\n"
        
        embed.add_field(name="🖼️ Variações de Skins", value=texto_skins, inline=False)

    # 5. Rodapé
    embed.set_footer(text="CartoonDex • Informações Gerais da Dex")
    return embed

def embed_info_instancia(instancia: dict, id_pessoal: int = None, id_global: str = "000000", usuario_solicitante_id: int = None):
    """
    Gera o embed de uma instância física de carta.
    """
    # 1. Trata o nome (substitui pelo nome da skin se for uma variante)
    nome_base = instancia.get("nome", "Desconhecido")
    skin_nome = instancia.get("skin_nome")
    skin_id = instancia.get("skin_id", 0)

    exibir_nome = skin_nome if (skin_id != 0 and skin_nome) else nome_base

    # 2. Formata o carta_id (ex: "0001-0")
    raw_dex = instancia.get("numero_dex", "0")
    dex_4digits = str(raw_dex).zfill(4) if isinstance(raw_dex, (int, str)) else "0000"
    carta_id = instancia.get("carta_id") or f"{dex_4digits}-{skin_id}"

    # 3. Verifica se quem está olhando é o dono da carta
    dono_id = instancia.get("membro_id")
    eh_o_dono = (
        id_pessoal is not None 
        and usuario_solicitante_id is not None 
        and int(dono_id) == int(usuario_solicitante_id)
    )

    # Formata a descrição dependendo de quem está olhando
    if eh_o_dono:
        txt_identificadores = f"Exibindo dados da carta `{id_pessoal}` - `#{id_global}`"
    else:
        txt_identificadores = f"Exibindo dados da carta `#{id_global}`"

    embed = discord.Embed(
        title=f"🃏 `#{carta_id}` - {exibir_nome}",
        description=txt_identificadores,
        color=discord.Color.from_rgb(46, 204, 113)
    )

    # Imagem anexada via memória RAM
    embed.set_image(url="attachment://carta.png")

    # 4. Detalhes da carta (Raridade, Origem, Coleção, Artista e Descrição)
    raridade = instancia.get("raridade", "Comum")
    origem = instancia.get("origem", "Desconhecida")
    colecao = instancia.get("colecao", "Base")
    artista = instancia.get("artista")
    
    descricao = instancia.get("descricao")
    texto_descricao = descricao if (descricao and descricao.strip()) else "Não encontrada ou não adicionada."

    txt_detalhes = (
        f"✨ **Raridade:** {raridade}\n"
        f"📺 **Origem:** {origem}\n"
        f"📚 **Coleção:** {colecao}\n"
    )
    if artista:
        txt_detalhes += f"🎨 **Artista:** {artista}\n"
    
    txt_detalhes += f"📖 **Descrição:** {texto_descricao}"

    embed.add_field(name="", value=txt_detalhes, inline=False)

    # 5. Status da Carta
    moldura_nome = instancia.get("moldura_nome") or instancia.get("moldura_id")
    moldura_txt = moldura_nome if moldura_nome else "Nenhuma"

    data_global = instancia.get("data_global")
    data_global_fmt = data_global.strftime("%d/%m/%Y às %H:%M") if data_global else "Desconhecida"

    txt_status = (
        f"**Nível Atual:** {instancia.get('nivel', 1)}\n"
        f"**Moldura Equipada:** {moldura_txt}\n"
        f"**Colocada em circulação em:** {data_global_fmt}\n"
    )

    # Inclui "No inventário desde:" APENAS se for o dono da carta
    if eh_o_dono:
        data_pessoal = instancia.get("data_pessoal")
        data_pessoal_fmt = data_pessoal.strftime("%d/%m/%Y às %H:%M") if data_pessoal else "Desconhecida"
        txt_status += f"**No inventário desde:** {data_pessoal_fmt}\n"

    txt_status += f"**Mestre Atual:** <@{dono_id}>"

    embed.add_field(name="### 📋 Status da Carta", value=txt_status, inline=False)

    embed.set_footer(text="CartoonDex • Visualização de Carta Física")
    return embed

def embed_perfil_provisorio(user_name, avatar_url, biscoitos, total_cartas, dex_desbloqueada, total_cartas_jogo):
    texto_biscoitos = f"{biscoitos} Biscoito Gatinho" if biscoitos <= 1 else f"{biscoitos} Biscoitos Gatinho"
    
    embed = discord.Embed(
        title=f"📋 Perfil de Treinador - {user_name}",
        color=discord.Color.from_rgb(255, 255, 255)
    )
    embed.set_thumbnail(url=avatar_url)
    
    embed.add_field(
        name="💰 Economia", 
        value=f"**Saldo:** {texto_biscoitos}", 
        inline=False
    )
    embed.add_field(
        name="🎴 Coleção", 
        value=f"**Total de Cartas:** {total_cartas}\n**Progresso da Dex:** {dex_desbloqueada}/{total_cartas_jogo}", 
        inline=False
    )
    embed.set_footer(text="Em breve: Cartão de Perfil em Imagem! 🚀")
    return embed

def embed_info_carta(carta_nome, dex_formatado, raridade, descricao, skins_do_personagem, skins_usuario, carta_base, url_carta_func):
    """Gera o embed detalhado da carta com imagem centralizada e descrição tratada."""
    embed = discord.Embed(
        title=f"🃏 #{dex_formatado} - {carta_nome}",
        color=discord.Color.from_rgb(255, 255, 255)
    )
    
    # 1. Foto da Carta: Injetada logo abaixo do título principal
    embed.set_image(url=url_carta_func(dict(carta_base)))
    
    # 2. Informações: Raridade
    embed.add_field(name="✨ Raridade", value=f"**{raridade}**", inline=False)
    
    # 3. Informações: Descrição (Tratando se for NULL / None no banco de dados)
    texto_descricao = descricao if descricao and descricao.strip() else "Ainda não há descrição para esta carta."
    embed.add_field(name="📖 Descrição", value=texto_descricao, inline=False)
    
    # 4. Informações: Variações de Skins
    texto_skins = ""
    for s_id, s_nome in skins_do_personagem.items():
        if s_id in skins_usuario:
            qtd = skins_usuario[s_id]
            texto_skins += f"✅ **{s_nome}** *(Possui: {qtd}x)*\n"
        else:
            texto_skins += f"🔒 *{s_nome}* *(Não coletada)*\n"
            
    if not texto_skins:
        texto_skins = "*Nenhuma skin cadastrada*"

    embed.add_field(name="🎨 Variações de Skins", value=texto_skins, inline=False)
    
    return embed