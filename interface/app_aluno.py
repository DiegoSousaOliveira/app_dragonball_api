"""Janela principal do aluno: menu lateral + uma tela de cada vez."""

import customtkinter as ctk

from core import api, turma
from interface import janelas, tarefas, tema
from interface.telas.batalha import TelaBatalha
from interface.telas.chat import TelaChat
from interface.telas.conexao import TelaConexao
from interface.telas.desafios import JanelaDesafioRecebido
from interface.telas.duelo import TelaDueloBatalha, TelaDueloQuiz
from interface.telas.esferas import TelaEsferas
from interface.telas.personagens import TelaPersonagens
from interface.telas.planetas import TelaPlanetas
from interface.telas.quiz import TelaQuiz
from interface.telas.ranking import TelaRanking
from interface.telas.rede import TelaRede
from interface.telas.turma import TelaTurma

MENU = [
    ("personagens", "🔎   Personagens", TelaPersonagens),
    ("batalha", "⚔   Batalha", TelaBatalha),
    ("planetas", "🪐   Planetas", TelaPlanetas),
    ("ranking", "🏆   Ranking", TelaRanking),
    ("quiz", "❓   Quem é?", TelaQuiz),
    ("turma", "👥   Turma e duelos", TelaTurma),
    ("chat", "💬   Chat", TelaChat),
    ("esferas", "🐉   Esferas", TelaEsferas),
    ("rede", "📡   Rede", TelaRede),
]


