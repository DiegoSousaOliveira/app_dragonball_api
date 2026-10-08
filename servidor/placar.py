"""Placar da turma: batalhas e quiz de todos os alunos, guardado num arquivo JSON."""

import threading
from datetime import datetime

from core.armazenamento import carregar_json, salvar_json
from core.batalha import contar_vitorias
from core.quiz import PREMIO_INICIAL


class DadoInvalido(ValueError):
    """O aluno mandou algo que nao faz sentido (o servidor responde 400)."""


def _texto(valor, campo, maximo=40):
    if not isinstance(valor, str) or not valor.strip():
        raise DadoInvalido(f"'{campo}' precisa ser um texto.")
    return valor.strip()[:maximo]


def _inteiro(valor, campo, minimo, maximo):
    if not isinstance(valor, int) or isinstance(valor, bool) or not minimo <= valor <= maximo:
        raise DadoInvalido(f"'{campo}' precisa ser um numero de {minimo} a {maximo}.")
    return valor


PONTOS_VITORIA = 3           # duelo contra um colega
PONTOS_DERROTA = 1           # perdeu, mas participou (derrota por W.O. nao vale ponto)


class PlacarDaTurma:
    def __init__(self, arquivo):
        self.arquivo = arquivo
        self._trava = threading.Lock()
        dados = carregar_json(arquivo, padrao={})
        self.batalhas = dados.get("batalhas", [])
        self.quiz = dados.get("quiz", [])
        self.duelos = dados.get("duelos", [])

    def _salvar(self):
        salvar_json(self.arquivo, {"batalhas": self.batalhas, "quiz": self.quiz, "duelos": self.duelos})

    def registrar_duelo(self, tipo, vencedor, perdedor, descricao, wo=False):
        """Um duelo entre dois ALUNOS (batalha ou quiz). Chamado pela sala quando a partida acaba."""
        registro = {"data": datetime.now().strftime("%d/%m %H:%M"), "tipo": tipo, "vencedor": vencedor,
                    "perdedor": perdedor, "descricao": descricao, "wo": wo}
        with self._trava:
            self.duelos.append(registro)
            self._salvar()
        return registro

    def classificacao(self):
        """Todos os alunos que ja duelaram, do que tem mais pontos para o que tem menos."""
        with self._trava:
            duelos = list(self.duelos)
        alunos = {}

        def aluno(nome):
            return alunos.setdefault(nome, {"nome": nome, "batalha_v": 0, "batalha_d": 0, "quiz_v": 0,
                                            "quiz_d": 0, "pontos": 0, "pontos_batalha": 0, "pontos_quiz": 0})

        for duelo in duelos:
            prefixo = "batalha" if duelo["tipo"] == "batalha" else "quiz"
            ganhador, perdedor = aluno(duelo["vencedor"]), aluno(duelo["perdedor"])
            ganhador[f"{prefixo}_v"] += 1
            ganhador[f"pontos_{prefixo}"] += PONTOS_VITORIA
            perdedor[f"{prefixo}_d"] += 1
            if not duelo.get("wo"):
                perdedor[f"pontos_{prefixo}"] += PONTOS_DERROTA
        for dados in alunos.values():
            dados["pontos"] = dados["pontos_batalha"] + dados["pontos_quiz"]
        return sorted(alunos.values(),
                      key=lambda a: (-a["pontos"], -(a["batalha_v"] + a["quiz_v"]), a["nome"].lower()))

    def registrar_batalha(self, aluno, dados):
        registro = {
            "data": datetime.now().strftime("%d/%m %H:%M"),
            "aluno": _texto(aluno or "Aluno", "aluno"),
            "vencedor": _texto(dados.get("vencedor"), "vencedor"),
            "perdedor": _texto(dados.get("perdedor"), "perdedor"),
            "rodadas": _inteiro(dados.get("rodadas"), "rodadas", 1, 500),
            "metrica": "ki" if dados.get("metrica") == "ki" else "maxKi",
        }
        with self._trava:
            self.batalhas.append(registro)
            self._salvar()
        return registro

    def registrar_quiz(self, aluno, dados):
        rodadas = _inteiro(dados.get("rodadas"), "rodadas", 1, 10)
        pontos = _inteiro(dados.get("pontos"), "pontos", 0, rodadas * PREMIO_INICIAL)
        registro = {"data": datetime.now().strftime("%d/%m %H:%M"), "aluno": _texto(aluno or "Aluno", "aluno"),
                    "pontos": pontos, "rodadas": rodadas}
        with self._trava:
            recorde = pontos > 0 and all(pontos > q["pontos"] for q in self.quiz if q["rodadas"] == rodadas)
            self.quiz.append(registro)
            self._salvar()
        return {"recorde": recorde}

    def resumo(self):
        with self._trava:
            batalhas = list(self.batalhas)
            quiz = list(self.quiz)
            duelos = list(self.duelos)
        # Melhor resultado de cada aluno no quiz, pelo aproveitamento (pontos / maximo possivel)
        melhores = {}
        for jogo in quiz:
            aproveitamento = jogo["pontos"] / (jogo["rodadas"] * PREMIO_INICIAL)
            atual = melhores.get(jogo["aluno"])
            if atual is None or aproveitamento > atual["aproveitamento"]:
                melhores[jogo["aluno"]] = dict(jogo, aproveitamento=round(aproveitamento, 3))
        recordes = sorted(melhores.values(), key=lambda j: (j["aproveitamento"], j["pontos"]), reverse=True)
        return {
            "hall_da_fama": [{"nome": nome, "vitorias": v} for nome, v in contar_vitorias(batalhas)[:10]],
            "recordes_quiz": recordes[:10],
            "ultimas_batalhas": list(reversed(batalhas[-10:])),
            "total_batalhas": len(batalhas),
            "total_quiz": len(quiz),
            "classificacao": self.classificacao(),
            "ultimos_duelos": list(reversed(duelos[-10:])),
            "total_duelos": len(duelos),
            "regra": f"Duelo contra colega: vitória = {PONTOS_VITORIA} pontos, derrota = {PONTOS_DERROTA} ponto.",
        }

    def zerar(self):
        with self._trava:
            self.batalhas = []
            self.quiz = []
            self.duelos = []
            self._salvar()
