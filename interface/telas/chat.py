"""Tela Chat: conversa da turma. O professor ve tudo e pode fechar o chat ou bloquear alunos."""

import customtkinter as ctk

from core import api, turma
from interface import tarefas, tema
from interface.telas import Tela, cabecalho

PERGUNTAR_A_CADA = 1000       # milissegundos
LIMITE = 200                  # caracteres (o servidor corta no mesmo tamanho)
CORES = {"professor": "#2E4A7A", "sistema": "#2B2D31"}


class TelaChat(Tela):
    def __init__(self, app):
        super().__init__(app)
        cabecalho(self, "Chat da turma", "Seja gentil: o professor vê todas as mensagens e pode bloquear o chat.")
        self.versao = None
        self.ultimo_id = 0
        self._agendado = None
        self._pedindo = False
        if not api.conectado_ao_servidor():
            tema.texto_secundario(self, "🔌 O chat só existe no servidor do professor.\n\nClique em \"Trocar conexão\" "
                                        "e conecte-se a ele.", 16, justify="center").pack(pady=80)
            self.lista = None
            return
        self.status = ctk.CTkLabel(self, text="", font=tema.fonte(14, negrito=True))
        self.status.pack(anchor="w", padx=26)
        self.lista = ctk.CTkScrollableFrame(self, fg_color=tema.LATERAL, corner_radius=10)
        self.lista.pack(fill="both", expand=True, padx=20, pady=(4, 8))
        self.lista.grid_columnconfigure(0, weight=1)
        barra = ctk.CTkFrame(self, fg_color="transparent")
        barra.pack(fill="x", padx=20, pady=(0, 16))
        self.campo = ctk.CTkEntry(barra, height=40, font=tema.fonte(15),
                                  placeholder_text="Escreva uma mensagem e aperte Enter...")
        self.campo.pack(side="left", fill="x", expand=True)
        self.campo.bind("<Return>", lambda evento: self.enviar())
        self.campo.bind("<KeyRelease>", lambda evento: self.contar_letras())
        self.contador = tema.texto_secundario(barra, f"0/{LIMITE}", 12)
        self.contador.pack(side="left", padx=8)
        self.botao = tema.botao(barra, "Enviar ➤", self.enviar, largura=110, altura=40)
        self.botao.pack(side="left")
        self.linhas = 0

    # ---------------- aparecer / sumir ----------------

    def ao_mostrar(self):
        if self.lista is not None:
            self.perguntar()
            self.campo.focus_set()

    def ao_esconder(self):
        if self._agendado:
            self.after_cancel(self._agendado)
            self._agendado = None

    # ---------------- receber ----------------

    def perguntar(self):
        if not self.visivel or self._pedindo:
            return
        self._pedindo = True
        depois, versao = self.ultimo_id, self.versao
        tarefas.em_segundo_plano(self, lambda: turma.ler_chat(depois, versao), self.chegou, self.falhou)

    def chegou(self, resposta):
        self._pedindo = False
        if resposta["todas"]:
            for filho in self.lista.winfo_children():
                filho.destroy()
            self.linhas = 0
            self.ultimo_id = 0
        self.versao = resposta["versao"]
        novas = [m for m in resposta["mensagens"] if m["id"] > self.ultimo_id]
        for mensagem in novas:
            self.desenhar(mensagem)
            self.ultimo_id = mensagem["id"]
        if novas:
            self.after(50, self.rolar_para_o_fim)
        self.app.chat_lido = max(self.app.chat_lido or 0, self.ultimo_id)
        self.app.atualizar_selo_do_chat(0)
        self.mostrar_situacao(resposta["liberado"], resposta["bloqueado"])
        self._agendado = self.after(PERGUNTAR_A_CADA, self.perguntar) if self.visivel else None

    def falhou(self, erro):
        self._pedindo = False
        self.status.configure(text=f"⚠ Sem conexão com o servidor ({erro})", text_color=tema.PERIGO)
        self._agendado = self.after(3000, self.perguntar) if self.visivel else None

    def mostrar_situacao(self, liberado, bloqueado):
        if bloqueado:
            texto, cor, pode = "🔇 Você está bloqueado no chat pelo professor.", tema.PERIGO, False
        elif not liberado:
            texto, cor, pode = "🔒 O professor fechou o chat por enquanto.", tema.DESTAQUE, False
        else:
            texto, cor, pode = "", tema.TEXTO, True
        self.status.configure(text=texto, text_color=cor)
        self.campo.configure(state="normal" if pode else "disabled")
        self.botao.configure(state="normal" if pode else "disabled")

    def desenhar(self, mensagem):
        """Minhas mensagens a direita (amarelas); dos colegas a esquerda; professor e sistema no meio."""
        tipo = mensagem["tipo"]
        if tipo == "sistema":
            ctk.CTkLabel(self.lista, text=f"— {mensagem['texto']} ({mensagem['hora']}) —", font=tema.fonte(12),
                         text_color=tema.TEXTO_SECUNDARIO).grid(row=self.linhas, column=0, pady=4)
            self.linhas += 1
            return
        minha = mensagem["minha"]
        if tipo == "professor":
            fundo, cor_nome, lado = CORES["professor"], "#9CC3FF", ""          # "" = centralizado
            nome = "📢 Professor"
        else:
            fundo = tema.DESTAQUE if minha else tema.CARD
            cor_nome = tema.FUNDO if minha else tema.DESTAQUE
            lado = "e" if minha else "w"
            nome = "Você" if minha else mensagem["autor"]
        balao = ctk.CTkFrame(self.lista, fg_color=fundo, corner_radius=12)
        balao.grid(row=self.linhas, column=0, sticky=lado, padx=10, pady=3)
        self.linhas += 1
        ctk.CTkLabel(balao, text=f"{nome}  ·  {mensagem['hora']}", font=tema.fonte(12, negrito=True),
                     text_color=cor_nome, anchor="w").pack(anchor="w", padx=12, pady=(6, 0))
        ctk.CTkLabel(balao, text=mensagem["texto"], font=tema.fonte(14), wraplength=520, justify="left",
                     text_color=tema.FUNDO if minha and tipo == "aluno" else tema.TEXTO,
                     anchor="w").pack(anchor="w", padx=12, pady=(0, 8))

    def rolar_para_o_fim(self):
        try:
            self.lista._parent_canvas.yview_moveto(1.0)
        except Exception:
            pass

    # ---------------- enviar ----------------

    def contar_letras(self):
        texto = self.campo.get()
        if len(texto) > LIMITE:
            self.campo.delete(LIMITE, "end")
        self.contador.configure(text=f"{min(len(texto), LIMITE)}/{LIMITE}")

    def enviar(self):
        texto = self.campo.get().strip()
        if not texto or str(self.botao.cget("state")) == "disabled":
            return
        self.campo.delete(0, "end")
        self.contar_letras()
        tarefas.em_segundo_plano(self, lambda: turma.enviar_chat(texto), lambda r: self.perguntar(),
                                 lambda erro: self.recusada(erro, texto))

    def recusada(self, erro, texto):
        self.status.configure(text=f"⚠ {erro}", text_color=tema.PERIGO)
        if not self.campo.get():
            self.campo.insert(0, texto)                 # devolve o texto para tentar de novo
