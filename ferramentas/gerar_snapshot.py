"""
Gera a "fotografia" dos dados (dados/snapshot_*.json) usada quando nao ha internet nem cache.

Ferramenta do professor: rode em casa, com internet, quando quiser atualizar os dados salvos.
    python ferramentas/gerar_snapshot.py
Cada personagem e salvo COM o planeta de origem e as transformacoes, e cada planeta COM
seus moradores, para as opcoes funcionarem offline (as imagens ficam no cache/).
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core import api
from core.armazenamento import PASTA_DADOS, salvar_json


def detalhar_todos(caminho, nome):
    """Baixa a lista e depois o detalhe de cada item, mostrando o progresso."""
    lista = api.baixar_lista_completa(caminho)
    detalhes = []
    for numero, item in enumerate(lista, start=1):
        detalhes.append(api.pegar_json(f"{caminho}/{item['id']}"))
        print(f"\r  {nome}: {numero}/{len(lista)}", end="")
    print()
    return detalhes


def principal():
    personagens = api.limpar_nomes(detalhar_todos("/characters", "personagens"))
    planetas = api.limpar_nomes(detalhar_todos("/planets", "planetas"))
    for planeta in planetas:
        api.limpar_nomes(planeta.get("characters", []))
    salvar_json(PASTA_DADOS / "snapshot_personagens.json", personagens)
    salvar_json(PASTA_DADOS / "snapshot_planetas.json", planetas)
    print(f"[OK] {len(personagens)} personagens e {len(planetas)} planetas salvos em {PASTA_DADOS}")


if __name__ == "__main__":
    principal()
