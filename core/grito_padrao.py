"""
O som do grito de guerra padrao, gerado pelo proprio programa (modulo wave + matematica): nenhum arquivo de ninguem.

Como um som vira numeros: o alto-falante vai e volta milhares de vezes por segundo. Guardamos a posicao dele
22.050 vezes por segundo (a "taxa de amostragem"), cada posicao num numero de -32.767 a 32.767 (16 bits).
Uma onda seno de 440 vezes por segundo (440 Hz) e a nota La; somando ondas, fazemos acordes.
"""

import io
import math
import struct
import wave

TAXA = 22050                 # amostras por segundo
ID_DO_PADRAO = "padrao.wav"  # o nome com que o servidor entrega este som (GET /gritos/padrao.wav)

_pronto = None


def _onda(frequencia, t):
    return math.sin(2 * math.pi * frequencia * t)


def gerar_wav():
    """~1,4 s: uma "carga de energia" que sobe (de 220 Hz a 880 Hz) e um acorde de vitoria (Do-Mi-Sol)."""
    global _pronto
    if _pronto is not None:
        return _pronto
    amostras = []
    subida = int(TAXA * 0.55)
    for i in range(subida):
        t = i / TAXA
        frequencia = 220 + 660 * (i / subida) ** 2               # cada vez mais agudo
        volume = 0.25 + 0.45 * i / subida
        amostras.append(volume * (_onda(frequencia, t) + 0.3 * _onda(frequencia * 2, t)))
    acorde = int(TAXA * 0.85)
    for i in range(acorde):
        t = i / TAXA
        volume = 0.7 * (1 - i / acorde) ** 1.5                     # vai sumindo
        tremido = 1 + 0.06 * _onda(6, t)
        amostras.append(volume * tremido * (_onda(523.25, t) + _onda(659.25, t) + _onda(783.99, t)) / 2.2)
    maior = max(abs(a) for a in amostras) or 1
    dados = struct.pack(f"<{len(amostras)}h", *(int(30000 * a / maior) for a in amostras))
    memoria = io.BytesIO()
    with wave.open(memoria, "wb") as arquivo:
        arquivo.setnchannels(1)
        arquivo.setsampwidth(2)
        arquivo.setframerate(TAXA)
        arquivo.writeframes(dados)
    _pronto = memoria.getvalue()
    return _pronto
