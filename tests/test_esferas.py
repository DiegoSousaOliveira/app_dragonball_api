"""Testes da logica da Caca as Esferas (core/esferas.py). Um relogio falso evita esperar de verdade."""

import json
import tempfile
from pathlib import Path

from core import esferas
from core.esferas import Cacada


class Relogio:
    """Relogio de mentira: so anda quando o teste manda."""

    def __init__(self):
        self.agora = 1_000_000.0

    def __call__(self):
        return self.agora

    def passar(self, segundos):
        self.agora += segundos


def nova_cacada(alunos=("Ana", "Beto"), minutos=None):
    """Cacada ja iniciada com estes alunos online (o id de cada um e 'id-<nome>')."""
    relogio = Relogio()
    avisos = []
    cacada = Cacada(avisar=avisos.append, relogio=relogio)
    cacada.iniciar([(f"id-{nome}", nome) for nome in alunos], minutos=minutos)
    return cacada, relogio, avisos


def codigo(cacada, nome, esfera):
    return esferas.gerar_codigo(cacada.segredo, cacada.numeros[f"id-{nome}"], esfera)


def resgatar(cacada, relogio, nome, texto):
    relogio.passar(esferas.INTERVALO_RESGATE)          # respeita o limite de 2 s entre tentativas
    return cacada.resgatar(f"id-{nome}", nome, texto)


def completar(cacada, relogio, nome):
    for esfera in range(2, 8):
        resgatar(cacada, relogio, nome, codigo(cacada, nome, esfera))


def levanta(classe, funcao, *args):
    """Confere que funcao(*args) levanta 'classe' e devolve o erro."""
    try:
        funcao(*args)
    except classe as erro:
        return erro
    raise AssertionError(f"esperava {classe.__name__}")


def pontos(cacada):
    return {c["nome"]: c["pontos"] for c in cacada.instantaneo()["cacadores"]}


# ---------------- codigos ----------------

def test_codigo_pessoal_e_formato():
    codigo_ana = esferas.gerar_codigo("segredo", 1, 3)
    assert codigo_ana == esferas.gerar_codigo("segredo", 1, 3)           # sempre o mesmo
    assert codigo_ana.startswith("ESF-") and len(codigo_ana) == 9
    assert all(letra in esferas.ALFABETO for letra in codigo_ana[4:])
    assert not set("0O1IL") & set(esferas.ALFABETO)                     # nada de letra ambigua
    todos = {esferas.gerar_codigo("segredo", numero, esfera) for numero in range(1, 16) for esfera in range(1, 8)}
    assert len(todos) == 15 * 7                                          # cada cacador tem os seus
    assert esferas.gerar_codigo("outro segredo", 1, 3) != codigo_ana     # nova cacada = codigos novos


def test_normalizar_codigo():
    for texto in (" esf-7kq2m ", "ESF 7KQ2M", "7kq2m", "ESF7KQ2M", "esf - 7kq 2m"):
        assert esferas.normalizar_codigo(texto) == "ESF-7KQ2M", texto
    assert esferas.normalizar_codigo("ESFAB") == "ESF-ESFAB"            # codigo que comeca com "ESF"
    for texto in ("", "ESF-7KQ2", "ESF-7KQ2MM", "ESF-0OIL1", None, 123):
        assert esferas.normalizar_codigo(texto) is None, texto


def test_resgate_e_codigo_de_outro_cacador():
    cacada, relogio, _ = nova_cacada()
    visao = resgatar(cacada, relogio, "Ana", " " + codigo(cacada, "Ana", 3).lower())
    assert visao["resgate"]["esfera"] == 3 and visao["resgate"]["nova"] is True
    assert visao["esferas"] == [1, 3]
    erro = levanta(esferas.DeOutroCacador, resgatar, cacada, relogio, "Ana", codigo(cacada, "Beto", 2))
    assert str(erro) == "Essa esfera pertence a outro caçador! 👀" and erro.status == 403
    erro = levanta(esferas.ErroDaCacada, resgatar, cacada, relogio, "Ana", "ESF-22222")
    assert erro.status == 400 and "errado" in str(erro)
    assert "não parece" in str(levanta(esferas.ErroDaCacada, resgatar, cacada, relogio, "Ana", "oi"))
    de_novo = resgatar(cacada, relogio, "Ana", codigo(cacada, "Ana", 3))
    assert de_novo["resgate"]["nova"] is False and de_novo["esferas"] == [1, 3]


