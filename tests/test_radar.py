"""Testes do mapa do radar (esfera 4): o mapa do app e so um cliente mais amigavel da MESMA rota /esferas/radar."""

import random
import time

import requests

from core import api, esferas, esferas_cliente
from core.esferas import Cacada
from tests.test_rotas_esferas import CHROME, base, com_cacada, entrar, numero_de, servidor


def com_app_conectado(aluno, funcao):
    """Faz o 'app' (api.sessao) falar com o servidor de teste como este aluno, e desfaz no fim."""
    antes = api.URL_BASE
    try:
        api.usar_servidor(base()[len("http://"):])
        api.sessao.headers["X-Jogador"] = aluno["X-Jogador"]
        return funcao()
    finally:
        api.sessao.headers.pop("X-Jogador", None)
        api.URL_BASE = antes


def viu_o_pedido(caminho):
    """O servidor anota o pedido no monitor logo DEPOIS de responder: espera um instante."""
    for _ in range(50):
        if any(p["caminho"] == caminho for p in servidor().monitor.instantaneo()["pedidos"][-10:]):
            return True
        time.sleep(0.02)
    return False


def test_a_url_do_mapa_e_a_mesma_da_barra_de_endereco():
    assert esferas_cliente.url_do_radar(7, 5, 5) == "/esferas/radar?cacador=7&x=5&y=5"
    assert esferas_cliente.url_do_radar("07", 0, 10) == "/esferas/radar?cacador=7&x=0&y=10"


@com_cacada
def test_o_mapa_faz_o_mesmo_pedido_que_o_navegador():
    ana = entrar("Ana RD")
    numero = numero_de(ana)
    alvo_x, alvo_y = esferas.alvo_do_radar(servidor().cacada.segredo, numero)
    x, y = (alvo_x + 3) % 11, alvo_y                          # uma casa errada (3 passos ao lado)
    resultado = com_app_conectado(ana, lambda: esferas_cliente.escanear_radar(numero, x, y))
    manual = f"/esferas/radar?cacador={numero}&x={x}&y={y}"
    assert resultado["pedido"] == f"GET {manual}" and resultado["status"] == 200
    assert viu_o_pedido(manual)                               # o servidor viu a MESMA URL da barra de endereco
    pelo_navegador = requests.get(base() + manual, headers={"User-Agent": CHROME}, timeout=5).text
    assert esferas_cliente.ler_radar(pelo_navegador) == (resultado["tipo"], resultado["valor"])
    achou = com_app_conectado(ana, lambda: esferas_cliente.escanear_radar(numero, alvo_x, alvo_y))
    assert achou["tipo"] == "achou" and achou["valor"] == esferas.gerar_codigo(servidor().cacada.segredo, numero, 4)


@com_cacada
def test_a_rota_do_radar_continua_com_o_400():
    ana = entrar("Ana R4")
    numero = numero_de(ana)
    fora = com_app_conectado(ana, lambda: esferas_cliente.escanear_radar(numero, 11, 2))
    assert fora["status"] == 400 and fora["tipo"] == "erro"
    assert requests.get(base() + "/esferas/radar", headers={"User-Agent": CHROME}, timeout=5).status_code == 400


def test_ler_a_resposta_e_pintar_o_historico():
    for distancia, faixa in ((1, "fervendo"), (2, "quente"), (3, "quente"), (5, "morno"), (6, "morno"), (9, "frio")):
        texto = f"{esferas.temperatura(distancia)}   (você procurou em x=1, y=1)"
        assert esferas_cliente.ler_radar(texto) == ("temperatura", faixa), distancia
    assert esferas_cliente.ler_radar("BIP! Código: ESF-7KQ2M") == ("achou", "ESF-7KQ2M")
    assert esferas_cliente.ler_radar("400: pedido mal feito!")[0] == "erro"
    historico = esferas_cliente.HistoricoDoRadar()
    historico.registrar(1, 1, {"tipo": "temperatura", "valor": "frio"})
    historico.registrar(4, 4, {"tipo": "temperatura", "valor": "quente"})
    historico.registrar(9, 9, {"tipo": "erro", "valor": "409"})              # erro nao conta como tentativa
    historico.registrar(5, 4, {"tipo": "achou", "valor": "ESF-7KQ2M"})
    assert historico.tentativas == 3
    assert (historico.faixa(1, 1), historico.faixa(4, 4), historico.faixa(5, 4), historico.faixa(9, 9)) == \
        ("frio", "quente", "achou", None)


def test_interruptor_do_mapa_no_painel():
    cacada = Cacada(relogio=lambda: 1_000.0, avisar=None)
    cacada.iniciar([("id-Ana", "Ana")])
    numero = cacada.numeros["id-Ana"]
    for esfera in (2, 3):                                     # chega na esfera 4
        cacada.cacadores[numero].achadas[esfera] = 1_000.0
    visao = cacada.visao("id-Ana", "Ana", "127.0.0.1:8000")
    assert visao["dica"]["esfera"] == 4 and visao["radar_no_app"] is True and "mapa do radar" in visao["dica"]["texto"]
    cacada.radar_no_app = False                               # o professor desligou: so pela barra de endereco
    visao = cacada.visao("id-Ana", "Ana", "127.0.0.1:8000")
    assert visao["radar_no_app"] is False and "mapa" not in visao["dica"]["texto"]
    assert "http://127.0.0.1:8000/esferas/radar?cacador=" in visao["dica"]["texto"]
    cacada.nova()
    assert cacada.radar_no_app is False                       # a escolha do professor vale para a proxima caçada


def test_rodada_de_busca_do_simulador_continua_achando():
    """O simular_cacada.py usa as temperaturas para eliminar casas: confere que a estrategia sempre acha."""
    for semente in range(20):
        rng = random.Random(semente)
        alvo = (rng.randrange(11), rng.randrange(11))
        casas = [(x, y) for x in range(11) for y in range(11)]
        for tentativa in range(30):
            x, y = rng.choice(casas)
            distancia = abs(x - alvo[0]) + abs(y - alvo[1])
            if distancia == 0:
                break
            resposta = esferas.temperatura(distancia)
            casas = [(a, b) for a, b in casas if (a, b) != (x, y)
                     and resposta.startswith(esferas.temperatura(abs(a - x) + abs(b - y)))]
        assert distancia == 0, semente
