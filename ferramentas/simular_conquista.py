"""
Ensaio da Conquista de Territorios: alunos falsos entram na sala, escolhem o Guardiao, trocam o grito de guerra e
invadem planetas DO MESMO JEITO que o app faz (as mesmas rotas). Serve para o professor testar o telao sozinho,
antes da aula.

    python ferramentas/simular_conquista.py --conectar 192.168.0.10:8000
    python ferramentas/simular_conquista.py --conectar 127.0.0.1:8000 --alunos 15 --velocidade 2

  --alunos N        quantos alunos falsos (padrao 15)
  --velocidade X    2 = duas vezes mais rapido, 0.5 = mais devagar (padrao 1)

Como ensaiar:
  1. Abra o "Dragon Ball Dex - Servidor do Professor" e va para a aba 🗺 Conquista.
  2. Rode este programa: os alunos falsos aparecem na sala.
  3. Clique em "Iniciar" e assista ao telao (⛶ Telão). Ctrl+C para parar os alunos falsos.
De vez em quando um aluno falso clica no proprio planeta (403), num planeta com escudo (409) ou invade rapido
demais (429): aparece no "Pedidos ao vivo", bom para explicar os codigos de status.
"""

import argparse
import random
import sys
import threading
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import requests

NOMES = ["Ana", "Bruno", "Carla", "Davi", "Eduarda", "Felipe", "Gabriela", "Heitor", "Isabela", "João",
         "Kauã", "Larissa", "Miguel", "Nicole", "Otávio", "Pietra", "Rafael", "Sofia", "Thiago", "Valentina"]
APP = "DragonBallDex/2.0"
GRITOS = ["Pelo poder de Namek!", "Ninguém segura a turma!", "KAMEHAMEHA!", "Final Flash!", "Ka... me... ha!",
          "Hoje o planeta é meu!", "Ataque do Dragão!", "Vai, Guardião!"]

parar = threading.Event()
_trava_da_tela = threading.Lock()


def escrever(texto):
    with _trava_da_tela:
        print(f"[{datetime.now():%H:%M:%S}] {texto}", flush=True)


