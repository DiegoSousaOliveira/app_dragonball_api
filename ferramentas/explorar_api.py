"""
Explorador da Dragon Ball API.

Faz varias requisicoes e mostra no terminal o que a API devolve:
status code, tipo do conteudo, tamanho, tempo e um pedaco do JSON.

Como rodar (dentro da pasta do projeto):
    python ferramentas/explorar_api.py            -> exploracao basica (Aula 1)
    python ferramentas/explorar_api.py --completo -> todos os testes da Etapa 0
"""

import json
import socket
import sys
import time

import requests

BASE = "https://dragonball-api.com/api"
CABECALHOS = {"User-Agent": "DragonBallDex-Escola/1.0"}


def pegar(caminho, params=None):
    """Faz um GET e devolve (resposta, dados_json). Nunca quebra: em erro devolve (None, None)."""
    url = BASE + caminho
    try:
        resposta = requests.get(url, params=params, headers=CABECALHOS, timeout=10)
    except requests.RequestException as erro:
        print(f"  [ERRO DE REDE] {erro}")
        return None, None
    try:
        dados = resposta.json()
    except ValueError:
        dados = None
    return resposta, dados


def resumo(resposta):
    """Uma linha com as informacoes de rede da resposta."""
    ms = int(resposta.elapsed.total_seconds() * 1000)
    tipo = resposta.headers.get("Content-Type", "?")
    return f"status={resposta.status_code}  {ms} ms  {len(resposta.content)} bytes  {tipo}"


def mostrar(titulo, caminho, params=None, tamanho=300):
    """Faz a requisicao e imprime um resumo + o comeco do JSON."""
    print("-" * 60)
    print(titulo)
    resposta, dados = pegar(caminho, params)
    if resposta is None:
        return None
    print("  URL final:", resposta.url)
    print("  " + resumo(resposta))
    if isinstance(dados, dict):
        print("  Formato: dicionario com as chaves", list(dados.keys()))
    elif isinstance(dados, list):
        print(f"  Formato: LISTA PURA com {len(dados)} itens")
    texto = json.dumps(dados, ensure_ascii=False)
    print("  JSON:", texto[:tamanho] + ("..." if len(texto) > tamanho else ""))
    return dados


def extrair_itens(resposta_json):
    """A API devolve {"items": [...]} paginado OU uma lista pura quando ha filtro."""
    if isinstance(resposta_json, dict):
        return resposta_json.get("items", [])
    return resposta_json or []


def exploracao_basica():
    """O que os alunos rodam na Aula 1."""
    dados = mostrar("1) Primeira pagina de personagens", "/characters")
    if isinstance(dados, dict):
        print("  meta  =", dados.get("meta"))
        print("  links =", dados.get("links"))
    mostrar("2) Pagina 2", "/characters", {"page": 2})
    dados = mostrar("3) Todos de uma vez (limit=100)", "/characters", {"limit": 100}, 120)
    print("  quantidade de itens:", len(extrair_itens(dados)))
    mostrar("4) Filtro por raca (repare no FORMATO!)", "/characters", {"race": "Saiyan"}, 120)
    mostrar("5) Lista de planetas", "/planets", None, 200)


# ----------------------------------------------------------------------
# Testes completos da Etapa 0 (para o professor)
# ----------------------------------------------------------------------

def nomes(dados):
    return [p.get("name") for p in extrair_itens(dados)]


def testar_filtro_nome():
    print("=" * 60)
    print("FILTRO ?name=")
    for termo in ["Goku", "goku", "GOKU", "gok", "go", "oku", "Gokuu", "Celula", "Célula", "Freezer", "Cell", "a"]:
        resposta, dados = pegar("/characters", {"name": termo})
        if resposta is None:
            continue
        print(f"  name={termo!r:10} status={resposta.status_code} -> {nomes(dados) if dados is not None else resposta.text[:80]}")


def testar_limit_e_page():
    print("=" * 60)
    print("PAGINACAO: limit e page")
    for params in [{"limit": 58}, {"limit": 100}, {"limit": 1000}, {"limit": 0}, {"limit": -1},
                   {"limit": "abc"}, {"page": 6}, {"page": 7}, {"page": 0}, {"page": 2, "limit": 20}]:
        resposta, dados = pegar("/characters", params)
        if resposta is None:
            continue
        meta = dados.get("meta") if isinstance(dados, dict) else None
        qtd = len(extrair_itens(dados)) if dados is not None else "-"
        print(f"  {params}: status={resposta.status_code} itens={qtd} meta={meta}")
        if isinstance(dados, dict) and "links" in dados:
            print(f"      links={dados['links']}")
        if isinstance(dados, dict) and "message" in dados:
            print(f"      message={dados['message']}")


def testar_seguir_next():
    print("=" * 60)
    print("ESTRATEGIA B: seguir links.next")
    url = BASE + "/characters"
    total = 0
    paginas = 0
    while url:
        resposta = requests.get(url, headers=CABECALHOS, timeout=10)
        dados = resposta.json()
        total += len(dados.get("items", []))
        paginas += 1
        url = dados.get("links", {}).get("next")
        print(f"  pagina {paginas}: acumulado={total} next={url!r}")
        if paginas > 10:
            break


