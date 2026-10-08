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

    def _raio(self):
        largura, altura = self.winfo_width(), self.winfo_height()
        return max(12.0, min(largura / 1.6, altura) * 0.062)

    def _posicao(self, territorio):
        largura, altura = self.winfo_width(), self.winfo_height()
        raio = self._raio()
        margem_x, topo, base = raio * 2.3, raio * 1.6, raio * 2.6        # sobra espaco para os nomes
        x = margem_x + territorio["x"] * max(1.0, largura - 2 * margem_x)
        y = topo + territorio["y"] * max(1.0, altura - topo - base)
        return x, y

    def _clique(self, evento):
        raio = self._raio()
        for territorio in self.mapa:
            x, y = self._posicao(territorio)
            if math.hypot(evento.x - x, evento.y - y) <= raio * 1.4:
                self.ao_clicar(territorio["id"])
                return

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
        raio = self._raio()
        agora = time.time()
        animar = False
        for territorio in self.mapa:
            x, y = self._posicao(territorio)
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
            nome = territorio["nome"]
            limite = int(raio * 0.9)                                      # mapa pequeno: nomes mais curtos
            if len(nome) > limite:
                nome = nome[:max(6, limite - 1)] + "…"
            self.create_text(x, y + raio * 1.45, text=nome, fill=tema.TEXTO,
                             font=(fonte, -int(max(11, raio * 0.42)), "bold"))
            dono = territorio["dono"] or "neutro"
            self.create_text(x, y + raio * 2.05, text=dono, fill=cor if territorio["dono"] else tema.TEXTO_SECUNDARIO,
                             font=(fonte, -int(max(10, raio * 0.36)), "bold" if territorio["dono"] else "normal"))
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
