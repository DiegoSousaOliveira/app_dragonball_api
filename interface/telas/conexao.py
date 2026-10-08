"""Primeira tela: nome do aluno e conexao com o servidor do professor (ou internet direto)."""

import customtkinter as ctk

from core import api, config, descoberta, turma
from interface import tarefas, tema
from interface.telas import Tela

PORTA_PADRAO = 8000


def arrumar_endereco(texto):
    """'http://192.168.0.10:8000/' -> '192.168.0.10:8000'; '192.168.0.10' -> '192.168.0.10:8000'."""
    texto = texto.strip().replace("http://", "").replace("https://", "").strip("/")
    if texto and ":" not in texto:
        texto = f"{texto}:{PORTA_PADRAO}"
    return texto


class TelaConexao(Tela):
    def __init__(self, app):
        super().__init__(app)
        preferencias = config.carregar()
        caixa = ctk.CTkFrame(self, fg_color=tema.CARD, corner_radius=12)
        caixa.place(relx=0.5, rely=0.5, anchor="center")
        miolo = ctk.CTkFrame(caixa, fg_color="transparent")
        miolo.pack(padx=40, pady=32)

        ctk.CTkLabel(miolo, text="🐉", font=tema.fonte(48)).pack()
        tema.titulo(miolo, "Bem-vindo ao Dragon Ball Dex", 26).pack()
        tema.texto_secundario(miolo, "Conecte-se ao servidor do professor para jogar com a turma.",
                              14).pack(pady=(4, 20))

        self.rotulo(miolo, "Seu nome")
        self.nome = ctk.CTkEntry(miolo, width=420, height=38, placeholder_text="ex.: Ana Souza",
                                 font=tema.fonte(15))
        self.nome.pack()
        if preferencias["nome"]:
            self.nome.insert(0, preferencias["nome"])

        self.rotulo(miolo, "Servidor do professor (o endereço aparece no telão)")
        linha = ctk.CTkFrame(miolo, fg_color="transparent")
        linha.pack(fill="x")
        self.endereco = ctk.CTkEntry(linha, width=250, height=38, placeholder_text="ex.: 192.168.0.10:8000",
                                     font=tema.fonte(15))
        self.endereco.pack(side="left")
        if preferencias["servidor"]:
            self.endereco.insert(0, preferencias["servidor"])
        self.botao_procurar = tema.botao_secundario(linha, "🔍 Procurar na rede", self.procurar,
                                                    largura=160, altura=38)
        self.botao_procurar.pack(side="right")

        self.botao_conectar = tema.botao(miolo, "Conectar ao servidor", self.conectar, largura=420, altura=42)
        self.botao_conectar.pack(pady=(18, 8))
        self.mensagem = ctk.CTkLabel(miolo, text="", font=tema.fonte(13), wraplength=420)
        self.mensagem.pack()
        tema.texto_secundario(miolo, "— ou —").pack(pady=(8, 4))
        tema.botao_secundario(miolo, "Usar sem servidor (internet direto)", self.usar_internet,
                              largura=420).pack()
        self.nome.bind("<Return>", lambda evento: self.conectar())
        self.endereco.bind("<Return>", lambda evento: self.conectar())

    def rotulo(self, mestre, texto):
        ctk.CTkLabel(mestre, text=texto, font=tema.fonte(13, negrito=True),
                     text_color=tema.TEXTO).pack(anchor="w", pady=(12, 4))

    def avisar(self, texto, cor=tema.TEXTO_SECUNDARIO):
        self.mensagem.configure(text=texto, text_color=cor)

    def nome_digitado(self):
        nome = " ".join(self.nome.get().split())[:30]
        if not nome:
            self.avisar("Digite o seu nome primeiro.", tema.PERIGO)
            self.nome.focus()
        return nome

    # ---------------- procurar o servidor (UDP broadcast) ----------------

    def procurar(self):
        self.botao_procurar.configure(state="disabled", text="Procurando...")
        self.avisar("Perguntando na rede: 'tem algum servidor Dragon Ball Dex aí?'")
        tarefas.em_segundo_plano(self, descoberta.procurar_servidores, self.achou, self.falhou_procura)

    def achou(self, servidores):
        self.botao_procurar.configure(state="normal", text="🔍 Procurar na rede")
        if not servidores:
            self.avisar("Nenhum servidor respondeu. Digite o endereço que aparece no telão.", tema.PERIGO)
            return
        self.endereco.delete(0, "end")
        self.endereco.insert(0, servidores[0]["endereco"])
        extra = f" (e mais {len(servidores) - 1})" if len(servidores) > 1 else ""
        self.avisar(f"Achei: {servidores[0]['endereco']}{extra}. Clique em Conectar.", tema.SUCESSO)

    def falhou_procura(self, erro):
        self.botao_procurar.configure(state="normal", text="🔍 Procurar na rede")
        self.avisar(f"Não consegui procurar na rede ({erro}). Digite o endereço.", tema.PERIGO)

    # ---------------- conectar ----------------

    def conectar(self):
        nome = self.nome_digitado()
        endereco = arrumar_endereco(self.endereco.get())
        if not nome:
            return
        if not endereco:
            self.avisar("Digite o endereço do servidor (ou clique em Procurar).", tema.PERIGO)
            return
        self.botao_conectar.configure(state="disabled", text="Conectando...")
        self.avisar(f"Batendo na porta de {endereco}...")
        api.definir_aluno(nome)

        def tentar():
            info = turma.verificar_servidor(endereco)
            api.usar_servidor(endereco)
            turma.entrar(nome)
            return info

        tarefas.em_segundo_plano(self, tentar, lambda info: self.conectou(nome, endereco),
                                 self.falhou_conexao)

    def conectou(self, nome, endereco):
        config.salvar(nome=nome, servidor=endereco, modo="servidor")
        self.app.conectado(nome, endereco)

    def falhou_conexao(self, erro):
        api.usar_internet()
        api.sessao.headers.pop("X-Jogador", None)
        self.botao_conectar.configure(state="normal", text="Conectar ao servidor")
        self.avisar(f"Não consegui conectar: {erro} Confira o endereço e se o servidor do professor "
                    "está ligado.", tema.PERIGO)

    def usar_internet(self):
        nome = self.nome_digitado()
        if not nome:
            return
        api.definir_aluno(nome)
        api.usar_internet()
        api.sessao.headers.pop("X-Jogador", None)
        config.salvar(nome=nome, modo="internet")
        self.app.conectado(nome, None)
