"""
As rotas do Grito de Guerra. O roteador (rotas.py) so encaminha para ca o que comeca com /gritos/.

  GET  /gritos/meu                      o meu grito (frase, audio, se e o padrao, se estou bloqueado)
  POST /gritos/meu  {"frase", "url"}    trocar (o SERVIDOR baixa a URL)  ·  {"padrao": true} volta ao padrao
                                        400 URL invalida/YouTube · 403 SSRF ou bloqueado pelo professor
                                        413 grande demais · 415 nao e audio · 429 troca rapida · 502 sem internet
  POST /gritos/audio?frase=...          um audio do PC do aluno: o ARQUIVO INTEIRO vai no corpo do pedido
                                        (Content-Type: audio/mpeg...; ate 500 KB). 413 · 415 · 403 · 429
  GET  /gritos/eventos?depois=<id>      eventos de som novos + lista de audios para pre-carregar
  GET  /gritos/<hash>.mp3|wav|ogg       o audio (e /gritos/padrao.wav, o som padrao gerado pelo programa)
O bloqueio NAO tem rota: fica so no painel (aba 📣 Gritos).
"""

import json

from core.grito_padrao import ID_DO_PADRAO, gerar_wav
from servidor import baixar_audio
from servidor.gritos import TIPOS, ErroDoGrito
from servidor.rotas_conquista import _quem

JSON = "application/json; charset=utf-8"


def _json(dados, status=200):
    return status, json.dumps(dados, ensure_ascii=False).encode("utf-8"), JSON, {"Cache-Control": "no-store"}


def _erro(status, mensagem):
    return _json({"statusCode": status, "message": mensagem}, status)


def atender(app, metodo, caminho, params, cabecalhos, ler_corpo, ler_bruto=None):
    """ler_corpo() le o JSON; ler_bruto(limite) le o corpo do jeito que veio (o arquivo do grito)."""
    try:
        if (metodo, caminho) == ("POST", "/gritos/audio") and ler_bruto is not None:
            conteudo = ler_bruto(baixar_audio.LIMITE)       # primeiro le o corpo inteiro (413 se passar de 500 KB)
            return _json(app.gritos.trocar(*_quem(app, cabecalhos), frase=params.get("frase"), arquivo=conteudo))
        if (metodo, caminho) == ("GET", "/gritos/meu"):
            return _json(app.gritos.meu(*_quem(app, cabecalhos)))
        if (metodo, caminho) == ("POST", "/gritos/meu"):
            dados = ler_corpo()
            return _json(app.gritos.trocar(*_quem(app, cabecalhos), frase=dados.get("frase"), url=dados.get("url"),
                                           padrao=bool(dados.get("padrao"))))
        if (metodo, caminho) == ("GET", "/gritos/eventos"):
            depois = params.get("depois", "0")
            depois = int(depois) if depois.isascii() and depois.isdigit() and len(depois) < 9 else 0
            return _json(app.gritos.estado_para(_quem(app, cabecalhos)[0], depois))
        if metodo == "GET":
            nome = caminho[len("/gritos/"):]
            if nome == ID_DO_PADRAO:
                return 200, gerar_wav(), "audio/wav", {"Cache-Control": "max-age=86400"}
            arquivo = app.gritos.arquivo(nome)
            if arquivo is not None:
                return 200, arquivo.read_bytes(), TIPOS[nome.rsplit(".", 1)[1]], {"Cache-Control": "max-age=86400"}
        return _erro(404, "Rota nao encontrada.")
    except (ErroDoGrito, baixar_audio.ErroDoAudio) as problema:
        return _erro(problema.status, str(problema))


def novidades(app):
    """O campo "novidades" do /turma/sala: so existe com a Caça ou a Conquista valendo (desligado, o JSON fica
    igual ao da 2.3.2). Os apps comparam os numeros e, se mudou, pedem /gritos/eventos."""
    ativas = app.cacada.estado in ("ativa", "pausada") or app.conquista.estado in ("ativa", "pausada")
    if not ativas:
        return None
    return {"eventos": app.gritos.ultimo_evento, "gritos": app.gritos.versao}
