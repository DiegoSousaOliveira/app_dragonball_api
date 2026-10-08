"""
A sala: quem esta conectado, os desafios entre alunos e os duelos (batalha e quiz).

Como os apps conversam com a sala (tudo HTTP, o app pergunta de 1,5 em 1,5 s):
  1. Ana pede GET /turma/sala -> ve quem esta online e "livre"
  2. Ana manda POST /turma/desafiar {"para": id_do_Beto, "tipo": "batalha", "personagem": 1}
  3. Beto, no proximo GET /turma/sala, ve o desafio em "recebidos" e responde (aceita ou recusa)
  4. Aceito: o servidor cria a partida; os dois veem "partida": id e abrem a tela do duelo
  5. Na batalha, o SERVIDOR joga as rodadas (uma a cada 1,3 s): os dois veem a mesma luta.
     No quiz, os dois respondem as MESMAS perguntas e mandam o progresso.
"""

import random
import secrets
import threading
import time

from core import batalha, quiz
from servidor.placar import DadoInvalido

ONLINE_ATE = 12              # segundos sem perguntar nada -> fora da sala
VALIDADE_DO_DESAFIO = 30     # segundos para responder
DESISTENCIA = 20             # segundos sumido durante um duelo -> perde por W.O.
MOSTRAR_RESULTADO = 15       # segundos que um desafio respondido continua aparecendo para quem desafiou


def _novo_id():
    return secrets.token_hex(5)


