"""
Ensaio da Caca as Esferas: alunos falsos entram na sala e cacam as esferas DO MESMO JEITO que um aluno faria
(navegador, cabecalho, radar, caverna 404, grito UDP, curl), cada um no seu ritmo. Serve para o professor
testar o telao sozinho, antes da aula.

    python ferramentas/simular_cacada.py --conectar 192.168.0.10:8000
    python ferramentas/simular_cacada.py --conectar 127.0.0.1:8000 --alunos 15 --velocidade 3

  --alunos N        quantos alunos falsos (padrao 15)
  --velocidade X    2 = duas vezes mais rapido, 0.5 = mais devagar (padrao 1: os primeiros terminam em ~3 min)

Como ensaiar:
  1. Abra o "Dragon Ball Dex - Servidor do Professor" e va para a aba 🐉 Caçada.
  2. Rode este programa: os alunos falsos aparecem na sala.
  3. Clique em "Iniciar caçada" e assista ao telao. Ctrl+C para parar os alunos falsos.
De vez em quando um aluno falso erra o codigo ou tenta usar o de um colega (aparece no "Pedidos ao vivo").
"""

import argparse
import random
import re
import socket
import sys
import threading
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import requests

from core import esferas
from core.descoberta import PORTA_DESCOBERTA

NOMES = ["Ana", "Bruno", "Carla", "Davi", "Eduarda", "Felipe", "Gabriela", "Heitor", "Isabela", "João",
         "Kauã", "Larissa", "Miguel", "Nicole", "Otávio", "Pietra", "Rafael", "Sofia", "Thiago", "Valentina"]
APP = "DragonBallDex/2.0"
NAVEGADOR = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
             "Chrome/129.0.0.0 Safari/537.36")
CURL = "curl/8.9.1"
CODIGO = re.compile(r"ESF-[A-Z0-9]{5}")

parar = threading.Event()
_trava_da_tela = threading.Lock()


def escrever(texto):
    with _trava_da_tela:
        print(f"[{datetime.now():%H:%M:%S}] {texto}", flush=True)


