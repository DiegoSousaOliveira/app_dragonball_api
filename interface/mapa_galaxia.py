"""
O mapa da galaxia da Conquista: cada territorio e um planeta (circulo) pintado com a cor do dono.
O mesmo desenho aparece no app do aluno, na aba do painel e no telao; os tamanhos saem do tamanho da janela.

  - anel amarelo: o planeta e SEU · anel grosso branco: o planeta que voce escolheu como alvo
  - 🛡 com segundos: escudo depois de uma conquista · ⚔ piscando: alguem esta invadindo agora
  - pulso dourado: o planeta acabou de trocar de dono
"""

import math
import random
import time
import tkinter as tk

from interface import tema
from interface.desenho_esfera import misturar

# 16 cores bem diferentes entre si (vermelho, verde, azul, amarelo, roxo, laranja, ...): uma por aluno
PALETA = ["#E5484D", "#3DD68C", "#4C9AFF", "#FAC02D", "#C77DFF", "#FF8A3D", "#2DD4BF", "#F472B6",
          "#A3E635", "#B08968", "#E5E7EB", "#22D3EE", "#D946EF", "#CA8A04", "#FDA4AF", "#818CF8"]
NEUTRO = "#6B6E73"
ESPACO = "#0B0D16"
PULSO = 3.0                     # segundos de destaque quando um planeta troca de dono


def cor_do_dono(cor):
    return NEUTRO if cor is None else PALETA[cor % len(PALETA)]


