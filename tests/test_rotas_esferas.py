"""Testes das rotas /esferas/ (servidor de teste em 127.0.0.1), pedindo como o app, o navegador e o curl.
Tambem o grito UDP (junto com a descoberta antiga) e 15 alunos resgatando ao mesmo tempo."""

import re
import socket
import threading

import requests

from core import api, descoberta, esferas, esferas_cliente, rede
from servidor import rotas_esferas
from servidor.rotas import PAGINA_INICIAL
from tests import test_servidor

CHROME = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
          "Chrome/129.0.0.0 Safari/537.36")
CURL = "curl/8.9.1"
POWERSHELL = "Mozilla/5.0 (Windows NT; Windows NT 10.0; pt-BR) WindowsPowerShell/5.1.19041.4894"
APP = "DragonBallDex/2.0"


def base():
    return test_servidor.servidor()


def servidor():
    base()
    return test_servidor._servidor


def entrar(nome):
    """Entra na sala como o app faz. Devolve os cabecalhos que o app manda em todo pedido."""
    resposta = requests.post(base() + "/turma/entrar", json={"nome": nome}, timeout=5).json()
    return {"X-Jogador": resposta["id"], "X-Aluno": nome, "User-Agent": APP}


def get(caminho, cabecalhos=None, **params):
    return requests.get(base() + caminho, params=params, headers=cabecalhos or {"User-Agent": APP}, timeout=5)


def post(caminho, dados, cabecalhos):
    return requests.post(base() + caminho, json=dados, headers=cabecalhos, timeout=5)


def numero_de(aluno):
    return get("/esferas/estado", aluno).json()["numero"]


def codigo(numero, esfera):
    return esferas.gerar_codigo(servidor().cacada.segredo, numero, esfera)


def com_cacada(funcao):
    """Comeca uma cacada nova (sem o limite de 2 s) e, no fim, deixa o servidor sem cacada, como na 2.2."""
    def teste():
        cacada, intervalo = servidor().cacada, esferas.INTERVALO_RESGATE
        cacada.encerrar()
        cacada.nova()
        cacada.iniciar()
        esferas.INTERVALO_RESGATE = 0
        try:
            funcao()
        finally:
            esferas.INTERVALO_RESGATE = intervalo
            cacada.encerrar()
            cacada.nova()
    teste.__name__ = funcao.__name__
    return teste


# ---------------- desligada ----------------

def test_tudo_409_antes_da_largada_e_pagina_igual_a_da_22():
    cacada = servidor().cacada
    cacada.encerrar()
    cacada.nova()
    ana = entrar("Ana Q")
    for caminho in ("/esferas/navegador", "/esferas/pista", "/esferas/radar", "/esferas/caverna-namek",
                    "/esferas/terminal", "/esferas/qualquer-coisa"):
        resposta = get(caminho, ana)
        assert resposta.status_code == 409 and "ainda não começou" in resposta.text, caminho
    estado = get("/esferas/estado", ana)
    assert estado.status_code == 409
    assert estado.json()["message"] == "A caçada ainda não começou 🐉" and estado.json()["numero"] >= 1
    assert post("/esferas/resgatar", {"codigo": "ESF-AAAAA"}, ana).status_code == 409
    assert get("/").content == PAGINA_INICIAL.encode("utf-8")         # byte a byte igual a 2.2


def test_estado_sem_entrar_na_sala():
    assert get("/esferas/estado").status_code == 400
    assert get("/esferas/estado", {"X-Jogador": "ninguem"}).status_code == 400


# ---------------- estado e resgate ----------------

