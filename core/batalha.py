"""
Regras da batalha. Sem print, sem input, sem janela: so a logica (por isso da para testar).

Todas as funcoes recebem 'rng', o "sorteador". O padrao e o proprio modulo random;
nos testes usamos random.Random(42): com a mesma semente, os sorteios saem sempre iguais.
"""

import random

from core.poder import forca_de_batalha, parse_ki

HP_INICIAL = 100
CHANCE_ESQUIVA = 0.08            # 8%
CHANCE_CRITICO = 0.10            # 10%
CHANCE_ITEM = 0.05               # 5% (so para quem tem ki 0, como a Bulma)
MULTIPLICADOR_CRITICO = 1.8
BONUS_TRANSFORMACAO = 1.5
RODADAS_TRANSFORMADO = 3
RAZAO_MINIMA = 0.5
RAZAO_MAXIMA = 2.5
LIMITE_DE_RODADAS = 200          # seguranca: nenhuma luta dura para sempre

GOLPES = ["Kamehameha", "Soco do Dragao", "Rajada de Ki", "Ataque Relampago",
          "Teletransporte", "Chute Giratorio", "Final Flash", "Masenko"]


def criar_lutador(personagem, metrica="maxKi"):
    """Transforma um personagem da API num lutador (dicionario com HP, forca...)."""
    ki = parse_ki(personagem[metrica])
    return {
        "nome": personagem["name"],
        "ki": ki,
        "forca": forca_de_batalha(ki),
        "hp": HP_INICIAL,
        "dano_total": 0,
        "transformacoes": personagem.get("transformations", []),
        "ja_transformou": False,
        "rodadas_transformado": 0,
    }


def forca_atual(lutador):
    """A forca, com o bonus de 1.5x se o lutador estiver transformado."""
    if lutador["rodadas_transformado"] > 0:
        return lutador["forca"] * BONUS_TRANSFORMACAO
    return lutador["forca"]


def calcular_ataque(atacante, defensor, rng=random):
    """Sorteia UM ataque. Nao muda ninguem: so devolve o que aconteceu."""
    golpe = rng.choice(GOLPES)
    if rng.random() < CHANCE_ESQUIVA:
        return {"golpe": golpe, "dano": 0, "critico": False, "esquivou": True, "item": False}
    razao = forca_atual(atacante) / forca_atual(defensor)
    razao = min(RAZAO_MAXIMA, max(RAZAO_MINIMA, razao))     # prende a razao entre 0.5 e 2.5
    dano = round(rng.randint(8, 14) * razao)
    critico = rng.random() < CHANCE_CRITICO
    if critico:
        dano = round(dano * MULTIPLICADOR_CRITICO)
    item = atacante["ki"] == 0 and rng.random() < CHANCE_ITEM
    if item:
        dano += 20
    return {"golpe": golpe, "dano": dano, "critico": critico, "esquivou": False, "item": item}


def narrar(atacante, defensor, ataque):
    """Uma frase contando o que aconteceu (sem acentos: tambem aparece no terminal)."""
    nome, alvo = atacante["nome"], defensor["nome"]
    if ataque["esquivou"]:
        frase = f"{nome} usa {ataque['golpe']}... mas {alvo} desviou!"
    elif ataque["item"]:
        frase = f"{nome} lanca uma bomba da Corporacao Capsula! {ataque['dano']} de dano!"
    elif ataque["critico"]:
        frase = f"{nome} acerta {ataque['golpe']} CRITICO! {ataque['dano']} de dano!"
    else:
        frase = f"{nome} acerta {ataque['golpe']}: {ataque['dano']} de dano."
    return f"{frase} [{alvo}: {defensor['hp']} HP]"


def aplicar_ataque(atacante, defensor, ataque):
    """Agora sim: tira HP do defensor e soma o dano do atacante."""
    defensor["hp"] = max(0, defensor["hp"] - ataque["dano"])
    atacante["dano_total"] += ataque["dano"]


def pode_transformar(lutador):
    return bool(lutador["transformacoes"]) and not lutador["ja_transformou"]


def transformar(lutador):
    """Usa a transformacao mais forte (a ultima da lista). Devolve a transformacao usada."""
    lutador["ja_transformou"] = True
    lutador["rodadas_transformado"] = RODADAS_TRANSFORMADO
    return lutador["transformacoes"][-1]


# ----------------------------------------------------------------------
# A luta, passo a passo (a janela usa estes passos, uma rodada por vez)
# ----------------------------------------------------------------------

def iniciar_luta(personagem_a, personagem_b, metrica="maxKi", rng=random):
    """Cria os dois lutadores e sorteia quem comeca."""
    a = criar_lutador(personagem_a, metrica)
    b = criar_lutador(personagem_b, metrica)
    if rng.random() < 0.5:
        atacante, defensor = a, b
    else:
        atacante, defensor = b, a
    return {"a": a, "b": b, "atacante": atacante, "defensor": defensor, "rodadas": 0}


def jogar_rodada(luta, rng=random):
    """Uma rodada: o atacante bate e a vez passa para o outro. Devolve a narracao."""
    atacante, defensor = luta["atacante"], luta["defensor"]
    ataque = calcular_ataque(atacante, defensor, rng)
    aplicar_ataque(atacante, defensor, ataque)
    luta["rodadas"] += 1
    for lutador in (atacante, defensor):
        if lutador["rodadas_transformado"] > 0:
            lutador["rodadas_transformado"] -= 1
    luta["atacante"], luta["defensor"] = defensor, atacante     # troca a vez
    return narrar(atacante, defensor, ataque)


def luta_acabou(luta):
    return luta["a"]["hp"] <= 0 or luta["b"]["hp"] <= 0 or luta["rodadas"] >= LIMITE_DE_RODADAS


def resultado(luta):
    """Quem ganhou, em quantas rodadas e quanto dano cada um causou."""
    a, b = luta["a"], luta["b"]
    if a["hp"] >= b["hp"]:
        vencedor, perdedor = a, b
    else:
        vencedor, perdedor = b, a
    return {"vencedor": vencedor["nome"], "perdedor": perdedor["nome"], "rodadas": luta["rodadas"],
            "dano": {a["nome"]: a["dano_total"], b["nome"]: b["dano_total"]}}


def contar_vitorias(historico):
    """Hall da Fama: [(nome, vitorias), ...] do que mais venceu para o que menos venceu."""
    vitorias = {}
    for luta in historico:
        nome = luta["vencedor"]
        vitorias[nome] = vitorias.get(nome, 0) + 1
    return sorted(vitorias.items(), key=lambda par: par[1], reverse=True)


def simular_luta(personagem_a, personagem_b, rng=random, metrica="maxKi"):
    """A luta inteira de uma vez (usada nos testes e na batalha do terminal)."""
    luta = iniciar_luta(personagem_a, personagem_b, metrica, rng)
    narracao = []
    while not luta_acabou(luta):
        narracao.append(jogar_rodada(luta, rng))
    final = resultado(luta)
    final["narracao"] = narracao
    return final
