"""O lado do aluno na Caca as Esferas: conversa com as rotas /esferas/ (HTTP) e grita na rede (UDP)."""

import re
import socket
import time

import requests

from core import api, descoberta, esferas
from core.turma import SemServidor

TEMPO_LIMITE = 4          # segundos
CODIGO = re.compile(r"ESF-[A-Z0-9]{5}")


class SemCacada(api.ErroDeApi):
    """O servidor e de uma versao antiga, sem a Caca as Esferas (respondeu 404)."""


class Recusado(api.ErroDeApi):
    """O servidor recusou o pedido. 'status' diz o porque: 400 codigo errado, 403 de outro cacador,
    409 cacada parada, 429 rapido demais."""

    def __init__(self, mensagem, status):
        super().__init__(mensagem)
        self.status = status


def _pedir(metodo, caminho, dados=None):
    """GET/POST no servidor da sala, registrando no log da tela Rede (como o resto do app)."""
    endereco = api.endereco_do_servidor()
    if endereco is None:
        raise SemServidor("A caçada precisa do servidor da sala.")
    url = f"http://{endereco}{caminho}"
    inicio = time.perf_counter()
    try:
        resposta = api.sessao.request(metodo, url, json=dados, timeout=TEMPO_LIMITE)
    except requests.RequestException:
        raise api.ApiForaDoAr("O servidor do professor não respondeu.")
    ms = int((time.perf_counter() - inicio) * 1000)
    api.registrar(url, resposta.status_code, ms, len(resposta.content),
                  resposta.headers.get("Content-Type", "-"), "rede", metodo)
    return resposta


def _mensagem(resposta):
    try:
        return resposta.json().get("message", "")
    except ValueError:
        return ""


def _resultado(resposta):
    if resposta.status_code == 200:
        return resposta.json()
    if resposta.status_code == 404:
        raise SemCacada("Este servidor não tem a Caça às Esferas.")
    raise Recusado(_mensagem(resposta) or f"O servidor recusou (erro {resposta.status_code}).",
                   resposta.status_code)


def estado():
    """O que a tela Esferas mostra. Com a cacada parada o servidor responde 409, mas manda os dados juntos."""
    resposta = _pedir("GET", "/esferas/estado")
    if resposta.status_code == 409:
        return resposta.json()
    return _resultado(resposta)


def resgatar(codigo):
    return _resultado(_pedir("POST", "/esferas/resgatar", {"codigo": codigo}))


def pedir(opcao):
    """O pedido ao dragao: 1, 2 ou 3."""
    return _resultado(_pedir("POST", "/esferas/pedido", {"pedido": opcao}))


def ip_do_servidor():
    endereco = api.endereco_do_servidor()
    return endereco.rsplit(":", 1)[0] if endereco else None


def gritar(numero, palavra, direto=False, espera=1.5):
    """Grita na rede: um pacote UDP para TODOS os computadores (broadcast), na porta 50505.
    So o servidor responde, e so para quem gritou. direto=True manda so para o IP do servidor (unicast),
    para redes que bloqueiam broadcast. Devolve {"ok", "codigo" ou "mensagem", "ip"} ou None (ninguem respondeu)."""
    servidor = ip_do_servidor()
    alvos = [servidor] if direto and servidor else descoberta.enderecos_de_broadcast()
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    sock.settimeout(0.2)
    reserva = None
    try:
        mensagem = esferas.montar_grito(numero, palavra)
        for alvo in alvos:
            try:
                sock.sendto(mensagem, (alvo, descoberta.PORTA_DESCOBERTA))
            except OSError:
                pass
        limite = time.time() + espera
        while time.time() < limite:
            try:
                dados, (ip, _) = sock.recvfrom(2048)
            except socket.timeout:
                continue
            except OSError:
                break
            resposta = esferas.ler_resposta_grito(dados)
            if resposta is None:
                continue
            resposta["ip"] = ip
            if servidor is None or ip == servidor or ip.startswith("127."):
                return resposta                    # foi o NOSSO servidor que respondeu
            reserva = reserva or resposta          # outro servidor na rede: so se o nosso nao responder
    finally:
        sock.close()
    return reserva


# ---------------- o mapa do radar (esfera 4) ----------------
# O mapa e so um cliente mais amigavel da MESMA rota que o aluno pode abrir no navegador: cada clique vira
# exatamente o pedido GET /esferas/radar?cacador=7&x=5&y=5 (com a query string na mesma ordem).

FAIXAS = {esferas.temperatura(1): "fervendo", esferas.temperatura(3): "quente",
          esferas.temperatura(6): "morno", esferas.temperatura(7): "frio"}


def url_do_radar(numero, x, y):
    """O caminho com a query string, igualzinho ao que se digita no navegador."""
    return f"/esferas/radar?cacador={int(numero)}&x={int(x)}&y={int(y)}"


def ler_radar(texto):
    """A resposta do radar -> ("achou", "ESF-XXXXX") ou ("temperatura", "frio"|"morno"|"quente"|"fervendo")."""
    achado = CODIGO.search(texto or "")
    if achado:
        return "achou", achado.group(0)
    for inicio, faixa in FAIXAS.items():
        if (texto or "").startswith(inicio):
            return "temperatura", faixa
    return "erro", (texto or "").strip().splitlines()[0] if texto and texto.strip() else "Resposta estranha"


def escanear_radar(numero, x, y):
    """Faz a varredura numa casa. Devolve {"pedido", "status", "tipo", "valor"} (tipo: achou, temperatura, erro)."""
    caminho = url_do_radar(numero, x, y)
    resposta = _pedir("GET", caminho)
    tipo, valor = ler_radar(resposta.text) if resposta.status_code == 200 else ("erro", resposta.text.strip())
    return {"pedido": f"GET {caminho}", "status": resposta.status_code, "tipo": tipo, "valor": valor}


class HistoricoDoRadar:
    """As casas ja escaneadas e a temperatura de cada uma (o mapa pinta o "calor" se formando)."""

    def __init__(self):
        self.casas = {}              # (x, y) -> "frio" | "morno" | "quente" | "fervendo" | "achou"
        self.tentativas = 0

    def registrar(self, x, y, resultado):
        if resultado["tipo"] in ("temperatura", "achou"):
            self.tentativas += 1
            self.casas[(x, y)] = resultado["valor"] if resultado["tipo"] == "temperatura" else "achou"

    def faixa(self, x, y):
        return self.casas.get((x, y))
