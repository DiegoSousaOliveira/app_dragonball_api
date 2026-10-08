"""
As rotas da Caca as Esferas. O roteador antigo (rotas.py) so encaminha para ca o que comeca com /esferas/:
nenhuma rota antiga passa por este arquivo.

  GET  /esferas/estado                   a tela Esferas do app pergunta a cada 1,5 s (409 se a cacada esta parada)
  POST /esferas/resgatar  {"codigo"}     o aluno digitou um codigo
  POST /esferas/pedido    {"pedido"}     1, 2 ou 3 (depois de juntar as 7)
  GET  /esferas/navegador?cacador=7      esfera 2: so para navegadores (User-Agent)
  GET  /esferas/pista                    esfera 3: o codigo vem no cabecalho X-Esfera
  GET  /esferas/radar?cacador=7&x=5&y=5  esfera 4: query string (400 se faltar algo)
  GET  /esferas/caverna-<nome>           esfera 5: 404 com o codigo no corpo (so a caverna certa)
  GET  /esferas/terminal?cacador=7       esfera 7: so para o curl / PowerShell
  UDP  50505 "DBDEX-ESFERA 7 palavra"    esfera 6: o grito (ao_receber_udp)
O cacador e reconhecido pelo cabecalho X-Jogador (app) ou por ?cacador=<numero> (navegador e terminal).
Antes da largada (ou com a cacada pausada), todas as rotas respondem 409.
"""

import json
import unicodedata
from html import escape
from urllib.parse import unquote

from core import esferas
from servidor.placar import DadoInvalido

JSON = "application/json; charset=utf-8"
TEXTO = "text/plain; charset=utf-8"
HTML = "text/html; charset=utf-8"
SEM_CACHE = {"Cache-Control": "no-store"}       # depois de uma "Nova cacada" os codigos mudam
ROTAS_DO_APP = {("GET", "/esferas/estado"), ("POST", "/esferas/resgatar"), ("POST", "/esferas/pedido")}

ESTILO = "font-family:sans-serif;background:#1E1F22;color:#fff;padding:24px"
AMARELO = "color:#FAC02D"


# ----------------------------------------------------------------------
# Respostas: (status, corpo, tipo, cabecalhos). O rotas.py transforma em Resposta.
# ----------------------------------------------------------------------

def _resposta(status, corpo, tipo, cabecalhos=None):
    return status, corpo.encode("utf-8"), tipo, dict(SEM_CACHE, **(cabecalhos or {}))


def _json(dados, status=200):
    return _resposta(status, json.dumps(dados, ensure_ascii=False), JSON)


def _texto(texto, status=200, cabecalhos=None):
    return _resposta(status, texto.rstrip("\n") + "\n", TEXTO, cabecalhos)   # \n: o cmd pula linha no fim


def _pagina(miolo, status=200):
    return _resposta(status, f"""<!doctype html><html lang="pt-br"><head><meta charset="utf-8">
<title>Área do caçador</title></head><body style="{ESTILO}">
<h1 style="{AMARELO}">&#128009; Área do caçador</h1>
{miolo}
</body></html>""", HTML)


def _para_terminal(resposta):
    """O cmd do Windows mostra acentos e emoji errados: para o terminal, so letras sem acento."""
    status, corpo, tipo, cabecalhos = resposta
    if tipo != TEXTO:
        return resposta
    separado = unicodedata.normalize("NFD", corpo.decode("utf-8"))
    simples = "".join(c for c in separado if c.isascii())
    return status, simples.encode("ascii"), tipo, cabecalhos


# ----------------------------------------------------------------------
# Quem esta pedindo
# ----------------------------------------------------------------------

def _quem(app, cabecalhos):
    """(id, nome) do aluno pelo X-Jogador, ou None se o pedido nao veio do app."""
    jogador = (cabecalhos.get("X-Jogador") or "").strip()[:20]
    if not jogador:
        return None
    dados = app.sala.jogador(jogador)              # DadoInvalido (400) se ele nao entrou na sala
    return dados["id"], dados["nome"]


def _numero(app, cabecalhos, params):
    """O numero do cacador: pelo X-Jogador (app) ou pelo ?cacador=7 da URL (navegador, terminal)."""
    quem = _quem(app, cabecalhos)
    if quem is not None:
        return app.cacada.inscrever(*quem)
    texto = (params.get("cacador") or "").strip()
    if not (texto.isascii() and texto.isdigit()) or len(texto) > 6:
        raise esferas.ErroDaCacada("Diga quem você é: coloque ?cacador=SEU_NUMERO no fim do endereço. "
                                   "O seu número aparece na tela 🐉 Esferas do app.")
    return int(texto)


# ----------------------------------------------------------------------
# As rotas
# ----------------------------------------------------------------------

