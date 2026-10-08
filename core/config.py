"""Preferencias do aluno guardadas entre uma execucao e outra (nome e ultimo servidor)."""

from core.armazenamento import PASTA_USUARIO, carregar_json, salvar_json

ARQUIVO = PASTA_USUARIO / "config.json"
PADRAO = {"nome": "", "servidor": "", "modo": "servidor"}


def carregar():
    dados = dict(PADRAO)
    dados.update(carregar_json(ARQUIVO, padrao={}))
    return dados


def salvar(**mudancas):
    dados = carregar()
    dados.update(mudancas)
    salvar_json(ARQUIVO, dados)
    return dados
