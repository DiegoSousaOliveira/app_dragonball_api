"""Filtrar e ordenar listas de personagens (sem internet, sem print: so logica)."""

from core.api import normalizar
from core.poder import parse_ki


def valores_unicos(personagens, campo):
    """Todos os valores DIFERENTES de um campo, em ordem alfabetica.
    O set (conjunto) joga fora as repeticoes: {'Saiyan', 'Saiyan', 'Human'} -> {'Saiyan', 'Human'}."""
    return sorted(set(personagem[campo] for personagem in personagens))


def filtrar(personagens, nome="", raca=None, afiliacao=None, genero=None):
    """Aplica so os filtros que foram preenchidos."""
    achados = personagens
    if nome:
        # list comprehension: "a lista de p, para cada p em achados, SE o nome contem o texto"
        achados = [p for p in achados if normalizar(nome) in normalizar(p["name"])]
    if raca:
        achados = [p for p in achados if p["race"] == raca]
    if afiliacao:
        achados = [p for p in achados if p["affiliation"] == afiliacao]
    if genero:
        achados = [p for p in achados if p["gender"] == genero]
    return achados


def montar_ranking(personagens, metrica="maxKi", quantos=10, raca=None):
    """Os 'quantos' mais fortes. Devolve (ranking, ignorados).
    ranking = [(personagem, ki), ...]; ignorados = quantos ficaram de fora por ter ki 0/desconhecido."""
    candidatos = filtrar(personagens, raca=raca)
    com_ki = [(p, parse_ki(p[metrica])) for p in candidatos]
    validos = [par for par in com_ki if par[1] > 0]
    ignorados = len(com_ki) - len(validos)
    validos = sorted(validos, key=lambda par: par[1], reverse=True)
    return validos[:quantos], ignorados


def ordenar(personagens, criterio="nome"):
    """criterio: 'nome' (A-Z), 'ki' ou 'maxKi' (do mais forte para o mais fraco)."""
    if criterio == "nome":
        return sorted(personagens, key=lambda p: normalizar(p["name"]))
    # key diz "ordene olhando para ISTO": o ki convertido em numero
    return sorted(personagens, key=lambda p: parse_ki(p[criterio]), reverse=True)
