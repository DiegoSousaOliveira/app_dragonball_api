"""
Conquista de Territorios: um torneio num mapa da galaxia. Cada aluno protege planetas com um Guardiao (um
personagem) e invade os planetas dos colegas. Quem decide as lutas e o SERVIDOR (o motor de batalha de sempre):
o atacante so assiste, e o dono do planeta nem precisa estar online.

  - Placar SEPARADO do placar da turma (as lutas daqui nunca entram na Sala nem nos 3/1 pontos dos duelos).
  - Cada luta e uma PartidaBatalha (a mesma dos duelos) com id "cq-...": o app assiste pela rota de sempre,
    GET /turma/partida/<id> (servidor/rotas_conquista.py).
  - Tudo fica na memoria, protegido por UMA trava: dois alunos invadindo o mesmo planeta ao mesmo tempo -> so um
    passa (o outro recebe 409).
  - E um objeto (nao um global): o modo demonstracao cria a sua propria Conquista, separada da turma.
"""

import csv
import random
import secrets
import threading
import time
from collections import deque
from contextlib import contextmanager
from datetime import datetime

from core import batalha
from core.armazenamento import PASTA_USUARIO
from core.poder import forca_de_batalha, parse_ki
from servidor.placar import DadoInvalido
from servidor.sala import PartidaBatalha

PASTA_DOS_RESULTADOS = PASTA_USUARIO / "conquistas"
TETO_DE_FORCA = 27.0           # o Grand Priest tem 103 e venceria sempre: aqui ninguem passa de 27 (~Zeno)
NEUTROS_PADRAO = 3
ESCUDO_PADRAO = 45             # segundos de protecao depois que um planeta muda de dono
ESPERA_PADRAO = 20             # segundos entre duas invasoes do mesmo aluno
TROCA_DE_GUARDIAO = 60         # segundos entre duas trocas de guardiao
METRICAS = {"maxKi": "Total KI", "ki": "Base KI"}
TRANSFORMA_ABAIXO_DE = 50      # o guardiao se transforma sozinho quando a vida cai abaixo disso

# Lugares do mapa (x e y de 0 a 1), do centro para fora: poucos territorios ficam juntinhos no meio.
LUGARES = [(0.50, 0.50), (0.33, 0.40), (0.67, 0.40), (0.40, 0.70), (0.60, 0.70), (0.50, 0.20),
           (0.17, 0.58), (0.83, 0.58), (0.22, 0.24), (0.78, 0.24), (0.24, 0.84), (0.76, 0.84),
           (0.06, 0.36), (0.94, 0.36), (0.50, 0.90), (0.36, 0.10), (0.64, 0.10), (0.06, 0.78),
           (0.94, 0.78), (0.10, 0.12)]

MENSAGENS_PARADA = {
    "aguardando": "A Conquista ainda não começou 🗺",
    "pausada": "A Conquista está pausada pelo professor ⏸",
    "encerrada": "A Conquista terminou! 🏁",
}


# ---------------- erros (cada um ja diz o status HTTP) ----------------

class ErroDaConquista(Exception):
    status = 400


class ConquistaParada(ErroDaConquista):
    status = 409


class Ocupado(ErroDaConquista):
    """Alvo em batalha, com escudo, ou o atacante ja esta numa invasao."""
    status = 409


class Proibido(ErroDaConquista):
    status = 403


class NaoExiste(ErroDaConquista):
    status = 404


class Devagar(ErroDaConquista):
    status = 429


def hora(instante):
    return datetime.fromtimestamp(instante).strftime("%H:%M")


class Participante:
    def __init__(self, id_jogador, nome, cor, agora):
        self.id = id_jogador
        self.nome = nome or "Aluno"
        self.cor = cor                       # numero da cor no mapa (cada aluno tem a sua)
        self.guardiao = None                 # id do personagem
        self.guardiao_escolhido = False
        self.trocou_guardiao_em = None
        self.ultima_invasao = None
        self.conquistas = 0
        self.defesas = 0
        self.invasoes = 0
        self.chegou_em = agora               # quando chegou ao numero de territorios que tem agora


