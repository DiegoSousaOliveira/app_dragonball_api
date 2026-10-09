"""
O mapa do Radar do Dragao (esfera 4) na tela 🐉 Esferas: uma grade 11 x 11 com cara de radar.
Clique numa casa (ou mova com as setas e aperte Enter/Espaco) para escanear: o app faz o MESMO pedido que o aluno
faria no navegador (GET /esferas/radar?cacador=7&x=5&y=5) e pinta a casa com a temperatura da resposta.
A requisicao equivalente fica sempre escrita em cima do mapa: o clique virou uma query string!
"""

import math
import time
import tkinter as tk

import customtkinter as ctk

from core import esferas, esferas_cliente
from interface import tarefas, tema
from interface.desenho_esfera import misturar

FUNDO = "#06130C"
LINHA = "#1D4D33"
VERDE = "#3DD68C"
CORES = {"frio": "#3B82F6", "morno": "#EAB308", "quente": "#F97316", "fervendo": "#EF4444", "achou": "#FAC02D"}
NOMES = {"frio": "❄ Frio", "morno": "🌤 Morno", "quente": "🔥 Quente", "fervendo": "🔥🔥 Fervendo!", "achou": "🐉 Achou!"}
LADO = esferas.LADO_DO_RADAR + 1          # 11 casas (0 a 10)
CASA = 28                                 # pixels de cada casa


