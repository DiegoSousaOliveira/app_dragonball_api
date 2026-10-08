"""Janelas de detalhe: personagem (card + descricao + planeta + transformacoes) e planeta."""

import customtkinter as ctk

from core import api
from interface import janelas, tarefas, tema
from interface.componentes import CartaoPersonagem, MiniCartao, RAIO, preparar_foto, selo_planeta


def subtitulo(painel, texto):
    ctk.CTkLabel(painel, text=texto, font=tema.fonte(15, negrito=True),
                 text_color=tema.TEXTO).pack(anchor="w", padx=16, pady=(14, 6))


class JanelaPersonagem:
    """Card a esquerda; a direita descricao, planeta de origem e o botao das transformacoes.
    Abre na hora com o que ja temos; o detalhe chega em segundo plano."""

    def __init__(self, mestre, personagem, imagem=None):
        self.janela = janelas.criar_janela(mestre, personagem["name"], 720, 630)
        self.cartao = CartaoPersonagem(self.janela, personagem, imagem)
        self.cartao.grid(row=0, column=0, padx=20, pady=20, sticky="n")
        self.painel = ctk.CTkFrame(self.janela, fg_color=tema.CARD, corner_radius=RAIO, width=340)
        self.painel.grid(row=0, column=1, padx=(0, 20), pady=20, sticky="nsew")
        self.janela.grid_rowconfigure(0, weight=1)
        self.carregando = tema.texto_secundario(self.painel, "Carregando detalhes...", 14)
        self.carregando.pack(pady=40, padx=60)
        if imagem is None:
            tarefas.carregar_foto(self.janela, personagem["image"], self.cartao.trocar_foto)
        tarefas.em_segundo_plano(self.janela, lambda: api.detalhar_personagem(personagem["id"]),
                                 self.preencher, self.falhou)

    def falhou(self, erro):
        self.carregando.configure(text=f"Não consegui carregar os detalhes.\n{erro}", text_color=tema.PERIGO)

    def preencher(self, detalhe):
        self.carregando.destroy()
        subtitulo(self.painel, "📜 Descrição (em espanhol)")
        caixa = ctk.CTkTextbox(self.painel, width=330, height=330, wrap="word", font=tema.fonte(14),
                               fg_color=tema.FUNDO, text_color=tema.TEXTO_SECUNDARIO)
        caixa.insert("1.0", detalhe.get("description", ""))
        caixa.configure(state="disabled")
        caixa.pack(padx=16)
        planeta = detalhe.get("originPlanet")
        if planeta:
            subtitulo(self.painel, "🪐 Planeta de origem")
            linha = ctk.CTkFrame(self.painel, fg_color="transparent")
            linha.pack(anchor="w", padx=16)
            ctk.CTkLabel(linha, text=planeta["name"], font=tema.fonte(16, negrito=True),
                         text_color=tema.DESTAQUE).pack(side="left", padx=(0, 10))
            selo_planeta(linha, planeta["isDestroyed"]).pack(side="left")
        transformacoes = detalhe.get("transformations", [])
        if transformacoes:
            texto = f"Ver transformações ▶  ({len(transformacoes)})"
            tema.botao(self.painel, texto, lambda: Carrossel(self.janela, transformacoes),
                       largura=240).pack(pady=20)
        else:
            tema.texto_secundario(self.painel, "Este personagem não tem transformações.").pack(pady=20)


class Carrossel:
    """Mostra as transformacoes uma de cada vez, com os botoes ◀ e ▶."""

    def __init__(self, mestre, transformacoes):
        self.transformacoes = transformacoes
        self.fotos = {}                       # indice -> imagem (chegam em segundo plano)
        self.indice = 0
        self.janela = janelas.criar_janela(mestre, "Transformações", 340, 530)
        self.foto = ctk.CTkLabel(self.janela, text="", font=tema.fonte(16, negrito=True))
        self.foto.pack(pady=(20, 10))
        self.nome = ctk.CTkLabel(self.janela, text="", font=tema.fonte(20, negrito=True),
                                 text_color=tema.DESTAQUE)
        self.nome.pack()
        self.ki = ctk.CTkLabel(self.janela, text="", font=tema.fonte(15))
        self.ki.pack()
        linha = ctk.CTkFrame(self.janela, fg_color="transparent")
        linha.pack(pady=12)
        tema.botao(linha, "◀", self.anterior, largura=60).pack(side="left")
        self.contador = ctk.CTkLabel(linha, text="", width=90)
        self.contador.pack(side="left")
        tema.botao(linha, "▶", self.proxima, largura=60).pack(side="left")
        for indice, transformacao in enumerate(transformacoes):
            tarefas.carregar_foto(self.janela, transformacao["image"],
                                  lambda imagem, i=indice: self.chegou_foto(i, imagem))
        self.mostrar()

    def chegou_foto(self, indice, imagem):
        self.fotos[indice] = imagem
        if indice == self.indice:
            self.mostrar()

    def mostrar(self):
        transformacao = self.transformacoes[self.indice]
        texto_sem_foto = "sem imagem" if self.indice in self.fotos else "carregando..."
        self.imagem, texto = preparar_foto(self.fotos.get(self.indice), 280, 360, texto_sem_foto=texto_sem_foto)
        self.foto.configure(image=self.imagem, text=texto, compound="center")
        self.nome.configure(text=transformacao["name"])
        self.ki.configure(text=f"KI: {transformacao['ki']}")
        self.contador.configure(text=f"{self.indice + 1} de {len(self.transformacoes)}")

    def proxima(self):
        self.indice = (self.indice + 1) % len(self.transformacoes)     # depois da ultima, a primeira
        self.mostrar()

    def anterior(self):
        self.indice = (self.indice - 1) % len(self.transformacoes)
        self.mostrar()


