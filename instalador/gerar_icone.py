"""Desenha o icone do programa (uma esfera do dragao de 4 estrelas) e salva instalador/icone.ico."""

import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

TAMANHO = 512
PASTA = Path(__file__).resolve().parent


def estrela(desenho, cx, cy, raio, cor):
    pontos = []
    for i in range(10):
        angulo = math.pi / 2 + i * math.pi / 5
        r = raio if i % 2 == 0 else raio * 0.45
        pontos.append((cx + r * math.cos(angulo), cy - r * math.sin(angulo)))
    desenho.polygon(pontos, fill=cor)


def desenhar():
    imagem = Image.new("RGBA", (TAMANHO, TAMANHO), (0, 0, 0, 0))
    desenho = ImageDraw.Draw(imagem)
    margem = 24
    # esfera laranja com um degrade simples (circulos concentricos)
    for passo in range(60):
        t = passo / 59
        cor = (int(246 + 6 * t), int(140 + 70 * t), int(20 + 40 * t), 255)
        deslocamento = int(t * 70)
        raio = (TAMANHO - 2 * margem) // 2 - int(t * 150)
        centro = TAMANHO // 2 - deslocamento // 2
        desenho.ellipse((centro - raio, centro - raio, centro + raio, centro + raio), fill=cor)
    desenho.ellipse((margem, margem, TAMANHO - margem, TAMANHO - margem), outline=(200, 90, 10, 255), width=10)
    # brilho
    brilho = Image.new("RGBA", (TAMANHO, TAMANHO), (0, 0, 0, 0))
    ImageDraw.Draw(brilho).ellipse((120, 90, 230, 170), fill=(255, 255, 255, 150))
    imagem.alpha_composite(brilho.filter(ImageFilter.GaussianBlur(14)))
    # 4 estrelas vermelhas
    for cx, cy in ((200, 215), (312, 215), (200, 327), (312, 327)):
        estrela(desenho, cx, cy, 52, (214, 40, 40, 255))
    return imagem


if __name__ == "__main__":
    icone = desenhar()
    icone.save(PASTA / "icone.png")
    icone.save(PASTA / "icone.ico", sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
    print("icone salvo em", PASTA / "icone.ico")
