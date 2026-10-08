"""As telas da janela principal do aluno (cada uma e um CTkFrame)."""

import customtkinter as ctk

from interface import tema


def cabecalho(tela, titulo, subtitulo=""):
    """Titulo amarelo + uma linha de explicacao no topo de cada tela."""
    area = ctk.CTkFrame(tela, fg_color="transparent")
    area.pack(fill="x", padx=24, pady=(20, 8))
    tema.titulo(area, titulo, 26).pack(anchor="w")
    if subtitulo:
        tema.texto_secundario(area, subtitulo, 14).pack(anchor="w")
    return area


class Tela(ctk.CTkFrame):
    """Base de todas as telas: guarda o app e recebe avisos de quando aparece/some."""

    def __init__(self, app):
        super().__init__(app.area, fg_color="transparent")
        self.app = app
        self.visivel = False

    def ao_mostrar(self):
        """Chamado toda vez que a tela aparece."""

    def ao_esconder(self):
        """Chamado quando o aluno vai para outra tela."""