class AppAluno(ctk.CTk):
    def __init__(self):
        ctk.set_appearance_mode("dark")
        super().__init__()
        self.title("Dragon Ball Dex")
        janelas.colocar_icone(self)
        self.configure(fg_color=tema.FUNDO)
        janelas.abrir_janela_principal(self, 1240, 780)
        self.minsize(820, 540)
        self.nome_do_aluno = ""
        self.personagens = []            # carregados uma vez, ao conectar
        self.planetas = []
        self.telas = {}
        self.tela_atual = None
        self.estado_sala = None          # o que o servidor disse da sala na ultima pergunta
        self.desafio_enviado = None      # id do desafio que estou esperando responderem
        self.desafios_vistos = set()
        self.duelo_atual = None
        self.chat_lido = None            # ultima mensagem do chat que o aluno ja viu (None = acabou de entrar)
        self._geracao = 0                # muda a cada conexao: ciclos antigos de pergunta param sozinhos
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self.criar_menu_lateral()
        self.area = ctk.CTkFrame(self, fg_color="transparent", corner_radius=0)
        self.area.grid(row=0, column=1, sticky="nsew")
        self.aviso = ctk.CTkLabel(self, text="", height=30, corner_radius=8, font=tema.fonte(13, negrito=True))
        self.mostrar_conexao()
        self.after(1000, self.conferir_avisos)

    # ---------------- menu lateral ----------------

    def criar_menu_lateral(self):
        lateral = ctk.CTkFrame(self, width=200, corner_radius=0, fg_color=tema.LATERAL)
        lateral.grid(row=0, column=0, sticky="ns")
        lateral.grid_propagate(False)
        lateral.pack_propagate(False)
        ctk.CTkLabel(lateral, text="🐉 DRAGON BALL", font=tema.fonte(20, negrito=True),
                     text_color=tema.DESTAQUE).pack(pady=(26, 0))
        ctk.CTkLabel(lateral, text="D  E  X", font=tema.fonte(15, negrito=True),
                     text_color=tema.TEXTO_SECUNDARIO).pack(pady=(0, 24))
        self.botoes = {}
        for chave, texto, _ in MENU:
            botao = ctk.CTkButton(lateral, text=texto, anchor="w", height=42, corner_radius=8,
                                  fg_color="transparent", hover_color=tema.CARD, text_color=tema.TEXTO,
                                  text_color_disabled="#5C5F66", font=tema.fonte(15, negrito=True),
                                  command=lambda c=chave: self.mostrar(c))
            botao.pack(fill="x", padx=12, pady=2)
            self.botoes[chave] = botao
        rodape = ctk.CTkFrame(lateral, fg_color="transparent")
        rodape.pack(side="bottom", fill="x", padx=14, pady=16)
        self.rotulo_aluno = ctk.CTkLabel(rodape, text="", font=tema.fonte(14, negrito=True), anchor="w")
        self.rotulo_aluno.pack(fill="x")
        self.rotulo_conexao = ctk.CTkLabel(rodape, text="● desconectado", anchor="w", justify="left",
                                           font=tema.fonte(12), text_color=tema.TEXTO_SECUNDARIO)
        self.rotulo_conexao.pack(fill="x", pady=(2, 8))
        tema.botao_secundario(rodape, "Trocar conexão", self.mostrar_conexao, largura=170).pack()

    def habilitar_menu(self, ligado):
        for botao in self.botoes.values():
            botao.configure(state="normal" if ligado else "disabled")

    def marcar_botao(self, chave):
        for c, botao in self.botoes.items():
            botao.configure(fg_color=tema.CARD if c == chave else "transparent",
                            text_color=tema.DESTAQUE if c == chave else tema.TEXTO)

    # ---------------- trocar de tela ----------------

    def _trocar_para(self, tela):
        if self.tela_atual is not None:
            self.tela_atual.visivel = False
            self.tela_atual.ao_esconder()
            self.tela_atual.pack_forget()
        self.tela_atual = tela
        tela.pack(fill="both", expand=True)
        tela.visivel = True
        tela.ao_mostrar()

    def mostrar(self, chave):
        if chave not in self.telas:
            classe = next(c for k, _, c in MENU if k == chave)
            self.telas[chave] = classe(self)
        self.marcar_botao(chave)
        self._trocar_para(self.telas[chave])

    def mostrar_conexao(self):
        self._geracao += 1                     # para a vigia da sala da conexao anterior
        self.estado_sala = None
        self.chat_lido = None
        self.atualizar_selo_do_chat(0)
        self.duelo_atual = None
        self.habilitar_menu(False)
        self.marcar_botao(None)
        for tela in self.telas.values():         # outra fonte de dados: as telas comecam do zero
            tela.destroy()
        self.telas = {}
        if self.tela_atual is not None and self.tela_atual.winfo_exists():
            self.tela_atual.destroy()
        self.tela_atual = None
        self._trocar_para(TelaConexao(self))

    def conectado(self, nome, endereco):
        """Chamado pela tela de conexao. endereco=None: internet direto."""
        self.nome_do_aluno = nome
        self.rotulo_aluno.configure(text=f"👤 {nome}")
        if endereco:
            self.rotulo_conexao.configure(text=f"● Servidor da sala\n{endereco}", text_color=tema.SUCESSO)
        else:
            self.rotulo_conexao.configure(text="● Internet direta\n(sem placar da turma)",
                                          text_color=tema.DESTAQUE)
        tarefas.esquecer_fotos()
        self.mostrar_aviso("Carregando os personagens...", tema.TEXTO_SECUNDARIO)

        def carregar():
            return api.listar_personagens(), api.listar_planetas()

        tarefas.em_segundo_plano(self, carregar, self._dados_prontos,
                                 lambda erro: self.mostrar_aviso(f"Não consegui carregar os dados: {erro}",
                                                                 tema.PERIGO))

    def _dados_prontos(self, dados):
        self.personagens, self.planetas = dados
        self.habilitar_menu(True)
        self.esconder_aviso()
        self.mostrar("personagens")
        if api.conectado_ao_servidor():
            self.vigiar_sala(self._geracao)

    # ---------------- a sala: desafios e duelos ----------------

    def vigiar_sala(self, geracao):
        """De 1,5 em 1,5 s pergunta ao servidor quem esta na sala, se chegou desafio, se comecou duelo."""
        if geracao != self._geracao or not api.conectado_ao_servidor():
            return
        tarefas.em_segundo_plano(self, turma.sala, lambda estado: self._sala_chegou(estado, geracao),
                                 lambda erro: self._sala_falhou(erro, geracao))

    def _sala_chegou(self, estado, geracao):
        if geracao != self._geracao:
            return
        self.estado_sala = estado
        for desafio in estado["recebidos"]:
            if desafio["id"] not in self.desafios_vistos and self.duelo_atual is None:
                self.desafios_vistos.add(desafio["id"])
                JanelaDesafioRecebido(self, desafio)
        partida = estado.get("partida")
        if partida and self.duelo_atual is None:
            self.abrir_duelo(partida)
        tela_turma = self.telas.get("turma")
        if tela_turma is not None and tela_turma.visivel:
            tela_turma.atualizar_sala(estado)
        chat = estado.get("chat")
        tela_chat = self.telas.get("chat")
        if chat and not (tela_chat is not None and tela_chat.visivel):
            if self.chat_lido is None:                  # acabou de entrar: o que ja estava la conta como lido
                self.chat_lido = chat["ultimo_id"]
            self.atualizar_selo_do_chat(chat["ultimo_id"] - self.chat_lido)
        self.after(1500, lambda: self.vigiar_sala(geracao))

    def _sala_falhou(self, erro, geracao):
        if geracao != self._geracao:
            return
        if "desconhecido" in str(erro).lower():         # o servidor foi reiniciado: entramos de novo
            tarefas.em_segundo_plano(self, lambda: turma.entrar(self.nome_do_aluno))
        self.after(3000, lambda: self.vigiar_sala(geracao))

    def atualizar_selo_do_chat(self, nao_lidas):
        """'💬 Chat (3)' no menu quando chegam mensagens novas."""
        botao = self.botoes.get("chat")
        if botao is not None:
            botao.configure(text=f"💬   Chat ({nao_lidas})" if nao_lidas > 0 else "💬   Chat")

    def abrir_duelo(self, partida):
        for janela in self.winfo_children():           # fecha avisos de desafio que estavam abertos
            if isinstance(janela, ctk.CTkToplevel) and "desafi" in janela.title().lower():
                janela.destroy()
        self.desafio_enviado = None
        classe = TelaDueloBatalha if partida["tipo"] == "batalha" else TelaDueloQuiz
        self.duelo_atual = classe(self, partida["id"])
        self.habilitar_menu(False)
        self.marcar_botao(None)
        self.mostrar_aviso("Duelo em andamento: o menu volta quando ele acabar.", tema.DESTAQUE, segundos=4)
        self._trocar_para(self.duelo_atual)

    def fim_do_duelo(self):
        duelo = self.duelo_atual
        self.duelo_atual = None
        self.habilitar_menu(True)
        self.mostrar("turma")
        if duelo is not None:
            duelo.destroy()

    # ---------------- avisos ----------------

    def mostrar_aviso(self, texto, cor=tema.DESTAQUE, segundos=0):
        self.aviso.configure(text=f"  {texto}  ", fg_color=tema.CARD, text_color=cor)
        self.aviso.place(relx=0.6, rely=0.97, anchor="s")
        self.aviso.lift()
        if segundos:
            self.after(segundos * 1000, self.esconder_aviso)

    def esconder_aviso(self):
        self.aviso.place_forget()

    def conferir_avisos(self):
        """De tempos em tempos: o core avisou que estamos sem conexao?"""
        for texto in api.pegar_avisos():
            self.mostrar_aviso(texto, tema.PERIGO, segundos=5)
            if self.nome_do_aluno:
                self.rotulo_conexao.configure(text="● Sem conexão\n(usando dados salvos)", text_color=tema.PERIGO)
        self.after(1000, self.conferir_avisos)
