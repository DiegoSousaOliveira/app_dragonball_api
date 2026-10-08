"""Tela Esferas: a Caca as Esferas do Dragao. O aluno ve o numero de cacador, as 7 esferas, a dica da vez,
digita os codigos que encontrar pela rede e grita a palavra magica (UDP). So existe com o servidor da sala."""

import math

import customtkinter as ctk

from core import api, esferas_cliente
from interface import janelas, tarefas, tema
from interface.desenho_esfera import desenhar_esfera
from interface.telas import Tela, cabecalho

PERGUNTAR_A_CADA = 1500       # milissegundos (so enquanto a tela esta aberta)
AZUL = "#9CC3FF"              # a mesma cor das mensagens do professor no chat
ESTADOS = {"ativa": ("● Caçada valendo!", tema.SUCESSO), "aguardando": ("🐉 A caçada ainda não começou", tema.DESTAQUE),
           "pausada": ("⏸ A caçada está pausada pelo professor", tema.DESTAQUE),
           "encerrada": ("🏁 A caçada terminou!", tema.PERIGO)}


class FileiraDeEsferas(ctk.CTkCanvas):
    """As 7 esferas lado a lado. Quando uma acende, ela cresce, brilha e volta ao tamanho normal."""

    RAIO = 29
    ESPACO = 74               # 7 x 74 cabe ate na janela minima (820 x 540)

    def __init__(self, mestre):
        super().__init__(mestre, width=7 * self.ESPACO, height=2 * self.RAIO + 26, bg=tema.FUNDO,
                         highlightthickness=0)
        self.acesas = set()
        self.animando = {}           # esfera -> quadro da animacao (0 a 20)
        self._agendado = None

    def mostrar(self, acesas, animar=True):
        novas = set(acesas) - self.acesas
        self.acesas = set(acesas)
        if animar:
            for esfera in novas:
                self.animando[esfera] = 0
        self.desenhar()

    def desenhar(self):
        self.delete("all")
        meio = self.RAIO + 13
        for esfera in range(1, 8):
            x = self.ESPACO * (esfera - 0.5)
            quadro = self.animando.get(esfera)
            if quadro is None:
                desenhar_esfera(self, x, meio, self.RAIO, esfera, acesa=esfera in self.acesas)
            else:
                progresso = quadro / 20
                raio = self.RAIO * (1 + 0.3 * math.sin(math.pi * progresso))
                desenhar_esfera(self, x, meio, raio, esfera, brilho=1 - progresso, giro=progresso * 2 * math.pi)
        if self.animando and self._agendado is None:
            self._agendado = self.after(35, self._proximo_quadro)

    def _proximo_quadro(self):
        self._agendado = None
        self.animando = {esfera: quadro + 1 for esfera, quadro in self.animando.items() if quadro < 20}
        self.desenhar()


