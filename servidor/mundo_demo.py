"""
O MODO DEMONSTRACAO 🎓: o professor ensaia (ou mostra no projetor) tudo o que os alunos vao fazer, sem que nada
apareca para a turma.

Isolamento POR CONSTRUCAO:
  - o servidor tem DOIS mundos: o real (ServidorDragonBall: a sala, o placar, a Caca... dos alunos) e o mundo
    demo (MundoDemo, aqui), com Sala, Chat, Caca, Conquista, Gritos e placar PROPRIOS;
  - para cada pedido, mundo_do_pedido() escolhe o mundo e as MESMAS funcoes de rota recebem esse objeto. Nao ha
    "if demo" espalhado pelas rotas: um pedido do demo simplesmente nao enxerga o mundo real (e vice-versa);
  - so entra no demo quem manda o cabecalho X-Demo com o TOKEN certo E vem do proprio PC do servidor (127.0.0.1,
    o "loopback"). O token e sorteado (secrets) cada vez que o servidor liga e so existe na memoria. Nenhuma rota,
    argumento ou nome de aluno liga o demo: so o botao 🎓 do painel.
  - O navegador e o curl nao mandam o token (esferas 2, 4, 5 e 7 do ensaio). Por isso, SO no proprio PC do servidor,
    um pedido /esferas/... com ?cacador=901 ou mais (os numeros do demo) vai para o ensaio; sem numero, tambem,
    quando nao ha Caca de verdade valendo. O grito UDP (esfera 6) segue a mesma regra.

No mundo demo, 2 alunos-robo 🤖 aceitam desafios, jogam o quiz e invadem planetas sozinhos.
"""

import ipaddress
import random
import secrets
import threading
import time

from core import api, demo, quiz
from core.esferas import Cacada
from servidor.chat import Chat, Proibido
from servidor.conquista import Conquista, ErroDaConquista
from servidor.gritos import Gritos
from servidor.monitor import Monitor
from servidor.placar import DadoInvalido, PlacarDaTurma
from servidor.sala import Sala

PRIMEIRO_NUMERO = 901             # numeros de cacador do ensaio (os alunos comecam no 1)
IP_DO_PROFESSOR = "127.0.0.1"
ROBOS = [("Kuririn 🤖", "Bip bop! Pela honra das máquinas!"), ("Yamcha 🤖", "Lobo Selvagem... versão 2.0!")]
TICK = 1.0                        # segundos entre as jogadas dos robos
INVADIR_A_CADA = (25, 45)         # segundos (sorteado) entre as invasoes de cada robo
RESPONDER_QUIZ_A_CADA = (3, 6)    # segundos por rodada do quiz


# ----------------------------------------------------------------------
# Quem atende cada pedido
# ----------------------------------------------------------------------

def do_proprio_pc(ip):
    """127.0.0.1 (ou ::1): o pedido saiu do mesmo computador do servidor. Um aluno nunca chega assim."""
    try:
        return ipaddress.ip_address((ip or "").split("%")[0]).is_loopback
    except ValueError:
        return False


def token_valido(app, token):
    if not token:
        return False
    return secrets.compare_digest(token.encode("utf-8", "replace"), app.token_demo.encode("utf-8"))


def numero_do_ensaio(texto):
    texto = (texto or "").strip()
    return texto.isascii() and texto.isdigit() and len(texto) <= 6 and int(texto) >= PRIMEIRO_NUMERO


def mundo_do_pedido(app, ip, cabecalhos, caminho, params):
    """O mundo que atende este pedido: app (o real) ou app.demo (o ensaio do professor)."""
    mundo_demo = app.demo
    if mundo_demo is None or not do_proprio_pc(ip):
        return app
    if token_valido(app, cabecalhos.get(demo.CABECALHO)):
        return mundo_demo
    if cabecalhos.get("X-Jogador"):                    # o app de um aluno rodando no PC do professor
        return app
    if caminho in ("", "/") or caminho.startswith("/esferas/"):   # navegador ou curl no PC do professor
        if numero_do_ensaio(params.get("cacador")):
            return mundo_demo
        if "cacador" not in params and app.cacada.estado != "ativa":
            return mundo_demo
    return app


def mundo_do_grito(app, ip, numero):
    """O grito UDP da esfera 6: do proprio PC e com numero 901+ -> ensaio."""
    if app.demo is not None and do_proprio_pc(ip) and numero >= PRIMEIRO_NUMERO:
        return app.demo
    return app


# ----------------------------------------------------------------------
# As pecas do mundo demo
# ----------------------------------------------------------------------

class PlacarDoDemo(PlacarDaTurma):
    """O placar do ensaio: so na memoria (nunca grava o arquivo da turma)."""

    def __init__(self):
        self.arquivo = None
        self._trava = threading.Lock()
        self.batalhas, self.quiz, self.duelos = [], [], []

    def _salvar(self):
        pass


class ChatDoDemo(Chat):
    """Fechado: no ensaio, ninguem escreve (403)."""

    def __init__(self):
        super().__init__()
        self.liberado = False
        self.mensagem_do_professor("🎓 Modo demonstração: este mundo é só seu. Nada daqui aparece para os alunos "
                                   "nem vale pontos. O chat fica fechado.")

    def enviar(self, jogador, texto):
        raise Proibido("No modo demonstração o chat fica fechado (nada sai daqui).")


class Robo:
    def __init__(self, jogador, frase, rng, agora):
        self.id, self.nome, self.frase = jogador["id"], jogador["nome"], frase
        self.proxima_invasao = agora + rng.uniform(6, 12)     # a primeira vem logo, para o mapa mexer
        self.proxima_resposta = 0.0
        self.quiz = None                                      # {"id", "rodada", "pontos"} do quiz em andamento


