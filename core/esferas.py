"""
Caca as Esferas do Dragao: a logica (sem rede e sem janela).

Como funciona:
  1. o professor clica em "Iniciar cacada"; cada aluno vira um CACADOR com um numero curto (1, 2, 3...)
  2. cada esfera tem um CODIGO PESSOAL (ex.: ESF-7KQ2M), calculado com HMAC a partir de um segredo da
     cacada e do numero do cacador: o codigo de um colega nao serve para voce
  3. cada esfera exige um conceito de Redes para ser achada (as rotas ficam em servidor/rotas_esferas.py)
  4. o aluno digita o codigo no app para resgatar a esfera; quem junta as 7 invoca o dragao e faz um pedido
O placar da cacada e SEPARADO do placar da turma. Tudo fica na memoria, protegido por uma trava (Lock):
cada aluno e atendido numa thread diferente.
"""

import csv
import hashlib
import hmac
import json
import secrets
import threading
import time
import unicodedata
from collections import deque
from contextlib import contextmanager
from datetime import datetime

from core.armazenamento import PASTA_USUARIO

ALFABETO = "23456789ABCDEFGHJKMNPQRSTUVWXYZ"   # sem 0/O e 1/I/L: ninguem confunde ao digitar
PREFIXO = "ESF-"
TAMANHO_DO_CODIGO = 5
PALAVRA_MAGICA = "KAMEHAMEHA"
PLANETA_DA_CAVERNA = "namek"                   # o planeta de origem do Piccolo (dados/snapshot_personagens.json)
LADO_DO_RADAR = 10                             # coordenadas x e y vao de 0 a 10
INTERVALO_RESGATE = 2.0                        # segundos entre duas tentativas de resgate (contra chute em massa)
TEMPO_DO_PEDIDO = 30                           # segundos para escolher o pedido; depois vale o primeiro
INTERVALO_DO_GRITO = 3                         # o telao mostra no maximo 1 grito de cada cacador nesse tempo
BONUS_ORDEM = {1: 5, 2: 3, 3: 2}               # bonus para os 3 primeiros que juntam as 7
PASTA_DOS_RESULTADOS = PASTA_USUARIO / "cacadas"

