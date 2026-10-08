"""O lado do aluno na Conquista de Territorios: conversa com as rotas /conquista/ (HTTP)."""

from core import api
from core.esferas_cliente import Recusado, _pedir


class SemConquista(api.ErroDeApi):
    """O servidor e de uma versao sem a Conquista (respondeu 404)."""


def _resultado(resposta):
    """200 -> os dados; qualquer outro -> Recusado com a mensagem do servidor (no invadir, 404 = planeta que nao
    existe, e nao "servidor sem Conquista": por isso so o estado() trata o 404 como servidor antigo)."""
    if resposta.status_code == 200:
        return resposta.json()
    try:
        mensagem = resposta.json().get("message", "")
    except ValueError:
        mensagem = ""
    raise Recusado(mensagem or f"O servidor recusou (erro {resposta.status_code}).", resposta.status_code)


def estado(depois=0):
    """O mapa, o ranking e os eventos novos. Com a Conquista parada vem 409, mas com os dados juntos."""
    resposta = _pedir("GET", f"/conquista/estado?depois={int(depois)}")
    if resposta.status_code == 409:
        return resposta.json()
    if resposta.status_code == 404:
        raise SemConquista("Este servidor não tem a Conquista de Territórios.")
    return _resultado(resposta)


def escolher_guardiao(id_personagem):
    return _resultado(_pedir("POST", "/conquista/guardiao", {"personagem": id_personagem}))


def invadir(id_territorio, id_personagem):
    """Devolve {"partida": "cq-...", ...}: a luta e assistida pela rota de sempre (/turma/partida/<id>)."""
    return _resultado(_pedir("POST", "/conquista/invadir", {"territorio": id_territorio,
                                                             "personagem": id_personagem}))
