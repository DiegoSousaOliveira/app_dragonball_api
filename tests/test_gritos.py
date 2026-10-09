"""Testes do Grito de Guerra: o download seguro (SSRF, tamanho, formato), as regras da troca, o bloqueio pelo
professor, os eventos de som e as rotas. Tudo com um servidor HTTP LOCAL de teste: nada de internet."""

import contextlib
import json
import socket
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import requests

from core import gritos_cliente
from core.esferas_cliente import Recusado
from core.grito_padrao import ID_DO_PADRAO, gerar_wav
from servidor import baixar_audio as ba
from servidor.gritos import FRASE_PADRAO, Devagar, Gritos, GritoBloqueado
from tests.test_radar import com_app_conectado
from tests.test_rotas_esferas import APP, base, com_cacada, entrar, get, post, servidor

MP3 = b"ID3\x04\x00\x00\x00\x00\x00\x00" + b"\x00" * 600
WAV = gerar_wav()
OGG = b"OggS\x00\x02" + b"\x00" * 300


class Arquivos(BaseHTTPRequestHandler):
    """O 'site' de teste: alguns audios de verdade e algumas pegadinhas."""

    def do_GET(self):
        porta = self.server.server_address[1]
        rotas = {"/ok.mp3": MP3, "/ok.wav": WAV, "/ok.ogg": OGG, "/falso.mp3": b"<html>nao sou audio</html>",
                 "/grande.mp3": b"ID3" + b"\x00" * (ba.LIMITE + 10)}
        destinos = {"/vai-para-ok": "/ok.mp3", "/vai-para-dentro": f"http://127.0.0.2:{porta}/ok.mp3",
                    "/volta": "/volta"}
        if self.path in destinos:
            self.send_response(302)
            self.send_header("Location", destinos[self.path])
            self.send_header("Content-Length", "0")
            self.end_headers()
            return
        corpo = rotas.get(self.path)
        self.send_response(200 if corpo else 404)
        self.send_header("Content-Length", str(len(corpo or b"")))
        self.end_headers()
        self.wfile.write(corpo or b"")

    def log_message(self, *args):
        pass


@contextlib.contextmanager
def site_local():
    """Liga o site de teste em 127.0.0.1 e libera SO esse endereco (e porta) nas protecoes, durante o teste."""
    site = ThreadingHTTPServer(("127.0.0.1", 0), Arquivos)
    threading.Thread(target=site.serve_forever, daemon=True).start()
    porta = site.server_address[1]
    ba.ENDERECOS_DE_TESTE.add("127.0.0.1")
    ba.PORTAS_DE_TESTE.add(porta)
    try:
        yield f"http://127.0.0.1:{porta}"
    finally:
        ba.ENDERECOS_DE_TESTE.discard("127.0.0.1")
        ba.PORTAS_DE_TESTE.discard(porta)
        site.shutdown()
        site.server_close()


def levanta(classe, funcao, *args, **kwargs):
    try:
        funcao(*args, **kwargs)
    except classe as erro:
        return erro
    raise AssertionError(f"esperava {classe.__name__}")


# ---------------- download seguro ----------------

def test_ssrf_enderecos_internos_sao_recusados():
    """Sem as liberacoes de teste: nada de loopback, rede local, link-local nem 'localhost'."""
    for url in ("http://127.0.0.1/grito.mp3", "http://localhost/grito.mp3", "http://192.168.0.10/grito.mp3",
                "http://10.0.0.1/a.mp3", "http://172.16.5.4/a.mp3", "http://169.254.169.254/latest/meta-data",
                "http://[::1]/a.mp3", "http://[::ffff:127.0.0.1]/a.mp3", "http://0.0.0.0/a.mp3",
                "http://224.0.0.1/a.mp3"):
        erro = levanta(ba.Bloqueado, ba.conferir, url)
        assert erro.status == 403, url
    assert levanta(ba.Bloqueado, ba.conferir, "http://exemplo.com:8080/a.mp3").status == 403      # porta
    assert levanta(ba.Bloqueado, ba.conferir, "http://ana:senha@exemplo.com/a.mp3").status == 403
    for url in ("ftp://exemplo.com/a.mp3", "file:///C:/Windows/win.ini", "javascript:alert(1)", "", "http://"):
        assert levanta(ba.ErroDoAudio, ba.conferir, url).status == 400, url
    assert "YouTube" in str(levanta(ba.ErroDoAudio, ba.conferir, "https://www.youtube.com/watch?v=abc"))
    assert not ba.ip_publico("127.0.0.1") and not ba.ip_publico("192.168.1.1") and ba.ip_publico("8.8.8.8")