# {endereco} = IP:PORTA do servidor e {numero} = numero do cacador (preenchidos na hora de mostrar).
# As dicas extras vao pelo aviso do chat, que corta em 200 caracteres: os testes conferem o tamanho.
ESFERAS = {
    1: {"conceito": "IP + porta",
        "dica": "Você usou um endereço IP e uma porta para chegar aqui. Isso já vale a 1ª esfera!",
        "aprendeu": "Você usou um endereço IP e uma porta para chegar aqui. Isso já vale a 1ª esfera! "
                    "O IP diz QUAL computador; a porta diz QUAL programa dentro dele.",
        "extra": "💡 Esfera 1: é automática! Basta estar conectado ao servidor da sala. Quem chegou depois "
                 "ganha a esfera ao abrir a tela 🐉 Esferas."},
    2: {"conceito": "User-Agent",
        "dica": "O servidor da sala também conversa com navegadores! Abra o Chrome ou o Edge, digite "
                "http://{endereco} e procure algo escondido na página. 🕵️",
        "aprendeu": "Todo programa que fala HTTP se apresenta no cabeçalho User-Agent. O servidor percebeu "
                    "que era um navegador, e não o app!",
        "extra": "💡 Esfera 2: no navegador, abra http://{endereco} e olhe o fim da página: tem um link bem "
                 "discreto. Lá dentro, digite o seu número de caçador."},
    3: {"conceito": "Cabeçalhos",
        "dica": "Deixaram uma pista em /esferas/pista. Na tela 📡 Rede → Testar, escolha /esferas/pista e "
                "clique em Enviar GET. A esfera não vem no corpo... leia com atenção TUDO o que voltou! 👀",
        "aprendeu": "Uma resposta HTTP tem cabeçalhos (informações extras) além do corpo. O código veio "
                    "escondido no cabeçalho X-Esfera.",
        "extra": "💡 Esfera 3: na tela Rede → Testar, escolha /esferas/pista. O código está nos Cabeçalhos "
                 "da resposta, na linha que começa com X-Esfera."},
    4: {"conceito": "Query string",
        "dica": "O Radar do Dragão diz se você está perto! No navegador, abra "
                "http://{endereco}/esferas/radar?cacador={numero}&x=5&y=5 e vá mudando x e y (de 0 a 10) "
                "até achar a esfera. ❄️ Frio... 🔥 Quente!",
        "aprendeu": "O que vem depois do ? na URL é a query string: são os parâmetros do pedido. Quando eles "
                    "estão errados, o servidor responde 400 (pedido mal feito).",
        "extra": "💡 Esfera 4: tudo depois do ? na URL é a query string. Mude só o x até esquentar; depois, "
                 "só o y. 🔥🔥 Fervendo = falta só 1 passo!"},
    5: {"conceito": "404 com corpo",
        "dica": "O Piccolo escondeu uma esfera numa caverna do planeta onde ele nasceu. Descubra o planeta "
                "na tela 🔎 Personagens e abra no navegador: "
                "http://{endereco}/esferas/caverna-NOMEDOPLANETA?cacador={numero} · Não desista se der erro! 💎",
        "aprendeu": "O status 404 quer dizer \"não encontrado\", mas a resposta ainda pode ter corpo. Sempre "
                    "leia tudo o que o servidor mandou!",
        "extra": "💡 Esfera 5: o Piccolo nasceu em Namek, então a caverna é caverna-namek. A resposta vem com "
                 "status 404 (não encontrado)... mas leia o corpo até o fim!"},
    6: {"conceito": "Broadcast UDP",
        "dica": "Grite a palavra mágica para a rede inteira! Aqui embaixo, em \"Grito na rede\", escreva o "
                "nome do golpe mais famoso do Goku e clique em 📡 Gritar na rede. Só o servidor vai "
                "responder. 📣",
        "aprendeu": "Broadcast é uma mensagem para TODOS os computadores da rede de uma vez (UDP, porta "
                    "50505). É assim que o app acha o servidor sozinho!",
        "extra": "💡 Esfera 6: a palavra mágica é KAMEHAMEHA. Se ninguém responder, a rede bloqueia gritos "
                 "(broadcast): marque \"Mandar direto para o servidor\" e grite de novo."},
    7: {"conceito": "Terminal",
        "dica": "A última esfera não aceita o app nem o navegador! Abra o Prompt de Comando (tecla Windows, "
                "digite cmd) e escreva: curl http://{endereco}/esferas/terminal?cacador={numero}",
        "aprendeu": "O curl é um programa de terminal que fala HTTP, igual ao navegador e ao app. HTTP é um "
                    "padrão: qualquer programa pode usar!",
        "extra": "💡 Esfera 7: use o cmd (Prompt de Comando), não o PowerShell. Escreva curl, um espaço e o "
                 "endereço inteiro. Se aparecer \"curl não é reconhecido\", chame o professor."},
}

PEDIDOS = {
    1: "+3 pontos na caçada para mim",
    2: "+1 ponto na caçada para todos da turma",
    3: "Ser o ajudante do professor na próxima atividade",
}

MENSAGENS_PARADA = {
    "aguardando": "A caçada ainda não começou 🐉",
    "pausada": "A caçada está pausada pelo professor ⏸",
    "encerrada": "A caçada terminou! 🏁",
}

# O grito vai por UDP na porta da descoberta (50505). Os prefixos sao DIFERENTES da pergunta
# "DRAGONBALLDEX?" e a resposta NAO e JSON puro: um app 2.2 que receba isso simplesmente ignora.
PREFIXO_GRITO = b"DBDEX-ESFERA "
PREFIXO_RESPOSTA = b"DBDEX-ESFERA-RESPOSTA "


# ----------------------------------------------------------------------
# Erros (cada um ja diz qual status HTTP o servidor deve responder)
# ----------------------------------------------------------------------

class ErroDaCacada(Exception):
    """Pedido que nao faz sentido (codigo errado, numero que nao existe...)."""
    status = 400


class CacadaParada(ErroDaCacada):
    """A cacada nao comecou, esta pausada ou terminou."""
    status = 409


class DeOutroCacador(ErroDaCacada):
    """O codigo existe, mas e de um colega."""
    status = 403


