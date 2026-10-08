"""
Gera o instalador do Dragon Ball Dex:
    1. PyInstaller: transforma o programa em dist/DragonBallDex/DragonBallDex.exe (com o Python dentro).
       ATENCAO: esse .exe so funciona JUNTO com a pasta _internal que fica ao lado dele.
    2. Inno Setup: empacota tudo em dist_instalador/DragonBallDex-Setup-<versao>.exe
    3. PyInstaller --onefile: dist_instalador/DragonBallDex-Portatil.exe (um arquivo so, para pendrive)
Use um Python baixado de python.org (o da Microsoft Store pode gerar um .exe que nao abre em outros PCs).

Uso (na pasta do projeto, num Python com: pip install -r requirements.txt pyinstaller):
    python instalador/construir.py            -> exe + instalador
    python instalador/construir.py --so-exe   -> so a pasta dist/DragonBallDex (sem instalador)
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path

PROJETO = Path(__file__).resolve().parent.parent
INSTALADOR = PROJETO / "instalador"
ICONE = INSTALADOR / "icone.ico"
SEPARADOR = ";" if os.name == "nt" else ":"
LUGARES_DO_ISCC = [
    Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Inno Setup 6" / "ISCC.exe",
    Path(r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe"),
    Path(r"C:\Program Files\Inno Setup 6\ISCC.exe"),
]


def dado(origem, destino):
    return ["--add-data", f"{origem}{SEPARADOR}{destino}"]


def gerar_exe(arquivo_unico=False):
    if not ICONE.exists():
        subprocess.run([sys.executable, str(INSTALADOR / "gerar_icone.py")], check=True)
    if "WindowsApps" in sys.executable:
        print("AVISO: este Python e o da Microsoft Store. Prefira o de python.org para gerar o .exe.")
    nome = "DragonBallDex-Portatil" if arquivo_unico else "DragonBallDex"
    destino = PROJETO / ("dist_instalador" if arquivo_unico else "dist")
    comando = [sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean", "--windowed",
               "--onefile" if arquivo_unico else "--onedir",
               "--name", nome, "--icon", str(ICONE),
               "--distpath", str(destino), "--workpath", str(PROJETO / "build" / nome),
               "--specpath", str(PROJETO / "build"),
               "--collect-data", "customtkinter"]
    comando += dado(PROJETO / "dados", "dados")              # snapshot (plano B sem internet)
    comando += dado(ICONE, ".")
    imagens = PROJETO / "cache" / "imagens"
    if imagens.exists():
        comando += dado(imagens, "cache/imagens")            # fotos ja baixadas: o servidor funciona offline
    else:
        print("AVISO: cache/imagens nao existe; o instalador vai sem as fotos embutidas.")
    figuras = PROJETO / "interface" / "imagens"
    if figuras.exists():
        comando += dado(figuras, "interface/imagens")        # o dragao do efeito da Caca as Esferas
    comando.append(str(PROJETO / "main.py"))
    print(f"PyInstaller ({nome})...")
    subprocess.run(comando, check=True, cwd=PROJETO)
    print("Pronto:", destino / nome)


def gerar_instalador():
    iscc = next((caminho for caminho in LUGARES_DO_ISCC if caminho.exists()), None)
    if iscc is None and shutil.which("iscc"):
        iscc = Path(shutil.which("iscc"))
    if iscc is None:
        sys.exit("Inno Setup nao encontrado. Instale com:  winget install JRSoftware.InnoSetup")
    print("Inno Setup...")
    subprocess.run([str(iscc), "/Q", str(INSTALADOR / "DragonBallDex.iss")], check=True)
    for arquivo in (PROJETO / "dist_instalador").glob("*.exe"):
        print("Instalador:", arquivo, f"({arquivo.stat().st_size / 1024 / 1024:.1f} MB)")


if __name__ == "__main__":
    gerar_exe()
    if "--so-exe" not in sys.argv:
        gerar_instalador()
        gerar_exe(arquivo_unico=True)
