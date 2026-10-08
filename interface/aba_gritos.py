"""
Aba "📣 Gritos" do painel: a moderacao MINIMA dos gritos de guerra. Os alunos personalizam livremente; aqui o
professor ouve (▶) e, se precisar, BLOQUEIA (um aluno ou varios selecionados). Bloqueado, o aluno volta na hora ao
grito padrao e nao consegue trocar ate ser liberado (🔊). Mesmo principio do chat: isso NAO tem rota de rede.
"""

import customtkinter as ctk

from core.grito_padrao import ID_DO_PADRAO, gerar_wav
from interface import audio, tema

ATUALIZAR_A_CADA = 1000


def bytes_do_grito(servidor, grito):
    """O audio de um grito, lido direto da pasta do servidor (o painel roda no mesmo PC)."""
    if grito["audio"] != ID_DO_PADRAO:
        arquivo = servidor.gritos.arquivo(grito["audio"])
        if arquivo is not None:
            return arquivo.read_bytes()
    return gerar_wav()


def tocar_grito_no_telao(servidor, id_jogador):
    """O grito de quem conquistou / invocou o dragao toca no PC do professor. Devolve o grito (para a frase)."""
    grito = servidor.gritos.grito_de(id_jogador)
    audio.player().tocar(bytes_do_grito(servidor, grito))
    return grito


class AbaGritos(ctk.CTkFrame):
    def __init__(self, mestre, servidor):
        super().__init__(mestre, fg_color="transparent")
        self.servidor = servidor
        self.marcados = {}                          # id do aluno -> CTkCheckBox
        self._assinatura = None
        topo = ctk.CTkFrame(self, fg_color="transparent")
        topo.pack(fill="x", padx=6, pady=(0, 6))
        tema.texto_secundario(topo, "Os alunos escolhem o grito livremente. 🔇 = volta ao grito padrão e não consegue "
                                    "trocar até você liberar.", 12, wraplength=560, justify="left").pack(anchor="w")
        linha = ctk.CTkFrame(self, fg_color="transparent")
        linha.pack(fill="x", padx=6, pady=(0, 6))
        tema.botao_secundario(linha, "🔇 Bloquear selecionados", lambda: self.marcar_selecionados(True),
                              largura=190).pack(side="left")
        tema.botao_secundario(linha, "🔊 Liberar selecionados", lambda: self.marcar_selecionados(False),
                              largura=180).pack(side="left", padx=6)
        self.som = tema.texto_secundario(linha, audio.player().motivo, 12)
        self.som.pack(side="left", padx=6)
        self.lista = ctk.CTkScrollableFrame(self, fg_color=tema.FUNDO)
        self.lista.pack(fill="both", expand=True, padx=6, pady=(0, 6))
        self.atualizar()

    def alunos(self):
        gritos = self.servidor.gritos.instantaneo()
        resultado = []
        for aluno in self.servidor.sala.visao_do_professor()["alunos"]:
            grito = gritos.get(aluno["id"]) or {"frase": None, "padrao": True, "bloqueado": False,
                                                 "audio_personalizado": False}
            resultado.append(dict(grito, id=aluno["id"], nome=aluno["nome"], online=aluno["estado"] != "ausente"))
        resultado.sort(key=lambda a: (not a["online"], a["nome"].lower()))
        return resultado

    def atualizar(self):
        try:
            alunos = self.alunos()
            assinatura = [(a["id"], a["frase"], a["bloqueado"], a["audio_personalizado"], a["online"]) for a in alunos]
            if assinatura != self._assinatura:
                self._assinatura = assinatura
                self.desenhar(alunos)
        finally:
            self.after(ATUALIZAR_A_CADA, self.atualizar)

    def desenhar(self, alunos):
        marcados = {id_aluno for id_aluno, caixa in self.marcados.items() if caixa.get()}
        for filho in self.lista.winfo_children():
            filho.destroy()
        self.marcados = {}
        if not alunos:
            tema.texto_secundario(self.lista, "Ninguém na sala ainda.", 14).pack(anchor="w", pady=8)
        for aluno in alunos:
            linha = ctk.CTkFrame(self.lista, fg_color=tema.CARD, corner_radius=8)
            linha.pack(fill="x", pady=2)
            caixa = ctk.CTkCheckBox(linha, text="", width=24, fg_color=tema.DESTAQUE)
            caixa.pack(side="left", padx=(8, 2))
            if aluno["id"] in marcados:
                caixa.select()
            self.marcados[aluno["id"]] = caixa
            bloqueado = aluno["bloqueado"]
            botao = ctk.CTkButton(linha, text="🔊" if bloqueado else "🔇", width=36,
                                  fg_color=tema.PERIGO if bloqueado else tema.FUNDO, hover_color="#4A4E54",
                                  command=lambda a=aluno: self.servidor.gritos.bloquear([a["id"]], not a["bloqueado"]))
            botao.pack(side="right", padx=4, pady=4)
            tema.botao_secundario(linha, "▶", lambda a=aluno: tocar_grito_no_telao(self.servidor, a["id"]),
                                  largura=36).pack(side="right")
            frase = "🔇 bloqueado (grito padrão)" if bloqueado else (
                f"“{aluno['frase']}”" + (" 🎵" if aluno["audio_personalizado"] else "") if aluno["frase"] or
                aluno["audio_personalizado"] else "grito padrão")
            cor = tema.SUCESSO if aluno["online"] else tema.TEXTO_SECUNDARIO
            ctk.CTkLabel(linha, text=f"● {aluno['nome']}", font=tema.fonte(14, negrito=True), text_color=cor,
                         anchor="w", width=150).pack(side="left", padx=4)
            ctk.CTkLabel(linha, text=frase, font=tema.fonte(13), anchor="w",
                         text_color=tema.PERIGO if bloqueado else tema.TEXTO).pack(side="left", fill="x", expand=True)

    def marcar_selecionados(self, bloquear):
        ids = [id_aluno for id_aluno, caixa in self.marcados.items() if caixa.get()]
        if ids:
            self.servidor.gritos.bloquear(ids, bloquear)
            for caixa in self.marcados.values():
                caixa.deselect()
