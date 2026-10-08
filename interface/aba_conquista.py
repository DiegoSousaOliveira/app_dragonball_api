"""
Aba "🗺 Conquista" do painel do professor: configuracao, os botoes (iniciar, pausar, encerrar, nova), o mapa ao
vivo, o ranking, o feed e o resultado em CSV. O botao "⛶ Telão" abre o mapa em tela cheia para o projetor, com uma
faixa grande quando um planeta troca de dono.
Os controles existem SO aqui (nao ha rota HTTP para iniciar/pausar/encerrar a Conquista).
"""

import os
import time
import webbrowser
from collections import deque
from tkinter import messagebox

import customtkinter as ctk

from interface import tema
from interface.efeito_dragao import Som
from interface.mapa_galaxia import MapaGalaxia
from servidor import conquista as modulo
from servidor import rotas_conquista

ATUALIZAR_A_CADA = 500             # milissegundos
TEMPOS = {"Sem limite": None, "10 min": 10, "15 min": 15, "20 min": 20, "30 min": 30, "45 min": 45}
NEUTROS = [str(n) for n in range(6)]
ESCUDOS = {"30 s": 30, "45 s": 45, "60 s": 60, "90 s": 90}
ESPERAS = {"10 s": 10, "20 s": 20, "30 s": 30, "60 s": 60}
PODERES = {"Total KI": "maxKi", "Base KI": "ki"}
ESTADOS = {"aguardando": ("Aguardando a largada", tema.TEXTO_SECUNDARIO), "ativa": ("● Conquista valendo!", tema.SUCESSO),
           "pausada": ("⏸ Pausada", tema.DESTAQUE), "encerrada": ("🏁 Encerrada", tema.PERIGO)}
MEDALHAS = ["🥇", "🥈", "🥉"]


def relogio(segundos):
    return f"⏱ {segundos // 60:02d}:{segundos % 60:02d}" if segundos is not None else ""


