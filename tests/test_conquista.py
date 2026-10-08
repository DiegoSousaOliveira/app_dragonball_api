"""Testes da logica da Conquista de Territorios (servidor/conquista.py). Relogio falso: nada de esperar de verdade."""

import json
import random
import tempfile
import threading
from pathlib import Path

from core.armazenamento import PASTA_DADOS
from servidor import conquista as modulo
from servidor.conquista import Conquista


class Fonte:
    """Os personagens e planetas dos dados que vem com o programa (o servidor usa o Espelho)."""

    def __init__(self):
        with open(PASTA_DADOS / "snapshot_personagens.json", encoding="utf-8") as arquivo:
            self._personagens = json.load(arquivo)
        with open(PASTA_DADOS / "snapshot_planetas.json", encoding="utf-8") as arquivo:
            self._planetas = json.load(arquivo)
        self.por_id = {p["id"]: p for p in self._personagens}

    def personagens(self):
        return self._personagens

    def planetas(self):
        return self._planetas

    def detalhe_personagem(self, id_personagem):
        return self.por_id.get(id_personagem)

    def id_de(self, nome):
        return next(p["id"] for p in self._personagens if p["name"].strip() == nome)


FONTE = Fonte()
FORTE = FONTE.id_de("Grand Priest")       # forca 103, mas na Conquista vale no maximo 27
FRACO = FONTE.id_de("Mr. Satan")          # forca ~2,7: perde sempre para o FORTE


class Relogio:
    def __init__(self):
        self.agora = 2_000_000.0

    def __call__(self):
        return self.agora

    def passar(self, segundos):
        self.agora += segundos


def nova(alunos=("Ana", "Beto"), neutros=0, **opcoes):
    """Conquista ja iniciada com estes alunos online (o id de cada um e 'id-<nome>')."""
    relogio, avisos = Relogio(), []
    conquista = Conquista(FONTE, avisar=avisos.append, relogio=relogio, rng=random.Random(7))
    conquista.iniciar([(f"id-{nome}", nome) for nome in alunos], neutros=neutros, **opcoes)
    return conquista, relogio, avisos


def territorio_de(conquista, nome):
    return next(t for t in conquista.territorios.values() if t.dono == f"id-{nome}")


def guardiao(conquista, nome, id_personagem):
    conquista.escolher_guardiao(f"id-{nome}", nome, id_personagem)


def lutar_ate_o_fim(conquista, relogio):
    """Deixa o tempo passar ate as lutas acabarem (o servidor joga uma rodada a cada 1,3 s)."""
    for _ in range(400):
        relogio.passar(1.3)
        conquista.instantaneo()
        if not any(not i.resolvida for i in conquista.invasoes.values()):
            return


def levanta(classe, funcao, *args):
    try:
        funcao(*args)
    except classe as erro:
        return erro
    raise AssertionError(f"esperava {classe.__name__}")


def contagem(conquista):
    return {linha["nome"]: linha["territorios"] for linha in conquista.instantaneo()["ranking"]}


# ---------------- largada ----------------

def test_largada_um_planeta_por_aluno_mais_neutros():
    conquista, _, avisos = nova(("Ana", "Beto", "Carla"), neutros=3)
    territorios = list(conquista.territorios.values())
    assert len(territorios) == 6 and contagem(conquista) == {"Ana": 1, "Beto": 1, "Carla": 1}
    neutros = [t for t in territorios if t.dono is None]
    assert len(neutros) == 3 and all(t.guardiao_neutro for t in neutros)
    assert {(t.x, t.y) for t in territorios} == set(modulo.LUGARES[:6])   # os lugares do meio do mapa
    assert avisos[0].startswith("🗺 A Conquista de Territórios começou!")
    assert len(nova(("Ana",), neutros=9)[0].territorios) == 1 + 5        # no maximo 5 neutros
    muitos = nova([f"A{i}" for i in range(22)], neutros=3)[0]             # so existem 20 planetas
    assert len(muitos.territorios) == 20 and all(t.dono for t in muitos.territorios.values())
    assert sum(1 for linha in muitos.instantaneo()["ranking"] if linha["territorios"] == 0) == 2


def test_quem_chega_depois_comeca_sem_territorio():
    conquista, relogio, _ = nova(("Ana",), neutros=1)
    visao = conquista.visao("id-Davi", "Davi")
    assert visao["eu"]["territorios"] == 0 and visao["estado"] == "ativa"
    neutro = next(t for t in conquista.territorios.values() if t.dono is None)
    conquista.escolher_guardiao("id-Davi", "Davi", FORTE)
    neutro.guardiao_neutro = FRACO
    conquista.invadir("id-Davi", "Davi", neutro.id, FORTE)
    lutar_ate_o_fim(conquista, relogio)
    assert contagem(conquista)["Davi"] == 1


# ---------------- invasoes ----------------

