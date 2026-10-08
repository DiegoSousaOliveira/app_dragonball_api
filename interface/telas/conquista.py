"""
Tela 🗺 Conquista: o mapa da galaxia, os meus planetas, o meu Guardiao, o botao Invadir, o ranking e o que esta
acontecendo. A luta da invasao e assistida na tela de duelo de sempre (TelaInvasao, logo abaixo): quem joga as
rodadas e o SERVIDOR. So existe com o servidor da sala e depois que o professor da a largada.
"""

from collections import deque
from tkinter import messagebox

import customtkinter as ctk

from core import api, conquista_cliente, gritos_cliente, turma
from interface import janelas, tarefas, tema
from interface.mapa_galaxia import MapaGalaxia, cor_do_dono
from interface.telas import Tela, cabecalho
from interface.telas.desafios import escolha_de_lutador, personagem_escolhido
from interface.telas.duelo import TelaDuelo, TelaDueloBatalha

PERGUNTAR_A_CADA = 1500        # milissegundos (so com a tela aberta)
MEDALHAS = ["🥇", "🥈", "🥉"]
ESTADOS = {"ativa": ("● Conquista valendo!", tema.SUCESSO),
           "aguardando": ("🗺 A Conquista ainda não começou", tema.DESTAQUE),
           "pausada": ("⏸ A Conquista está pausada pelo professor", tema.DESTAQUE),
           "encerrada": ("🏁 A Conquista terminou!", tema.PERIGO)}


def relogio(segundos):
    return f"⏱ {segundos // 60:02d}:{segundos % 60:02d}" if segundos is not None else ""


class JanelaLutador:
    """Escolher um lutador (para ser o Guardiao ou para invadir). ao_escolher(personagem) faz o pedido e devolve
    o erro (texto) ou None; com sucesso, a janela fecha."""

    def __init__(self, app, titulo, explicacao, botao, ao_escolher, inicial=None):
        self.app = app
        self.ao_escolher = ao_escolher
        self.janela = janelas.criar_janela(app, titulo, 460, 300)
        self.janela.transient(app)
        miolo = ctk.CTkFrame(self.janela, fg_color="transparent")
        miolo.pack(fill="both", expand=True, padx=24, pady=18)
        tema.titulo(miolo, titulo, 20).pack()
        tema.texto_secundario(miolo, explicacao, 13, wraplength=400, justify="center").pack(pady=(4, 10))
        self.lutador = escolha_de_lutador(miolo, app, inicial)
        self.mensagem = ctk.CTkLabel(miolo, text="", wraplength=400, font=tema.fonte(13, negrito=True))
        self.mensagem.pack(pady=4)
        self.botao = tema.botao(miolo, botao, self.confirmar, largura=220)
        self.botao.pack()

    def confirmar(self):
        personagem = personagem_escolhido(self.app, self.lutador)
        if personagem is None:
            self.mensagem.configure(text=f'Não encontrei "{self.lutador.get()}".', text_color=tema.PERIGO)
            return
        self.botao.configure(state="disabled")
        self.mensagem.configure(text="Enviando...", text_color=tema.TEXTO_SECUNDARIO)
        self.ao_escolher(personagem, self)

    def falhou(self, texto):
        if self.janela.winfo_exists():
            self.botao.configure(state="normal")
            self.mensagem.configure(text=f"✖ {texto}", text_color=tema.PERIGO)

    def fechar(self):
        if self.janela.winfo_exists():
            self.janela.destroy()


