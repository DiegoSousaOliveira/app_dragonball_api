"""
Baixar imagens (com cache em disco) e prepara-las para as janelas.

Aqui so usamos o Pillow (PIL), que mexe em imagens. Nada de janela.
"""

import functools
import hashlib
import os
import random
import threading
from typing import Optional

from PIL import Image, ImageDraw

from core import api
from core.armazenamento import PASTA_CACHE, PASTA_CACHE_EMBUTIDO

PASTA_IMAGENS = PASTA_CACHE / "imagens"


def arquivo_da_imagem(url):
    """Nome do arquivo no cache: o 'md5' da URL, um codigo que e sempre o mesmo para a mesma URL."""
    codigo = hashlib.md5(url.encode("utf-8")).hexdigest()
    extensao = url.rsplit(".", 1)[-1].lower()
    return PASTA_IMAGENS / f"{codigo}.{extensao}"


def obter_arquivo(url):
    """Caminho do arquivo da imagem no disco: cache do usuario -> cache que veio no instalador ->
    download. Levanta ErroDeApi/HTTPError se nao conseguir."""
    arquivo = arquivo_da_imagem(url)
    if arquivo.exists():
        api.registrar(url, "-", 0, arquivo.stat().st_size, "image (cache)", "cache")
        return arquivo
    embutido = PASTA_CACHE_EMBUTIDO / "imagens" / arquivo.name
    if embutido.exists():
        api.registrar(url, "-", 0, embutido.stat().st_size, "image (embutida)", "cache")
        return embutido
    resposta = api.baixar(url)
    resposta.raise_for_status()
    PASTA_IMAGENS.mkdir(parents=True, exist_ok=True)
    # Grava num nome temporario e depois troca: duas threads baixando a mesma imagem nao se atrapalham
    temporario = arquivo.with_name(f"{arquivo.name}.{threading.get_ident()}.tmp")
    temporario.write_bytes(resposta.content)
    os.replace(temporario, arquivo)
    return arquivo


def baixar_imagem(url) -> Optional[Image.Image]:
    """Devolve a imagem pronta para usar. Se algo der errado, devolve None ("sem imagem")."""
    if not url:
        return None
    try:
        imagem = Image.open(obter_arquivo(url))
        imagem.load()                  # le o arquivo inteiro agora
        return imagem
    except Exception:
        # Sem conexao, erro 404, arquivo estragado, formato desconhecido...
        # Em todos os casos a resposta e a mesma: o card mostra "sem imagem".
        return None


def ajustar_contendo(imagem, largura, altura, fundo):
    """Encolhe a imagem para CABER inteira em largura x altura, apoiada no chao, sobre 'fundo'."""
    escala = min(largura / imagem.width, altura / imagem.height)
    nova = imagem.convert("RGBA").resize((round(imagem.width * escala), round(imagem.height * escala)))
    resultado = fundo.convert("RGBA").resize((largura, altura))
    x = (largura - nova.width) // 2           # centralizada na horizontal
    y = altura - nova.height                  # encostada embaixo
    resultado.alpha_composite(nova, (x, y))
    return resultado.convert("RGB")


def ajustar_cobrindo(imagem, largura, altura):
    """Amplia a imagem para COBRIR largura x altura e corta o que sobra (mantendo o topo)."""
    escala = max(largura / imagem.width, altura / imagem.height)
    nova = imagem.resize((round(imagem.width * escala), round(imagem.height * escala)))
    x = (nova.width - largura) // 2           # corta igual dos dois lados
    return nova.crop((x, 0, x + largura, altura))  # e so embaixo: a cabeca fica


@functools.lru_cache(maxsize=32)
def fundo_triangulos(largura, altura, tamanho=70):
    """Fundo claro com triangulos cinzentos, como no site da API. (Guardado em memoria: e sempre igual;
    quem usa faz uma copia com .convert().)"""
    sorteio = random.Random(7)                # mesma semente = mesmo desenho todas as vezes
    fundo = Image.new("RGB", (largura, altura), "#FFFFFF")
    desenho = ImageDraw.Draw(fundo)
    t = tamanho
    for y in range(0, altura, t):
        for x in range(0, largura, t):
            for triangulo in (((x, y), (x + t, y), (x, y + t)), ((x + t, y), (x + t, y + t), (x, y + t))):
                cinza = sorteio.randint(232, 253)
                desenho.polygon(triangulo, fill=(cinza, cinza, cinza))
    return fundo


def arredondar_cantos_de_cima(imagem, raio, cor_de_fora):
    """Arredonda os 2 cantos de cima, pintando o 'lado de fora' com cor_de_fora."""
    largura, altura = imagem.size
    # Truque: desenhamos um retangulo arredondado MAIS ALTO que a imagem e cortamos
    # a parte de baixo. Assim so os cantos de cima ficam redondos.
    mascara = Image.new("L", (largura, altura + raio), 0)
    ImageDraw.Draw(mascara).rounded_rectangle((0, 0, largura - 1, altura + raio), raio, fill=255)
    mascara = mascara.crop((0, 0, largura, altura))
    resultado = Image.new("RGB", (largura, altura), cor_de_fora)
    resultado.paste(imagem.convert("RGB"), (0, 0), mascara)
    return resultado


def imagem_lisa(largura, altura, cor):
    """Uma imagem de uma cor so (usada no lugar da foto que nao baixou)."""
    return Image.new("RGB", (largura, altura), cor)


def miniatura(imagem, largura, altura):
    """Foto pequena: a imagem COBRE o quadro (rosto e peito) sobre o fundo de triangulos."""
    coberta = ajustar_cobrindo(imagem.convert("RGBA"), largura, altura)
    fundo = fundo_triangulos(largura, altura).convert("RGBA")
    fundo.alpha_composite(coberta)
    return fundo.convert("RGB")


def foto_de_card(imagem, largura, altura):
    """A foto do card: personagem inteiro sobre o fundo de triangulos."""
    return ajustar_contendo(imagem, largura, altura, fundo_triangulos(largura, altura))


def pixelar(imagem, nivel):
    """Deixa a imagem 'quadriculada': reduz para 'nivel' quadradinhos de largura e amplia de volta.
    NEAREST amplia sem suavizar, por isso os quadradinhos aparecem."""
    largura, altura = imagem.size
    pequena = imagem.resize((nivel, max(1, round(nivel * altura / largura))))
    return pequena.resize((largura, altura), Image.NEAREST)