class Devagar(ErroDaCacada):
    """Tentou resgatar antes de passar 2 segundos."""
    status = 429


# ----------------------------------------------------------------------
# Codigos, radar e textos (funcoes puras: facil de testar)
# ----------------------------------------------------------------------

def _resumo(segredo, mensagem):
    return hmac.new(segredo.encode("utf-8"), mensagem.encode("utf-8"), hashlib.sha256).digest()


def gerar_codigo(segredo, numero, esfera):
    """HMAC(segredo, "7:3") -> 'ESF-7KQ2M'. Sem o segredo, ninguem consegue calcular o codigo de ninguem."""
    valor = int.from_bytes(_resumo(segredo, f"{numero}:{esfera}")[:8], "big")
    letras = ""
    for _ in range(TAMANHO_DO_CODIGO):
        valor, resto = divmod(valor, len(ALFABETO))
        letras += ALFABETO[resto]
    return PREFIXO + letras


def normalizar_codigo(texto):
    """' esf-7kq2m ' -> 'ESF-7KQ2M'. Ignora maiusculas, espacos e o prefixo. None se nao parece um codigo."""
    if not isinstance(texto, str):
        return None
    limpo = "".join(texto.upper().split()).replace("-", "")
    if len(limpo) == len("ESF") + TAMANHO_DO_CODIGO and limpo.startswith("ESF"):
        limpo = limpo[len("ESF"):]
    if len(limpo) != TAMANHO_DO_CODIGO or any(letra not in ALFABETO for letra in limpo):
        return None
    return PREFIXO + limpo


def alvo_do_radar(segredo, numero):
    """As coordenadas (x, y) da esfera 4 deste cacador: cada um tem as suas."""
    resumo = _resumo(segredo, f"{numero}:radar")
    return resumo[0] % (LADO_DO_RADAR + 1), resumo[1] % (LADO_DO_RADAR + 1)


def temperatura(distancia):
    """Distancia = passos na horizontal + passos na vertical ate a esfera."""
    if distancia <= 1:
        return "🔥🔥 Fervendo!"
    if distancia <= 3:
        return "🔥 Quente"
    if distancia <= 6:
        return "🌤 Morno"
    return "❄️ Frio"


def _so_letras(texto):
    """'Kame-hamê-ha!' -> 'kamehameha': sem acentos, sem espacos e sem pontuacao."""
    separado = unicodedata.normalize("NFD", texto or "")
    return "".join(c for c in separado if c.isascii() and c.isalnum()).lower()


def eh_a_palavra_magica(texto):
    return _so_letras(texto) == PALAVRA_MAGICA.lower()


def eh_a_caverna_certa(nome):
    """'Namek', 'namék', 'NAMEK' -> True."""
    return _so_letras(nome) == PLANETA_DA_CAVERNA


def eh_navegador(user_agent):
    """Todo navegador diz 'Mozilla' no User-Agent. O app diz 'DragonBallDex/2.0'; o PowerShell tambem
    diz 'Mozilla', mas se entrega com 'WindowsPowerShell'."""
    ua = user_agent or ""
    return "Mozilla" in ua and not any(p in ua for p in ("DragonBallDex", "python-requests", "PowerShell", "curl"))


def eh_terminal(user_agent):
    """curl.exe (Windows 10+) diz 'curl/8.x'; no PowerShell, 'curl' e o Invoke-WebRequest."""
    ua = user_agent or ""
    return ua.startswith("curl/") or "PowerShell" in ua


def preencher(texto, endereco, numero):
    return texto.format(endereco=endereco or "IP:PORTA", numero=numero)


def hora(instante):
    return datetime.fromtimestamp(instante).strftime("%H:%M")


# ---------------- o grito (UDP) ----------------

def montar_grito(numero, palavra):
    return PREFIXO_GRITO + f"{numero} {palavra}".encode("utf-8")


