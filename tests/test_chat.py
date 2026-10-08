"""Testes do chat da turma (pelo HTTP, como os apps fazem; os controles do professor direto no objeto)."""

import requests

from servidor import chat as modulo_chat
from tests import test_servidor


def base():
    return test_servidor.servidor()


def chat_do_servidor():
    base()
    return test_servidor._servidor.chat


def entrar(nome):
    resposta = requests.post(base() + "/turma/entrar", json={"nome": nome}, timeout=5).json()
    return {"X-Jogador": resposta["id"], "X-Aluno": nome}


def enviar(quem, texto):
    return requests.post(base() + "/chat", json={"texto": texto}, headers=quem, timeout=5)


def ler(quem, **params):
    return requests.get(base() + "/chat", params=params, headers=quem, timeout=5).json()


def sem_espera(funcao):
    """Desliga o limite de 1,5 s entre mensagens durante um teste."""
    def teste():
        antes = modulo_chat.INTERVALO_MINIMO
        modulo_chat.INTERVALO_MINIMO = 0
        try:
            funcao()
        finally:
            modulo_chat.INTERVALO_MINIMO = antes
    teste.__name__ = funcao.__name__
    return teste


@sem_espera
def test_enviar_e_ler():
    ana, beto = entrar("Ana C"), entrar("Beto C")
    resposta = enviar(ana, "  Oi   turma!\n ")
    assert resposta.status_code == 201 and resposta.json()["texto"] == "Oi turma!"
    ultimo = resposta.json()["id"]
    enviar(beto, "Oi Ana")
    novas = ler(beto, depois=ultimo, versao=chat_do_servidor().versao)
    assert [m["texto"] for m in novas["mensagens"]] == ["Oi Ana"]
    assert novas["mensagens"][0]["minha"] is True and "id_autor" not in novas["mensagens"][0]
    assert ler(ana, depois=ultimo, versao=chat_do_servidor().versao)["mensagens"][0]["minha"] is False


@sem_espera
def test_professor_fecha_e_bloqueia():
    chat = chat_do_servidor()
    ana, beto = entrar("Ana B"), entrar("Beto B")
    chat.liberar(False)
    try:
        resposta = enviar(ana, "posso falar?")
        assert resposta.status_code == 403 and "fechado" in resposta.json()["message"]
        assert ler(ana)["liberado"] is False
    finally:
        chat.liberar(True)
    chat.bloquear(beto["X-Jogador"], "Beto B")
    assert enviar(beto, "oi").status_code == 403
    assert ler(beto)["bloqueado"] is True
    assert enviar(ana, "eu ainda posso").status_code == 201        # so o Beto foi bloqueado
    chat.desbloquear(beto["X-Jogador"])
    assert enviar(beto, "voltei").status_code == 201


def test_limite_contra_spam():
    ana = entrar("Ana S")
    assert enviar(ana, "um").status_code == 201
    assert enviar(ana, "dois").status_code == 403


@sem_espera
def test_apagar_e_limpar_mudam_a_versao():
    chat = chat_do_servidor()
    ana = entrar("Ana A")
    mensagem = enviar(ana, "mensagem feia").json()
    versao = chat.versao
    chat.apagar(mensagem["id"])
    resposta = ler(ana, depois=mensagem["id"], versao=versao)
    assert resposta["todas"] is True and all(m["id"] != mensagem["id"] for m in resposta["mensagens"])
    chat.mensagem_do_professor("Vamos manter o respeito!")
    assert ler(ana)["mensagens"][-1]["tipo"] == "professor"
    chat.limpar()
    assert ler(ana)["mensagens"] == []


def test_texto_invalido_e_aluno_desconhecido():
    ana = entrar("Ana I")
    assert enviar(ana, "   ").status_code == 403
    assert len(enviar(entrar("Ana I2"), "x" * 500).json()["texto"]) == modulo_chat.TAMANHO_MAXIMO
    assert requests.get(base() + "/chat", headers={"X-Jogador": "ninguem"}, timeout=5).status_code == 400