class TelaConquista(Tela):
    def __init__(self, app):
        super().__init__(app)
        cabecalho(self, "Conquista de Territórios", "Proteja os seus planetas e invada os dos colegas. "
                                                    "Quem tiver mais territórios no fim vence!")
        self.visao = None
        self.alvo = None
        self.ultimo_evento = 0
        self.feed = deque(maxlen=30)
        self._agendado = None
        self._pedindo = False
        self._sem_conquista = False
        if not api.conectado_ao_servidor():
            tema.texto_secundario(self, "🔌 A Conquista precisa do servidor da sala.\n\nClique em \"Trocar conexão\" "
                                        "e conecte-se a ele.", 16, justify="center").pack(pady=80)
            self.corpo = None
            return
        self.aviso_geral = tema.texto_secundario(self, "", 16, justify="center")
        self.corpo = ctk.CTkFrame(self, fg_color="transparent")
        self.corpo.pack(fill="both", expand=True, padx=16, pady=(0, 12))
        self.lado = ctk.CTkScrollableFrame(self.corpo, fg_color="transparent", width=290)
        self.lado.pack(side="right", fill="y", padx=(10, 0))          # primeiro o painel: quem encolhe e o mapa
        self.mapa = MapaGalaxia(self.corpo, ao_clicar=self.escolher_alvo)
        self.mapa.pack(side="left", fill="both", expand=True)
        self.criar_painel()

    # ---------------- montagem ----------------

    def cartao(self, titulo):
        caixa = ctk.CTkFrame(self.lado, fg_color=tema.CARD, corner_radius=10)
        caixa.pack(fill="x", pady=4)
        ctk.CTkLabel(caixa, text=titulo, font=tema.fonte(15, negrito=True), text_color=tema.DESTAQUE,
                     anchor="w").pack(fill="x", padx=12, pady=(8, 2))
        return caixa

    def criar_painel(self):
        topo = ctk.CTkFrame(self.lado, fg_color="transparent")
        topo.pack(fill="x")
        self.situacao = ctk.CTkLabel(topo, text="Perguntando ao servidor...", font=tema.fonte(15, negrito=True),
                                     anchor="w", justify="left", wraplength=240)
        self.situacao.pack(fill="x")
        self.relogio = ctk.CTkLabel(topo, text="", font=tema.fonte(22, negrito=True), text_color=tema.DESTAQUE,
                                    anchor="w")
        self.relogio.pack(fill="x")
        self.minha_cor = ctk.CTkLabel(topo, text="", font=tema.fonte(13, negrito=True), anchor="w")
        self.minha_cor.pack(fill="x")
        self.meus = ctk.CTkLabel(topo, text="", font=tema.fonte(13), anchor="w", justify="left", wraplength=240)
        self.meus.pack(fill="x")
        caixa = self.cartao("🛡 Seu Guardião")
        self.nome_guardiao = ctk.CTkLabel(caixa, text="", font=tema.fonte(15, negrito=True), anchor="w",
                                          wraplength=240, justify="left")
        self.nome_guardiao.pack(fill="x", padx=12)
        self.botao_guardiao = tema.botao_secundario(caixa, "Trocar Guardião", self.trocar_guardiao, largura=200)
        self.botao_guardiao.pack(anchor="w", padx=12, pady=(4, 10))
        caixa = self.cartao("⚔ Invadir")
        self.texto_alvo = ctk.CTkLabel(caixa, text="Clique num planeta do mapa para escolher o alvo.",
                                       font=tema.fonte(13), anchor="w", justify="left", wraplength=240)
        self.texto_alvo.pack(fill="x", padx=12)
        self.botao_invadir = tema.botao(caixa, "⚔ Invadir", self.invadir, largura=200)
        self.botao_invadir.pack(anchor="w", padx=12, pady=(6, 4))
        self.resultado = ctk.CTkLabel(caixa, text="", font=tema.fonte(12, negrito=True), anchor="w",
                                      justify="left", wraplength=240)
        self.resultado.pack(fill="x", padx=12, pady=(0, 8))
        self.criar_grito()
        caixa = self.cartao("🏆 Ranking")
        self.ranking = ctk.CTkLabel(caixa, text="", font=tema.fonte(13, negrito=True), anchor="w", justify="left")
        self.ranking.pack(fill="x", padx=12, pady=(0, 8))
        caixa = self.cartao("📜 Acontecendo agora")
        self.texto_feed = ctk.CTkLabel(caixa, text="", font=tema.fonte(12), anchor="w", justify="left",
                                       wraplength=240, text_color=tema.TEXTO_SECUNDARIO)
        self.texto_feed.pack(fill="x", padx=12, pady=(0, 8))

    def criar_grito(self):
        """O meu grito de guerra: a frase + o audio (o SERVIDOR baixa o link, com protecoes)."""
        caixa = self.cartao("📣 Seu grito de guerra")
        self.grito_atual = ctk.CTkLabel(caixa, text="...", font=tema.fonte(14, negrito=True), anchor="w",
                                        justify="left", wraplength=240)
        self.grito_atual.pack(fill="x", padx=12)
        self.campo_frase = ctk.CTkEntry(caixa, placeholder_text="Sua frase (até 40 letras)", height=32)
        self.campo_frase.pack(fill="x", padx=12, pady=(6, 3))
        self.campo_url = ctk.CTkEntry(caixa, placeholder_text="Link do áudio: https://.../grito.mp3", height=32)
        self.campo_url.pack(fill="x", padx=12, pady=3)
        tema.texto_secundario(caixa, "Link DIRETO de um arquivo .mp3, .wav ou .ogg (até 500 KB). YouTube não vale: "
                                     "ele abre uma página, não um arquivo.", 11, wraplength=240,
                              justify="left").pack(anchor="w", padx=12)
        linha = ctk.CTkFrame(caixa, fg_color="transparent")
        linha.pack(fill="x", padx=12, pady=(6, 2))
        tema.botao(linha, "Salvar", self.salvar_grito, largura=76, altura=30).pack(side="left")
        tema.botao_secundario(linha, "▶ Testar", self.app.som.tocar_meu_grito, largura=76, altura=30).pack(
            side="left", padx=4)
        tema.botao_secundario(linha, "Padrão", self.grito_padrao, largura=70, altura=30).pack(side="left")
        self.status_grito = ctk.CTkLabel(caixa, text="", font=tema.fonte(12, negrito=True), anchor="w",
                                         justify="left", wraplength=240)
        self.status_grito.pack(fill="x", padx=12, pady=(0, 8))
        self._grito_carregado = False

    def mostrar_grito(self, meu):
        self._grito_carregado = True
        tipo = " (padrão)" if meu["padrao"] else ("" if not meu["audio_personalizado"] else " 🎵")
        self.grito_atual.configure(text=f"“{meu['frase']}”{tipo}")
        if meu["bloqueado"]:
            self.status_grito.configure(text="🔇 O professor bloqueou o seu grito personalizado.",
                                        text_color=tema.PERIGO)
        elif self.status_grito.cget("text").startswith("🔇"):
            self.status_grito.configure(text="")                    # o professor liberou

    def salvar_grito(self):
        frase = self.campo_frase.get().strip() or None
        url = self.campo_url.get().strip() or None
        if not frase and not url:
            self.status_grito.configure(text="Escreva uma frase e/ou cole um link.", text_color=tema.DESTAQUE)
            return
        self.status_grito.configure(text="Enviando... (o servidor baixa o áudio)", text_color=tema.TEXTO_SECUNDARIO)

        def deu_certo(meu):
            self.campo_frase.delete(0, "end")
            self.campo_url.delete(0, "end")
            self.mostrar_grito(meu)
            self.status_grito.configure(text="✔ Grito salvo!", text_color=tema.SUCESSO)

        tarefas.em_segundo_plano(self, lambda: gritos_cliente.trocar(frase, url), deu_certo,
                                 lambda erro: self.status_grito.configure(text=f"✖ {erro}", text_color=tema.PERIGO))

    def grito_padrao(self):
        tarefas.em_segundo_plano(self, gritos_cliente.usar_padrao,
                                 lambda meu: (self.mostrar_grito(meu), self.status_grito.configure(
                                     text="✔ Voltou ao grito padrão.", text_color=tema.SUCESSO)),
                                 lambda erro: self.status_grito.configure(text=f"✖ {erro}", text_color=tema.PERIGO))

    # ---------------- aparecer / sumir ----------------

    def ao_mostrar(self):
        if self.corpo is not None:
            self.perguntar()
            tarefas.em_segundo_plano(self, gritos_cliente.meu, self.mostrar_grito, lambda erro: None)

    def ao_esconder(self):
        if self._agendado:
            self.after_cancel(self._agendado)
            self._agendado = None

    # ---------------- perguntar ao servidor (GET /conquista/estado) ----------------

    def perguntar(self):
        if not self.visivel or self._pedindo:
            return
        self._pedindo = True
        depois = self.ultimo_evento
        tarefas.em_segundo_plano(self, lambda: conquista_cliente.estado(depois), self.chegou, self.falhou)

    def chegou(self, visao):
        self._pedindo = False
        if self._sem_conquista:
            self._sem_conquista = False
            self.aviso_geral.pack_forget()
            self.corpo.pack(fill="both", expand=True, padx=16, pady=(0, 12))
        self.mostrar(visao)
        self._agendado = self.after(PERGUNTAR_A_CADA, self.perguntar) if self.visivel else None

    def falhou(self, erro):
        self._pedindo = False
        if isinstance(erro, conquista_cliente.SemConquista):
            if not self._sem_conquista:
                self._sem_conquista = True
                self.aviso_geral.configure(text="🗺 Este servidor não tem a Conquista de Territórios.\n\nO computador "
                                                "do professor precisa da versão 2.4 (ou mais nova) do Dragon Ball Dex.")
                self.corpo.pack_forget()
                self.aviso_geral.pack(pady=(30, 0))
            espera = 10000
        else:
            self.situacao.configure(text=f"⚠ Sem conexão com o servidor ({erro})", text_color=tema.PERIGO)
            espera = 3000
        self._agendado = self.after(espera, self.perguntar) if self.visivel else None

    # ---------------- mostrar ----------------

    def mostrar(self, visao):
        if visao["eventos"] and visao["eventos"][0]["tipo"] in ("nova", "inicio"):
            self.feed.clear()
        for evento in visao["eventos"]:
            self.feed.append(f"{evento['hora']} · {evento['texto']}")
        self.ultimo_evento = visao["ultimo_evento"]
        self.visao = visao
        estado, eu = visao["estado"], visao["eu"]
        texto, cor = ESTADOS.get(estado, ("", tema.TEXTO))
        self.situacao.configure(text=texto, text_color=cor)
        self.relogio.configure(text=relogio(visao["tempo_restante"]) if estado != "encerrada" else "")
        lugar = f"  ·  {eu['posicao']}º lugar" if eu["posicao"] and estado != "aguardando" else ""
        self.meus.configure(text=f"Seus planetas: {eu['territorios']}{lugar}\nPoder nas lutas: "
                                 f"{visao['nome_da_metrica']}")
        self.minha_cor.configure(text="● a sua cor no mapa" if eu["cor"] is not None else "",
                                 text_color=cor_do_dono(eu["cor"]) if eu["cor"] is not None else tema.TEXTO)
        sorteado = "" if eu["guardiao"]["escolhido"] else "\n(sorteado: escolha o seu!)"
        self.nome_guardiao.configure(text=f"{eu['guardiao']['nome']}{sorteado}")
        pode_trocar = eu["troca_em"] == 0 and estado != "encerrada"
        self.botao_guardiao.configure(state="normal" if pode_trocar else "disabled",
                                      text="Trocar Guardião" if eu["troca_em"] == 0 else
                                      f"Trocar em {eu['troca_em']} s")
        if self.alvo and not any(t["id"] == self.alvo for t in visao["mapa"]):
            self.alvo = None
        self.mapa.mostrar(visao["mapa"], self.alvo)
        self.mostrar_alvo()
        linhas = [f"{MEDALHAS[i] if i < 3 else str(i + 1) + 'º'} {linha['nome']} · {linha['territorios']} 🪐"
                  for i, linha in enumerate(visao["ranking"])]
        self.ranking.configure(text="\n".join(linhas) or "Ninguém ainda.")
        self.texto_feed.configure(text="\n".join(list(self.feed)[-8:][::-1]) or "Nada ainda.")

    def escolher_alvo(self, id_territorio):
        self.alvo = id_territorio
        self.resultado.configure(text="")
        if self.visao:
            self.mapa.mostrar(self.visao["mapa"], self.alvo)
            self.mostrar_alvo()

    def _territorio(self, id_territorio):
        return next((t for t in (self.visao or {}).get("mapa", []) if t["id"] == id_territorio), None)

    def mostrar_alvo(self):
        eu = self.visao["eu"]
        if eu["invasao"]:
            self.texto_alvo.configure(text="Você está numa invasão agora!")
            self.botao_invadir.configure(state="normal", text="⚔ Ver a minha luta")
            return
        alvo = self._territorio(self.alvo)
        if alvo is None:
            self.texto_alvo.configure(text="Clique num planeta do mapa para escolher o alvo.")
            self.botao_invadir.configure(state="disabled", text="⚔ Invadir")
            return
        dono = f"de {alvo['dono']}" if alvo["dono"] else "neutro"
        self.texto_alvo.configure(text=f"Alvo: {alvo['nome']} ({dono})\nGuardião: {alvo['guardiao']}")
        motivo = ""
        if self.visao["estado"] != "ativa":
            motivo = self.visao["mensagem"]
        elif alvo["meu"]:
            motivo = "Esse planeta já é seu."
        elif alvo["em_batalha"]:
            motivo = "Alguém já está invadindo esse planeta."
        elif alvo["escudo"]:
            motivo = f"Protegido por escudo 🛡 ({alvo['escudo']} s)."
        texto = f"⚔ Invadir em {eu['espera']} s" if eu["espera"] and not motivo else "⚔ Invadir"
        self.botao_invadir.configure(state="disabled" if motivo or eu["espera"] else "normal", text=texto)
        if motivo:
            self.resultado.configure(text=motivo, text_color=tema.TEXTO_SECUNDARIO)

    # ---------------- acoes ----------------

    def trocar_guardiao(self):
        atual = (self.visao or {}).get("eu", {}).get("guardiao", {}).get("nome")

        def escolher(personagem, janela):
            tarefas.em_segundo_plano(self, lambda: conquista_cliente.escolher_guardiao(personagem["id"]),
                                     lambda visao: (janela.fechar(), self.mostrar(visao)),
                                     lambda erro: janela.falhou(str(erro)))

        JanelaLutador(self.app, "🛡 Escolher Guardião", "O Guardião defende TODOS os seus planetas quando alguém "
                      "invade. Depois de trocar, só dá para trocar de novo em 60 s.", "Escolher", escolher, atual)

    def invadir(self):
        eu = self.visao["eu"]
        if eu["invasao"]:
            self.abrir_luta(eu["invasao"], self._territorio(self.alvo))
            return
        alvo = self._territorio(self.alvo)
        if alvo is None:
            return

        def escolher(personagem, janela):
            tarefas.em_segundo_plano(self, lambda: conquista_cliente.invadir(alvo["id"], personagem["id"]),
                                     lambda resposta: (janela.fechar(), self.abrir_luta(resposta["partida"], alvo)),
                                     lambda erro: janela.falhou(str(erro)))

        dono = f"de {alvo['dono']}" if alvo["dono"] else "neutro"
        JanelaLutador(self.app, f"⚔ Invadir {alvo['nome']}",
                      f"{alvo['nome']} ({dono}) é defendido por {alvo['guardiao']}. Poder usado na luta: "
                      f"{self.visao['nome_da_metrica']}. Quem decide a luta é o servidor!", "⚔ Invadir!", escolher)

    def abrir_luta(self, id_partida, alvo):
        nome = alvo["nome"] if alvo else ""
        self.app.som.tocar_meu_grito()                      # ao invadir, o grito toca no PC do atacante
        self.app.abrir_duelo({"id": id_partida, "tipo": "invasao"},
                             classe=lambda app, partida: TelaInvasao(app, partida, nome))


