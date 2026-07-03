import random

# Configuração centralizada de todas as raridades do CartoonDex
CONFIG_RARIDADES = {
    "Comum": {
        "chance_spawn": 0.50,       # 50% de chance de aparecer
        "biscoitos_min": 10,
        "biscoitos_max": 15
    },
    "Incomum": {
        "chance_spawn": 0.25,      # 25% de chance de aparecer
        "biscoitos_min": 20,
        "biscoitos_max": 30
    },
    "Raro": {
        "chance_spawn": 0.15,      # 15% de chance de aparecer
        "biscoitos_min": 40,
        "biscoitos_max": 60
    },
    "Épico": {
        "chance_spawn": 0.075,     # 7,5% de chance de aparecer
        "biscoitos_min": 80,
        "biscoitos_max": 120
    },
    "Lendário": {
        "chance_spawn": 0.025,     # 2,5% de chance de aparecer
        "biscoitos_min": 150,
        "biscoitos_max": 220
    },
    "Especial": {
        "chance_spawn": 0.0,       # 0% (Ativado apenas em eventos manuais)
        "biscoitos_min": 250,
        "biscoitos_max": 350
    },
    "Secreto": {
        "chance_spawn": 0.0,       # 0% (Desativado no momento)
        "biscoitos_min": 500,
        "biscoitos_max": 700
    }
}

def calcular_biscoitos_ganhos(raridade: str) -> int:
    """
    Sorteia a quantidade de Biscoitos Gatinho com base na raridade fornecida.
    """
    dados = CONFIG_RARIDADES.get(raridade, CONFIG_RARIDADES["Comum"])
    return random.randint(dados["biscoitos_min"], dados["biscoitos_max"])