@com_cacada
def test_estado_resgate_e_pedido():
    ana, beto = entrar("Ana R"), entrar("Beto R")
    estado = get("/esferas/estado", ana)
    assert estado.status_code == 200 and estado.json()["esferas"] == [1]
    assert estado.json()["dica"]["esfera"] == 2 and base() in estado.json()["dica"]["texto"]
    n_ana, n_beto = numero_de(ana), numero_de(beto)
    outro = post("/esferas/resgatar", {"codigo": codigo(n_beto, 2)}, ana)
    assert outro.status_code == 403 and outro.json()["message"] == "Essa esfera pertence a outro caçador! 👀"
    assert post("/esferas/resgatar", {"codigo": "ESF-22222"}, ana).status_code == 400
    assert post("/esferas/resgatar", {"codigo": "oi"}, ana).status_code == 400
    certo = post("/esferas/resgatar", {"codigo": codigo(n_ana, 2).replace("ESF-", "esf ")}, ana)
    assert certo.status_code == 200 and certo.json()["resgate"]["nova"] is True
    assert post("/esferas/pedido", {"pedido": 1}, ana).status_code == 400          # ainda nao juntou as 7
    for esfera in range(3, 8):
        post("/esferas/resgatar", {"codigo": codigo(n_ana, esfera)}, ana)
    estado = get("/esferas/estado", ana).json()
    assert estado["posicao"] == 1 and estado["pedido"]["pendente"] is True
    assert post("/esferas/pedido", {"pedido": 3}, ana).json()["pedido"]["escolhido"] == 3
    mensagens = [m["texto"] for m in servidor().chat.instantaneo()["mensagens"]]
    assert "🐉 Ana R invocou o dragão! (1º lugar)" in mensagens      # aviso pelo chat, sem rota nova


@com_cacada
def test_limite_de_2_segundos_responde_429():
    esferas.INTERVALO_RESGATE = 2.0
    ana = entrar("Ana L")
    numero = numero_de(ana)
    assert post("/esferas/resgatar", {"codigo": codigo(numero, 2)}, ana).status_code == 200
    rapido = post("/esferas/resgatar", {"codigo": codigo(numero, 3)}, ana)
    assert rapido.status_code == 429 and "2 segundos" in rapido.json()["message"]


@com_cacada
def test_pausada_responde_409():
    ana = entrar("Ana P")
    servidor().cacada.pausar()
    resposta = get("/esferas/pista", ana)
    assert resposta.status_code == 409 and "pausada" in resposta.text
    estado = get("/esferas/estado", ana)
    assert estado.status_code == 409 and estado.json()["esferas"] == [1]   # 409, mas com o progresso
    assert "/esferas/navegador" not in get("/").text


# ---------------- as esferas ----------------

@com_cacada
def test_esfera_2_so_para_navegador():
    numero = numero_de(entrar("Ana N"))
    assert "/esferas/navegador" in get("/").text                      # o link discreto da pagina inicial
    formulario = get("/esferas/navegador", {"User-Agent": CHROME})
    assert formulario.status_code == 200 and 'name="cacador"' in formulario.text
    pagina = get("/esferas/navegador", {"User-Agent": CHROME}, cacador=numero)
    assert pagina.status_code == 200 and codigo(numero, 2) in pagina.text
    for user_agent in (APP, CURL, POWERSHELL, "python-requests/2.34.2"):
        recusado = get("/esferas/navegador", {"User-Agent": user_agent}, cacador=numero)
        assert recusado.status_code == 403 and codigo(numero, 2) not in recusado.text, user_agent
    assert "User-Agent" in get("/esferas/navegador", {"User-Agent": APP}).text
    assert get("/esferas/navegador", {"User-Agent": CHROME}, cacador=999).status_code == 400
    assert get("/esferas/navegador", {"User-Agent": CHROME}, cacador="abc").status_code == 400


@com_cacada
def test_esfera_3_vem_no_cabecalho():
    ana = entrar("Ana H")
    numero = numero_de(ana)
    resposta = get("/esferas/pista", ana)
    assert resposta.status_code == 200 and resposta.headers["X-Esfera"] == codigo(numero, 3)
    assert "olhe com mais atenção" in resposta.text and codigo(numero, 3) not in resposta.text


@com_cacada
def test_tela_testar_alcanca_a_pista_com_o_x_jogador():
    ana = entrar("Ana T")
    numero = numero_de(ana)
    antes = api.URL_BASE
    try:
        api.usar_servidor(base()[len("http://"):])
        api.sessao.headers["X-Jogador"] = ana["X-Jogador"]
        resposta = rede.requisicao_crua("/esferas/pista")
        assert resposta.url == base() + "/esferas/pista" and resposta.headers["X-Esfera"] == codigo(numero, 3)
        assert rede.requisicao_crua("/characters/1").url == base() + "/api/characters/1"   # o resto nao muda
    finally:
        api.sessao.headers.pop("X-Jogador", None)
        api.URL_BASE = antes