def test_limite_de_2_segundos():
    cacada, relogio, _ = nova_cacada()
    resgatar(cacada, relogio, "Ana", codigo(cacada, "Ana", 2))
    relogio.passar(1.9)
    erro = levanta(esferas.Devagar, cacada.resgatar, "id-Ana", "Ana", codigo(cacada, "Ana", 3))
    assert erro.status == 429
    relogio.passar(0.1)                                   # 2 s depois da ultima tentativa que valeu
    assert cacada.resgatar("id-Ana", "Ana", codigo(cacada, "Ana", 3))["esferas"] == [1, 2, 3]
    relogio.passar(0.5)                                   # o limite e por aluno: o Beto nao espera a Ana
    assert cacada.resgatar("id-Beto", "Beto", codigo(cacada, "Beto", 2))["esferas"] == [1, 2]


# ---------------- radar, caverna, palavra magica, User-Agent ----------------

def test_radar():
    cacada, _, _ = nova_cacada()
    numero = cacada.numeros["id-Ana"]
    x, y = esferas.alvo_do_radar(cacada.segredo, numero)
    assert 0 <= x <= 10 and 0 <= y <= 10
    assert cacada.radar(numero, x, y) == {"achou": True, "codigo": codigo(cacada, "Ana", 4)}
    vizinho = x + 1 if x < 10 else x - 1
    assert cacada.radar(numero, vizinho, y) == {"achou": False, "temperatura": "🔥🔥 Fervendo!"}
    assert [esferas.temperatura(d) for d in (1, 3, 4, 6, 7, 20)] == [
        "🔥🔥 Fervendo!", "🔥 Quente", "🌤 Morno", "🌤 Morno", "❄️ Frio", "❄️ Frio"]
    alvos = {esferas.alvo_do_radar(cacada.segredo, n) for n in range(1, 16)}
    assert len(alvos) > 1                                  # cada cacador tem o seu lugar
    assert levanta(esferas.ErroDaCacada, cacada.radar, 99, 1, 1).status == 400


def test_caverna_palavra_e_user_agent():
    assert all(esferas.eh_a_caverna_certa(nome) for nome in ("namek", "Namek", "NAMÉK", " namek "))
    assert not esferas.eh_a_caverna_certa("vegeta")
    assert all(esferas.eh_a_palavra_magica(p) for p in ("KAMEHAMEHA", "kamehameha", "Kame-hame-há!"))
    assert not esferas.eh_a_palavra_magica("hadouken")
    chrome = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
              "Chrome/129.0.0.0 Safari/537.36 Edg/129.0.0.0")
    firefox = "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:131.0) Gecko/20100101 Firefox/131.0"
    powershell = "Mozilla/5.0 (Windows NT; Windows NT 10.0; pt-BR) WindowsPowerShell/5.1.19041.4894"
    powershell7 = "Mozilla/5.0 (Windows NT 10.0; Microsoft Windows 10.0.19045; pt-BR) PowerShell/7.4.5"
    app, requests_puro, curl = "DragonBallDex/2.0", "python-requests/2.34.2", "curl/8.9.1"
    assert [esferas.eh_navegador(ua) for ua in (chrome, firefox, powershell, powershell7, app, requests_puro,
                                                 curl, "", None)] == [True, True] + [False] * 7
    assert [esferas.eh_terminal(ua) for ua in (curl, powershell, powershell7, chrome, app, None)] == [
        True, True, True, False, False, False]


# ---------------- esfera 1, dicas, ordem ----------------

def test_esfera_1_automatica_e_dicas_em_sequencia():
    relogio = Relogio()
    cacada = Cacada(relogio=relogio)
    antes = cacada.visao("id-Ana", "Ana")                 # abriu a tela Esferas antes da largada
    assert antes["estado"] == "aguardando" and antes["numero"] == 1 and antes["esferas"] == []
    assert antes["dica"] is None
    cacada.iniciar([("id-Beto", "Beto")])
    visao = cacada.visao("id-Ana", "Ana", "192.168.0.10:8000")
    assert visao["esferas"] == [1] and visao["ultima"]["esfera"] == 1
    assert visao["dica"]["esfera"] == 2 and "http://192.168.0.10:8000" in visao["dica"]["texto"]
    assert cacada.visao("id-Carla", "Carla")["esferas"] == [1]       # chegou depois: ganha a 1 na hora
    relogio.passar(2)
    visao = cacada.resgatar("id-Ana", "Ana", esferas.gerar_codigo(cacada.segredo, 1, 3))   # a 3 antes da 2
    assert visao["esferas"] == [1, 3] and visao["dica"]["esfera"] == 2  # a dica nao pula
    relogio.passar(2)
    visao = cacada.resgatar("id-Ana", "Ana", esferas.gerar_codigo(cacada.segredo, 1, 2), "192.168.0.10:8000")
    assert visao["dica"]["esfera"] == 4 and "cacador=1&x=5&y=5" in visao["dica"]["texto"]


