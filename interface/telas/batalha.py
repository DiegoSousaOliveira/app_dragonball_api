"""Tela Batalha: escolher dois lutadores e assistir a luta animada. O resultado vai para o placar da turma."""

import random

import customtkinter as ctk

from core import api, batalha, turma
from interface import tarefas, tema
from interface.componentes import BarraDeVida, CartaoPersonagem
from interface.telas import Tela, cabecalho

PAUSA_ENTRE_RODADAS = 900        # milissegundos
METRICAS = {"Total KI": "maxKi", "Base KI": "ki"}


class ArenaBatalha(ctk.CTkFrame):
    """Dois cards frente a frente, barras de vida, narracao e os botoes. Uma rodada a cada 0,9 s
    com after() (time.sleep travaria a janela inteira)."""

    def __init__(self, mestre, personagem_a, personagem_b, fotos, fotos_transformacao, metrica, ao_terminar):
        super().__init__(mestre, fg_color="transparent")
        self.luta = batalha.iniciar_luta(personagem_a, personagem_b, metrica)
        self.ao_terminar = ao_terminar
        self.agendado = None
        self.barras, self.cartoes, self.botoes_transformar = {}, {}, {}
        self.fotos_transformacao = {"a": fotos_transformacao[0], "b": fotos_transformacao[1]}
        self.criar_lado("a", personagem_a, fotos[0], coluna=0)
        self.criar_centro()
        self.criar_lado("b", personagem_b, fotos[1], coluna=2)
        self.grid_columnconfigure(1, weight=1)

    def criar_lado(self, lado, personagem, foto, coluna):
        coluna_frame = ctk.CTkFrame(self, fg_color="transparent")
        coluna_frame.grid(row=0, column=coluna, padx=16, sticky="n")
        self.cartoes[lado] = CartaoPersonagem(coluna_frame, personagem, foto, largura=210, altura_foto=210)
        self.cartoes[lado].pack()
        self.barras[lado] = BarraDeVida(coluna_frame, largura=210)
        self.barras[lado].pack(pady=(10, 0))
        if batalha.pode_transformar(self.luta[lado]):
            botao = tema.botao(coluna_frame, "Transformar! ⚡", lambda: self.transformar(lado))
            botao.pack(pady=(10, 0))
            self.botoes_transformar[lado] = botao

    def criar_centro(self):
        centro = ctk.CTkFrame(self, fg_color="transparent")
        centro.grid(row=0, column=1, sticky="n")
        ctk.CTkLabel(centro, text="VS", font=tema.fonte(36, negrito=True), text_color=tema.DESTAQUE).pack()
        self.narracao = ctk.CTkTextbox(centro, width=300, height=380, wrap="word", font=tema.fonte(13),
                                       fg_color=tema.CARD)
        self.narracao.pack(pady=10)
        self.botao_lutar = tema.botao(centro, "Lutar! 👊", self.lutar, largura=200)
        self.botao_lutar.pack()

    def escrever(self, frase):
        self.narracao.insert("end", frase + "\n\n")
        self.narracao.see("end")

    def lutar(self):
        self.botao_lutar.configure(state="disabled")
        self.proxima_rodada()

    def proxima_rodada(self):
        if batalha.luta_acabou(self.luta):
            self.terminar()
            return
        self.escrever(batalha.jogar_rodada(self.luta))
        self.barras["a"].atualizar(self.luta["a"]["hp"])
        self.barras["b"].atualizar(self.luta["b"]["hp"])
        self.agendado = self.after(PAUSA_ENTRE_RODADAS, self.proxima_rodada)

    def transformar(self, lado):
        lutador = self.luta[lado]
        if not batalha.pode_transformar(lutador):
            return
        transformacao = batalha.transformar(lutador)
        if self.fotos_transformacao[lado] is not None:
            self.cartoes[lado].trocar_foto(self.fotos_transformacao[lado])
        self.cartoes[lado].nome.configure(text=transformacao["name"])
        self.botoes_transformar[lado].configure(state="disabled")
        self.escrever(f"⚡ {lutador['nome']} se transformou em {transformacao['name']}! "
                      f"Força x{batalha.BONUS_TRANSFORMACAO} por {batalha.RODADAS_TRANSFORMADO} rodadas!")

    def terminar(self):
        self.agendado = None
        resultado = batalha.resultado(self.luta)
        self.escrever(f"🏆 {resultado['vencedor']} venceu em {resultado['rodadas']} rodadas!")
        for botao in self.botoes_transformar.values():
            botao.configure(state="disabled")
        self.ao_terminar(resultado)

    def destroy(self):
        """Cancela a rodada agendada antes de sumir (senao: erro 'invalid command name')."""
        if self.agendado is not None:
            self.after_cancel(self.agendado)
            self.agendado = None
        super().destroy()


