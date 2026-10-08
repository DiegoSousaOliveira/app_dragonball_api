"""
Chat da turma.

Os alunos so podem LER (GET /chat) e ENVIAR (POST /chat). Todo o controle (fechar o chat,
bloquear alunos, apagar mensagens) fica no painel do professor, que roda no mesmo programa do
servidor: nao existe rota de rede para isso, entao nenhum aluno consegue se desbloquear.
As mensagens ficam so na memoria: desligou o servidor, o chat some.
"""

import threading
import time
import unicodedata
from collections import deque
from datetime import datetime

TAMANHO_MAXIMO = 200          # caracteres por mensagem
INTERVALO_MINIMO = 1.5        # segundos entre duas mensagens do mesmo aluno (contra spam)
GUARDAR = 300                 # ultimas mensagens guardadas


class Proibido(Exception):
    """O aluno nao pode mandar mensagem agora (o servidor responde 403)."""


def limpar_texto(texto):
    """Tira caracteres de controle, junta espacos repetidos e corta no tamanho maximo."""
    if not isinstance(texto, str):
        return ""
    texto = "".join(c for c in texto if unicodedata.category(c)[0] != "C" or c == " ")
    return " ".join(texto.split())[:TAMANHO_MAXIMO]


class Chat:
    def __init__(self):
        self._trava = threading.Lock()
        self.mensagens = deque(maxlen=GUARDAR)
        self.proximo_id = 1
        self.versao = 1              # muda quando o professor apaga algo: os apps redesenham tudo
        self.liberado = True
        self.bloqueados = {}         # id do aluno -> nome
        self._ultima_de = {}         # id do aluno -> horario da ultima mensagem

    def _adicionar(self, autor, id_autor, texto, tipo):
        mensagem = {"id": self.proximo_id, "hora": datetime.now().strftime("%H:%M"), "autor": autor,
                    "id_autor": id_autor, "texto": texto, "tipo": tipo}
        self.proximo_id += 1
        self.mensagens.append(mensagem)
        return mensagem

    # ---------------- o que os alunos podem fazer ----------------

    def enviar(self, jogador, texto):
        """jogador = {"id", "nome"} (vem da sala)."""
        texto = limpar_texto(texto)
        if not texto:
            raise Proibido("Mensagem vazia.")
        with self._trava:
            if not self.liberado:
                raise Proibido("O chat está fechado pelo professor.")
            if jogador["id"] in self.bloqueados:
                raise Proibido("Você está bloqueado no chat pelo professor.")
            agora = time.time()
            if agora - self._ultima_de.get(jogador["id"], 0) < INTERVALO_MINIMO:
                raise Proibido("Calma! Espere um pouquinho antes de mandar outra mensagem.")
            self._ultima_de[jogador["id"]] = agora
            return self._publica(self._adicionar(jogador["nome"], jogador["id"], texto, "aluno"), jogador["id"])

    def ler(self, id_jogador, depois=0, versao=None):
        """As mensagens com id maior que 'depois'. Se a versao mudou (o professor apagou algo), todas."""
        with self._trava:
            todas = versao != self.versao
            mensagens = [self._publica(m, id_jogador) for m in self.mensagens if todas or m["id"] > depois]
            return {"versao": self.versao, "todas": todas, "mensagens": mensagens,
                    "liberado": self.liberado, "bloqueado": id_jogador in self.bloqueados}

    def resumo(self, id_jogador):
        """Para o menu do app mostrar quantas mensagens novas existem."""
        with self._trava:
            return {"ultimo_id": self.proximo_id - 1, "liberado": self.liberado,
                    "bloqueado": id_jogador in self.bloqueados}

    @staticmethod
    def _publica(mensagem, id_leitor):
        """O app nao recebe o codigo dos outros alunos: so sabe se a mensagem e dele ("minha")."""
        dados = {chave: mensagem[chave] for chave in ("id", "hora", "autor", "texto", "tipo")}
        dados["minha"] = mensagem["id_autor"] == id_leitor
        return dados

    # ---------------- o que so o professor faz (pelo painel) ----------------

    def mensagem_do_professor(self, texto):
        texto = limpar_texto(texto)
        if texto:
            with self._trava:
                self._adicionar("Professor", "", texto, "professor")

    def liberar(self, ligado):
        with self._trava:
            if self.liberado != ligado:
                self.liberado = ligado
                aviso = "O professor abriu o chat." if ligado else "O professor fechou o chat."
                self._adicionar("Sistema", "", aviso, "sistema")

    def bloquear(self, id_jogador, nome):
        with self._trava:
            self.bloqueados[id_jogador] = nome

    def desbloquear(self, id_jogador):
        with self._trava:
            self.bloqueados.pop(id_jogador, None)

    def apagar(self, id_mensagem):
        with self._trava:
            antes = len(self.mensagens)
            self.mensagens = deque((m for m in self.mensagens if m["id"] != id_mensagem), maxlen=GUARDAR)
            if len(self.mensagens) != antes:
                self.versao += 1

    def limpar(self):
        with self._trava:
            self.mensagens.clear()
            self.versao += 1

    def instantaneo(self):
        with self._trava:
            return {"mensagens": [dict(m) for m in self.mensagens], "liberado": self.liberado,
                    "bloqueados": dict(self.bloqueados), "versao": self.versao, "ultimo_id": self.proximo_id - 1}