class QuadroDaConquista(ctk.CTkFrame):
    """Relogio + mapa + ranking + feed. O mesmo quadro aparece na aba (pequeno) e no telao (grande)."""

    def __init__(self, mestre, escala=1.0):
        super().__init__(mestre, fg_color="transparent")
        topo = ctk.CTkFrame(self, fg_color="transparent")
        topo.pack(fill="x", pady=(0, 4))
        self.situacao = ctk.CTkLabel(topo, text="", font=tema.fonte(int(16 * escala), negrito=True))
        self.situacao.pack(side="left", padx=4)
        self.relogio = ctk.CTkLabel(topo, text="", font=tema.fonte(int(28 * escala), negrito=True),
                                    text_color=tema.DESTAQUE)
        self.relogio.pack(side="right", padx=4)
        self.faixa = ctk.CTkLabel(self, text="", font=tema.fonte(int(20 * escala), negrito=True), corner_radius=8,
                                  fg_color=tema.CARD, text_color=tema.DESTAQUE)
        self._faixa_ate = 0
        corpo = self._corpo = ctk.CTkFrame(self, fg_color="transparent")
        corpo.pack(fill="both", expand=True)
        lado = ctk.CTkFrame(corpo, fg_color=tema.CARD, corner_radius=10, width=int(230 * escala))
        lado.pack(side="right", fill="y", padx=(6, 0))
        lado.pack_propagate(False)
        self.mapa = MapaGalaxia(corpo)
        self.mapa.pack(side="left", fill="both", expand=True)
        ctk.CTkLabel(lado, text="🏆 Ranking", font=tema.fonte(int(15 * escala), negrito=True),
                     text_color=tema.DESTAQUE).pack(anchor="w", padx=10, pady=(8, 2))
        self.ranking = ctk.CTkLabel(lado, text="", font=tema.fonte(int(13 * escala), negrito=True), justify="left",
                                    anchor="w", wraplength=int(210 * escala))
        self.ranking.pack(anchor="w", padx=10, pady=(0, 8))
        ctk.CTkLabel(lado, text="📜 Acontecendo", font=tema.fonte(int(15 * escala), negrito=True),
                     text_color=tema.DESTAQUE).pack(anchor="w", padx=10)
        self.feed = ctk.CTkTextbox(lado, wrap="word", font=tema.fonte(int(12 * escala)), fg_color=tema.FUNDO)
        self.feed.pack(fill="both", expand=True, padx=6, pady=(2, 6))
        self._assinatura = None

    def mostrar_faixa(self, texto, segundos=5):
        """A faixa grande no alto: "🏴 Ana conquistou Namek de Bruno!"."""
        self.faixa.configure(text=f"  {texto}  ")
        self.faixa.pack(fill="x", pady=(0, 6), before=self._corpo)
        self._faixa_ate = time.time() + segundos

    def mostrar(self, foto, feed):
        texto, cor = ESTADOS[foto["estado"]]
        if foto["estado"] != "aguardando":
            texto += f" · {len(foto['ranking'])} alunos · {foto['lutas']} luta(s) agora"
        self.situacao.configure(text=texto, text_color=cor)
        restante = foto["tempo_restante"] if foto["estado"] != "encerrada" else None
        self.relogio.configure(text=relogio(restante),
                               text_color=tema.PERIGO if restante is not None and restante <= 60 else tema.DESTAQUE)
        if self._faixa_ate and time.time() > self._faixa_ate:
            self.faixa.pack_forget()
            self._faixa_ate = 0
        self.mapa.mostrar(foto["mapa"])
        assinatura = ([(r["nome"], r["territorios"], r["conquistas"], r["defesas"]) for r in foto["ranking"]],
                      len(feed), feed[-1] if feed else "")
        if assinatura == self._assinatura:
            return
        self._assinatura = assinatura
        linhas = []
        for i, linha in enumerate(foto["ranking"][:10]):
            medalha = MEDALHAS[i] if i < 3 else f"{i + 1}º"
            linhas.append(f"{medalha} {linha['nome']} · {linha['territorios']} 🪐   "
                          f"⚔{linha['conquistas']} 🛡{linha['defesas']}")
        self.ranking.configure(text="\n".join(linhas) or "ninguém ainda")
        self.feed.configure(state="normal")
        self.feed.delete("1.0", "end")
        self.feed.insert("1.0", "\n".join(reversed(feed)))
        self.feed.configure(state="disabled")


class JanelaTelao(ctk.CTkToplevel):
    """O mapa da Conquista em tela cheia, para o projetor. Esc fecha."""

    def __init__(self, mestre):
        super().__init__(mestre)
        self.title("Conquista de Territórios - Telão")
        self.configure(fg_color=tema.FUNDO)
        self.attributes("-fullscreen", True)
        topo = ctk.CTkFrame(self, fg_color="transparent")
        topo.pack(fill="x", padx=30, pady=(18, 6))
        ctk.CTkLabel(topo, text="🗺 CONQUISTA DE TERRITÓRIOS", font=tema.fonte(34, negrito=True),
                     text_color=tema.DESTAQUE).pack(side="left")
        tema.botao_secundario(topo, "✕ Sair do telão (Esc)", self.destroy, largura=200).pack(side="right")
        self.quadro = QuadroDaConquista(self, escala=1.6)
        self.quadro.pack(fill="both", expand=True, padx=30, pady=(0, 24))
        self.bind("<Escape>", lambda evento: self.destroy())
        self.after(200, self.focus_force)


