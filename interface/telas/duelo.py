"""
Telas de duelo entre alunos. Quem manda e o SERVIDOR:
  - batalha: o servidor joga as rodadas; o app pergunta o estado a cada 0,5 s e desenha;
  - quiz: os dois respondem as mesmas perguntas; o app manda o progresso e ve o do colega.
"""

from tkinter import messagebox

import customtkinter as ctk

from core import turma
from interface import tarefas, tema
from interface.componentes import BarraDeVida, CartaoPersonagem
from interface.telas import Tela, cabecalho
from interface.telas.quiz import PartidaQuiz

OUTRO = {"a": "b", "b": "a"}


class TelaDuelo(Tela):
    """O que as duas telas de duelo tem em comum: perguntar o estado e mostrar o resultado."""

    INTERVALO = 500                   # milissegundos entre as perguntas ao servidor

    def __init__(self, app, id_partida, titulo):
        super().__init__(app)
        self.id_partida = id_partida
        self.estado = None
        self.acabou = False
        self.falhas_seguidas = 0
        cabecalho(self, titulo)
        self.aviso = ctk.CTkLabel(self, text="Carregando o duelo...", font=tema.fonte(18, negrito=True),
                                  text_color=tema.DESTAQUE)
        self.aviso.pack(pady=(0, 6))
        self.palco = ctk.CTkFrame(self, fg_color="transparent")
        self.palco.pack(fill="both", expand=True, padx=12)
        self.rodape = ctk.CTkFrame(self, fg_color="transparent")
        self.rodape.pack(pady=(4, 12))
        self.botao_desistir = tema.botao_secundario(self.rodape, "🏳 Desistir", self.desistir, largura=140)
        self.botao_desistir.pack()
        self.perguntar()

    def perguntar(self):
        if self.acabou or not self.winfo_exists():
            return
        tarefas.em_segundo_plano(self, lambda: turma.partida(self.id_partida), self._chegou, self._falhou)

    def _chegou(self, estado):
        self.falhas_seguidas = 0
        primeira_vez = self.estado is None
        self.estado = estado
        self.eu = estado["seu_lado"]
        self.nome_eu = estado["jogadores"][self.eu]["nome"]
        self.nome_outro = estado["jogadores"][OUTRO[self.eu]]["nome"]
        if primeira_vez:
            self.montar(estado)
        self.atualizar(estado)
        if estado["fim"]:
            self.terminar(estado["fim"])
        else:
            self.after(self.INTERVALO, self.perguntar)

    def _falhou(self, erro):
        self.falhas_seguidas += 1
        self.aviso.configure(text=f"Conexão instável... ({erro})", text_color=tema.PERIGO)
        if self.falhas_seguidas > 40:              # ~30 s sem servidor: desistimos de esperar
            self.terminar(None)
            return
        self.after(800, self.perguntar)

    def terminar(self, fim):
        self.acabou = True
        self.botao_desistir.destroy()
        if fim is None:
            texto, cor = "O servidor parou de responder. O duelo foi interrompido.", tema.PERIGO
        else:
            ganhei = fim["vencedor"] == self.eu
            vencedor = self.nome_eu if ganhei else self.nome_outro
            motivo = {"desistencia": " (o outro desistiu)", "tempo": " (empate nos pontos: terminou mais rápido)"}
            if ganhei:
                texto, cor = f"🏆 VOCÊ VENCEU!{motivo.get(fim['motivo'], '')}  +3 pontos no placar", tema.SUCESSO
            else:
                texto, cor = f"{vencedor} venceu{motivo.get(fim['motivo'], '')}. Você ganhou 1 ponto por participar.", \
                             tema.PERIGO
        self.aviso.configure(text=texto, text_color=cor)
        tema.botao(self.rodape, "Voltar para a turma", self.app.fim_do_duelo, largura=220).pack()

    def desistir(self):
        if messagebox.askyesno("Desistir", "Desistir do duelo? O colega ganha a vitória.", parent=self):
            tarefas.em_segundo_plano(self, lambda: turma.desistir(self.id_partida))

    # as filhas preenchem estas duas
    def montar(self, estado):
        pass

    def atualizar(self, estado):
        pass


