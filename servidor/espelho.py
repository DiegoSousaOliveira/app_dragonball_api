"""
Espelho da dragonball-api: o servidor do professor entrega os MESMOS dados para os alunos.

Os dados vem do core.api (internet -> cache -> snapshot), entao o servidor funciona mesmo se
o laboratorio estiver sem internet. As URLs das imagens sao trocadas pelas do proprio servidor:
    https://dragonball-api.com/characters/goku_normal.webp
 -> http://192.168.0.10:8000/imagens/characters/goku_normal.webp
"""

import math
import threading
import time
from urllib.parse import quote, unquote

from core import api, imagens

URL_IMAGENS_ORIGINAL = "https://dragonball-api.com/"
EXTENSOES_DE_IMAGEM = {"webp": "image/webp", "png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg"}
VALIDADE_NA_MEMORIA = 10 * 60          # segundos


class Espelho:
    def __init__(self):
        self._memoria = {}               # chave -> (horario, dados)
        self._travas = {}                # uma trava para cada chave
        self._trava_geral = threading.Lock()
        self.sem_internet = False        # o painel mostra se os dados vieram de "dados salvos"

    def _trava_da(self, chave):
        with self._trava_geral:
            return self._travas.setdefault(chave, threading.Lock())

    def _obter(self, chave, buscar):
        """Guarda na memoria por 10 minutos: 30 alunos pedindo a lista = 1 busca so.
        A trava e por chave: enquanto um dado demora, os outros continuam sendo entregues."""
        with self._trava_da(chave):
            guardado = self._memoria.get(chave)
            if guardado and time.time() - guardado[0] < VALIDADE_NA_MEMORIA:
                return guardado[1]
            dados = buscar()
            if api.pegar_avisos():
                self.sem_internet = True
            self._memoria[chave] = (time.time(), dados)
            return dados

    def esquecer(self):
        """Apaga a memoria (o proximo pedido busca de novo)."""
        with self._trava_geral:
            self._memoria.clear()

    # ---------------- os dados ----------------

    def personagens(self):
        return self._obter("personagens", api.listar_personagens)

    def planetas(self):
        return self._obter("planetas", api.listar_planetas)

    def transformacoes(self):
        return self._obter("transformacoes", api.listar_transformacoes)

    def detalhe_personagem(self, id_personagem):
        """O detalhe, ou None se o id nao existe."""
        if not any(p["id"] == id_personagem for p in self.personagens()):
            return None
        return self._obter(f"personagem_{id_personagem}", lambda: api.detalhar_personagem(id_personagem))

    def detalhe_planeta(self, id_planeta):
        if not any(p["id"] == id_planeta for p in self.planetas()):
            return None
        return self._obter(f"planeta_{id_planeta}", lambda: api.detalhar_planeta(id_planeta))

    def arquivo_de_imagem(self, caminho):
        """'characters/goku_normal.webp' -> arquivo no disco (baixa se precisar). None = nao pode."""
        caminho = unquote(caminho)
        extensao = caminho.rsplit(".", 1)[-1].lower()
        if ".." in caminho or caminho.startswith("/") or extensao not in EXTENSOES_DE_IMAGEM:
            return None, None                       # so imagens da dragonball-api, nada de outros arquivos
        try:
            return imagens.obter_arquivo(URL_IMAGENS_ORIGINAL + caminho), EXTENSOES_DE_IMAGEM[extensao]
        except Exception:
            return None, None

    def preaquecer(self, progresso=None):
        """Baixa todos os dados e imagens agora (para o laboratorio sem internet).
        progresso(feitos, total, texto) e chamado a cada passo."""
        personagens = self.personagens()
        planetas = self.planetas()
        detalhes = []
        for numero, personagem in enumerate(personagens, start=1):
            detalhes.append(self.detalhe_personagem(personagem["id"]))
            if progresso:
                progresso(numero, len(personagens), "dados dos personagens")
        for planeta in planetas:
            self.detalhe_planeta(planeta["id"])
        urls = [p["image"] for p in personagens] + [p["image"] for p in planetas]
        for detalhe in detalhes:
            urls += [t["image"] for t in detalhe.get("transformations", [])]
        falhas = 0
        for numero, url in enumerate(urls, start=1):
            try:
                imagens.obter_arquivo(url)
            except Exception:
                falhas += 1
            if progresso:
                progresso(numero, len(urls), "imagens")
        return len(urls), falhas


# ----------------------------------------------------------------------
# Imitando a API original: filtros, paginacao e imagens
# ----------------------------------------------------------------------

FILTROS_PERSONAGEM = ("name", "race", "affiliation", "gender")
FILTROS_PLANETA = ("name", "isDestroyed")


def tem_filtro(params, filtros):
    return any(params.get(chave) for chave in filtros)


def filtrar(itens, params, filtros):
    """Como a API original: 'name' busca um PEDACO do nome; os outros comparam o valor inteiro.
    Tudo sem diferenciar maiusculas e acentos."""
    achados = itens
    for chave in filtros:
        valor = params.get(chave)
        if not valor:
            continue
        procurado = api.normalizar(valor)
        if chave == "name":
            achados = [i for i in achados if procurado in api.normalizar(i["name"])]
        else:
            achados = [i for i in achados if api.normalizar(str(i.get(chave, ""))) == procurado]
    return achados


def _inteiro(texto, padrao):
    try:
        return int(texto)
    except (TypeError, ValueError):
        return padrao


def paginar(itens, params, url_da_lista):
    """Monta {"items", "meta", "links"} igual a dragonball-api (limit maximo 100)."""
    limite = _inteiro(params.get("limit"), 10)
    if limite < 1:
        limite = 10
    limite = min(limite, 100)
    pagina = max(1, _inteiro(params.get("page"), 1))
    total = len(itens)
    paginas = max(1, math.ceil(total / limite))
    fatia = itens[(pagina - 1) * limite: pagina * limite]

    def link(numero):
        return f"{url_da_lista}?page={numero}&limit={limite}"

    return {
        "items": fatia,
        "meta": {"totalItems": total, "itemCount": len(fatia), "itemsPerPage": limite,
                 "totalPages": paginas, "currentPage": pagina},
        "links": {"first": f"{url_da_lista}?limit={limite}",
                  "previous": link(pagina - 1) if pagina > 1 else "",
                  "next": link(pagina + 1) if pagina < paginas else "",
                  "last": link(paginas)},
    }


def trocar_url_de_imagem(url, base_imagens):
    if isinstance(url, str) and url.startswith(URL_IMAGENS_ORIGINAL):
        return base_imagens + quote(url[len(URL_IMAGENS_ORIGINAL):], safe="/")
    return url


def reescrever_imagens(dados, base_imagens):
    """Copia os dados trocando TODA chave 'image' (inclusive dentro de planetas e transformacoes)."""
    if isinstance(dados, dict):
        return {chave: (trocar_url_de_imagem(valor, base_imagens) if chave == "image"
                        else reescrever_imagens(valor, base_imagens))
                for chave, valor in dados.items()}
    if isinstance(dados, list):
        return [reescrever_imagens(item, base_imagens) for item in dados]
    return dados
