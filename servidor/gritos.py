"""
O grito de guerra de cada aluno: uma frase (ate 40 letras) + um audio. A personalizacao e livre (sem aprovacao);
o professor so pode BLOQUEAR pelo painel (aba 📣 Gritos): quem esta bloqueado volta na hora ao grito padrao.

  - Audio personalizado: o aluno manda uma URL; o SERVIDOR baixa (servidor/baixar_audio.py, com as protecoes contra
    SSRF), guarda em %LOCALAPPDATA%\\DragonBallDex\\gritos\\<hash>.<formato> e entrega em GET /gritos/<hash>.
    O nome do arquivo vem do CONTEUDO (hash), nunca do codigo X-Jogador de ninguem.
  - Eventos de som: quando alguem conquista um planeta, acha a esfera 6 ou invoca o dragao, nasce um evento com a
    frase e o audio dele; os apps descobrem pelo campo "novidades" do /turma/sala e tocam o som.
  - E um objeto (nao um global): o modo demonstracao tem os seus proprios gritos, separados da turma.
"""

import hashlib
import re
import threading
import time
from collections import deque

from core.armazenamento import PASTA_USUARIO
from core.grito_padrao import ID_DO_PADRAO
from servidor import baixar_audio
from servidor.chat import limpar_texto

# Quem ouve os gritos dos eventos. "todos": todos os apps da sala. "envolvidos": so quem participou (quem conquistou
# e quem perdeu o planeta, por exemplo). Com 15 PCs, "todos" vira um coro: troque aqui se ficar barulhento demais.
QUEM_OUVE = "todos"
FRASE_PADRAO = "Pela honra da Terra!"
TAMANHO_DA_FRASE = 40
INTERVALO_DE_TROCA = 10            # segundos entre duas trocas do mesmo aluno
PASTA = PASTA_USUARIO / "gritos"
NOME_DO_AUDIO = re.compile(r"^[0-9a-f]{16}\.(mp3|wav|ogg)$")
TIPOS = {"mp3": "audio/mpeg", "wav": "audio/wav", "ogg": "audio/ogg"}


class ErroDoGrito(Exception):
    status = 400


class Devagar(ErroDoGrito):
    status = 429


class GritoBloqueado(ErroDoGrito):
    status = 403


