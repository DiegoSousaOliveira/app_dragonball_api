"""Testes dos duelos entre alunos (desafios, batalha no servidor, quiz, W.O., classificacao)."""

import time

import requests

from servidor import sala as modulo_sala
from tests import test_servidor


def base():
    return test_servidor.servidor()


def sala_do_servidor():
    base()
    return test_servidor._servidor.sala


def entrar(nome):
    resposta = requests.post(base() + "/turma/entrar", json={"nome": nome}, timeout=5).json()
    return {"X-Jogador": resposta["id"], "X-Aluno": nome}


def get(caminho, quem):
    return requests.get(base() + caminho, headers=quem, timeout=5)


def post(caminho, quem, dados=None):
    return requests.post(base() + caminho, json=dados or {}, headers=quem, timeout=5)


def acelerar(id_partida):
    """Faz a batalha 'ja ter comecado ha muito tempo' (o servidor joga todas as rodadas)."""
    sala_do_servidor().partidas[id_partida].comeca = time.time() - 1000


def test_desafio_de_batalha_completo():
    ana, beto, carlos = entrar("Ana D"), entrar("Beto D"), entrar("Carlos D")
    visao = get("/turma/sala", ana).json()
    nomes = {j["nome"]: j["estado"] for j in visao["jogadores"]}
    assert nomes["Beto D"] == "livre" and visao["jogadores"][0]["voce"]
    id_beto = beto["X-Jogador"]
    assert post("/turma/desafiar", ana, {"para": id_beto, "tipo": "batalha", "personagem": 1}).status_code == 201
    recebidos = get("/turma/sala", beto).json()["recebidos"]
    assert len(recebidos) == 1 and recebidos[0]["de"]["nome"] == "Ana D"
    aceito = post("/turma/responder", beto, {"desafio": recebidos[0]["id"], "aceitar": True, "personagem": 5})
    assert aceito.status_code == 200 and aceito.json()["estado"] == "aceito"
    id_partida = get("/turma/sala", ana).json()["partida"]["id"]
    # ocupados: ninguem pode desafiar a Ana agora
    resposta = post("/turma/desafiar", carlos, {"para": ana["X-Jogador"], "tipo": "quiz"})
    assert resposta.status_code == 400 and "nao esta livre" in resposta.json()["message"]
    estado = get(f"/turma/partida/{id_partida}", beto).json()
    assert estado["seu_lado"] == "b" and estado["fim"] is None
    assert estado["personagens"]["a"]["image"].startswith(base() + "/imagens/")
    acelerar(id_partida)
    estado = get(f"/turma/partida/{id_partida}", ana).json()
    assert estado["fim"] is not None and len(estado["narracao"]) >= 3
    assert min(estado["hp"].values()) == 0
    vencedor = estado["jogadores"][estado["fim"]["vencedor"]]["nome"]
    classificacao = get("/turma/placar", ana).json()["classificacao"]
    pontos = {a["nome"]: a["pontos"] for a in classificacao}
    perdedor = "Beto D" if vencedor == "Ana D" else "Ana D"
    assert pontos[vencedor] >= 3 and pontos[perdedor] >= 1
    assert get("/turma/sala", ana).json()["partida"] is None       # acabou: livre de novo


def test_transformar_so_uma_vez():
    ana, beto = entrar("Ana T"), entrar("Beto T")
    post("/turma/desafiar", ana, {"para": beto["X-Jogador"], "tipo": "batalha", "personagem": 1})   # Goku
    desafio = get("/turma/sala", beto).json()["recebidos"][0]
    post("/turma/responder", beto, {"desafio": desafio["id"], "aceitar": True, "personagem": 4})    # Bulma
    id_partida = get("/turma/sala", ana).json()["partida"]["id"]
    assert post(f"/turma/partida/{id_partida}/transformar", ana).status_code == 200
    assert post(f"/turma/partida/{id_partida}/transformar", ana).status_code == 400
    assert post(f"/turma/partida/{id_partida}/transformar", beto).status_code == 400   # Bulma nao transforma
    estado = get(f"/turma/partida/{id_partida}", ana).json()
    assert estado["transformado"]["a"]["name"] == "Goku Ultra Instinc"
    post(f"/turma/partida/{id_partida}/desistir", beto)