def _estado(app, cabecalhos, host):
    quem = _quem(app, cabecalhos)
    if quem is None:
        raise DadoInvalido("Entre na sala pelo app (falta o cabeçalho X-Jogador).")
    visao = app.cacada.visao(*quem, endereco=host)
    if visao["estado"] == "ativa":
        return _json(visao)
    return _json(dict(visao, statusCode=409, message=visao["mensagem"]), 409)   # parada: 409, mas com os dados


def _resgatar(app, cabecalhos, dados, host):
    quem = _quem(app, cabecalhos)
    if quem is None:
        raise DadoInvalido("Entre na sala pelo app (falta o cabeçalho X-Jogador).")
    visao = app.cacada.resgatar(*quem, dados.get("codigo"), endereco=host)
    resgate = visao["resgate"]
    if resgate["nova"]:                         # o grito de guerra de quem achou toca nos PCs (servidor/gritos.py)
        if resgate["esfera"] == 6:
            app.gritos.anunciar(quem[0], quem[1], "esfera6", f"{quem[1]} achou a esfera de 6 estrelas!", {quem[0]})
        if visao["posicao"] and len(visao["esferas"]) == len(esferas.ESFERAS):
            app.gritos.anunciar(quem[0], quem[1], "dragao", f"{quem[1]} invocou o dragão!", {quem[0]})
    return _json(visao)


def _pedido(app, cabecalhos, dados, host):
    quem = _quem(app, cabecalhos)
    if quem is None:
        raise DadoInvalido("Entre na sala pelo app (falta o cabeçalho X-Jogador).")
    return _json(app.cacada.escolher_pedido(*quem, dados.get("pedido"), endereco=host))


def _navegador(app, cabecalhos, params, user_agent):
    """Esfera 2: o servidor olha o User-Agent para saber QUEM esta pedindo."""
    if not esferas.eh_navegador(user_agent):
        return _texto("Só aceito visitas de navegadores. Eu sei quem você é pelo User-Agent!\n\n"
                      f"O seu User-Agent: {user_agent or '(nenhum)'}", 403)
    if "cacador" not in params and not cabecalhos.get("X-Jogador"):
        return _pagina("""<p>Bem-vindo(a), caçador(a)! Digite o seu número de caçador
(ele aparece na tela &#128009; Esferas do app):</p>
<form action="/esferas/navegador" method="get">
<input name="cacador" type="number" min="1" style="font-size:20px;width:120px" autofocus>
<button style="font-size:20px">Mostrar a minha esfera</button></form>""")
    numero = _numero(app, cabecalhos, params)
    codigo = app.cacada.codigo_para(numero, 2)
    return _pagina(f"""<p>Caçador {numero:02d}, você me visitou pelo <b>navegador</b>. Eu sei disso porque
todo navegador se apresenta no cabeçalho <code>User-Agent</code>:</p>
<p style="color:#B5B8BD"><code>{escape(user_agent)}</code></p>
<p>&#11088; A esfera de 2 estrelas é sua! Código:</p>
<p style="font-size:44px;font-weight:bold;{AMARELO}">{codigo}</p>
<p>Digite o código na tela &#128009; Esferas do app.</p>""")


def _pista(app, cabecalhos, params):
    """Esfera 3: o corpo nao tem nada; o codigo vai num CABECALHO da resposta."""
    numero = _numero(app, cabecalhos, params)
    codigo = app.cacada.codigo_para(numero, 3)
    return _texto("A esfera não está aqui... olhe com mais atenção 👀", 200, {"X-Esfera": codigo})


def _radar(app, cabecalhos, params, host):
    """Esfera 4: a query string. Sem parametros (ou com valores errados) -> 400 explicando como montar."""
    explicacao = ("O Radar do Dragão precisa de 3 informações na URL (a query string, tudo depois do ?):\n"
                  "  cacador = o seu número de caçador\n"
                  "  x = um número de 0 a 10\n"
                  "  y = um número de 0 a 10\n"
                  "O & separa uma informação da outra. Exemplo:\n"
                  f"  http://{host}/esferas/radar?cacador=7&x=5&y=5")
    coordenadas = []
    for nome in ("x", "y"):
        valor = (params.get(nome) or "").strip()
        if not (valor.isascii() and valor.isdigit()) or not 0 <= int(valor) <= esferas.LADO_DO_RADAR:
            problema = f"Falta o {nome}." if not valor else f"O {nome} precisa ser um número de 0 a 10."
            return _texto(f"400: pedido mal feito! {problema}\n\n{explicacao}", 400)
        coordenadas.append(int(valor))
    try:
        numero = _numero(app, cabecalhos, params)
    except esferas.ErroDaCacada:
        return _texto(f"400: pedido mal feito! Falta o cacador.\n\n{explicacao}", 400)
    x, y = coordenadas
    resultado = app.cacada.radar(numero, x, y)
    if resultado["achou"]:
        return _texto(f"📡 BIP BIP BIP! Você achou a esfera de 4 estrelas em x={x}, y={y}!\n\n"
                      f"Código: {resultado['codigo']}\n\nDigite o código na tela 🐉 Esferas do app.")
    return _texto(f"{resultado['temperatura']}   (você procurou em x={x}, y={y})\n\n"
                  "Mude o x e o y na URL e tente de novo.")