def testar_detalhes():
    print("=" * 60)
    print("DETALHE DE PERSONAGEM / PLANETA / TRANSFORMACAO")
    resposta, goku = pegar("/characters/1")
    print("  /characters/1 chaves:", list(goku.keys()))
    print("  originPlanet:", json.dumps(goku.get("originPlanet"), ensure_ascii=False)[:300])
    transf = goku.get("transformations") or []
    print(f"  transformations: {len(transf)} itens; chaves do 1o: {list(transf[0].keys()) if transf else '-'}")
    for t in transf:
        print(f"     {t.get('id')} {t.get('name')!r} ki={t.get('ki')!r} image={t.get('image')}")
    resposta, namek = pegar("/planets/1")
    print("  /planets/1 chaves:", list(namek.keys()))
    print("  moradores:", [c.get("name") for c in namek.get("characters", [])])
    print("  chaves de um morador:", list(namek["characters"][0].keys()) if namek.get("characters") else "-")
    mostrar("  /transformations", "/transformations", None, 150)
    mostrar("  /transformations/1", "/transformations/1", None, 200)
    for caminho in ["/characters/99999", "/characters/abc", "/planets/999", "/transformations/999",
                    "/rota-que-nao-existe"]:
        mostrar(f"  ERRO PROPOSITAL {caminho}", caminho, None, 200)


def coletar_todos():
    _, dados = pegar("/characters", {"limit": 100})
    return extrair_itens(dados)


def testar_valores(personagens):
    print("=" * 60)
    print(f"VALORES REAIS ({len(personagens)} personagens)")
    for campo in ["race", "affiliation", "gender"]:
        valores = sorted({str(p.get(campo)) for p in personagens})
        print(f"  {campo}: {valores}")
    print("  ids:", sorted(p["id"] for p in personagens))
    print("  deletedAt nao nulo:", [p["name"] for p in personagens if p.get("deletedAt")])
    print("  TODOS os ki/maxKi (para testar parse_ki):")
    for p in personagens:
        print(f"     {p['id']:>3} {p['name']:<22} ki={p['ki']!r:<22} maxKi={p['maxKi']!r}")
    extensoes = sorted({p["image"].rsplit(".", 1)[-1] for p in personagens if p.get("image")})
    print("  extensoes de imagem:", extensoes)
    print("  nomes com acento/espaco:", [p["name"] for p in personagens
                                         if any(ord(c) > 127 for c in p["name"]) or " " in p["name"]])


def testar_detalhe_de_todos(personagens):
    print("=" * 60)
    print("DETALHE DE CADA PERSONAGEM (planeta e transformacoes)")
    sem_planeta = []
    com_transf = []
    for p in personagens:
        _, d = pegar(f"/characters/{p['id']}")
        if not d:
            continue
        if not d.get("originPlanet"):
            sem_planeta.append(p["name"])
        if d.get("transformations"):
            com_transf.append(f"{p['name']}({len(d['transformations'])})")
    print("  sem originPlanet:", sem_planeta)
    print("  com transformacoes:", com_transf)


def testar_filtros_servidor():
    print("=" * 60)
    print("FILTROS NO SERVIDOR")
    for params in [{"race": "Saiyan"}, {"race": "saiyan"}, {"race": "Saiyan", "affiliation": "Z fighter"},
                   {"affiliation": "Z Fighter"}, {"gender": "Female"}, {"race": "Inexistente"},
                   {"race": "Saiyan", "page": 2}, {"race": "Saiyan", "limit": 2}]:
        resposta, dados = pegar("/characters", params)
        if resposta is None:
            continue
        formato = "dict" if isinstance(dados, dict) else "lista"
        print(f"  {params}: status={resposta.status_code} formato={formato} -> {nomes(dados)}")
    for params in [{"isDestroyed": "true"}, {"name": "namek"}]:
        resposta, dados = pegar("/planets", params)
        formato = "dict" if isinstance(dados, dict) else "lista"
        print(f"  /planets {params}: status={resposta.status_code} formato={formato} -> {nomes(dados)}")


def testar_cabecalhos_e_limite():
    print("=" * 60)
    print("CABECALHOS E LIMITE DE REQUISICOES")
    resposta, _ = pegar("/characters")
    for chave, valor in resposta.headers.items():
        print(f"  {chave}: {valor}")
    print("  Disparando 40 requisicoes seguidas (com Session) para procurar 429...")
    sessao = requests.Session()
    sessao.headers.update(CABECALHOS)
    codigos = {}
    inicio = time.perf_counter()
    for _ in range(40):
        r = sessao.get(BASE + "/planets", timeout=10)
        codigos[r.status_code] = codigos.get(r.status_code, 0) + 1
        limite = {k: v for k, v in r.headers.items() if "limit" in k.lower() or "retry" in k.lower()}
    print(f"  codigos: {codigos}  em {time.perf_counter() - inicio:.1f}s; cabecalhos de limite: {limite}")


def testar_rede():
    print("=" * 60)
    print("REDE")
    print("  IP de dragonball-api.com:", socket.gethostbyname("dragonball-api.com"))
    try:
        requests.get(BASE + "/characters", timeout=0.001)
    except requests.RequestException as erro:
        print("  timeout=0.001 ->", type(erro).__name__)
    r = requests.get("https://web.dragonball-api.com/documentation", headers=CABECALHOS, timeout=10)
    print(f"  documentacao: status={r.status_code} bytes={len(r.content)} (pagina montada por JS?)")


def exploracao_completa():
    exploracao_basica()
    testar_filtro_nome()
    testar_limit_e_page()
    testar_seguir_next()
    testar_detalhes()
    personagens = coletar_todos()
    testar_valores(personagens)
    testar_detalhe_de_todos(personagens)
    testar_filtros_servidor()
    testar_cabecalhos_e_limite()
    testar_rede()


if __name__ == "__main__":
    if "--completo" in sys.argv:
        exploracao_completa()
    else:
        exploracao_basica()
