"""
O som dos gritos de guerra no app do aluno, em QUALQUER tela.

O app ja pergunta /turma/sala a cada 1,5 s. Com a Caca ou a Conquista valendo, a resposta traz "novidades"
(o numero do ultimo evento de som e a versao dos gritos). Mudou? So entao o app pede /gritos/eventos: toca os
gritos novos (do cache: o som sai na hora) e pre-carrega os audios da turma. Sem polling novo.
"""

import customtkinter as ctk

from core import api, config, gritos_cliente
from core.grito_padrao import ID_DO_PADRAO
from interface import audio, janelas, tarefas, tema

TOCAR_NO_MAXIMO = 3          # se chegarem muitos eventos de uma vez, so os ultimos tocam


class SomDaTurma:
    def __init__(self, app):
        self.app = app
        self.player = audio.player()
        preferencias = config.carregar()
        self.player.mudo = not preferencias.get("som_ligado", True)
        self.player.volume = int(preferencias.get("som_volume", 80))
        self.reiniciar()

    def reiniciar(self):
        """Nova conexao: comeca do zero (e nao toca de novo o que ja tinha acontecido)."""
        self.ultimo = None
        self.versao = None
        self._buscando = False

    # ---------------- novidades do /turma/sala ----------------

    def novidades(self, novidades):
        if not novidades or self._buscando or not api.conectado_ao_servidor():
            return
        if self.ultimo is None:
            self.ultimo = novidades["eventos"]           # acabou de conectar: o que ja aconteceu nao toca
        if novidades["eventos"] <= self.ultimo and novidades["gritos"] == self.versao:
            return
        self._buscando = True
        depois, versao = self.ultimo, self.versao
        tarefas.em_segundo_plano(self.app, lambda: self._buscar(depois, versao), self._chegou, self._falhou)

    @staticmethod
    def _buscar(depois, versao):
        """Numa thread: os eventos novos e, se os gritos mudaram, o pre-carregamento dos audios da turma."""
        estado = gritos_cliente.eventos(depois)
        if estado["versao"] != versao:
            gritos_cliente.pre_carregar(estado["audios"])
        sons = [(evento, gritos_cliente.em_cache(evento["audio"]) or gritos_cliente.em_cache(ID_DO_PADRAO))
                for evento in estado["eventos"]]
        return estado, sons[-TOCAR_NO_MAXIMO:]

    def _chegou(self, resultado):
        estado, sons = resultado
        self._buscando = False
        self.ultimo, self.versao = estado["ultimo"], estado["versao"]
        for evento, dados in sons:
            self.player.tocar(dados)
            self.app.mostrar_aviso(f"📣 {evento['texto']}   “{evento['frase']}”", tema.DESTAQUE, segundos=5)

    def _falhou(self, erro):
        self._buscando = False

    # ---------------- o meu proprio grito ----------------

    def tocar_meu_grito(self):
        """Ao invadir: o grito do atacante toca no PC dele."""
        def buscar():
            meu = gritos_cliente.meu()
            return gritos_cliente.audio(meu["audio"]) or gritos_cliente.em_cache(ID_DO_PADRAO)

        tarefas.em_segundo_plano(self.app, buscar, self.player.tocar, lambda erro: None)


class JanelaSom:
    """O botao 🔊 do menu: som ligado/desligado e volume (cada PC tem o seu; bom para quem usa fone)."""

    def __init__(self, app):
        self.app = app
        self.player = app.som.player
        janela = self.janela = janelas.criar_janela(app, "Som", 380, 260)
        janela.transient(app)
        miolo = ctk.CTkFrame(janela, fg_color="transparent")
        miolo.pack(fill="both", expand=True, padx=22, pady=16)
        tema.titulo(miolo, "🔊 Som dos gritos de guerra", 18).pack(anchor="w")
        self.chave = ctk.CTkSwitch(miolo, text="Som ligado", font=tema.fonte(14, negrito=True),
                                   progress_color=tema.SUCESSO, command=self.salvar)
        if not self.player.mudo:
            self.chave.select()
        self.chave.pack(anchor="w", pady=(12, 6))
        tema.texto_secundario(miolo, "Volume", 13).pack(anchor="w")
        self.volume = ctk.CTkSlider(miolo, from_=0, to=100, number_of_steps=20, command=lambda valor: self.salvar(),
                                    button_color=tema.DESTAQUE, progress_color=tema.DESTAQUE)
        self.volume.set(self.player.volume)
        self.volume.pack(fill="x", pady=(2, 8))
        aviso = self.player.motivo or "Os sons tocam um de cada vez (no máximo 6 s cada)."
        tema.texto_secundario(miolo, aviso, 12, wraplength=330, justify="left").pack(anchor="w")
        tema.botao_secundario(miolo, "▶ Testar", self.testar, largura=120).pack(anchor="w", pady=(10, 0))

    def salvar(self):
        self.player.mudo = not bool(self.chave.get())
        self.player.volume = int(self.volume.get())
        config.salvar(som_ligado=not self.player.mudo, som_volume=self.player.volume)

    def testar(self):
        if api.conectado_ao_servidor():
            self.app.som.tocar_meu_grito()
        else:
            self.player.tocar(gritos_cliente.em_cache(ID_DO_PADRAO))