class AbaConquista(ctk.CTkFrame):
    def __init__(self, mestre, servidor):
        super().__init__(mestre, fg_color="transparent")
        self.servidor = servidor
        self.conquista = servidor.conquista
        self.ultimo_evento = 0
        self.feed = deque(maxlen=60)
        self.som = Som()
        self.telao = None
        self.erro_ao_salvar = ""
        self.criar_botoes()
        self.quadro = QuadroDaConquista(self)
        self.quadro.pack(fill="both", expand=True, padx=4)
        self.criar_rodape()
        self.atualizar()

    # ---------------- montagem ----------------

    def menu(self, linha, rotulo, valores, inicial, largura=86):
        tema.texto_secundario(linha, rotulo, 12).pack(side="left", padx=(6, 2))
        caixa = ctk.CTkOptionMenu(linha, values=list(valores), width=largura, fg_color=tema.CARD,
                                  button_color=tema.CARD, font=tema.fonte(12))
        caixa.set(inicial)
        caixa.pack(side="left")
        return caixa

    def criar_botoes(self):
        linha = ctk.CTkFrame(self, fg_color="transparent")
        linha.pack(fill="x", padx=4, pady=(0, 4))
        self.botao_iniciar = tema.botao(linha, "▶ Iniciar", self.iniciar, largura=110)
        self.botao_iniciar.pack(side="left")
        self.botao_pausar = tema.botao_secundario(linha, "⏸ Pausar", self.pausar_ou_retomar, largura=105)
        self.botao_pausar.pack(side="left", padx=6)
        self.botao_encerrar = tema.botao_secundario(linha, "■ Encerrar", self.encerrar, largura=100)
        self.botao_encerrar.pack(side="left")
        tema.botao_secundario(linha, "↺ Nova", self.nova, largura=80).pack(side="left", padx=6)
        self.botao_som = tema.botao_secundario(linha, "🔊", self.trocar_som, largura=40)
        self.botao_som.pack(side="left")
        tema.botao(linha, "⛶ Telão", self.abrir_telao, largura=90).pack(side="left", padx=6)
        linha = ctk.CTkFrame(self, fg_color="transparent")
        linha.pack(fill="x", padx=4, pady=(0, 6))
        self.tempo = self.menu(linha, "Tempo", TEMPOS, "20 min", 100)
        self.neutros = self.menu(linha, "Neutros", NEUTROS, str(modulo.NEUTROS_PADRAO), 54)
        self.escudo = self.menu(linha, "Escudo", ESCUDOS, f"{modulo.ESCUDO_PADRAO} s", 66)
        self.espera = self.menu(linha, "Espera", ESPERAS, f"{modulo.ESPERA_PADRAO} s", 66)
        self.poder = self.menu(linha, "Poder", PODERES, "Total KI", 92)
        self.configuracao = (self.tempo, self.neutros, self.escudo, self.espera, self.poder)

    def criar_rodape(self):
        linha = ctk.CTkFrame(self, fg_color="transparent")
        linha.pack(fill="x", padx=4, pady=(4, 0))
        self.texto_resultado = tema.texto_secundario(linha, "", 12)
        self.texto_resultado.pack(side="left")
        self.botao_pasta = tema.botao_secundario(linha, "📂 Abrir pasta", self.abrir_pasta, largura=120, altura=28)

    # ---------------- atualizacao (a cada meio segundo) ----------------

    def atualizar(self):
        try:
            foto = self.conquista.instantaneo()
            for evento in self.conquista.eventos_depois(self.ultimo_evento):
                self.ultimo_evento = evento["id"]
                self.tratar(evento)
            if foto["estado"] == "encerrada" and not foto["resultado_salvo"] and not self.erro_ao_salvar:
                self.salvar_resultado()
                foto = self.conquista.instantaneo()
            self.mostrar(foto)
        finally:
            self.after(ATUALIZAR_A_CADA, self.atualizar)

    def mostrar(self, foto):
        estado = foto["estado"]
        self.botao_iniciar.configure(state="normal" if estado == "aguardando" else "disabled")
        self.botao_pausar.configure(state="normal" if estado in ("ativa", "pausada") else "disabled",
                                    text="▶ Retomar" if estado == "pausada" else "⏸ Pausar")
        self.botao_encerrar.configure(state="normal" if estado in ("ativa", "pausada") else "disabled")
        for caixa in self.configuracao:
            caixa.configure(state="normal" if estado == "aguardando" else "disabled")
        if foto["resultado_salvo"]:
            self.texto_resultado.configure(text=f"✔ Resultado salvo: {os.path.basename(foto['resultado_salvo'])}",
                                           text_color=tema.SUCESSO)
            self.botao_pasta.pack(side="left", padx=8)
        else:
            self.texto_resultado.configure(text=self.erro_ao_salvar, text_color=tema.PERIGO)
            self.botao_pasta.pack_forget()
        self.quadro.mostrar(foto, self.feed)
        if self.telao is not None and self.telao.winfo_exists():
            self.telao.quadro.mostrar(foto, self.feed)

    def tratar(self, evento):
        """Cada coisa que aconteceu vira uma linha no feed; as conquistas tambem viram faixa no telao e som."""
        tipo = evento["tipo"]
        if tipo in ("inicio", "nova"):
            self.feed.clear()
        if tipo != "nova":
            self.feed.append(f"{evento['hora']} · {evento['texto']}")
        if tipo == "conquista":
            for quadro in self._quadros():
                quadro.mostrar_faixa(evento["texto"])
            self.som.tocar("conquista")
        elif tipo == "defesa":
            self.som.tocar("defesa")
        elif tipo == "invasao":
            self.som.tocar("invasao")
        elif tipo == "inicio":
            self.som.tocar("inicio")

    def _quadros(self):
        quadros = [self.quadro]
        if self.telao is not None and self.telao.winfo_exists():
            quadros.append(self.telao.quadro)
        return quadros

    # ---------------- botoes ----------------

    def iniciar(self):
        try:
            rotas_conquista.iniciar_conquista(self.servidor, TEMPOS[self.tempo.get()], neutros=int(self.neutros.get()),
                                              escudo=ESCUDOS[self.escudo.get()], espera=ESPERAS[self.espera.get()],
                                              metrica=PODERES[self.poder.get()])
        except modulo.ErroDaConquista as erro:
            messagebox.showinfo("Conquista de Territórios", str(erro), parent=self)

    def pausar_ou_retomar(self):
        if self.conquista.estado == "pausada":
            self.conquista.retomar()
        else:
            self.conquista.pausar()

    def encerrar(self):
        if messagebox.askyesno("Encerrar a Conquista", "Encerrar a Conquista agora?\n\nLutas pela metade são "
                                                       "canceladas e o resultado vai para um arquivo CSV.",
                               parent=self):
            self.conquista.encerrar()

    def nova(self):
        if not messagebox.askyesno("Nova conquista", "Começar uma NOVA Conquista?\n\nO mapa e o ranking voltam a "
                                                     "zero. (Se a atual ainda não terminou, ela é encerrada e o "
                                                     "resultado é salvo antes.)", parent=self):
            return
        if self.conquista.estado in ("ativa", "pausada"):
            self.conquista.encerrar()
        if self.conquista.estado == "encerrada" and not self.conquista.instantaneo()["resultado_salvo"]:
            self.salvar_resultado()
        self.conquista.nova()
        self.erro_ao_salvar = ""

    def trocar_som(self):
        self.som.mudo = not self.som.mudo
        self.botao_som.configure(text="🔇" if self.som.mudo else "🔊")

    def abrir_telao(self):
        if self.telao is not None and self.telao.winfo_exists():
            self.telao.lift()
            return
        self.telao = JanelaTelao(self.winfo_toplevel())

    def salvar_resultado(self):
        try:
            self.conquista.salvar_csv()
            self.erro_ao_salvar = ""
        except OSError as erro:                      # tenta uma vez so
            self.erro_ao_salvar = f"⚠ Não consegui salvar o CSV: {erro}"

    def abrir_pasta(self):
        pasta = modulo.PASTA_DOS_RESULTADOS
        pasta.mkdir(parents=True, exist_ok=True)
        if hasattr(os, "startfile"):
            os.startfile(str(pasta))
        else:
            webbrowser.open(pasta.as_uri())