class MapaDoRadar(ctk.CTkFrame):
    """numero(): o numero de cacador do aluno. ao_achar(codigo): chamado quando a varredura acha a esfera."""

    def __init__(self, mestre, numero, ao_achar):
        super().__init__(mestre, fg_color=tema.CARD, corner_radius=10)
        self.numero = numero
        self.ao_achar = ao_achar
        self.historico = esferas_cliente.HistoricoDoRadar()
        self.marcador = (5, 5)
        self.escaneando = False
        self.inicio = time.time()
        ctk.CTkLabel(self, text="🧭 Mapa do Radar do Dragão", font=tema.fonte(15, negrito=True),
                     text_color=tema.DESTAQUE).pack(anchor="w", padx=12, pady=(8, 0))
        tema.texto_secundario(self, "Clique numa casa (ou use as setas e Enter) para escanear.", 12).pack(
            anchor="w", padx=12)
        self.pedido = ctk.CTkLabel(self, text="Última varredura: (nenhuma ainda)", font=("Consolas", 12),
                                   text_color="#9CC3FF", anchor="w")
        self.pedido.pack(anchor="w", padx=12, pady=(4, 0))
        self.resultado = ctk.CTkLabel(self, text="", font=tema.fonte(13, negrito=True), anchor="w")
        self.resultado.pack(anchor="w", padx=12)
        margem = 26
        self.margem = margem
        tamanho = margem + LADO * CASA + 6
        self.canvas = tk.Canvas(self, width=tamanho, height=tamanho, bg=FUNDO, highlightthickness=1,
                                highlightbackground=LINHA, highlightcolor=VERDE, cursor="crosshair")
        self.canvas.pack(padx=12, pady=6)
        legenda = ctk.CTkFrame(self, fg_color="transparent")
        legenda.pack(anchor="w", padx=12)
        for faixa in ("frio", "morno", "quente", "fervendo"):          # cada faixa na cor que ela pinta no mapa
            ctk.CTkLabel(legenda, text=f"■ {NOMES[faixa]}", font=tema.fonte(12),
                         text_color=CORES[faixa]).pack(side="left", padx=(0, 14))
        self.tentativas = tema.texto_secundario(self, "Tentativas: 0", 12)
        self.tentativas.pack(anchor="w", padx=12, pady=(0, 8))
        self.canvas.bind("<Button-1>", self._clique)
        for tecla, (dx, dy) in {"<Left>": (-1, 0), "<Right>": (1, 0), "<Up>": (0, 1), "<Down>": (0, -1)}.items():
            self.canvas.bind(tecla, lambda evento, d=(dx, dy): self._mover(*d))
        for tecla in ("<Return>", "<space>"):
            self.canvas.bind(tecla, lambda evento: self.escanear(*self.marcador))
        self._agendado = None
        self._girar()

    # ---------------- contas (y cresce para CIMA, como no plano cartesiano) ----------------

    def _centro(self, x, y):
        return self.margem + (x + 0.5) * CASA, 3 + (LADO - 1 - y + 0.5) * CASA

    def _casa(self, px, py):
        x = int((px - self.margem) // CASA)
        y = LADO - 1 - int((py - 3) // CASA)
        if 0 <= x < LADO and 0 <= y < LADO:
            return x, y
        return None

    # ---------------- desenho ----------------

    def desenhar(self):
        c = self.canvas
        c.delete("all")
        meio_x, meio_y = self._centro(5, 5)
        for i in range(LADO):
            x, _ = self._centro(i, 0)
            _, y = self._centro(0, i)
            c.create_text(x, 3 + LADO * CASA + 10, text=str(i), fill=tema.TEXTO_SECUNDARIO, font=("Consolas", 9))
            c.create_text(self.margem - 12, y, text=str(i), fill=tema.TEXTO_SECUNDARIO, font=("Consolas", 9))
        c.create_text(self.margem + LADO * CASA - 4, 3 + LADO * CASA + 10, text="x→", fill=VERDE, font=("Consolas", 9))
        c.create_text(self.margem - 12, 6, text="y↑", fill=VERDE, font=("Consolas", 9))
        for x in range(LADO):
            for y in range(LADO):
                cx, cy = self._centro(x, y)
                faixa = self.historico.faixa(x, y)
                cor = CORES.get(faixa)
                c.create_rectangle(cx - CASA / 2 + 1, cy - CASA / 2 + 1, cx + CASA / 2 - 1, cy + CASA / 2 - 1,
                                   fill=misturar(FUNDO, cor, 0.85) if cor else FUNDO, outline=LINHA)
        for anel in (1, 2, 3, 4, 5):                                  # aneis do radar (por cima das casas)
            r = anel * CASA * 1.1
            c.create_oval(meio_x - r, meio_y - r, meio_x + r, meio_y + r, outline="#2E7D52")
        # a varredura girando (so enfeite: quem acha a esfera e a sua query string!)
        angulo = (time.time() - self.inicio) * 1.6
        r = CASA * 5.6
        for passo in range(6):
            a = angulo - passo * 0.06
            c.create_line(meio_x, meio_y, meio_x + r * math.cos(a), meio_y + r * math.sin(a),
                          fill=misturar(FUNDO, VERDE, 0.7 - passo * 0.11), width=2)
        mx, my = self._centro(*self.marcador)
        c.create_rectangle(mx - CASA / 2, my - CASA / 2, mx + CASA / 2, my + CASA / 2, outline="#FFFFFF", width=2)

    def _girar(self):
        if not self.winfo_exists():
            return
        if self.winfo_viewable():                    # escondido (outra tela aberta): nao gasta desenhando
            self.desenhar()
            self._agendado = self.after(70, self._girar)
        else:
            self._agendado = self.after(500, self._girar)

    # ---------------- varredura ----------------

    def _clique(self, evento):
        self.canvas.focus_set()
        casa = self._casa(evento.x, evento.y)
        if casa:
            self.marcador = casa
            self.escanear(*casa)

    def _mover(self, dx, dy):
        x, y = self.marcador
        self.marcador = (min(LADO - 1, max(0, x + dx)), min(LADO - 1, max(0, y + dy)))

    def escanear(self, x, y):
        if self.escaneando:
            return
        self.escaneando = True
        numero = self.numero()
        self.pedido.configure(text=f"Última varredura: {esferas_cliente.url_do_radar(numero, x, y)}")
        self.resultado.configure(text="📡 Escaneando...", text_color=tema.TEXTO_SECUNDARIO)
        tarefas.em_segundo_plano(self, lambda: esferas_cliente.escanear_radar(numero, x, y),
                                 lambda resultado: self._chegou(x, y, resultado), self._falhou)

    def _chegou(self, x, y, resultado):
        self.escaneando = False
        self.historico.registrar(x, y, resultado)
        self.pedido.configure(text=f"Última varredura: {resultado['pedido']}  →  {resultado['status']}")
        self.tentativas.configure(text=f"Tentativas: {self.historico.tentativas}")
        if resultado["tipo"] == "achou":
            self.resultado.configure(text=f"🐉 Achou! Código {resultado['valor']}: resgatando...",
                                     text_color=tema.SUCESSO)
            self.ao_achar(resultado["valor"])
        elif resultado["tipo"] == "temperatura":
            self.resultado.configure(text=f"(x={x}, y={y}): {NOMES[resultado['valor']]}",
                                     text_color=CORES[resultado["valor"]])
        else:
            self.resultado.configure(text=f"✖ {resultado['valor']}", text_color=tema.PERIGO)

    def _falhou(self, erro):
        self.escaneando = False
        self.resultado.configure(text=f"✖ Não consegui escanear ({erro})", text_color=tema.PERIGO)
