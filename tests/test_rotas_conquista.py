"""Testes das rotas /conquista/ (servidor de teste em 127.0.0.1), pedindo como o app faz."""

import threading

import requests

from servidor import rotas_conquista
from tests.test_conquista import FONTE
from tests.test_rotas_esferas import base, entrar, get, post, servidor

FORTE, FRACO = FONTE.id_de("Grand Priest"), FONTE.id_de("Mr. Satan")


def com_conquista(funcao):
    """Comeca com a Conquista desligada e, no fim, deixa o servidor sem Conquista (como na 2.3.2)."""
    def teste():
        conquista = servidor().conquista
        conquista.encerrar()
        conquista.nova()
        try:
            funcao()
        finally:
            conquista.encerrar()
            conquista.nova()
    teste.__name__ = funcao.__name__
    return teste


def largada(*alunos, neutros=0):
    """Comeca a Conquista so com estes alunos (outros testes deixam muita gente "online" na sala)."""
    servidor().conquista.iniciar([(a["X-Jogador"], a["X-Aluno"]) for a in alunos], neutros=neutros)


def meu_territorio(aluno):
    return next(t for t in get("/conquista/estado", aluno).json()["mapa"] if t["meu"])


@com_conquista
def test_parada_responde_409_com_os_dados():
    ana = entrar("Ana CQ")
    estado = get("/conquista/estado", ana)
    assert estado.status_code == 409 and estado.json()["message"] == "A Conquista ainda não começou 🗺"
    assert estado.json()["estado"] == "aguardando" and estado.json()["mapa"] == []
    assert post("/conquista/guardiao", {"personagem": FORTE}, ana).status_code == 200    # da para escolher antes
    assert post("/conquista/invadir", {"territorio": "1", "personagem": FORTE}, ana).status_code == 409
    assert get("/conquista/estado").status_code == 400                                     # sem X-Jogador
    assert get("/conquista/qualquer-coisa", ana).status_code == 404


@com_conquista
def test_invasao_pela_rede():
    ana, beto, carla = entrar("Ana CR"), entrar("Beto CR"), entrar("Carla CR")
    placar_antes = requests.get(base() + "/turma/placar", timeout=5).json()["classificacao"]
    largada(ana, beto, carla)
    assert post("/conquista/guardiao", {"personagem": FRACO}, beto).status_code == 200
    assert post("/conquista/guardiao", {"personagem": FORTE}, beto).status_code == 429     # trocou rapido demais
    alvo = meu_territorio(beto)
    assert post("/conquista/invadir", {"territorio": meu_territorio(ana)["id"], "personagem": FORTE},
                ana).status_code == 403
    assert post("/conquista/invadir", {"territorio": "999", "personagem": FORTE}, ana).status_code == 404
    resposta = post("/conquista/invadir", {"territorio": alvo["id"], "personagem": FORTE}, ana)
    assert resposta.status_code == 200
    id_partida = resposta.json()["partida"]
    assert post("/conquista/invadir", {"territorio": alvo["id"], "personagem": FORTE}, carla).status_code == 409
    luta = get(f"/turma/partida/{id_partida}", ana)                                       # a rota dos duelos
    assert luta.status_code == 200 and luta.json()["seu_lado"] == "a" and luta.json()["conquista"] is True
    assert luta.json()["personagens"]["a"]["image"].startswith(base() + "/imagens/")
    assert get(f"/turma/partida/{id_partida}", carla).status_code == 403                  # nao e a luta dela
    estado = get("/conquista/estado", ana).json()
    assert estado["eu"]["invasao"] == id_partida and any(t["em_batalha"] for t in estado["mapa"])
    sala = get("/turma/sala", ana).json()                                                  # a Sala nem fica sabendo
    assert sala["partida"] is None and next(j for j in sala["jogadores"] if j["voce"])["estado"] == "livre"
    assert post(f"/turma/partida/{id_partida}/desistir", {}, ana).status_code == 200
    assert post("/conquista/invadir", {"territorio": alvo["id"], "personagem": FORTE}, ana).status_code == 429
    assert requests.get(base() + "/turma/placar", timeout=5).json()["classificacao"] == placar_antes


@com_conquista
def test_duas_invasoes_simultaneas_pela_rede():
    alunos = [entrar(f"Aluno {i} CS") for i in range(6)]
    alvo_dono = entrar("Alvo CS")
    largada(alvo_dono, *alunos)
    alvo = meu_territorio(alvo_dono)
    status, juntos = [], threading.Barrier(len(alunos))

    def invadir(aluno):
        juntos.wait(timeout=5)
        status.append(post("/conquista/invadir", {"territorio": alvo["id"], "personagem": FORTE}, aluno).status_code)

    threads = [threading.Thread(target=invadir, args=(aluno,)) for aluno in alunos]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=10)
    assert sorted(status) == [200] + [409] * 5


@com_conquista
def test_estado_traz_eventos_novos_pelo_depois():
    ana, beto = entrar("Ana CE"), entrar("Beto CE")
    largada(ana, beto, neutros=1)
    primeiro = get("/conquista/estado", ana).json()
    assert primeiro["eventos"][-1]["tipo"] == "inicio" and primeiro["eu"]["territorios"] == 1
    depois = get("/conquista/estado", ana, depois=primeiro["ultimo_evento"]).json()
    assert depois["eventos"] == []
    neutro = next(t for t in primeiro["mapa"] if t["dono"] is None)
    post("/conquista/invadir", {"territorio": neutro["id"], "personagem": FORTE}, beto)
    novos = get("/conquista/estado", ana, depois=primeiro["ultimo_evento"]).json()["eventos"]
    assert [e["tipo"] for e in novos] == ["invasao"] and "Beto CE" in novos[0]["texto"]


@com_conquista
def test_iniciar_pelo_painel_pega_quem_esta_online():
    entrar("Ana CG")
    rotas_conquista.iniciar_conquista(servidor(), minutos=15, neutros=2)
    conquista = servidor().conquista
    assert "Ana CG" in [p.nome for p in conquista.participantes.values()]
    assert conquista.estado == "ativa" and 14 * 60 <= conquista.instantaneo()["tempo_restante"] <= 15 * 60
