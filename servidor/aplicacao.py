"""O servidor do professor inteiro: HTTP + espelho + placar + monitor + descoberta na rede."""

import socket
import threading
from http.server import ThreadingHTTPServer

from core.armazenamento import PASTA_USUARIO
from core.descoberta import RespondedorDeDescoberta, ips_locais
from core.esferas import Cacada
from servidor import rotas_esferas
from servidor.chat import Chat
from servidor.espelho import Espelho
from servidor.monitor import Monitor
from servidor.placar import PlacarDaTurma
from servidor.rotas import TratadorDragonBall
from servidor.sala import Sala

PORTA_PADRAO = 8000


class ServidorHTTP(ThreadingHTTPServer):
    daemon_threads = True              # cada aluno e atendido numa thread; elas morrem com o programa
    allow_reuse_address = False        # no Windows, True deixaria dois servidores na mesma porta


def abrir_porta(host, porta_inicial):
    """Tenta a porta 8000; se estiver ocupada, 8001, 8002... (porta 0 = o sistema escolhe).
    host "0.0.0.0" = aceita conexoes de qualquer computador da rede; "127.0.0.1" = so deste."""
    if porta_inicial == 0:
        return ServidorHTTP((host, 0), TratadorDragonBall)
    ultimo_erro = None
    for porta in range(porta_inicial, porta_inicial + 10):
        try:
            return ServidorHTTP((host, porta), TratadorDragonBall)
        except OSError as problema:
            ultimo_erro = problema
    raise OSError(f"Nenhuma porta livre entre {porta_inicial} e {porta_inicial + 9}: {ultimo_erro}")


class ServidorDragonBall:
    def __init__(self, porta=PORTA_PADRAO, descoberta=True, arquivo_placar=None, host="0.0.0.0"):
        self.nome = f"Servidor do professor ({socket.gethostname()})"
        self.espelho = Espelho()
        self.monitor = Monitor()
        self.placar = PlacarDaTurma(arquivo_placar or PASTA_USUARIO / "placar_da_turma.json")
        self.sala = Sala(self.espelho, self.placar)
        self.chat = Chat()
        self.cacada = Cacada(avisar=self.chat.mensagem_do_professor)   # desligada ate o professor iniciar
        self.host = host
        self.http = abrir_porta(host, porta)
        self.http.app = self               # o tratador acha tudo por aqui (self.server.app)
        self.porta = self.http.server_address[1]
        self.usar_descoberta = descoberta
        self.descoberta = None
        self.aviso_descoberta = ""
        self._thread = None

    def iniciar(self):
        self._thread = threading.Thread(target=self.http.serve_forever, daemon=True)
        self._thread.start()
        if self.usar_descoberta:
            try:
                self.descoberta = RespondedorDeDescoberta(
                    self.porta, self.nome, self.host,
                    ao_receber_outro=lambda dados, remetente: rotas_esferas.ao_receber_udp(self, dados, remetente))
            except OSError as problema:
                self.aviso_descoberta = f"Busca automatica indisponivel ({problema}). Digite o IP."
        # Em segundo plano: deixa a lista de personagens pronta na memoria
        threading.Thread(target=self._aquecer_lista, daemon=True).start()

    def _aquecer_lista(self):
        try:
            self.espelho.personagens()
            self.espelho.planetas()
        except Exception:
            pass

    def parar(self):
        if self.descoberta:
            self.descoberta.parar()
        self.http.shutdown()
        self.http.server_close()

    def enderecos(self):
        """Como os alunos encontram este servidor: ['192.168.0.10:8000', ...]."""
        ips = ["127.0.0.1"] if self.host == "127.0.0.1" else (ips_locais() or ["127.0.0.1"])
        return [f"{ip}:{self.porta}" for ip in ips]
