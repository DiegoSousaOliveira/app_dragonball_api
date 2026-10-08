"""Tela "Quem é?": imagem pixelada que fica mais nitida a cada erro. Pontos vao para o placar da turma."""

import customtkinter as ctk

from core import api, imagens, quiz, turma
from interface import tarefas, tema
from interface.telas import Tela, cabecalho

LARGURA_FOTO = 300
ALTURA_FOTO = 360


class PartidaQuiz(ctk.CTkFrame):
    """O jogo inteiro. Guarda o estado: rodada atual, pontos, erros e se usou dica."""

    def __init__(self, mestre, rodadas, fotos, ao_terminar, ao_progresso=None):
        """ao_progresso(rodadas_concluidas, pontos) e chamado ao fim de cada rodada (usado no duelo)."""
        super().__init__(mestre, fg_color="transparent")
        self.rodadas = rodadas
        self.fotos = fotos
        self.ao_terminar = ao_terminar
        self.ao_progresso = ao_progresso
        self.numero = 0
        self.pontos = 0
        self.criar_tela()
        self.comecar_rodada()

    def criar_tela(self):
        self.placar = ctk.CTkLabel(self, text="", font=tema.fonte(15, negrito=True), text_color=tema.DESTAQUE)
        self.placar.pack(pady=(0, 6))
        self.foto = ctk.CTkLabel(self, text="")
        self.foto.pack()
        self.dica = ctk.CTkLabel(self, text="", text_color=tema.TEXTO_SECUNDARIO)
        self.dica.pack()
        self.mensagem = ctk.CTkLabel(self, text="", font=tema.fonte(16, negrito=True))
        self.mensagem.pack(pady=(0, 6))
        grade = ctk.CTkFrame(self, fg_color="transparent")
        grade.pack()
        self.botoes_opcao = []
        for indice in range(quiz.OPCOES_POR_RODADA):
            botao = tema.botao(grade, "", lambda i=indice: self.responder(i), largura=250)
            botao.grid(row=indice // 2, column=indice % 2, padx=6, pady=4)
            self.botoes_opcao.append(botao)
        rodape = ctk.CTkFrame(self, fg_color="transparent")
        rodape.pack(pady=10)
        self.botao_dica = tema.botao_secundario(rodape, "💡 Dica (-1 ponto)", self.dar_dica, largura=180)
        self.botao_dica.pack(side="left", padx=6)
        self.botao_proxima = tema.botao(rodape, "Próxima ▶", self.proxima_rodada, largura=180)
        self.botao_proxima.pack(side="left", padx=6)

    def comecar_rodada(self):
        rodada = self.rodadas[self.numero]
        self.erros = 0
        self.usou_dica = False
        self.rodada_acabou = False
        foto = self.fotos[self.numero]
        if foto is None:
            self.foto_base = imagens.imagem_lisa(LARGURA_FOTO, ALTURA_FOTO, tema.SEM_FOTO)
        else:
            self.foto_base = imagens.foto_de_card(foto, LARGURA_FOTO, ALTURA_FOTO)
        for indice, botao in enumerate(self.botoes_opcao):
            botao.configure(text=rodada["opcoes"][indice]["name"], state="normal", fg_color=tema.DESTAQUE)
        self.dica.configure(text="")
        self.mensagem.configure(text="Quem é esse personagem?", text_color=tema.TEXTO)
        self.botao_dica.configure(state="normal")
        self.botao_proxima.configure(state="disabled", text="Próxima ▶")
        self.mostrar_foto()
        self.atualizar_placar()

    def mostrar_foto(self):
        nivel = None if self.rodada_acabou else quiz.nivel_de_pixel(self.erros)
        pronta = self.foto_base if nivel is None else imagens.pixelar(self.foto_base, nivel)
        self.imagem = ctk.CTkImage(light_image=pronta, dark_image=pronta, size=(LARGURA_FOTO, ALTURA_FOTO))
        self.foto.configure(image=self.imagem)

    def responder(self, indice):
        rodada = self.rodadas[self.numero]
        escolhido = rodada["opcoes"][indice]
        botao = self.botoes_opcao[indice]
        if escolhido["id"] == rodada["resposta"]["id"]:
            ganhou = quiz.premio(self.erros, self.usou_dica)
            self.pontos += ganhou
            botao.configure(fg_color=tema.SUCESSO)
            self.mensagem.configure(text=f"Acertou! É {escolhido['name']}. +{ganhou} ponto(s)",
                                    text_color=tema.SUCESSO)
            self.terminar_rodada()
        else:
            self.erros += 1
            botao.configure(state="disabled", fg_color=tema.PERIGO)
            self.mensagem.configure(text="Errou! A imagem ficou mais nítida...", text_color=tema.PERIGO)
            self.mostrar_foto()
        self.atualizar_placar()

    def dar_dica(self):
        resposta = self.rodadas[self.numero]["resposta"]
        self.usou_dica = True
        self.dica.configure(text=f"💡 Raça: {resposta['race']}  ·  Afiliação: {resposta['affiliation']}")
        self.botao_dica.configure(state="disabled")
        self.atualizar_placar()

    def terminar_rodada(self):
        self.rodada_acabou = True
        for botao in self.botoes_opcao:
            botao.configure(state="disabled")
        self.botao_dica.configure(state="disabled")
        self.mostrar_foto()
        if self.ao_progresso:
            self.ao_progresso(self.numero + 1, self.pontos)
        ultima = self.numero == len(self.rodadas) - 1
        self.botao_proxima.configure(state="normal", text="Ver resultado 🏁" if ultima else "Próxima ▶")

    def proxima_rodada(self):
        self.numero += 1
        if self.numero < len(self.rodadas):
            self.comecar_rodada()
        else:
            maximo = len(self.rodadas) * quiz.PREMIO_INICIAL
            self.mensagem.configure(text=f"Fim de jogo! {self.pontos} de {maximo} pontos.", text_color=tema.DESTAQUE)
            self.botao_proxima.configure(state="disabled")
            self.ao_terminar(self.pontos)

    def atualizar_placar(self):
        vale = 0 if self.rodada_acabou else quiz.premio(self.erros, self.usou_dica)
        self.placar.configure(text=f"Rodada {self.numero + 1} de {len(self.rodadas)}   ·   Pontos: {self.pontos}"
                                   f"   ·   Esta rodada vale: {vale}")


class TelaQuiz(Tela):
    def __init__(self, app):
        super().__init__(app)
        cabecalho(self, "Quem é esse personagem?",
                  "A imagem começa quadriculada. Acertar de primeira vale 4; cada erro ou dica tira 1 ponto.")
        barra = ctk.CTkFrame(self, fg_color="transparent")
        barra.pack(pady=(4, 8))
        tema.texto_secundario(barra, "Rodadas:", 14).pack(side="left", padx=(0, 8))
        self.quantas = ctk.CTkSegmentedButton(barra, values=["3", "5", "10"], font=tema.fonte(14, negrito=True),
                                              selected_color=tema.DESTAQUE, selected_hover_color=tema.DESTAQUE_ESCURO)
        self.quantas.set("5")
        self.quantas.pack(side="left")
        self.botao_comecar = tema.botao(barra, "Começar ▶", self.comecar, largura=150)
        self.botao_comecar.pack(side="left", padx=12)
        self.mensagem = ctk.CTkLabel(self, text="", font=tema.fonte(14, negrito=True))
        self.mensagem.pack()
        self.palco = ctk.CTkFrame(self, fg_color="transparent")
        self.palco.pack(fill="both", expand=True)

    def comecar(self):
        quantas = int(self.quantas.get())
        rodadas = quiz.montar_rodadas(self.app.personagens, quantas)
        self.botao_comecar.configure(state="disabled")
        self.mensagem.configure(text="Preparando as imagens...", text_color=tema.TEXTO_SECUNDARIO)
        tarefas.em_segundo_plano(self, lambda: [tarefas.baixar_foto(r["resposta"]["image"]) for r in rodadas],
                                 lambda fotos: self.jogar(rodadas, fotos),
                                 lambda erro: self.mensagem.configure(text=f"Erro: {erro}", text_color=tema.PERIGO))

    def jogar(self, rodadas, fotos):
        for filho in self.palco.winfo_children():
            filho.destroy()
        self.mensagem.configure(text="")
        self.botao_comecar.configure(state="normal", text="Recomeçar")
        PartidaQuiz(self.palco, rodadas, fotos, lambda pontos: self.terminou(pontos, len(rodadas))).pack()

    def terminou(self, pontos, quantas):
        if not api.conectado_ao_servidor():
            self.mensagem.configure(text=f"Você fez {pontos} pontos! (sem servidor: não vai para o placar da turma)",
                                    text_color=tema.DESTAQUE)
            return

        def mostrar(resposta):
            if resposta.get("recorde"):
                texto, cor = f"🏆 NOVO RECORDE DA TURMA com {quantas} rodadas: {pontos} pontos!", tema.SUCESSO
            else:
                texto, cor = f"Você fez {pontos} pontos! Enviado para o placar da turma.", tema.DESTAQUE
            self.mensagem.configure(text=texto, text_color=cor)

        tarefas.em_segundo_plano(self, lambda: turma.enviar_quiz(pontos, quantas), mostrar,
                                 lambda erro: self.mensagem.configure(text=f"Não consegui enviar: {erro}",
                                                                      text_color=tema.PERIGO))
