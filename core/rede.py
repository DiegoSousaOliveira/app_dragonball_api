"""
Ferramentas da tela "Rede" (o raio-X da conexao).
Aqui so medimos e devolvemos numeros; quem mostra e explica e a interface.
"""

import socket
import time
from urllib.parse import urlsplit

import requests

from core import api

ERROS_DE_PROPOSITO = [
    ("ID que nao existe", "/characters/99999"),
    ("Rota que nao existe", "/rota-que-nao-existe"),
    ("ID que nem e numero", "/characters/abc"),
    ("Transformacao que nao existe", "/transformations/999"),
]


def cabecalhos():
    """Os mesmos cabecalhos do app (inclusive o nome do aluno), para o painel do professor."""
    return dict(api.sessao.headers)


def host_da_fonte(base=None):
    """('192.168.0.10', 8000) ou ('dragonball-api.com', 443)."""
    partes = urlsplit(base or api.URL_BASE)
    porta = partes.port or (443 if partes.scheme == "https" else 80)
    return partes.hostname, porta


def anotar(resposta, ms):
    """Coloca a requisicao no log (o mesmo que a aba 'Pedidos' mostra)."""
    tipo = resposta.headers.get("Content-Type", "-")
    api.registrar(resposta.url, resposta.status_code, round(ms), len(resposta.content), tipo, "rede")


def requisicao_crua(caminho, params=None, timeout=api.TIMEOUT):
    """GET direto, SEM cache e sem esconder erros: para ver a resposta exatamente como ela vem.
    Erros de rede sobem como excecoes do requests."""
    inicio = time.perf_counter()
    resposta = requests.get(api.URL_BASE + caminho, params=params, headers=cabecalhos(), timeout=timeout)
    anotar(resposta, (time.perf_counter() - inicio) * 1000)
    return resposta


def medir_latencias(quantas, base=None, caminho="/planets", usar_sessao=True):
    """Faz 'quantas' requisicoes seguidas e devolve os tempos em milissegundos.
    usar_sessao=False: cada requests.get abre uma conexao NOVA (DNS + TCP (+ TLS) toda vez).
    usar_sessao=True: a Session reaproveita a mesma conexao (keep-alive)."""
    url = (base or api.URL_BASE) + caminho
    sessao = requests.Session()
    sessao.headers.update(cabecalhos())
    tempos = []
    try:
        for _ in range(quantas):
            inicio = time.perf_counter()
            if usar_sessao:
                resposta = sessao.get(url, timeout=api.TIMEOUT)
            else:
                resposta = requests.get(url, headers=cabecalhos(), timeout=api.TIMEOUT)
            ms = (time.perf_counter() - inicio) * 1000
            anotar(resposta, ms)
            tempos.append(ms)
    finally:
        sessao.close()
    return tempos


def resumo(tempos):
    """(minimo, media, maximo) de uma lista de tempos."""
    return min(tempos), sum(tempos) / len(tempos), max(tempos)


def descobrir_ip(host):
    """Pergunta ao DNS qual e o endereco IP de um nome. Devolve (ip, milissegundos).
    Se 'host' ja e um IP (servidor da sala), o DNS nem e consultado."""
    inicio = time.perf_counter()
    ip = socket.gethostbyname(host)
    return ip, (time.perf_counter() - inicio) * 1000


def provocar_timeout(segundos=0.001):
    """Pede uma resposta em 1 milissegundo (impossivel!). Devolve o nome do erro que acontece."""
    try:
        requests.get(api.URL_BASE + "/characters", headers=cabecalhos(), timeout=segundos)
    except requests.RequestException as erro:
        return type(erro).__name__
    return "nenhum erro (a rede esta MUITO rapida!)"
