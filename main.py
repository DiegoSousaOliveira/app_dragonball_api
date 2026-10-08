"""
Dragon Ball Dex.

    python main.py                          -> aplicativo do aluno
    python main.py --servidor               -> servidor do professor (com o painel para o telao)
    python main.py --servidor --sem-janela  -> servidor so no terminal (Ctrl+C para parar)
    python main.py --porta 8080             -> escolher outra porta para o servidor
    python main.py --host 127.0.0.1         -> servidor so para este computador (testes)
    python main.py --atualizar-cache        -> apaga o cache de dados e baixa de novo
    python main.py --fumaca [--conectar IP:PORTA]  -> o app testa todas as telas sozinho
    python main.py --demo                   -> modo demonstracao 🎓 (so funciona aberto pelo botao do painel,
                                               que passa o token; sem ele, abre o app normal)

No instalador, "DragonBallDex.exe" e o aluno e "DragonBallDex.exe --servidor" e o professor.
"""

import sys
import time


def valor_do_argumento(nome, padrao):
    if nome in sys.argv:
        posicao = sys.argv.index(nome)
        if posicao + 1 < len(sys.argv):
            return sys.argv[posicao + 1]
    return padrao


def mostrar_erro(titulo, mensagem):
    """No .exe nao ha terminal: o erro aparece numa caixinha."""
    try:
        from tkinter import Tk, messagebox
        raiz = Tk()
        raiz.withdraw()
        messagebox.showerror(titulo, mensagem)
        raiz.destroy()
    except Exception:
        print(f"{titulo}: {mensagem}")


def rodar_servidor():
    from servidor.aplicacao import ServidorDragonBall
    porta = int(valor_do_argumento("--porta", 8000))
    host = valor_do_argumento("--host", "0.0.0.0")
    try:
        servidor = ServidorDragonBall(porta=porta, host=host)
    except OSError as erro:
        mostrar_erro("Servidor Dragon Ball Dex", f"Não consegui ligar o servidor.\n\n{erro}")
        return
    servidor.iniciar()
    if "--sem-janela" in sys.argv:
        print("Servidor Dragon Ball Dex ligado. Os alunos podem usar:", flush=True)
        for endereco in servidor.enderecos():
            print("   ", endereco, flush=True)
        print("Ctrl+C para desligar.", flush=True)
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            servidor.parar()
        return
    from interface.painel_servidor import PainelServidor
    PainelServidor(servidor).mainloop()


def rodar_aluno():
    from core import demo
    from interface.app_aluno import AppAluno
    ensaio = demo.ler_do_ambiente() if "--demo" in sys.argv else None     # (token, endereco) vindos do painel
    AppAluno(demo=ensaio).mainloop()


def principal():
    if "--atualizar-cache" in sys.argv:
        from core import api
        api.limpar_cache()
    if "--servidor" in sys.argv:
        rodar_servidor()
    elif "--fumaca" in sys.argv:
        from interface import fumaca
        sys.exit(0 if fumaca.rodar(valor_do_argumento("--conectar", None)) else 1)
    else:
        rodar_aluno()


if __name__ == "__main__":
    principal()
