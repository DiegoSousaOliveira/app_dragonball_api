"""Onde o programa guarda e le arquivos (JSON de dados, cache, configuracao, placar)."""

import json
import os
import sys
import threading
from pathlib import Path

# True quando o programa roda como DragonBallDex.exe (empacotado pelo PyInstaller)
CONGELADO = getattr(sys, "frozen", False)

if CONGELADO:
    # Arquivos que vieram DENTRO do instalador (so leitura)
    PASTA_RECURSOS = Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
    # Arquivos que o programa grava: na pasta do usuario do Windows
    PASTA_USUARIO = Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "DragonBallDex"
else:
    PASTA_RECURSOS = Path(__file__).resolve().parent.parent
    PASTA_USUARIO = PASTA_RECURSOS / "dados_usuario"

PASTA_DADOS = PASTA_RECURSOS / "dados"                  # snapshot_*.json (plano B sem internet)
PASTA_CACHE_EMBUTIDO = PASTA_RECURSOS / "cache"         # imagens que ja vem no instalador
PASTA_CACHE = PASTA_USUARIO / "cache"                   # o que o programa baixa


def salvar_json(caminho, dados):
    """Grava 'dados' num arquivo JSON, criando a pasta se precisar.
    Grava num arquivo temporario e depois troca: assim nunca fica um JSON pela metade."""
    caminho = Path(caminho)
    caminho.parent.mkdir(parents=True, exist_ok=True)
    temporario = caminho.with_name(f"{caminho.name}.{threading.get_ident()}.tmp")   # um por thread
    with open(temporario, "w", encoding="utf-8") as arquivo:
        json.dump(dados, arquivo, ensure_ascii=False, indent=2)
    os.replace(temporario, caminho)


def carregar_json(caminho, padrao=None):
    """Le um arquivo JSON. Se ele nao existir ou estiver estragado, devolve 'padrao'."""
    try:
        with open(caminho, encoding="utf-8") as arquivo:
            return json.load(arquivo)
    except (OSError, ValueError):
        return padrao
