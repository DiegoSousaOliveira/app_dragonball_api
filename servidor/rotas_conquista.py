"""
As rotas da Conquista de Territorios. O roteador (rotas.py) so encaminha para ca o que comeca com /conquista/
e as lutas "cq-..." de /turma/partida/: nenhuma rota antiga passa por este arquivo.

  GET  /conquista/estado?depois=<id>        o mapa, os donos, os escudos, o ranking e os eventos novos (polling)
                                            200 com a Conquista valendo; 409 (com os mesmos dados) se parada
  POST /conquista/guardiao  {"personagem"}  escolher o Guardiao dos meus planetas (429 se trocar rapido demais)
  POST /conquista/invadir   {"territorio", "personagem"}   -> {"partida": "cq-..."}
                                            403 o planeta e seu · 404 nao existe · 409 ocupado/escudo/parada · 429 espera
  GET  /turma/partida/cq-...                a luta (a MESMA rota dos duelos) + POST .../transformar e .../desistir
Os controles do professor (iniciar, pausar, encerrar) NAO tem rota: ficam so no painel.
"""

import json

from servidor import espelho as esp
from servidor.conquista import ErroDaConquista
from servidor.placar import DadoInvalido

JSON = "application/json; charset=utf-8"


def _json(dados, status=200):
    return status, json.dumps(dados, ensure_ascii=False).encode("utf-8"), JSON, {"Cache-Control": "no-store"}


def _erro(status, mensagem):
    return _json({"statusCode": status, "message": mensagem}, status)


def _quem(app, cabecalhos):
    """(id, nome) do aluno pelo X-Jogador (DadoInvalido -> 400 se ele nao entrou na sala)."""
    jogador = (cabecalhos.get("X-Jogador") or "").strip()[:20]
    if not jogador:
        raise DadoInvalido("Entre na sala pelo app (falta o cabeçalho X-Jogador).")
    dados = app.sala.jogador(jogador)
    return dados["id"], dados["nome"]


def _numero(params, nome):
    texto = (params.get(nome) or "").strip()
    return int(texto) if texto.isascii() and texto.isdigit() and len(texto) < 9 else 0


def atender(app, metodo, caminho, params, cabecalhos, ler_corpo):
    """Atende um pedido /conquista/... e devolve (status, corpo, tipo, cabecalhos)."""
    try:
        if (metodo, caminho) == ("GET", "/conquista/estado"):
            visao = app.conquista.visao(*_quem(app, cabecalhos), depois=_numero(params, "depois"))
            if visao["estado"] == "ativa":
                return _json(visao)
            return _json(dict(visao, statusCode=409, message=visao["mensagem"]), 409)
        if (metodo, caminho) == ("POST", "/conquista/guardiao"):
            dados = ler_corpo()
            return _json(app.conquista.escolher_guardiao(*_quem(app, cabecalhos), dados.get("personagem")))
        if (metodo, caminho) == ("POST", "/conquista/invadir"):
            dados = ler_corpo()
            return _json(app.conquista.invadir(*_quem(app, cabecalhos), dados.get("territorio"),
                                               dados.get("personagem")))
        return _erro(404, "Rota nao encontrada.")
    except ErroDaConquista as problema:
        return _erro(problema.status, str(problema))


def eh_luta_da_conquista(id_partida):
    return id_partida.startswith("cq-")


def partida(app, metodo, id_partida, acao, jogador, host):
    """/turma/partida/cq-...[/acao]: a luta de uma invasao, no mesmo formato dos duelos."""
    try:
        if metodo == "GET" and not acao:
            estado = app.conquista.estado_da_partida(jogador, id_partida)
            return _json(esp.reescrever_imagens(estado, f"http://{host}/imagens/"))
        if metodo == "POST" and acao == "transformar":
            return _json(app.conquista.transformar(jogador, id_partida))
        if metodo == "POST" and acao == "desistir":
            return _json(app.conquista.desistir(jogador, id_partida))
        return _erro(404, "Rota nao encontrada.")
    except ErroDaConquista as problema:
        return _erro(problema.status, str(problema))


def iniciar_conquista(app, minutos=None, **opcoes):
    """Botao "Iniciar" do painel: quem esta online na sala ganha um planeta."""
    online = [(a["id"], a["nome"]) for a in app.sala.visao_do_professor()["alunos"] if a["estado"] != "ausente"]
    return app.conquista.iniciar(online, minutos, **opcoes)

