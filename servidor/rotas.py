"""
O HTTP do servidor: recebe cada pedido, decide quem atende (rota) e devolve a resposta.

Rotas:
  GET  /                         pagina simples (para testar no navegador)
  GET  /api/characters[/<id>]    personagens (mesmo formato da dragonball-api)
  GET  /api/planets[/<id>]       planetas
  GET  /api/transformations      transformacoes
  GET  /imagens/<caminho>        as fotos
  GET  /turma/ping               "sou um servidor Dragon Ball Dex"
  GET  /turma/placar             Hall da Fama, recordes do quiz, ultimas batalhas
  POST /turma/entrar             {"nome": ...}
  POST /turma/batalha            {"vencedor", "perdedor", "rodadas", "metrica"}
  POST /turma/quiz               {"pontos", "rodadas"}            (treino contra o computador)
  GET  /turma/sala               quem esta online, desafios recebidos/enviados, partida atual
  POST /turma/desafiar           {"para", "tipo": "batalha"|"quiz", "personagem", "metrica", "rodadas"}
  POST /turma/responder          {"desafio", "aceitar", "personagem"}
  POST /turma/cancelar           {"desafio"}
  GET  /turma/partida/<id>       estado do duelo (a batalha avanca sozinha no servidor)
  POST /turma/partida/<id>/transformar | /progresso {"rodada","pontos","terminou"} | /desistir
  GET  /chat?depois=<id>&versao=<v>   mensagens novas do chat
  POST /chat                     {"texto"}   (403 se o chat estiver fechado ou o aluno bloqueado)
  GET|POST /esferas/...          Caca as Esferas (tudo em servidor/rotas_esferas.py)
O aluno se identifica pelo cabecalho X-Jogador (recebido em /turma/entrar).
Os controles do professor (fechar o chat, bloquear, apagar) NAO tem rota: ficam so no painel.
"""

import json
import time
import traceback
from http.server import BaseHTTPRequestHandler
from urllib.parse import parse_qsl, urlsplit

from core import api
from servidor import espelho as esp
from servidor import rotas_esferas
from servidor.chat import Proibido
from servidor.placar import DadoInvalido

VERSAO = "2.2"
TAMANHO_MAXIMO_DO_CORPO = 10_000         # bytes: ninguem precisa mandar mais que isso


class Resposta:
    def __init__(self, status, corpo=b"", tipo="application/json; charset=utf-8", cabecalhos=None):
        self.status = status
        self.corpo = corpo
        self.tipo = tipo
        self.cabecalhos = cabecalhos or {}


def json_resposta(dados, status=200):
    corpo = json.dumps(dados, ensure_ascii=False).encode("utf-8")
    return Resposta(status, corpo)


def erro(status, mensagem):
    """Erros no mesmo estilo da dragonball-api: {"statusCode": 404, "message": "..."}."""
    return json_resposta({"statusCode": status, "message": mensagem}, status)


PAGINA_INICIAL = """<!doctype html><html lang="pt-br"><head><meta charset="utf-8">
<title>Servidor Dragon Ball Dex</title></head>
<body style="font-family:sans-serif;background:#1E1F22;color:#fff;padding:24px">
<h1 style="color:#FAC02D">&#128009; Servidor Dragon Ball Dex esta funcionando!</h1>
<p>Este e o servidor do professor. Experimente:</p>
<ul>
<li><a style="color:#FAC02D" href="/api/characters">/api/characters</a> (10 por pagina)</li>
<li><a style="color:#FAC02D" href="/api/characters?race=Saiyan">/api/characters?race=Saiyan</a></li>
<li><a style="color:#FAC02D" href="/api/characters/1">/api/characters/1</a></li>
<li><a style="color:#FAC02D" href="/api/planets">/api/planets</a></li>
<li><a style="color:#FAC02D" href="/turma/placar">/turma/placar</a></li>
</ul></body></html>"""


# ----------------------------------------------------------------------
# As rotas
# ----------------------------------------------------------------------

