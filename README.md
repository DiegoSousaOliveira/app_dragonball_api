# 🐉 Dragon Ball Dex

Aplicativo para a turma explorar o universo Dragon Ball **e ver uma rede de computadores funcionando de verdade**.
O computador do professor vira um **servidor** na rede do laboratório; os computadores dos alunos se conectam a ele
para buscar personagens, lutar, jogar o quiz e entrar no **placar da turma**. Tudo o que passa pela rede aparece ao vivo
no telão.

![Painel do professor](docs/imagens/painel_professor.png)

---

## Sumário

1. [Como funciona](#1-como-funciona)
2. [Instalação](#2-instalação)
3. [Usando na aula](#3-usando-na-aula)
4. [O aplicativo do aluno](#4-o-aplicativo-do-aluno)
5. [O que dá para ensinar de Redes](#5-o-que-dá-para-ensinar-de-redes)
6. [Solução de problemas](#6-solução-de-problemas)
7. [Para quem vai mexer no código](#7-para-quem-vai-mexer-no-código)

---

## 1. Como funciona

```
 PC do professor                                         PCs dos alunos
 ┌────────────────────────────────────┐               ┌─────────────────────────────┐
 │ "Dragon Ball Dex - Servidor"       │   rede da     │ "Dragon Ball Dex"            │
 │  • painel no telão (quem está      │   sala        │  Personagens · Batalha ·     │
 │    conectado, pedidos ao vivo,     │ ◀──────────▶  │  Planetas · Ranking · Quiz · │
 │    placar da turma)                │  HTTP 8000    │  Turma · Rede                │
 │  • entrega os dados e as fotos     │  UDP 50505    │                              │
 │  • guarda o placar da turma        │  (busca)      └─────────────────────────────┘
 │        │                           │
 │        └─ internet (se houver) → dragonball-api.com
 │           sem internet: usa as cópias que vêm no instalador
 └────────────────────────────────────┘
```

- **Um único programa**, dois atalhos: **Dragon Ball Dex** (aluno) e **Dragon Ball Dex - Servidor do Professor**.
- **Não precisa de internet na sala:** o servidor já vem com os dados e as fotos dos 58 personagens e 20 planetas. Se
  houver internet, ele busca a versão mais nova.
- **Também funciona sem servidor:** o aluno pode escolher "usar sem servidor (internet direto)". Só o placar da turma
  fica de fora.

---

## 2. Instalação

Na pasta `dist_instalador\` há **duas** formas de levar o programa para os computadores. Nenhuma precisa de Python:
o programa já leva tudo dentro.

| Arquivo | Quando usar |
|---|---|
| **`DragonBallDex-Setup-2.2.0.exe`** (≈ 30 MB) | **Recomendado.** Instala com atalhos e libera o servidor no Firewall |
| **`DragonBallDex-Portatil.exe`** (≈ 34 MB) | Sem instalar: copie **só este arquivo** (pendrive, Downloads...) e dê dois cliques. Demora uns segundos a mais para abrir |

### Com o instalador

1. Copie o instalador para um pendrive (ou para uma pasta compartilhada da rede).
2. Em **cada** computador (professor e alunos), dê dois cliques e avance. O Windows pede permissão de administrador.
3. Pronto: aparecem os atalhos no Menu Iniciar (e, se marcado, na Área de Trabalho).

| O que o instalador faz | Por quê |
|---|---|
| Instala em `C:\Program Files\Dragon Ball Dex` | Para todos os usuários do computador |
| Cria os atalhos "Dragon Ball Dex" e "Dragon Ball Dex - Servidor do Professor" | O mesmo programa, em dois modos |
| **Libera o programa no Firewall do Windows** | Senão os alunos não conseguem chegar ao servidor |
| Cria o desinstalador (Painel de Controle → Aplicativos) | O placar e o cache ficam em `%LOCALAPPDATA%\DragonBallDex` e não são apagados |

> **Sem senha de administrador?** Execute o instalador com `/CURRENTUSER` (ex.: `DragonBallDex-Setup-2.2.0.exe
> /CURRENTUSER`): ele instala só para aquele usuário. Nos PCs dos **alunos** isso basta. No PC do **professor**, o
> Firewall vai perguntar na primeira vez em que o servidor for aberto (pode pedir a senha de administrador): clique em
> **Permitir acesso** e marque redes privadas **e** públicas.

### Versão portátil
`DragonBallDex-Portatil.exe` funciona sozinho em qualquer pasta. Para usar como **servidor do professor**, crie um
atalho para ele e acrescente ` --servidor` no fim do campo "Destino" do atalho. Na primeira vez, o Firewall vai pedir
permissão: clique em **Permitir acesso** e marque redes privadas **e** públicas.

---

## 3. Usando na aula

### Professor (no computador ligado ao projetor)
1. Abra **Dragon Ball Dex - Servidor do Professor**.
2. O painel mostra, bem grande, o **endereço do servidor** (ex.: `192.168.0.10:8000`).
3. *(Recomendado, se houver internet)* clique em **⬇ Baixar tudo agora** para atualizar as cópias.
4. Deixe o painel no telão. Os alunos aparecem em "Alunos conectados" e cada pedido aparece em "Pedidos chegando".
5. **🗑 Zerar placar** começa uma turma nova. **🌐 Abrir no navegador** mostra a página do servidor (bom para mostrar
   que o servidor "fala HTTP" com qualquer navegador).

### Alunos
1. Abra **Dragon Ball Dex**.
2. Digite o **nome** (é ele que aparece no telão e no placar).
3. Clique em **🔍 Procurar na rede**: o endereço do servidor aparece sozinho. (Se não aparecer, digite o que está no
   telão.)
4. **Conectar ao servidor**. Pronto!

![Tela de conexão](docs/imagens/conexao.png)

### Duelos entre alunos
Na tela **👥 Turma e duelos**, cada aluno vê quem está na sala e se está **Livre**, **Lutando** ou **No quiz**.

1. Ao lado de um colega **livre**, clique em **⚔** (batalha) ou **❓** (quiz).
2. Batalha: escolha o seu lutador e o tipo de poder. Quiz: escolha 3, 5 ou 10 rodadas. **Enviar desafio**.
3. O colega recebe um aviso na hora ("Ana te desafiou!"), escolhe o lutador dele e tem 30 s para **Aceitar** ou
   **Recusar**.
4. Aceito, os dois apps abrem o duelo:
   - **Batalha:** quem joga as rodadas é o **servidor**, e os dois veem exatamente a mesma luta. Cada um tem o seu
     botão **Transformar!** (uma vez por luta).
   - **Quiz:** as **mesmas perguntas** para os dois. Cada um responde no seu ritmo e vê o progresso do colega. Ganha
     quem fizer mais pontos; no empate, quem terminou primeiro.
5. Quem está num duelo não pode ser desafiado. Quem fecha o app (ou clica em **Desistir**) perde por W.O.

**Placar:** vitória = **3 pontos**, derrota = **1 ponto** (por ter participado; derrota por W.O. vale 0). A tela
Turma mostra o **pódio** com os 3 primeiros e a classificação de todos (vitórias/derrotas em batalha e no quiz). O
mesmo placar aparece no painel do professor. As telas Batalha e "Quem é?" do menu são **treino** contra o computador
e não contam pontos.

| | |
|---|---|
| ![Turma e duelos](docs/imagens/turma.png) | ![Duelo de batalha](docs/imagens/duelo_batalha.png) |

### Chat da turma
Os alunos conversam na tela **💬 Chat**: as próprias mensagens aparecem à direita (amarelas), as dos colegas à
esquerda e as do professor no meio, em azul. Quando chega mensagem nova, o menu mostra **💬 Chat (3)**. Cada mensagem
pode ter até 200 caracteres, e cada aluno pode mandar uma a cada 1,5 s (contra spam).

**O professor controla tudo pelo painel** (aba **💬 Chat**, no meio do painel):

| Controle | O que acontece |
|---|---|
| Interruptor **"Chat aberto para a turma"** | Desligado: **ninguém** consegue escrever (os alunos veem "O professor fechou o chat por enquanto") |
| **🔇** ao lado de um aluno (lista da esquerda) | Bloqueia **só aquele aluno**: ele continua lendo, mas não escreve. **🔊** libera de novo |
| **✕** ao lado de uma mensagem | Apaga a mensagem da tela de todos |
| **🧹 Limpar chat** | Apaga todas as mensagens |
| Campo **"Mensagem do professor"** + **📢 Enviar** | Aviso destacado para a turma (funciona mesmo com o chat fechado) |

Esses controles existem **só no painel**: não há nenhum endereço de rede para eles, então nenhum aluno consegue se
desbloquear ou reabrir o chat pelo app. As mensagens ficam apenas na memória do servidor: ao desligá-lo, o chat é
apagado.

| | |
|---|---|
| ![Chat do aluno](docs/imagens/chat.png) | ![Chat no painel do professor](docs/imagens/painel_chat.png) |

### Dicas de atividade
- **Corrida da conexão:** quem aparece primeiro no telão?
- **Torneio da sala:** cada aluno faz 3 duelos de batalha; o pódio mostra os campeões.
- **Desafio do quiz:** duelos de 5 rodadas, perguntas iguais para os dois.
- **Investigação de Redes:** na tela **Rede**, comparar o servidor da sala com a internet (seção 5).

---

## 4. O aplicativo do aluno

| Tela | O que faz |
|---|---|
| 🔎 **Personagens** | Busca pelo nome (aceita erro: `gokuu` → "Você quis dizer Goku?") e filtros de raça, afiliação e gênero. Clique num card para ver a descrição, o planeta de origem e as transformações. |
| ⚔ **Batalha** | Treino: dois lutadores (ou 🎲), luta animada, botão **Transformar!** (uma vez por luta). |
| 🪐 **Planetas** | Os 20 planetas; clique para ver a descrição e quem nasceu lá. |
| 🏆 **Ranking** | Os mais fortes, com barras em escala de logaritmo. |
| ❓ **Quem é?** | Treino do quiz: a imagem começa quadriculada e fica mais nítida a cada erro. |
| 👥 **Turma e duelos** | Quem está na sala (para desafiar), o **pódio** e a classificação da turma (atualiza sozinho). |
| 💬 **Chat** | Conversa da turma, controlada pelo professor. |
| 📡 **Rede** | O raio-X da conexão (seção 5). |

| | |
|---|---|
| ![Personagens](docs/imagens/personagens.png) | ![Batalha](docs/imagens/batalha.png) |
| ![Quiz](docs/imagens/quiz.png) | ![Duelo de quiz](docs/imagens/duelo_quiz.png) |

---

## 5. O que dá para ensinar de Redes

| Onde | Conceito | O que os alunos veem |
|---|---|---|
| Tela de conexão | **Endereço IP e porta** | `192.168.0.10:8000` = "qual computador" + "qual programa" |
| "Procurar na rede" | **Broadcast UDP** | O app grita para a rede inteira e só o servidor responde |
| Chat | **Polling** ("tem mensagem nova depois da nº 42?"), **status 403** (proibido) | No painel, marque "Mostrar as consultas automáticas" e veja os `GET /chat?depois=...` chegando a cada segundo |
| Duelos | **Estado compartilhado no servidor**, **polling** | Os dois apps perguntam ao servidor várias vezes por segundo e desenham a mesma luta |
| Painel do professor | **Cliente-servidor**, **requisições HTTP** | Cada clique de cada aluno vira uma linha: hora, aluno, método (`GET`/`POST`), **status code**, tempo, rota |
| Rede → Conexão | **IP local**, **HTTP × HTTPS**, **DNS**, **TCP**, **TLS** | Na sala não há DNS nem TLS (é `http://` com IP); na internet, há os dois |
| Rede → Pedidos | **Cache** | Pedidos `rede` × `cache`: a 2ª vez nem usa a rede |
| Rede → Testar | **URL, query string, cabeçalhos, JSON** | Montar `?page=2&limit=5`, ver os cabeçalhos e o corpo da resposta |
| Rede → Velocidade | **Latência**, **rede local × internet**, **keep-alive** | Servidor da sala ≈ 1–5 ms × internet ≈ 300 ms (medido: 79 vezes mais rápido) |
| Rede → Experimentos | **4xx × 5xx**, **timeout**, **modo offline** | 404, 400, timeout de 0,001 s, "tirar o cabo" sem tirar o cabo |
| Navegador → `http://IP:8000` | **HTTP é um padrão** | O mesmo servidor responde ao navegador e ao app |

![Servidor da sala x internet](docs/imagens/rede_velocidade.png)

**Rotas do servidor** (dá para abrir no navegador):

| Rota | Resposta |
|---|---|
| `GET /` | Página "o servidor está funcionando" |
| `GET /api/characters` | Personagens, 10 por página (`?page=2`, `?limit=100`) |
| `GET /api/characters?race=Saiyan` | Com filtro: lista pura (como na dragonball-api original) |
| `GET /api/characters/1` | Um personagem, com planeta e transformações |
| `GET /api/planets`, `/api/planets/1`, `/api/transformations` | Planetas e transformações |
| `GET /imagens/...` | As fotos |
| `GET /turma/ping` · `GET /turma/placar` | "Sou um servidor Dragon Ball Dex" · placar da turma |
| `POST /turma/entrar` | O aluno chega e recebe um código (vai no cabeçalho `X-Jogador` dos pedidos seguintes) |
| `GET /turma/sala` | Quem está na sala (livre/lutando/no quiz), desafios recebidos e enviados, duelo atual |
| `POST /turma/desafiar` · `/turma/responder` · `/turma/cancelar` | Os desafios entre alunos |
| `GET /turma/partida/<id>` · `POST .../transformar` · `.../progresso` · `.../desistir` | O duelo (a batalha avança sozinha no servidor) |
| `GET /chat?depois=<id>` · `POST /chat` | Ler as mensagens novas e mandar uma (403 se o chat estiver fechado ou o aluno bloqueado) |

---

## 6. Solução de problemas

| Sintoma | Causa provável | O que fazer |
|---|---|---|
| "Procurar na rede" não acha nada | A rede da escola bloqueia broadcast, ou o PC do aluno está em outra rede (ex.: Wi-Fi × cabo) | Digite o endereço do telão. Confira se todos estão na mesma rede |
| "Não consegui conectar" | Firewall bloqueando o servidor, endereço errado ou servidor desligado | Confira o endereço. No PC do professor: Firewall do Windows → permitir "Dragon Ball Dex" (o instalador já faz isso). Teste no navegador do aluno: `http://IP:8000` |
| Funciona no PC do professor, mas não nos alunos | Firewall do PC do professor (rede marcada como "Pública") | Reinstale como administrador ou permita manualmente o `DragonBallDex.exe` |
| O endereço no telão é `127.0.0.1` | O PC do professor está sem rede | Conecte o cabo/Wi-Fi e abra o servidor de novo |
| A porta mudou para 8001 | A 8000 já estava em uso (outro servidor aberto?) | Use o endereço que aparece no telão |
| "Sem conexão: usando dados salvos" | O servidor caiu, ou o aluno está offline | O app continua funcionando com o que já baixou. Reconecte em "Trocar conexão" |
| Fotos aparecem "sem imagem" | Sem internet e a foto não estava nas cópias | No servidor: "⬇ Baixar tudo agora" quando houver internet |
| "Failed to load Python DLL ... `_internal\python3xx.dll`" | Foi copiado só o `DragonBallDex.exe` de uma pasta de build, sem a pasta `_internal` que fica ao lado dele | Use o **instalador** ou o **`DragonBallDex-Portatil.exe`** (que funciona sozinho) |
| A janela fica maior que a tela, ou os cards da direita aparecem cortados | (corrigido na 2.1) Escala de tela do Windows em 125%/150% | Atualize para a versão 2.1. A janela agora se ajusta e abre maximizada em telas pequenas |
| O aluno não consegue escrever no chat | O professor fechou o chat ou bloqueou aquele aluno (a mensagem aparece no topo da tela do Chat) | No painel: interruptor "Chat aberto" ligado e 🔊 ao lado do nome |
| A lista "Pedidos ao vivo" não mostra os pedidos de sala/chat | Os apps perguntam "tem novidade?" a cada segundo; essas consultas ficam escondidas para não lotar a lista | Marque "Mostrar as consultas automáticas" (bom para mostrar o polling em aula) |
| O botão de desafio está apagado | O colega está num duelo, ou você já está esperando outra resposta | Espere ele terminar (o estado aparece ao lado do nome) |
| Quero testar um computador | — | Abra `DragonBallDex.exe --fumaca` (pelo "Executar" do Windows): o app passa por todas as telas sozinho e grava o resultado em `%LOCALAPPDATA%\DragonBallDex\fumaca.txt` |

---

## 7. Para quem vai mexer no código

Python 3.9+ · `requests`, `customtkinter`, `pillow` · servidor só com a biblioteca padrão (`http.server`).

```
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt

python main.py                         aplicativo do aluno
python main.py --servidor              servidor + painel
python main.py --servidor --sem-janela servidor só no terminal
python main.py --fumaca [--conectar IP:PORTA]
python tests/rodar_testes.py           48 testes (sem internet; o servidor de teste usa 127.0.0.1)
```

**Gerar o instalador** (Windows, com [Inno Setup 6](https://jrsoftware.org/isinfo.php) instalado):

```
pip install -r requirements.txt -r requirements-dev.txt     (com um Python de python.org, não o da Microsoft Store)
python instalador/construir.py        ->  dist_instalador\DragonBallDex-Setup-2.2.0.exe  e  DragonBallDex-Portatil.exe
```

| Pasta | Conteúdo |
|---|---|
| `core/` | Lógica sem interface: dados (`api.py`), imagens, poder/ki, batalha, quiz, filtros, rede, placar (`turma.py`), busca na rede (`descoberta.py`) |
| `servidor/` | O servidor do professor: rotas HTTP, espelho da API, placar da turma, monitor ao vivo |
| `interface/` | CustomTkinter: `app_aluno.py`, `painel_servidor.py`, `telas/`, componentes (card, mini-card...) |
| `dados/` | Cópia dos dados da API (usada sem internet) · `ferramentas/gerar_snapshot.py` atualiza |
| `cache/imagens/` | Fotos que vão dentro do instalador |
| `instalador/` | Ícone, roteiro do Inno Setup e `construir.py` |
| `tests/` | Testes automáticos |
| `docs/` | `API_NOTAS.md` (o que descobrimos da API), `ANALISE.md` e `DECISOES.md` |
| `arquivo_versao_aulas.zip` | A versão anterior (roteiro de aulas, terminal + janelas), guardada |

Dados e imagens: [Dragon Ball API](https://dragonball-api.com). Dragon Ball pertence aos seus detentores (Akira
Toriyama / Bird Studio / Shueisha / Toei Animation). **Uso exclusivamente educacional.**
