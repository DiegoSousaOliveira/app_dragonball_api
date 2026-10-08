"""
Desenha o dragao que sai das esferas no efeito do telao (interface/efeito_dragao.py).
E um desenho proprio, so com formas do Canvas (linhas, circulos e poligonos): corpo verde que da uma volta,
nadadeira nas costas, barriga clara em gomos, chifres, bigodes e olhos vermelhos brilhando. Nenhuma imagem de fora.

O corpo e feito de muitos pedacinhos de linha GROSSA com ponta redonda, um depois do outro: juntos viram um
"tubo". Para o dragao "nascer" da luz, so desenhamos a parte que ja cresceu, e a ponta nova brilha em amarelo.
"""

import math

from interface.desenho_esfera import misturar

VERDE_ESCURO = "#14532D"
VERDE = "#2F8F46"
VERDE_CLARO = "#6CCB5F"
BARRIGA = "#D2DE96"
GOMO = "#A9BD6E"
CHIFRE = "#E2CB8C"
OLHO = "#FF2A2A"
BIGODE = "#E6F4D7"
LUZ = "#FFF1A8"

PEDACOS = 80                 # quantos pedacinhos de linha formam o corpo
TAMANHO_DA_CABECA = 0.13

# Por onde o corpo passa, da cauda (dentro das esferas) ate o pescoco: sobe pela esquerda, passa por cima da
# cabeca, desce pela direita e volta para a cabeca, no meio. x a partir do meio da tela e y a partir do topo,
# os dois em "alturas de tela" (0.1 = 10% da altura): assim o desenho cabe em qualquer monitor.
CAMINHO = [(0.0, 0.45), (-0.15, 0.43), (-0.36, 0.4), (-0.55, 0.3), (-0.6, 0.17), (-0.48, 0.07), (-0.27, 0.08),
           (-0.1, 0.04), (0.1, 0.07), (0.3, 0.04), (0.5, 0.1), (0.6, 0.24), (0.5, 0.36), (0.3, 0.38), (0.14, 0.32),
           (0.04, 0.24), (0.0, 0.18)]


def _curva(pontos, total):
    """Curva suave (Catmull-Rom) que passa por todos os pontos, com 'total' + 1 pontinhos."""
    estendidos = [pontos[0]] + list(pontos) + [pontos[-1]]
    trechos = len(pontos) - 1
    curva = []
    for indice in range(total + 1):
        posicao = indice / total * trechos
        trecho = min(int(posicao), trechos - 1)
        t = posicao - trecho
        p0, p1, p2, p3 = estendidos[trecho:trecho + 4]
        curva.append(tuple(0.5 * (2 * p1[i] + (p2[i] - p0[i]) * t + (2 * p0[i] - 5 * p1[i] + 4 * p2[i] - p3[i]) * t * t
                                 + (3 * p1[i] - p0[i] - 3 * p2[i] + p3[i]) * t ** 3) for i in (0, 1)))
    return curva


_CURVA = _curva(CAMINHO, PEDACOS)


def _ponto(indice, t):
    """Um ponto do corpo, balancando devagar com o tempo t (a cauda e a cabeca quase nao mexem)."""
    s = indice / PEDACOS
    x, y = _CURVA[indice]
    balanco = 0.012 * math.sin(2 * math.pi * (2 * s - 0.4 * t)) * math.sin(math.pi * s)
    return x + balanco, y + balanco * 0.6


def _raio(s):
    """Grossura do corpo: fino na cauda, grosso no meio, um pouco mais fino no pescoco."""
    return 0.036 * (0.2 + 0.8 * min(1.0, s / 0.35)) * (1 - 0.2 * max(0.0, s - 0.85) / 0.15)


def desenhar_dragao(canvas, largura, altura, crescido, t, fundo="#000000"):
    """crescido: quanto do corpo ja apareceu (0 a 1; a cabeca surge no 1). Pode passar de 1: assim o brilho
    da ponta vai sumindo depois que o dragao fica inteiro. t: segundos (para ele balancar)."""
    if crescido <= 0:
        return
    meio = largura / 2
    pontos = []
    for indice in range(PEDACOS + 1):
        x, y = _ponto(indice, t)
        pontos.append((meio + x * altura, y * altura, indice / PEDACOS))
    ultimo = max(1, int(min(1.0, crescido) * PEDACOS))

    def cor(base, s):
        idade = crescido - s                          # a ponta que acabou de crescer brilha
        return misturar(LUZ, base, idade / 0.2) if idade < 0.2 else base

    pedacos = []
    for indice in range(ultimo):
        (x1, y1, s), (x2, y2, _) = pontos[indice], pontos[indice + 1]
        comprimento = math.hypot(x2 - x1, y2 - y1) or 1
        nx, ny = -(y2 - y1) / comprimento, (x2 - x1) / comprimento    # perpendicular: barriga do lado de dentro
        pedacos.append((x1, y1, x2, y2, s, nx, ny, _raio(s) * altura))

    # 1) nadadeira das costas (atras de tudo)
    for x1, y1, x2, y2, s, nx, ny, r in pedacos[4::4]:
        dx, dy = (x2 - x1), (y2 - y1)
        canvas.create_polygon(x1 - nx * r * 0.6 - dx, y1 - ny * r * 0.6 - dy, x1 - nx * r * 1.8, y1 - ny * r * 1.8,
                              x1 - nx * r * 0.6 + dx * 2, y1 - ny * r * 0.6 + dy * 2, fill=cor(VERDE_ESCURO, s),
                              outline="")
    # 2) o corpo, em camadas: contorno, verde, brilho nas costas, barriga e os gomos da barriga
    camadas = ((2.0, 0.0, VERDE_ESCURO), (1.6, -0.1, VERDE), (0.35, -0.5, VERDE_CLARO), (0.75, 0.48, BARRIGA))
    for grossura, desvio, base in camadas:
        for x1, y1, x2, y2, s, nx, ny, r in pedacos:
            canvas.create_line(x1 + nx * r * desvio, y1 + ny * r * desvio, x2 + nx * r * desvio,
                               y2 + ny * r * desvio, width=max(1, r * grossura), fill=cor(base, s),
                               capstyle="round")
    for x1, y1, x2, y2, s, nx, ny, r in pedacos[1::2]:
        canvas.create_line(x1 + nx * r * 0.15, y1 + ny * r * 0.15, x1 + nx * r * 0.82, y1 + ny * r * 0.82,
                           width=max(1, r * 0.12), fill=cor(GOMO, s))
    # 3) a cabeca aparece quando o corpo termina de crescer (de frente, olhando para a turma)
    if crescido >= 1:
        x, y, _ = pontos[-1]
        desenhar_cabeca(canvas, x, y, TAMANHO_DA_CABECA * altura, t)