class JanelaPedido:
    """A escolha do pedido ao dragao (30 s). Nao da para fechar no X: ou escolhe, ou o tempo acaba."""

    def __init__(self, tela, pedido):
        self.tela = tela
        self.restante = pedido["segundos"]
        self.janela = janelas.criar_janela(tela.app, "Pedido ao dragão", 560, 420)
        self.janela.protocol("WM_DELETE_WINDOW", lambda: None)
        ctk.CTkLabel(self.janela, text="🐉", font=tema.fonte(48)).pack(pady=(18, 0))
        tema.titulo(self.janela, "Você invocou o dragão!", 26).pack()
        tema.texto_secundario(self.janela, "Faça o seu pedido. Ele vai aparecer no telão!", 14).pack(pady=(2, 12))
        self.botoes = []
        for opcao in pedido["opcoes"]:
            botao = tema.botao(self.janela, opcao["texto"], lambda n=opcao["id"]: self.escolher(n), largura=460,
                               altura=44)
            botao.pack(pady=5)
            self.botoes.append(botao)
        self.relogio = ctk.CTkLabel(self.janela, text="", font=tema.fonte(14, negrito=True))
        self.relogio.pack(pady=(12, 0))
        self.contar()

    def aberta(self):
        try:
            return bool(self.janela.winfo_exists())
        except Exception:
            return False

    def contar(self):
        if not self.aberta():
            return
        if self.restante <= 0:
            self.relogio.configure(text="O tempo acabou: valeu o 1º pedido.", text_color=tema.PERIGO)
            for botao in self.botoes:
                botao.configure(state="disabled")
            self.janela.after(2500, self.fechar)
            return
        self.relogio.configure(text=f"Se você não escolher em {self.restante} s, vale o 1º pedido.",
                               text_color=tema.DESTAQUE if self.restante > 10 else tema.PERIGO)
        self.restante -= 1
        self.janela.after(1000, self.contar)

    def escolher(self, opcao):
        for botao in self.botoes:
            botao.configure(state="disabled")
        self.relogio.configure(text="Enviando o pedido...", text_color=tema.TEXTO_SECUNDARIO)
        tarefas.em_segundo_plano(self.janela, lambda: esferas_cliente.pedir(opcao), self.pedido_aceito,
                                 self.pedido_recusado)

    def pedido_aceito(self, visao):
        self.fechar()
        self.tela.mostrar(visao)

    def pedido_recusado(self, erro):
        self.relogio.configure(text=f"⚠ {erro}", text_color=tema.PERIGO)
        self.janela.after(2500, self.fechar)

    def fechar(self):
        if self.aberta():
            self.janela.destroy()