class AlunoFalso(threading.Thread):
    def __init__(self, nome, endereco, velocidade, total):
        super().__init__(daemon=True)
        self.nome = nome
        self.base = f"http://{endereco}"
        self.ip_servidor = endereco.rsplit(":", 1)[0]
        self.velocidade = velocidade
        self.total = total
        self.ritmo = random.uniform(0.6, 2.2)          # cada aluno tem o seu ritmo
        self.sessao = requests.Session()
        self.sessao.headers.update({"User-Agent": APP, "X-Aluno": nome})
        self.numero = None
        self.ultima_tentativa = 0.0

    # ---------------- ajudantes ----------------

    def esperar(self, segundos):
        """Espera (mais rapido com --velocidade) sem deixar de dizer "estou aqui" para a sala."""
        fim = time.time() + segundos / self.velocidade
        while time.time() < fim and not parar.is_set():
            time.sleep(min(1.5, max(0.0, fim - time.time())))
            try:
                self.sessao.get(self.base + "/turma/sala", timeout=5)
            except requests.RequestException:
                pass                                 # rede piscou: tenta de novo na proxima volta

    def estado(self):
        resposta = self.sessao.get(self.base + "/esferas/estado", timeout=5)
        if resposta.status_code == 404:
            raise SystemExit("Esse servidor nao tem a Caca as Esferas (versao antiga?).")
        return resposta.json()

    def get(self, caminho, user_agent=None, **params):
        """Pedido 'de fora do app' (navegador ou curl): sem o X-Jogador, com ?cacador=."""
        return requests.get(self.base + caminho, params=params, timeout=5,
                            headers={"User-Agent": user_agent or NAVEGADOR})

    def resgatar(self, codigo):
        falta = self.ultima_tentativa + esferas.INTERVALO_RESGATE + 0.2 - time.time()
        if falta > 0:
            time.sleep(falta)                        # respeita o limite de 2 s (como um aluno paciente)
        self.ultima_tentativa = time.time()
        return self.sessao.post(self.base + "/esferas/resgatar", json={"codigo": codigo}, timeout=5)

    # ---------------- como achar cada esfera ----------------

    def achar(self, esfera):
        n = self.numero
        if esfera == 2:
            self.get("/")                                                      # olha a pagina inicial...
            return self.codigo_em(self.get("/esferas/navegador", cacador=n).text)
        if esfera == 3:
            return self.sessao.get(self.base + "/esferas/pista", timeout=5).headers.get("X-Esfera")
        if esfera == 4:
            return self.radar()
        if esfera == 5:
            if random.random() < 0.5:
                self.get("/esferas/caverna-tierra", cacador=n)                 # errou o planeta primeiro
            return self.codigo_em(self.get("/esferas/caverna-namek", cacador=n).text)
        if esfera == 6:
            return self.gritar()
        if esfera == 7:
            return self.codigo_em(self.get("/esferas/terminal", user_agent=CURL, cacador=n).text)
        return None

    @staticmethod
    def codigo_em(texto):
        achado = CODIGO.search(texto or "")
        return achado.group(0) if achado else None

    def radar(self):
        """Procura como um aluno esperto: cada resposta (frio, morno...) elimina os lugares impossiveis."""
        lugares = [(x, y) for x in range(esferas.LADO_DO_RADAR + 1) for y in range(esferas.LADO_DO_RADAR + 1)]
        while lugares and not parar.is_set():
            x, y = random.choice(lugares)
            resposta = self.get("/esferas/radar", cacador=self.numero, x=x, y=y)
            codigo = self.codigo_em(resposta.text)
            if codigo or resposta.status_code != 200:
                return codigo
            lugares = [(a, b) for a, b in lugares if (a, b) != (x, y)
                       and resposta.text.startswith(esferas.temperatura(abs(a - x) + abs(b - y)))]
            self.esperar(random.uniform(1, 3))
        return None

    def gritar(self):
        """O grito UDP. Vai direto para o IP do servidor (funciona tambem no mesmo PC)."""
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(1.5)
        try:
            if random.random() < 0.3:                                          # errou a palavra primeiro
                sock.sendto(esferas.montar_grito(self.numero, "HADOUKEN"), (self.ip_servidor, PORTA_DESCOBERTA))
                sock.recvfrom(2048)
                self.esperar(2)
            sock.sendto(esferas.montar_grito(self.numero, "Kamehameha"), (self.ip_servidor, PORTA_DESCOBERTA))
            resposta = esferas.ler_resposta_grito(sock.recvfrom(2048)[0]) or {}
            return resposta.get("codigo")
        except OSError:
            return None
        finally:
            sock.close()

    # ---------------- a cacada ----------------

    def run(self):
        try:
            entrada = self.sessao.post(self.base + "/turma/entrar", json={"nome": self.nome}, timeout=5).json()
            self.sessao.headers["X-Jogador"] = entrada["id"]
            self.cacar()
        except SystemExit as aviso:
            escrever(str(aviso))
            parar.set()
        except requests.RequestException as erro:
            escrever(f"{self.nome}: perdi a conexão com o servidor ({type(erro).__name__}).")

    def cacar(self):
        """Fica na sala ate o Ctrl+C: da para ensaiar varias cacadas seguidas ("Nova caçada")."""
        ultimo_estado = None
        while not parar.is_set():
            visao = self.estado()
            self.numero = visao["numero"]
            estado = visao["estado"]
            if estado != "ativa":
                if estado != ultimo_estado and estado == "encerrada":
                    escrever(f"{self.nome}: fim! {len(visao['esferas'])} esferas, {visao['pontos']} pontos.")
                elif estado != ultimo_estado and estado == "aguardando":
                    escrever(f"{self.nome} (caçador {self.numero:02d}) está na sala, esperando a largada...")
                ultimo_estado = estado
                self.esperar(1.5 * self.velocidade)
                continue
            ultimo_estado = estado
            pedido = visao["pedido"]
            if pedido and pedido["pendente"]:
                self.escolher_pedido()
                continue
            faltam = [n for n in range(2, 8) if n not in visao["esferas"]]
            if not faltam:
                self.esperar(3 * self.velocidade)                         # ja terminou: so fica na sala
                continue
            self.esperar(random.uniform(6, 25) * self.ritmo)
            if parar.is_set() or self.estado()["estado"] != "ativa":
                continue
            esfera = faltam[0]
            codigo = self.achar(esfera)
            if not codigo:
                continue
            if random.random() < 0.1:                                        # errou uma letra
                self.resgatar(codigo[:-1] + ("2" if codigo[-1] != "2" else "3"))
            if random.random() < 0.05:                                       # tentou o codigo de um colega
                colega = self.numero % self.total + 1
                self.resgatar(self.codigo_em(self.get("/esferas/terminal", user_agent=CURL, cacador=colega).text)
                              or "ESF-22222")
            resposta = self.resgatar(codigo)
            if resposta.status_code == 200 and resposta.json()["resgate"]["nova"]:
                escrever(f"{self.nome} achou a esfera {esfera} ({esferas.ESFERAS[esfera]['conceito']})")

    def escolher_pedido(self):
        if random.random() < 0.2:
            escrever(f"{self.nome} juntou as 7! Vai deixar o tempo do pedido acabar...")
            self.esperar((esferas.TEMPO_DO_PEDIDO + 2) * self.velocidade)    # 32 s de verdade, sem acelerar
            return
        self.esperar(random.uniform(2, 10))
        opcao = random.randint(1, 3)
        if self.sessao.post(self.base + "/esferas/pedido", json={"pedido": opcao}, timeout=5).status_code == 200:
            escrever(f"{self.nome} pediu: {esferas.PEDIDOS[opcao]}")


def principal():
    argumentos = argparse.ArgumentParser(description="Alunos falsos para ensaiar a Caça às Esferas.")
    argumentos.add_argument("--conectar", required=True, help="endereço do servidor, ex.: 192.168.0.10:8000")
    argumentos.add_argument("--alunos", type=int, default=15)
    argumentos.add_argument("--velocidade", type=float, default=1.0)
    opcoes = argumentos.parse_args()
    endereco = opcoes.conectar.replace("http://", "").strip("/")
    try:
        ping = requests.get(f"http://{endereco}/turma/ping", timeout=4).json()
    except (requests.RequestException, ValueError):
        sys.exit(f"Não achei um servidor Dragon Ball Dex em {endereco}. Ele está ligado?")
    print(f"Servidor: {ping.get('nome')} (versão {ping.get('versao')})")
    nomes = [NOMES[i] if i < len(NOMES) else f"Aluno {i + 1}" for i in range(opcoes.alunos)]
    print(f"Entrando com {len(nomes)} alunos falsos. Clique em \"Iniciar caçada\" no painel. Ctrl+C para parar.\n")
    alunos = [AlunoFalso(nome, endereco, max(0.1, opcoes.velocidade), len(nomes)) for nome in nomes]
    for aluno in alunos:
        aluno.start()
        time.sleep(0.3)
    try:
        while any(aluno.is_alive() for aluno in alunos):
            time.sleep(0.5)
    except KeyboardInterrupt:
        print("\nParando os alunos falsos...")
        parar.set()


if __name__ == "__main__":
    principal()
