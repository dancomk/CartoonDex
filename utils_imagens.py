import os

def formatar_dex(dex):
    return str(dex).zfill(4)

def caminho_spawn(dex, skin_id):
    dex = formatar_dex(dex)
    skin_id = skin_id or 0
    caminho = f"assets/spawn/{dex}/{dex}-{skin_id}-spawn.png"

    if not os.path.exists(caminho):
        caminho = f"assets/spawn/{dex}/{dex}-0-spawn.png"

    return caminho

def caminho_carta(dex, skin_id):
    dex = formatar_dex(dex)
    skin_id = skin_id or 0
    caminho = f"assets/cartas/{dex}/{dex}-{skin_id}-carta.png"

    if not os.path.exists(caminho):
        caminho = f"assets/cartas/{dex}/{dex}-0-carta.png"

    return caminho