class TelaBatalha(Tela):
    def __init__(self, app):
        super().__init__(app)
        cabecalho(self, "Batalha", "Escolha dois lutadores (ou 🎲 para sortear). O vencedor entra no Hall da "
                                  "Fama do telão.")
        self.nomes = sorted(p["name"] for p in app.personagens)
        self.criar_escolha()
        self.mensagem = ctk.CTkLabel(self, text="", font=tema.fonte(14, negrito=True))
        self.mensagem.pack(pady=(0, 6))
        self.palco = ctk.CTkFrame(self, fg_color="transparent")
        self.palco.pack(fill="both", expand=True, padx=12)
        self.arena = None
        self.ultima_luta = None
        tema.texto_secundario(self.palco, "⚔  Escolha os lutadores e clique em Preparar luta.", 16).pack(pady=80)

    def criar_escolha(self):
        barra = ctk.CTkFrame(self, fg_color=tema.CARD, corner_radius=10)
        barra.pack(fill="x", padx=24, pady=(4, 10))
        miolo = ctk.CTkFrame(barra, fg_color="transparent")
        miolo.pack(padx=14, pady=10)
        self.lutador_a = self.escolha(miolo, "Goku")
        ctk.CTkLabel(miolo, text="VS", font=tema.fonte(18, negrito=True), text_color=tema.DESTAQUE).pack(
            side="left", padx=10)
        self.lutador_b = self.escolha(miolo, "Freezer")
        self.metrica = ctk.CTkSegmentedButton(miolo, values=list(METRICAS), font=tema.fonte(13, negrito=True),
                                              selected_color=tema.DESTAQUE, selected_hover_color=tema.DESTAQUE_ESCURO,
                                              text_color=tema.TEXTO)
        self.metrica.set("Total KI")
        self.metrica.pack(side="left", padx=(20, 12))
        self.botao_preparar = tema.botao(miolo, "Preparar luta", self.preparar, largura=150)
        self.botao_preparar.pack(side="left")

    def escolha(self, mestre, inicial):
        caixa = ctk.CTkComboBox(mestre, values=self.nomes, width=200, height=34, font=tema.fonte(14))
        caixa.set(inicial)
        caixa.pack(side="left")
        tema.botao_secundario(mestre, "🎲", lambda: caixa.set(random.choice(self.nomes)), largura=36,
                              altura=34).pack(side="left", padx=(4, 0))
        return caixa

    def achar(self, texto):
        """Busca tolerante: 'goku', 'GOKU' e 'gokuu' acham o Goku."""
        achados = api.buscar_personagem(texto, self.app.personagens)
        if achados:
            return achados[0]
        return api.sugerir_personagem(texto, self.app.personagens)

    def preparar(self, revanche=False):
        if revanche and self.ultima_luta:
            personagem_a, personagem_b, metrica = self.ultima_luta
        else:
            personagem_a, personagem_b = self.achar(self.lutador_a.get()), self.achar(self.lutador_b.get())
            metrica = METRICAS[self.metrica.get()]
            for caixa, achado in ((self.lutador_a, personagem_a), (self.lutador_b, personagem_b)):
                if achado is None:
                    self.avisar(f'Não encontrei "{caixa.get()}".', tema.PERIGO)
                    return
                caixa.set(achado["name"])
        self.botao_preparar.configure(state="disabled")
        self.avisar("Preparando a arena (detalhes e fotos)...", tema.TEXTO_SECUNDARIO)
        tarefas.em_segundo_plano(self, lambda: self.carregar(personagem_a, personagem_b),
                                 lambda dados: self.montar_arena(dados, metrica),
                                 lambda erro: self.falhou(erro))

    def carregar(self, personagem_a, personagem_b):
        """Em segundo plano: detalhes (para as transformacoes) e as 4 fotos."""
        detalhes = [api.detalhar_personagem(personagem_a["id"]), api.detalhar_personagem(personagem_b["id"])]
        fotos = [tarefas.baixar_foto(d["image"]) for d in detalhes]
        transformacoes = [d["transformations"][-1]["image"] if d.get("transformations") else None
                          for d in detalhes]
        fotos_transformacao = [tarefas.baixar_foto(url) if url else None for url in transformacoes]
        return detalhes, fotos, fotos_transformacao

    def falhou(self, erro):
        self.botao_preparar.configure(state="normal")
        self.avisar(f"Não consegui preparar a luta: {erro}", tema.PERIGO)

    def montar_arena(self, dados, metrica):
        detalhes, fotos, fotos_transformacao = dados
        self.ultima_luta = (detalhes[0], detalhes[1], metrica)
        self.botao_preparar.configure(state="normal")
        for filho in self.palco.winfo_children():
            filho.destroy()
        self.arena = ArenaBatalha(self.palco, detalhes[0], detalhes[1], fotos, fotos_transformacao, metrica,
                                  self.luta_terminou)
        self.arena.pack(fill="both", expand=True)
        self.avisar("Tudo pronto! Clique em Lutar! (e use o Transformar na hora certa)", tema.DESTAQUE)

    def luta_terminou(self, resultado):
        metrica = self.ultima_luta[2]
        self.mostrar_botoes_finais()
        if not api.conectado_ao_servidor():
            self.avisar(f"🏆 {resultado['vencedor']} venceu! (sem servidor: não vai para o placar da turma)",
                        tema.DESTAQUE)
            return
        tarefas.em_segundo_plano(self, lambda: turma.enviar_batalha(resultado, metrica),
                                 lambda r: self.avisar(f"🏆 {resultado['vencedor']} venceu! Resultado enviado "
                                                       "para o placar da turma.", tema.SUCESSO),
                                 lambda erro: self.avisar(f"🏆 {resultado['vencedor']} venceu! (não consegui "
                                                          f"enviar ao servidor: {erro})", tema.PERIGO))

    def mostrar_botoes_finais(self):
        linha = ctk.CTkFrame(self.arena, fg_color="transparent")
        linha.grid(row=1, column=1, pady=6)
        tema.botao(linha, "Revanche 🔁", lambda: self.preparar(revanche=True), largura=140).pack(side="left", padx=4)

    def avisar(self, texto, cor):
        self.mensagem.configure(text=texto, text_color=cor)
