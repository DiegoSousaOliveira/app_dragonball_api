"""Tela Ranking: os mais fortes em barras com escala de logaritmo."""

import customtkinter as ctk

from core import filtros
from core.poder import escala_log, formatar_ki
from interface import tarefas, tema
from interface.componentes import preparar_foto
from interface.telas import Tela, cabecalho
from interface.telas.detalhe import JanelaPersonagem

TODAS = "Todas"
METRICAS = {"Total KI": "maxKi", "Base KI": "ki"}
SOBRESCRITO = str.maketrans("0123456789", "⁰¹²³⁴⁵⁶⁷⁸⁹")


def ki_bonito(ki):
    """'9.0 x 10^25' -> '9.0 × 10²⁵'."""
    texto = formatar_ki(ki)
    if "^" not in texto:
        return texto
    numero, expoente = texto.split("^")
    return numero.replace(" x ", " × ") + expoente.translate(SOBRESCRITO)


class LinhaRanking(ctk.CTkFrame):
    """#posicao, foto, nome, barra (log) e valor. Clicar abre o personagem."""

    def __init__(self, mestre, app, posicao, personagem, ki, maior):
        super().__init__(mestre, fg_color=tema.CARD, corner_radius=8)
        ctk.CTkLabel(self, text=f"#{posicao}", width=44, font=tema.fonte(16, negrito=True),
                     text_color=tema.DESTAQUE).pack(side="left", padx=(8, 0))
        self.foto = ctk.CTkLabel(self, text="", font=tema.fonte(8))
        self.foto.pack(side="left", padx=8, pady=6)
        self.trocar_foto(None, "...")
        ctk.CTkLabel(self, text=personagem["name"], width=170, anchor="w",
                     font=tema.fonte(14, negrito=True)).pack(side="left")
        barra = ctk.CTkProgressBar(self, height=16, progress_color=tema.DESTAQUE)
        barra.set(escala_log(ki, maior))
        barra.pack(side="left", padx=8, fill="x", expand=True)
        ctk.CTkLabel(self, text=ki_bonito(ki), width=120, anchor="e",
                     font=tema.fonte(13, negrito=True)).pack(side="left", padx=(0, 14))
        self.foto.bind("<Button-1>", lambda evento: JanelaPersonagem(app, personagem, self.imagem_original))
        self.foto.configure(cursor="hand2")
        self.imagem_original = None
        tarefas.carregar_foto(self, personagem["image"], self.trocar_foto)

    def trocar_foto(self, imagem, texto_sem_foto="?"):
        self.imagem_original = imagem
        self.imagem, texto = preparar_foto(imagem, 48, 48, miniatura=True, texto_sem_foto=texto_sem_foto)
        self.foto.configure(image=self.imagem, text=texto)


class TelaRanking(Tela):
    def __init__(self, app):
        super().__init__(app)
        cabecalho(self, "Ranking de poder", "As barras usam escala de LOGARITMO: cada pedacinho a mais = 10x mais forte.")
        barra = ctk.CTkFrame(self, fg_color=tema.CARD, corner_radius=10)
        barra.pack(fill="x", padx=24, pady=(4, 8))
        miolo = ctk.CTkFrame(barra, fg_color="transparent")
        miolo.pack(padx=14, pady=10, anchor="w")
        self.metrica = ctk.CTkSegmentedButton(miolo, values=list(METRICAS), command=lambda v: self.montar(),
                                              selected_color=tema.DESTAQUE, selected_hover_color=tema.DESTAQUE_ESCURO,
                                              font=tema.fonte(13, negrito=True))
        self.metrica.set("Total KI")
        self.metrica.pack(side="left")
        tema.texto_secundario(miolo, "Raça").pack(side="left", padx=(20, 4))
        self.raca = ctk.CTkOptionMenu(miolo, values=[TODAS] + filtros.valores_unicos(app.personagens, "race"),
                                      command=lambda v: self.montar(), fg_color=tema.FUNDO, button_color=tema.FUNDO)
        self.raca.pack(side="left")
        tema.texto_secundario(miolo, "Quantos").pack(side="left", padx=(20, 4))
        self.quantos = ctk.CTkSegmentedButton(miolo, values=["5", "10", "20"], command=lambda v: self.montar(),
                                              selected_color=tema.DESTAQUE, selected_hover_color=tema.DESTAQUE_ESCURO,
                                              font=tema.fonte(13, negrito=True))
        self.quantos.set("10")
        self.quantos.pack(side="left")
        self.lista = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.lista.pack(fill="both", expand=True, padx=16)
        self.rodape = tema.texto_secundario(self, "", 12, wraplength=900)
        self.rodape.pack(pady=(4, 12))
        self.montar()

    def montar(self):
        for filho in self.lista.winfo_children():
            filho.destroy()
        raca = None if self.raca.get() == TODAS else self.raca.get()
        ranking, ignorados = filtros.montar_ranking(self.app.personagens, METRICAS[self.metrica.get()],
                                                    int(self.quantos.get()), raca)
        if not ranking:
            tema.texto_secundario(self.lista, "Ninguém com ki conhecido nesse filtro.", 15).pack(pady=40)
        maior = ranking[0][1] if ranking else 1
        for posicao, (personagem, ki) in enumerate(ranking, start=1):
            LinhaRanking(self.lista, self.app, posicao, personagem, ki, maior).pack(fill="x", pady=4, padx=4)
        self.rodape.configure(text=f"{ignorados} personagem(ns) ficaram de fora porque o ki é 0 ou desconhecido "
                                   "(\"unknown\"): na escala de logaritmo o 0 não cabe, log(0) não existe!")