def _caverna(app, caminho, cabecalhos, params):
    """Esfera 5: SEMPRE 404 (nao encontrado)... mas a caverna certa tem o codigo no corpo."""
    nome = unquote(caminho[len("/esferas/caverna-"):])
    if not esferas.eh_a_caverna_certa(nome):
        return _texto("Caverna vazia. 🕳️", 404)
    numero = _numero(app, cabecalhos, params)
    codigo = app.cacada.codigo_para(numero, 5)
    return _texto("Caverna vazia... ou não? 💎\n\n"
                  "Lá no fundo, brilhando no escuro: a esfera de 5 estrelas!\n"
                  f"Código: {codigo}\n\nDigite o código na tela 🐉 Esferas do app.", 404)


def _terminal(app, cabecalhos, params, user_agent):
    """Esfera 7: so o curl (ou o PowerShell) recebe o codigo."""
    if not esferas.eh_terminal(user_agent):
        return _texto("Use o terminal, caçador! 💻\n\nO app e o navegador não valem aqui: abra o Prompt de "
                      "Comando (cmd) e use o curl.", 403)
    numero = _numero(app, cabecalhos, params)
    codigo = app.cacada.codigo_para(numero, 7)
    return _texto(f"Parabens, cacador {numero}! Voce achou a esfera de 7 estrelas pelo terminal.\n"
                  f"Codigo: {codigo}\n"
                  "Digite o codigo na tela Esferas do app.")


def atender(app, metodo, caminho, params, cabecalhos, ler_corpo):
    """Atende um pedido /esferas/... e devolve (status, corpo, tipo, cabecalhos).
    ler_corpo() le o JSON do POST (so e chamado quando precisa)."""
    host = cabecalhos.get("Host") or app.enderecos()[0]
    user_agent = cabecalhos.get("User-Agent") or ""
    do_app = (metodo, caminho) in ROTAS_DO_APP
    try:
        if (metodo, caminho) == ("GET", "/esferas/estado"):
            return _estado(app, cabecalhos, host)
        app.cacada.exigir_ativa()                      # antes da largada, pausada ou encerrada: 409
        if (metodo, caminho) == ("POST", "/esferas/resgatar"):
            resposta = _resgatar(app, cabecalhos, ler_corpo(), host)
        elif (metodo, caminho) == ("POST", "/esferas/pedido"):
            resposta = _pedido(app, cabecalhos, ler_corpo(), host)
        elif metodo != "GET":
            resposta = _json({"statusCode": 404, "message": "Rota nao encontrada."}, 404)
        elif caminho == "/esferas/navegador":
            resposta = _navegador(app, cabecalhos, params, user_agent)
        elif caminho == "/esferas/pista":
            resposta = _pista(app, cabecalhos, params)
        elif caminho == "/esferas/radar":
            resposta = _radar(app, cabecalhos, params, host)
        elif caminho.startswith("/esferas/caverna-"):
            resposta = _caverna(app, caminho, cabecalhos, params)
        elif caminho == "/esferas/terminal":
            resposta = _terminal(app, cabecalhos, params, user_agent)
        else:
            resposta = _json({"statusCode": 404, "message": "Rota nao encontrada."}, 404)
    except esferas.ErroDaCacada as problema:
        if do_app:
            resposta = _json({"statusCode": problema.status, "message": str(problema)}, problema.status)
        else:
            resposta = _texto(str(problema), problema.status)
    if esferas.eh_terminal(user_agent):
        resposta = _para_terminal(resposta)
    return resposta


# ----------------------------------------------------------------------
# Ganchos usados pelo resto do servidor
# ----------------------------------------------------------------------

def link_da_area(app):
    """O link discreto da pagina inicial (esfera 2). Sem cacada ativa: "" (a pagina fica igual a da 2.2)."""
    if app.cacada.estado != "ativa":
        return ""
    return ('<p style="margin-top:56px;font-size:12px"><a style="color:#5C5F66" href="/esferas/navegador">'
            '&#128009; Área do caçador</a></p>')


def ao_receber_udp(app, dados, remetente):
    """Chamado pela descoberta (porta 50505) para o que NAO e a pergunta "DRAGONBALLDEX?".
    Devolve os bytes da resposta (so para quem gritou) ou None para ignorar."""
    grito = esferas.ler_grito(dados)
    if grito is None:
        return None
    return esferas.montar_resposta_grito(app.cacada.grito(*grito))


def iniciar_cacada(app, minutos=None):
    """Botao "Iniciar cacada" do painel: quem esta online na sala ganha numero e a esfera 1."""
    online = [(a["id"], a["nome"]) for a in app.sala.visao_do_professor()["alunos"] if a["estado"] != "ausente"]
    app.cacada.iniciar(online, minutos)
