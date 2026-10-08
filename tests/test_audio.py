"""Testes do player de som (interface/audio.py) com um "alto-falante" falso: a fila nunca deixa dois sons tocarem
ao mesmo tempo, descarta o excedente e nunca trava o app quando o audio falha."""

import threading
import time

from core.grito_padrao import gerar_wav
from interface.audio import NA_FILA, Player


class AltoFalante:
    """Anota quando cada som comecou e terminou (e quanto durou)."""

    def __init__(self, duracao=0.15, falhar_com=None):
        self.tocados, self.duracao, self.falhar_com = [], duracao, falhar_com
        self.juntos = 0                   # quantos estao tocando AGORA (nunca pode passar de 1)
        self.maximo_juntos = 0
        self._trava = threading.Lock()

    def __call__(self, dados, volume):
        if self.falhar_com is not None and dados.startswith(self.falhar_com):
            raise RuntimeError("arquivo estragado")
        with self._trava:
            self.juntos += 1
            self.maximo_juntos = max(self.maximo_juntos, self.juntos)
        time.sleep(self.duracao)
        with self._trava:
            self.juntos -= 1
            self.tocados.append((dados[:4], volume))


def esperar_acabar(player, segundos=3):
    fim = time.time() + segundos
    while time.time() < fim and (player.tocando or player._fila):
        time.sleep(0.02)
    time.sleep(0.05)


def test_fila_um_de_cada_vez_e_descarta_o_excedente():
    alto = AltoFalante()
    player = Player(tocador=alto)
    aceitos = [player.tocar(bytes([65 + i]) * 8) for i in range(6)]      # 6 gritos de uma vez
    esperar_acabar(player)
    assert aceitos.count(True) == 1 + NA_FILA and aceitos[0] is True     # 1 tocando + 2 esperando
    assert len(alto.tocados) == 3 and alto.maximo_juntos == 1            # nunca dois ao mesmo tempo


def test_mudo_volume_e_som_vazio():
    alto = AltoFalante(duracao=0.01)
    player = Player(tocador=alto)
    player.mudo = True
    assert player.tocar(b"RIFFxxxx") is False
    player.mudo, player.volume = False, 35
    assert player.tocar(b"") is False
    assert player.tocar(b"RIFFxxxx") is True
    esperar_acabar(player)
    assert alto.tocados == [(b"RIFF", 35)]


def test_arquivo_ruim_toca_o_padrao_e_sem_audio_nao_trava():
    alto = AltoFalante(duracao=0.01, falhar_com=b"ID3")
    player = Player(tocador=alto)
    player.tocar(b"ID3estragado")
    esperar_acabar(player)
    assert alto.tocados == [(gerar_wav()[:4], 80)] and player.disponivel     # tocou o padrao no lugar
    quebrado = Player(tocador=lambda dados, volume: (_ for _ in ()).throw(OSError("sem placa de som")))
    quebrado.tocar(b"RIFFxxxx")
    esperar_acabar(quebrado)
    assert not quebrado.disponivel and quebrado.motivo == "sem áudio neste PC"
    assert quebrado.tocar(b"RIFFxxxx") is False                            # segue mudo, sem travar