def rota_api(app, caminho, params, host):
    """/api/... : igual a dragonball-api, mas com as imagens apontando para este servidor."""
    partes = caminho.strip("/").split("/")          # ["api", "characters", "1"]
    if len(partes) < 2 or len(partes) > 3:
        return erro(404, "Rota nao encontrada.")
    recurso = partes[1]
    url_da_lista = f"http://{host}/api/{recurso}"
    base_imagens = f"http://{host}/imagens/"
    if recurso == "transformations":
        transformacoes = app.espelho.transformacoes()
        if len(partes) == 2:
            return json_resposta(esp.reescrever_imagens(transformacoes, base_imagens))
        achada = next((t for t in transformacoes if str(t["id"]) == partes[2]), None)
        if achada is None:
            return erro(404, f"Nenhuma transformacao com o id {partes[2]}.")
        return json_resposta(esp.reescrever_imagens(achada, base_imagens))
    if recurso == "characters":
        lista, detalhar, filtros = app.espelho.personagens, app.espelho.detalhe_personagem, esp.FILTROS_PERSONAGEM
    elif recurso == "planets":
        lista, detalhar, filtros = app.espelho.planetas, app.espelho.detalhe_planeta, esp.FILTROS_PLANETA
    else:
        return erro(404, "Rota nao encontrada.")
    if len(partes) == 3:
        if not partes[2].isdigit():
            return erro(400, "O id precisa ser um numero.")
        detalhe = detalhar(int(partes[2]))
        if detalhe is None:
            return erro(404, f"Nada encontrado com o id {partes[2]}.")
        return json_resposta(esp.reescrever_imagens(detalhe, base_imagens))
    itens = lista()
    if esp.tem_filtro(params, filtros):
        resposta = esp.filtrar(itens, params, filtros)          # com filtro: lista pura (como a original)
    else:
        resposta = esp.paginar(itens, params, url_da_lista)
    return json_resposta(esp.reescrever_imagens(resposta, base_imagens))


def rota_imagem(app, caminho):
    arquivo, tipo = app.espelho.arquivo_de_imagem(caminho[len("/imagens/"):])
    if arquivo is None:
        return erro(404, "Imagem nao encontrada.")
    return Resposta(200, arquivo.read_bytes(), tipo, {"Cache-Control": "max-age=86400"})


def rota_partida(app, metodo, caminho, dados, jogador, host):
    """/turma/partida/<id>[/acao]"""
    partes = caminho.strip("/").split("/")          # ["turma", "partida", "<id>", "transformar"]
    id_partida = partes[2] if len(partes) > 2 else ""
    acao = partes[3] if len(partes) > 3 else ""
    if metodo == "GET" and not acao:
        estado = app.sala.estado_da_partida(jogador, id_partida)
        return json_resposta(esp.reescrever_imagens(estado, f"http://{host}/imagens/"))
    if metodo == "POST" and acao == "transformar":
        return json_resposta(app.sala.transformar(jogador, id_partida))
    if metodo == "POST" and acao == "progresso":
        return json_resposta(app.sala.progresso(jogador, id_partida, dados))
    if metodo == "POST" and acao == "desistir":
        return json_resposta(app.sala.desistir(jogador, id_partida))
    return erro(404, "Rota nao encontrada.")


def rota_get(app, caminho, params, host, jogador=""):
    if caminho in ("", "/"):
        pagina = PAGINA_INICIAL.replace("</ul>", "</ul>" + rotas_esferas.link_da_area(app))   # "" sem cacada
        return Resposta(200, pagina.encode("utf-8"), "text/html; charset=utf-8")
    if caminho == "/turma/ping":
        return json_resposta({"servico": "Dragon Ball Dex", "versao": VERSAO, "nome": app.nome})
    if caminho == "/turma/placar":
        dados = app.placar.resumo()
        dados["alunos"] = [{"nome": a["nome"] or a["ip"], "online": a["online"]}
                           for a in app.monitor.instantaneo()["alunos"]]
        return json_resposta(dados)
    if caminho == "/turma/sala":
        dados = app.sala.visao(jogador)
        dados["chat"] = app.chat.resumo(jogador)
        return json_resposta(dados)
    if caminho == "/chat":
        app.sala.jogador(jogador)                         # so quem entrou na sala le o chat
        depois = int(params["depois"]) if params.get("depois", "").isdigit() else 0
        versao = int(params["versao"]) if params.get("versao", "").isdigit() else None
        return json_resposta(app.chat.ler(jogador, depois, versao))
    if caminho.startswith("/turma/partida/"):
        return rota_partida(app, "GET", caminho, {}, jogador, host)
    if caminho.startswith("/imagens/"):
        return rota_imagem(app, caminho)
    if caminho.startswith("/api/"):
        return rota_api(app, caminho, params, host)
    return erro(404, "Rota nao encontrada.")