class Territorio:
    def __init__(self, planeta, lugar):
        self.id = str(planeta["id"])
        self.nome = planeta["name"].strip()
        self.x, self.y = lugar
        self.dono = None                     # id do participante (None = neutro)
        self.guardiao_neutro = None          # id do personagem que defende o neutro
        self.escudo_ate = 0.0
        self.em_batalha = None               # id da partida


class Invasao:
    def __init__(self, partida, territorio, atacante, dono, guardiao_nome):
        self.partida = partida
        self.territorio = territorio
        self.atacante = atacante
        self.dono = dono                     # id do dono no comeco da luta (None = neutro)
        self.guardiao_nome = guardiao_nome
        self.resolvida = False


class Conquista:
    """Estados: aguardando -> ativa <-> pausada -> encerrada. "Nova conquista" volta para aguardando.

    fonte: de onde vem os personagens e planetas (o Espelho do servidor: .personagens(), .planetas(),
    .detalhe_personagem(id)). avisar(texto): aviso do professor no chat. relogio e rng: injetaveis nos testes."""

    def __init__(self, fonte, avisar=None, relogio=time.time, rng=None):
        self.fonte = fonte
        self.avisar = avisar or (lambda texto: None)
        self.relogio = relogio
        self.rng = rng or random.Random()
        self._trava = threading.Lock()
        self._eventos = deque(maxlen=400)
        self._proximo_evento = 1
        self._avisos = []
        self.ao_conquistar = None            # gancho: chamado (fora da trava) quando um planeta muda de dono
        self._ganchos = []
        self._zerar()

    def _zerar(self):
        self.estado = "aguardando"
        self.participantes = {}              # id do jogador -> Participante
        self.territorios = {}                # id do planeta -> Territorio
        self.invasoes = {}                   # id da partida -> Invasao
        self.metrica = "maxKi"
        self.escudo = ESCUDO_PADRAO
        self.espera = ESPERA_PADRAO
        self.duracao = None
        self.fim_previsto = None
        self.pausada_em = None
        self.resultado_salvo = None

    @contextmanager
    def _mexendo(self):
        """Toda operacao: trava, poe o relogio em dia (lutas, fim do tempo) e, depois de soltar a trava,
        entrega os avisos do chat e os ganchos (assim ninguem fica esperando a Conquista)."""
        self._trava.acquire()
        try:
            agora = self.relogio()
            self._atualizar(agora)
            yield agora
        finally:
            avisos, self._avisos = self._avisos, []
            ganchos, self._ganchos = self._ganchos, []
            self._trava.release()
            for texto in avisos:
                try:
                    self.avisar(texto)
                except Exception:
                    pass
            for funcao, argumentos in ganchos:
                try:
                    funcao(*argumentos)
                except Exception:
                    pass

    # ---------------- eventos (feed do app e do telao) ----------------

    def _evento(self, tipo, agora, texto, **extras):
        self._eventos.append(dict(extras, id=self._proximo_evento, tipo=tipo, hora=hora(agora), texto=texto))
        self._proximo_evento += 1

    @staticmethod
    def _publico(evento):
        """O que vai para os apps (sem o codigo X-Jogador de ninguem)."""
        return {chave: evento[chave] for chave in ("id", "tipo", "hora", "texto", "territorio", "cor")
                if chave in evento}

    def eventos_depois(self, id_evento):
        """Para o painel (com tudo)."""
        with self._trava:
            return [dict(e) for e in self._eventos if e["id"] > id_evento]

    # ---------------- personagens ----------------

    def _detalhe(self, id_personagem):
        if not isinstance(id_personagem, int) or isinstance(id_personagem, bool):
            raise ErroDaConquista("Escolha um lutador.")
        detalhe = self.fonte.detalhe_personagem(id_personagem)
        if detalhe is None:
            raise ErroDaConquista("Esse lutador não existe.")
        return detalhe

    def _forca(self, personagem):
        return forca_de_batalha(parse_ki(personagem.get(self.metrica)))

    def _sorteio_medio(self):
        """Um personagem de forca media (o terco do meio): guardiao dos territorios neutros."""
        lista = sorted(self.fonte.personagens(), key=self._forca)
        terco = len(lista) // 3
        return self.rng.choice(lista[terco:len(lista) - terco] or lista)["id"]

    def _nome_do_personagem(self, id_personagem):
        detalhe = self.fonte.detalhe_personagem(id_personagem) if id_personagem else None
        return detalhe["name"].strip() if detalhe else "?"

    # ---------------- participantes ----------------

    def _participante(self, id_jogador, nome, agora):
        participante = self.participantes.get(id_jogador)
        if participante is None:
            participante = Participante(id_jogador, nome, len(self.participantes), agora)
            participante.guardiao = self.rng.choice(self.fonte.personagens())["id"]   # sorteado ate ele escolher
            self.participantes[id_jogador] = participante
        elif nome:
            participante.nome = nome
        return participante

    def _territorios_de(self, id_jogador):
        return [t for t in self.territorios.values() if t.dono == id_jogador]

    def _mudou_a_contagem(self, id_jogador, agora):
        if id_jogador in self.participantes:
            self.participantes[id_jogador].chegou_em = agora

    def _classificacao(self):
        """Mais territorios -> mais conquistas -> mais defesas -> quem chegou antes aquele numero."""
        contagem = {}
        for territorio in self.territorios.values():
            if territorio.dono:
                contagem[territorio.dono] = contagem.get(territorio.dono, 0) + 1
        return sorted(self.participantes.values(),
                      key=lambda p: (-contagem.get(p.id, 0), -p.conquistas, -p.defesas, p.chegou_em, p.cor)), contagem

    # ---------------- relogio e lutas ----------------

    def _atualizar(self, agora):
        for invasao in list(self.invasoes.values()):
            if not invasao.resolvida:
                self._avancar(invasao, agora)
        if self.estado == "ativa" and self.fim_previsto is not None and agora >= self.fim_previsto:
            self._encerrar(agora, "tempo")

    def _avancar(self, invasao, agora):
        partida = invasao.partida
        partida.avancar(agora)
        guardiao = partida.luta["b"]
        if (not partida.fim and guardiao["hp"] < TRANSFORMA_ABAIXO_DE and batalha.pode_transformar(guardiao)
                and agora >= partida.comeca):
            try:
                partida.transformar(partida.jogadores["b"]["id"])    # o guardiao reage sozinho
            except DadoInvalido:
                pass
        if partida.fim:
            self._resolver(invasao, agora)

    def _resolver(self, invasao, agora):
        invasao.resolvida = True
        territorio = self.territorios[invasao.territorio]
        territorio.em_batalha = None
        atacante = self.participantes[invasao.atacante]
        dono = self.participantes.get(invasao.dono) if invasao.dono else None
        if invasao.partida.fim["vencedor"] == "a":
            territorio.dono = atacante.id
            territorio.escudo_ate = agora + self.escudo
            atacante.conquistas += 1
            self._mudou_a_contagem(atacante.id, agora)
            if dono:
                self._mudou_a_contagem(dono.id, agora)
                texto = f"🏴 {atacante.nome} conquistou {territorio.nome} de {dono.nome}!"
            else:
                texto = f"🏴 {atacante.nome} conquistou o território neutro {territorio.nome}!"
            self._evento("conquista", agora, texto, territorio=territorio.id, cor=atacante.cor, jogador=atacante.id)
            if self.ao_conquistar:
                self._ganchos.append((self.ao_conquistar, (atacante.id, atacante.nome, territorio.nome,
                                                           dono.id if dono else None)))
        else:
            if dono:
                dono.defesas += 1
                texto = f"🛡 {invasao.guardiao_nome}, guardião de {dono.nome}, defendeu {territorio.nome} " \
                        f"contra {atacante.nome}!"
            else:
                texto = f"🛡 O guardião de {territorio.nome} expulsou {atacante.nome}!"
            self._evento("defesa", agora, texto, territorio=territorio.id,
                         cor=dono.cor if dono else None)

    # ---------------- comandos do professor (painel) ----------------

    def iniciar(self, alunos=(), minutos=None, neutros=NEUTROS_PADRAO, escudo=ESCUDO_PADRAO, espera=ESPERA_PADRAO,
                metrica="maxKi"):
        """alunos = [(id_do_jogador, nome), ...] online na sala: cada um ganha 1 planeta sorteado."""
        with self._mexendo() as agora:
            if self.estado != "aguardando":
                raise ErroDaConquista("A Conquista já começou. Use \"Nova conquista\" para começar outra.")
            self.metrica = metrica if metrica in METRICAS else "maxKi"
            self.escudo, self.espera = int(escudo), int(espera)
            planetas = sorted(self.fonte.planetas(), key=lambda p: p["id"])[:len(LUGARES)]
            self.rng.shuffle(planetas)
            alunos = [self._participante(id_jogador, nome, agora) for id_jogador, nome in alunos]
            neutros = max(0, min(5, int(neutros), len(planetas) - len(alunos)))
            em_jogo = planetas[:min(len(planetas), len(alunos) + neutros)]
            for lugar, planeta in zip(LUGARES, em_jogo):
                territorio = Territorio(planeta, lugar)
                self.territorios[territorio.id] = territorio
            territorios = list(self.territorios.values())
            for participante, territorio in zip(alunos, territorios):
                territorio.dono = participante.id
                participante.chegou_em = agora
            for territorio in territorios[len(alunos):]:
                territorio.guardiao_neutro = self._sorteio_medio()
            self.estado = "ativa"
            self.duracao = int(minutos * 60) if minutos else None
            self.fim_previsto = agora + self.duracao if self.duracao else None
            self._evento("inicio", agora, f"🗺 A Conquista começou! {len(territorios)} territórios em jogo.")
            self._avisos.append("🗺 A Conquista de Territórios começou! Abra a tela 🗺 Conquista do app, escolha o seu "
                                "Guardião e invada os planetas dos colegas.")
            return {"territorios": len(territorios), "neutros": sum(1 for t in territorios if t.dono is None)}

    def pausar(self):
        with self._mexendo() as agora:
            if self.estado == "ativa":
                self.estado, self.pausada_em = "pausada", agora
                self._evento("pausa", agora, "⏸ A Conquista foi pausada.")

    def retomar(self):
        with self._mexendo() as agora:
            if self.estado != "pausada":
                return
            if self.fim_previsto is not None:
                self.fim_previsto += agora - self.pausada_em        # o tempo parado nao conta
            self.estado, self.pausada_em = "ativa", None
            self._evento("retomada", agora, "▶ A Conquista voltou!")

    def encerrar(self):
        with self._mexendo() as agora:
            if self.estado in ("ativa", "pausada"):
                self._encerrar(agora, "professor")

    def _encerrar(self, agora, motivo):
        for invasao in self.invasoes.values():               # luta pela metade: o planeta fica com quem estava
            if not invasao.resolvida:
                invasao.resolvida = True
                invasao.partida.encerrar("b", "cancelada")
                self.territorios[invasao.territorio].em_batalha = None
        self.estado, self.pausada_em = "encerrada", None
        self._evento("fim", agora, "🏁 Fim da Conquista!" + (" (acabou o tempo)" if motivo == "tempo" else ""),
                     motivo=motivo)
        classificacao, contagem = self._classificacao()
        medalhas = ["🥇", "🥈", "🥉"]
        podio = " · ".join(f"{medalhas[i]} {p.nome[:30]} ({contagem.get(p.id, 0)})" for i, p in
                           enumerate(classificacao[:3]))
        self._avisos.append("🏁 Fim da Conquista de Territórios!" + (f" {podio}" if podio else ""))

    def nova(self):
        with self._mexendo() as agora:
            self._zerar()
            self._evento("nova", agora, "↺ Nova conquista: esperando a largada.")

    def entregar(self, id_territorio, id_jogador):
        """Da um territorio NEUTRO a um participante (o ensaio do modo demonstracao comeca com os robos maiores)."""
        with self._mexendo():
            territorio = self.territorios.get(str(id_territorio))
            if territorio is not None and territorio.dono is None and id_jogador in self.participantes:
                territorio.dono = id_jogador

    # ---------------- o que os alunos fazem ----------------

    def exigir_ativa(self):
        with self._mexendo():
            if self.estado != "ativa":
                raise ConquistaParada(MENSAGENS_PARADA[self.estado])

    def escolher_guardiao(self, id_jogador, nome, id_personagem):
        with self._mexendo() as agora:
            if self.estado == "encerrada":
                raise ConquistaParada(MENSAGENS_PARADA["encerrada"])
            participante = self._participante(id_jogador, nome, agora)
            personagem = self._detalhe(id_personagem)
            if participante.trocou_guardiao_em is not None and agora - participante.trocou_guardiao_em < \
                    TROCA_DE_GUARDIAO:
                falta = int(TROCA_DE_GUARDIAO - (agora - participante.trocou_guardiao_em)) + 1
                raise Devagar(f"Calma! O seu Guardião acabou de entrar. Você pode trocar de novo em {falta} s.")
            participante.guardiao = personagem["id"]
            participante.guardiao_escolhido = True
            participante.trocou_guardiao_em = agora
            return self._visao(participante, agora, 0)

    def invadir(self, id_jogador, nome, id_territorio, id_personagem):
        """Confere tudo DENTRO da trava (dois cliques no mesmo alvo: so um passa) e cria a luta."""
        with self._mexendo() as agora:
            if self.estado != "ativa":
                raise ConquistaParada(MENSAGENS_PARADA[self.estado])
            atacante = self._participante(id_jogador, nome, agora)
            territorio = self.territorios.get(str(id_territorio))
            if territorio is None:
                raise NaoExiste("Esse território não existe no mapa.")
            if territorio.dono == atacante.id:
                raise Proibido("Esse território já é seu! Escolha o de outra pessoa.")
            if any(not i.resolvida and i.atacante == atacante.id for i in self.invasoes.values()):
                raise Ocupado("Você já está numa invasão. Termine essa primeiro.")
            if territorio.em_batalha:
                raise Ocupado(f"{territorio.nome} já está sendo invadido por outra pessoa. Tente outro alvo!")
            if agora < territorio.escudo_ate:
                raise Ocupado(f"{territorio.nome} está protegido por um escudo 🛡 por mais "
                              f"{int(territorio.escudo_ate - agora) + 1} s.")
            if atacante.ultima_invasao is not None and agora - atacante.ultima_invasao < self.espera:
                falta = int(self.espera - (agora - atacante.ultima_invasao)) + 1
                raise Devagar(f"Calma! Espere {falta} s para invadir de novo. ⏳")
            lutador = self._detalhe(id_personagem)
            dono = self.participantes.get(territorio.dono) if territorio.dono else None
            guardiao = self._detalhe(dono.guardiao if dono else territorio.guardiao_neutro)
            guardiao_nome = guardiao["name"].strip()
            de_quem = f"de {dono.nome}" if dono else "neutro"
            partida = PartidaBatalha(f"cq-{secrets.token_hex(5)}", {"id": atacante.id, "nome": atacante.nome},
                                     {"id": f"guardiao-{territorio.id}", "nome": f"🛡 {territorio.nome} ({de_quem})"},
                                     lutador, guardiao, self.metrica)
            partida.comeca = agora + PartidaBatalha.CONTAGEM             # no relogio da Conquista
            partida.rng = random.Random(self.rng.getrandbits(32))        # nos testes, a luta sai sempre igual
            for lado in ("a", "b"):                                      # o teto de forca
                partida.luta[lado]["forca"] = min(partida.luta[lado]["forca"], TETO_DE_FORCA)
            invasao = Invasao(partida, territorio.id, atacante.id, territorio.dono, guardiao_nome)
            self.invasoes[partida.id] = invasao
            territorio.em_batalha = partida.id
            atacante.ultima_invasao = agora
            atacante.invasoes += 1
            self._evento("invasao", agora, f"⚔ {atacante.nome} está invadindo {territorio.nome} ({de_quem})!",
                         territorio=territorio.id, cor=atacante.cor, jogador=atacante.id)
            return {"partida": partida.id, "territorio": territorio.id, "guardiao": guardiao_nome}

    # ---------------- as lutas (pela rota /turma/partida/<id>) ----------------

    def tem_partida(self, id_partida):
        with self._trava:
            return id_partida in self.invasoes

    def _invasao(self, id_partida, id_jogador):
        """A invasao, se ela existir e for DESTE aluno (so o atacante assiste, transforma ou desiste)."""
        invasao = self.invasoes.get(id_partida or "")
        if invasao is None:
            raise NaoExiste("Luta desconhecida.")
        if invasao.atacante != id_jogador:
            raise Proibido("Essa luta não é sua.")
        return invasao

    def estado_da_partida(self, id_jogador, id_partida):
        with self._mexendo() as agora:
            partida = self._invasao(id_partida, id_jogador).partida
            estado = partida.estado(agora)
            estado["seu_lado"] = "a"                                      # o atacante e sempre o lado "a"
            estado["conquista"] = True
            return estado

    def transformar(self, id_jogador, id_partida):
        with self._mexendo() as agora:
            invasao = self._invasao(id_partida, id_jogador)
            invasao.partida.avancar(agora)
            invasao.partida.transformar(id_jogador)
            return {"ok": True}

    def desistir(self, id_jogador, id_partida):
        with self._mexendo() as agora:
            invasao = self._invasao(id_partida, id_jogador)
            if not invasao.resolvida:
                invasao.partida.encerrar("b", "desistencia")
                self._resolver(invasao, agora)
            return {"ok": True}

    # ---------------- o que cada um ve ----------------

    def _tempo_restante(self, agora):
        if self.fim_previsto is None:
            return None
        if self.estado == "pausada":
            return max(0, int(self.fim_previsto - self.pausada_em))
        if self.estado == "encerrada":
            return 0
        return max(0, int(self.fim_previsto - agora))

    def _mapa(self, agora, id_jogador=None):
        mapa = []
        for territorio in self.territorios.values():
            dono = self.participantes.get(territorio.dono) if territorio.dono else None
            guardiao = dono.guardiao if dono else territorio.guardiao_neutro
            mapa.append({"id": territorio.id, "nome": territorio.nome, "x": territorio.x, "y": territorio.y,
                         "dono": dono.nome if dono else None, "cor": dono.cor if dono else None,
                         "meu": bool(id_jogador) and territorio.dono == id_jogador,
                         "escudo": max(0, int(territorio.escudo_ate - agora) + 1) if agora < territorio.escudo_ate
                         else 0,
                         "em_batalha": bool(territorio.em_batalha),
                         "guardiao": self._nome_do_personagem(guardiao)})
        return mapa

    def _ranking(self, limite=None):
        classificacao, contagem = self._classificacao()
        linhas = [{"posicao": i, "nome": p.nome, "cor": p.cor, "territorios": contagem.get(p.id, 0),
                   "conquistas": p.conquistas, "defesas": p.defesas, "invasoes": p.invasoes}
                  for i, p in enumerate(classificacao, start=1)]
        return linhas[:limite] if limite else linhas

    def visao(self, id_jogador, nome, depois=0):
        """O que a tela 🗺 Conquista do aluno mostra (o servidor responde 200 se ativa, 409 se parada)."""
        with self._mexendo() as agora:
            participante = self._participante(id_jogador, nome, agora) if self.estado != "encerrada" \
                else self.participantes.get(id_jogador) or Participante(id_jogador, nome, None, agora)
            return self._visao(participante, agora, depois)

    def _visao(self, participante, agora, depois):
        classificacao, contagem = self._classificacao()
        posicao = next((i for i, p in enumerate(classificacao, start=1) if p.id == participante.id), None)
        invasao = next((i.partida.id for i in self.invasoes.values()
                        if not i.resolvida and i.atacante == participante.id), None)
        troca = 0
        if participante.trocou_guardiao_em is not None:
            troca = max(0, int(TROCA_DE_GUARDIAO - (agora - participante.trocou_guardiao_em)) + 1) \
                if agora - participante.trocou_guardiao_em < TROCA_DE_GUARDIAO else 0
        espera = 0
        if participante.ultima_invasao is not None and agora - participante.ultima_invasao < self.espera:
            espera = int(self.espera - (agora - participante.ultima_invasao)) + 1
        guardiao = self.fonte.detalhe_personagem(participante.guardiao) if participante.guardiao else None
        return {
            "estado": self.estado,
            "mensagem": MENSAGENS_PARADA.get(self.estado, ""),
            "tempo_restante": self._tempo_restante(agora),
            "metrica": self.metrica, "nome_da_metrica": METRICAS[self.metrica],
            "escudo": self.escudo, "espera": self.espera,
            "mapa": self._mapa(agora, participante.id),
            "eu": {"nome": participante.nome, "cor": participante.cor,
                   "territorios": contagem.get(participante.id, 0), "posicao": posicao,
                   "conquistas": participante.conquistas, "defesas": participante.defesas,
                   "invasoes": participante.invasoes,
                   "guardiao": {"id": participante.guardiao, "nome": guardiao["name"].strip() if guardiao else "?",
                                "escolhido": participante.guardiao_escolhido},
                   "troca_em": troca, "espera": espera, "invasao": invasao},
            "ranking": self._ranking(5),
            "eventos": [self._publico(e) for e in self._eventos if e["id"] > depois],
            "ultimo_evento": self._proximo_evento - 1,
        }

    def instantaneo(self):
        """Uma COPIA de tudo, para o painel do professor e o telao."""
        with self._mexendo() as agora:
            return {"estado": self.estado, "mensagem": MENSAGENS_PARADA.get(self.estado, ""),
                    "tempo_restante": self._tempo_restante(agora), "duracao": self.duracao,
                    "metrica": self.metrica, "escudo": self.escudo, "espera": self.espera,
                    "mapa": self._mapa(agora), "ranking": self._ranking(),
                    "lutas": sum(1 for i in self.invasoes.values() if not i.resolvida),
                    "resultado_salvo": self.resultado_salvo}

    # ---------------- resultado em CSV ----------------

    def linhas_do_resultado(self):
        with self._mexendo():
            linhas = [["posicao", "aluno", "territorios", "conquistas", "defesas", "invasoes"]]
            for item in self._ranking():
                linhas.append([item["posicao"], item["nome"], item["territorios"], item["conquistas"],
                               item["defesas"], item["invasoes"]])
            return linhas

    def salvar_csv(self, pasta=None):
        """conquista_<data_hora>.csv (separado por ';' e com BOM: o Excel em portugues abre certinho)."""
        pasta = pasta or PASTA_DOS_RESULTADOS
        pasta.mkdir(parents=True, exist_ok=True)
        caminho = pasta / f"conquista_{datetime.now():%Y-%m-%d_%H-%M-%S}.csv"
        with open(caminho, "w", encoding="utf-8-sig", newline="") as arquivo:
            csv.writer(arquivo, delimiter=";").writerows(self.linhas_do_resultado())
        with self._trava:
            self.resultado_salvo = str(caminho)
        return caminho