class AlunoFalso(threading.Thread):
    def __init__(self, nome, endereco, velocidade, personagens):
        super().__init__(daemon=True)
        self.nome = nome
        self.base = f"http://{endereco}"
        self.velocidade = velocidade
        self.personagens = personagens
        self.ritmo = random.uniform(0.6, 2.0)          # cada aluno tem o seu ritmo
        self.sessao = requests.Session()
        self.sessao.headers.update({"User-Agent": APP, "X-Aluno": nome})
        self.escolheu_guardiao = False
        self.trocou_grito = False

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
        resposta = self.sessao.get(self.base + "/conquista/estado", timeout=5)
        if resposta.status_code == 404:
            raise SystemExit("Esse servidor nao tem a Conquista de Territorios (versao antiga?).")
        return resposta.json()

    def post(self, caminho, dados):
        return self.sessao.post(self.base + caminho, json=dados, timeout=10)

    # ---------------- o que um aluno faz ----------------

    def escolher_guardiao(self):
        resposta = self.post("/conquista/guardiao", {"personagem": random.choice(self.personagens)})
        if resposta.status_code == 200:
            self.escolheu_guardiao = True
            escrever(f"{self.nome} escolheu {resposta.json()['eu']['guardiao']['nome']} como Guardião")

    def trocar_grito(self):
        if self.post("/gritos/meu", {"frase": random.choice(GRITOS)}).status_code == 200:
            self.trocou_grito = True

    def invadir(self, visao):
        mapa = visao["mapa"]
        meus = [t for t in mapa if t["meu"]]
        livres = [t for t in mapa if not t["meu"] and not t["em_batalha"] and not t["escudo"]]
        sorteio = random.random()
        if sorteio < 0.05 and meus:
            alvo = random.choice(meus)                                       # clicou no proprio planeta (403)
        elif sorteio < 0.12:
            alvo = random.choice([t for t in mapa if not t["meu"]] or mapa)  # nem olhou o escudo (409)
        elif livres:
            alvo = random.choice(livres)
        else:
            return
        resposta = self.post("/conquista/invadir", {"territorio": alvo["id"],
                                                    "personagem": random.choice(self.personagens)})
        if resposta.status_code != 200:
            return
        partida = resposta.json()["partida"]
        de_quem = alvo["dono"] or "neutro"
        escrever(f"{self.nome} invadiu {alvo['nome']} ({de_quem})")
        if random.random() < 0.15:
            self.post("/conquista/invadir", {"territorio": alvo["id"], "personagem": 1})   # clique duplo (409)
        self.assistir(partida)
        if random.random() < 0.1:                                                # impaciente (429)
            self.post("/conquista/invadir", {"territorio": alvo["id"], "personagem": 1})

    def assistir(self, partida):
        """Assiste a luta como a tela do app (as vezes aperta Transformar!)."""
        while not parar.is_set():
            resposta = self.sessao.get(f"{self.base}/turma/partida/{partida}", timeout=5)
            if resposta.status_code != 200:
                return
            estado = resposta.json()
            if estado["fim"]:
                venceu = estado["fim"]["vencedor"] == estado["seu_lado"]
                escrever(f"{self.nome} {'CONQUISTOU' if venceu else 'perdeu para o Guardião de'} "
                         f"{estado['jogadores']['b']['nome'].replace('🛡 ', '')}")
                return
            if estado["pode_transformar"]["a"] and random.random() < 0.3:
                self.sessao.post(f"{self.base}/turma/partida/{partida}/transformar", timeout=5)
            time.sleep(1.0)

    # ---------------- a Conquista ----------------

    def run(self):
        try:
            entrada = self.post("/turma/entrar", {"nome": self.nome}).json()
            self.sessao.headers["X-Jogador"] = entrada["id"]
            self.jogar()
        except SystemExit as aviso:
            escrever(str(aviso))
            parar.set()
        except requests.RequestException as erro:
            escrever(f"{self.nome}: perdi a conexão com o servidor ({type(erro).__name__}).")

    def jogar(self):
        """Fica na sala ate o Ctrl+C: da para ensaiar varias Conquistas seguidas ("Nova")."""
        ultimo_estado = None
        while not parar.is_set():
            visao = self.estado()
            estado = visao["estado"]
            if estado != "ativa":
                if estado != ultimo_estado and estado == "encerrada":
                    eu = visao["eu"]
                    escrever(f"{self.nome}: fim! {eu['territorios']} planeta(s), {eu['posicao'] or '-'}º lugar.")
                elif estado != ultimo_estado and estado == "aguardando":
                    escrever(f"{self.nome} está na sala, esperando a largada...")
                ultimo_estado = estado
                self.esperar(1.5 * self.velocidade)
                continue
            ultimo_estado = estado
            if not self.escolheu_guardiao and random.random() < 0.5:
                self.escolher_guardiao()
            if not self.trocou_grito and random.random() < 0.3:
                self.trocar_grito()
            self.esperar(random.uniform(8, 25) * self.ritmo)
            if parar.is_set():
                continue
            visao = self.estado()
            if visao["estado"] == "ativa" and not visao["eu"]["invasao"]:
                self.invadir(visao)


def principal():
    argumentos = argparse.ArgumentParser(description="Alunos falsos para ensaiar a Conquista de Territórios.")
    argumentos.add_argument("--conectar", required=True, help="endereço do servidor, ex.: 192.168.0.10:8000")
    argumentos.add_argument("--alunos", type=int, default=15)
    argumentos.add_argument("--velocidade", type=float, default=1.0)
    opcoes = argumentos.parse_args()
    endereco = opcoes.conectar.replace("http://", "").strip("/")
    try:
        ping = requests.get(f"http://{endereco}/turma/ping", timeout=4).json()
        personagens = [p["id"] for p in requests.get(f"http://{endereco}/api/characters?limit=100",
                                                     timeout=10).json()["items"]]
    except (requests.RequestException, ValueError, KeyError):
        sys.exit(f"Não achei um servidor Dragon Ball Dex em {endereco}. Ele está ligado?")
    print(f"Servidor: {ping.get('nome')} (versão {ping.get('versao')})")
    nomes = [NOMES[i] if i < len(NOMES) else f"Aluno {i + 1}" for i in range(opcoes.alunos)]
    print(f"Entrando com {len(nomes)} alunos falsos. Clique em \"Iniciar\" na aba 🗺 Conquista. Ctrl+C para parar.\n")
    alunos = [AlunoFalso(nome, endereco, max(0.1, opcoes.velocidade), personagens) for nome in nomes]
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
