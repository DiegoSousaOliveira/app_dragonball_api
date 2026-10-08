"""Testes do guia "Como funciona?": toda tela do menu tem a sua explicacao (ninguem fica perdido)."""

from interface import ajuda
from interface.app_aluno import MENU
from interface.telas.duelo import TelaDueloBatalha, TelaDueloQuiz


def test_toda_tela_do_menu_tem_explicacao():
    secoes = {chave for chave, *_ in ajuda.GUIA}
    for chave, _, classe in MENU:
        assert chave in secoes, f"falta a explicacao da tela '{chave}' em interface/ajuda.py"
        assert ajuda.TELAS.get(classe.__name__) == chave, f"{classe.__name__} nao abre a secao '{chave}'"
    for classe in (TelaDueloBatalha, TelaDueloQuiz):
        assert ajuda.TELAS.get(classe.__name__) == "turma"
    assert "inicio" in secoes and "problemas" in secoes


def test_textos_do_guia():
    chaves = [chave for chave, *_ in ajuda.GUIA]
    assert len(chaves) == len(set(chaves))                       # nenhuma secao repetida
    for chave, titulo, para_que, passos, dicas in ajuda.GUIA:
        assert titulo.strip() and para_que.strip(), chave
        assert passos, f"a secao '{chave}' precisa de pelo menos um passo"
        assert all(texto.strip() for texto in passos + dicas), chave
