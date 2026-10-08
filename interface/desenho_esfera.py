"""Desenha uma Esfera do Dragao num Canvas do Tkinter: circulo laranja com degrade, brilho e estrelas vermelhas
(o mesmo estilo do icone do programa, instalador/gerar_icone.py). Apagada = cinza."""

import math

LARANJA = "#F28C18"
LARANJA_CLARO = "#FFD86B"
BORDA = "#B8560A"
VERMELHO = "#D62828"
BRILHO = "#FFB52E"
CINZA = "#4A4D52"
CINZA_CLARO = "#5E6168"
CINZA_BORDA = "#3A3D42"
ESTRELA_APAGADA = "#6B6E73"

# Onde ficam as estrelas (em fracoes do raio) para 1 a 7 estrelas, e o tamanho de cada estrela
_SEIS = [(0.47 * math.cos(math.pi / 2 + i * math.pi / 3), -0.47 * math.sin(math.pi / 2 + i * math.pi / 3))
         for i in range(6)]
POSICOES = {
    1: [(0, 0)],
    2: [(-0.3, 0), (0.3, 0)],
    3: [(0, -0.3), (-0.3, 0.24), (0.3, 0.24)],
    4: [(-0.28, -0.28), (0.28, -0.28), (-0.28, 0.28), (0.28, 0.28)],
    5: [(0, 0), (-0.38, -0.38), (0.38, -0.38), (-0.38, 0.38), (0.38, 0.38)],
    6: [(-0.4, -0.24), (0, -0.24), (0.4, -0.24), (-0.4, 0.24), (0, 0.24), (0.4, 0.24)],
    7: [(0, 0)] + _SEIS,
}
TAMANHO_DA_ESTRELA = {1: 0.42, 2: 0.3, 3: 0.28, 4: 0.26, 5: 0.22, 6: 0.2, 7: 0.2}


def misturar(cor_a, cor_b, t):
    """A cor que fica t (0 a 1) do caminho entre cor_a e cor_b. O Tkinter nao tem transparencia:
    o brilho e feito com cores que vao 'sumindo' na cor do fundo."""
    t = max(0.0, min(1.0, t))
    a = [int(cor_a[i:i + 2], 16) for i in (1, 3, 5)]
    b = [int(cor_b[i:i + 2], 16) for i in (1, 3, 5)]
    return "#" + "".join(f"{round(x + (y - x) * t):02x}" for x, y in zip(a, b))


def estrela(canvas, cx, cy, raio, cor, tags, giro=0.0):
    pontos = []
    for i in range(10):
        angulo = math.pi / 2 + giro + i * math.pi / 5
        r = raio if i % 2 == 0 else raio * 0.45
        pontos += [cx + r * math.cos(angulo), cy - r * math.sin(angulo)]
    canvas.create_polygon(pontos, fill=cor, outline="", tags=tags)


def desenhar_esfera(canvas, cx, cy, raio, estrelas, acesa=True, brilho=0.0, fundo="#1E1F22", giro=0.0, tags=()):
    """brilho de 0 a 1 (aureola em volta); giro em radianos (as estrelas giram dentro da esfera)."""
    if acesa and brilho > 0:
        for anel in (3, 2, 1):
            r = raio * (1 + 0.22 * anel * brilho)
            cor = misturar(fundo, BRILHO, 0.55 * brilho / anel)
            canvas.create_oval(cx - r, cy - r, cx + r, cy + r, fill=cor, outline="", tags=tags)
    escura, clara, borda, cor_estrela = ((LARANJA, LARANJA_CLARO, BORDA, VERMELHO) if acesa
                                         else (CINZA, CINZA_CLARO, CINZA_BORDA, ESTRELA_APAGADA))
    canvas.create_oval(cx - raio, cy - raio, cx + raio, cy + raio, fill=escura, outline=borda,
                       width=max(1, raio / 12), tags=tags)
    passos = 6 if raio > 12 else 3
    for passo in range(1, passos):                     # degrade: circulos cada vez menores e mais claros
        t = passo / passos
        r = raio * (1 - 0.6 * t)
        desvio = -raio * 0.22 * t                      # a luz vem de cima, da esquerda
        canvas.create_oval(cx + desvio - r, cy + desvio - r, cx + desvio + r, cy + desvio + r,
                           fill=misturar(escura, clara, t), outline="", tags=tags)
    if acesa and raio > 8:
        r = raio * 0.2
        bx, by = cx - raio * 0.42, cy - raio * 0.45
        canvas.create_oval(bx - r, by - r * 0.7, bx + r, by + r * 0.7, fill=misturar(clara, "#FFFFFF", 0.7),
                           outline="", tags=tags)
    tamanho = raio * TAMANHO_DA_ESTRELA[estrelas]
    seno, cosseno = math.sin(giro), math.cos(giro)
    for px, py in POSICOES[estrelas]:
        x = px * cosseno - py * seno
        y = px * seno + py * cosseno
        estrela(canvas, cx + x * raio, cy + y * raio, tamanho, cor_estrela, tags, giro)
