"""
O que aparece no telao durante a Caca as Esferas:
  - EfeitoDragao: tela cheia quando o 1o aluno junta as 7 esferas (fundo escurece, esferas girando e brilhando,
    flash de luz, o dragao aparecendo, "O DRAGAO FOI INVOCADO!", o nome do aluno e o pedido).
    O dragao e a figura interface/imagens/shenlong.png. Se esse arquivo nao existir, aparece um dragao
    desenhado com formas do Canvas (interface/desenho_dragao.py).
  - AvisoNoTelao: uma faixa no alto da tela por alguns segundos ("Bruno tambem invocou o dragao!").
  - Som: bipes com o winsound (so existe no Windows; em outro sistema fica mudo).
"""

import math
import threading
import time
import tkinter as tk

from PIL import Image, ImageEnhance, ImageTk

from core.armazenamento import PASTA_RECURSOS
from interface import tema
from interface.desenho_dragao import desenhar_dragao
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
TEXTOS_DEPOIS = 1.6                 # segundos depois do clarao (o dragao aparece primeiro)
PRETO = "#000000"
AMARELO = tema.DESTAQUE
ARQUIVO_DA_FIGURA = PASTA_RECURSOS / "interface" / "imagens" / "shenlong.png"
ALTURA_DA_FIGURA = 0.6              # fracao da altura da tela
LUZES = [i / 10 for i in range(17)]  # luminosidades da figura: de 0 (preto) a 1.6 (estourada de luz)

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


class FiguraDoDragao:
    """A figura do dragao preparada em varias luminosidades. O Tkinter nao tem transparencia; como o fundo da
    figura e preto, ela 'acende' trocando de uma versao mais escura para uma mais clara."""

    def __init__(self, altura_da_tela):
        imagem = Image.open(ARQUIVO_DA_FIGURA).convert("RGB")
        self.altura = int(altura_da_tela * ALTURA_DA_FIGURA)
        imagem = imagem.resize((round(imagem.width * self.altura / imagem.height), self.altura), Image.LANCZOS)
        clarear = ImageEnhance.Brightness(imagem)
        self.versoes = [ImageTk.PhotoImage(clarear.enhance(luz)) for luz in LUZES]   # guardadas: senao somem

    def desenhar(self, canvas, x, y, desde):
        """desde = segundos desde que o dragao comecou a aparecer (antes disso, nada)."""
        if desde <= 0:
            return
        if desde < 1.0:
            luz = 1.6 * desde                          # acende e passa do ponto (um clarao verde)...
        elif desde < 1.6:
            luz = 1.6 - (desde - 1.0)                  # ...e volta ao normal
        else:
            luz = 1.0
        versao = self.versoes[min(len(LUZES) - 1, round(luz * 10))]
        respiracao = math.sin(desde * 1.3) * self.altura * 0.01
        canvas.create_image(x, y + respiracao, image=versao)


def carregar_figura(altura_da_tela):
    """A figura do dragao, ou None se o arquivo nao existir (ai o efeito usa o dragao desenhado)."""
    if not ARQUIVO_DA_FIGURA.exists():
        return None
    try:
        return FiguraDoDragao(altura_da_tela)
    except Exception:
        return None


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
        self.figura = carregar_figura(self.altura)
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
        desenhar_cena(self.canvas, self.largura, self.altura, t, self.nome, self.opcoes, self.pedido,
                      self.figura)
        self.after(QUADRO, self.desenhar)


def _fonte(altura, fracao, negrito=True):
    return (tema.escolher_fonte(), -max(14, int(altura * fracao)), "bold" if negrito else "normal")


def _suave(x):
    """0 a 1, comecando rapido e terminando devagar."""
    x = min(1.0, max(0.0, x))
    return 1 - (1 - x) ** 2


