"""
Teste de fumaca do app do aluno: abre, conecta, passa por TODAS as telas sozinho e fecha.
Serve para conferir um computador do laboratorio (ou o instalador) em 1 minuto:

    DragonBallDex.exe --fumaca                         (internet direto)
    DragonBallDex.exe --fumaca --conectar 192.168.0.10:8000

O resultado fica em %LOCALAPPDATA%\\DragonBallDex\\fumaca.txt (ou dados_usuario/fumaca.txt).
"""

import tkinter
import traceback
from datetime import datetime

from core import api, turma
from core.armazenamento import PASTA_USUARIO

ARQUIVO = PASTA_USUARIO / "fumaca.txt"


def rodar(endereco=None):
    from interface import ajuda
    from interface.app_aluno import AppAluno
    from interface.telas import batalha as tela_batalha
    from interface.telas.detalhe import JanelaPersonagem

    tela_batalha.PAUSA_ENTRE_RODADAS = 50
    problemas = []
    passos_ok = []

    def anotar_erro(self, tipo, valor, rastro):
        problemas.append("".join(traceback.format_exception(tipo, valor, rastro)))

    tkinter.Tk.report_callback_exception = anotar_erro
    app = AppAluno()

    def conectar():
        api.definir_aluno("Teste de fumaca")
        if endereco:
            turma.verificar_servidor(endereco)
            api.usar_servidor(endereco)
            turma.entrar("Teste de fumaca")
        app.conectado("Teste de fumaca", endereco)

    def abrir_detalhe():
        goku = next(p for p in app.personagens if p["name"] == "Goku")
        JanelaPersonagem(app, goku)

    def lutar():
        app.tela_atual.preparar()

    def comecar_luta():
        if app.tela_atual.arena is not None:
            app.tela_atual.arena.lutar()

    roteiro = [
        (500, "conectar", conectar),
        (5000, "personagens", lambda: app.tela_atual.filtrar()),
        (300, "detalhe", abrir_detalhe),
        (2500, "batalha", lambda: app.mostrar("batalha")),
        (300, "preparar luta", lutar),
        (4000, "lutar", comecar_luta),
        (3000, "planetas", lambda: app.mostrar("planetas")),
        (2000, "ranking", lambda: app.mostrar("ranking")),
        (2000, "quiz", lambda: (app.mostrar("quiz"), app.tela_atual.comecar())),
        (3000, "turma", lambda: app.mostrar("turma")),
        (2000, "chat", lambda: app.mostrar("chat")),
        (2000, "esferas", lambda: app.mostrar("esferas")),
        (2000, "rede", lambda: app.mostrar("rede")),
        (1500, "ajuda", lambda: [ajuda.abrir_ajuda(app, chave) for chave, *_ in ajuda.GUIA][-1].fechar()),
        (2000, "fim", app.destroy),
    ]

    def executar(indice=0):
        if indice >= len(roteiro):
            return
        espera, nome, acao = roteiro[indice]

        def fazer():
            try:
                acao()
                passos_ok.append(nome)
            except Exception:
                problemas.append(f"[{nome}] " + traceback.format_exc())
            executar(indice + 1)

        app.after(espera, fazer)

    executar()
    app.mainloop()
    linhas = [f"Teste de fumaca - {datetime.now():%d/%m/%Y %H:%M}",
              f"Fonte: {endereco or 'internet direto'}",
              f"Passos OK: {len(passos_ok)} de {len(roteiro)} ({', '.join(passos_ok)})",
              f"Problemas: {len(problemas)}"] + problemas
    ARQUIVO.parent.mkdir(parents=True, exist_ok=True)
    ARQUIVO.write_text("\n".join(linhas), encoding="utf-8")
    return len(problemas) == 0 and len(passos_ok) == len(roteiro)
