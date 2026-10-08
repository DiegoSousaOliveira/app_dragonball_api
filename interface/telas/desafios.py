"""Janelinhas de desafio: desafiar um colega e responder a um desafio recebido."""

import random

import customtkinter as ctk

from core import api, turma
from interface import janelas, tarefas, tema

METRICAS = {"Total KI": "maxKi", "Base KI": "ki"}
NOME_DA_METRICA = {"maxKi": "Total KI", "ki": "Base KI"}


def escolha_de_lutador(mestre, app, inicial=None):
    """Caixa com os nomes + botao 🎲. Devolve a caixa (ComboBox)."""
    nomes = sorted(p["name"] for p in app.personagens)
    linha = ctk.CTkFrame(mestre, fg_color="transparent")
    linha.pack(pady=(4, 10))
    caixa = ctk.CTkComboBox(linha, values=nomes, width=230, height=34, font=tema.fonte(14))
    caixa.set(inicial or random.choice(nomes))
    caixa.pack(side="left")
    tema.botao_secundario(linha, "🎲", lambda: caixa.set(random.choice(nomes)), largura=36, altura=34).pack(
        side="left", padx=(4, 0))
    return caixa


def personagem_escolhido(app, caixa):
    achados = api.buscar_personagem(caixa.get(), app.personagens)
    return achados[0] if achados else api.sugerir_personagem(caixa.get(), app.personagens)


class JanelaDesafiar:
    """Escolher o lutador (ou as rodadas do quiz), mandar o desafio e esperar a resposta."""

    def __init__(self, app, adversario, tipo):
        self.app = app
        self.adversario = adversario
        self.tipo = tipo
        self.id_desafio = None
        self.janela = janelas.criar_janela(app, f"Desafiar {adversario['nome']}", 440, 330)
        self.janela.transient(app)
        self.miolo = ctk.CTkFrame(self.janela, fg_color="transparent")
        self.miolo.pack(fill="both", expand=True, padx=24, pady=20)
        icone = "⚔" if tipo == "batalha" else "❓"
        texto = "BATALHA" if tipo == "batalha" else "QUIZ"
        tema.titulo(self.miolo, f"{icone} Desafiar {adversario['nome']}", 20).pack()
        tema.texto_secundario(self.miolo, f"Duelo de {texto}: quem ganhar leva 3 pontos no placar da turma.",
                              wraplength=380).pack(pady=(2, 12))
        if tipo == "batalha":
            tema.texto_secundario(self.miolo, "Seu lutador:", 14).pack()
            self.lutador = escolha_de_lutador(self.miolo, app)
            self.metrica = ctk.CTkSegmentedButton(self.miolo, values=list(METRICAS), selected_color=tema.DESTAQUE,
                                                  selected_hover_color=tema.DESTAQUE_ESCURO)
            self.metrica.set("Total KI")
            self.metrica.pack()
        else:
            tema.texto_secundario(self.miolo, "Quantas rodadas:", 14).pack()
            self.rodadas = ctk.CTkSegmentedButton(self.miolo, values=["3", "5", "10"], selected_color=tema.DESTAQUE,
                                                  selected_hover_color=tema.DESTAQUE_ESCURO)
            self.rodadas.set("5")
            self.rodadas.pack(pady=(4, 10))
        self.mensagem = ctk.CTkLabel(self.miolo, text="", wraplength=380, font=tema.fonte(13, negrito=True))
        self.mensagem.pack(pady=8)
        self.botao = tema.botao(self.miolo, "Enviar desafio", self.enviar, largura=220)
        self.botao.pack()

    def enviar(self):
        if self.tipo == "batalha":
            personagem = personagem_escolhido(self.app, self.lutador)
            if personagem is None:
                self.mensagem.configure(text=f'Não encontrei "{self.lutador.get()}".', text_color=tema.PERIGO)
                return
            opcoes = {"personagem": personagem["id"], "metrica": METRICAS[self.metrica.get()]}
        else:
            opcoes = {"rodadas": int(self.rodadas.get())}
        self.botao.configure(state="disabled")
        tarefas.em_segundo_plano(self.janela, lambda: turma.desafiar(self.adversario["id"], self.tipo, **opcoes),
                                 self.enviado, self.falhou)

    def falhou(self, erro):
        self.botao.configure(state="normal")
        self.mensagem.configure(text=str(erro), text_color=tema.PERIGO)

    def enviado(self, desafio):
        self.id_desafio = desafio["id"]
        self.app.desafio_enviado = desafio["id"]
        self.botao.configure(text="Cancelar desafio", state="normal", command=self.cancelar,
                             fg_color=tema.CARD, hover_color="#4A4E54", text_color=tema.TEXTO)
        self.acompanhar()

    def acompanhar(self):
        """Olha o que o app recebeu da sala (ele pergunta ao servidor a cada 1,5 s)."""
        if not self.janela.winfo_exists():
            return
        enviado = (self.app.estado_sala or {}).get("enviado")
        if enviado and enviado["id"] == self.id_desafio:
            estado = enviado["estado"]
            if estado == "pendente":
                self.mensagem.configure(text=f"⏳ Esperando {self.adversario['nome']} responder... "
                                             f"({enviado['expira_em']} s)", text_color=tema.TEXTO_SECUNDARIO)
            elif estado == "aceito":
                self.mensagem.configure(text="✔ Aceito! Abrindo o duelo...", text_color=tema.SUCESSO)
                self.janela.after(800, self.fechar)
                return
            else:
                motivos = {"recusado": f"{self.adversario['nome']} recusou o desafio.",
                           "expirado": f"{self.adversario['nome']} não respondeu a tempo.",
                           "cancelado": "Desafio cancelado."}
                self.mensagem.configure(text=motivos.get(estado, estado), text_color=tema.PERIGO)
                self.botao.configure(text="Fechar", command=self.fechar)
                self.app.desafio_enviado = None
                return
        self.janela.after(500, self.acompanhar)

    def cancelar(self):
        if self.id_desafio:
            tarefas.em_segundo_plano(self.app, lambda: turma.cancelar(self.id_desafio))
        self.fechar()

    def fechar(self):
        self.app.desafio_enviado = None
        if self.janela.winfo_exists():
            self.janela.destroy()