class Gritos:
    def __init__(self, pasta=None, baixar=None, relogio=time.time):
        self.pasta = pasta or PASTA
        self.baixar = baixar or baixar_audio.baixar
        self.relogio = relogio
        self._trava = threading.Lock()
        self.alunos = {}               # id do jogador -> {"nome", "frase", "audio", "bloqueado", "trocou_em"}
        self.versao = 1                # muda a cada troca/bloqueio: os apps pre-carregam os audios de novo
        self._eventos = deque(maxlen=100)
        self._proximo_evento = 1

    # ---------------- ajudantes ----------------

    def _aluno(self, id_jogador, nome=None):
        dados = self.alunos.setdefault(id_jogador, {"nome": nome or "Aluno", "frase": None, "audio": None,
                                                    "bloqueado": False, "trocou_em": None})
        if nome:
            dados["nome"] = nome
        return dados

    @staticmethod
    def _valendo(dados):
        """O grito que vale agora: o personalizado, ou o padrao (sem grito ou bloqueado pelo professor)."""
        if dados is None or dados["bloqueado"]:
            return {"frase": FRASE_PADRAO, "audio": ID_DO_PADRAO, "padrao": True}
        return {"frase": dados["frase"] or FRASE_PADRAO, "audio": dados["audio"] or ID_DO_PADRAO,
                "padrao": not dados["frase"] and not dados["audio"]}

    def _meu(self, dados, agora):
        valendo = self._valendo(dados)
        falta = 0
        if dados["trocou_em"] is not None and agora - dados["trocou_em"] < INTERVALO_DE_TROCA:
            falta = int(INTERVALO_DE_TROCA - (agora - dados["trocou_em"])) + 1
        return dict(valendo, bloqueado=dados["bloqueado"], troca_em=falta,
                    frase_personalizada=dados["frase"] or "", audio_personalizado=bool(dados["audio"]))

    # ---------------- o que o aluno faz ----------------

    def meu(self, id_jogador, nome):
        with self._trava:
            return self._meu(self._aluno(id_jogador, nome), self.relogio())

    def trocar(self, id_jogador, nome, frase=None, url=None, padrao=False):
        """Troca a frase e/ou o audio (URL baixada pelo servidor). padrao=True volta ao grito padrao."""
        agora = self.relogio()
        with self._trava:
            dados = self._aluno(id_jogador, nome)
            if dados["bloqueado"]:
                raise GritoBloqueado("O professor bloqueou o seu grito personalizado.")
            if dados["trocou_em"] is not None and agora - dados["trocou_em"] < INTERVALO_DE_TROCA:
                falta = int(INTERVALO_DE_TROCA - (agora - dados["trocou_em"])) + 1
                raise Devagar(f"Calma! Você pode trocar o grito de novo em {falta} s.")
            anterior, dados["trocou_em"] = dados["trocou_em"], agora     # conta a tentativa (mesmo se o download falhar)
        nova_frase, novo_audio = None, None
        if not padrao:
            if frase is not None:
                nova_frase = limpar_texto(frase)[:TAMANHO_DA_FRASE].strip()
            if url:                                        # baixar demora: FORA da trava
                try:
                    conteudo, formato = self.baixar(url)
                except baixar_audio.ErroDoAudio as erro:
                    if erro.status == 400:                 # recusado so de olhar o endereco (sem usar a rede):
                        with self._trava:                  # nao gasta a vez do aluno
                            if dados["trocou_em"] == agora:
                                dados["trocou_em"] = anterior
                    raise
                novo_audio = f"{hashlib.sha1(conteudo).hexdigest()[:16]}.{formato}"
                self.pasta.mkdir(parents=True, exist_ok=True)
                arquivo = self.pasta / novo_audio
                if not arquivo.exists():
                    arquivo.write_bytes(conteudo)
        with self._trava:
            if dados["bloqueado"]:                         # o professor bloqueou durante o download
                raise GritoBloqueado("O professor bloqueou o seu grito personalizado.")
            if padrao:
                dados["frase"] = dados["audio"] = None
            else:
                if frase is not None:
                    dados["frase"] = nova_frase or None
                if novo_audio:
                    dados["audio"] = novo_audio
            self.versao += 1
            return self._meu(dados, self.relogio())

    # ---------------- eventos de som ----------------

    def anunciar(self, id_jogador, nome, tipo, texto, envolvidos=None):
        """Alguem fez algo grandioso: os apps vao tocar o grito DELE. (O texto e montado pelo programa e nunca
        contem a palavra magica da esfera 6; a frase e a que o aluno escolheu.)"""
        with self._trava:
            valendo = self._valendo(self.alunos.get(id_jogador))
            self._eventos.append({"id": self._proximo_evento, "tipo": tipo, "nome": nome, "texto": texto,
                                  "frase": valendo["frase"], "audio": valendo["audio"],
                                  "para": set(envolvidos) if envolvidos else None})
            self._proximo_evento += 1

    @property
    def ultimo_evento(self):
        return self._proximo_evento - 1

    def estado_para(self, id_jogador, depois=0):
        """Os eventos novos que ESTE aluno deve ouvir + a lista de audios para pre-carregar."""
        with self._trava:
            eventos = [{chave: e[chave] for chave in ("id", "tipo", "nome", "texto", "frase", "audio")}
                       for e in self._eventos if e["id"] > depois
                       and (QUEM_OUVE == "todos" or e["para"] is None or id_jogador in e["para"])]
            audios = sorted({self._valendo(d)["audio"] for d in self.alunos.values()} | {ID_DO_PADRAO})
            return {"eventos": eventos, "ultimo": self._proximo_evento - 1, "versao": self.versao, "audios": audios}

    def grito_de(self, id_jogador):
        with self._trava:
            return self._valendo(self.alunos.get(id_jogador))

    def arquivo(self, nome):
        """O arquivo de um audio personalizado (nome = hash.formato; nada de "../")."""
        if not NOME_DO_AUDIO.match(nome or ""):
            return None
        caminho = self.pasta / nome
        return caminho if caminho.is_file() else None

    # ---------------- moderacao (so pelo painel) ----------------

    def bloquear(self, ids, bloqueado=True):
        with self._trava:
            for id_jogador in ids:
                self._aluno(id_jogador)["bloqueado"] = bloqueado
            self.versao += 1

    def desbloquear(self, ids):
        self.bloquear(ids, bloqueado=False)

    def instantaneo(self):
        with self._trava:
            return {id_jogador: dict(self._valendo(d), nome=d["nome"], bloqueado=d["bloqueado"],
                                     frase_personalizada=d["frase"] or "", audio_personalizado=bool(d["audio"]))
                    for id_jogador, d in self.alunos.items()}
