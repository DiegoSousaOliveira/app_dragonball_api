"""Testes do core/quiz.py."""

import random

from core import quiz

PERSONAGENS = [{"id": numero, "name": f"P{numero}"} for numero in range(1, 11)]


def test_rodadas_sem_resposta_repetida():
    rodadas = quiz.montar_rodadas(PERSONAGENS, 5, random.Random(42))
    respostas = [r["resposta"]["id"] for r in rodadas]
    assert len(set(respostas)) == 5
    for rodada in rodadas:
        ids = [p["id"] for p in rodada["opcoes"]]
        assert len(set(ids)) == 4 and rodada["resposta"]["id"] in ids


def test_nivel_de_pixel():
    assert [quiz.nivel_de_pixel(erros) for erros in range(5)] == [8, 16, 32, None, None]


def test_premio():
    assert quiz.premio(0, False) == 4
    assert quiz.premio(1, True) == 2
    assert quiz.premio(3, True) == 0


def test_recorde():
    recordes = {"5": {"nome": "Ana", "pontos": 12}}
    assert quiz.e_recorde(recordes, 5, 13)
    assert not quiz.e_recorde(recordes, 5, 12)
    assert quiz.e_recorde(recordes, 3, 1)       # ainda nao ha recorde para 3 rodadas
    assert not quiz.e_recorde({}, 3, 0)