class MundoDemo:
    """O mundo do ensaio: as mesmas pecas do servidor real (as rotas nao percebem a diferenca)."""

    demo = True

    def __init__(self, real, rng=None, relogio=time.time, robos_jogando=True):
        self.real = real
        self.nome = real.nome
        self.espelho = real.espelho                 # personagens e planetas: so leitura, os mesmos
        self.monitor = Monitor()                    # "alunos" do /turma/placar do demo (o painel usa o real)
        self.placar = PlacarDoDemo()
        self.sala = Sala(self.espelho, self.placar)
        self.chat = ChatDoDemo()
        self.cacada = Cacada(avisar=self.chat.mensagem_do_professor, primeiro_numero=PRIMEIRO_NUMERO)
        self.conquista = Conquista(self.espelho, avisar=self.chat.mensagem_do_professor)
        self.gritos = Gritos()
        self.conquista.ao_conquistar = lambda atacante, nome, planeta, dono: self.gritos.anunciar(
            atacante, nome, "conquista", f"{nome} conquistou {planeta}!", envolvidos={atacante, dono} - {None})
        self.rng = rng or random.Random()
        self.relogio = relogio
        agora = relogio()
        self.professor = self.sala.entrar(demo.NOME, IP_DO_PROFESSOR)   # o app entra com o mesmo nome e IP
        self.robos = [Robo(self.sala.entrar(nome, "robô"), frase, self.rng, agora) for nome, frase in ROBOS]
        self.cacada.iniciar([(self.professor["id"], demo.NOME)])         # sempre valendo: o professor e o 901
        self._parar = threading.Event()
        self._preparado = False
        if robos_jogando:
            threading.Thread(target=self._jogar, daemon=True, name="robos-do-demo").start()

    def enderecos(self):
        return self.real.enderecos()

    def parar(self):
        self._parar.set()

    # ---------------- os robos ----------------

    def preparar(self):
        """A Conquista do ensaio (precisa da lista de planetas: por isso fora do __init__, que o painel chama na
        hora do clique). Os robos chamam a cada jogada ate dar certo (sem os dados ainda, tenta de novo)."""
        if self._preparado:
            return
        alunos = [(self.professor["id"], demo.NOME)] + [(r.id, r.nome) for r in self.robos]
        self.conquista.iniciar(alunos, minutos=None, neutros=3)
        self._preparado = True
        personagens = self.espelho.personagens()
        for robo in self.robos:
            self.gritos.trocar(robo.id, robo.nome, frase=robo.frase)
            self.conquista.escolher_guardiao(robo.id, robo.nome, self.rng.choice(personagens)["id"])

    def _jogar(self):
        try:
            self.preparar()
        except Exception:
            pass
        while not self._parar.wait(TICK):
            try:
                self.passo()
            except Exception:
                pass                                # um robo com problema nunca derruba o servidor

    def passo(self):
        """Uma jogada de cada robo (os testes chamam direto, com o relogio falso)."""
        try:
            self.preparar()
        except api.ErroDeApi:
            pass                                    # sem os dados ainda: os robos ficam na sala e tentam de novo
        agora = self.relogio()
        for robo in self.robos:
            visao = self.sala.visao(robo.id)        # tambem deixa o robo "online" na sala
            for desafio in visao["recebidos"]:
                self._aceitar(robo, desafio)
            partida = visao["partida"]
            if partida and partida["tipo"] == "quiz":
                self._jogar_quiz(robo, partida["id"], agora)
            if agora >= robo.proxima_invasao:
                robo.proxima_invasao = agora + self.rng.uniform(*INVADIR_A_CADA)
                self._invadir(robo)
        self.conquista.instantaneo()                # poe as lutas em dia mesmo sem ninguem olhando

    def _aceitar(self, robo, desafio):
        personagem = self.rng.choice(self.espelho.personagens())["id"]
        try:
            self.sala.responder(robo.id, {"desafio": desafio["id"], "aceitar": True, "personagem": personagem})
        except DadoInvalido:
            pass

    def _jogar_quiz(self, robo, id_partida, agora):
        estado = self.sala.estado_da_partida(robo.id, id_partida)
        if robo.quiz is None or robo.quiz["id"] != id_partida:
            robo.quiz = {"id": id_partida, "rodada": 0, "pontos": 0}
            robo.proxima_resposta = agora + estado["comeca_em"] + self.rng.uniform(*RESPONDER_QUIZ_A_CADA)
        meu = robo.quiz
        total = len(estado["rodadas"])
        if estado["fim"] or meu["rodada"] >= total or agora < robo.proxima_resposta:
            return
        meu["rodada"] += 1
        meu["pontos"] += self.rng.choice([quiz.PREMIO_INICIAL, quiz.PREMIO_INICIAL, 3, 2, 0])
        robo.proxima_resposta = agora + self.rng.uniform(*RESPONDER_QUIZ_A_CADA)
        self.sala.progresso(robo.id, id_partida, {"rodada": meu["rodada"], "pontos": meu["pontos"],
                                                  "terminou": meu["rodada"] >= total})

    def _invadir(self, robo):
        """Os robos invadem planetas neutros ou do outro robo (nunca o do professor: ele esta apresentando)."""
        mapa = self.conquista.visao(robo.id, robo.nome)["mapa"]
        alvos = [t for t in mapa if not t["meu"] and not t["em_batalha"] and not t["escudo"]
                 and t["dono"] != demo.NOME]
        if not alvos:
            return
        alvo = self.rng.choice(alvos)
        try:
            self.conquista.invadir(robo.id, robo.nome, alvo["id"], self.rng.choice(self.espelho.personagens())["id"])
        except ErroDaConquista:
            pass
