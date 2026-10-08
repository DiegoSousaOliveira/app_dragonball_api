"""O lado do aluno no Grito de Guerra: o meu grito, a troca (quem baixa a URL e o SERVIDOR), os eventos de som e o
cache dos audios da turma (assim o som toca na hora, sem esperar a rede)."""

import re

from core import api
from core.armazenamento import PASTA_CACHE
from core.esferas_cliente import Recusado, _pedir
from core.grito_padrao import ID_DO_PADRAO, gerar_wav

PASTA = PASTA_CACHE / "gritos"
NOME = re.compile(r"^[0-9a-f]{16}\.(mp3|wav|ogg)$")


def _resultado(resposta):
    if resposta.status_code == 200:
        return resposta.json()
    try:
        mensagem = resposta.json().get("message", "")
    except ValueError:
        mensagem = ""
    raise Recusado(mensagem or f"O servidor recusou (erro {resposta.status_code}).", resposta.status_code)


def meu():
    return _resultado(_pedir("GET", "/gritos/meu"))


def trocar(frase=None, url=None):
    """O servidor baixa a URL (pode demorar uns segundos) e confere tudo: SSRF, tamanho, formato."""
    dados = {}
    if frase is not None:
        dados["frase"] = frase
    if url:
        dados["url"] = url
    return _resultado(_pedir("POST", "/gritos/meu", dados))


def usar_padrao():
    return _resultado(_pedir("POST", "/gritos/meu", {"padrao": True}))


def eventos(depois=0):
    """{"eventos": [...], "ultimo", "versao", "audios": [...]}"""
    return _resultado(_pedir("GET", f"/gritos/eventos?depois={int(depois)}"))


def em_cache(nome):
    """Os bytes do audio, se ja estiverem no computador (sem usar a rede). O padrao e gerado aqui mesmo."""
    if nome == ID_DO_PADRAO:
        return gerar_wav()
    if not NOME.match(nome or ""):
        return None
    arquivo = PASTA / nome
    return arquivo.read_bytes() if arquivo.is_file() else None


def audio(nome):
    """Os bytes do audio: do cache ou baixados do servidor (e guardados para a proxima vez)."""
    guardado = em_cache(nome)
    if guardado is not None or not NOME.match(nome or ""):
        return guardado
    if api.modo_offline:
        return None
    resposta = _pedir("GET", f"/gritos/{nome}")
    if resposta.status_code != 200:
        return None
    PASTA.mkdir(parents=True, exist_ok=True)
    (PASTA / nome).write_bytes(resposta.content)
    return resposta.content


def pre_carregar(nomes):
    """Baixa os audios da turma que ainda nao estao no cache (chamado quando a Caca ou a Conquista comeca e sempre
    que alguem troca o grito). Erros nao importam: na hora, sem o audio, toca o padrao."""
    for nome in nomes:
        try:
            audio(nome)
        except api.ErroDeApi:
            pass
