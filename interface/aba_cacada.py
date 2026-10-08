"""
Aba "🐉 Caçada" do painel do professor: os botoes da Caca as Esferas, a grade ao vivo (uma linha por aluno,
7 esferas que acendem), o podio, o feed de achados, as dicas extras e o resultado em CSV.
O botao "⛶ Telão" abre a mesma grade em tela cheia, com letras grandes para o projetor.
Os controles existem SO aqui (nao ha rota HTTP para iniciar/pausar/encerrar a cacada).
"""

import os
import time
import tkinter as tk
import webbrowser
from collections import deque
from tkinter import messagebox

import customtkinter as ctk

from core import esferas
from interface import tema
from interface.desenho_esfera import desenhar_esfera
from interface.efeito_dragao import AvisoNoTelao, EfeitoDragao, Som
from servidor import rotas_esferas

ATUALIZAR_A_CADA = 500             # milissegundos
TEMPOS = {"Sem limite": None, "10 min": 10, "15 min": 15, "20 min": 20, "30 min": 30, "45 min": 45}
ESTADOS = {"aguardando": ("Aguardando a largada", tema.TEXTO_SECUNDARIO), "ativa": ("● Caçada valendo!", tema.SUCESSO),
           "pausada": ("⏸ Pausada", tema.DESTAQUE), "encerrada": ("🏁 Encerrada", tema.PERIGO)}
MEDALHAS = ["🥇", "🥈", "🥉"]
OURO_ESCURO = "#3D3519"            # fundo da linha de quem ja juntou as 7


def relogio(segundos):
    if segundos is None:
        return "sem limite"
    return f"{segundos // 60:02d}:{segundos % 60:02d}"


class GradeDaCacada(tk.Canvas):
    """Uma linha por cacador: numero, nome, as 7 esferas (acesas/apagadas) e os pontos.
    A altura das linhas se ajusta para caber todo mundo, do jeito que a janela estiver."""

    def __init__(self, mestre, escala=1.0):
        super().__init__(mestre, bg=tema.FUNDO, highlightthickness=0)
        self.escala = escala
        self.cacadores = []
        self.recentes = {}          # (numero, esfera) -> horario em que acendeu (brilha por 2 s)
        self.bind("<Configure>", lambda evento: self.desenhar())

    def mostrar(self, cacadores, recentes):
        self.cacadores, self.recentes = cacadores, recentes
        self.desenhar()

    def desenhar(self):
        self.delete("all")
        largura, altura = self.winfo_width(), self.winfo_height()
        if largura < 50 or altura < 50:
            return
        fonte = tema.escolher_fonte()
        if not self.cacadores:
            self.create_text(largura / 2, altura / 2, fill=tema.TEXTO_SECUNDARIO, justify="center",
                             font=(fonte, -int(16 * self.escala)),
                             text="Ninguém na caçada ainda.\n\nOs alunos aparecem aqui quando a caçada começa\n"
                                  "(ou quando abrem a tela 🐉 Esferas do app).")
            return
        cabecalho = 26 * self.escala
        linha = max(16.0, min(46 * self.escala, (altura - cabecalho) / len(self.cacadores)))
        raio = linha * 0.36
        passo = linha * 0.95
        largura_pontos = linha * 2.6
        inicio_esferas = largura - largura_pontos - 7 * passo
        coluna_nome = linha * 1.6
        letra = -int(max(11, linha * 0.42))
        for esfera in range(1, 8):
            self.create_text(inicio_esferas + (esfera - 0.5) * passo, cabecalho / 2, text=f"{esfera}★",
                             fill=tema.TEXTO_SECUNDARIO, font=(fonte, -int(11 * self.escala)))
        self.create_text(largura - largura_pontos / 2, cabecalho / 2, text="pontos", fill=tema.TEXTO_SECUNDARIO,
                         font=(fonte, -int(11 * self.escala)))
        agora = time.time()
        maximo_de_letras = max(4, int((inicio_esferas - coluna_nome) / (linha * 0.26)))
        for posicao, cacador in enumerate(self.cacadores):
            topo = cabecalho + posicao * linha
            meio = topo + linha / 2
            if cacador["posicao"]:
                self.create_rectangle(2, topo + 1, largura - 2, topo + linha - 1, fill=OURO_ESCURO, outline="")
            self.create_text(linha * 0.15, meio, anchor="w", text=f"{cacador['numero']:02d}",
                             fill=tema.TEXTO_SECUNDARIO, font=(fonte, letra, "bold"))
            nome = cacador["nome"]
            if len(nome) > maximo_de_letras:
                nome = nome[:maximo_de_letras - 1] + "…"
            self.create_text(coluna_nome, meio, anchor="w", text=nome, fill=tema.TEXTO, font=(fonte, letra, "bold"))
            for esfera in range(1, 8):
                acendeu = self.recentes.get((cacador["numero"], esfera))
                brilho = max(0.0, 1 - (agora - acendeu) / 2) if acendeu else 0.0
                desenhar_esfera(self, inicio_esferas + (esfera - 0.5) * passo, meio, raio, esfera,
                                acesa=esfera in cacador["esferas"], brilho=brilho,
                                fundo=OURO_ESCURO if cacador["posicao"] else tema.FUNDO)
            pontos = f"{cacador['pontos']}"
            if cacador["posicao"]:
                pontos = f"{cacador['posicao']}º · {pontos}"
            self.create_text(largura - linha * 0.2, meio, anchor="e", text=pontos, fill=tema.DESTAQUE,
                             font=(fonte, letra, "bold"))