@com_cacada
def test_esfera_4_radar():
    numero = numero_de(entrar("Ana D"))
    navegador = {"User-Agent": CHROME}
    for params in ({}, {"cacador": numero}, {"cacador": numero, "x": 11, "y": 2},
                   {"cacador": numero, "x": "a", "y": 2}, {"x": 1, "y": 2}):
        resposta = get("/esferas/radar", navegador, **params)
        assert resposta.status_code == 400 and "query string" in resposta.text, params
    x, y = esferas.alvo_do_radar(servidor().cacada.segredo, numero)
    achou = get("/esferas/radar", navegador, cacador=numero, x=x, y=y)
    assert achou.status_code == 200 and codigo(numero, 4) in achou.text
    perto = get("/esferas/radar", navegador, cacador=numero, x=x + 1 if x < 10 else x - 1, y=y)
    assert perto.status_code == 200 and "Fervendo" in perto.text and codigo(numero, 4) not in perto.text


@com_cacada
def test_esfera_5_404_com_corpo():
    ana = entrar("Ana K")
    numero = numero_de(ana)
    vazia = get("/esferas/caverna-vegeta", {"User-Agent": CHROME}, cacador=numero)
    assert vazia.status_code == 404 and "Caverna vazia" in vazia.text and "ESF-" not in vazia.text
    certa = get("/esferas/caverna-Namék", {"User-Agent": CHROME}, cacador=numero)    # vai como %C3%A9
    assert certa.status_code == 404 and codigo(numero, 5) in certa.text and "ou não?" in certa.text
    pelo_app = get("/esferas/caverna-namek", ana)                                    # com o X-Jogador
    assert pelo_app.status_code == 404 and codigo(numero, 5) in pelo_app.text


@com_cacada
def test_esfera_7_so_pelo_terminal():
    numero = numero_de(entrar("Ana C"))
    for user_agent in (CURL, POWERSHELL):
        resposta = get("/esferas/terminal", {"User-Agent": user_agent}, cacador=numero)
        assert resposta.status_code == 200 and codigo(numero, 7) in resposta.text, user_agent
        assert resposta.content.isascii()                 # o cmd mostra acento errado: so ASCII
    for user_agent in (CHROME, APP):
        recusado = get("/esferas/terminal", {"User-Agent": user_agent}, cacador=numero)
        assert recusado.status_code == 403 and "Use o terminal, caçador!" in recusado.text
    erro = get("/esferas/terminal", {"User-Agent": CURL})
    assert erro.status_code == 400 and erro.content.isascii()


def test_iniciar_cacada_pega_quem_esta_online():
    cacada = servidor().cacada
    cacada.encerrar()
    cacada.nova()
    ana = entrar("Ana O")
    try:
        rotas_esferas.iniciar_cacada(servidor(), minutos=20)
        foto = cacada.instantaneo()
        assert any(c["nome"] == "Ana O" and c["esferas"] == [1] for c in foto["cacadores"])
        assert 20 * 60 - 2 <= foto["tempo_restante"] <= 20 * 60           # relogio de verdade: 1199 ou 1200
        assert get("/esferas/estado", ana).json()["esferas"] == [1]
    finally:
        cacada.encerrar()
        cacada.nova()


# ---------------- grito (UDP) ----------------

def mandar_udp(*mensagens):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        for mensagem in mensagens:
            sock.sendto(mensagem, ("127.0.0.1", descoberta.PORTA_DESCOBERTA))
    finally:
        sock.close()


