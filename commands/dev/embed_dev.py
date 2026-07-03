import discord

def embed_spawn_dev(nome: str, raridade: str):
    """Gera o embed de visualização para o comando de spawn manual do desenvolvedor."""
    embed = discord.Embed(
        title="✨ [DEV] Personagem Spawnado Manualmente",
        description=f"Um novo personagem apareceu no canal!\n\n**Personagem:** {nome}\n**Raridade:** {raridade}",
        color=discord.Color.purple()
    )
    embed.set_footer(text="CartoonDex • Ferramentas de Desenvolvedor")
    return embed