def desenhar_cabeca(canvas, cx, cy, tamanho, t):
    """tamanho = altura da cabeca em pixels."""
    h = tamanho
    cy += math.sin(t * 1.6) * h * 0.04                                # balanca de leve
    # juba espetada atras da cabeca
    juba = []
    for i in range(17):
        angulo = math.pi * (-0.05 + 1.1 * i / 16)
        r = h * (1.0 if i % 2 == 0 else 0.68)
        juba += [cx - math.cos(angulo) * r * 1.15, cy - math.sin(angulo) * r * 0.8 + h * 0.2]
    canvas.create_polygon(juba, fill=VERDE_ESCURO, outline="")
    # chifres: um tronco e um galho de cada lado
    for lado in (-1, 1):
        canvas.create_line(cx + lado * h * 0.3, cy - h * 0.4, cx + lado * h * 0.55, cy - h * 0.85,
                           cx + lado * h * 0.9, cy - h * 1.2, fill=CHIFRE, width=max(3, h * 0.11), smooth=True,
                           capstyle="round")
        canvas.create_line(cx + lado * h * 0.6, cy - h * 0.92, cx + lado * h * 0.42, cy - h * 1.18,
                           fill=CHIFRE, width=max(2, h * 0.075), capstyle="round")
    # cabeca e focinho
    canvas.create_oval(cx - h * 0.62, cy - h * 0.62, cx + h * 0.62, cy + h * 0.38, fill=VERDE, outline=VERDE_ESCURO,
                       width=max(2, h * 0.04))
    canvas.create_oval(cx - h * 0.44, cy - h * 0.05, cx + h * 0.44, cy + h * 0.74, fill=VERDE_CLARO,
                       outline=VERDE_ESCURO, width=max(2, h * 0.04))
    canvas.create_oval(cx - h * 0.24, cy + h * 0.4, cx + h * 0.24, cy + h * 0.68, fill=BARRIGA, outline="")
    for lado in (-1, 1):                                               # narinas
        canvas.create_oval(cx + lado * h * 0.17 - h * 0.05, cy + h * 0.16, cx + lado * h * 0.17 + h * 0.05,
                           cy + h * 0.25, fill=VERDE_ESCURO, outline="")
    canvas.create_line(cx - h * 0.32, cy + h * 0.57, cx, cy + h * 0.66, cx + h * 0.32, cy + h * 0.57,
                       fill=VERDE_ESCURO, width=max(2, h * 0.035), smooth=True)
    for lado in (-1, 1):                                               # presas
        canvas.create_polygon(cx + lado * h * 0.21, cy + h * 0.58, cx + lado * h * 0.14, cy + h * 0.6,
                              cx + lado * h * 0.18, cy + h * 0.76, fill="#FFFFFF", outline="")
    # bigodes compridos que ondulam
    for lado in (-1, 1):
        pontos = []
        for i in range(9):
            u = i / 8
            pontos += [cx + lado * (h * 0.4 + u * h * 2.1),
                       cy + h * 0.3 + u * h * 0.55 + math.sin(t * 2.2 + u * 3) * h * 0.14 * u]
        canvas.create_line(pontos, fill=BIGODE, width=max(2, h * 0.04), smooth=True, capstyle="round")
    # sobrancelhas grossas e olhos vermelhos brilhando (pulsam)
    brilho = 0.6 + 0.4 * math.sin(t * 5)
    for lado in (-1, 1):
        ox, oy = cx + lado * h * 0.3, cy - h * 0.2
        for anel in (3, 2, 1):
            r = h * 0.1 * (1 + 0.5 * anel * brilho)
            canvas.create_oval(ox - r * 1.3, oy - r, ox + r * 1.3, oy + r,
                               fill=misturar(VERDE, OLHO, 0.5 * brilho / anel), outline="")
        canvas.create_oval(ox - h * 0.13, oy - h * 0.085, ox + h * 0.13, oy + h * 0.085, fill=OLHO, outline="")
        canvas.create_oval(ox - h * 0.035 + lado * h * 0.03, oy - h * 0.05, ox + h * 0.02 + lado * h * 0.03,
                           oy - h * 0.005, fill="#FFFFFF", outline="")
        canvas.create_line(ox - lado * h * 0.18, oy - h * 0.21, ox + lado * h * 0.17, oy - h * 0.09,
                           fill=VERDE_ESCURO, width=max(3, h * 0.075), capstyle="round")
