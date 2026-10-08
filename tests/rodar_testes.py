"""
Roda todos os testes SEM precisar do pytest.

Uso (na pasta do projeto):  python tests/rodar_testes.py
Ele procura arquivos tests/test_*.py e executa toda funcao que comeca com "test_".
"""

import importlib
import sys
import traceback
from pathlib import Path

PASTA_TESTES = Path(__file__).resolve().parent
sys.path.insert(0, str(PASTA_TESTES.parent))     # para conseguir "import core..."


def rodar_arquivo(nome_modulo):
    """Executa os testes de um arquivo. Devolve (quantos passaram, quantos falharam)."""
    modulo = importlib.import_module(f"tests.{nome_modulo}")
    passou, falhou = 0, 0
    for nome in dir(modulo):
        funcao = getattr(modulo, nome)
        if not (nome.startswith("test_") and callable(funcao)):
            continue
        try:
            funcao()
            print(f"  [OK]    {nome_modulo}.{nome}")
            passou += 1
        except Exception:
            print(f"  [FALHA] {nome_modulo}.{nome}")
            traceback.print_exc(limit=1)
            falhou += 1
    return passou, falhou


def principal():
    total_ok, total_falha = 0, 0
    for arquivo in sorted(PASTA_TESTES.glob("test_*.py")):
        ok, falha = rodar_arquivo(arquivo.stem)
        total_ok += ok
        total_falha += falha
    print("-" * 40)
    print(f"{total_ok} passaram, {total_falha} falharam")
    return 1 if total_falha else 0


if __name__ == "__main__":
    sys.exit(principal())
