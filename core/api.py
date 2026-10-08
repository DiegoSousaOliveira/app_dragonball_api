"""
Cliente de dados do Dragon Ball Dex.

Ele pode buscar os dados em DOIS lugares:
  - no servidor do professor (rede da sala):  http://192.168.0.10:8000/api
  - direto na internet:                       https://dragonball-api.com/api
Os dois falam o MESMO formato, entao o resto do programa nem percebe a diferenca.

Para cada dado, tentamos nesta ordem:
  1. o cache em disco (se tiver menos de 24 horas)
  2. a fonte (servidor ou internet)
  3. o cache vencido
  4. o snapshot (pasta dados/), que vem junto com o programa
"""

import difflib
import threading
import time
import unicodedata
from collections import deque
from datetime import datetime

import requests

from core.armazenamento import PASTA_CACHE, PASTA_DADOS, carregar_json, salvar_json

URL_INTERNET = "https://dragonball-api.com/api"
CABECALHOS = {"User-Agent": "DragonBallDex/2.0"}
TIMEOUT = 10                                             # segundos
VALIDADE_CACHE = 24 * 60 * 60                            # 24 horas

# Para onde os pedidos vao agora (muda com usar_servidor / usar_internet)
URL_BASE = URL_INTERNET
# Ultimas requisicoes (rede ou cache). A tela "Rede" mostra esta lista.
LOG_REQUISICOES = deque(maxlen=500)
_trava_do_log = threading.Lock()
# Recados para a interface mostrar (o core nao mexe em janela)
AVISOS = []
# Ligado na tela "Rede" para simular "cabo de rede desligado"
modo_offline = False

# Uma Session reaproveita a conexao (keep-alive): bem mais rapido para varios pedidos
sessao = requests.Session()
sessao.headers.update(CABECALHOS)


class ErroDeApi(Exception):
    """Um erro que ja vem com mensagem amigavel em portugues."""


class ApiForaDoAr(ErroDeApi):
    """Sem conexao, demorou demais ou o servidor quebrou: vale a pena usar dados salvos."""


# ----------------------------------------------------------------------
# Para onde falar
# ----------------------------------------------------------------------

def usar_servidor(endereco):
    """Passa a buscar tudo no servidor do professor. endereco = '192.168.0.10:8000'."""
    global URL_BASE
    URL_BASE = f"http://{endereco}/api"


def usar_internet():
    global URL_BASE
    URL_BASE = URL_INTERNET


def conectado_ao_servidor():
    return URL_BASE != URL_INTERNET


def endereco_do_servidor():
    """'192.168.0.10:8000' (ou None se estamos usando a internet direto)."""
    if not conectado_ao_servidor():
        return None
    return URL_BASE[len("http://"):-len("/api")]


def definir_aluno(nome):
    """O nome vai em todo pedido (cabecalho X-Aluno): o painel do professor mostra quem e quem."""
    sessao.headers["X-Aluno"] = nome.encode("ascii", "ignore").decode() or "Aluno"


# ----------------------------------------------------------------------
# Registro de requisicoes
# ----------------------------------------------------------------------

def registrar(url, status, ms, tamanho, tipo, origem, metodo="GET"):
    """Anota uma requisicao no LOG_REQUISICOES (pode ser chamado de varias threads)."""
    with _trava_do_log:
        LOG_REQUISICOES.append({
            "hora": datetime.now().strftime("%H:%M:%S"),
            "metodo": metodo,
            "url": url,
            "status": status,
            "ms": ms,
            "bytes": tamanho,
            "content_type": tipo,
            "origem": origem,
        })


def copia_do_log():
    with _trava_do_log:
        return list(LOG_REQUISICOES)


def avisar_sem_conexao():
    aviso = "Sem conexão: usando dados salvos."
    if aviso not in AVISOS:
        AVISOS.append(aviso)


def pegar_avisos():
    """Entrega os avisos pendentes (e esvazia a lista)."""
    avisos = list(AVISOS)
    AVISOS.clear()
    return avisos


# ----------------------------------------------------------------------
# Falar com a fonte (servidor ou internet)
# ----------------------------------------------------------------------