def test_ordem_de_conclusao_e_bonus():
    cacada, relogio, avisos = nova_cacada(("Ana", "Beto", "Carla", "Davi"))
    for nome in ("Beto", "Ana", "Davi", "Carla"):
        completar(cacada, relogio, nome)
        cacada.escolher_pedido(f"id-{nome}", nome, 3)    # pedido simbolico: nao muda os pontos
    foto = cacada.instantaneo()
    assert {c["nome"]: c["posicao"] for c in foto["cacadores"]} == {"Beto": 1, "Ana": 2, "Davi": 3, "Carla": 4}
    assert pontos(cacada) == {"Beto": 7 + 5, "Ana": 7 + 3, "Davi": 7 + 2, "Carla": 7}
    assert [p["nome"] for p in foto["podio"]] == ["Beto", "Ana", "Davi"]
    assert "🐉 Beto invocou o dragão! (1º lugar)" in avisos
    assert "🐉 Carla invocou o dragão! (4º lugar)" in avisos


def test_pedidos():
    cacada, relogio, avisos = nova_cacada(("Ana", "Beto", "Carla"))
    assert "Junte" in str(levanta(esferas.ErroDaCacada, cacada.escolher_pedido, "id-Ana", "Ana", 1))
    completar(cacada, relogio, "Ana")
    assert cacada.visao("id-Ana", "Ana")["pedido"]["pendente"] is True
    cacada.escolher_pedido("id-Ana", "Ana", 2)            # +1 para todos (inclusive ela)
    assert pontos(cacada) == {"Ana": 7 + 5 + 1, "Beto": 1 + 1, "Carla": 1 + 1}
    assert "já fez" in str(levanta(esferas.ErroDaCacada, cacada.escolher_pedido, "id-Ana", "Ana", 1))
    completar(cacada, relogio, "Beto")
    for invalido in (True, 4, "1", None):
        levanta(esferas.ErroDaCacada, cacada.escolher_pedido, "id-Beto", "Beto", invalido)
    cacada.escolher_pedido("id-Beto", "Beto", 1)          # +3 para ele
    assert pontos(cacada)["Beto"] == 7 + 3 + 1 + 3
    completar(cacada, relogio, "Carla")                    # nao escolhe nada...
    relogio.passar(esferas.TEMPO_DO_PEDIDO - 1)
    assert cacada.visao("id-Carla", "Carla")["pedido"]["segundos"] == 1
    relogio.passar(1)                                      # ...e depois de 30 s vale o primeiro
    assert pontos(cacada)["Carla"] == 7 + 2 + 1 + 3
    assert cacada.visao("id-Carla", "Carla")["pedido"]["escolhido"] == 1
    assert avisos[-1] == "🎁 Pedido de Carla: +3 pontos na caçada para mim (o tempo acabou e valeu o 1º)"


# ---------------- estados e tempo ----------------

def test_pausar_retomar_encerrar_nova():
    cacada, relogio, avisos = nova_cacada(("Ana",), minutos=10)
    assert cacada.instantaneo()["tempo_restante"] == 600
    relogio.passar(60)
    cacada.pausar()
    erro = levanta(esferas.CacadaParada, resgatar, cacada, relogio, "Ana", codigo(cacada, "Ana", 2))
    assert erro.status == 409 and str(erro) == "A caçada está pausada pelo professor ⏸"
    assert cacada.grito(1, "KAMEHAMEHA")["ok"] is False
    relogio.passar(300)                                    # o tempo parado nao conta
    assert cacada.instantaneo()["tempo_restante"] == 540
    cacada.retomar()
    relogio.passar(40)
    assert cacada.instantaneo()["tempo_restante"] == 500
    segredo, numero = cacada.segredo, cacada.numeros["id-Ana"]
    cacada.encerrar()
    assert cacada.instantaneo()["estado"] == "encerrada" and avisos[-1].startswith("🏁 Fim da Caça às Esferas!")
    assert "terminou" in str(levanta(esferas.CacadaParada, cacada.codigo_para, numero, 2))
    cacada.nova()
    assert cacada.estado == "aguardando" and cacada.segredo != segredo and cacada.cacadores == {}
    assert cacada.visao("id-Ana", "Ana")["numero"] == numero         # o numero continua o mesmo
    erro = levanta(esferas.CacadaParada, cacada.codigo_para, numero, 2)
    assert str(erro) == "A caçada ainda não começou 🐉"


