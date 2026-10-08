"""Tela Planetas: grade com os 20 planetas. Clicar abre o planeta com os moradores."""

import customtkinter as ctk

from interface import janelas, tarefas, tema
from interface.componentes import MiniCartao
from interface.telas import Tela, cabecalho
from interface.telas.detalhe import JanelaPlaneta

LARGURA_MINI = 150


class TelaPlanetas(Tela):
    def __init__(self, app):
        super().__init__(app)
        destruidos = sum(1 for p in app.planetas if p["isDestroyed"])
        cabecalho(self, "Planetas", f"{len(app.planetas)} planetas, {destruidos} destruídos. "
                                    "Clique para ver a descrição e quem nasceu lá.")
        self.grade = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.grade.pack(fill="both", expand=True, padx=16, pady=(4, 16))
        self.minis = []
        for planeta in app.planetas:
            situacao = "Destruído" if planeta["isDestroyed"] else "Preservado"
            cor = tema.PERIGO if planeta["isDestroyed"] else tema.SUCESSO
            mini = MiniCartao(self.grade, planeta, None, self.abrir, largura=LARGURA_MINI,
                              subtitulo=situacao, cor_subtitulo=cor, carregando=True)
            self.minis.append(mini)
            tarefas.carregar_foto(mini, planeta["image"], mini.trocar_foto)
        self.colunas = 0
        self.bind("<Configure>", lambda evento: self.organizar())
        self.organizar()

    def abrir(self, planeta, imagem):
        JanelaPlaneta(self.app, planeta, imagem)

    def organizar(self):
        largura = self.winfo_width() / janelas.escala(self) - 60       # pixels "logicos", como os cards
        colunas = max(1, int(largura // (LARGURA_MINI + 16)))
        if colunas == self.colunas:
            return
        self.colunas = colunas
        for posicao, mini in enumerate(self.minis):
            mini.grid(row=posicao // colunas, column=posicao % colunas, padx=8, pady=8, sticky="n")
