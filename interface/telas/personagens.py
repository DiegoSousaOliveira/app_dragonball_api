"""Tela Personagens: busca com filtros e grade de mini-cards. Clicar abre o detalhe."""

import customtkinter as ctk

from core import api, filtros
from interface import janelas, tarefas, tema
from interface.componentes import MiniCartao
from interface.telas import Tela, cabecalho
from interface.telas.detalhe import JanelaPersonagem

TODAS = "Todas"
ORDENS = {"Nome (A-Z)": "nome", "Base KI (maior)": "ki", "Total KI (maior)": "maxKi"}
LARGURA_MINI = 150


class TelaPersonagens(Tela):
    def __init__(self, app):
        super().__init__(app)
        cabecalho(self, "Personagens", "Digite um nome ou use os filtros. Clique num card para ver tudo.")
        self.criar_filtros()
        self.area_sugestao = ctk.CTkFrame(self, fg_color="transparent", height=1)
        self.area_sugestao.pack(fill="x", padx=28)
        self.sugestao = ctk.CTkLabel(self.area_sugestao, text="", font=tema.fonte(14, negrito=True),
                                     text_color=tema.DESTAQUE, cursor="hand2")
        self.grade = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.grade.pack(fill="both", expand=True, padx=16, pady=(4, 16))
        self.minis = {}              # id -> MiniCartao (criados uma vez so)
        self.colunas = 0
        self._agendado = None
        self.criar_minis()
        self.bind("<Configure>", lambda evento: self.reorganizar_se_mudou())

    def criar_filtros(self):
        barra = ctk.CTkFrame(self, fg_color="transparent")
        barra.pack(fill="x", padx=24, pady=(4, 6))
        self.busca = ctk.CTkEntry(barra, width=240, height=36, placeholder_text="🔎 Buscar pelo nome...",
                                  font=tema.fonte(14))
        self.busca.pack(side="left")
        self.busca.bind("<KeyRelease>", lambda evento: self.filtrar_daqui_a_pouco())
        personagens = self.app.personagens
        self.raca = self.menu(barra, "Raça", [TODAS] + filtros.valores_unicos(personagens, "race"))
        self.afiliacao = self.menu(barra, "Afiliação", [TODAS] + filtros.valores_unicos(personagens, "affiliation"))
        self.genero = self.menu(barra, "Gênero", [TODAS] + filtros.valores_unicos(personagens, "gender"))
        self.ordem = self.menu(barra, "Ordem", list(ORDENS))
        self.contador = tema.texto_secundario(barra, "", 13)
        self.contador.pack(side="right")

    def menu(self, barra, rotulo, valores):
        ctk.CTkLabel(barra, text=rotulo, font=tema.fonte(12), text_color=tema.TEXTO_SECUNDARIO).pack(
            side="left", padx=(14, 4))
        opcao = ctk.CTkOptionMenu(barra, values=valores, width=130, height=32, fg_color=tema.CARD,
                                  button_color=tema.CARD, button_hover_color="#4A4E54",
                                  command=lambda valor: self.filtrar())
        opcao.pack(side="left")
        return opcao

    def criar_minis(self):
        for personagem in self.app.personagens:
            mini = MiniCartao(self.grade, personagem, None, self.abrir, largura=LARGURA_MINI, carregando=True)
            self.minis[personagem["id"]] = mini
            tarefas.carregar_foto(mini, personagem["image"], mini.trocar_foto)
        self.filtrar()

    def abrir(self, personagem, imagem):
        JanelaPersonagem(self.app, personagem, imagem)

    # ---------------- filtrar e organizar ----------------

    def filtrar_daqui_a_pouco(self):
        """Espera o aluno parar de digitar (300 ms) antes de filtrar."""
        if self._agendado:
            self.after_cancel(self._agendado)
        self._agendado = self.after(300, self.filtrar)

    def valor(self, menu):
        escolhido = menu.get()
        return None if escolhido == TODAS else escolhido

    def filtrar(self):
        self._agendado = None
        texto = self.busca.get().strip()
        achados = filtros.filtrar(self.app.personagens, texto, self.valor(self.raca),
                                  self.valor(self.afiliacao), self.valor(self.genero))
        achados = filtros.ordenar(achados, ORDENS[self.ordem.get()])
        self.visiveis = [p["id"] for p in achados]
        self.organizar()
        self.contador.configure(text=f"{len(achados)} de {len(self.app.personagens)}")
        self.mostrar_sugestao(texto, achados)

    def mostrar_sugestao(self, texto, achados):
        self.sugestao.pack_forget()
        if achados or not texto:
            return
        sugerido = api.sugerir_personagem(texto, self.app.personagens)
        if sugerido is None:
            self.sugestao.configure(text=f'Nenhum personagem com "{texto}".')
            self.sugestao.unbind("<Button-1>")
        else:
            self.sugestao.configure(text=f'Nenhum "{texto}"... Você quis dizer {sugerido["name"]}? (clique)')
            self.sugestao.bind("<Button-1>", lambda evento: self.usar_sugestao(sugerido["name"]))
        self.sugestao.pack(anchor="w")

    def usar_sugestao(self, nome):
        self.busca.delete(0, "end")
        self.busca.insert(0, nome)
        self.filtrar()

    def colunas_que_cabem(self):
        # winfo_width vem em pixels de verdade; os cards sao medidos em pixels "logicos" (antes da escala)
        largura = self.winfo_width() / janelas.escala(self) - 60       # margens + barra de rolagem
        return max(1, int(largura // (LARGURA_MINI + 16)))

    def reorganizar_se_mudou(self):
        if self.colunas_que_cabem() != self.colunas:
            self.organizar()

    def organizar(self):
        """Mostra so os cards filtrados, na ordem certa, preenchendo as colunas que cabem."""
        self.colunas = self.colunas_que_cabem()
        for mini in self.minis.values():
            mini.grid_forget()
        for posicao, id_personagem in enumerate(getattr(self, "visiveis", [])):
            self.minis[id_personagem].grid(row=posicao // self.colunas, column=posicao % self.colunas,
                                           padx=8, pady=8, sticky="n")