def baixar(url, params=None, timeout=None):
    """Faz um GET e devolve a resposta do requests. Erros de rede viram ApiForaDoAr."""
    if modo_offline:
        raise ApiForaDoAr("Modo offline ligado: nao vou usar a rede.")
    try:
        resposta = sessao.get(url, params=params, timeout=timeout or TIMEOUT)
    except requests.Timeout:
        raise ApiForaDoAr(f"A fonte demorou mais de {timeout or TIMEOUT} segundos para responder.")
    except requests.ConnectionError:
        raise ApiForaDoAr("Sem conexao. Verifique a rede ou o servidor do professor.")
    except requests.RequestException:
        raise ErroDeApi("Nao consegui fazer o pedido.")
    ms = int(resposta.elapsed.total_seconds() * 1000)
    tipo = resposta.headers.get("Content-Type", "-")
    registrar(resposta.url, resposta.status_code, ms, len(resposta.content), tipo, "rede")
    return resposta


def pegar_json(caminho, params=None):
    """GET em um caminho ('/characters') ou URL completa. Devolve o JSON ja convertido."""
    url = caminho if caminho.startswith("http") else URL_BASE + caminho
    resposta = baixar(url, params)
    if resposta.status_code >= 500:
        raise ApiForaDoAr(f"O servidor esta com problemas (erro {resposta.status_code}).")
    try:
        resposta.raise_for_status()           # 4xx vira HTTPError
    except requests.HTTPError:
        raise ErroDeApi(f"O servidor recusou o pedido (erro {resposta.status_code}).")
    if not resposta.content:
        raise ErroDeApi("O servidor respondeu, mas sem dados.")
    try:
        return resposta.json()
    except ValueError:
        raise ErroDeApi("O servidor respondeu algo que nao e JSON.")


def extrair_itens(resposta_json):
    """A API devolve {"items": [...]} paginado OU uma lista pura quando ha filtro."""
    if isinstance(resposta_json, dict):
        return resposta_json.get("items", [])
    return resposta_json


def baixar_lista_completa(caminho):
    """Estrategia A: pede tudo de uma vez (limit=100). Se nao vier tudo, usa a estrategia B."""
    resposta = pegar_json(caminho, {"limit": 100})
    itens = extrair_itens(resposta)
    total = len(itens)
    if isinstance(resposta, dict):
        total = resposta.get("meta", {}).get("totalItems", total)
    if len(itens) >= total:
        return itens
    return baixar_pagina_por_pagina(caminho)


def baixar_pagina_por_pagina(caminho):
    """Estrategia B: pede a pagina 1 e vai seguindo o link 'next' ate ele vir vazio."""
    itens = []
    url = URL_BASE + caminho
    while url:
        resposta = pegar_json(url)
        itens.extend(extrair_itens(resposta))
        url = resposta.get("links", {}).get("next")
    return itens


# ----------------------------------------------------------------------
# Cache em disco (uma pasta para cada fonte) e snapshot
# ----------------------------------------------------------------------

def pasta_do_cache_json():
    """Cada fonte tem seu cache: as URLs das imagens do servidor sao diferentes das da internet."""
    if conectado_ao_servidor():
        nome = "servidor_" + endereco_do_servidor().replace(":", "_")
    else:
        nome = "internet"
    return PASTA_CACHE / "json" / nome


def arquivo_do_cache(nome):
    return pasta_do_cache_json() / f"{nome}.json"


def salvar_cache(nome, dados):
    salvar_json(arquivo_do_cache(nome), {"salvo_em": time.time(), "dados": dados})


def ler_cache(nome, validade=VALIDADE_CACHE):
    """Devolve os dados guardados, ou None se nao existirem ou forem mais velhos que 'validade'.
    validade=None aceita qualquer idade."""
    arquivo = arquivo_do_cache(nome)
    guardado = carregar_json(arquivo)
    if guardado is None:
        return None
    idade = time.time() - guardado["salvo_em"]
    if validade is not None and idade > validade:
        return None
    registrar(f"cache/{nome}.json", "-", 0, arquivo.stat().st_size, "application/json", "cache")
    return guardado["dados"]


def limpar_cache():
    """Apaga os JSON do cache de todas as fontes (os dados serao baixados de novo)."""
    for arquivo in (PASTA_CACHE / "json").glob("*/*.json"):
        arquivo.unlink()


def obter(nome_cache, caminho, lista_completa=False):
    """Cache valido -> fonte -> cache vencido. Se tudo falhar, levanta ApiForaDoAr."""
    dados = ler_cache(nome_cache)
    if dados is not None:
        return dados
    try:
        if lista_completa:
            dados = baixar_lista_completa(caminho)
        else:
            dados = pegar_json(caminho)
    except ApiForaDoAr:
        dados = ler_cache(nome_cache, validade=None)
        if dados is None:
            raise
        avisar_sem_conexao()
        return dados
    salvar_cache(nome_cache, dados)
    return dados


