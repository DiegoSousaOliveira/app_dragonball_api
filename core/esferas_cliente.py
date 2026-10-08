"""O lado do aluno na Caca as Esferas: conversa com as rotas /esferas/ (HTTP) e grita na rede (UDP)."""

import socket
import time

import requests

from core import api, descoberta, esferas
from core.turma import SemServidor

TEMPO_LIMITE = 4          # segundos


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