def test_fim_pelo_tempo():
    cacada, relogio, _ = nova_cacada(("Ana",), minutos=1)
    relogio.passar(59)
    assert cacada.instantaneo()["estado"] == "ativa"
    relogio.passar(1)
    assert cacada.instantaneo()["estado"] == "encerrada"
    assert any(e["tipo"] == "fim" and e["motivo"] == "tempo" for e in cacada.eventos_depois(0))
    assert cacada.visao("id-Novo", "Novo")["esferas"] == []         # quem chega depois do fim nao entra
    assert len(cacada.cacadores) == 1


def test_dicas_extras_e_avisos_cabem_no_chat():
    for esfera in esferas.ESFERAS.values():                # o chat corta em 200 caracteres
        assert len(esferas.preencher(esfera["extra"], "255.255.255.255:65535", "SEU_NUMERO")) <= 200
    nome_comprido = "X" * 30
    cacada, relogio, avisos = nova_cacada(("Ana", nome_comprido))
    texto = cacada.dica_extra(6, "192.168.0.10:8000")
    assert avisos[-1] == texto and "KAMEHAMEHA" in texto
    visao = cacada.visao("id-Ana", "Ana")
    assert visao["grito_direto"] is True and visao["dica"]["extra"] == ""   # a dica atual dela e a 2
    cacada.dica_extra(2, "192.168.0.10:8000")
    assert "http://192.168.0.10:8000" in cacada.visao("id-Ana", "Ana", "192.168.0.10:8000")["dica"]["extra"]
    completar(cacada, relogio, nome_comprido)
    relogio.passar(esferas.TEMPO_DO_PEDIDO)
    cacada.encerrar()
    assert all(len(aviso) <= 200 for aviso in avisos)


# ---------------- grito (UDP) ----------------

def test_mensagens_do_grito():
    assert esferas.ler_grito(esferas.montar_grito(7, "KAMEHAMEHA")) == (7, "KAMEHAMEHA")
    for lixo in (b"DRAGONBALLDEX?", b"DBDEX-ESFERA abc", b"DBDEX-ESFERA \xff\xfe", "DBDEX-ESFERA ²".encode(),
                 b"DBDEX-ESFERA ", b"", b"DBDEX-ESFERA 1234567 X"):
        assert esferas.ler_grito(lixo) is None, lixo
    resposta = esferas.montar_resposta_grito({"ok": True, "codigo": "ESF-AAAAA"})
    assert esferas.ler_resposta_grito(resposta) == {"ok": True, "codigo": "ESF-AAAAA"}
    assert esferas.ler_grito(resposta) is None             # o servidor nao confunde resposta com grito
    try:                                                   # um app 2.2 que recebesse isso ignoraria:
        json.loads(resposta.decode("utf-8"))               # ele faz json.loads e pula o que der ValueError
        raise AssertionError("a resposta do grito nao pode ser JSON puro")
    except ValueError:
        pass


def test_grito_na_cacada():
    cacada, relogio, _ = nova_cacada()
    numero = cacada.numeros["id-Ana"]
    assert cacada.grito(numero, "hadouken")["ok"] is False
    assert cacada.grito(numero, "Kame-hame-ha!") == {"ok": True, "codigo": codigo(cacada, "Ana", 6),
                                                       "mensagem": "O servidor ouviu o seu grito e respondeu só "
                                                                   "para você! 📡"}
    assert cacada.grito(99, "KAMEHAMEHA")["ok"] is False
    gritos = [e for e in cacada.eventos_depois(0) if e["tipo"] == "grito"]
    assert len(gritos) == 1                                # 2 gritos seguidos = 1 aviso no telao
    relogio.passar(esferas.INTERVALO_DO_GRITO)
    cacada.grito(numero, "KAMEHAMEHA")
    assert len([e for e in cacada.eventos_depois(0) if e["tipo"] == "grito"]) == 2


# ---------------- resultado ----------------

def test_csv_do_resultado():
    cacada, relogio, _ = nova_cacada(("Ana", "Beto"))
    completar(cacada, relogio, "Ana")
    cacada.escolher_pedido("id-Ana", "Ana", 3)
    cacada.encerrar()
    caminho = cacada.salvar_csv(Path(tempfile.mkdtemp()))
    linhas = caminho.read_text(encoding="utf-8-sig").splitlines()
    assert caminho.name.startswith("cacada_") and caminho.suffix == ".csv"
    assert linhas[0].startswith("posicao;aluno;numero;esferas;esfera_1;")
    ana = linhas[1].split(";")
    assert ana[:4] == ["1", "Ana", "1", "7"] and all(ana[4:11]) and ana[-1] == str(7 + 5)
    assert linhas[2].split(";")[:4] == ["2", "Beto", "2", "1"]
    assert cacada.instantaneo()["resultado_salvo"] == str(caminho)
