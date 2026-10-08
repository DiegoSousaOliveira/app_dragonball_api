"""
O que aparece no telao durante a Caca as Esferas:
  - EfeitoDragao: tela cheia quando o 1o aluno junta as 7 esferas (fundo escurece, esferas girando e brilhando,
    flash de luz, "O DRAGAO FOI INVOCADO!", o nome do aluno e o pedido). Sem desenho do dragao: so as esferas.
  - AvisoNoTelao: uma faixa no alto da tela por alguns segundos ("Bruno tambem invocou o dragao!").
  - Som: bipes com o winsound (so existe no Windows; em outro sistema fica mudo).
"""

import math
import threading
import time
import tkinter as tk

from interface import tema
from interface.desenho_esfera import desenhar_esfera, misturar

try:
    import winsound
except ImportError:                 # Linux/Mac: sem som
    winsound = None

QUADRO = 33                         # milissegundos entre um desenho e outro (~30 por segundo)
DURACAO_MINIMA = 8                  # segundos de efeito, no minimo
DEPOIS_DO_PEDIDO = 3.5              # segundos mostrando o pedido escolhido
DURACAO_MAXIMA = 45                 # seguranca: fecha sozinho mesmo se o pedido nunca chegar
FLASH = 2.4                         # segundo em que acontece o clarao
PRETO = "#000000"
AMARELO = tema.DESTAQUE

MELODIAS = {
    "achado": [(1047, 70), (1568, 110)],
    "grito": [(660, 60), (880, 60)],
    "inicio": [(523, 120), (784, 180)],
    "dragao": [(392, 160), (523, 160), (659, 160), (784, 220), (1047, 520)],
}


class Som:
    def __init__(self):
        self.mudo = False

    def tocar(self, nome):
        if self.mudo or winsound is None:
            return

        def bipar():
            try:
                for frequencia, duracao in MELODIAS[nome]:
                    winsound.Beep(frequencia, duracao)
            except Exception:
                pass                # PC sem placa de som: tudo bem, segue sem som

        threading.Thread(target=bipar, daemon=True).start()


