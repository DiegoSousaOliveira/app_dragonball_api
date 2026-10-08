"""Testes do core/filtros.py com uma lista pequena (sem internet)."""

from core.filtros import filtrar, montar_ranking, ordenar, valores_unicos

PERSONAGENS = [
    {"name": "Goku", "race": "Saiyan", "affiliation": "Z Fighter", "gender": "Male",
     "ki": "60.000.000", "maxKi": "90 Septillion"},
    {"name": "Bulma", "race": "Human", "affiliation": "Z Fighter", "gender": "Female",
     "ki": "0", "maxKi": "0"},
    {"name": "Vegeta", "race": "Saiyan", "affiliation": "Z Fighter", "gender": "Male",
     "ki": "54.000.000", "maxKi": "19.84 Septillion"},
    {"name": "Freezer", "race": "Frieza Race", "affiliation": "Army of Frieza", "gender": "Male",
     "ki": "530.000", "maxKi": "52.71 Septillion"},
]


def nomes(lista):
    return [p["name"] for p in lista]


def test_valores_unicos():
    assert valores_unicos(PERSONAGENS, "race") == ["Frieza Race", "Human", "Saiyan"]


def test_filtrar_combinado():
    assert nomes(filtrar(PERSONAGENS, raca="Saiyan")) == ["Goku", "Vegeta"]
    assert nomes(filtrar(PERSONAGENS, nome="E", genero="Male")) == ["Vegeta", "Freezer"]
    assert nomes(filtrar(PERSONAGENS)) == ["Goku", "Bulma", "Vegeta", "Freezer"]


def test_ordenar():
    assert nomes(ordenar(PERSONAGENS, "nome")) == ["Bulma", "Freezer", "Goku", "Vegeta"]
    assert nomes(ordenar(PERSONAGENS, "ki")) == ["Goku", "Vegeta", "Freezer", "Bulma"]
    assert nomes(ordenar(PERSONAGENS, "maxKi")) == ["Goku", "Freezer", "Vegeta", "Bulma"]


def test_ranking_ignora_ki_zero():
    ranking, ignorados = montar_ranking(PERSONAGENS, "maxKi", quantos=2)
    assert [(p["name"], ki) for p, ki in ranking] == [("Goku", 90 * 10**24), ("Freezer", 5271 * 10**22)]
    assert ignorados == 1                      # a Bulma (ki 0)
    ranking, ignorados = montar_ranking(PERSONAGENS, "ki", raca="Saiyan")
    assert nomes([p for p, ki in ranking]) == ["Goku", "Vegeta"]
