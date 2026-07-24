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
    texto_moeda = f"{biscoitos_ganhos} Biscoito Gatinho" if biscoitos_ganhos <= 1 else f"{biscoitos_ganhos} Biscoitos Gatinho"
    
    frase_dex = " Carta adicionada na Dex." if quantidade == 1 else ""

    embed = discord.Embed(
        title="🎉 CARTA COLETADA com sucesso! 🎉",
        description=f"Você capturou **{nome}**!{frase_dex} Você ganhou **{texto_moeda}**!",
        color=discord.Color.from_rgb(255, 255, 255)
    )
    return embed


def embed_inventario(descricao_lista, pagina_atual, total_paginas, total_cartas):
    """Gera o embed do comando /inventario com o volume total real acumulado."""
    x = (pagina_atual - 1) * 10 + 1
    y = min(pagina_atual * 10, total_cartas)
    
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
        f"Use **/info** para ver informações da carta."
    )

    embed = discord.Embed(
        title=f"📱 Sua Dex — Página {pagina_atual}/{total_paginas}",
        description=corpo_embed,
        color=discord.Color.from_rgb(255, 255, 255)
    )
    embed.set_footer(text="CartoonDex • Dex")
    return embed


def embed_info_carta(carta: dict, skins_do_personagem: dict = None, skins_usuario: dict = None):
    """Gera o embed detalhado da carta mapeando diretamente as colunas da Dex."""
    if skins_do_personagem is None:
        skins_do_personagem = {}
    if skins_usuario is None:
        skins_usuario = {}

    nome_base = carta.get("nome", "Desconhecido")
    skin_nome = carta.get("skin_nome")
    skin_id = carta.get("skin_id", 0)

    exibir_nome = skin_nome if (skin_id != 0 and skin_nome) else nome_base
    raw_dex = carta.get("numero_dex", "0")
    dex_4digits = str(raw_dex).zfill(4) if isinstance(raw_dex, (int, str)) else "0000"
    carta_id = carta.get("carta_id") or f"{dex_4digits}-{skin_id}"

    embed = discord.Embed(
        title=f"🃏 `#{carta_id}` - {exibir_nome}",
        color=discord.Color.from_rgb(255, 255, 255)
    )
    
    embed.set_image(url="attachment://carta.png")

    raridade = carta.get("raridade", "Comum")
    origem = carta.get("origem", "Desconhecida")
    colecao = carta.get("colecao", "Base")
    
    embed.add_field(name="✨ Raridade", value=f"**{raridade}**", inline=True)
    embed.add_field(name="📺 Origem", value=f"**{origem}**", inline=True)
    embed.add_field(name="📚 Coleção", value=f"**{colecao}**", inline=True)
    
    artista = carta.get("artista")
    if artista:
        embed.add_field(name="🎨 Artista", value=f"**{artista}**", inline=True)
    
    descricao = carta.get("descricao")
    texto_descricao = descricao if (descricao and descricao.strip()) else "Não encontrada ou não adicionada."
    embed.add_field(name="📖 Descrição", value=texto_descricao, inline=False)
    
    if skins_do_personagem:
        texto_skins = ""
        for s_id, s_nome in skins_do_personagem.items():
            cod_skin = f"`{dex_4digits}-{s_id}`"
            nome_skin_exibicao = nome_base if str(s_id) == "0" or s_id == 0 else s_nome
            
            if s_id in skins_usuario or str(s_id) in skins_usuario:
                qtd = skins_usuario.get(s_id) or skins_usuario.get(str(s_id))
                texto_skins += f"{cod_skin} - ✅ **{nome_skin_exibicao}** *(Possui: {qtd}x)*\n"
            else:
                texto_skins += f"{cod_skin} - 🔒 *{nome_skin_exibicao}* *(Não coletada)*\n"
        
        embed.add_field(name="🖼️ Variações de Skins", value=texto_skins, inline=False)

    embed.set_footer(text="CartoonDex • Informações Gerais da Dex")
    return embed


def embed_info_instancia(instancia: dict, id_pessoal: int = None, id_global: str = "000000", usuario_solicitante_id: int = None):
    """Gera o embed de uma instância física de carta."""
    nome_base = instancia.get("nome", "Desconhecido")
    skin_nome = instancia.get("skin_nome")
    skin_id = instancia.get("skin_id", 0)

    exibir_nome = skin_nome if (skin_id != 0 and skin_nome) else nome_base

    raw_dex = instancia.get("numero_dex", "0")
    dex_4digits = str(raw_dex).zfill(4) if isinstance(raw_dex, (int, str)) else "0000"
    carta_id = instancia.get("carta_id") or f"{dex_4digits}-{skin_id}"

    dono_id = instancia.get("membro_id")
    eh_o_dono = (
        id_pessoal is not None 
        and usuario_solicitante_id is not None 
        and str(dono_id) == str(usuario_solicitante_id)
    )

    if eh_o_dono:
        txt_identificadores = f"Exibindo dados da carta `{id_pessoal}` - `#{id_global}`"
    else:
        txt_identificadores = f"Exibindo dados da carta `#{id_global}`"

    embed = discord.Embed(
        title=f"🃏 `#{carta_id}` - {exibir_nome}",
        description=txt_identificadores,
        color=discord.Color.from_rgb(255, 255, 255)
    )

    embed.set_image(url="attachment://carta.png")

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

    moldura_nome = instancia.get("moldura_nome") or instancia.get("moldura_id")
    moldura_txt = moldura_nome if moldura_nome else "Nenhuma"

    data_global = instancia.get("data_global")
    data_global_fmt = data_global.strftime("%d/%m/%Y às %H:%M") if data_global else "Desconhecida"

    txt_status = (
        f"**Nível Atual:** {instancia.get('nivel', 1)}\n"
        f"**Moldura Equipada:** {moldura_txt}\n"
        f"**Colocada em circulação em:** {data_global_fmt}\n"
    )

    if eh_o_dono:
        data_pessoal = instancia.get("data_pessoal")
        data_pessoal_fmt = data_pessoal.strftime("%d/%m/%Y às %H:%M") if data_pessoal else "Desconhecida"
        txt_status += f"**No inventário desde:** {data_pessoal_fmt}\n"

    txt_status += f"**Mestre Atual:** <@{dono_id}>"

    embed.add_field(name="📋 Status da Carta", value=txt_status, inline=False)

    embed.set_footer(text="CartoonDex • Visualização de Carta Física")
    return embed


def embed_perfil_provisorio(user_name, avatar_url, biscoitos, total_cartas, dex_desbloqueada, total_cartas_jogo):
    """Gera o embed provisório para o comando de perfil do jogador."""
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