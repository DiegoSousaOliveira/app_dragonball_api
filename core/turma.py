"""Conversa com as rotas /turma do servidor do professor (placar da sala)."""

import time

import requests

from core import api

TEMPO_LIMITE = 4          # segundos: na rede da sala as respostas chegam em milissegundos


class SemServidor(api.ErroDeApi):
    """O app nao esta conectado a um servidor do professor."""


def _url(caminho):
    endereco = api.endereco_do_servidor()
    if endereco is None:
        raise SemServidor("Conecte-se ao servidor do professor para usar o placar da turma.")
    return f"http://{endereco}{caminho}"


def _pedir(metodo, url, dados=None, timeout=TEMPO_LIMITE):
    """GET/POST com JSON, registrando no log da tela Rede. Erros viram ErroDeApi."""
    inicio = time.perf_counter()
    try:
        resposta = api.sessao.request(metodo, url, json=dados, timeout=timeout)
    except requests.RequestException:
        raise api.ApiForaDoAr("O servidor do professor nao respondeu.")
    ms = int((time.perf_counter() - inicio) * 1000)
    api.registrar(url, resposta.status_code, ms, len(resposta.content),
                  resposta.headers.get("Content-Type", "-"), "rede", metodo)
    if resposta.status_code >= 400:
        try:
            mensagem = resposta.json().get("message", "")
        except ValueError:
            mensagem = ""
        raise api.ErroDeApi(mensagem or f"O servidor recusou o pedido (erro {resposta.status_code}).")
    return resposta.json()


def verificar_servidor(endereco, timeout=3):
    """Testa se existe um servidor Dragon Ball Dex em 'endereco' ('192.168.0.10:8000').
    Devolve as informacoes dele (nome, versao...) ou levanta ErroDeApi."""
    resposta = _pedir("GET", f"http://{endereco}/turma/ping", timeout=timeout)
    if resposta.get("servico") != "Dragon Ball Dex":
        raise api.ErroDeApi("Esse endereco respondeu, mas nao e um servidor Dragon Ball Dex.")
    return resposta


def entrar(nome):
    """Avisa o servidor que este aluno chegou. O servidor devolve um codigo (id) que vai em todo
    pedido seguinte (cabecalho X-Jogador): e assim que ele sabe quem e quem na sala."""
    resposta = _pedir("POST", _url("/turma/entrar"), {"nome": nome})
    api.sessao.headers["X-Jogador"] = resposta["id"]
    return resposta


def meu_id():
    return api.sessao.headers.get("X-Jogador")


# ---------------- duelos entre alunos ----------------

def sala():
    """{'voce', 'jogadores': [{id, nome, estado, voce}], 'recebidos': [...], 'enviado', 'partida'}"""
    return _pedir("GET", _url("/turma/sala"))


def desafiar(id_adversario, tipo, **opcoes):
    """tipo 'batalha' (opcoes: personagem=id, metrica) ou 'quiz' (opcoes: rodadas)."""
    return _pedir("POST", _url("/turma/desafiar"), dict(opcoes, para=id_adversario, tipo=tipo))


def responder(id_desafio, aceitar, **opcoes):
    return _pedir("POST", _url("/turma/responder"), dict(opcoes, desafio=id_desafio, aceitar=aceitar))


def cancelar(id_desafio):
    return _pedir("POST", _url("/turma/cancelar"), {"desafio": id_desafio})


def partida(id_partida):
    return _pedir("GET", _url(f"/turma/partida/{id_partida}"))


def transformar(id_partida):
    return _pedir("POST", _url(f"/turma/partida/{id_partida}/transformar"))


def enviar_progresso(id_partida, rodada, pontos, terminou=False):
    return _pedir("POST", _url(f"/turma/partida/{id_partida}/progresso"),
                  {"rodada": rodada, "pontos": pontos, "terminou": terminou})


def desistir(id_partida):
    return _pedir("POST", _url(f"/turma/partida/{id_partida}/desistir"))


def enviar_batalha(resultado, metrica):
    return _pedir("POST", _url("/turma/batalha"), {
        "vencedor": resultado["vencedor"],
        "perdedor": resultado["perdedor"],
        "rodadas": resultado["rodadas"],
        "metrica": metrica,
    })


def enviar_quiz(pontos, rodadas):
    return _pedir("POST", _url("/turma/quiz"), {"pontos": pontos, "rodadas": rodadas})


def placar():
    """{'classificacao': [...], 'hall_da_fama': [...], 'recordes_quiz': [...], 'ultimos_duelos': [...], ...}"""
    return _pedir("GET", _url("/turma/placar"))


# ---------------- chat da turma ----------------

def ler_chat(depois=0, versao=None):
    """{'versao', 'todas', 'mensagens': [{id, hora, autor, texto, tipo, minha}], 'liberado', 'bloqueado'}"""
    caminho = f"/chat?depois={depois}" + (f"&versao={versao}" if versao is not None else "")
    return _pedir("GET", _url(caminho))


def enviar_chat(texto):
    return _pedir("POST", _url("/chat"), {"texto": texto})
