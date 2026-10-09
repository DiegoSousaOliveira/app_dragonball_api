"""Testes do modo demonstracao 🎓: quem entra no mundo demo (so token certo + loopback), o isolamento (nada do ensaio
aparece no mundo real, e vice-versa), o chat fechado, os numeros 901+ pelo navegador e pelo UDP e os robos."""

import secrets

import requests

from core import demo, esferas
from servidor import rotas_esferas
from servidor.mundo_demo import PRIMEIRO_NUMERO, MundoDemo, mundo_do_grito, mundo_do_pedido
from tests.test_rotas_esferas import APP, CHROME, CURL, base, entrar, get, post, servidor


def com_demo(funcao):
    """Liga um mundo demo (sem a thread dos robos: o teste joga por eles) e, no fim, desliga."""
    def teste():
        app = servidor()
        app.desligar_demo()
        app.demo = MundoDemo(app, robos_jogando=False)
        app.demo.preparar()
        try:
            funcao()
        finally:
            app.desligar_demo()
    teste.__name__ = funcao.__name__
    return teste


def do_demo(cabecalhos=None):
    """Os cabecalhos do app aberto pelo botao 🎓 (o token vai em todo pedido)."""
    return dict(cabecalhos or {"User-Agent": APP}, **{demo.CABECALHO: servidor().token_demo})


def entrar_no_demo():
    resposta = requests.post(base() + "/turma/entrar", json={"nome": demo.NOME}, headers=do_demo(), timeout=5)
    return do_demo({"X-Jogador": resposta.json()["id"], "X-Aluno": "Professor", "User-Agent": APP})


@com_demo
def test_so_token_certo_e_loopback_entram_no_demo():
    app = servidor()
    certo = {demo.CABECALHO: app.token_demo}
    radar = "/esferas/radar"
    assert mundo_do_pedido(app, "127.0.0.1", certo, "/turma/sala", {}) is app.demo
    assert mundo_do_pedido(app, "::1", certo, "/turma/sala", {}) is app.demo
    assert mundo_do_pedido(app, "192.168.0.20", certo, "/turma/sala", {}) is app       # de outro PC: aluno normal
    for errado in ("", "demo", "Professor", secrets.token_urlsafe(32), app.token_demo[:-1], "çãõ🎓"):
        assert mundo_do_pedido(app, "127.0.0.1", {demo.CABECALHO: errado}, "/turma/sala", {}) is app
    # navegador / curl no PC do professor: so com o numero do ensaio (901+)
    assert mundo_do_pedido(app, "127.0.0.1", {}, radar, {"cacador": str(PRIMEIRO_NUMERO)}) is app.demo
    assert mundo_do_pedido(app, "127.0.0.1", {}, radar, {"cacador": "7"}) is app
    assert mundo_do_pedido(app, "192.168.0.20", {}, radar, {"cacador": "901"}) is app
    assert mundo_do_pedido(app, "127.0.0.1", {"X-Jogador": "abc"}, radar, {"cacador": "901"}) is app
    assert mundo_do_pedido(app, "127.0.0.1", {}, "/turma/sala", {"cacador": "901"}) is app
    assert mundo_do_grito(app, "127.0.0.1", 901) is app.demo
    assert mundo_do_grito(app, "192.168.0.20", 901) is app and mundo_do_grito(app, "127.0.0.1", 7) is app
    app.desligar_demo()                                     # sem o botao 🎓, nem o token certo abre o demo
    assert mundo_do_pedido(app, "127.0.0.1", certo, "/turma/sala", {}) is app
    assert mundo_do_grito(app, "127.0.0.1", 901) is app


def test_sem_token_no_ambiente_o_demo_nao_abre():
    import os
    for nome in (demo.VARIAVEL_TOKEN, demo.VARIAVEL_SERVIDOR):
        os.environ.pop(nome, None)
    assert demo.ler_do_ambiente() is None                  # "DragonBallDex.exe --demo" na mao: nada muda
    os.environ.update(demo.ambiente_para_o_app("abc", "127.0.0.1:8000"))
    assert demo.ler_do_ambiente() == ("abc", "127.0.0.1:8000")
    assert demo.VARIAVEL_TOKEN not in os.environ             # o que o app abrir depois nao herda o token