def ler_grito(dados):
    """b'DBDEX-ESFERA 7 KAMEHAMEHA' -> (7, 'KAMEHAMEHA'). Qualquer outra coisa -> None."""
    if not dados.startswith(PREFIXO_GRITO):
        return None
    try:
        partes = dados[len(PREFIXO_GRITO):].decode("utf-8").split(None, 1)
    except UnicodeDecodeError:
        return None
    if not partes or not (partes[0].isascii() and partes[0].isdigit()) or len(partes[0]) > 6:
        return None
    return int(partes[0]), (partes[1] if len(partes) > 1 else "")[:40]


def montar_resposta_grito(resposta):
    return PREFIXO_RESPOSTA + json.dumps(resposta, ensure_ascii=False).encode("utf-8")


def ler_resposta_grito(dados):
    if not dados.startswith(PREFIXO_RESPOSTA):
        return None
    try:
        resposta = json.loads(dados[len(PREFIXO_RESPOSTA):].decode("utf-8"))
    except ValueError:
        return None
    return resposta if isinstance(resposta, dict) else None


# ----------------------------------------------------------------------
# A cacada
# ----------------------------------------------------------------------

class Cacador:
    def __init__(self, numero, id_jogador, nome):
        self.numero = numero
        self.id = id_jogador
        self.nome = nome or f"Caçador {numero}"
        self.achadas = {}            # esfera -> horario em que foi resgatada
        self.ultima_tentativa = 0.0
        self.ultimo_grito = 0.0
        self.posicao = None          # 1, 2, 3... (ordem em que juntou as 7)
        self.pedido = None           # 1, 2 ou 3
        self.pedido_ate = None       # horario limite para escolher o pedido
        self.bonus_pedido = 0

    def pontos(self):
        return len(self.achadas) + BONUS_ORDEM.get(self.posicao, 0) + self.bonus_pedido