def test_baixar_audio_de_verdade_e_formato_pelos_primeiros_bytes():
    with site_local() as site:
        assert ba.baixar(f"{site}/ok.mp3") == (MP3, "mp3")
        assert ba.baixar(f"{site}/ok.wav")[1] == "wav"
        assert ba.baixar(f"{site}/ok.ogg")[1] == "ogg"
        assert ba.baixar(f"{site}/vai-para-ok")[1] == "mp3"                     # redirecionamento permitido
        assert levanta(ba.FormatoErrado, ba.baixar, f"{site}/falso.mp3").status == 415   # extensao mente
        assert levanta(ba.GrandeDemais, ba.baixar, f"{site}/grande.mp3").status == 413
        assert levanta(ba.FalhaNoDownload, ba.baixar, f"{site}/nao-existe.mp3").status == 502
        assert levanta(ba.FalhaNoDownload, ba.baixar, f"{site}/volta").status == 502      # redireciona sem fim
        erro = levanta(ba.Bloqueado, ba.baixar, f"{site}/vai-para-dentro")             # 302 para 127.0.0.2
        assert erro.status == 403


# ---------------- regras do grito ----------------

class Relogio:
    def __init__(self):
        self.agora = 5_000.0

    def __call__(self):
        return self.agora


def gritos_de_teste():
    relogio = Relogio()
    return Gritos(pasta=Path(tempfile.mkdtemp()), relogio=relogio), relogio


def test_trocar_frase_e_audio_com_espera():
    gritos, relogio = gritos_de_teste()
    assert gritos.meu("id-Ana", "Ana")["frase"] == FRASE_PADRAO and gritos.meu("id-Ana", "Ana")["padrao"]
    with site_local() as site:
        meu = gritos.trocar("id-Ana", "Ana", frase="  KAMEHAMEHA!\n\x07 ", url=f"{site}/ok.mp3")
    assert meu["frase"] == "KAMEHAMEHA!" and meu["audio"].endswith(".mp3") and not meu["padrao"]   # o professor deixou
    assert gritos.arquivo(meu["audio"]).read_bytes() == MP3
    assert levanta(Devagar, gritos.trocar, "id-Ana", "Ana", frase="outra").status == 429
    relogio.agora += 10
    assert levanta(ba.ErroDoAudio, gritos.trocar, "id-Ana", "Ana", url="https://youtu.be/abc").status == 400
    assert gritos.meu("id-Ana", "Ana")["troca_em"] == 0             # link recusado sem usar a rede: nao gasta a vez
    assert levanta(ba.Bloqueado, gritos.trocar, "id-Ana", "Ana", url="http://127.0.0.1/x.mp3").status == 403
    assert gritos.meu("id-Ana", "Ana")["troca_em"] > 0              # tentativa contra a rede interna: gasta
    relogio.agora += 10
    assert gritos.trocar("id-Ana", "Ana", frase="x" * 80)["frase"] == "x" * 40
    relogio.agora += 10
    assert gritos.trocar("id-Ana", "Ana", padrao=True)["padrao"] is True
    assert gritos.arquivo("../../segredo.txt") is None and gritos.arquivo("a" * 16 + ".exe") is None


def test_bloquear_volta_ao_padrao_e_nao_deixa_trocar():
    gritos, relogio = gritos_de_teste()
    gritos.trocar("id-Bia", "Bia", frase="Pelo poder do Kaioken!")
    versao = gritos.versao
    gritos.bloquear(["id-Bia", "id-Caio"])
    assert gritos.versao > versao
    assert gritos.grito_de("id-Bia") == {"frase": FRASE_PADRAO, "audio": ID_DO_PADRAO, "padrao": True}
    relogio.agora += 60
    erro = levanta(GritoBloqueado, gritos.trocar, "id-Bia", "Bia", frase="de novo")
    assert erro.status == 403 and "bloqueou" in str(erro)
    assert gritos.meu("id-Bia", "Bia")["bloqueado"] is True
    gritos.desbloquear(["id-Bia"])
    assert gritos.grito_de("id-Bia")["frase"] == "Pelo poder do Kaioken!"            # o dele volta a valer
    assert gritos.trocar("id-Bia", "Bia", frase="Liberado!")["frase"] == "Liberado!"