class AvisoNoTelao:
    """Uma faixa no alto da tela, por cima de tudo, que some sozinha. Avisos importantes nao sao
    trocados por avisos sem importancia (um grito nao apaga o "Bruno tambem invocou o dragao")."""

    def __init__(self, mestre):
        self.mestre = mestre
        self.janela = None
        self.importante = False
        self._sumir = None

    def mostrar(self, texto, segundos=5, importante=False):
        if self._aberta() and self.importante and not importante:
            return
        if not self._aberta():
            self.janela = tk.Toplevel(self.mestre)
            self.janela.overrideredirect(True)          # sem barra de titulo
            self.janela.attributes("-topmost", True)
            self.janela.configure(bg=AMARELO)
            self.rotulo = tk.Label(self.janela, bg=tema.CARD, fg=AMARELO, padx=36, pady=16,
                                   font=(tema.escolher_fonte(), -max(22, self.mestre.winfo_screenheight() // 30),
                                         "bold"))
            self.rotulo.pack(padx=3, pady=3)
            self.janela.bind("<Button-1>", lambda evento: self.fechar())
            self.rotulo.bind("<Button-1>", lambda evento: self.fechar())
        self.importante = importante
        self.rotulo.configure(text=texto)
        self.janela.update_idletasks()
        largura = self.janela.winfo_reqwidth()
        self.janela.geometry(f"+{(self.janela.winfo_screenwidth() - largura) // 2}+40")
        self.janela.lift()
        if self._sumir:
            self.mestre.after_cancel(self._sumir)
        self._sumir = self.mestre.after(segundos * 1000, self.fechar)

    def _aberta(self):
        return self.janela is not None and self.janela.winfo_exists()

    def fechar(self):
        if self._aberta():
            self.janela.destroy()
        self.janela = None
        self.importante = False
        self._sumir = None


class EfeitoDragao(tk.Toplevel):
    """Tela cheia por cima de tudo. Fica pelo menos 8 s e espera o pedido do aluno (mostrar_pedido).
    Clique ou Esc fecha antes."""

    def __init__(self, mestre, nome, opcoes, ao_fechar=None):
        super().__init__(mestre)
        self.nome = nome
        self.opcoes = opcoes                   # {1: "+3 pontos...", 2: ..., 3: ...}
        self.pedido = None
        self.pedido_em = None
        self.ao_fechar = ao_fechar
        self.inicio = time.time()
        self.fechando = None
        self.configure(bg=PRETO)
        self.attributes("-alpha", 0.0)
        self.attributes("-fullscreen", True)
        self.attributes("-topmost", True)
        self.largura, self.altura = self.winfo_screenwidth(), self.winfo_screenheight()
        self.canvas = tk.Canvas(self, width=self.largura, height=self.altura, bg=PRETO, highlightthickness=0,
                                cursor="hand2")
        self.canvas.pack(fill="both", expand=True)
        for evento in ("<Escape>", "<Button-1>", "<space>"):
            self.bind(evento, lambda e: self.fechar())
        self.after(50, self.focus_force)
        self.desenhar()

    def mostrar_pedido(self, opcao):
        self.pedido = opcao
        self.pedido_em = time.time()

    def fechar(self):
        if self.fechando is None:
            self.fechando = time.time()

    def _fonte(self, fracao, negrito=True):
        return (tema.escolher_fonte(), -max(14, int(self.altura * fracao)), "bold" if negrito else "normal")

    def desenhar(self):
        if not self.winfo_exists():
            return
        agora = time.time()
        t = agora - self.inicio
        pronto = t >= DURACAO_MINIMA and self.pedido_em is not None and agora - self.pedido_em >= DEPOIS_DO_PEDIDO
        if self.fechando is None and (pronto or t >= DURACAO_MAXIMA):
            self.fechando = agora
        # o fundo escurece (a janela vai ficando opaca) e, no fim, clareia de novo
        if self.fechando is not None:
            opacidade = max(0.0, 1 - (agora - self.fechando) / 0.6)
        else:
            opacidade = min(1.0, t / 0.8)
        self.attributes("-alpha", opacidade)
        if self.fechando is not None and opacidade <= 0:
            self.destroy()
            if self.ao_fechar:
                self.ao_fechar()
            return
        c, w, h = self.canvas, self.largura, self.altura
        c.delete("all")
        # o clarao: o fundo fica branco e volta ao preto em meio segundo
        if FLASH <= t < FLASH + 0.5:
            fundo = misturar("#FFFFFF", PRETO, (t - FLASH) / 0.5)
        else:
            fundo = PRETO
        c.configure(bg=fundo)
        # as 7 esferas girando: no comeco, em roda no meio da tela; depois do clarao, sobem para dar lugar ao texto
        mudanca = min(1.0, max(0.0, (t - FLASH) / 0.8))
        centro_y = h * (0.5 - 0.26 * mudanca)
        raio_da_roda = h * (0.27 - 0.13 * mudanca) * min(1.0, 0.3 + t / 1.2)
        velocidade = 0.6 + 2.6 * min(1.0, t / FLASH) if t < FLASH else 0.5
        angulo_base = t * velocidade
        tamanho = h * (0.06 - 0.012 * mudanca)
        brilho = 0.55 + 0.45 * math.sin(t * 6)
        for i in range(7):
            angulo = angulo_base + i * 2 * math.pi / 7
            x = w / 2 + raio_da_roda * math.cos(angulo)
            y = centro_y + raio_da_roda * math.sin(angulo)
            desenhar_esfera(c, x, y, tamanho, i + 1, brilho=brilho, fundo=fundo, giro=t * 0.8)
        if t < FLASH:
            return self.after(QUADRO, self.desenhar)
        # os textos aparecem depois do clarao
        cor_titulo = misturar(AMARELO, "#FFFFFF", 0.5 + 0.5 * math.sin(t * 4))
        c.create_text(w / 2, h * 0.52, text="O DRAGÃO FOI INVOCADO!", fill=cor_titulo, font=self._fonte(0.085))
        c.create_text(w / 2, h * 0.62, text=self.nome, fill="#FFFFFF", font=self._fonte(0.06))
        if self.pedido is None:
            restante = max(0, 30 - int(t))
            c.create_text(w / 2, h * 0.705, text=f"está escolhendo o pedido...  {restante}",
                          fill=tema.TEXTO_SECUNDARIO, font=self._fonte(0.03, negrito=False))
        else:
            c.create_text(w / 2, h * 0.705, text="pediu:", fill=tema.TEXTO_SECUNDARIO,
                          font=self._fonte(0.03, negrito=False))
        for posicao, (numero, texto) in enumerate(self.opcoes.items()):
            y = h * (0.775 + 0.065 * posicao)
            if self.pedido is None:
                cor, fonte = "#9A9DA3", self._fonte(0.032, negrito=False)
            elif self.pedido == numero:
                cor, fonte, texto = AMARELO, self._fonte(0.042), f"✔  {texto}"
            else:
                cor, fonte = "#4A4D52", self._fonte(0.028, negrito=False)
            c.create_text(w / 2, y, text=texto, fill=cor, font=fonte)
        self.after(QUADRO, self.desenhar)