class TelaEsferas(Tela):
    def __init__(self, app):
        super().__init__(app)
        cabecalho(self, "Caça às Esferas", "Encontre as 7 Esferas do Dragão escondidas na rede da sala! "
                                           "Cada uma ensina um segredo de Redes.")
        self.visao = None
        self.janela_pedido = None
        self._agendado = None
        self._pedindo = False
        self._resgatando = False         # pedido de resgate a caminho (o botao fica apagado)
        self._gritando = False
        self._sem_cacada = False
        if not api.conectado_ao_servidor():
            tema.texto_secundario(self, "🔌 A caçada precisa do servidor da sala.\n\nClique em \"Trocar conexão\" "
                                        "e conecte-se a ele.", 16, justify="center").pack(pady=80)
            self.corpo = None
            return
        self.aviso_geral = tema.texto_secundario(self, "", 16, justify="center")
        self.corpo = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.corpo.pack(fill="both", expand=True, padx=14, pady=(0, 10))
        self.criar_topo()
        self.fileira = FileiraDeEsferas(self.corpo)
        self.fileira.pack(anchor="w", padx=8, pady=(6, 0))
        self.aprendeu = ctk.CTkLabel(self.corpo, text="", font=tema.fonte(13), text_color=tema.SUCESSO,
                                     justify="left", anchor="w")
        self.aprendeu.pack(fill="x", padx=12, pady=(0, 6))
        self.criar_dica()
        self.criar_resgate()
        self.criar_grito()
        self.corpo.bind("<Configure>", self._ajustar_quebra_de_linha)

    # ---------------- montagem ----------------

    def criar_topo(self):
        caixa = ctk.CTkFrame(self.corpo, fg_color=tema.CARD, corner_radius=10)
        caixa.pack(fill="x", padx=6, pady=(0, 4))
        numero = ctk.CTkFrame(caixa, fg_color="transparent")
        numero.pack(side="left", padx=16, pady=8)
        tema.texto_secundario(numero, "Seu número de caçador", 13).pack(anchor="w")
        self.numero = ctk.CTkLabel(numero, text="--", font=tema.fonte(34, negrito=True), text_color=tema.DESTAQUE)
        self.numero.pack(anchor="w")
        meio = ctk.CTkFrame(caixa, fg_color="transparent")
        meio.pack(side="left", padx=16, fill="x", expand=True)
        self.situacao = ctk.CTkLabel(meio, text="Perguntando ao servidor...", font=tema.fonte(17, negrito=True),
                                     anchor="w")
        self.situacao.pack(anchor="w")
        self.pontos = tema.texto_secundario(meio, "", 14)
        self.pontos.pack(anchor="w")
        self.relogio = ctk.CTkLabel(caixa, text="", font=tema.fonte(26, negrito=True), text_color=tema.DESTAQUE)
        self.relogio.pack(side="right", padx=16)

    def criar_dica(self):
        caixa = ctk.CTkFrame(self.corpo, fg_color=tema.CARD, corner_radius=10)
        caixa.pack(fill="x", padx=6, pady=4)
        self.titulo_dica = ctk.CTkLabel(caixa, text="", font=tema.fonte(16, negrito=True), text_color=tema.DESTAQUE,
                                        anchor="w")
        self.titulo_dica.pack(fill="x", padx=14, pady=(10, 2))
        self.texto_dica = ctk.CTkLabel(caixa, text="", font=tema.fonte(15), justify="left", anchor="w",
                                       wraplength=640)
        self.texto_dica.pack(fill="x", padx=14, pady=(0, 4))
        self.extra = ctk.CTkLabel(caixa, text="", font=tema.fonte(14, negrito=True), text_color=AZUL,
                                  justify="left", anchor="w", wraplength=640)
        self.extra.pack(fill="x", padx=14, pady=(0, 10))

    def criar_resgate(self):
        linha = ctk.CTkFrame(self.corpo, fg_color="transparent")
        linha.pack(fill="x", padx=6, pady=(8, 0))
        self.campo_codigo = ctk.CTkEntry(linha, width=230, height=40, font=tema.fonte(17, negrito=True),
                                         placeholder_text="ESF-XXXXX")
        self.campo_codigo.pack(side="left")
        self.campo_codigo.bind("<Return>", lambda evento: self.resgatar())
        self.botao_resgatar = tema.botao(linha, "⭐ Resgatar", self.resgatar, largura=130, altura=40)
        self.botao_resgatar.pack(side="left", padx=8)
        self.resultado = ctk.CTkLabel(self.corpo, text="", font=tema.fonte(14, negrito=True), justify="left",
                                      anchor="w", wraplength=640)
        self.resultado.pack(fill="x", padx=10, pady=(4, 6))

    def criar_grito(self):
        caixa = ctk.CTkFrame(self.corpo, fg_color=tema.LATERAL, corner_radius=10)
        caixa.pack(fill="x", padx=6, pady=4)
        ctk.CTkLabel(caixa, text="📣 Grito na rede", font=tema.fonte(15, negrito=True), text_color=tema.DESTAQUE
                     ).pack(anchor="w", padx=14, pady=(8, 2))
        linha = ctk.CTkFrame(caixa, fg_color="transparent")
        linha.pack(fill="x", padx=14)
        self.campo_palavra = ctk.CTkEntry(linha, width=230, height=36, font=tema.fonte(15),
                                          placeholder_text="palavra mágica")
        self.campo_palavra.pack(side="left")
        self.campo_palavra.bind("<Return>", lambda evento: self.gritar())
        self.botao_gritar = tema.botao_secundario(linha, "📡 Gritar na rede", self.gritar, largura=160, altura=36)
        self.botao_gritar.pack(side="left", padx=8)
        self.direto = ctk.CTkCheckBox(linha, text="Mandar direto para o servidor (unicast)", font=tema.fonte(13),
                                      fg_color=tema.DESTAQUE)
        self.resultado_grito = ctk.CTkLabel(caixa, text="", font=tema.fonte(13, negrito=True), justify="left",
                                            anchor="w", wraplength=640)
        self.resultado_grito.pack(fill="x", padx=14, pady=(4, 10))

    def _ajustar_quebra_de_linha(self, evento):
        largura = max(300, int(evento.width / janelas.escala(self)) - 60)
        for rotulo in (self.texto_dica, self.extra, self.resultado, self.resultado_grito, self.aprendeu):
            rotulo.configure(wraplength=largura)

    # ---------------- aparecer / sumir ----------------

    def ao_mostrar(self):
        if self.corpo is not None:
            self.perguntar()

    def ao_esconder(self):
        if self._agendado:
            self.after_cancel(self._agendado)
            self._agendado = None

    def destroy(self):
        if self.janela_pedido is not None:
            self.janela_pedido.fechar()
        super().destroy()

    # ---------------- perguntar ao servidor (GET /esferas/estado) ----------------

    def perguntar(self):
        if not self.visivel or self._pedindo:
            return
        self._pedindo = True
        tarefas.em_segundo_plano(self, esferas_cliente.estado, self.chegou, self.falhou)

    def chegou(self, visao):
        self._pedindo = False
        if self._sem_cacada:                           # o professor atualizou o servidor
            self._sem_cacada = False
            self.aviso_geral.pack_forget()
            self.corpo.pack(fill="both", expand=True, padx=14, pady=(0, 10))
        self.mostrar(visao)
        self._agendado = self.after(PERGUNTAR_A_CADA, self.perguntar) if self.visivel else None

    def falhou(self, erro):
        self._pedindo = False
        if isinstance(erro, esferas_cliente.SemCacada):
            if not self._sem_cacada:
                self._sem_cacada = True
                self.aviso_geral.configure(text="🐉 Este servidor não tem a Caça às Esferas.\n\nO computador do "
                                                "professor precisa da versão 2.3 (ou mais nova) do Dragon Ball Dex.")
                self.corpo.pack_forget()
                self.aviso_geral.pack(pady=(30, 0))
            espera = 10000
        else:
            self.situacao.configure(text=f"⚠ Sem conexão com o servidor ({erro})", text_color=tema.PERIGO)
            espera = 3000
        self._agendado = self.after(espera, self.perguntar) if self.visivel else None

    # ---------------- mostrar ----------------

    def mostrar(self, visao):
        primeira_vez = self.visao is None
        self.visao = visao
        estado = visao["estado"]
        self.numero.configure(text=f"{visao['numero']:02d}")
        texto, cor = ESTADOS.get(estado, ("", tema.TEXTO))
        if estado == "aguardando":
            texto += " — espere o professor dar a largada."
        self.situacao.configure(text=texto, text_color=cor)
        pontos = f"{visao['pontos']} ponto{'s' if visao['pontos'] != 1 else ''} na caçada"
        if visao["colocacao"] and estado != "aguardando":
            pontos += f"  ·  {visao['colocacao']}º lugar de {visao['total_cacadores']}"
        self.pontos.configure(text=pontos)
        restante = visao["tempo_restante"]
        self.relogio.configure(text=f"⏱ {restante // 60:02d}:{restante % 60:02d}"
                               if restante is not None and estado != "encerrada" else "")
        self.fileira.mostrar(visao["esferas"], animar=not primeira_vez)
        ultima = visao["ultima"]
        self.aprendeu.configure(text=f"✔ Esfera {ultima['esfera']}: {ultima['aprendeu']}" if ultima else "")
        self.mostrar_dica(visao)
        ativa = estado == "ativa"
        for widget, ocupado in ((self.campo_codigo, False), (self.botao_resgatar, self._resgatando),
                                (self.campo_palavra, False), (self.botao_gritar, self._gritando)):
            widget.configure(state="normal" if ativa and not ocupado else "disabled")
        if visao["grito_direto"]:
            self.direto.pack(side="left", padx=6)
        pedido = visao["pedido"]
        aberta = self.janela_pedido is not None and self.janela_pedido.aberta()
        if ativa and pedido and pedido["pendente"] and not aberta:
            self.janela_pedido = JanelaPedido(self, pedido)

    def mostrar_dica(self, visao):
        dica, pedido = visao["dica"], visao["pedido"]
        if visao["estado"] == "aguardando":
            titulo, texto = "🔎 Dica", "Quando o professor começar a caçada, a primeira dica aparece aqui."
        elif dica:
            titulo = f"🔎 Dica da esfera {dica['esfera']}  {dica['estrelas']}"
            texto = dica["texto"]
        else:
            titulo = f"🐉 Você juntou as 7 esferas! ({visao['posicao']}º lugar)"
            if pedido and pedido["escolhido"]:
                texto = f"Seu pedido ao dragão: {pedido['texto']}"
            else:
                texto = "Faça o seu pedido ao dragão!"
        self.titulo_dica.configure(text=titulo)
        self.texto_dica.configure(text=texto)
        extra = dica["extra"] if dica else ""
        self.extra.configure(text=f"Dica extra do professor: {extra}" if extra else "")

    # ---------------- resgatar um codigo ----------------

    def avisar(self, rotulo, texto, cor):
        rotulo.configure(text=texto, text_color=cor)

    def resgatar(self):
        codigo = self.campo_codigo.get().strip()
        if str(self.botao_resgatar.cget("state")) == "disabled":
            return
        if not codigo:
            self.avisar(self.resultado, "Digite o código que você encontrou (ex.: ESF-7KQ2M).", tema.DESTAQUE)
            return
        self._resgatando = True
        self.botao_resgatar.configure(state="disabled")
        tarefas.em_segundo_plano(self, lambda: esferas_cliente.resgatar(codigo), self.resgatou, self.recusou)

    def resgatou(self, visao):
        self._resgatando = False
        self.botao_resgatar.configure(state="normal")
        self.campo_codigo.delete(0, "end")
        resgate = visao["resgate"]
        self.avisar(self.resultado, resgate["mensagem"], tema.SUCESSO if resgate["nova"] else tema.DESTAQUE)
        self.mostrar(visao)

    def recusou(self, erro):
        self._resgatando = False
        self.botao_resgatar.configure(state="normal")
        status = getattr(erro, "status", None)
        cor = tema.DESTAQUE if status in (409, 429) else tema.PERIGO
        self.avisar(self.resultado, f"✖ {erro}", cor)
        if status == 409:
            self.perguntar()

    # ---------------- gritar na rede (UDP) ----------------

    def gritar(self):
        palavra = self.campo_palavra.get().strip()
        if str(self.botao_gritar.cget("state")) == "disabled" or self.visao is None:
            return
        if not palavra:
            self.avisar(self.resultado_grito, "Escreva a palavra mágica primeiro.", tema.DESTAQUE)
            return
        direto = bool(self.direto.get()) and self.visao["grito_direto"]
        numero = self.visao["numero"]
        self._gritando = True
        self.botao_gritar.configure(state="disabled", text="📡 Gritando...")
        como = "só para o servidor (unicast)" if direto else "para a rede inteira (broadcast)"
        self.avisar(self.resultado_grito, f"Gritando {como}: um pacote UDP para a porta 50505...",
                    tema.TEXTO_SECUNDARIO)
        tarefas.em_segundo_plano(self, lambda: esferas_cliente.gritar(numero, palavra, direto), self.ouviu,
                                 self.grito_falhou)

    def ouviu(self, resposta):
        self._gritando = False
        self.botao_gritar.configure(state="normal", text="📡 Gritar na rede")
        if resposta is None:
            self.avisar(self.resultado_grito, "Ninguém respondeu... 🤫 A rede da escola pode estar bloqueando "
                                              "gritos (broadcast). Peça uma dica ao professor!", tema.PERIGO)
        elif resposta.get("ok"):
            codigo = resposta.get("codigo", "")
            self.campo_codigo.delete(0, "end")
            self.campo_codigo.insert(0, codigo)
            self.avisar(self.resultado_grito, f"{resposta.get('mensagem', '')}  Código: {codigo}  (já está no "
                                              "campo lá em cima: clique em ⭐ Resgatar)", tema.SUCESSO)
        else:
            self.avisar(self.resultado_grito, resposta.get("mensagem", "O servidor não aceitou o grito."),
                        tema.DESTAQUE)

    def grito_falhou(self, erro):
        self._gritando = False
        self.botao_gritar.configure(state="normal", text="📡 Gritar na rede")
        self.avisar(self.resultado_grito, f"Não consegui gritar na rede ({erro}).", tema.PERIGO)