def test_duelo_de_quiz():
    ana, beto = entrar("Ana Q"), entrar("Beto Q")
    post("/turma/desafiar", ana, {"para": beto["X-Jogador"], "tipo": "quiz", "rodadas": 3})
    desafio = get("/turma/sala", beto).json()["recebidos"][0]
    assert desafio["opcoes"] == {"rodadas": 3}
    post("/turma/responder", beto, {"desafio": desafio["id"], "aceitar": True})
    id_partida = get("/turma/sala", beto).json()["partida"]["id"]
    estado = get(f"/turma/partida/{id_partida}", ana).json()
    assert len(estado["rodadas"]) == 3 and len(estado["rodadas"][0]["opcoes"]) == 4
    assert post(f"/turma/partida/{id_partida}/progresso", ana, {"rodada": 9, "pontos": 1}).status_code == 400
    post(f"/turma/partida/{id_partida}/progresso", ana, {"rodada": 3, "pontos": 5, "terminou": True})
    assert get(f"/turma/partida/{id_partida}", beto).json()["fim"] is None        # Beto ainda jogando
    post(f"/turma/partida/{id_partida}/progresso", beto, {"rodada": 3, "pontos": 9, "terminou": True})
    fim = get(f"/turma/partida/{id_partida}", ana).json()["fim"]
    assert fim == {"vencedor": "b", "motivo": "pontos"}


def test_recusar_cancelar_e_expirar():
    ana, beto = entrar("Ana R"), entrar("Beto R")
    post("/turma/desafiar", ana, {"para": beto["X-Jogador"], "tipo": "quiz"})
    desafio = get("/turma/sala", beto).json()["recebidos"][0]
    post("/turma/responder", beto, {"desafio": desafio["id"], "aceitar": False})
    assert get("/turma/sala", ana).json()["enviado"]["estado"] == "recusado"
    post("/turma/desafiar", ana, {"para": beto["X-Jogador"], "tipo": "quiz"})
    enviado = get("/turma/sala", ana).json()["enviado"]
    post("/turma/cancelar", ana, {"desafio": enviado["id"]})
    assert get("/turma/sala", beto).json()["recebidos"] == []
    post("/turma/desafiar", ana, {"para": beto["X-Jogador"], "tipo": "quiz"})
    enviado = get("/turma/sala", ana).json()["enviado"]
    validade = modulo_sala.VALIDADE_DO_DESAFIO
    modulo_sala.VALIDADE_DO_DESAFIO = -1                  # "passaram" os 30 segundos
    try:
        assert get("/turma/sala", ana).json()["enviado"]["estado"] == "expirado"
    finally:
        modulo_sala.VALIDADE_DO_DESAFIO = validade


def test_desistencia_nao_da_ponto_ao_perdedor():
    ana, beto = entrar("Ana W"), entrar("Beto W")
    post("/turma/desafiar", ana, {"para": beto["X-Jogador"], "tipo": "batalha", "personagem": 2})
    desafio = get("/turma/sala", beto).json()["recebidos"][0]
    post("/turma/responder", beto, {"desafio": desafio["id"], "aceitar": True, "personagem": 3})
    id_partida = get("/turma/sala", ana).json()["partida"]["id"]
    post(f"/turma/partida/{id_partida}/desistir", ana)
    assert get(f"/turma/partida/{id_partida}", beto).json()["fim"]["motivo"] == "desistencia"
    classificacao = {a["nome"]: a for a in get("/turma/placar", ana).json()["classificacao"]}
    assert classificacao["Beto W"]["pontos"] == 3 and classificacao["Ana W"]["pontos"] == 0


def test_desafio_invalido():
    ana = entrar("Ana X")
    assert post("/turma/desafiar", ana, {"para": ana["X-Jogador"], "tipo": "quiz"}).status_code == 400
    assert post("/turma/desafiar", ana, {"para": "naoexiste", "tipo": "quiz"}).status_code == 400
    assert get("/turma/sala", {"X-Jogador": "naoexiste"}).status_code == 400
