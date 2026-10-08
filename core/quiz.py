"""Regras do jogo "Quem e esse personagem?" (sem janela: so logica)."""

import random

OPCOES_POR_RODADA = 4
PREMIO_INICIAL = 4               # acertar de primeira vale 4; cada erro ou dica tira 1
NIVEIS_DE_PIXEL = [8, 16, 32, None]   # None = imagem original (nitida)


def montar_rodadas(personagens, quantas, rng=random):
    """Sorteia 'quantas' respostas diferentes; cada uma com 4 alternativas embaralhadas."""
    respostas = rng.sample(personagens, quantas)        # sample: sorteia SEM repetir
    rodadas = []
    for resposta in respostas:
        outros = [p for p in personagens if p["id"] != resposta["id"]]
        opcoes = rng.sample(outros, OPCOES_POR_RODADA - 1) + [resposta]
        rng.shuffle(opcoes)                              # a resposta certa muda de lugar
        rodadas.append({"resposta": resposta, "opcoes": opcoes})
    return rodadas


def nivel_de_pixel(erros):
    """8 quadradinhos no comeco; cada erro deixa a imagem mais nitida."""
    return NIVEIS_DE_PIXEL[min(erros, len(NIVEIS_DE_PIXEL) - 1)]


def premio(erros, usou_dica):
    """Quantos pontos a rodada vale agora: 4 - erros - dica (nunca menos que 0)."""
    descontos = erros + (1 if usou_dica else 0)
    return max(0, PREMIO_INICIAL - descontos)


def e_recorde(recordes, quantas, pontos):
    """recordes = {"5": {"nome": "Ana", "pontos": 17}, ...} (uma chave por numero de rodadas)."""
    atual = recordes.get(str(quantas))
    return pontos > 0 and (atual is None or pontos > atual["pontos"])