def rota_post(app, caminho, dados, ip, aluno, jogador="", host=""):
    if caminho == "/turma/entrar":
        nome = str(dados.get("nome", "")).strip()[:30]
        app.monitor.aluno_entrou(ip, nome)
        novo = app.sala.entrar(nome, ip)
        return json_resposta({"ok": True, "id": novo["id"], "mensagem": f"Bem-vindo(a), {novo['nome']}!"})
    if caminho == "/chat":
        return json_resposta(app.chat.enviar(app.sala.jogador(jogador), dados.get("texto")), 201)
    if caminho == "/turma/desafiar":
        return json_resposta(app.sala.desafiar(jogador, dados), 201)
    if caminho == "/turma/responder":
        return json_resposta(app.sala.responder(jogador, dados))
    if caminho == "/turma/cancelar":
        return json_resposta(app.sala.cancelar(jogador, dados.get("desafio")))
    if caminho.startswith("/turma/partida/"):
        return rota_partida(app, "POST", caminho, dados, jogador, host)
    if caminho == "/turma/batalha":
        return json_resposta(app.placar.registrar_batalha(aluno, dados), 201)
    if caminho == "/turma/quiz":
        return json_resposta(app.placar.registrar_quiz(aluno, dados), 201)
    return erro(404, "Rota nao encontrada.")


# ----------------------------------------------------------------------
# O "atendente" de cada pedido
# ----------------------------------------------------------------------

class TratadorDragonBall(BaseHTTPRequestHandler):
    # HTTP/1.1 permite manter a conexao aberta (keep-alive): a Session do aluno fica bem rapida
    protocol_version = "HTTP/1.1"
    server_version = f"DragonBallDexServidor/{VERSAO}"
    timeout = 30                      # conexao parada por 30 s e fechada

    def do_GET(self):
        self._atender("GET")

    def do_POST(self):
        self._atender("POST")

    def log_message(self, formato, *args):
        pass                           # o painel mostra os pedidos; nao precisa poluir o terminal

    def _ler_corpo_json(self):
        tamanho = int(self.headers.get("Content-Length") or 0)
        if tamanho > TAMANHO_MAXIMO_DO_CORPO:
            raise DadoInvalido("Corpo grande demais.")
        bruto = self.rfile.read(tamanho) if tamanho else b"{}"
        try:
            dados = json.loads(bruto.decode("utf-8") or "{}")
        except ValueError:
            raise DadoInvalido("O corpo precisa ser JSON.")
        if not isinstance(dados, dict):
            raise DadoInvalido("O corpo precisa ser um objeto JSON.")
        return dados

    def _atender(self, metodo):
        inicio = time.perf_counter()
        app = self.server.app
        partes = urlsplit(self.path)
        params = dict(parse_qsl(partes.query))
        ip = self.client_address[0]
        aluno = (self.headers.get("X-Aluno") or "").strip()[:40]
        jogador = (self.headers.get("X-Jogador") or "").strip()[:20]
        host = self.headers.get("Host") or f"{app.enderecos()[0]}"
        try:
            if partes.path.startswith("/esferas/"):        # Caca as Esferas: servidor/rotas_esferas.py
                resposta = Resposta(*rotas_esferas.atender(app, metodo, partes.path, params, self.headers,
                                                           self._ler_corpo_json))
            elif metodo == "GET":
                resposta = rota_get(app, partes.path, params, host, jogador)
            else:
                resposta = rota_post(app, partes.path, self._ler_corpo_json(), ip, aluno, jogador, host)
        except DadoInvalido as problema:
            resposta = erro(400, str(problema))
        except Proibido as problema:
            resposta = erro(403, str(problema))
        except api.ErroDeApi as problema:
            resposta = erro(503, f"Dados indisponiveis: {problema}")
        except Exception:
            traceback.print_exc()
            resposta = erro(500, "Erro interno do servidor.")
        self._enviar(resposta)
        ms = int((time.perf_counter() - inicio) * 1000)
        app.monitor.registrar(ip, aluno, metodo, self.path, resposta.status, ms, len(resposta.corpo))

    def _enviar(self, resposta):
        try:
            self.send_response(resposta.status)
            self.send_header("Content-Type", resposta.tipo)
            self.send_header("Content-Length", str(len(resposta.corpo)))
            for nome, valor in resposta.cabecalhos.items():
                self.send_header(nome, valor)
            self.end_headers()
            self.wfile.write(resposta.corpo)
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
            pass                       # o aluno fechou o programa no meio da resposta
