; Instalador do Dragon Ball Dex (Inno Setup 6).
; Nao rode este arquivo direto: use  python instalador\construir.py  (ele gera o .exe antes).

#define Versao "2.4.1"
#define Nome "Dragon Ball Dex"
#define Exe "DragonBallDex.exe"

[Setup]
AppId={{6F1D2B8E-4C7A-4E59-9B1F-DB2026DEX001}
AppName={#Nome}
AppVersion={#Versao}
AppVerName={#Nome} {#Versao}
AppPublisher=Projeto escolar de Redes de Computadores
DefaultDirName={autopf}\{#Nome}
DefaultGroupName={#Nome}
DisableProgramGroupPage=yes
OutputDir=..\dist_instalador
OutputBaseFilename=DragonBallDex-Setup-{#Versao}
SetupIconFile=icone.ico
UninstallDisplayIcon={app}\{#Exe}
UninstallDisplayName={#Nome}
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
; Administrador: instala para todos os usuarios e libera o servidor no Firewall.
; (Da para instalar so para o usuario atual, sem administrador: o Firewall entao pergunta na 1a vez.)
PrivilegesRequired=admin
PrivilegesRequiredOverridesAllowed=dialog commandline
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0

[Languages]
Name: "ptbr"; MessagesFile: "compiler:Languages\BrazilianPortuguese.isl"

[Tasks]
Name: "atalho_aluno"; Description: "Atalho do Dragon Ball Dex (aluno) na Área de Trabalho"; GroupDescription: "Atalhos:"
Name: "atalho_servidor"; Description: "Atalho do Servidor do Professor na Área de Trabalho"; GroupDescription: "Atalhos:"; Flags: unchecked

[Files]
Source: "..\dist\DragonBallDex\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#Nome}"; Filename: "{app}\{#Exe}"; Comment: "Aplicativo do aluno"
Name: "{group}\{#Nome} - Servidor do Professor"; Filename: "{app}\{#Exe}"; Parameters: "--servidor"; Comment: "Liga o servidor da sala e o painel para o telão"
Name: "{group}\Desinstalar {#Nome}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#Nome}"; Filename: "{app}\{#Exe}"; Tasks: atalho_aluno
Name: "{autodesktop}\{#Nome} - Servidor"; Filename: "{app}\{#Exe}"; Parameters: "--servidor"; Tasks: atalho_servidor

[Run]
; Libera o programa no Firewall do Windows (porta 8000 TCP do servidor e 50505 UDP da busca automatica).
; profile=any porque muitas redes de escola sao classificadas como "Publica" pelo Windows.
Filename: "{sys}\netsh.exe"; Parameters: "advfirewall firewall delete rule name=""{#Nome}"""; Flags: runhidden; Check: IsAdminInstallMode
Filename: "{sys}\netsh.exe"; Parameters: "advfirewall firewall add rule name=""{#Nome}"" dir=in action=allow program=""{app}\{#Exe}"" enable=yes profile=any"; Flags: runhidden; Check: IsAdminInstallMode; StatusMsg: "Liberando o servidor no Firewall do Windows..."
Filename: "{app}\{#Exe}"; Description: "Abrir o Dragon Ball Dex agora"; Flags: nowait postinstall skipifsilent

[UninstallRun]
Filename: "{sys}\netsh.exe"; Parameters: "advfirewall firewall delete rule name=""{#Nome}"""; Flags: runhidden; Check: IsAdminInstallMode; RunOnceId: "RemoverRegraDoFirewall"

[UninstallDelete]
; Os dados de cada usuario (cache, placar) ficam em %LOCALAPPDATA%\DragonBallDex e NAO sao apagados
; de proposito: reinstalar nao perde o placar da turma.
Type: filesandordirs; Name: "{app}\_internal"