class JanelaPlaneta:
    """Card do planeta a esquerda; moradores (clicaveis) a direita."""

    LARGURA_FOTO = 380

    def __init__(self, mestre, planeta, imagem=None):
        self.mestre = mestre
        self.janela = janelas.criar_janela(mestre, planeta["name"], 800, 600)
        self.criar_cartao(planeta, imagem)
        lado = ctk.CTkFrame(self.janela, fg_color="transparent")
        lado.grid(row=0, column=1, pady=20, sticky="n")
        self.titulo_moradores = ctk.CTkLabel(lado, text="👥 Moradores", font=tema.fonte(16, negrito=True),
                                             text_color=tema.DESTAQUE)
        self.titulo_moradores.pack(anchor="w")
        self.lista = ctk.CTkScrollableFrame(lado, width=330, height=500, fg_color=tema.FUNDO)
        self.lista.pack()
        self.carregando = tema.texto_secundario(self.lista, "Carregando...")
        self.carregando.grid(row=0, column=0, pady=20)
        if imagem is None:
            tarefas.carregar_foto(self.janela, planeta["image"], self.trocar_foto)
        tarefas.em_segundo_plano(self.janela, lambda: api.detalhar_planeta(planeta["id"]),
                                 self.mostrar_moradores,
                                 lambda erro: self.carregando.configure(text=f"Erro: {erro}"))

    def criar_cartao(self, planeta, imagem):
        cartao = ctk.CTkFrame(self.janela, corner_radius=RAIO, fg_color=tema.CARD)
        cartao.grid(row=0, column=0, padx=20, pady=20, sticky="n")
        self.foto = ctk.CTkLabel(cartao, text="", compound="center")
        self.foto.pack()
        self.trocar_foto(imagem, "carregando...")
        linha = ctk.CTkFrame(cartao, fg_color="transparent")
        linha.pack(fill="x", padx=16, pady=(12, 8))
        ctk.CTkLabel(linha, text=planeta["name"], font=tema.fonte(22, negrito=True),
                     wraplength=240, justify="left").pack(side="left")
        selo_planeta(linha, planeta["isDestroyed"]).pack(side="right")
        caixa = ctk.CTkTextbox(cartao, width=self.LARGURA_FOTO - 32, height=170, wrap="word",
                               font=tema.fonte(13), fg_color=tema.FUNDO, text_color=tema.TEXTO_SECUNDARIO)
        caixa.insert("1.0", planeta.get("description", ""))
        caixa.configure(state="disabled")
        caixa.pack(padx=16, pady=(0, 16))

    def trocar_foto(self, imagem, texto_sem_foto="sem imagem"):
        self.imagem, texto = preparar_foto(imagem, self.LARGURA_FOTO, 250, miniatura=True,
                                           texto_sem_foto=texto_sem_foto)
        self.foto.configure(image=self.imagem, text=texto)

    def mostrar_moradores(self, detalhe):
        self.carregando.destroy()
        moradores = detalhe.get("characters", [])
        self.titulo_moradores.configure(text=f"👥 Moradores ({len(moradores)})")
        if not moradores:
            tema.texto_secundario(self.lista, "Nenhum personagem da API\nnasceu neste planeta.",
                                  justify="left").grid(row=0, column=0, pady=10)
            return
        for posicao, morador in enumerate(moradores):
            mini = MiniCartao(self.lista, morador, None,
                              lambda personagem, foto: JanelaPersonagem(self.mestre, personagem, foto),
                              carregando=True)
            mini.grid(row=posicao // 2, column=posicao % 2, padx=6, pady=6, sticky="n")
            tarefas.carregar_foto(mini, morador["image"], mini.trocar_foto)
