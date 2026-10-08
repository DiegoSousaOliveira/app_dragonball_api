"""Tela Turma: quem esta na sala (para desafiar), o podio e a classificacao dos alunos."""

import customtkinter as ctk

from core import api, turma
from interface import tarefas, tema
from interface.telas import Tela, cabecalho
from interface.telas.desafios import JanelaDesafiar

ATUALIZAR_PLACAR_A_CADA = 4000       # milissegundos
ESTADOS = {"livre": ("Livre", tema.SUCESSO), "em_batalha": ("Lutando", tema.PERIGO),
           "em_quiz": ("No quiz", tema.DESTAQUE), "ausente": ("Ausente", tema.TEXTO_SECUNDARIO)}
OURO, PRATA, BRONZE = "#FAC02D", "#C0C4CC", "#CD7F32"


class TelaTurma(Tela):
    def __init__(self, app):
        super().__init__(app)
        cabecalho(self, "Turma", "Desafie um colega que esteja livre. Vitória = 3 pontos, derrota = 1 ponto.")
        self._agendado = None
        self._assinatura_sala = None
        self._assinatura_placar = None
        if not api.conectado_ao_servidor():
            tema.texto_secundario(self, "🔌 Você está usando a internet direto.\n\nPara desafiar colegas e entrar no "
                                        "placar, clique em \"Trocar conexão\" e conecte-se ao servidor do professor.",
                                  16, justify="center").pack(pady=80)
            self.lista = None
            return
        corpo = ctk.CTkFrame(self, fg_color="transparent")
        corpo.pack(fill="both", expand=True, padx=20, pady=(4, 14))
        corpo.grid_columnconfigure(1, weight=1)
        corpo.grid_rowconfigure(0, weight=1)
        esquerda = ctk.CTkFrame(corpo, fg_color=tema.CARD, corner_radius=10, width=300)
        esquerda.grid(row=0, column=0, sticky="nsw", padx=(0, 10))
        esquerda.grid_propagate(False)
        esquerda.pack_propagate(False)
        self.titulo_sala = ctk.CTkLabel(esquerda, text="🟢 Na sala agora", font=tema.fonte(17, negrito=True),
                                        text_color=tema.DESTAQUE)
        self.titulo_sala.pack(anchor="w", padx=14, pady=(12, 6))
        self.lista = ctk.CTkScrollableFrame(esquerda, fg_color="transparent")
        self.lista.pack(fill="both", expand=True, padx=4, pady=(0, 8))
        direita = ctk.CTkFrame(corpo, fg_color="transparent")
        direita.grid(row=0, column=1, sticky="nsew")
        self.podio = ctk.CTkFrame(direita, fg_color=tema.CARD, corner_radius=10, height=230)
        self.podio.pack(fill="x")
        self.podio.pack_propagate(False)
        self.tabela = ctk.CTkScrollableFrame(direita, fg_color=tema.CARD, corner_radius=10)
        self.tabela.pack(fill="both", expand=True, pady=(10, 0))
        self.regra = tema.texto_secundario(direita, "", 12)
        self.regra.pack(anchor="w", pady=(4, 0))

    def ao_mostrar(self):
        if self.lista is not None:
            self.atualizar_sala(self.app.estado_sala)
            self.atualizar_placar()

    def ao_esconder(self):
        if self._agendado:
            self.after_cancel(self._agendado)
            self._agendado = None

    # ---------------- quem esta na sala (vem do app, que pergunta ao servidor a cada 1,5 s) ----------------

    def atualizar_sala(self, estado):
        if self.lista is None or estado is None:
            return
        livre_para_desafiar = self.app.desafio_enviado is None and estado.get("partida") is None
        assinatura = ([(j["id"], j["estado"]) for j in estado["jogadores"]], livre_para_desafiar)
        if assinatura == self._assinatura_sala:
            return                                           # nada mudou: nao redesenha (evita piscar)
        self._assinatura_sala = assinatura
        for filho in self.lista.winfo_children():
            filho.destroy()
        self.titulo_sala.configure(text=f"🟢 Na sala agora ({len(estado['jogadores'])})")
        for jogador in estado["jogadores"]:
            self.linha_de_jogador(jogador, livre_para_desafiar)

    def linha_de_jogador(self, jogador, livre_para_desafiar):
        linha = ctk.CTkFrame(self.lista, fg_color=tema.FUNDO, corner_radius=8)
        linha.pack(fill="x", pady=3, padx=4)
        texto_estado, cor = ESTADOS.get(jogador["estado"], ESTADOS["ausente"])
        info = ctk.CTkFrame(linha, fg_color="transparent")
        info.pack(side="left", padx=10, pady=6)
        nome = jogador["nome"] + ("  (você)" if jogador["voce"] else "")
        ctk.CTkLabel(info, text=nome, font=tema.fonte(14, negrito=True), anchor="w",
                     text_color=tema.DESTAQUE if jogador["voce"] else tema.TEXTO).pack(anchor="w")
        ctk.CTkLabel(info, text=f"● {texto_estado}", font=tema.fonte(12), text_color=cor, anchor="w").pack(anchor="w")
        if jogador["voce"]:
            return
        pode = livre_para_desafiar and jogador["estado"] == "livre"
        for icone, tipo in (("❓", "quiz"), ("⚔", "batalha")):
            botao = tema.botao(linha, icone, lambda t=tipo: JanelaDesafiar(self.app, jogador, t), largura=40)
            botao.pack(side="right", padx=(0, 8))
            if not pode:
                botao.configure(state="disabled")

    # ---------------- podio e classificacao ----------------

    def atualizar_placar(self):
        tarefas.em_segundo_plano(self, turma.placar, self.mostrar_placar, lambda erro: None)
        self._agendado = self.after(ATUALIZAR_PLACAR_A_CADA, self.atualizar_placar) if self.visivel else None

    def mostrar_placar(self, placar):
        classificacao = placar.get("classificacao", [])
        assinatura = [(a["nome"], a["pontos"], a["batalha_v"], a["quiz_v"]) for a in classificacao]
        if assinatura == self._assinatura_placar:
            return
        self._assinatura_placar = assinatura
        self.desenhar_podio(classificacao[:3])
        self.desenhar_tabela(classificacao)
        self.regra.configure(text=placar.get("regra", ""))

    def desenhar_podio(self, primeiros):
        for filho in self.podio.winfo_children():
            filho.destroy()
        ctk.CTkLabel(self.podio, text="🏆 Pódio", font=tema.fonte(17, negrito=True),
                     text_color=tema.DESTAQUE).place(x=14, y=10)
        if not primeiros:
            tema.texto_secundario(self.podio, "Ninguém duelou ainda. Desafie um colega!", 15).place(
                relx=0.5, rely=0.55, anchor="center")
            return
        degraus = ctk.CTkFrame(self.podio, fg_color="transparent")
        degraus.place(relx=0.5, rely=1.0, anchor="s")
        # ordem classica do podio: 2o lugar, 1o lugar, 3o lugar
        for posicao, altura, cor in ((2, 70, PRATA), (1, 105, OURO), (3, 45, BRONZE)):
            coluna = ctk.CTkFrame(degraus, fg_color="transparent", width=170)
            coluna.pack(side="left", padx=6, anchor="s")
            if posicao <= len(primeiros):
                aluno = primeiros[posicao - 1]
                ctk.CTkLabel(coluna, text=aluno["nome"], font=tema.fonte(15, negrito=True),
                             wraplength=160).pack()
                ctk.CTkLabel(coluna, text=f"{aluno['pontos']} pts", font=tema.fonte(13),
                             text_color=tema.TEXTO_SECUNDARIO).pack()
            bloco = ctk.CTkFrame(coluna, fg_color=cor if posicao <= len(primeiros) else tema.FUNDO,
                                 width=160, height=altura, corner_radius=6)
            bloco.pack(pady=(4, 0))
            bloco.pack_propagate(False)
            ctk.CTkLabel(bloco, text=f"{posicao}º", font=tema.fonte(26, negrito=True),
                         text_color=tema.FUNDO).pack(expand=True)

    def desenhar_tabela(self, classificacao):
        for filho in self.tabela.winfo_children():
            filho.destroy()
        colunas = [("#", 40), ("Aluno", 200), ("⚔ Batalhas (V/D)", 150), ("❓ Quiz (V/D)", 130), ("Pontos", 80)]
        self.linha_da_tabela([c for c, _ in colunas], colunas, tema.TEXTO_SECUNDARIO, negrito=True)
        meu_nome = (self.app.estado_sala or {}).get("voce", {}).get("nome")
        for posicao, aluno in enumerate(classificacao, start=1):
            valores = [f"{posicao}º", aluno["nome"], f"{aluno['batalha_v']} / {aluno['batalha_d']}",
                       f"{aluno['quiz_v']} / {aluno['quiz_d']}", str(aluno["pontos"])]
            cor = tema.DESTAQUE if aluno["nome"] == meu_nome else tema.TEXTO
            self.linha_da_tabela(valores, colunas, cor, negrito=aluno["nome"] == meu_nome)
        if not classificacao:
            tema.texto_secundario(self.tabela, "A classificação aparece depois do primeiro duelo.", 14).pack(pady=20)

    def linha_da_tabela(self, valores, colunas, cor, negrito=False):
        linha = ctk.CTkFrame(self.tabela, fg_color="transparent")
        linha.pack(fill="x", padx=8, pady=1)
        for valor, (_, largura) in zip(valores, colunas):
            ctk.CTkLabel(linha, text=valor, width=largura, anchor="w", text_color=cor,
                         font=tema.fonte(14, negrito=negrito)).pack(side="left")