@com_cacada
def test_grito_udp_e_a_descoberta_antiga_continua_igual():
    app = servidor()
    numero = numero_de(entrar("Ana G"))
    respondedor = descoberta.RespondedorDeDescoberta(
        8124, "Teste", host="127.0.0.1",
        ao_receber_outro=lambda dados, remetente: rotas_esferas.ao_receber_udp(app, dados, remetente))
    try:
        mandar_udp(b"\xff\xfe", b"DBDEX-ESFERA", b"DBDEX-ESFERA abc", b"x" * 1000)     # lixo na porta
        direto = esferas_cliente.gritar(numero, "kamehameha", direto=True)            # sem servidor: broadcast
        assert direto["ok"] is True and direto["codigo"] == codigo(numero, 6) and direto["ip"] == "127.0.0.1"
        assert esferas_cliente.gritar(numero, "hadouken")["ok"] is False
        achados = descoberta.procurar_servidores(espera=1.0)
        assert {"endereco": "127.0.0.1:8124", "nome": "Teste"} in achados              # igual ao teste antigo
        assert respondedor.thread.is_alive()
    finally:
        respondedor.parar()
    assert any(e["tipo"] == "grito" for e in app.cacada.eventos_depois(0))


def test_mensagem_estranha_nao_derruba_a_descoberta():
    def com_defeito(dados, remetente):
        raise RuntimeError("um erro qualquer no tratamento do grito")

    respondedor = descoberta.RespondedorDeDescoberta(8125, "Teste", host="127.0.0.1", ao_receber_outro=com_defeito)
    try:
        mandar_udp(esferas.montar_grito(1, "KAMEHAMEHA"), b"qualquer coisa")
        assert {"endereco": "127.0.0.1:8125", "nome": "Teste"} in descoberta.procurar_servidores(espera=1.0)
        assert respondedor.thread.is_alive()
    finally:
        respondedor.parar()


# ---------------- 15 alunos ao mesmo tempo ----------------

@com_cacada
def test_15_alunos_ao_mesmo_tempo():
    """15 threads acham (pelas rotas, como os alunos) e resgatam as 7 esferas ao mesmo tempo."""
    app = servidor()
    alunos = [entrar(f"Aluno {i:02d} S") for i in range(15)]
    numeros = [numero_de(aluno) for aluno in alunos]
    problemas = []
    largada = threading.Barrier(len(alunos))
    procurar = re.compile(r"ESF-[A-Z0-9]{5}").search

    def cacar(aluno, numero):
        try:
            largada.wait(timeout=10)                       # todos comecam juntos
            navegador = {"User-Agent": CHROME}
            x, y = esferas.alvo_do_radar(app.cacada.segredo, numero)
            grito = rotas_esferas.ao_receber_udp(app, esferas.montar_grito(numero, "KAMEHAMEHA"), None)
            codigos = {
                2: procurar(get("/esferas/navegador", navegador, cacador=numero).text).group(0),
                3: get("/esferas/pista", aluno).headers["X-Esfera"],
                4: procurar(get("/esferas/radar", navegador, cacador=numero, x=x, y=y).text).group(0),
                5: procurar(get("/esferas/caverna-namek", navegador, cacador=numero).text).group(0),
                6: esferas.ler_resposta_grito(grito)["codigo"],
                7: procurar(get("/esferas/terminal", {"User-Agent": CURL}, cacador=numero).text).group(0),
            }
            for esfera, codigo in codigos.items():
                resposta = post("/esferas/resgatar", {"codigo": codigo}, aluno)
                if resposta.status_code != 200 or resposta.json()["resgate"]["esfera"] != esfera:
                    problemas.append(f"{numero}/{esfera}: {resposta.status_code} {resposta.text[:80]}")
        except Exception as erro:
            problemas.append(f"{numero}: {erro!r}")

    threads = [threading.Thread(target=cacar, args=par) for par in zip(alunos, numeros)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=30)
    assert not problemas, problemas
    foto = app.cacada.instantaneo()
    meus = [c for c in foto["cacadores"] if c["numero"] in numeros]
    assert len(meus) == 15 and all(c["esferas"] == list(range(1, 8)) for c in meus)
    assert sorted(c["posicao"] for c in meus) == list(range(1, 16))            # ninguem empatou na ordem
    assert all(c["pontos"] == 7 + esferas.BONUS_ORDEM.get(c["posicao"], 0) for c in meus)
    assert sum(1 for e in app.cacada.eventos_depois(0) if e["tipo"] == "completou" and e["numero"] in numeros) == 15
    assert not [p for p in app.monitor.instantaneo()["pedidos"] if p["status"] >= 500]
