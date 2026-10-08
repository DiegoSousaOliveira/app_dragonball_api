"""
O servidor baixa o audio do grito de guerra (ele faz o papel de "proxy": os PCs dos alunos podem estar sem internet).

Baixar um endereco escolhido pelo ALUNO e perigoso: ele poderia pedir ao servidor para acessar coisas que so o
servidor alcanca (o proprio servidor em http://127.0.0.1:8000, o roteador 192.168.0.1, a impressora...). Esse
ataque tem nome: SSRF (Server-Side Request Forgery, "falsificacao de pedido feita pelo servidor"). As protecoes:
  1. so http/https, so as portas 80/443 e nada de usuario:senha na URL;
  2. o nome e resolvido no DNS e TODOS os IPs precisam ser publicos (nada de loopback, rede local, link-local,
     multicast ou reservado). A conexao vai direto para o IP conferido: o DNS nao e consultado de novo (assim um
     DNS "espertinho" nao troca o IP no meio do caminho);
  3. cada redirecionamento passa pela mesma conferencia (no maximo 3);
  4. timeout curto, no maximo 500 KB, e o formato conferido pelos PRIMEIROS BYTES do arquivo (nao pela extensao).
Isso protege a REDE. O conteudo do audio quem modera e o professor (painel, aba 📣 Gritos).
"""

import http.client
import ipaddress
import socket
import ssl
from urllib.parse import urljoin, urlsplit

LIMITE = 500 * 1024              # bytes
TIMEOUT = 5                      # segundos
MAX_REDIRECIONAMENTOS = 3
PORTAS = {80, 443}
ENDERECOS_DE_TESTE = set()       # so os testes mexem aqui (ex.: {"127.0.0.1"}), para usar um servidor local
PORTAS_DE_TESTE = set()


class ErroDoAudio(Exception):
    """Cada erro ja diz o status HTTP (e cada um ensina um status diferente)."""
    status = 400


class Bloqueado(ErroDoAudio):
    status = 403


class GrandeDemais(ErroDoAudio):
    status = 413


class FormatoErrado(ErroDoAudio):
    status = 415


class FalhaNoDownload(ErroDoAudio):
    status = 502


def detectar_formato(dados):
    """Pelos primeiros bytes (a "assinatura" do arquivo): 'mp3', 'wav', 'ogg' ou None."""
    if dados[:3] == b"ID3" or (len(dados) > 1 and dados[0] == 0xFF and (dados[1] & 0xE0) == 0xE0):
        return "mp3"
    if dados[:4] == b"RIFF" and dados[8:12] == b"WAVE":
        return "wav"
    if dados[:4] == b"OggS":
        return "ogg"
    return None


def ip_publico(texto):
    """True so para IPs da internet (nada de 127.x, 10.x, 192.168.x, 169.254.x, multicast, reservados...)."""
    if texto in ENDERECOS_DE_TESTE:
        return True
    try:
        ip = ipaddress.ip_address(texto.split("%")[0])
    except ValueError:
        return False
    if getattr(ip, "ipv4_mapped", None):                 # ::ffff:127.0.0.1 e o 127.0.0.1 disfarcado
        ip = ip.ipv4_mapped
    return ip.is_global and not (ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_multicast
                                 or ip.is_reserved or ip.is_unspecified)


def conferir(url):
    """Confere a URL e o IP. Devolve (esquema, host, porta, ip, caminho) ou levanta ErroDoAudio."""
    try:
        partes = urlsplit((url or "").strip())
        porta = partes.port
    except ValueError:
        raise ErroDoAudio("Endereço inválido.")
    if partes.scheme not in ("http", "https"):
        raise ErroDoAudio("Use um endereço que começa com http:// ou https://.")
    host = partes.hostname
    if not host:
        raise ErroDoAudio("Endereço inválido.")
    if host.endswith(("youtube.com", "youtu.be")):
        raise ErroDoAudio("Link do YouTube não vale: ele abre uma PÁGINA, não um arquivo. Use um link direto para um "
                          "arquivo .mp3, .wav ou .ogg.")
    if partes.username or partes.password:
        raise Bloqueado("Endereços com usuário e senha não são aceitos.")
    porta = porta or (443 if partes.scheme == "https" else 80)
    if porta not in PORTAS and porta not in PORTAS_DE_TESTE:
        raise Bloqueado(f"Só aceito as portas 80 e 443 (esse endereço usa a {porta}).")
    try:
        infos = socket.getaddrinfo(host, porta, type=socket.SOCK_STREAM)
    except (OSError, UnicodeError):
        raise FalhaNoDownload("Não achei esse endereço. O servidor está sem internet? Use o grito padrão.")
    ips = sorted({info[4][0] for info in infos}, key=lambda ip: (":" in ip, ip))      # IPv4 primeiro
    if not ips or not all(ip_publico(ip) for ip in ips):
        raise Bloqueado("Esse endereço aponta para dentro da rede (ou para o próprio servidor): bloqueado por "
                        "segurança.")
    caminho = (partes.path or "/") + (f"?{partes.query}" if partes.query else "")
    return partes.scheme, host, porta, ips[0], caminho


class _ConexaoNoIpConferido(http.client.HTTPConnection):
    """Conecta no IP ja conferido, mas manda o nome certo no cabecalho Host (e no TLS, para conferir o certificado)."""

    def __init__(self, host, ip, porta, https, timeout):
        super().__init__(host, porta, timeout=timeout)
        self._ip, self._https = ip, https

    def connect(self):
        self.sock = socket.create_connection((self._ip, self.port), self.timeout)
        if self._https:
            self.sock = ssl.create_default_context().wrap_socket(self.sock, server_hostname=self.host)


def baixar(url):
    """Baixa o audio com todas as protecoes. Devolve (bytes, formato) ou levanta ErroDoAudio."""
    for _ in range(MAX_REDIRECIONAMENTOS + 1):
        esquema, host, porta, ip, caminho = conferir(url)
        conexao = _ConexaoNoIpConferido(host, ip, porta, esquema == "https", TIMEOUT)
        try:
            conexao.request("GET", caminho, headers={"User-Agent": "DragonBallDex-Servidor/2.4", "Accept": "audio/*"})
            resposta = conexao.getresponse()
            if resposta.status in (301, 302, 303, 307, 308):
                destino = resposta.getheader("Location")
                if not destino:
                    raise FalhaNoDownload("O endereço mandou redirecionar, mas não disse para onde.")
                url = urljoin(url, destino)                          # o novo endereco e conferido de novo
                continue
            if resposta.status != 200:
                raise FalhaNoDownload(f"O endereço respondeu {resposta.status} (o arquivo existe mesmo?).")
            tamanho = resposta.getheader("Content-Length") or ""
            if tamanho.isdigit() and int(tamanho) > LIMITE:
                raise GrandeDemais("O arquivo passa de 500 KB. Escolha um áudio mais curto.")
            dados = resposta.read(LIMITE + 1)
            if len(dados) > LIMITE:
                raise GrandeDemais("O arquivo passa de 500 KB. Escolha um áudio mais curto.")
            formato = detectar_formato(dados)
            if formato is None:
                raise FormatoErrado("Isso não é um áudio mp3, wav ou ogg (conferi os primeiros bytes do arquivo).")
            return dados, formato
        except (OSError, http.client.HTTPException) as erro:            # inclui timeout e erro de certificado
            raise FalhaNoDownload(f"Não consegui baixar ({type(erro).__name__}). O servidor está sem internet? "
                                  "Use o grito padrão.")
        finally:
            conexao.close()
    raise FalhaNoDownload("Redirecionamentos demais (o limite é 3).")
