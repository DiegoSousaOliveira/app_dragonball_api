"""Pecas reaproveitadas em varias telas: o card do personagem, o mini-card, a barra de vida..."""

import customtkinter as ctk

from core import imagens
from interface import tema

RAIO = 8          # arredondado dos cantos do card (igual a imagem de referencia)


def preparar_foto(imagem, largura, altura, miniatura=False, texto_sem_foto="sem imagem"):
    """Monta a foto no tamanho certo, com os cantos de cima arredondados.
    Sem imagem (None): quadrado cinza com 'texto_sem_foto'. Devolve (CTkImage, texto).
    miniatura=True: corta a foto para mostrar so o rosto e o peito."""
    if imagem is None:
        pronta = imagens.imagem_lisa(largura, altura, tema.SEM_FOTO)
        texto = texto_sem_foto
    elif miniatura:
        pronta = imagens.miniatura(imagem, largura, altura)
        texto = ""
    else:
        pronta = imagens.foto_de_card(imagem, largura, altura)
        texto = ""
    pronta = imagens.arredondar_cantos_de_cima(pronta, RAIO, tema.FUNDO)
    return ctk.CTkImage(light_image=pronta, dark_image=pronta, size=(largura, altura)), texto


def selo_planeta(mestre, destruido):
    """Etiqueta colorida: vermelha 'Destruído' ou verde 'Preservado'.
    (Usamos cor de fundo em vez de emoji 🔴/🟢: o Tkinter desenha emojis sem cor.)"""
    if destruido:
        texto, cor = "Destruído", tema.PERIGO
    else:
        texto, cor = "Preservado", tema.SUCESSO
    return ctk.CTkLabel(mestre, text=texto, fg_color=cor, corner_radius=10, text_color=tema.FUNDO,
                        font=tema.fonte(13, negrito=True), height=24, width=96)


class CartaoPersonagem(ctk.CTkFrame):
    """O card do personagem, igual ao do site da API: foto em cima, dados embaixo.

    Uma CLASSE e um molde. CartaoPersonagem(janela, goku, foto) cria UM card a partir do molde.
    'self' e o proprio card que esta sendo criado.
    """

    def __init__(self, mestre, personagem, imagem=None, largura=290, altura_foto=350):
        super().__init__(mestre, corner_radius=RAIO, fg_color=tema.CARD)
        self.largura = largura
        self.altura_foto = altura_foto
        self.foto = ctk.CTkLabel(self, text="", corner_radius=0, text_color=tema.TEXTO,
                                 font=tema.fonte(16, negrito=True))
        self.foto.pack()
        self.trocar_foto(imagem)
        self.criar_textos(personagem)

    def trocar_foto(self, imagem):
        """Coloca (ou troca) a foto do card."""
        # IMPORTANTE: guardar a imagem em self.imagem. Se ela ficar so numa variavel
        # local, o Python joga fora quando a funcao termina e a foto some da janela.
        self.imagem, texto = preparar_foto(imagem, self.largura, self.altura_foto)
        self.foto.configure(image=self.imagem, text=texto, compound="center")

    def criar_textos(self, personagem):
        """Nome, raca - genero e os tres pares rotulo/valor."""
        area = ctk.CTkFrame(self, fg_color="transparent")
        area.pack(fill="x", padx=16, pady=(10, 14))
        self.nome = self.texto(area, personagem["name"], 22, tema.TEXTO)
        self.texto(area, f"{personagem['race']} - {personagem['gender']}", 16, tema.DESTAQUE)
        self.par(area, "Base KI:", personagem["ki"])
        self.par(area, "Total KI:", personagem["maxKi"])
        self.par(area, "Affiliation:", personagem["affiliation"])

    def texto(self, area, conteudo, tamanho, cor, espaco_acima=0):
        rotulo = ctk.CTkLabel(area, text=conteudo, font=tema.fonte(tamanho, negrito=True),
                              text_color=cor, anchor="w", height=tamanho + 6,
                              wraplength=self.largura - 32, justify="left")
        rotulo.pack(fill="x", pady=(espaco_acima, 0))
        return rotulo

    def par(self, area, rotulo, valor):
        """Um rotulo branco pequeno ('Base KI:') e embaixo o valor amarelo maior."""
        self.texto(area, rotulo, 13, tema.TEXTO, espaco_acima=8)
        self.texto(area, valor, 17, tema.DESTAQUE)


class MiniCartao(ctk.CTkFrame):
    """Card pequeno: foto, nome e raca. Clicar nele chama ao_clicar(personagem, imagem).
    'subtitulo' troca a raca por outro texto (usado nos planetas).
    Sem imagem ainda (imagem=None, carregando=True): mostra "carregando..." ate trocar_foto()."""

    def __init__(self, mestre, personagem, imagem, ao_clicar, largura=150, subtitulo=None,
                 cor_subtitulo=None, carregando=False):
        super().__init__(mestre, corner_radius=RAIO, fg_color=tema.CARD)
        self.personagem = personagem
        self.largura = largura
        self.imagem_original = imagem
        self.ao_clicar = ao_clicar
        if subtitulo is None:
            subtitulo = personagem["race"]
        self.foto = ctk.CTkLabel(self, text="", compound="center", font=tema.fonte(12))
        self.foto.pack()
        self._mostrar(imagem, "carregando..." if carregando else "sem imagem")
        nome = ctk.CTkLabel(self, text=personagem["name"], font=tema.fonte(14, negrito=True),
                            text_color=tema.TEXTO, wraplength=largura - 16, height=40)
        nome.pack(padx=8)
        raca = ctk.CTkLabel(self, text=subtitulo, font=tema.fonte(12, negrito=True),
                            text_color=cor_subtitulo or tema.DESTAQUE, height=18)
        raca.pack(padx=8, pady=(0, 8))
        # O clique pode cair na foto, no nome, na raca ou na borda: ligamos todos.
        for parte in (self, self.foto, nome, raca):
            parte.bind("<Button-1>", lambda evento: self.ao_clicar(self.personagem, self.imagem_original))
            parte.configure(cursor="hand2")

    def _mostrar(self, imagem, texto_sem_foto):
        self.imagem, texto = preparar_foto(imagem, self.largura, self.largura, miniatura=True,
                                           texto_sem_foto=texto_sem_foto)
        self.foto.configure(image=self.imagem, text=texto)

    def trocar_foto(self, imagem):
        self.imagem_original = imagem
        self._mostrar(imagem, "sem imagem")


class BarraDeVida(ctk.CTkFrame):
    """'HP 100/100' em cima de uma barra que esvazia. Fica vermelha quando o HP esta baixo."""

    def __init__(self, mestre, largura=200):
        super().__init__(mestre, fg_color="transparent")
        self.texto = ctk.CTkLabel(self, text="", font=tema.fonte(14, negrito=True), height=20)
        self.texto.pack()
        self.barra = ctk.CTkProgressBar(self, width=largura, height=14, progress_color=tema.SUCESSO)
        self.barra.pack()
        self.atualizar(100)

    def atualizar(self, hp, hp_maximo=100):
        self.texto.configure(text=f"HP {hp}/{hp_maximo}")
        self.barra.set(hp / hp_maximo)               # a barra vai de 0.0 (vazia) a 1.0 (cheia)
        cor = tema.PERIGO if hp < 30 else tema.SUCESSO
        self.barra.configure(progress_color=cor)