class PartidaBatalha:
    tipo = "batalha"
    INTERVALO = 1.3          # segundos entre as rodadas
    CONTAGEM = 4             # segundos de "a luta comeca em..."

    def __init__(self, id_partida, jogador_a, jogador_b, personagem_a, personagem_b, metrica):
        self.id = id_partida
        self.jogadores = {"a": jogador_a, "b": jogador_b}
        self.personagens = {"a": personagem_a, "b": personagem_b}
        self.metrica = metrica
        self.rng = random.Random()
        self.luta = batalha.iniciar_luta(personagem_a, personagem_b, metrica, self.rng)
        self.comeca = time.time() + self.CONTAGEM
        self.rodadas_feitas = 0
        self.narracao = []
        self.transformado = {"a": None, "b": None}
        self.fim = None              # {"vencedor": "a"|"b", "motivo": "..."}

    def lado_de(self, id_jogador):
        for lado, jogador in self.jogadores.items():
            if jogador["id"] == id_jogador:
                return lado
        raise DadoInvalido("Voce nao esta nesta partida.")

    def avancar(self, agora):
        """Joga as rodadas que ja deveriam ter acontecido ate 'agora'."""
        if self.fim or agora < self.comeca:
            return
        devidas = int((agora - self.comeca) // self.INTERVALO) + 1
        while self.rodadas_feitas < devidas and not batalha.luta_acabou(self.luta):
            self.narracao.append(batalha.jogar_rodada(self.luta, self.rng))
            self.rodadas_feitas += 1
        if batalha.luta_acabou(self.luta):
            vencedor = "a" if self.luta["a"]["hp"] >= self.luta["b"]["hp"] else "b"
            self.fim = {"vencedor": vencedor, "motivo": "nocaute"}

    def transformar(self, id_jogador):
        lado = self.lado_de(id_jogador)
        lutador = self.luta[lado]
        if self.fim or not batalha.pode_transformar(lutador):
            raise DadoInvalido("Nao da para transformar agora.")
        transformacao = batalha.transformar(lutador)
        self.transformado[lado] = {"name": transformacao["name"], "image": transformacao.get("image")}
        self.narracao.append(f"⚡ {self.jogadores[lado]['nome']}: {lutador['nome']} se transformou em "
                             f"{transformacao['name']}! Forca x{batalha.BONUS_TRANSFORMACAO} por "
                             f"{batalha.RODADAS_TRANSFORMADO} rodadas!")

    def encerrar(self, vencedor, motivo):
        if not self.fim:
            self.fim = {"vencedor": vencedor, "motivo": motivo}

    def estado(self, agora):
        return {
            "id": self.id, "tipo": self.tipo, "jogadores": self.jogadores,
            "personagens": self.personagens, "metrica": self.metrica,
            "comeca_em": max(0.0, round(self.comeca - agora, 1)),
            "hp": {"a": self.luta["a"]["hp"], "b": self.luta["b"]["hp"]},
            "narracao": self.narracao, "transformado": self.transformado,
            "pode_transformar": {lado: batalha.pode_transformar(self.luta[lado]) for lado in ("a", "b")},
            "fim": self.fim,
        }

    def descricao(self):
        return f"{self.personagens['a']['name']} x {self.personagens['b']['name']}"


class PartidaQuiz:
    tipo = "quiz"
    CONTAGEM = 3

    def __init__(self, id_partida, jogador_a, jogador_b, personagens, quantas):
        self.id = id_partida
        self.jogadores = {"a": jogador_a, "b": jogador_b}
        sorteadas = quiz.montar_rodadas(personagens, quantas, random.Random())
        campos = ("id", "name", "race", "affiliation", "image")
        self.rodadas = [{"resposta": r["resposta"]["id"],
                         "opcoes": [{c: p.get(c) for c in campos} for p in r["opcoes"]]} for r in sorteadas]
        self.comeca = time.time() + self.CONTAGEM
        self.progresso = {lado: {"rodada": 0, "pontos": 0, "terminou": False, "tempo": None} for lado in "ab"}
        self.fim = None

    lado_de = PartidaBatalha.lado_de
    encerrar = PartidaBatalha.encerrar

    def registrar_progresso(self, id_jogador, rodada, pontos, terminou):
        lado = self.lado_de(id_jogador)
        maximo = len(self.rodadas)
        if not isinstance(rodada, int) or not 0 <= rodada <= maximo:
            raise DadoInvalido("Rodada invalida.")
        if not isinstance(pontos, int) or not 0 <= pontos <= maximo * quiz.PREMIO_INICIAL:
            raise DadoInvalido("Pontos invalidos.")
        meu = self.progresso[lado]
        if meu["terminou"] or self.fim:
            return
        meu.update(rodada=rodada, pontos=pontos)
        if terminou:
            meu["terminou"] = True
            meu["tempo"] = round(time.time() - self.comeca, 1)

    def avancar(self, agora):
        a, b = self.progresso["a"], self.progresso["b"]
        if self.fim or not (a["terminou"] and b["terminou"]):
            return
        if a["pontos"] != b["pontos"]:
            vencedor = "a" if a["pontos"] > b["pontos"] else "b"
            self.fim = {"vencedor": vencedor, "motivo": "pontos"}
        else:                                       # empate: ganha quem terminou mais rapido
            vencedor = "a" if a["tempo"] <= b["tempo"] else "b"
            self.fim = {"vencedor": vencedor, "motivo": "tempo"}

    def estado(self, agora):
        return {"id": self.id, "tipo": self.tipo, "jogadores": self.jogadores, "rodadas": self.rodadas,
                "comeca_em": max(0.0, round(self.comeca - agora, 1)), "progresso": self.progresso,
                "fim": self.fim}

    def descricao(self):
        return f"quiz de {len(self.rodadas)} rodadas"


class Sala:
    def __init__(self, espelho, placar):
        self.espelho = espelho
        self.placar = placar
        self._trava = threading.RLock()
        self.jogadores = {}          # id -> {"id", "nome", "ip", "visto"}
        self.desafios = {}           # id -> {...}
        self.partidas = {}           # id -> PartidaBatalha | PartidaQuiz
        self._registradas = set()    # partidas ja anotadas no placar

    # ---------------- quem esta na sala ----------------

    def entrar(self, nome, ip):
        nome = (nome or "").strip()[:30] or "Aluno"
        with self._trava:
            for jogador in self.jogadores.values():          # mesmo aluno voltando (reabriu o app)
                if jogador["nome"] == nome and jogador["ip"] == ip:
                    jogador["visto"] = time.time()
                    return jogador
            jogador = {"id": _novo_id(), "nome": nome, "ip": ip, "visto": time.time()}
            self.jogadores[jogador["id"]] = jogador
            return jogador

    def jogador(self, id_jogador):
        """{"id", "nome"} de um aluno que entrou na sala (ou DadoInvalido)."""
        with self._trava:
            dados = self._jogador(id_jogador)
            dados["visto"] = time.time()
            return {"id": dados["id"], "nome": dados["nome"]}

    def _jogador(self, id_jogador):
        jogador = self.jogadores.get(id_jogador or "")
        if jogador is None:
            raise DadoInvalido("Jogador desconhecido: entre na sala de novo.")
        return jogador

    def _online(self, jogador, agora):
        return agora - jogador["visto"] <= ONLINE_ATE

    def _partida_ativa(self, id_jogador):
        for partida in self.partidas.values():
            if not partida.fim and any(j["id"] == id_jogador for j in partida.jogadores.values()):
                return partida
        return None

    def _estado_de(self, jogador, agora):
        if not self._online(jogador, agora):
            return "ausente"
        partida = self._partida_ativa(jogador["id"])
        if partida is None:
            return "livre"
        return "em_batalha" if partida.tipo == "batalha" else "em_quiz"

    # ---------------- manutencao (chamada a cada pedido) ----------------

    def _arrumar(self, agora):
        for desafio in self.desafios.values():
            if desafio["estado"] == "pendente" and agora - desafio["criado"] > VALIDADE_DO_DESAFIO:
                desafio.update(estado="expirado", respondido=agora)
        for partida in self.partidas.values():
            partida.avancar(agora)
            if not partida.fim:
                for lado, jogador in partida.jogadores.items():
                    sumido = agora - self.jogadores[jogador["id"]]["visto"] > DESISTENCIA
                    if sumido:
                        partida.encerrar("b" if lado == "a" else "a", "desistencia")
            if partida.fim and partida.id not in self._registradas:
                self._registradas.add(partida.id)
                vencedor = partida.jogadores[partida.fim["vencedor"]]["nome"]
                perdedor = partida.jogadores["b" if partida.fim["vencedor"] == "a" else "a"]["nome"]
                self.placar.registrar_duelo(partida.tipo, vencedor, perdedor, partida.descricao(),
                                            wo=partida.fim["motivo"] == "desistencia")

    # ---------------- o que cada aluno ve ----------------

    def visao(self, id_jogador):
        agora = time.time()
        with self._trava:
            eu = self._jogador(id_jogador)
            eu["visto"] = agora
            self._arrumar(agora)
            jogadores = [{"id": j["id"], "nome": j["nome"], "estado": self._estado_de(j, agora),
                          "voce": j["id"] == id_jogador}
                         for j in self.jogadores.values() if self._online(j, agora)]
            jogadores.sort(key=lambda j: (not j["voce"], j["nome"].lower()))
            recebidos = [self._publico(d) for d in self.desafios.values()
                         if d["para"] == id_jogador and d["estado"] == "pendente"]
            enviados = [d for d in self.desafios.values() if d["de"] == id_jogador
                        and (d["estado"] == "pendente" or agora - d.get("respondido", agora) < MOSTRAR_RESULTADO)]
            enviado = self._publico(max(enviados, key=lambda d: d["criado"])) if enviados else None
            partida = self._partida_ativa(id_jogador)
            return {"voce": {"id": eu["id"], "nome": eu["nome"]}, "jogadores": jogadores,
                    "recebidos": recebidos, "enviado": enviado,
                    "partida": {"id": partida.id, "tipo": partida.tipo} if partida else None}

    def _publico(self, desafio):
        dados = {chave: desafio[chave] for chave in ("id", "tipo", "estado", "opcoes", "partida")}
        dados["de"] = {"id": desafio["de"], "nome": self.jogadores[desafio["de"]]["nome"]}
        dados["para"] = {"id": desafio["para"], "nome": self.jogadores[desafio["para"]]["nome"]}
        dados["expira_em"] = max(0, int(VALIDADE_DO_DESAFIO - (time.time() - desafio["criado"])))
        return dados

    def visao_do_professor(self):
        agora = time.time()
        with self._trava:
            self._arrumar(agora)
            alunos = [{"id": j["id"], "nome": j["nome"], "ip": j["ip"], "estado": self._estado_de(j, agora),
                       "visto_ha": int(agora - j["visto"])} for j in self.jogadores.values()]
            duelos = [{"tipo": p.tipo, "a": p.jogadores["a"]["nome"], "b": p.jogadores["b"]["nome"],
                       "descricao": p.descricao()} for p in self.partidas.values() if not p.fim]
            return {"alunos": alunos, "duelos": duelos}

    # ---------------- desafios ----------------

    def _personagem(self, id_personagem):
        if not isinstance(id_personagem, int):
            raise DadoInvalido("Escolha um personagem.")
        detalhe = self.espelho.detalhe_personagem(id_personagem)
        if detalhe is None:
            raise DadoInvalido("Personagem desconhecido.")
        return detalhe

    def desafiar(self, id_jogador, dados):
        agora = time.time()
        with self._trava:
            self._arrumar(agora)
            eu = self._jogador(id_jogador)
            eu["visto"] = agora
            outro = self._jogador(dados.get("para"))
            tipo = dados.get("tipo")
            if tipo not in ("batalha", "quiz"):
                raise DadoInvalido("Tipo de desafio invalido.")
            if outro["id"] == eu["id"]:
                raise DadoInvalido("Voce nao pode desafiar voce mesmo.")
            if self._estado_de(eu, agora) != "livre":
                raise DadoInvalido("Voce ja esta num duelo.")
            if self._estado_de(outro, agora) != "livre":
                raise DadoInvalido(f"{outro['nome']} nao esta livre agora.")
            if tipo == "batalha":
                personagem = self._personagem(dados.get("personagem"))
                opcoes = {"personagem": {"id": personagem["id"], "name": personagem["name"]},
                          "metrica": "ki" if dados.get("metrica") == "ki" else "maxKi"}
            else:
                rodadas = dados.get("rodadas")
                opcoes = {"rodadas": rodadas if rodadas in (3, 5, 10) else 5}
            for antigo in self.desafios.values():                 # so um desafio pendente por vez
                if antigo["de"] == eu["id"] and antigo["estado"] == "pendente":
                    antigo.update(estado="cancelado", respondido=agora)
            desafio = {"id": _novo_id(), "de": eu["id"], "para": outro["id"], "tipo": tipo, "opcoes": opcoes,
                       "estado": "pendente", "criado": agora, "partida": None}
            self.desafios[desafio["id"]] = desafio
            return self._publico(desafio)

    def _desafio(self, id_desafio):
        desafio = self.desafios.get(id_desafio or "")
        if desafio is None:
            raise DadoInvalido("Desafio desconhecido.")
        return desafio

    def cancelar(self, id_jogador, id_desafio):
        with self._trava:
            desafio = self._desafio(id_desafio)
            if desafio["de"] != id_jogador:
                raise DadoInvalido("So quem desafiou pode cancelar.")
            if desafio["estado"] == "pendente":
                desafio.update(estado="cancelado", respondido=time.time())
            return self._publico(desafio)

    def responder(self, id_jogador, dados):
        agora = time.time()
        with self._trava:
            self._arrumar(agora)
            desafio = self._desafio(dados.get("desafio"))
            if desafio["para"] != id_jogador:
                raise DadoInvalido("Este desafio nao e para voce.")
            if desafio["estado"] != "pendente":
                raise DadoInvalido(f"Este desafio ja foi {desafio['estado']}.")
            if not dados.get("aceitar"):
                desafio.update(estado="recusado", respondido=agora)
                return self._publico(desafio)
            de, para = self.jogadores[desafio["de"]], self.jogadores[desafio["para"]]
            if self._estado_de(de, agora) != "livre":
                desafio.update(estado="expirado", respondido=agora)
                raise DadoInvalido(f"{de['nome']} nao esta mais livre.")
            jogador_a = {"id": de["id"], "nome": de["nome"]}
            jogador_b = {"id": para["id"], "nome": para["nome"]}
            if desafio["tipo"] == "batalha":
                partida = PartidaBatalha(_novo_id(), jogador_a, jogador_b,
                                         self._personagem(desafio["opcoes"]["personagem"]["id"]),
                                         self._personagem(dados.get("personagem")), desafio["opcoes"]["metrica"])
            else:
                partida = PartidaQuiz(_novo_id(), jogador_a, jogador_b, self.espelho.personagens(),
                                      desafio["opcoes"]["rodadas"])
            self.partidas[partida.id] = partida
            desafio.update(estado="aceito", respondido=agora, partida=partida.id)
            return self._publico(desafio)

    # ---------------- durante o duelo ----------------

    def _partida(self, id_partida):
        partida = self.partidas.get(id_partida or "")
        if partida is None:
            raise DadoInvalido("Partida desconhecida.")
        return partida

    def estado_da_partida(self, id_jogador, id_partida):
        agora = time.time()
        with self._trava:
            self._jogador(id_jogador)["visto"] = agora
            self._arrumar(agora)
            partida = self._partida(id_partida)
            estado = partida.estado(agora)
            estado["seu_lado"] = partida.lado_de(id_jogador)
            return estado

    def transformar(self, id_jogador, id_partida):
        with self._trava:
            partida = self._partida(id_partida)
            if partida.tipo != "batalha":
                raise DadoInvalido("So existe transformacao na batalha.")
            partida.avancar(time.time())
            partida.transformar(id_jogador)
            return {"ok": True}

    def progresso(self, id_jogador, id_partida, dados):
        with self._trava:
            partida = self._partida(id_partida)
            if partida.tipo != "quiz":
                raise DadoInvalido("Progresso so existe no quiz.")
            partida.registrar_progresso(id_jogador, dados.get("rodada"), dados.get("pontos"),
                                        bool(dados.get("terminou")))
            partida.avancar(time.time())
            return {"ok": True}

    def desistir(self, id_jogador, id_partida):
        with self._trava:
            partida = self._partida(id_partida)
            lado = partida.lado_de(id_jogador)
            partida.encerrar("b" if lado == "a" else "a", "desistencia")
            self._arrumar(time.time())
            return {"ok": True}
