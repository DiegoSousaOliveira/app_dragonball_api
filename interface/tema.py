"""Cores e fontes do Dragon Ball Dex. Nenhuma cor fica "solta" no codigo: todas moram aqui."""

from tkinter import font as tkfont

import customtkinter as ctk

FUNDO = "#1E1F22"             # fundo das janelas
LATERAL = "#2B2D31"           # menu lateral
CARD = "#3A3D42"              # paineis e cards
DESTAQUE = "#FAC02D"          # amarelo do site da API
DESTAQUE_ESCURO = "#D9A21F"   # amarelo do botao quando o mouse passa por cima
TEXTO = "#FFFFFF"
TEXTO_SECUNDARIO = "#B5B8BD"
PERIGO = "#E5484D"            # vermelho
SUCESSO = "#3DD68C"           # verde
SEM_FOTO = "#6B6E73"          # quadrado cinza quando a imagem nao baixa

_fonte_escolhida = None


def fonte_existe(nome):
    """O Tkinter troca uma fonte que nao existe por outra. Conferimos qual ele usou de verdade."""
    return tkfont.Font(family=nome).actual("family") == nome


def escolher_fonte():
    """Roboto se existir (o CustomTkinter traz ela), senao Segoe UI ou Arial."""
    global _fonte_escolhida
    if _fonte_escolhida is None:
        _fonte_escolhida = "TkDefaultFont"
        for nome in ("Roboto", "Segoe UI", "Arial"):
            if fonte_existe(nome):
                _fonte_escolhida = nome
                break
    return _fonte_escolhida


def fonte(tamanho, negrito=False):
    """Atalho: tema.fonte(22, negrito=True)."""
    peso = "bold" if negrito else "normal"
    return ctk.CTkFont(family=escolher_fonte(), size=tamanho, weight=peso)


def botao(mestre, texto, comando, largura=140, altura=32):
    """Botao amarelo com texto escuro, igual em todas as telas."""
    return ctk.CTkButton(mestre, text=texto, command=comando, width=largura, height=altura,
                         fg_color=DESTAQUE, hover_color=DESTAQUE_ESCURO, text_color=FUNDO,
                         text_color_disabled="#6B6E73", font=fonte(14, negrito=True))


def botao_secundario(mestre, texto, comando, largura=140, altura=32):
    """Botao cinza, para acoes menos importantes."""
    return ctk.CTkButton(mestre, text=texto, command=comando, width=largura, height=altura,
                         fg_color=CARD, hover_color="#4A4E54", text_color=TEXTO,
                         font=fonte(13, negrito=True))


def titulo(mestre, texto, tamanho=22):
    return ctk.CTkLabel(mestre, text=texto, font=fonte(tamanho, negrito=True), text_color=DESTAQUE)


def texto_secundario(mestre, texto, tamanho=13, **opcoes):
    return ctk.CTkLabel(mestre, text=texto, font=fonte(tamanho), text_color=TEXTO_SECUNDARIO, **opcoes)
