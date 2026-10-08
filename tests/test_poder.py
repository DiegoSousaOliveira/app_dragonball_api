"""Testes do core/poder.py. Todos os textos de ki abaixo existem de verdade na API."""

from core.poder import escala_log, forca_de_batalha, formatar_ki, parse_ki

# (entrada, saida esperada)
CASOS_PARSE_KI = [
    ("60.000.000", 60_000_000),
    ("450.000", 450_000),
    ("20.000", 20_000),
    ("250.000.000", 250_000_000),
    ("0", 0),
    ("5 Billion", 5_000_000_000),
    ("250 Billion", 250 * 10**9),
    ("34.8 Billion", 34_800_000_000),
    ("90 Septillion", 90 * 10**24),
    ("19.84 Septillion", 1984 * 10**22),
    ("40 septillion", 40 * 10**24),          # minusculo
    ("37.4 septllion", 374 * 10**23),        # erro de digitacao da propria API
    (None, 0),
    ("", 0),
    ("???", 0),
    # Casos extras encontrados na Etapa 0
    ("160,000,000", 160_000_000),            # virgula como separador de milhar
    ("42.000 ", 42_000),                     # espaco sobrando no fim
    ("unknown", 0),                          # 10 personagens tem ki desconhecido
    ("7 quadrillion", 7 * 10**15),
    ("969 Googolplex", 969 * 10**100),       # Grand Priest: googolplex vira googol (teto)
]


def test_parse_ki_tabela():
    for entrada, esperado in CASOS_PARSE_KI:
        resultado = parse_ki(entrada)
        assert resultado == esperado, f"parse_ki({entrada!r}) deu {resultado}, esperado {esperado}"


def test_parse_ki_devolve_int():
    assert type(parse_ki("19.84 Septillion")) is int


def test_formatar_ki():
    assert formatar_ki(0) == "0"
    assert formatar_ki(450_000) == "450.000"
    assert formatar_ki(90 * 10**24) == "9.0 x 10^25"
    assert formatar_ki(60_000_000) == "6.0 x 10^7"


def test_forca_de_batalha():
    assert forca_de_batalha(0) == 1.0                    # Bulma ainda luta
    assert round(forca_de_batalha(60_000_000), 2) == 7.78
    assert round(forca_de_batalha(90 * 10**24), 2) == 25.95


def test_escala_log():
    assert escala_log(10**25, 10**25) == 1.0
    assert escala_log(10**5, 10**25) == 0.2          # 5 algarismos de 25
    assert escala_log(0, 10**25) == 0.0