class JanelaDesafioRecebido:
    """Alguem desafiou este aluno: escolher o lutador e aceitar (ou recusar)."""

    def __init__(self, app, desafio):
        self.app = app
        self.desafio = desafio
        self.restante = desafio["expira_em"]
        self.janela = janelas.criar_janela(app, "Você foi desafiado!", 460, 330)
        self.janela.bell()
        miolo = ctk.CTkFrame(self.janela, fg_color="transparent")
        miolo.pack(fill="both", expand=True, padx=24, pady=20)
        de = desafio["de"]["nome"]
        if desafio["tipo"] == "batalha":
            opcoes = desafio["opcoes"]
            tema.titulo(miolo, f"⚔ {de} te desafiou!", 21).pack()
            tema.texto_secundario(miolo, f"Batalha: {de} vai lutar com {opcoes['personagem']['name']} "
                                         f"({NOME_DA_METRICA[opcoes['metrica']]}). Escolha o seu lutador:",
                                  14, wraplength=400).pack(pady=(4, 6))
            self.lutador = escolha_de_lutador(miolo, app)
        else:
            tema.titulo(miolo, f"❓ {de} te desafiou!", 21).pack()
            tema.texto_secundario(miolo, f"Quiz de {desafio['opcoes']['rodadas']} rodadas: as mesmas perguntas "
                                         "para os dois. Ganha quem fizer mais pontos!", 14,
                                  wraplength=400).pack(pady=(4, 14))
            self.lutador = None
        self.mensagem = ctk.CTkLabel(miolo, text="", font=tema.fonte(13, negrito=True), wraplength=400)
        self.mensagem.pack(pady=6)
        linha = ctk.CTkFrame(miolo, fg_color="transparent")
        linha.pack()
        self.botao_aceitar = tema.botao(linha, "Aceitar ✔", self.aceitar, largura=150)
        self.botao_aceitar.pack(side="left", padx=6)
        tema.botao_secundario(linha, "Recusar", self.recusar, largura=150).pack(side="left", padx=6)
        self.contar()

    def contar(self):
        if not self.janela.winfo_exists():
            return
        recebidos = [d["id"] for d in (self.app.estado_sala or {}).get("recebidos", [])]
        if self.desafio["id"] not in recebidos and self.restante < self.desafio["expira_em"] - 2:
            self.janela.destroy()                     # cancelado, expirado ou ja respondido
            return
        self.restante = max(0, self.restante - 1)
        self.mensagem.configure(text=f"Responda em {self.restante} s", text_color=tema.TEXTO_SECUNDARIO)
        self.janela.after(1000, self.contar)

    def aceitar(self):
        opcoes = {}
        if self.lutador is not None:
            personagem = personagem_escolhido(self.app, self.lutador)
            if personagem is None:
                self.mensagem.configure(text=f'Não encontrei "{self.lutador.get()}".', text_color=tema.PERIGO)
                return
            opcoes["personagem"] = personagem["id"]
        self.botao_aceitar.configure(state="disabled", text="Aceitando...")
        tarefas.em_segundo_plano(self.janela, lambda: turma.responder(self.desafio["id"], True, **opcoes),
                                 lambda r: self.janela.destroy(), self.falhou)

    def falhou(self, erro):
        self.botao_aceitar.configure(state="normal", text="Aceitar ✔")
        self.mensagem.configure(text=str(erro), text_color=tema.PERIGO)

    def recusar(self):
        tarefas.em_segundo_plano(self.app, lambda: turma.responder(self.desafio["id"], False))
        self.janela.destroy()