class QuadroDaCacada(ctk.CTkFrame):
    """Relogio + grade + podio + feed. O mesmo quadro aparece na aba (pequeno) e no telao (grande)."""

    def __init__(self, mestre, escala=1.0):
        super().__init__(mestre, fg_color="transparent")
        self.escala = escala
        topo = ctk.CTkFrame(self, fg_color="transparent")
        topo.pack(fill="x", pady=(0, 4))
        self.situacao = ctk.CTkLabel(topo, text="", font=tema.fonte(int(16 * escala), negrito=True))
        self.situacao.pack(side="left", padx=4)
        self.relogio = ctk.CTkLabel(topo, text="", font=tema.fonte(int(30 * escala), negrito=True),
                                    text_color=tema.DESTAQUE)
        self.relogio.pack(side="right", padx=4)
        corpo = ctk.CTkFrame(self, fg_color="transparent")
        corpo.pack(fill="both", expand=True)
        lado = ctk.CTkFrame(corpo, fg_color=tema.CARD, corner_radius=10, width=int(220 * escala))
        lado.pack(side="right", fill="y", padx=(6, 0))
        lado.pack_propagate(False)
        self.grade = GradeDaCacada(corpo, escala)
        self.grade.pack(side="left", fill="both", expand=True)
        ctk.CTkLabel(lado, text="🏆 Pódio da caçada", font=tema.fonte(int(15 * escala), negrito=True),
                     text_color=tema.DESTAQUE).pack(anchor="w", padx=10, pady=(8, 2))
        self.podio = ctk.CTkLabel(lado, text="", font=tema.fonte(int(14 * escala), negrito=True), justify="left",
                                  anchor="w", wraplength=int(200 * escala))
        self.podio.pack(anchor="w", padx=10, pady=(0, 8))
        ctk.CTkLabel(lado, text="📜 Achados", font=tema.fonte(int(15 * escala), negrito=True),
                     text_color=tema.DESTAQUE).pack(anchor="w", padx=10)
        self.feed = ctk.CTkTextbox(lado, wrap="word", font=tema.fonte(int(12 * escala)), fg_color=tema.FUNDO)
        self.feed.pack(fill="both", expand=True, padx=6, pady=(2, 6))
        self._assinatura = None

    def mostrar(self, foto, feed, recentes):
        texto, cor = ESTADOS[foto["estado"]]
        if foto["estado"] == "aguardando" and foto["cacadores"]:
            texto += f" · {len(foto['cacadores'])} prontos"
        elif foto["estado"] != "aguardando":
            texto += f" · {len(foto['cacadores'])} caçadores"
        self.situacao.configure(text=texto, text_color=cor)
        restante = foto["tempo_restante"] if foto["estado"] != "encerrada" else None
        self.relogio.configure(text=f"⏱ {relogio(restante)}" if restante is not None else "",
                               text_color=tema.PERIGO if restante is not None and restante <= 60 else tema.DESTAQUE)
        agora = time.time()
        brilhando = {chave: hora for chave, hora in recentes.items() if agora - hora < 2.2}
        assinatura = ([(c["numero"], c["nome"], tuple(c["esferas"]), c["pontos"], c["posicao"])
                       for c in foto["cacadores"]], tuple(brilhando), len(feed), feed[-1] if feed else "",
                      tuple(p["pontos"] for p in foto["podio"]))
        if assinatura == self._assinatura and not brilhando:
            return                                     # nada mudou: nao redesenha (evita piscar)
        self._assinatura = assinatura
        self.grade.mostrar(foto["cacadores"], brilhando)
        linhas = [f"{MEDALHAS[i]} {p['nome']} · {p['pontos']} pts" for i, p in enumerate(foto["podio"])]
        self.podio.configure(text="\n".join(linhas) or "ninguém pontuou ainda")
        self.feed.configure(state="normal")
        self.feed.delete("1.0", "end")
        self.feed.insert("1.0", "\n".join(reversed(feed)))
        self.feed.configure(state="disabled")


