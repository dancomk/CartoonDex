import discord

def embed_sucesso_monitoramento(canal_mention: str, adicionado: bool):
    """Gera uma resposta com a ação em negrito para a lista de monitoramento."""
    acao = "**adicionado à**" if adicionado else "**removido da**"
    return f"✅ Canal {canal_mention} foi {acao} lista de monitoramento."

def embed_sucesso_spawn(canal_mention: str):
    """Gera uma resposta com 'Canal de spawn' em negrito para a alteração de spawn principal."""
    return f"✅ **Canal de spawn** configurado com sucesso para: {canal_mention}"

def embed_config_info(canal_spawn_id: int, lista_monitoramento_ids: list):
    """Gera o layout visual das configurações atuais do servidor."""
    embed = discord.Embed(
        title="⚙️ Configurações Atuais do CartoonDex",
        color=discord.Color.blue()
    )

    # 1. Tratamento do Canal de Spawn
    if canal_spawn_id:
        texto_spawn = f"<#{canal_spawn_id}>"
    else:
        texto_spawn = "*Não definido* (O spawn ocorrerá no canal da última mensagem)"

    # 2. Tratamento dos Canais de Monitoramento
    if lista_monitoramento_ids:
        texto_monitoramento = ", ".join([f"<#{cid}>" for cid in lista_monitoramento_ids])
    else:
        texto_monitoramento = "*Não definido* (O bot está monitorando todos os canais do servidor)"

    embed.add_field(name="📢 Canal de Spawn Oficial", value=texto_spawn, inline=False)
    embed.add_field(name="💬 Canais Monitorados", value=texto_monitoramento, inline=False)
    
    return embed