def test_eventos_de_som():
    gritos, _ = gritos_de_teste()
    gritos.trocar("id-Ana", "Ana", frase="Pela Ana!")
    gritos.anunciar("id-Ana", "Ana", "conquista", "Ana conquistou Namek!", {"id-Ana", "id-Beto"})
    gritos.anunciar("id-Caio", "Caio", "dragao", "Caio invocou o dragão!")
    estado = gritos.estado_para("id-Zeca", 0)
    assert [(e["tipo"], e["frase"]) for e in estado["eventos"]] == [("conquista", "Pela Ana!"),
                                                                    ("dragao", FRASE_PADRAO)]
    assert ID_DO_PADRAO in estado["audios"] and "id-Ana" not in json.dumps(estado)     # o X-Jogador e secreto
    assert gritos.estado_para("id-Zeca", estado["ultimo"])["eventos"] == []


# ---------------- pelas rotas (servidor de teste) ----------------

def test_rotas_do_grito():
    gritos = servidor().gritos
    gritos.pasta = Path(tempfile.mkdtemp())
    ana = entrar("Ana GR")
    meu = get("/gritos/meu", ana)
    assert meu.status_code == 200 and meu.json()["padrao"] is True
    padrao = get(f"/gritos/{ID_DO_PADRAO}")
    assert padrao.status_code == 200 and padrao.headers["Content-Type"] == "audio/wav" and padrao.content[:4] == b"RIFF"
    assert get("/gritos/..%2F..%2Fcore%2Fapi.py").status_code == 404
    proibido = post("/gritos/meu", {"url": "http://192.168.0.1/grito.mp3"}, ana)
    assert proibido.status_code == 403 and "dentro da rede" in proibido.json()["message"]
    assert post("/gritos/meu", {"frase": "outra"}, ana).status_code == 429                  # 10 s entre trocas
    gritos.alunos[ana["X-Jogador"]]["trocou_em"] = None
    with site_local() as site:
        trocado = post("/gritos/meu", {"frase": "Vai, Ana!", "url": f"{site}/ok.ogg"}, ana).json()
    audio = get(f"/gritos/{trocado['audio']}")
    assert audio.status_code == 200 and audio.headers["Content-Type"] == "audio/ogg" and audio.content == OGG
    gritos.bloquear([ana["X-Jogador"]])
    assert get("/gritos/meu", ana).json()["frase"] == FRASE_PADRAO
    gritos.desbloquear([ana["X-Jogador"]])


def test_novidades_so_aparecem_com_atividade_valendo():
    ana = entrar("Ana NV")
    servidor().cacada.encerrar()
    servidor().cacada.nova()
    assert "novidades" not in get("/turma/sala", ana).json()                                 # igual a 2.3.2

    @com_cacada
    def com_a_cacada():
        assert get("/turma/sala", ana).json()["novidades"]["gritos"] >= 1

    com_a_cacada()


@com_cacada
def test_esfera_6_toca_o_grito_sem_a_palavra_magica():
    from core import esferas
    ana = entrar("Ana E6")
    numero = get("/esferas/estado", ana).json()["numero"]
    antes = servidor().gritos.ultimo_evento
    codigo = esferas.gerar_codigo(servidor().cacada.segredo, numero, 6)
    assert post("/esferas/resgatar", {"codigo": codigo}, ana).status_code == 200
    eventos = get("/gritos/eventos", ana, depois=antes).json()["eventos"]
    assert [e["tipo"] for e in eventos] == ["esfera6"] and eventos[0]["nome"] == "Ana E6"
    texto = json.dumps(eventos, ensure_ascii=False).lower()
    assert "kamehameha" not in texto and "kame" not in texto       # o sistema nunca entrega a palavra magica
    assert base()                                                  # (o servidor de teste continua de pe)


# ---------------- 2.4.1: o audio do PC do aluno (upload) ----------------

def enviar(dados, cabecalhos, sessao=requests, **params):
    """Como o app manda um arquivo: o arquivo INTEIRO no corpo, a frase na query string."""
    return sessao.post(base() + "/gritos/audio", data=dados, params=params, timeout=5,
                       headers=dict(cabecalhos, **{"Content-Type": "audio/mpeg"}))