def desenhar_cena(c, w, h, t, nome, opcoes, pedido, figura=None):
    """Um quadro do efeito, t segundos depois do comeco (separado da janela para dar para testar).
    figura: FiguraDoDragao (a imagem) ou None (usa o dragao desenhado)."""
    c.delete("all")
    # o clarao: o fundo fica branco e volta ao preto em meio segundo
    if FLASH <= t < FLASH + 0.5:
        fundo = misturar("#FFFFFF", PRETO, (t - FLASH) / 0.5)
    else:
        fundo = PRETO
    c.configure(bg=fundo)
    centro_figura = h * (0.02 + ALTURA_DA_FIGURA / 2)
    if figura is not None:
        figura.desenhar(c, w / 2, centro_figura, t - FLASH - 0.4)     # acende quando o clarao vai embora
    else:
        progresso = (t - FLASH - 0.15) / 1.8                         # o dragao desenhado nasce das esferas
        desenhar_dragao(c, w, h, _suave(progresso) if progresso < 1 else progresso, t, fundo)
    # as 7 esferas: antes do clarao, uma roda grande girando no meio da tela; depois, vao para perto do dragao
    # (com a figura: um "U" em volta dela; com o desenho: uma rodinha aos pes dele)
    mudanca = _suave((t - FLASH) / 0.8)
    abrir = min(1.0, 0.3 + t / 1.2)
    velocidade = 0.6 + 2.6 * min(1.0, t / FLASH) if t < FLASH else 0.7
    brilho = 0.55 + 0.45 * math.sin(t * 6)
    tamanho = h * (0.06 - (0.024 if figura is not None else 0.034) * mudanca)
    for i in range(7):
        angulo = t * velocidade + i * 2 * math.pi / 7
        x0 = w / 2 + h * 0.27 * abrir * math.cos(angulo)
        y0 = h * 0.5 + h * 0.27 * abrir * math.sin(angulo)
        if figura is not None:
            posicao = math.pi * (1 - i / 6)                            # 1 estrela na esquerda, 7 na direita
            x1 = w / 2 + h * 0.34 * math.cos(posicao)
            y1 = centro_figura + h * 0.235 * math.sin(posicao) + h * 0.008 * math.sin(t * 2 + i)
        else:
            x1 = w / 2 + h * 0.075 * math.cos(angulo)
            y1 = h * 0.40 + h * 0.075 * math.sin(angulo)
        x, y = x0 + (x1 - x0) * mudanca, y0 + (y1 - y0) * mudanca
        desenhar_esfera(c, x, y, tamanho, i + 1, brilho=brilho, fundo=fundo, giro=t * 0.8)
    if t < FLASH + TEXTOS_DEPOIS:
        return
    # os textos aparecem quando o dragao ja esta inteiro
    topo = 0.655 if figura is not None else 0.565
    cor_titulo = misturar(AMARELO, "#FFFFFF", 0.5 + 0.5 * math.sin(t * 4))
    c.create_text(w / 2, h * topo, text="O DRAGÃO FOI INVOCADO!", fill=cor_titulo, font=_fonte(h, 0.068))
    c.create_text(w / 2, h * (topo + 0.075), text=nome, fill="#FFFFFF", font=_fonte(h, 0.05))
    if pedido is None:
        restante = max(0, 30 - int(t))
        c.create_text(w / 2, h * (topo + 0.14), text=f"está escolhendo o pedido...  {restante}",
                      fill=tema.TEXTO_SECUNDARIO, font=_fonte(h, 0.027, negrito=False))
    else:
        c.create_text(w / 2, h * (topo + 0.14), text="pediu:", fill=tema.TEXTO_SECUNDARIO,
                      font=_fonte(h, 0.027, negrito=False))
    for posicao, (numero, texto) in enumerate(opcoes.items()):
        y = h * (topo + 0.195 + 0.052 * posicao)
        if pedido is None:
            cor, fonte = "#9A9DA3", _fonte(h, 0.029, negrito=False)
        elif pedido == numero:
            cor, fonte, texto = AMARELO, _fonte(h, 0.038), f"✔  {texto}"
        else:
            cor, fonte = "#4A4D52", _fonte(h, 0.026, negrito=False)
        c.create_text(w / 2, y, text=texto, fill=cor, font=fonte)