def test_invadir_proprio_inexistente_e_parada():
    conquista, _, _ = nova()
    assert levanta(modulo.Proibido, conquista.invadir, "id-Ana", "Ana", territorio_de(conquista, "Ana").id,
                   FORTE).status == 403
    assert levanta(modulo.NaoExiste, conquista.invadir, "id-Ana", "Ana", "999", FORTE).status == 404
    assert levanta(modulo.ErroDaConquista, conquista.invadir, "id-Ana", "Ana", territorio_de(conquista, "Beto").id,
                   "Goku").status == 400
    conquista.pausar()
    erro = levanta(modulo.ConquistaParada, conquista.invadir, "id-Ana", "Ana", territorio_de(conquista, "Beto").id,
                   FORTE)
    assert erro.status == 409 and "pausada" in str(erro)
    antes = Conquista(FONTE, relogio=Relogio())
    assert "não começou" in str(levanta(modulo.ConquistaParada, antes.invadir, "id-Ana", "Ana", "1", FORTE))


def test_conquista_escudo_e_espera():
    conquista, relogio, _ = nova(("Ana", "Beto", "Carla"))
    guardiao(conquista, "Beto", FRACO)
    alvo = territorio_de(conquista, "Beto")
    resposta = conquista.invadir("id-Ana", "Ana", alvo.id, FORTE)
    assert resposta["partida"].startswith("cq-") and alvo.em_batalha
    lutar_ate_o_fim(conquista, relogio)
    assert alvo.dono == "id-Ana" and contagem(conquista) == {"Ana": 2, "Carla": 1, "Beto": 0}
    assert conquista.participantes["id-Ana"].conquistas == 1
    eventos = [e for e in conquista.eventos_depois(0) if e["tipo"] == "conquista"]
    assert eventos[-1]["texto"] == f"🏴 Ana conquistou {alvo.nome} de Beto!"
    erro = levanta(modulo.Ocupado, conquista.invadir, "id-Carla", "Carla", alvo.id, FORTE)      # escudo de 45 s
    assert erro.status == 409 and "escudo" in str(erro)
    erro = levanta(modulo.Devagar, conquista.invadir, "id-Ana", "Ana", territorio_de(conquista, "Carla").id, FORTE)
    assert erro.status == 429                                                                    # espera de 20 s
    relogio.passar(modulo.ESCUDO_PADRAO)
    assert conquista.invadir("id-Carla", "Carla", alvo.id, FORTE)["partida"]                    # o escudo acabou


def test_defesa_e_alvo_ocupado():
    conquista, relogio, _ = nova(("Ana", "Beto", "Carla"))
    guardiao(conquista, "Beto", FORTE)
    alvo = territorio_de(conquista, "Beto")
    conquista.invadir("id-Ana", "Ana", alvo.id, FRACO)
    erro = levanta(modulo.Ocupado, conquista.invadir, "id-Carla", "Carla", alvo.id, FORTE)
    assert erro.status == 409 and "sendo invadido" in str(erro)
    erro = levanta(modulo.Ocupado, conquista.invadir, "id-Ana", "Ana", territorio_de(conquista, "Carla").id, FORTE)
    assert "já está numa invasão" in str(erro)
    lutar_ate_o_fim(conquista, relogio)
    assert alvo.dono == "id-Beto" and conquista.participantes["id-Beto"].defesas == 1
    assert alvo.escudo_ate == 0                                     # defender nao da escudo


def test_duas_invasoes_ao_mesmo_tempo_so_uma_passa():
    alunos = [f"A{i}" for i in range(10)] + ["Alvo"]
    conquista, _, _ = nova(alunos)
    alvo = territorio_de(conquista, "Alvo")
    resultados, largada = [], threading.Barrier(10)

    def invadir(nome):
        largada.wait(timeout=5)
        try:
            resultados.append(conquista.invadir(f"id-{nome}", nome, alvo.id, FORTE)["partida"])
        except modulo.Ocupado:
            resultados.append(409)

    threads = [threading.Thread(target=invadir, args=(f"A{i}",)) for i in range(10)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=10)
    assert resultados.count(409) == 9 and len(conquista.invasoes) == 1


def test_teto_de_forca_e_guardiao_que_se_transforma():
    conquista, relogio, _ = nova()
    goku = FONTE.id_de("Goku")                                      # tem transformacoes
    guardiao(conquista, "Beto", goku)
    id_partida = conquista.invadir("id-Ana", "Ana", territorio_de(conquista, "Beto").id, FORTE)["partida"]
    partida = conquista.invasoes[id_partida].partida
    assert partida.luta["a"]["forca"] == modulo.TETO_DE_FORCA        # o Grand Priest nao passa de 27
    relogio.passar(partida.CONTAGEM)
    partida.luta["b"]["hp"] = 40                                     # o guardiao esta perdendo...
    conquista.instantaneo()
    assert partida.transformado["b"] is not None                     # ...e se transformou sozinho


