"""
Transforma o ki (que a API manda como TEXTO) em numero, e de volta em texto bonito.

Exemplos de ki reais da API: "60.000.000", "90 Septillion", "37.4 septllion", "unknown".
"""

import difflib
import math
from decimal import Decimal

# Escala curta (a usada em ingles): cada degrau multiplica por 1000.
ESCALAS = {
    "million": 10**6,
    "billion": 10**9,
    "trillion": 10**12,
    "quadrillion": 10**15,
    "quintillion": 10**18,
    "sextillion": 10**21,
    "septillion": 10**24,
    "googol": 10**100,
    # Um googolplex e 10 elevado a um googol: tem mais algarismos do que atomos no universo.
    # Nem o Python consegue guardar esse numero, entao usamos um googol como "teto".
    "googolplex": 10**100,
}


def pegar_numero(texto: str) -> str:
    """Pega o primeiro numero que aparece no texto: '19.84 septillion' -> '19.84'."""
    numero = ""
    for caractere in texto:
        if caractere.isdigit() or (numero and caractere in ".,"):
            numero += caractere
        elif numero:
            break
    return numero.rstrip(".,")


def descobrir_escala(texto: str) -> int:
    """Procura uma palavra de escala ('billion'...) no texto. Devolve o multiplicador, ou 0."""
    for palavra in texto.split():
        # get_close_matches aceita palavras PARECIDAS: 'septllion' ~ 'septillion'
        parecidas = difflib.get_close_matches(palavra, ESCALAS, n=1, cutoff=0.7)
        if parecidas:
            return ESCALAS[parecidas[0]]
    return 0


def parse_ki(texto) -> int:
    """Converte o ki da API em numero inteiro. Texto vazio ou sem numero vira 0."""
    if not texto:
        return 0
    texto = str(texto).strip().lower()
    numero = pegar_numero(texto)
    if not numero:
        return 0                      # ex.: "unknown"
    escala = descobrir_escala(texto)
    if escala == 0:
        # Sem palavra de escala, "." e "," separam milhares: "60.000.000" = 60 milhoes
        return int(numero.replace(".", "").replace(",", ""))
    # Com palavra de escala, "." e a virgula decimal: "19.84 Septillion" = 19,84 x 10^24
    # Decimal faz a conta exata (float erraria os ultimos algarismos)
    return int(Decimal(numero.replace(",", ".")) * escala)


def formatar_ki(ki: int) -> str:
    """Numero -> texto curto. 450000 -> '450.000'; 9*10**25 -> '9.0 x 10^25'."""
    if ki < 10**6:
        return f"{ki:,}".replace(",", ".")
    expoente = len(str(ki)) - 1           # quantos algarismos depois do primeiro
    mantissa = ki / 10**expoente          # um numero entre 1 e 10
    return f"{mantissa:.1f} x 10^{expoente}"


def escala_log(ki: int, maior: int) -> float:
    """Tamanho da barra do ranking (0.0 a 1.0) em escala de LOGARITMO.
    Em escala normal, so o maior apareceria: os outros seriam barras invisiveis."""
    if ki <= 1 or maior <= 1:
        return 0.0
    return math.log10(ki) / math.log10(maior)


def forca_de_batalha(ki: int) -> float:
    """Converte o ki (numero enorme) numa escala pequena. Minimo 1 para ninguem ter forca zero."""
    return max(1.0, math.log10(ki + 1))
