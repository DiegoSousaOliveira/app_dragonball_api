"""Janelas extras (detalhe de personagem, planeta, carrossel) abertas a partir da janela principal."""

import customtkinter as ctk

from core.armazenamento import PASTA_RECURSOS
from interface import tema


def caminho_do_icone():
    for caminho in (PASTA_RECURSOS / "icone.ico", PASTA_RECURSOS / "instalador" / "icone.ico"):
        if caminho.exists():
            return str(caminho)
    return None


def colocar_icone(janela):
    """A esfera do dragao no canto da janela e na barra de tarefas."""
    icone = caminho_do_icone()
    if icone:
        try:
            janela.iconbitmap(icone)
        except Exception:
            pass                      # no Linux o .ico pode nao funcionar: fica o icone padrao


def criar_janela(mestre, titulo, largura, altura):
    """Uma janela filha, centralizada na tela e na frente da principal. Fecha junto com a 'mestre'."""
    janela = ctk.CTkToplevel(mestre)
    janela.title(f"Dragon Ball Dex - {titulo}")
    janela.configure(fg_color=tema.FUNDO)
    centralizar(janela, largura, altura)
    janela.after(250, lambda: janela.winfo_exists() and colocar_icone(janela))   # depois do icone padrao do CTk
    # Por um instante fica acima de tudo (senao pode abrir atras da janela principal)
    janela.attributes("-topmost", True)
    janela.after(300, lambda: janela.winfo_exists() and janela.attributes("-topmost", False))
    janela.after(350, lambda: janela.winfo_exists() and janela.focus_force())
    return janela


BARRA_DE_TAREFAS = 60          # pixels reservados para a barra do Windows


def escala(widget):
    """Escala de tela do Windows (1.0 = 100%, 1.25 = 125%...). O CustomTkinter multiplica os
    tamanhos que passamos por ela; a tela (winfo_screenwidth) ja vem em pixels de verdade."""
    try:
        return ctk.ScalingTracker.get_window_scaling(widget.winfo_toplevel())
    except Exception:
        return 1.0


def centralizar(janela, largura, altura):
    """Centraliza a janela SEM deixar ela passar do tamanho da tela. Devolve True se coube inteira."""
    fator = escala(janela)
    tela_largura = janela.winfo_screenwidth()
    tela_altura = janela.winfo_screenheight() - BARRA_DE_TAREFAS
    cabe = largura * fator <= tela_largura * 0.96 and altura * fator <= tela_altura * 0.95
    largura = min(largura, int(tela_largura * 0.96 / fator))
    altura = min(altura, int(tela_altura * 0.95 / fator))
    x = max(0, (tela_largura - int(largura * fator)) // 2)
    y = max(0, (tela_altura - int(altura * fator)) // 2)
    janela.geometry(f"{largura}x{altura}+{x}+{y}")
    return cabe


def abrir_janela_principal(janela, largura, altura):
    """Janela principal: centralizada; se a tela for pequena demais, abre maximizada."""
    if not centralizar(janela, largura, altura):
        janela.after(50, lambda: janela.state("zoomed"))