def test_so_o_atacante_assiste_e_pode_desistir():
    conquista, _, _ = nova(("Ana", "Beto", "Carla"))
    alvo = territorio_de(conquista, "Beto")
    id_partida = conquista.invadir("id-Ana", "Ana", alvo.id, FRACO)["partida"]
    estado = conquista.estado_da_partida("id-Ana", id_partida)
    assert estado["seu_lado"] == "a" and estado["conquista"] is True
    for funcao in (conquista.estado_da_partida, conquista.transformar, conquista.desistir):
        assert levanta(modulo.Proibido, funcao, "id-Carla", id_partida).status == 403      # nao e a luta dela
    assert levanta(modulo.NaoExiste, conquista.estado_da_partida, "id-Ana", "cq-nada").status == 404
    conquista.desistir("id-Ana", id_partida)
    assert alvo.dono == "id-Beto" and not alvo.em_batalha and conquista.participantes["id-Beto"].defesas == 1


def test_guardiao_troca_com_espera():
    conquista, relogio, _ = nova()
    visao = conquista.escolher_guardiao("id-Ana", "Ana", FORTE)
    assert visao["eu"]["guardiao"]["nome"] == "Grand Priest" and visao["eu"]["guardiao"]["escolhido"]
    assert levanta(modulo.Devagar, conquista.escolher_guardiao, "id-Ana", "Ana", FRACO).status == 429
    relogio.passar(modulo.TROCA_DE_GUARDIAO)
    assert conquista.escolher_guardiao("id-Ana", "Ana", FRACO)["eu"]["guardiao"]["nome"] == "Mr. Satan"


# ---------------- ranking, pausa, fim ----------------

def test_desempate_do_ranking():
    conquista, _, _ = nova(("Ana", "Beto", "Carla", "Davi"))
    p = conquista.participantes
    p["id-Ana"].conquistas, p["id-Beto"].conquistas = 2, 2           # Ana e Beto: 1 territorio e 2 conquistas
    p["id-Ana"].defesas, p["id-Beto"].defesas = 0, 1                 # Beto defendeu mais
    p["id-Carla"].chegou_em, p["id-Davi"].chegou_em = 10.0, 5.0      # Davi chegou antes ao mesmo numero
    assert [linha["nome"] for linha in conquista.instantaneo()["ranking"]] == ["Beto", "Ana", "Davi", "Carla"]


def test_pausa_congela_o_relogio_e_a_luta_termina():
    conquista, relogio, _ = nova(("Ana", "Beto"), minutos=10)
    guardiao(conquista, "Beto", FRACO)
    conquista.invadir("id-Ana", "Ana", territorio_de(conquista, "Beto").id, FORTE)
    relogio.passar(60)
    conquista.pausar()
    relogio.passar(300)                                              # parado nao conta...
    assert conquista.instantaneo()["tempo_restante"] == 540
    assert contagem(conquista)["Ana"] == 2                           # ...mas a luta que ja tinha comecado terminou
    conquista.retomar()
    relogio.passar(540)
    assert conquista.instantaneo()["estado"] == "encerrada"


def test_encerrar_cancela_a_luta_e_salva_csv():
    conquista, _, avisos = nova(("Ana", "Beto", "Carla"))
    alvo = territorio_de(conquista, "Beto")
    id_partida = conquista.invadir("id-Ana", "Ana", alvo.id, FORTE)["partida"]
    conquista.encerrar()
    assert alvo.dono == "id-Beto" and not alvo.em_batalha
    assert conquista.estado_da_partida("id-Ana", id_partida)["fim"]["motivo"] == "cancelada"
    assert avisos[-1].startswith("🏁 Fim da Conquista de Territórios!")
    caminho = conquista.salvar_csv(Path(tempfile.mkdtemp()))
    linhas = caminho.read_text(encoding="utf-8-sig").splitlines()
    assert linhas[0] == "posicao;aluno;territorios;conquistas;defesas;invasoes"
    assert len(linhas) == 4 and any(linha.split(";")[1:3] == ["Ana", "1"] for linha in linhas[1:])
    assert conquista.instantaneo()["resultado_salvo"] == str(caminho)
    conquista.nova()
    assert conquista.estado == "aguardando" and not conquista.territorios


def test_eventos_publicos_sem_codigo_de_ninguem():
    conquista, relogio, _ = nova()
    guardiao(conquista, "Beto", FRACO)
    conquista.invadir("id-Ana", "Ana", territorio_de(conquista, "Beto").id, FORTE)
    lutar_ate_o_fim(conquista, relogio)
    visao = conquista.visao("id-Beto", "Beto")
    texto = json.dumps(visao, ensure_ascii=False)
    assert "id-Ana" not in texto and "id-Beto" not in texto          # o X-Jogador e secreto
    assert [e["tipo"] for e in visao["eventos"]] == ["inicio", "invasao", "conquista"]
    assert conquista.visao("id-Beto", "Beto", depois=visao["ultimo_evento"])["eventos"] == []
