"""
O lado do app no MODO DEMONSTRACAO 🎓.

O painel do professor abre o app com --demo e passa duas coisas por VARIAVEL DE AMBIENTE (nao aparecem na linha
de comando): o token sorteado pelo servidor e o endereco 127.0.0.1:PORTA. O app manda o token no cabecalho X-Demo
de todo pedido. Sem o token (ex.: alguem rodando "DragonBallDex.exe --demo" na mao), o --demo nao faz nada.
"""

import os

from core import api

NOME = "Professor 🎓"                      # o nome do professor no mundo demo (o servidor ja deixa ele na sala)
VARIAVEL_TOKEN = "DBDEX_DEMO_TOKEN"
VARIAVEL_SERVIDOR = "DBDEX_DEMO_SERVIDOR"
CABECALHO = "X-Demo"


def ler_do_ambiente():
    """(token, endereco) que o painel passou, ou None. Tira as variaveis do ambiente: o que este app abrir depois
    nao herda o token."""
    token = os.environ.pop(VARIAVEL_TOKEN, "").strip()
    endereco = os.environ.pop(VARIAVEL_SERVIDOR, "").strip()
    if not token or not endereco:
        return None
    return token, endereco


def ambiente_para_o_app(token, endereco):
    """As variaveis que o painel passa para o app que ele abre."""
    return dict(os.environ, **{VARIAVEL_TOKEN: token, VARIAVEL_SERVIDOR: endereco})


def ativar(token):
    """Daqui para frente, todo pedido do app leva o token (inclusive os da tela Rede)."""
    api.sessao.headers[CABECALHO] = token
