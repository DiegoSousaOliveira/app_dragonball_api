"""Testes das partes do core/api.py que nao precisam de internet."""

from core.api import buscar_personagem, extrair_itens, limpar_nomes, normalizar, sugerir_personagem

PERSONAGENS = [{"name": nome} for nome in ["Goku", "Gohan", "Gotenks", "Gogeta", "Celula", "Vegeta", "Vegetto"]]


def nomes(lista):
    return [personagem["name"] for personagem in lista]


def test_normalizar():
    assert normalizar("  Célula ") == "celula"
    assert normalizar("GOKU") == "goku"


def test_buscar_exato_ganha_do_parcial():
    assert nomes(buscar_personagem("vegeta", PERSONAGENS)) == ["Vegeta"]
    assert nomes(buscar_personagem("GOKU", PERSONAGENS)) == ["Goku"]


def test_buscar_parcial_e_acentos():
    assert nomes(buscar_personagem("go", PERSONAGENS)) == ["Goku", "Gohan", "Gotenks", "Gogeta"]
    assert nomes(buscar_personagem("Célula", PERSONAGENS)) == ["Celula"]
    assert buscar_personagem("Gokuu", PERSONAGENS) == []


def test_sugerir():
    assert sugerir_personagem("Gokuu", PERSONAGENS)["name"] == "Goku"
    assert sugerir_personagem("xyz", PERSONAGENS) is None


def test_extrair_itens_com_envelope():
    resposta = {"items": [{"id": 1}], "meta": {}, "links": {}}
    assert extrair_itens(resposta) == [{"id": 1}]


def test_extrair_itens_lista_pura():
    assert extrair_itens([{"id": 1}, {"id": 2}]) == [{"id": 1}, {"id": 2}]


def test_limpar_nomes():
    itens = limpar_nomes([{"name": "Grand Priest "}, {"name": "Goku"}])
    assert [item["name"] for item in itens] == ["Grand Priest", "Goku"]