def carregar_snapshot(nome_arquivo):
    """Ultimo recurso: a fotografia dos dados que vem junto com o programa."""
    dados = carregar_json(PASTA_DADOS / nome_arquivo)
    if dados is None:
        raise ApiForaDoAr("Sem conexao e sem dados salvos.")
    avisar_sem_conexao()
    return dados


def procurar_por_id(itens, id_procurado):
    for item in itens:
        if item["id"] == id_procurado:
            return item
    raise ErroDeApi(f"Nao encontrei nada com o id {id_procurado}.")


def limpar_nomes(itens):
    """Alguns nomes vem com espaco no fim ('Grand Priest '). Tiramos esse espaco."""
    for item in itens:
        item["name"] = item["name"].strip()
    return itens


# ----------------------------------------------------------------------
# Funcoes que o resto do programa usa
# ----------------------------------------------------------------------

def listar_personagens():
    """Os 58 personagens (lista de dicionarios)."""
    try:
        itens = obter("personagens", "/characters", lista_completa=True)
    except ApiForaDoAr:
        itens = carregar_snapshot("snapshot_personagens.json")
    return limpar_nomes(itens)


def detalhar_personagem(id_personagem):
    """Um personagem com 'originPlanet' (planeta de origem) e 'transformations'."""
    try:
        detalhe = obter(f"personagem_{id_personagem}", f"/characters/{id_personagem}")
    except ApiForaDoAr:
        detalhe = procurar_por_id(carregar_snapshot("snapshot_personagens.json"), id_personagem)
    limpar_nomes([detalhe])
    return detalhe


def listar_planetas():
    """Os 20 planetas."""
    try:
        itens = obter("planetas", "/planets", lista_completa=True)
    except ApiForaDoAr:
        itens = carregar_snapshot("snapshot_planetas.json")
    return limpar_nomes(itens)


def detalhar_planeta(id_planeta):
    """Um planeta com a lista 'characters' (quem mora la)."""
    try:
        detalhe = obter(f"planeta_{id_planeta}", f"/planets/{id_planeta}")
    except ApiForaDoAr:
        detalhe = procurar_por_id(carregar_snapshot("snapshot_planetas.json"), id_planeta)
    limpar_nomes([detalhe])
    limpar_nomes(detalhe.get("characters", []))
    return detalhe


def listar_transformacoes():
    """As 43 transformacoes (a API devolve lista pura). Sem conexao: montadas a partir do snapshot."""
    try:
        return obter("transformacoes", "/transformations")
    except ApiForaDoAr:
        transformacoes = []
        for personagem in carregar_snapshot("snapshot_personagens.json"):
            transformacoes.extend(personagem.get("transformations", []))
        return transformacoes


# ----------------------------------------------------------------------
# Busca tolerante (acentos, maiusculas, pedacos do nome, erros de digitacao)
# ----------------------------------------------------------------------

def tirar_acentos(texto):
    """'Kaiō del Norte' -> 'Kaio del Norte'."""
    separado = unicodedata.normalize("NFD", texto)
    return "".join(c for c in separado if unicodedata.category(c) != "Mn")


def normalizar(texto):
    """'  Célula ' -> 'celula': sem acentos, minusculo e sem espacos nas pontas."""
    return tirar_acentos(texto).strip().lower()


def buscar_personagem(texto, personagens):
    """Devolve [o personagem com nome identico] ou [todos que CONTEM o texto] ou []."""
    procurado = normalizar(texto)
    exatos = []
    parciais = []
    for personagem in personagens:
        nome = normalizar(personagem["name"])
        if nome == procurado:
            exatos.append(personagem)
        elif procurado in nome:
            parciais.append(personagem)
    if exatos:
        return exatos
    return parciais


def sugerir_personagem(texto, personagens):
    """Para quem digitou errado: devolve o personagem de nome mais PARECIDO, ou None."""
    por_nome = {}
    for personagem in personagens:
        por_nome[normalizar(personagem["name"])] = personagem
    parecidos = difflib.get_close_matches(normalizar(texto), list(por_nome), n=1, cutoff=0.6)
    if parecidos:
        return por_nome[parecidos[0]]
    return None
