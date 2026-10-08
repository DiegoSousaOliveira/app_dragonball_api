"""Testes do servidor do professor. Rodam sem internet (snapshot + imagens do cache embutido)
e so em 127.0.0.1 (o Firewall do Windows nem e consultado)."""

import tempfile
from pathlib import Path

import requests

from core import api, descoberta
from servidor.aplicacao import ServidorDragonBall

_servidor = None


def servidor():
    """Liga UM servidor de teste (na primeira vez que alguem pede) e devolve a URL base."""
    global _servidor
    if _servidor is None:
        api.modo_offline = True                    # o servidor usa so os dados salvos
        placar = Path(tempfile.mkdtemp()) / "placar.json"
        _servidor = ServidorDragonBall(porta=0, descoberta=False, arquivo_placar=placar, host="127.0.0.1")
        _servidor.iniciar()
    return f"http://127.0.0.1:{_servidor.porta}"


def get(caminho, **params):
    return requests.get(servidor() + caminho, params=params, timeout=5)


def test_ping():
    resposta = get("/turma/ping")
    assert resposta.status_code == 200
    assert resposta.json()["servico"] == "Dragon Ball Dex"


def test_lista_paginada_igual_a_api_original():
    dados = get("/api/characters").json()
    assert len(dados["items"]) == 10
    assert dados["meta"]["totalItems"] == 58 and dados["meta"]["totalPages"] == 6
    assert dados["links"]["previous"] == ""
    assert dados["links"]["next"].endswith("/api/characters?page=2&limit=10")
    assert len(get("/api/characters", limit=100).json()["items"]) == 58
    assert get("/api/characters", limit=1000).json()["meta"]["itemsPerPage"] == 100


def test_filtros_devolvem_lista_pura():
    saiyans = get("/api/characters", race="saiyan").json()
    assert isinstance(saiyans, list) and len(saiyans) == 10
    assert [p["name"] for p in get("/api/characters", name="go").json()] == ["Goku", "Gohan", "Gotenks", "Gogeta"]
    assert len(get("/api/planets", isDestroyed="true").json()) == 4


def test_detalhe_com_imagens_do_servidor():
    goku = get("/api/characters/1").json()
    base = servidor() + "/imagens/"
    assert goku["name"] == "Goku" and len(goku["transformations"]) == 6
    assert goku["image"].startswith(base)
    assert goku["originPlanet"]["image"].startswith(base)
    assert all(t["image"].startswith(base) for t in goku["transformations"])


def test_erros():
    assert get("/api/characters/99999").status_code == 404
    assert get("/api/characters/abc").status_code == 400
    assert get("/nao-existe").status_code == 404
    assert get("/imagens/../core/api.py").status_code == 404


def test_imagem():
    url = get("/api/characters/1").json()["image"]
    resposta = requests.get(url, timeout=5)
    assert resposta.status_code == 200
    assert resposta.headers["Content-Type"] == "image/webp"
    assert len(resposta.content) > 10_000


def test_placar_da_turma():
    base = servidor()
    cabecalho = {"X-Aluno": "Ana"}
    batalha = {"vencedor": "Goku", "perdedor": "Freezer", "rodadas": 15, "metrica": "maxKi"}
    assert requests.post(base + "/turma/batalha", json=batalha, headers=cabecalho, timeout=5).status_code == 201
    assert requests.post(base + "/turma/batalha", json={"vencedor": "Goku"}, timeout=5).status_code == 400
    quiz = requests.post(base + "/turma/quiz", json={"pontos": 9, "rodadas": 5}, headers=cabecalho, timeout=5)
    assert quiz.status_code == 201 and quiz.json()["recorde"] is True
    assert requests.post(base + "/turma/quiz", json={"pontos": 99, "rodadas": 5}, timeout=5).status_code == 400
    placar = requests.get(base + "/turma/placar", timeout=5).json()
    assert placar["hall_da_fama"][0] == {"nome": "Goku", "vitorias": 1}
    assert placar["recordes_quiz"][0]["aluno"] == "Ana"


def test_monitor_ve_os_alunos():
    requests.post(servidor() + "/turma/entrar", json={"nome": "Bia"}, timeout=5)
    alunos = _servidor.monitor.instantaneo()["alunos"]
    assert any(a["nome"] == "Bia" and a["online"] for a in alunos)


def test_descoberta_na_rede():
    respondedor = descoberta.RespondedorDeDescoberta(8123, "Teste", host="127.0.0.1")
    try:
        achados = descoberta.procurar_servidores(espera=1.0)
    finally:
        respondedor.parar()
    assert {"endereco": "127.0.0.1:8123", "nome": "Teste"} in achados


def test_transformacoes():
    lista = get("/api/transformations").json()
    assert len(lista) >= 40
    assert get(f"/api/transformations/{lista[0]['id']}").json()["name"] == lista[0]["name"]
    assert get("/api/transformations/999").status_code == 404
