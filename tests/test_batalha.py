"""Testes do core/batalha.py. Com random.Random(42) os sorteios saem SEMPRE iguais."""

import random

from core import batalha

GOKU = {"name": "Goku", "ki": "60.000.000", "maxKi": "90 Septillion"}
FREEZER = {"name": "Freezer", "ki": "530.000", "maxKi": "52.71 Septillion"}
BULMA = {"name": "Bulma", "ki": "0", "maxKi": "0"}
CHI_CHI = {"name": "Chi-Chi", "ki": "0", "maxKi": "0"}


def test_luta_com_semente_42_sempre_igual():
    resultado = batalha.simular_luta(GOKU, FREEZER, random.Random(42))
    assert resultado["vencedor"] == "Freezer"
    assert resultado["rodadas"] == 15
    assert resultado["dano"] == {"Goku": 98, "Freezer": 105}
    assert resultado["narracao"][0] == "Freezer acerta Kamehameha: 9 de dano. [Goku: 91 HP]"


def test_mesma_semente_mesmo_resultado():
    primeira = batalha.simular_luta(GOKU, FREEZER, random.Random(7))
    segunda = batalha.simular_luta(GOKU, FREEZER, random.Random(7))
    assert primeira == segunda


def test_cem_lutas_com_ki_zero_sem_erro():
    for semente in range(100):
        resultado = batalha.simular_luta(BULMA, GOKU, random.Random(semente))
        assert resultado["vencedor"] in ("Bulma", "Goku")
        resultado = batalha.simular_luta(BULMA, CHI_CHI, random.Random(semente))   # 0 contra 0
        assert resultado["rodadas"] < batalha.LIMITE_DE_RODADAS


def test_esquiva_da_dano_zero():
    goku = batalha.criar_lutador(GOKU)
    freezer = batalha.criar_lutador(FREEZER)
    ataque = batalha.calcular_ataque(goku, freezer, random.Random(42))
    assert ataque["esquivou"] is True and ataque["dano"] == 0


def test_dano_fica_dentro_dos_limites():
    """Sem critico e sem item, o dano vai de 8 x 0.5 = 4 ate 14 x 2.5 = 35."""
    goku = batalha.criar_lutador(GOKU)
    bulma = batalha.criar_lutador(BULMA)
    sorteador = random.Random(1)
    for _ in range(500):
        ataque = batalha.calcular_ataque(goku, bulma, sorteador)
        if not ataque["critico"] and not ataque["esquivou"]:
            assert 20 <= ataque["dano"] <= 35          # Goku x Bulma: razao presa em 2.5
        ataque = batalha.calcular_ataque(bulma, goku, sorteador)
        if not (ataque["critico"] or ataque["esquivou"] or ataque["item"]):
            assert 4 <= ataque["dano"] <= 7            # Bulma x Goku: razao presa em 0.5


def test_transformacao_aumenta_a_forca_por_3_rodadas():
    goku = batalha.criar_lutador(dict(GOKU, transformations=[{"name": "Goku SSJ"}]))
    assert batalha.pode_transformar(goku)
    batalha.transformar(goku)
    assert batalha.forca_atual(goku) == goku["forca"] * 1.5
    assert not batalha.pode_transformar(goku)       # so uma vez por luta
    luta = {"a": goku, "b": batalha.criar_lutador(FREEZER), "rodadas": 0}
    luta["atacante"], luta["defensor"] = luta["a"], luta["b"]
    for _ in range(3):
        batalha.jogar_rodada(luta, random.Random(3))
    assert batalha.forca_atual(goku) == goku["forca"]


def test_hall_da_fama():
    historico = [{"vencedor": "Goku"}, {"vencedor": "Freezer"}, {"vencedor": "Goku"}]
    assert batalha.contar_vitorias(historico) == [("Goku", 2), ("Freezer", 1)]
    assert batalha.contar_vitorias([]) == []