class MapaGalaxia(tk.Canvas):
    def __init__(self, mestre, ao_clicar=None):
        super().__init__(mestre, bg=ESPACO, highlightthickness=0, cursor="hand2" if ao_clicar else "")
        self.ao_clicar = ao_clicar
        self.mapa = []
        self.selecionado = None
        self.destaques = {}             # id do territorio -> quando trocou de dono
        self.aviso_vazio = "O mapa aparece quando o professor começar a Conquista."
        sorteio = random.Random(42)     # estrelas sempre nos mesmos lugares
        self.estrelas = [(sorteio.random(), sorteio.random(), sorteio.choice((1, 1, 1, 2))) for _ in range(140)]
        self._agendado = None
        self.bind("<Configure>", lambda evento: self.desenhar())
        if ao_clicar:
            self.bind("<Button-1>", self._clique)

    def mostrar(self, mapa, selecionado=None):
        donos_antes = {t["id"]: t["dono"] for t in self.mapa}
        agora = time.time()
        for territorio in mapa:
            if territorio["id"] in donos_antes and donos_antes[territorio["id"]] != territorio["dono"]:
                self.destaques[territorio["id"]] = agora
        self.mapa, self.selecionado = mapa, selecionado
        self.desenhar()

    # ---------------- contas ----------------

    def _raio_da_tela(self):
        largura, altura = self.winfo_width(), self.winfo_height()
        return max(12.0, min(largura / 1.6, altura) * 0.062)

    def _caixa(self):
        """O retangulo ocupado pelos lugares em jogo. Os lugares foram pensados para 20 planetas; com poucos, eles
        ficam todos no meio, e por isso o mapa se ESPALHA pela tela (no maximo 2,5 vezes)."""
        xs = [t["x"] for t in self.mapa] or [0.5]
        ys = [t["y"] for t in self.mapa] or [0.5]
        return ((min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2,
                max(0.2, (max(xs) - min(xs)) / 2), max(0.2, (max(ys) - min(ys)) / 2))

    def _posicoes(self, raio):
        largura, altura = self.winfo_width(), self.winfo_height()
        meio_x, meio_y, meia_x, meia_y = self._caixa()
        margem_x, topo, base = raio * 2.3, raio * 1.6, raio * 2.6        # sobra espaco para os nomes
        posicoes = {}
        for territorio in self.mapa:
            nx = 0.5 + (territorio["x"] - meio_x) / meia_x * 0.5
            ny = 0.5 + (territorio["y"] - meio_y) / meia_y * 0.5
            posicoes[territorio["id"]] = (margem_x + nx * max(1.0, largura - 2 * margem_x),
                                          topo + ny * max(1.0, altura - topo - base))
        return posicoes

    def _layout(self):
        """(raio, {id: (x, y)}). O raio vem do tamanho da tela, mas nunca passa de 30% da distancia entre os dois
        planetas mais proximos (senao o nome de um fica embaixo do outro)."""
        raio = self._raio_da_tela()
        posicoes = self._posicoes(raio)
        pontos = list(posicoes.values())
        distancias = [math.hypot(a[0] - b[0], a[1] - b[1]) for i, a in enumerate(pontos) for b in pontos[i + 1:]]
        if distancias and min(distancias) * 0.3 < raio:
            raio = max(10.0, min(distancias) * 0.3)
            posicoes = self._posicoes(raio)
        return raio, posicoes

    def _clique(self, evento):
        raio, posicoes = self._layout()
        for territorio in self.mapa:
            x, y = posicoes[territorio["id"]]
            if math.hypot(evento.x - x, evento.y - y) <= raio * 1.4:
                self.ao_clicar(territorio["id"])
                return

    def _etiqueta(self, x, y, texto, cor, fonte):
        """Um texto com um fundo escuro atras: sempre legivel, mesmo passando por cima de outro planeta."""
        item = self.create_text(x, y, text=texto, fill=cor, font=fonte)
        caixa = self.bbox(item)
        if caixa:
            fundo = self.create_rectangle(caixa[0] - 3, caixa[1] - 1, caixa[2] + 3, caixa[3] + 1, fill=ESPACO,
                                          outline="")
            self.tag_lower(fundo, item)

    # ---------------- desenho ----------------

    def desenhar(self):
        self.delete("all")
        largura, altura = self.winfo_width(), self.winfo_height()
        if largura < 60 or altura < 60:
            return
        for ex, ey, tamanho in self.estrelas:
            x, y = ex * largura, ey * altura
            self.create_oval(x, y, x + tamanho, y + tamanho, fill="#3A3F55" if tamanho == 1 else "#6B7090", outline="")
        fonte = tema.escolher_fonte()
        if not self.mapa:
            self.create_text(largura / 2, altura / 2, text=self.aviso_vazio, fill=tema.TEXTO_SECUNDARIO,
                             font=(fonte, -int(max(13, altura * 0.035))), width=largura * 0.8, justify="center")
            return
        raio, posicoes = self._layout()
        agora = time.time()
        animar = False
        for territorio in self.mapa:
            x, y = posicoes[territorio["id"]]
            cor = cor_do_dono(territorio["cor"])
            destaque = self.destaques.get(territorio["id"])
            if destaque and agora - destaque < PULSO:                     # pulso: acabou de trocar de dono
                progresso = (agora - destaque) / PULSO
                r = raio * (1.2 + 1.3 * progresso)
                self.create_oval(x - r, y - r, x + r, y + r, outline=misturar(tema.DESTAQUE, ESPACO, progresso),
                                 width=max(2, raio * 0.18 * (1 - progresso)))
                animar = True
            if territorio["em_batalha"]:                                  # brilho vermelho piscando
                piscar = 0.5 + 0.5 * math.sin(agora * 8)
                r = raio * 1.35
                self.create_oval(x - r, y - r, x + r, y + r, fill=misturar(ESPACO, tema.PERIGO, 0.45 * piscar),
                                 outline="")
                animar = True
            if territorio["id"] == self.selecionado:
                r = raio * 1.28
                self.create_oval(x - r, y - r, x + r, y + r, outline="#FFFFFF", width=max(2, raio * 0.12))
            if territorio.get("meu"):
                r = raio * 1.15
                self.create_oval(x - r, y - r, x + r, y + r, outline=tema.DESTAQUE, width=max(2, raio * 0.1),
                                 dash=(6, 4))
            self.create_oval(x - raio, y - raio, x + raio, y + raio, fill=misturar(cor, "#000000", 0.45),
                             outline=cor, width=max(2, raio * 0.14))
            r = raio * 0.55                                               # um brilho de planeta
            self.create_oval(x - r - raio * 0.2, y - r - raio * 0.2, x + r - raio * 0.2, y + r - raio * 0.2,
                             fill=misturar(cor, "#000000", 0.2), outline="")
        for territorio in self.mapa:              # os textos DEPOIS de todos os planetas: nenhum fica escondido
            x, y = posicoes[territorio["id"]]
            cor = cor_do_dono(territorio["cor"])
            nome = territorio["nome"]
            limite = max(10, int(raio * 0.9))                             # mapa pequeno: nomes mais curtos
            if len(nome) > limite:
                nome = nome[:limite - 1] + "…"
            self._etiqueta(x, y + raio * 1.45, nome, tema.TEXTO, (fonte, -int(max(11, raio * 0.42)), "bold"))
            dono = territorio["dono"] or "neutro"
            self._etiqueta(x, y + raio * 2.05, dono, cor if territorio["dono"] else tema.TEXTO_SECUNDARIO,
                           (fonte, -int(max(10, raio * 0.36)), "bold" if territorio["dono"] else "normal"))
            if territorio["escudo"]:
                self.create_text(x + raio * 0.95, y - raio * 0.95, text=f"🛡{territorio['escudo']}",
                                 fill="#9CC3FF", font=(fonte, -int(max(10, raio * 0.36)), "bold"))
            if territorio["em_batalha"]:
                self.create_text(x - raio * 0.95, y - raio * 0.95, text="⚔", fill=tema.PERIGO,
                                 font=(fonte, -int(max(12, raio * 0.5)), "bold"))
        self._continuar(animar)

    def _continuar(self, animar):
        """Enquanto houver pulso ou luta, redesenha sozinho (~16 vezes por segundo)."""
        if animar and self._agendado is None:
            self._agendado = self.after(60, self._quadro)

    def _quadro(self):
        self._agendado = None
        if self.winfo_exists():
            self.desenhar()
