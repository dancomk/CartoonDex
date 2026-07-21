import discord

def embed_spawn(nome, raridade):
    """Gera o embed visual quando um personagem surge no chat sem revelar a raridade."""
    embed = discord.Embed(
        title="✨ UM NOVO PERSONAGEM APARECEU! ✨",
        description="Quem é esse personagem?\nUse `/capturar [nome]` para tentar capturar!",
        color=discord.Color.from_rgb(255, 255, 255)
    )
    return embed


def embed_sem_carta_ativa():
    """Gera o embed de aviso quando tentam capturar sem nenhuma carta ativa no canal."""
    embed = discord.Embed(
        title="⚠️ Nenhuma carta ativa",
        description="Não há nenhum personagem disponível para captura neste canal no momento.",
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
        title="🎉 CAPTURADO com sucesso! 🎉",
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
        f"Use **/info (nome/dex)** para ver informações da carta."
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
        f"Use **/info (nome/dex)** para ver informações da carta."
    )

    embed = discord.Embed(
        title=f"📱 Sua Dex — Página {pagina_atual}/{total_paginas}",
        description=corpo_embed,
        color=discord.Color.from_rgb(255, 255, 255)
    )
    embed.set_footer(text="CartoonDex • Dex")
    return embed


def embed_info_carta(carta_nome, numero_dex, raridade, origem, colecao, hp, skins_do_personagem, skins_usuario, carta_base, url_carta_func=None):
    """Gera a visualização geral da Dex de um personagem específico."""
    embed = discord.Embed(
        title=f"🃏 #{numero_dex} — {carta_nome}",
        color=discord.Color.from_rgb(255, 255, 255)
    )
    
    txt_info = (
        f"• **Origem:** {origem}\n"
        f"• **Coleção:** {colecao}\n"
        f"• **Raridade:** {raridade}\n"
        f"• **HP:** {hp} HP"
    )
    embed.add_field(name="📊 Informações Gerais", value=txt_info, inline=False)

    txt_skins = ""
    for sk_id, sk_nome in skins_do_personagem.items():
        total_posse = skins_usuario.get(sk_id, 0)
        txt_skins += f"• `ID {sk_id}` {sk_nome} — (Possui: **x{total_posse}**)\n"
    
    embed.add_field(name="🖼️ Skins Disponíveis", value=txt_skins, inline=False)

    if carta_base.get("ataque_1_nome"):
        embed.add_field(
            name=f"⚔️ {carta_base['ataque_1_nome']} ({carta_base['ataque_1_dano']} Dano)",
            value=f"*{carta_base['ataque_1_descricao'] or 'Sem descrição.'}*",
            inline=True
        )
    if carta_base.get("ataque_2_nome"):
        embed.add_field(
            name=f"💥 {carta_base['ataque_2_nome']} ({carta_base['ataque_2_dano']} Dano)",
            value=f"*{carta_base['ataque_2_descricao'] or 'Sem descrição.'}*",
            inline=True
        )

    embed.set_footer(text="CartoonDex • Informações Gerais da Dex")
    return embed


def embed_info_instancia(instancia, id_pessoal, id_global):
    """Gera a visualização de uma instância de carta específica exibindo o formato combinado."""
    nome_exibicao = instancia["skin_nome"] if instancia["skin_nome"] else instancia["nome"]
    
    embed = discord.Embed(
        title=f"🛡️ {nome_exibicao}",
        description=f"Exibindo dados da carta física {id_pessoal} - #{id_global}",
        color=discord.Color.from_rgb(46, 204, 113)
    )

    moldura_txt = f"`{instancia['moldura_id']}`" if instancia["moldura_id"] else "*Nenhuma*"
    
    data_global = instancia.get("data_global")
    data_formatada = data_global.strftime("%d/%m/%Y às %H:%M") if data_global else "*Desconhecida*"

    txt_status = (
        f"• **Número da Dex:** `{instancia['numero_dex']}`\n"
        f"• **Skin Código:** `{instancia['skin_id']}`\n"
        f"• **Nível Atual:** Lvl {instancia['nivel']}\n"
        f"• **Moldura Equipada:** {moldura_txt}\n"
        f"• **Colocada em circulação em:** {data_formatada}\n"
        f"• **Mestre Atual:** <@{instancia['membro_id']}>"
    )
    embed.add_field(name="📋 Status da Carta", value=txt_status, inline=False)

    txt_batalha = (
        f"• **HP:** {instancia['hp']} HP\n"
        f"• **Ataque Principal:** {instancia['ataque_1_nome'] or '*Não possui*'}\n"
        f"• **Ataque Secundário:** {instancia['ataque_2_nome'] or '*Não possui*'}"
    )
    embed.add_field(name="⚔️ Atributos Base", value=txt_batalha, inline=False)
    
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