def test_arquivo_do_pc_pela_rota():
    gritos = servidor().gritos
    gritos.pasta = Path(tempfile.mkdtemp())
    ana = entrar("Ana UP")
    falso = enviar(b"<html>nao sou audio</html>", ana)
    assert falso.status_code == 415 and "primeiros bytes" in falso.json()["message"]
    assert enviar(b"", ana).status_code == 400
    assert get("/gritos/meu", ana).json()["troca_em"] == 0                  # arquivo recusado nao gasta a vez
    ok = enviar(MP3, ana, frase="Pelo meu PC!")
    assert ok.status_code == 200 and ok.json()["frase"] == "Pelo meu PC!" and ok.json()["audio"].endswith(".mp3")
    assert get(f"/gritos/{ok.json()['audio']}").content == MP3                # os colegas baixam o mesmo arquivo
    assert enviar(WAV, ana).status_code == 429                                 # 10 s entre trocas
    assert enviar(WAV, {"User-Agent": APP}).status_code == 400                 # sem X-Jogador
    gritos.alunos[ana["X-Jogador"]]["trocou_em"] = None
    gritos.bloquear([ana["X-Jogador"]])
    assert enviar(OGG, ana).status_code == 403
    gritos.desbloquear([ana["X-Jogador"]])
    so_audio = enviar(OGG, ana).json()                                         # sem frase: a frase continua
    assert so_audio["frase"] == "Pelo meu PC!" and so_audio["audio"].endswith(".ogg")


def test_arquivo_grande_demais_responde_413():
    ana = entrar("Ana 413")
    limite, ba.LIMITE = ba.LIMITE, 1000
    try:
        sessao = requests.Session()
        grande = enviar(b"ID3" + bytes(3000), ana, sessao)
        assert grande.status_code == 413
        assert sessao.get(base() + "/gritos/meu", headers=ana, timeout=5).status_code == 200   # conexao segue boa
        # enorme: o servidor responde 413 sem ler o corpo (so os cabecalhos chegaram) e fecha a conexao
        host, porta = base()[len("http://"):].split(":")
        pedido = "\r\n".join(["POST /gritos/audio HTTP/1.1", f"Host: {host}", f"X-Jogador: {ana['X-Jogador']}",
                              "Content-Type: audio/mpeg", "Content-Length: 999999999", "", ""])
        with socket.create_connection((host, int(porta)), timeout=5) as conexao:
            conexao.sendall(pedido.encode())
            resposta = conexao.recv(4096).decode("utf-8", "replace")
        assert resposta.startswith("HTTP/1.1 413")
    finally:
        ba.LIMITE = limite


def test_app_manda_o_arquivo_do_pc():
    servidor().gritos.pasta = Path(tempfile.mkdtemp())
    ana = entrar("Ana APP")
    pasta = Path(tempfile.mkdtemp())
    (pasta / "grito.wav").write_bytes(WAV)
    (pasta / "grande.mp3").write_bytes(b"ID3" + bytes(gritos_cliente.LIMITE + 1))
    (pasta / "video.mp4").write_bytes(b"nao")
    meu = com_app_conectado(ana, lambda: gritos_cliente.enviar_arquivo(pasta / "grito.wav", "Do meu PC"))
    assert meu["frase"] == "Do meu PC" and meu["audio"].endswith(".wav") and meu["audio_personalizado"]
    assert levanta(Recusado, gritos_cliente.enviar_arquivo, pasta / "grande.mp3").status == 413   # nem manda
    assert levanta(Recusado, gritos_cliente.enviar_arquivo, pasta / "video.mp4").status == 415
    assert levanta(Recusado, gritos_cliente.enviar_arquivo, pasta / "sumiu.mp3").status == 400
    youtube = levanta(ba.ErroDoAudio, ba.conferir, "https://youtu.be/abc")
    assert youtube.status == 400 and "Arquivo do PC" in str(youtube)          # a mensagem ensina o caminho certo


def test_trocar_com_arquivo_confere_os_bytes():
    gritos, relogio = gritos_de_teste()
    executavel = b"MZ" + bytes(100)                                            # um .exe renomeado para .mp3
    assert levanta(ba.FormatoErrado, gritos.trocar, "id-Bia", "Bia", arquivo=executavel).status == 415
    grande = b"RIFF" + bytes(ba.LIMITE)
    assert levanta(ba.GrandeDemais, gritos.trocar, "id-Bia", "Bia", arquivo=grande).status == 413
    meu = gritos.trocar("id-Bia", "Bia", arquivo=OGG)                        # recusas acima nao gastaram a vez
    assert meu["audio"].endswith(".ogg") and gritos.arquivo(meu["audio"]).read_bytes() == OGG
