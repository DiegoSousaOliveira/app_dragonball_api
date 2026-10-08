"""
O som do app: toca os gritos de guerra (mp3, wav, ogg) UM DE CADA VEZ.

  - Fila: um tocando e no maximo 2 esperando; o que passar disso e descartado (numa sala com 15 PCs, melhor perder
    um grito do que virar barulho).
  - Cada som e cortado em 6 s. Volume de 0 a 100 e mudo (guardados no config.json de cada PC).
  - Biblioteca: miniaudio (leve, toca mp3/wav/ogg). Sem ela, so WAV com o winsound. Sem nada disso (ou se o PC nao
    tiver placa de som), o app segue MUDO, avisa "sem áudio neste PC" e nunca trava.
"""

import threading
import time
from array import array
from collections import deque

from core.grito_padrao import gerar_wav

try:
    import miniaudio
except Exception:                     # nao instalado, ou a DLL nao carregou
    miniaudio = None
try:
    import winsound
except ImportError:                   # Linux/Mac
    winsound = None

DURACAO_MAXIMA = 6.0                  # segundos
NA_FILA = 2                           # quantos sons podem esperar enquanto um toca
TAXA = 44100


def _tocar_com_miniaudio(dados, volume):
    som = miniaudio.decode(dados, output_format=miniaudio.SampleFormat.SIGNED16, nchannels=2, sample_rate=TAXA)
    amostras = som.samples[:int(DURACAO_MAXIMA * TAXA) * 2]                 # corta em 6 s
    if volume < 100:
        fator = max(0, volume) / 100
        amostras = array("h", (int(a * fator) for a in amostras))
    duracao = len(amostras) / 2 / TAXA

    def gerador():
        posicao = 0
        pedido = yield b""
        while posicao < len(amostras):
            pedaco = amostras[posicao:posicao + pedido * 2]
            posicao += pedido * 2
            pedido = yield pedaco.tobytes()

    with miniaudio.PlaybackDevice(output_format=miniaudio.SampleFormat.SIGNED16, nchannels=2,
                                  sample_rate=TAXA) as dispositivo:
        fluxo = gerador()
        next(fluxo)
        dispositivo.start(fluxo)
        time.sleep(duracao + 0.15)


def _tocar_com_winsound(dados, volume):
    """Sem miniaudio: o winsound so entende WAV (e toca tudo, sem volume). Outro formato vira o som padrao."""
    if not dados.startswith(b"RIFF"):
        dados = gerar_wav()
    winsound.PlaySound(dados, winsound.SND_MEMORY)


class Player:
    """tocador(dados, volume): quem toca de verdade (os testes passam um falso)."""

    def __init__(self, tocador=None):
        if tocador is not None:
            self._tocador, self.motivo = tocador, ""
        elif miniaudio is not None:
            self._tocador, self.motivo = _tocar_com_miniaudio, ""
        elif winsound is not None:
            self._tocador, self.motivo = _tocar_com_winsound, "só WAV neste PC (falta o miniaudio)"
        else:
            self._tocador, self.motivo = None, "sem áudio neste PC"
        self.mudo = False
        self.volume = 80
        self.tocando = False
        self._fila = deque()
        self._trava = threading.Lock()
        self._acordar = threading.Event()
        threading.Thread(target=self._trabalhar, daemon=True, name="som").start()

    @property
    def disponivel(self):
        return self._tocador is not None

    def tocar(self, dados):
        """Poe o som na fila. Devolve False se ele foi descartado (mudo, sem audio ou fila cheia)."""
        if self.mudo or not dados or not self.disponivel:
            return False
        with self._trava:
            if len(self._fila) + (1 if self.tocando else 0) >= 1 + NA_FILA:     # 1 tocando + 2 esperando
                return False
            self._fila.append(dados)
        self._acordar.set()
        return True

    def _trabalhar(self):
        while True:
            self._acordar.wait()
            with self._trava:
                if not self._fila:
                    self._acordar.clear()
                    continue
                dados = self._fila.popleft()
                self.tocando = True
            try:
                self._tocar_um(dados)
            finally:
                self.tocando = False


    def _tocar_um(self, dados):
        """Um arquivo ruim toca o som padrao no lugar; se nem o padrao tocar (sem placa de som...), fica mudo."""
        for tentativa in (dados, gerar_wav()):
            try:
                self._tocador(tentativa, self.volume)
                return
            except Exception:
                continue
        self._tocador, self.motivo = None, "sem áudio neste PC"
        with self._trava:
            self._fila.clear()


_player = None


def player():
    """O player do app (um so por programa)."""
    global _player
    if _player is None:
        _player = Player()
    return _player
