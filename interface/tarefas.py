"""
Trabalho demorado (rede, imagens) em segundo plano, sem travar a janela.

Regra de ouro do Tkinter: SO a thread principal pode mexer nos widgets. Entao:
  1. a funcao demorada roda numa thread do "pool" (ThreadPoolExecutor);
  2. a janela confere de 50 em 50 ms (after) se ela terminou;
  3. quando termina, o resultado e entregue na thread principal (ao_terminar).
"""

import threading
from concurrent.futures import ThreadPoolExecutor

from core import imagens

_executor = ThreadPoolExecutor(max_workers=6, thread_name_prefix="dbdex")
_fotos = {}                         # url -> imagem ja reduzida (para nao baixar/decodificar de novo)
_trava_fotos = threading.Lock()
TAMANHO_MAXIMO_DA_FOTO = (520, 720)  # as originais chegam a 1435x2597: reduzimos para economizar memoria


def _widget_existe(widget):
    try:
        return bool(widget.winfo_exists())
    except Exception:
        return False


def em_segundo_plano(widget, funcao, ao_terminar=None, ao_falhar=None):
    """Roda funcao() numa thread. Depois chama ao_terminar(resultado) ou ao_falhar(erro)
    na thread principal (se o widget ainda existir)."""
    futuro = _executor.submit(funcao)

    def conferir():
        if not _widget_existe(widget):
            return
        if not futuro.done():
            widget.after(50, conferir)
            return
        erro = futuro.exception()
        if erro is not None:
            if ao_falhar:
                ao_falhar(erro)
        elif ao_terminar:
            ao_terminar(futuro.result())

    widget.after(50, conferir)
    return futuro


def baixar_foto(url):
    """Baixa (ou pega do cache) e reduz. Pode ser chamada de dentro de uma thread."""
    imagem = imagens.baixar_imagem(url)
    if imagem is not None:
        imagem.thumbnail(TAMANHO_MAXIMO_DA_FOTO)
    with _trava_fotos:
        _fotos[url] = imagem
    return imagem


def foto_pronta(url):
    """A foto se ela ja estiver na memoria (ou None)."""
    with _trava_fotos:
        return _fotos.get(url)


def carregar_foto(widget, url, ao_terminar):
    """Entrega a foto (PIL, ja reduzida, ou None se falhar) para ao_terminar(imagem)."""
    with _trava_fotos:
        pronta = url in _fotos
        imagem = _fotos.get(url)
    if pronta:
        widget.after(0, lambda: _widget_existe(widget) and ao_terminar(imagem))
        return
    em_segundo_plano(widget, lambda: baixar_foto(url), ao_terminar,
                     lambda erro: ao_terminar(None))


def esquecer_fotos():
    """Ao trocar de servidor as URLs mudam: comecamos de novo."""
    with _trava_fotos:
        _fotos.clear()