@com_demo
def test_o_ensaio_nao_aparece_no_mundo_real():
    app = servidor()
    real = entrar("Ana Real")
    prof = entrar_no_demo()
    assert prof["X-Jogador"] == app.demo.professor["id"]
    sala_demo = get("/turma/sala", prof).json()
    nomes_demo = {j["nome"] for j in sala_demo["jogadores"]}
    assert demo.NOME in nomes_demo and all("🤖" in n for n in nomes_demo - {demo.NOME})
    assert "Ana Real" not in nomes_demo
    nomes_reais = {j["nome"] for j in get("/turma/sala", real).json()["jogadores"]}
    assert not nomes_reais & nomes_demo
    assert not {a["nome"] for a in app.sala.visao_do_professor()["alunos"]} & nomes_demo
    # um aluno de verdade chamado "Professor 🎓" ou "demo" continua no mundo real
    for nome in (demo.NOME, "demo"):
        falso = {"X-Jogador": requests.post(base() + "/turma/entrar", json={"nome": nome}, timeout=5).json()["id"],
                 "User-Agent": APP}
        assert falso["X-Jogador"] != prof["X-Jogador"] and falso["X-Jogador"] in app.sala.jogadores
        assert get("/esferas/estado", falso).status_code == 409                      # a Caca real nao comecou
    # a Caca do ensaio esta sempre valendo, com os numeros 901+
    estado = get("/esferas/estado", prof)
    assert estado.status_code == 200 and estado.json()["numero"] == PRIMEIRO_NUMERO
    assert app.cacada.estado != "ativa" and all(c["numero"] < PRIMEIRO_NUMERO
                                                for c in app.cacada.instantaneo()["cacadores"])
    # a Conquista do ensaio: o professor tem um planeta; nada disso no mundo real
    conquista = get("/conquista/estado", prof).json()
    assert conquista["estado"] == "ativa" and sum(t["meu"] for t in conquista["mapa"]) == 1
    assert not {r["nome"] for r in app.conquista.instantaneo()["ranking"]} & nomes_demo
    # o placar e o monitor: o professor do demo nao vira "aluno conectado"
    assert not {a["nome"] for a in get("/turma/placar").json()["alunos"]} & {"Professor", demo.NOME}
    assert not {a["nome"] for a in app.monitor.instantaneo()["alunos"]} & {"Professor", demo.NOME}
    pedidos = app.monitor.instantaneo()["pedidos"]
    assert any(p.get("demo") and p["caminho"] == "/conquista/estado" for p in pedidos)
    assert not any(p.get("demo") for p in pedidos if p["aluno"] == "Ana Real")


@com_demo
def test_chat_fechado_e_gritos_separados():
    app = servidor()
    prof = entrar_no_demo()
    real = entrar("Beto Real")
    antes = app.chat.instantaneo()["ultimo_id"]
    recusa = post("/chat", {"texto": "oi turma"}, prof)
    assert recusa.status_code == 403 and "demonstração" in recusa.json()["message"]
    assert app.chat.instantaneo()["ultimo_id"] == antes                              # nada no chat da turma
    assert "demonstração" in get("/chat", prof).json()["mensagens"][0]["texto"]
    assert post("/gritos/meu", {"frase": "Ensaio do professor!"}, prof).json()["frase"] == "Ensaio do professor!"
    assert get("/gritos/meu", real).json()["frase"] != "Ensaio do professor!"
    assert prof["X-Jogador"] not in app.gritos.instantaneo()
    app.demo.gritos.anunciar(prof["X-Jogador"], demo.NOME, "conquista", "Professor conquistou Namek!")
    assert all(e["texto"] != "Professor conquistou Namek!"
               for e in get("/gritos/eventos", real).json()["eventos"])