class Cacada:
    """Estados: aguardando -> ativa <-> pausada -> encerrada. 'Nova cacada' volta para aguardando.

    avisar(texto): funcao chamada para avisar a turma (o servidor usa o aviso do professor no chat).
    relogio(): de onde vem a hora (os testes passam um relogio falso para nao precisar esperar)."""

    def __init__(self, avisar=None, relogio=time.time):
        self._trava = threading.Lock()
        self.avisar = avisar or (lambda texto: None)
        self.relogio = relogio
        self.numeros = {}            # id do jogador (X-Jogador) -> numero de cacador (fica de uma cacada para outra)
        self._proximo_numero = 1
        self._eventos = deque(maxlen=300)
        self._proximo_evento = 1
        self._avisos = []
        self._zerar()

    def _zerar(self):
        self.segredo = secrets.token_hex(16)
        self.estado = "aguardando"
        self.cacadores = {}          # numero -> Cacador
        self._codigos = {}           # numero -> {codigo: esfera} (calculados uma vez so)
        self.duracao = None          # segundos (None = sem limite de tempo)
        self.fim_previsto = None
        self.pausada_em = None
        self.concluidos = 0
        self.dicas_extras = set()
        self.resultado_salvo = None  # caminho do CSV, depois de encerrar

    @contextmanager
    def _mexendo(self):
        """Toda operacao passa por aqui: trava, poe o relogio em dia (fim do tempo, pedidos vencidos) e, no
        fim, entrega os avisos para o chat FORA da trava (assim o chat nunca fica esperando a cacada)."""
        self._trava.acquire()
        try:
            agora = self.relogio()
            self._atualizar(agora)
            yield agora
        finally:
            avisos, self._avisos = self._avisos, []
            self._trava.release()
            for texto in avisos:
                try:
                    self.avisar(texto)
                except Exception:
                    pass

    # ---------------- relogio ----------------

    def _atualizar(self, agora):
        if self.estado != "ativa":
            return
        for cacador in self.cacadores.values():
            if cacador.pedido is None and cacador.pedido_ate is not None and agora >= cacador.pedido_ate:
                self._aplicar_pedido(cacador, 1, agora, automatico=True)
        if self.fim_previsto is not None and agora >= self.fim_previsto:
            self._encerrar(agora, "tempo")

    def _tempo_restante(self, agora):
        if self.fim_previsto is None:
            return self.duracao if self.estado == "aguardando" else None
        if self.estado == "pausada":
            return max(0, int(self.fim_previsto - self.pausada_em))
        if self.estado == "encerrada":
            return 0
        return max(0, int(self.fim_previsto - agora))

    # ---------------- eventos (o painel le e mostra no telao) ----------------

    def _evento(self, tipo, agora, **dados):
        dados.update(id=self._proximo_evento, tipo=tipo, hora=hora(agora))
        self._proximo_evento += 1
        self._eventos.append(dados)

    def eventos_depois(self, id_evento):
        with self._trava:
            return [dict(e) for e in self._eventos if e["id"] > id_evento]

    # ---------------- cacadores ----------------

    def _inscrever(self, id_jogador, nome, agora, criar=True):
        """O cacador deste aluno (cria na primeira vez). Quem chega com a cacada rolando ganha a esfera 1."""
        numero = self.numeros.get(id_jogador)
        if numero is None:
            numero = self._proximo_numero
            self._proximo_numero += 1
            self.numeros[id_jogador] = numero
        cacador = self.cacadores.get(numero)
        if cacador is None:
            cacador = Cacador(numero, id_jogador, nome)
            if not criar:
                return cacador       # so para mostrar (nao entra na cacada que ja terminou)
            self.cacadores[numero] = cacador
            if self.estado in ("ativa", "pausada"):
                self._achou(cacador, 1, agora)
        if nome:
            cacador.nome = nome
        return cacador

    def inscrever(self, id_jogador, nome):
        """Devolve o numero de cacador do aluno (as rotas usam quando o pedido vem do app, com X-Jogador)."""
        with self._mexendo() as agora:
            return self._inscrever(id_jogador, nome, agora, criar=self.estado != "encerrada").numero

    def _exigir_ativa(self):
        if self.estado != "ativa":
            raise CacadaParada(MENSAGENS_PARADA[self.estado])

    def exigir_ativa(self):
        """CacadaParada (409) se a cacada nao comecou, esta pausada ou terminou."""
        with self._mexendo():
            self._exigir_ativa()

    def _cacador_pelo_numero(self, numero):
        cacador = self.cacadores.get(numero)
        if cacador is None:
            raise ErroDaCacada(f"Não existe caçador com o número {numero}. Confira o seu número na tela "
                               "🐉 Esferas do app.")
        return cacador

    def _codigos_de(self, numero):
        if numero not in self._codigos:
            self._codigos[numero] = {gerar_codigo(self.segredo, numero, n): n for n in ESFERAS}
        return self._codigos[numero]

    # ---------------- comandos do professor (painel) ----------------

    def iniciar(self, alunos=(), minutos=None):
        """alunos = [(id_do_jogador, nome), ...]: quem esta online na sala ganha numero e a esfera 1."""
        with self._mexendo() as agora:
            if self.estado != "aguardando":
                raise ErroDaCacada("A caçada já começou. Use \"Nova caçada\" para começar outra.")
            self.estado = "ativa"
            self.duracao = int(minutos * 60) if minutos else None
            self.fim_previsto = agora + self.duracao if self.duracao else None
            for id_jogador, nome in alunos:
                self._inscrever(id_jogador, nome, agora)
            for cacador in self.cacadores.values():
                if 1 not in cacador.achadas:
                    self._achou(cacador, 1, agora, na_largada=True)
            self._evento("inicio", agora, minutos=minutos, cacadores=len(self.cacadores))
            self._avisos.append("🐉 A Caça às Esferas começou! Abra a tela 🐉 Esferas do app: você já ganhou a "
                                "1ª esfera. Faltam 6!")

    def pausar(self):
        with self._mexendo() as agora:
            if self.estado == "ativa":
                self.estado = "pausada"
                self.pausada_em = agora
                self._evento("pausa", agora)

    def retomar(self):
        with self._mexendo() as agora:
            if self.estado != "pausada":
                return
            parada = agora - self.pausada_em          # o tempo parado nao conta: empurra os prazos
            if self.fim_previsto is not None:
                self.fim_previsto += parada
            for cacador in self.cacadores.values():
                if cacador.pedido_ate is not None:
                    cacador.pedido_ate += parada
            self.estado = "ativa"
            self.pausada_em = None
            self._evento("retomada", agora)

    def encerrar(self):
        with self._mexendo() as agora:
            if self.estado in ("ativa", "pausada"):
                self._encerrar(agora, "professor")

    def _encerrar(self, agora, motivo):
        for cacador in self.cacadores.values():
            if cacador.posicao is not None and cacador.pedido is None:
                self._aplicar_pedido(cacador, 1, agora, automatico=True)
        self.estado = "encerrada"
        self.pausada_em = None
        self._evento("fim", agora, motivo=motivo)
        medalhas = ["🥇", "🥈", "🥉"]
        podio = " · ".join(f"{medalhas[i]} {c.nome[:30]} ({c.pontos()} pt{'s' if c.pontos() != 1 else ''})"
                           for i, c in enumerate(self._classificacao()[:3]))
        self._avisos.append("🏁 Fim da Caça às Esferas!" + (f" {podio}" if podio else ""))

    def nova(self):
        """Segredo novo e progresso zerado (os numeros de cacador continuam os mesmos)."""
        with self._mexendo() as agora:
            self._zerar()
            self._evento("nova", agora)

    def dica_extra(self, esfera, endereco=""):
        """Manda a dica extra para a turma (aviso do chat) e mostra tambem na tela Esferas."""
        with self._mexendo() as agora:
            self.dicas_extras.add(esfera)
            texto = preencher(ESFERAS[esfera]["extra"], endereco, "SEU_NUMERO")
            self._evento("dica_extra", agora, esfera=esfera)
            self._avisos.append(texto)
            return texto

    # ---------------- o que os alunos fazem ----------------

    def _achou(self, cacador, esfera, agora, na_largada=False):
        cacador.achadas[esfera] = agora
        self._evento("achado", agora, nome=cacador.nome, numero=cacador.numero, esfera=esfera,
                     conceito=ESFERAS[esfera]["conceito"], na_largada=na_largada)
        if len(cacador.achadas) == len(ESFERAS):
            self.concluidos += 1
            cacador.posicao = self.concluidos
            cacador.pedido_ate = agora + TEMPO_DO_PEDIDO
            self._evento("completou", agora, nome=cacador.nome, numero=cacador.numero, posicao=cacador.posicao)
            self._avisos.append(f"🐉 {cacador.nome} invocou o dragão! ({cacador.posicao}º lugar)")

    def resgatar(self, id_jogador, nome, texto, endereco=""):
        """O aluno digitou um codigo. Devolve a visao dele com {"resgate": {...}} ou levanta ErroDaCacada."""
        with self._mexendo() as agora:
            self._exigir_ativa()
            cacador = self._inscrever(id_jogador, nome, agora)
            if agora - cacador.ultima_tentativa < INTERVALO_RESGATE:
                raise Devagar("Calma! Espere 2 segundos entre uma tentativa e outra. ⏳")
            cacador.ultima_tentativa = agora
            codigo = normalizar_codigo(texto)
            if codigo is None:
                raise ErroDaCacada("Isso não parece um código. O formato é ESF-XXXXX (os códigos não têm 0, O, "
                                   "1, I nem L).")
            esfera = self._codigos_de(cacador.numero).get(codigo)
            if esfera is None:
                if any(codigo in self._codigos_de(outro) for outro in self.cacadores if outro != cacador.numero):
                    raise DeOutroCacador("Essa esfera pertence a outro caçador! 👀")
                raise ErroDaCacada("Código errado. Confira as letras e tente de novo.")
            nova = esfera not in cacador.achadas
            if nova:
                self._achou(cacador, esfera, agora)
            visao = self._visao(cacador, endereco, agora)
            visao["resgate"] = {"esfera": esfera, "nova": nova,
                                "mensagem": (f"Você encontrou a esfera de {esfera} estrela"
                                             f"{'s' if esfera > 1 else ''}! 🎉") if nova
                                else f"Você já tinha a esfera de {esfera} estrela{'s' if esfera > 1 else ''}."}
            return visao

    def escolher_pedido(self, id_jogador, nome, opcao, endereco=""):
        with self._mexendo() as agora:
            self._exigir_ativa()
            cacador = self._inscrever(id_jogador, nome, agora)
            if cacador.posicao is None:
                raise ErroDaCacada("Junte as 7 esferas antes de fazer um pedido! 🐉")
            if cacador.pedido is not None:
                raise ErroDaCacada("Você já fez o seu pedido.")
            if not isinstance(opcao, int) or isinstance(opcao, bool) or opcao not in PEDIDOS:
                raise ErroDaCacada("Escolha o pedido 1, 2 ou 3.")
            self._aplicar_pedido(cacador, opcao, agora)
            return self._visao(cacador, endereco, agora)

    def _aplicar_pedido(self, cacador, opcao, agora, automatico=False):
        cacador.pedido = opcao
        cacador.pedido_ate = None
        if opcao == 1:
            cacador.bonus_pedido += 3
        elif opcao == 2:
            for outro in self.cacadores.values():      # vale para quem ja e cacador agora
                outro.bonus_pedido += 1
        self._evento("pedido", agora, nome=cacador.nome, numero=cacador.numero, posicao=cacador.posicao,
                     pedido=opcao, texto=PEDIDOS[opcao], automatico=automatico)
        self._avisos.append(f"🎁 Pedido de {cacador.nome}: {PEDIDOS[opcao]}"
                            + (" (o tempo acabou e valeu o 1º)" if automatico else ""))

    def codigo_para(self, numero, esfera):
        """O codigo pessoal, para as rotas que entregam uma esfera (navegador, pista, caverna, terminal)."""
        with self._mexendo():
            self._exigir_ativa()
            self._cacador_pelo_numero(numero)
            return gerar_codigo(self.segredo, numero, esfera)

    def radar(self, numero, x, y):
        """{"achou": True, "codigo": ...} ou {"achou": False, "temperatura": "🔥 Quente"}."""
        with self._mexendo():
            self._exigir_ativa()
            self._cacador_pelo_numero(numero)
            alvo_x, alvo_y = alvo_do_radar(self.segredo, numero)
            distancia = abs(x - alvo_x) + abs(y - alvo_y)
            if distancia == 0:
                return {"achou": True, "codigo": gerar_codigo(self.segredo, numero, 4)}
            return {"achou": False, "temperatura": temperatura(distancia)}

    def grito(self, numero, palavra):
        """Alguem gritou na rede (UDP). Devolve o que o servidor responde so para quem gritou."""
        with self._mexendo() as agora:
            if self.estado != "ativa":
                return {"ok": False, "mensagem": MENSAGENS_PARADA[self.estado]}
            cacador = self.cacadores.get(numero)
            if cacador is None:
                return {"ok": False, "mensagem": f"Não conheço o caçador {numero}."}
            if agora - cacador.ultimo_grito >= INTERVALO_DO_GRITO:
                cacador.ultimo_grito = agora
                self._evento("grito", agora, nome=cacador.nome, numero=numero)
            if not eh_a_palavra_magica(palavra):
                return {"ok": False, "mensagem": "O servidor ouviu o seu grito, mas essa não é a palavra mágica! 🤔"}
            return {"ok": True, "codigo": gerar_codigo(self.segredo, numero, 6),
                    "mensagem": "O servidor ouviu o seu grito e respondeu só para você! 📡"}

    # ---------------- o que cada um ve ----------------

    def _classificacao(self):
        def chave(c):
            ultimo = max(c.achadas.values()) if c.achadas else float("inf")
            return (-c.pontos(), -len(c.achadas), c.posicao or 999, ultimo, c.numero)
        return sorted(self.cacadores.values(), key=chave)

    def visao(self, id_jogador, nome, endereco=""):
        """O que a tela Esferas do aluno mostra (o servidor responde 200 se ativa, 409 se parada)."""
        with self._mexendo() as agora:
            cacador = self._inscrever(id_jogador, nome, agora, criar=self.estado != "encerrada")
            return self._visao(cacador, endereco, agora)

    def _visao(self, cacador, endereco, agora):
        achadas = sorted(cacador.achadas)
        proxima = next((n for n in ESFERAS if n not in cacador.achadas), None)
        dica = None
        if proxima is not None and self.estado != "aguardando":
            dica = {"esfera": proxima, "estrelas": "★" * proxima, "conceito": ESFERAS[proxima]["conceito"],
                    "texto": preencher(ESFERAS[proxima]["dica"], endereco, cacador.numero),
                    "extra": preencher(ESFERAS[proxima]["extra"], endereco, cacador.numero)
                    if proxima in self.dicas_extras else ""}
        ultima = max(cacador.achadas, key=cacador.achadas.get) if cacador.achadas else None
        pedido = None
        if cacador.posicao is not None:
            pendente = cacador.pedido is None
            segundos = TEMPO_DO_PEDIDO
            if pendente and cacador.pedido_ate is not None:
                referencia = self.pausada_em if self.estado == "pausada" else agora
                segundos = max(0, int(cacador.pedido_ate - referencia))
            pedido = {"pendente": pendente, "segundos": segundos, "escolhido": cacador.pedido,
                      "texto": PEDIDOS.get(cacador.pedido, ""),
                      "opcoes": [{"id": n, "texto": texto} for n, texto in PEDIDOS.items()]}
        classificacao = self._classificacao()
        return {
            "estado": self.estado,
            "mensagem": MENSAGENS_PARADA.get(self.estado, ""),
            "numero": cacador.numero,
            "nome": cacador.nome,
            "esferas": achadas,
            "ultima": {"esfera": ultima, "aprendeu": ESFERAS[ultima]["aprendeu"]} if ultima else None,
            "dica": dica,
            "grito_direto": 6 in self.dicas_extras,
            "tempo_restante": self._tempo_restante(agora),
            "pontos": cacador.pontos(),
            "colocacao": classificacao.index(cacador) + 1 if cacador in classificacao else None,
            "total_cacadores": len(self.cacadores),
            "posicao": cacador.posicao,
            "pedido": pedido,
        }

    def instantaneo(self):
        """Uma COPIA de tudo, para o painel do professor (grade, podio, relogio)."""
        with self._mexendo() as agora:
            cacadores = [{"numero": c.numero, "nome": c.nome, "esferas": sorted(c.achadas), "pontos": c.pontos(),
                          "posicao": c.posicao, "pedido": c.pedido, "pedido_texto": PEDIDOS.get(c.pedido, "")}
                         for c in sorted(self.cacadores.values(), key=lambda c: c.numero)]
            podio = [{"numero": c.numero, "nome": c.nome, "pontos": c.pontos(), "esferas": len(c.achadas)}
                     for c in self._classificacao()[:3] if c.pontos() > 0]
            return {"estado": self.estado, "mensagem": MENSAGENS_PARADA.get(self.estado, ""),
                    "tempo_restante": self._tempo_restante(agora), "duracao": self.duracao,
                    "cacadores": cacadores, "podio": podio, "concluidos": self.concluidos,
                    "dicas_extras": sorted(self.dicas_extras), "resultado_salvo": self.resultado_salvo}

    # ---------------- resultado em CSV ----------------

    def linhas_do_resultado(self):
        with self._mexendo():
            linhas = [["posicao", "aluno", "numero", "esferas"] + [f"esfera_{n}" for n in ESFERAS]
                      + ["bonus_conclusao", "bonus_pedidos", "pedido", "pontos"]]
            for posicao, c in enumerate(self._classificacao(), start=1):
                horarios = [datetime.fromtimestamp(c.achadas[n]).strftime("%H:%M:%S") if n in c.achadas else ""
                            for n in ESFERAS]
                linhas.append([posicao, c.nome, c.numero, len(c.achadas)] + horarios
                              + [BONUS_ORDEM.get(c.posicao, 0), c.bonus_pedido, PEDIDOS.get(c.pedido, ""),
                                 c.pontos()])
            return linhas

    def salvar_csv(self, pasta=None):
        """Grava cacada_<data_hora>.csv (separado por ';' e com BOM: o Excel em portugues abre certinho)."""
        pasta = pasta or PASTA_DOS_RESULTADOS
        pasta.mkdir(parents=True, exist_ok=True)
        caminho = pasta / f"cacada_{datetime.now():%Y-%m-%d_%H-%M-%S}.csv"
        with open(caminho, "w", encoding="utf-8-sig", newline="") as arquivo:
            csv.writer(arquivo, delimiter=";").writerows(self.linhas_do_resultado())
        with self._trava:
            self.resultado_salvo = str(caminho)
        return caminho