class TelaDueloBatalha(TelaDuelo):
    def __init__(self, app, id_partida):
        self.narrados = 0
        self.transformacoes_aplicadas = set()
        super().__init__(app, id_partida, "⚔ Duelo de batalha")

    def montar(self, estado):
        self.cartoes, self.barras = {}, {}
        arena = ctk.CTkFrame(self.palco, fg_color="transparent")
        arena.pack()
        self.criar_lado(arena, "a", estado, coluna=0)
        centro = ctk.CTkFrame(arena, fg_color="transparent")
        centro.grid(row=0, column=1, sticky="n", padx=10)
        ctk.CTkLabel(centro, text="VS", font=tema.fonte(36, negrito=True), text_color=tema.DESTAQUE).pack()
        self.narracao = ctk.CTkTextbox(centro, width=300, height=360, wrap="word", font=tema.fonte(13),
                                       fg_color=tema.CARD)
        self.narracao.pack(pady=8)
        self.criar_lado(arena, "b", estado, coluna=2)

    def criar_lado(self, arena, lado, estado, coluna):
        coluna_frame = ctk.CTkFrame(arena, fg_color="transparent")
        coluna_frame.grid(row=0, column=coluna, sticky="n", padx=12)
        jogador = estado["jogadores"][lado]["nome"] + ("  (você)" if lado == self.eu else "")
        ctk.CTkLabel(coluna_frame, text=jogador, font=tema.fonte(16, negrito=True),
                     text_color=tema.DESTAQUE if lado == self.eu else tema.TEXTO).pack(pady=(0, 4))
        personagem = estado["personagens"][lado]
        cartao = CartaoPersonagem(coluna_frame, personagem, None, largura=210, altura_foto=200)
        cartao.pack()
        # se a transformacao chegar antes da foto normal, a foto normal NAO pode cobrir a transformada
        tarefas.carregar_foto(cartao, personagem["image"],
                              lambda foto: lado not in self.transformacoes_aplicadas and cartao.trocar_foto(foto))
        self.cartoes[lado] = cartao
        self.barras[lado] = BarraDeVida(coluna_frame, largura=210)
        self.barras[lado].pack(pady=(8, 0))
        if lado == self.eu and estado["pode_transformar"][lado]:
            self.botao_transformar = tema.botao(coluna_frame, "Transformar! ⚡", self.transformar)
            self.botao_transformar.pack(pady=(8, 0))
        else:
            self.botao_transformar = getattr(self, "botao_transformar", None)

    def atualizar(self, estado):
        if not estado["fim"]:
            if estado["comeca_em"] > 0:
                self.aviso.configure(text=f"{self.nome_eu} x {self.nome_outro}: a luta começa em "
                                          f"{estado['comeca_em']:.0f}...", text_color=tema.DESTAQUE)
            else:
                self.aviso.configure(text=f"{self.nome_eu} x {self.nome_outro}: LUTEM!", text_color=tema.DESTAQUE)
        for frase in estado["narracao"][self.narrados:]:
            self.narracao.insert("end", frase + "\n\n")
            self.narracao.see("end")
        self.narrados = len(estado["narracao"])
        for lado in ("a", "b"):
            self.barras[lado].atualizar(estado["hp"][lado])
            transformacao = estado["transformado"][lado]
            if transformacao and lado not in self.transformacoes_aplicadas:
                self.transformacoes_aplicadas.add(lado)
                self.cartoes[lado].nome.configure(text=transformacao["name"])
                if transformacao.get("image"):
                    tarefas.carregar_foto(self.cartoes[lado], transformacao["image"],
                                          lambda foto, c=self.cartoes[lado]: foto and c.trocar_foto(foto))
        if self.botao_transformar is not None and (estado["fim"] or not estado["pode_transformar"][self.eu]):
            self.botao_transformar.configure(state="disabled")

    def transformar(self):
        self.botao_transformar.configure(state="disabled")
        tarefas.em_segundo_plano(self, lambda: turma.transformar(self.id_partida), None,
                                 lambda erro: self.aviso.configure(text=str(erro), text_color=tema.PERIGO))


class TelaDueloQuiz(TelaDuelo):
    INTERVALO = 900

    def __init__(self, app, id_partida):
        self.partida_quiz = None
        self.terminei = False
        super().__init__(app, id_partida, "❓ Duelo de quiz")

    def montar(self, estado):
        self.placar_outro = ctk.CTkLabel(self.palco, text="", font=tema.fonte(15, negrito=True))
        self.placar_outro.pack(pady=(0, 6))
        rodadas = []
        for rodada in estado["rodadas"]:
            resposta = next(o for o in rodada["opcoes"] if o["id"] == rodada["resposta"])
            rodadas.append({"resposta": resposta, "opcoes": rodada["opcoes"]})
        self.rodadas = rodadas
        self.aviso.configure(text="Preparando as imagens...", text_color=tema.TEXTO_SECUNDARIO)
        tarefas.em_segundo_plano(self, lambda: [tarefas.baixar_foto(r["resposta"]["image"]) for r in rodadas],
                                 self.fotos_prontas, lambda erro: self.fotos_prontas([None] * len(rodadas)))

    def fotos_prontas(self, fotos):
        self.fotos = fotos
        self.comecar_quando_der()

    def comecar_quando_der(self):
        if self.acabou or not self.winfo_exists():
            return
        if self.estado and self.estado["comeca_em"] > 0:
            self.aviso.configure(text=f"O quiz começa em {self.estado['comeca_em']:.0f}...", text_color=tema.DESTAQUE)
            self.after(300, self.comecar_quando_der)
            return
        self.aviso.configure(text=f"{self.nome_eu} x {self.nome_outro}: as MESMAS perguntas para os dois!",
                             text_color=tema.DESTAQUE)
        self.partida_quiz = PartidaQuiz(self.palco, self.rodadas, self.fotos, self.minha_ultima_rodada,
                                        self.meu_progresso)
        self.partida_quiz.pack()

    def meu_progresso(self, concluidas, pontos):
        tarefas.em_segundo_plano(self, lambda: turma.enviar_progresso(self.id_partida, concluidas, pontos))

    def minha_ultima_rodada(self, pontos):
        self.terminei = True
        quantas = len(self.rodadas)
        tarefas.em_segundo_plano(self, lambda: turma.enviar_progresso(self.id_partida, quantas, pontos, True))
        self.aviso.configure(text=f"Você terminou com {pontos} pontos! Esperando {self.nome_outro}...",
                             text_color=tema.TEXTO_SECUNDARIO)

    def atualizar(self, estado):
        outro = estado["progresso"][OUTRO[self.eu]]
        total = len(estado["rodadas"])
        if outro["terminou"]:
            texto = f"{self.nome_outro}: terminou com {outro['pontos']} pontos"
        else:
            texto = f"{self.nome_outro}: {outro['rodada']} de {total} rodadas · {outro['pontos']} pontos"
        self.placar_outro.configure(text=texto)

    def terminar(self, fim):
        if self.partida_quiz is not None:
            for botao in self.partida_quiz.botoes_opcao + [self.partida_quiz.botao_dica,
                                                           self.partida_quiz.botao_proxima]:
                botao.configure(state="disabled")
        super().terminar(fim)