class JanelaTelao(ctk.CTkToplevel):
    """A grade da cacada em tela cheia, para o projetor. Esc fecha."""

    def __init__(self, mestre):
        super().__init__(mestre)
        self.title("Caça às Esferas - Telão")
        self.configure(fg_color=tema.FUNDO)
        self.attributes("-fullscreen", True)
        topo = ctk.CTkFrame(self, fg_color="transparent")
        topo.pack(fill="x", padx=30, pady=(18, 6))
        ctk.CTkLabel(topo, text="🐉 CAÇA ÀS ESFERAS DO DRAGÃO", font=tema.fonte(34, negrito=True),
                     text_color=tema.DESTAQUE).pack(side="left")
        tema.botao_secundario(topo, "✕ Sair do telão (Esc)", self.destroy, largura=200).pack(side="right")
        self.quadro = QuadroDaCacada(self, escala=1.7)
        self.quadro.pack(fill="both", expand=True, padx=30, pady=(0, 24))
        self.bind("<Escape>", lambda evento: self.destroy())
        self.after(200, self.focus_force)


class AbaCacada(ctk.CTkFrame):
    def __init__(self, mestre, servidor):
        super().__init__(mestre, fg_color="transparent")
        self.servidor = servidor
        self.cacada = servidor.cacada
        self.ultimo_evento = 0
        self.feed = deque(maxlen=60)
        self.recentes = {}
        self.som = Som()
        self.aviso = AvisoNoTelao(self)
        self.efeito = None
        self.numero_do_efeito = None
        self.telao = None
        self.erro_ao_salvar = ""
        self.criar_botoes()
        self.quadro = QuadroDaCacada(self)
        self.quadro.pack(fill="both", expand=True, padx=4)
        self.criar_rodape()
        self.atualizar()

    # ---------------- montagem ----------------

    def criar_botoes(self):
        linha = ctk.CTkFrame(self, fg_color="transparent")
        linha.pack(fill="x", padx=4, pady=(0, 4))
        self.botao_iniciar = tema.botao(linha, "▶ Iniciar caçada", self.iniciar, largura=140)
        self.botao_iniciar.pack(side="left")
        self.botao_pausar = tema.botao_secundario(linha, "⏸ Pausar", self.pausar_ou_retomar, largura=110)
        self.botao_pausar.pack(side="left", padx=6)
        self.botao_encerrar = tema.botao_secundario(linha, "■ Encerrar", self.encerrar, largura=105)
        self.botao_encerrar.pack(side="left")
        tema.botao_secundario(linha, "↺ Nova caçada", self.nova, largura=125).pack(side="left", padx=6)
        linha = ctk.CTkFrame(self, fg_color="transparent")
        linha.pack(fill="x", padx=4, pady=(0, 6))
        tema.texto_secundario(linha, "Tempo:", 13).pack(side="left")
        self.tempo = ctk.CTkOptionMenu(linha, values=list(TEMPOS), width=120, fg_color=tema.CARD,
                                       button_color=tema.CARD)
        self.tempo.set("20 min")
        self.tempo.pack(side="left", padx=(4, 10))
        self.botao_som = tema.botao_secundario(linha, "🔊 Som", self.trocar_som, largura=90)
        self.botao_som.pack(side="left")
        tema.botao(linha, "⛶ Telão", self.abrir_telao, largura=100).pack(side="left", padx=6)

    def criar_rodape(self):
        linha = ctk.CTkFrame(self, fg_color="transparent")
        linha.pack(fill="x", padx=4, pady=(6, 0))
        tema.texto_secundario(linha, "💡 Dica extra:", 13).pack(side="left")
        self.botoes_dica = {}
        for esfera in esferas.ESFERAS:
            botao = ctk.CTkButton(linha, text=str(esfera), width=34, height=28, fg_color=tema.CARD,
                                  hover_color="#4A4E54", font=tema.fonte(13, negrito=True),
                                  command=lambda n=esfera: self.mandar_dica(n))
            botao.pack(side="left", padx=2)
            self.botoes_dica[esfera] = botao
        linha = ctk.CTkFrame(self, fg_color="transparent")
        linha.pack(fill="x", padx=4, pady=(4, 0))
        self.texto_resultado = tema.texto_secundario(linha, "", 12)
        self.texto_resultado.pack(side="left")
        self.botao_pasta = tema.botao_secundario(linha, "📂 Abrir pasta", self.abrir_pasta, largura=120, altura=28)

    # ---------------- atualizacao (a cada meio segundo) ----------------

    def atualizar(self):
        try:
            foto = self.cacada.instantaneo()
            for evento in self.cacada.eventos_depois(self.ultimo_evento):
                self.ultimo_evento = evento["id"]
                self.tratar(evento)
            if foto["estado"] == "encerrada" and not foto["resultado_salvo"] and not self.erro_ao_salvar:
                self.salvar_resultado()
                foto = self.cacada.instantaneo()
            agora = time.time()
            self.recentes = {chave: hora for chave, hora in self.recentes.items() if agora - hora < 5}
            self.mostrar(foto)
        finally:
            self.after(ATUALIZAR_A_CADA, self.atualizar)

    def mostrar(self, foto):
        estado = foto["estado"]
        self.botao_iniciar.configure(state="normal" if estado == "aguardando" else "disabled")
        self.botao_pausar.configure(state="normal" if estado in ("ativa", "pausada") else "disabled",
                                    text="▶ Retomar" if estado == "pausada" else "⏸ Pausar")
        self.botao_encerrar.configure(state="normal" if estado in ("ativa", "pausada") else "disabled")
        self.tempo.configure(state="normal" if estado == "aguardando" else "disabled")
        for esfera, botao in self.botoes_dica.items():
            enviada = esfera in foto["dicas_extras"]
            botao.configure(fg_color=tema.DESTAQUE_ESCURO if enviada else tema.CARD,
                            text_color=tema.FUNDO if enviada else tema.TEXTO)
        if foto["resultado_salvo"]:
            self.texto_resultado.configure(text=f"✔ Resultado salvo: {os.path.basename(foto['resultado_salvo'])}",
                                           text_color=tema.SUCESSO)
            self.botao_pasta.pack(side="left", padx=8)
        else:
            self.texto_resultado.configure(text=self.erro_ao_salvar, text_color=tema.PERIGO)
            self.botao_pasta.pack_forget()
        self.quadro.mostrar(foto, self.feed, self.recentes)
        if self.telao is not None and self.telao.winfo_exists():
            self.telao.quadro.mostrar(foto, self.feed, self.recentes)

    def anotar(self, evento, texto):
        self.feed.append(f"{evento['hora']} · {texto}")

    def tratar(self, evento):
        """Cada coisa que aconteceu na cacada vira uma linha no feed, um aviso, o efeito ou um som."""
        tipo = evento["tipo"]
        if tipo == "achado":
            self.recentes[(evento["numero"], evento["esfera"])] = time.time()
            if evento["na_largada"]:
                return
            if evento["esfera"] == 1:
                self.anotar(evento, f"{evento['nome']} entrou na caçada (★ {evento['conceito']})")
            else:
                self.anotar(evento, f"{evento['nome']} encontrou a {'★' * evento['esfera']} ({evento['conceito']})")
                self.som.tocar("achado")
        elif tipo == "completou":
            self.anotar(evento, f"🐉 {evento['nome']} juntou as 7 esferas! ({evento['posicao']}º lugar)")
            self.som.tocar("dragao")
            if evento["posicao"] == 1:
                self.abrir_efeito(evento)
            else:
                self.aviso.mostrar(f"🐉 {evento['nome']} também invocou o dragão! ({evento['posicao']}º lugar)",
                                   segundos=6, importante=True)
        elif tipo == "pedido":
            self.anotar(evento, f"🎁 Pedido de {evento['nome']}: {evento['texto']}")
            if self.efeito is not None and self.numero_do_efeito == evento["numero"]:
                self.efeito.mostrar_pedido(evento["pedido"])
            else:
                self.aviso.mostrar(f"🎁 Pedido de {evento['nome']}: {evento['texto']}", segundos=6, importante=True)
        elif tipo == "grito":
            self.anotar(evento, "📡 Alguém gritou na rede!")
            self.aviso.mostrar("📡 Alguém gritou na rede!", segundos=3)
            self.som.tocar("grito")
        elif tipo == "inicio":
            self.feed.clear()
            self.anotar(evento, f"🐉 A caçada começou! ({evento['cacadores']} caçadores)")
            self.som.tocar("inicio")
        elif tipo == "pausa":
            self.anotar(evento, "⏸ Caçada pausada")
        elif tipo == "retomada":
            self.anotar(evento, "▶ Caçada retomada")
        elif tipo == "fim":
            self.anotar(evento, "🏁 Fim da caçada" + (" (acabou o tempo)" if evento["motivo"] == "tempo" else ""))
        elif tipo == "dica_extra":
            self.anotar(evento, f"💡 Dica extra da esfera {evento['esfera']} enviada")
        elif tipo == "nova":
            self.feed.clear()
            self.recentes.clear()

    def abrir_efeito(self, evento):
        if self.efeito is not None and self.efeito.winfo_exists():
            self.efeito.destroy()
        self.numero_do_efeito = evento["numero"]
        self.efeito = EfeitoDragao(self, evento["nome"], esferas.PEDIDOS, ao_fechar=self._efeito_fechou)

    def _efeito_fechou(self):
        self.efeito = None
        self.numero_do_efeito = None

    # ---------------- botoes ----------------

    def iniciar(self):
        try:
            rotas_esferas.iniciar_cacada(self.servidor, TEMPOS[self.tempo.get()])
        except esferas.ErroDaCacada as erro:
            messagebox.showinfo("Caça às Esferas", str(erro), parent=self)

    def pausar_ou_retomar(self):
        if self.cacada.estado == "pausada":
            self.cacada.retomar()
        else:
            self.cacada.pausar()

    def encerrar(self):
        if messagebox.askyesno("Encerrar a caçada", "Encerrar a caçada agora?\n\nO resultado vai ser salvo num "
                                                    "arquivo CSV.", parent=self):
            self.cacada.encerrar()

    def nova(self):
        if not messagebox.askyesno("Nova caçada", "Começar uma NOVA caçada?\n\nOs códigos mudam e o progresso de "
                                                  "todos volta a zero. (Se a caçada atual ainda não terminou, ela "
                                                  "é encerrada e o resultado é salvo antes.)", parent=self):
            return
        if self.cacada.estado in ("ativa", "pausada"):
            self.cacada.encerrar()
        if self.cacada.estado == "encerrada" and not self.cacada.instantaneo()["resultado_salvo"]:
            self.salvar_resultado()
        self.cacada.nova()
        self.erro_ao_salvar = ""

    def mandar_dica(self, esfera):
        endereco = self.servidor.enderecos()[0]
        self.cacada.dica_extra(esfera, endereco)

    def trocar_som(self):
        self.som.mudo = not self.som.mudo
        self.botao_som.configure(text="🔇 Mudo" if self.som.mudo else "🔊 Som")

    def abrir_telao(self):
        if self.telao is not None and self.telao.winfo_exists():
            self.telao.lift()
            return
        self.telao = JanelaTelao(self.winfo_toplevel())

    def salvar_resultado(self):
        try:
            self.cacada.salvar_csv()
            self.erro_ao_salvar = ""
        except OSError as erro:                      # tenta uma vez so (nao fica repetindo a cada meio segundo)
            self.erro_ao_salvar = f"⚠ Não consegui salvar o CSV: {erro}"

    def abrir_pasta(self):
        pasta = esferas.PASTA_DOS_RESULTADOS
        pasta.mkdir(parents=True, exist_ok=True)
        if hasattr(os, "startfile"):
            os.startfile(str(pasta))                 # Windows: abre o Explorador de Arquivos
        else:
            webbrowser.open(pasta.as_uri())