@com_demo
def test_esferas_do_ensaio_pelo_navegador_curl_e_udp():
    app = servidor()
    prof = entrar_no_demo()
    numero = get("/esferas/estado", prof).json()["numero"]
    segredo = app.demo.cacada.segredo
    pagina = requests.get(base() + "/", headers={"User-Agent": CHROME}, timeout=5).text
    assert "/esferas/navegador" in pagina                  # o link da esfera 2 do ensaio (sem Caca real valendo)
    navegador = get("/esferas/navegador", {"User-Agent": CHROME}, cacador=numero)
    assert esferas.gerar_codigo(segredo, numero, 2) in navegador.text
    assert get("/esferas/navegador", {"User-Agent": CHROME}).status_code == 200      # o formulario do ensaio
    terminal = get("/esferas/terminal", {"User-Agent": CURL}, cacador=numero)
    assert esferas.gerar_codigo(segredo, numero, 7) in terminal.text
    real = entrar("Caio Real")
    assert get("/esferas/navegador", dict(real, **{"User-Agent": CHROME}), cacador=numero).status_code == 409
    grito = esferas.montar_grito(numero, "KAMEHAMEHA")
    do_pc = esferas.ler_resposta_grito(rotas_esferas.ao_receber_udp(app, grito, ("127.0.0.1", 50000)))
    assert do_pc["ok"] and do_pc["codigo"] == esferas.gerar_codigo(segredo, numero, 6)
    de_fora = esferas.ler_resposta_grito(rotas_esferas.ao_receber_udp(app, grito, ("192.168.0.20", 50000)))
    assert not de_fora["ok"]                              # um aluno nao chega no ensaio pelo UDP
    resgate = post("/esferas/resgatar", {"codigo": do_pc["codigo"]}, prof)
    assert resgate.status_code == 200 and resgate.json()["resgate"]["esfera"] == 6


class Relogio:
    def __init__(self):
        self.agora = 1_000.0

    def __call__(self):
        return self.agora


def test_robos_aceitam_desafios_jogam_quiz_e_invadem():
    app = servidor()
    relogio = Relogio()
    mundo = MundoDemo(app, rng=__import__("random").Random(4), relogio=relogio, robos_jogando=False)
    mundo.preparar()
    prof, robo = mundo.professor["id"], mundo.robos[0]
    mundo.sala.desafiar(prof, {"para": robo.id, "tipo": "quiz", "rodadas": 3})
    mundo.passo()
    partida = mundo.sala.visao(prof)["partida"]
    assert partida and partida["tipo"] == "quiz"                       # o robo aceitou sozinho
    for _ in range(6):
        relogio.agora += 10
        mundo.passo()
    estado = mundo.sala.estado_da_partida(prof, partida["id"])
    lado = "b" if estado["seu_lado"] == "a" else "a"
    assert estado["progresso"][lado]["terminou"] and estado["progresso"][lado]["rodada"] == 3
    mundo.sala.desistir(prof, partida["id"])
    assert any(d["vencedor"] == robo.nome for d in mundo.placar.duelos)    # no placar do DEMO
    assert all(d["vencedor"] != robo.nome for d in app.placar.duelos)       # nunca no da turma
    mapa = mundo.conquista.instantaneo()["mapa"]
    assert sum(t["dono"] in {r.nome for r in mundo.robos} for t in mapa) == 4     # 4 territorios de robos 🤖
    assert sum(t["dono"] is None for t in mapa) == 2 and sum(t["dono"] == demo.NOME for t in mapa) == 1
    assert all(g["padrao"] for g in mundo.gritos.instantaneo().values())          # so o grito padrao no ensaio
    meu = next(t for t in mapa if t["dono"] == demo.NOME)
    for _ in range(8):                                                     # os robos invadem (nunca o professor)
        relogio.agora += 60
        mundo.passo()
    invadidos = {i.territorio for i in mundo.conquista.invasoes.values()}
    assert invadidos and meu["id"] not in invadidos
    assert {i.atacante for i in mundo.conquista.invasoes.values()} <= {r.id for r in mundo.robos}


def test_botao_do_painel_cria_um_mundo_novo_e_desliga_o_anterior():
    app = servidor()
    primeiro = app.ligar_demo()
    segundo = app.ligar_demo()
    try:
        assert app.demo is segundo and primeiro is not segundo and primeiro._parar.is_set()
        assert segundo.cacada.estado == "ativa" and app.token_demo        # o token nao muda (so a cada inicio)
    finally:
        app.desligar_demo()
    assert app.demo is None and segundo._parar.is_set()
