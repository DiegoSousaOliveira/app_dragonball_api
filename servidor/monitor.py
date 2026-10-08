"""Tudo o que acontece no servidor, para o painel do professor mostrar ao vivo."""

import threading
import time
from collections import deque
from datetime import datetime

ONLINE_ATE = 60            # segundos sem pedir nada -> aluno aparece como "ausente"


class Monitor:
    """Guarda os ultimos pedidos e quem esta conectado. Varias threads usam ao mesmo tempo,
    por isso tudo passa por uma trava (Lock)."""

    def __init__(self, maximo_de_pedidos=300):
        self._trava = threading.Lock()
        self._pedidos = deque(maxlen=maximo_de_pedidos)
        self._alunos = {}                # ip -> {"ip", "nome", "pedidos", "primeiro", "ultimo"}
        self._marcas = deque(maxlen=5000)   # horario de cada pedido (para "pedidos por minuto")
        self.total_pedidos = 0
        self.bytes_enviados = 0
        self.inicio = time.time()

    def registrar(self, ip, aluno, metodo, caminho, status, ms, tamanho):
        agora = time.time()
        with self._trava:
            self._pedidos.append({
                "hora": datetime.now().strftime("%H:%M:%S"), "ip": ip, "aluno": aluno,
                "metodo": metodo, "caminho": caminho, "status": status, "ms": ms, "bytes": tamanho,
            })
            self._marcas.append(agora)
            self.total_pedidos += 1
            self.bytes_enviados += tamanho
            self._atualizar_aluno(ip, aluno, agora, contar=True)

    def aluno_entrou(self, ip, nome):
        with self._trava:
            self._atualizar_aluno(ip, nome, time.time(), contar=False)

    def _atualizar_aluno(self, ip, nome, agora, contar):
        aluno = self._alunos.setdefault(ip, {"ip": ip, "nome": "", "pedidos": 0,
                                             "primeiro": agora, "ultimo": agora})
        if nome:
            aluno["nome"] = nome
        if contar:
            aluno["pedidos"] += 1
        aluno["ultimo"] = agora

    def instantaneo(self):
        """Uma COPIA de tudo, para a interface ler sem atrapalhar o servidor."""
        agora = time.time()
        with self._trava:
            pedidos = list(self._pedidos)
            alunos = [dict(a) for a in self._alunos.values()]
            ultimo_minuto = sum(1 for marca in self._marcas if agora - marca <= 60)
            total, enviados = self.total_pedidos, self.bytes_enviados
        for aluno in alunos:
            aluno["online"] = agora - aluno["ultimo"] <= ONLINE_ATE
            aluno["visto_ha"] = int(agora - aluno["ultimo"])
        alunos.sort(key=lambda a: (not a["online"], a["nome"].lower() or a["ip"]))
        return {"pedidos": pedidos, "alunos": alunos, "total": total, "bytes": enviados,
                "por_minuto": ultimo_minuto, "ligado_ha": int(agora - self.inicio)}