class TelaInvasao(TelaDueloBatalha):
    """A luta de uma invasao: igual ao duelo de batalha (o servidor joga as rodadas), so muda o final."""

    VOLTAR_PARA = "conquista"

    def __init__(self, app, id_partida, alvo=""):
        self.alvo = alvo or "o planeta"
        self.narrados = 0
        self.transformacoes_aplicadas = set()
        TelaDuelo.__init__(self, app, id_partida, f"⚔ Invasão de {alvo}" if alvo else "⚔ Invasão")

    def terminar(self, fim):
        self.acabou = True
        self.botao_desistir.destroy()
        if fim is None:
            texto, cor = "O servidor parou de responder. A luta foi interrompida.", tema.PERIGO
        elif fim["motivo"] == "cancelada":
            texto, cor = "🏁 A Conquista terminou durante a luta: o planeta continua com o dono.", tema.DESTAQUE
        elif fim["vencedor"] == "a":
            texto, cor = f"🏴 VOCÊ CONQUISTOU {self.alvo.upper()}!", tema.SUCESSO
        elif fim["motivo"] == "desistencia":
            texto, cor = "Você desistiu: o Guardião continua no planeta.", tema.PERIGO
        else:
            texto, cor = f"🛡 O Guardião defendeu {self.alvo}. Tente outro alvo!", tema.PERIGO
        self.aviso.configure(text=texto, text_color=cor)
        tema.botao(self.rodape, "Voltar para a Conquista", self.app.fim_do_duelo, largura=240).pack()

    def desistir(self):
        if messagebox.askyesno("Desistir", "Desistir da invasão? O Guardião fica com o planeta.", parent=self):
            tarefas.em_segundo_plano(self, lambda: turma.desistir(self.id_partida))

