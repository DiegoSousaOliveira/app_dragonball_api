"""
Achar o servidor do professor na rede, sem digitar IP.

Como funciona (UDP broadcast):
  1. o app do aluno grita para a rede inteira: "DRAGONBALLDEX?" (porta UDP 50505)
  2. o servidor do professor escuta essa porta e responde so para quem perguntou:
     {"porta": 8000, "nome": "..."}
  3. o IP de quem respondeu + a porta = endereco do servidor.
Algumas redes bloqueiam broadcast; ai e so digitar o endereco que aparece no telao.
"""

import json
import socket
import threading
import time

PORTA_DESCOBERTA = 50505
PERGUNTA = b"DRAGONBALLDEX?"


def ips_locais():
    """Os enderecos IPv4 deste computador na rede (sem o 127.0.0.1)."""
    ips = set()
    try:
        for info in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
            ips.add(info[4][0])
    except OSError:
        pass
    try:
        # Truque: "conectar" um socket UDP nao envia nada, mas revela qual IP sai para a rede
        teste = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        teste.connect(("8.8.8.8", 80))
        ips.add(teste.getsockname()[0])
        teste.close()
    except OSError:
        pass
    return sorted(ip for ip in ips if not ip.startswith("127."))


def enderecos_de_broadcast():
    """255.255.255.255 e o broadcast de cada rede /24 (ex.: 192.168.0.255)."""
    alvos = ["255.255.255.255", "127.0.0.1"]
    for ip in ips_locais():
        partes = ip.split(".")
        alvos.append(".".join(partes[:3] + ["255"]))
    return alvos


def procurar_servidores(espera=1.5):
    """Pergunta na rede e devolve [{'endereco': '192.168.0.10:8000', 'nome': ...}, ...]."""
    achados = {}
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    sock.settimeout(0.2)
    try:
        for alvo in enderecos_de_broadcast():
            try:
                sock.sendto(PERGUNTA, (alvo, PORTA_DESCOBERTA))
            except OSError:
                pass
        limite = time.time() + espera
        while time.time() < limite:
            try:
                dados, (ip, _) = sock.recvfrom(2048)
            except socket.timeout:
                continue
            except OSError:
                break
            try:
                info = json.loads(dados.decode("utf-8"))
            except ValueError:
                continue
            endereco = f"{ip}:{info['porta']}"
            achados[endereco] = {"endereco": endereco, "nome": info.get("nome", "Servidor")}
    finally:
        sock.close()
    # o proprio computador responde pelo 127.0.0.1 e pelo IP da rede: preferimos o da rede
    if len(achados) > 1:
        achados = {e: i for e, i in achados.items() if not e.startswith("127.")} or achados
    return list(achados.values())


class RespondedorDeDescoberta:
    """Roda no servidor: escuta a porta UDP 50505 e responde a quem perguntar."""

    def __init__(self, porta_http, nome="Servidor do professor", host="0.0.0.0"):
        self.resposta = json.dumps({"porta": porta_http, "nome": nome}).encode("utf-8")
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind((host, PORTA_DESCOBERTA))
        self.sock.settimeout(0.5)
        self.rodando = True
        self.thread = threading.Thread(target=self._escutar, daemon=True)
        self.thread.start()

    def _escutar(self):
        while self.rodando:
            try:
                dados, remetente = self.sock.recvfrom(1024)
            except socket.timeout:
                continue
            except OSError:
                break
            if dados == PERGUNTA:
                try:
                    self.sock.sendto(self.resposta, remetente)
                except OSError:
                    pass

    def parar(self):
        self.rodando = False
        self.sock.close()
