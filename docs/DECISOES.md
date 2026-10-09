# Decisões da versão 2.0 (aplicativo + servidor da sala)

| # | Decisão | Por quê |
|---|---|---|
| 1 | O servidor usa só a **biblioteca padrão** (`ThreadingHTTPServer`), sem Flask. | Nenhuma dependência nova, e o HTTP fica "à mostra" (bom para Redes). 30 alunos com pedidos pequenos cabem com folga. |
| 2 | O servidor imita o **formato da dragonball-api** (paginação, filtros com lista pura, mesmos campos). | O cliente reaproveita o `core/api.py` inteiro: só troca o endereço. |
| 3 | As URLs das imagens são reescritas para `http://IP-do-servidor/imagens/...`, e a rota de imagens só aceita caminhos da dragonball-api (sem `..`, só `.webp/.png/.jpg`). | Os alunos não precisam de internet, e o servidor não vira um "proxy aberto" nem expõe arquivos do professor. |
| 4 | `protocol_version = "HTTP/1.1"` no servidor. | Permite keep-alive: a `Session` do aluno reaproveita a conexão (e a comparação `get` × `Session` da tela Rede faz sentido também na rede local). |
| 5 | O servidor responde **404/400 "certinho"**, diferente da API original (400 para id inexistente, 500 para `abc`, 200 vazio). | A tela Rede → Experimentos compara os dois comportamentos. |
| 6 | Uma trava (`Lock`) **por dado** no espelho, mais memória de 10 min. | 30 alunos pedindo a lista = 1 busca; um dado lento não bloqueia os outros. |
| 7 | Placar e monitor com `Lock`; placar salvo em JSON com troca atômica (`os.replace`). | Cada aluno é atendido numa thread; o arquivo nunca fica pela metade. |
| 8 | Descoberta por **UDP broadcast** (porta 50505) + IP manual como alternativa. | "Procurar na rede" evita digitar IP; redes que bloqueiam broadcast continuam funcionando. |
| 9 | O nome do aluno vai no cabeçalho `X-Aluno` de todo pedido. | O painel mostra quem é quem sem login. Não é autenticação (é uma sala de aula). |
| 10 | O app do aluno faz downloads em **threads** (`ThreadPoolExecutor`) e entrega o resultado à janela por `after()`. | A janela nunca trava; só a thread principal mexe nos widgets (regra do Tkinter). |
| 11 | Fotos guardadas em memória já **reduzidas** (máx. 520×720). | As originais chegam a 1435×2597 RGBA (~15 MB descomprimidas cada). |
| 12 | Cache JSON **separado por fonte** (internet × cada servidor). | As URLs das imagens mudam conforme a fonte. |
| 13 | Instalador com o **cache de imagens embutido** (~12 MB) e o snapshot dos dados. | O servidor funciona no laboratório mesmo sem internet. |
| 14 | **Um único `DragonBallDex.exe`**; o servidor é o mesmo exe com `--servidor`. | Instalador menor (~28 MB) e uma regra de Firewall só. |
| 15 | PyInstaller `--onedir` (não `--onefile`) + Inno Setup. | Abre mais rápido e é menos bloqueado por antivírus; o Inno Setup dá atalhos, desinstalador e a regra de Firewall. |
| 16 | Regra de Firewall com `profile=any`. | Muitas redes de escola são classificadas como "Pública" pelo Windows. A regra vale só para o `DragonBallDex.exe`. |
| 17 | Dados graváveis em `%LOCALAPPDATA%\DragonBallDex` (fora da pasta do programa) e não apagados na desinstalação. | `Program Files` não aceita gravação sem administrador; reinstalar não perde o placar. |
| 18 | Build com Python 3.14 de python.org (na 2.0 era o 3.12 da Microsoft Store); código compatível com 3.9+ para quem rodar pelo código-fonte. | O .exe roda em Windows 10/11; o Python da Store é menos confiável para empacotar. |
| 19 | `--fumaca`: o app percorre todas as telas sozinho e grava `fumaca.txt`. | Testar um PC do laboratório (ou um instalador novo) em 1 minuto. |
| 20 | A versão de aulas (terminal + janelas, 18 etapas, roteiro) foi guardada em `arquivo_versao_aulas.zip`. | O professor não precisa mais dela, mas nada foi perdido. |

## Versão 2.1 (duelos entre alunos, pódio, correções)

| # | Decisão | Por quê |
|---|---|---|
| 21 | Duelos por **polling HTTP**: o app pergunta `GET /turma/sala` a cada 1,5 s e o estado da partida a cada 0,5–0,9 s. | Funciona com a biblioteca padrão (sem WebSocket), atravessa qualquer Firewall que já deixe o HTTP passar, e a pergunta também serve de "estou online". |
| 22 | Na batalha, **o servidor joga as rodadas** (uma a cada 1,3 s, calculadas pelo relógio quando alguém pergunta). | Os dois alunos veem exatamente a mesma luta, e ninguém consegue "trapacear" pelo próprio app. |
| 23 | No quiz, as **mesmas perguntas** para os dois, cada um no seu ritmo; empate decidido pelo tempo. | Duelo justo sem precisar sincronizar cliques. |
| 24 | Vitória = 3, derrota = 1, derrota por W.O. = 0. Sumir por 20 s (ou "Desistir") = W.O. | Premia participar, mas não premia abandonar. |
| 25 | Batalha e "Quem é?" do menu viraram **treino** (não contam pontos). | O pódio mede duelos entre alunos, como o professor pediu. |
| 26 | Janelas e grades levam em conta a **escala de tela do Windows** (125%/150%); a janela principal abre maximizada se não couber. | Em outro PC os cards da direita ficavam cortados, porque a janela era maior que a tela. |
| 27 | Além do instalador, um **`DragonBallDex-Portatil.exe`** (PyInstaller `--onefile`). Build com Python de python.org. | O erro "Failed to load Python DLL" acontecia ao copiar só o `.exe` da pasta de build, sem a pasta `_internal`. O portátil funciona sozinho. |

## Versão 2.2 (chat da turma)

| # | Decisão | Por quê |
|---|---|---|
| 28 | O chat usa o mesmo **polling HTTP** dos duelos (`GET /chat?depois=<id>` a cada 1 s com a tela aberta). O contador de não lidas vem junto com `/turma/sala`. | Nenhuma tecnologia nova; o aluno vê o selo "💬 Chat (3)" em qualquer tela. |
| 29 | Os controles do professor (fechar o chat, bloquear, apagar, limpar, aviso) **não têm rota HTTP**: só existem no painel, que roda no mesmo programa do servidor. | Assim é impossível um aluno se desbloquear ou reabrir o chat mandando um pedido "esperto". |
| 30 | O bloqueio é pelo código do aluno na sala (o mesmo nome no mesmo PC reaproveita o código). | Reabrir o app não "limpa" o bloqueio. Trocar de nome cria outro aluno, que aparece no painel e pode ser bloqueado também. |
| 31 | Limites: 200 caracteres, 1 mensagem a cada 1,5 s, caracteres de controle removidos; o app nunca recebe o código dos outros alunos (só "minha: sim/não"). | Contra spam e para ninguém se passar por outro. |
| 32 | As mensagens ficam só na memória (as últimas 300) e somem quando o servidor desliga. | Privacidade: não fica histórico de conversa de alunos gravado no computador. |
| 33 | O painel esconde, por padrão, as consultas automáticas (sala, chat, duelo, placar) da lista "Pedidos ao vivo". | Com 30 alunos seriam ~50 pedidos por segundo; uma caixinha mostra tudo quando o professor quiser explicar o polling. |

## Versão 2.3 (Caça às Esferas)

Plano completo e a lista de ganchos nos arquivos antigos: `docs/PLANO_ESFERAS.md`.

| # | Decisão | Por quê |
|---|---|---|
| 34 | Tudo da caçada em **arquivos novos** (`core/esferas.py`, `core/esferas_cliente.py`, `servidor/rotas_esferas.py`, `interface/aba_cacada.py`, `interface/efeito_dragao.py`, `interface/desenho_esfera.py`, `interface/telas/esferas.py`); nos antigos, só ganchos de 1 a 5 linhas. A caçada nasce **desligada**. | Não quebrar nada do que já funciona: sem clicar em "Iniciar caçada", o comportamento é o da 2.2 (a página `/` fica byte a byte igual, e há um teste para isso). |
| 35 | Código pessoal = **HMAC-SHA256**(segredo da caçada, `"numero:esfera"`) → 5 letras de `23456789ABCDEFGHJKMNPQRSTUVWXYZ`. | Copiar o código do colega não serve, e ninguém calcula o código sem o segredo. Sem 0/O e 1/I/L: ninguém confunde ao digitar. |
| 36 | **Número de caçador** dado na largada (quem está online) ou no primeiro pedido `/esferas/...`, mantido até desligar o servidor. | Não mexer em `POST /turma/entrar`. O número é público (vai na URL) e o `X-Jogador` continua secreto. |
| 37 | O caçador é identificado pelo `X-Jogador` (app) **ou** por `?cacador=<n>` (navegador e terminal). | Navegador e curl não mandam `X-Jogador`. E `?cacador=7&x=5&y=5` vira um bom exemplo de query string. |
| 38 | Esfera 2 = User-Agent com `Mozilla` e **sem** `DragonBallDex`, `python-requests`, `PowerShell` e `curl`. Esfera 7 = `curl/...` ou `PowerShell`. | O app manda `DragonBallDex/2.0` (não `python-requests`), e o PowerShell também diz `Mozilla`. |
| 39 | Status: **409** com a caçada parada (o `/esferas/estado` manda os dados juntos), **429** para "espere 2 s", **403** para "código de outro caçador", **400** para código errado ou URL incompleta, **404 com corpo** na caverna. | Cada status ensina alguma coisa. A tela Esferas mostra o progresso mesmo com a caçada pausada. |
| 40 | O grito usa a **mesma porta UDP 50505** da descoberta, com outro prefixo (`DBDEX-ESFERA`). A resposta **não é JSON puro**. O gancho na descoberta fica dentro de `try/except`. | Dois sockets na mesma porta não funcionam de forma confiável no Windows. Um app 2.2 que recebesse a resposta cairia no `except ValueError` e ignoraria; e a resposta vai só para o socket de quem gritou. |
| 41 | Plano B do grito: a 💡 dica extra 6 libera no app a opção **unicast** (direto para o IP do servidor). | Uma dica sozinha não faz o broadcast passar numa rede que bloqueia. E broadcast × unicast vira assunto de aula. |
| 42 | As dicas aparecem em sequência, mas o **resgate não exige ordem**. | Quem travar numa esfera (ex.: rede sem broadcast) não fica preso. |
| 43 | Avisos para a turma com `chat.mensagem_do_professor()`, chamada **fora da trava** da caçada. | Sem rota nova e sem polling novo (o aviso já chega pelo contador do chat). Fora da trava, o chat nunca espera a caçada. |
| 44 | O efeito do 1º lugar dura **pelo menos 8 s e espera o pedido** (até 30 s); um clique fecha. Os seguintes ganham um aviso menor. | A turma assiste à escolha do pedido. |
| 48 | Depois do clarão, um **dragão verde desenhado com formas do Canvas** (`interface/desenho_dragao.py`) nasce das esferas, dá uma volta e mostra a cabeça de olhos vermelhos. Substitui o "sem desenho do dragão" da primeira versão da 2.3, a pedido do professor. | A dragonball-api não tem o Shenlong (nem o Porunga). Um desenho próprio, feito de linhas e círculos, evita trazer imagem de fora e roda leve (~5 ms por quadro em 1920×1080). |
| 49 | O professor quis o dragão **igual a uma figura** que ele trouxe: o efeito usa `interface/imagens/shenlong.png` (fundo preto), que "acende" trocando entre 17 versões de luminosidade, com as esferas num "U" em volta. Sem o arquivo, volta o desenho da decisão 48. A figura fica fora do git (`.gitignore`) e entra no instalador pelo `construir.py`. | O Tkinter não tem transparência, mas com o fundo preto a troca de luminosidade parece um "acender". O repositório é público: a figura pode ser arte de outra pessoa, então só vai para o GitHub se o professor decidir. |
| 45 | A grade do painel é um `Canvas` que **ajusta a altura das linhas** para caber todos os alunos; o botão **⛶ Telão** mostra a mesma grade em tela cheia. | A coluna do meio do painel tem ~600 px: estreita para 15 alunos no projetor. |
| 46 | Resultado em CSV com `;` e UTF-8 com BOM, em `%LOCALAPPDATA%\DragonBallDex\cacadas\`. | O Excel em português abre certinho, com acentos. |
| 47 | Resposta da esfera 7 só em **ASCII** (sem acento nem emoji) quando o cliente é um terminal. | O `cmd` mostra o UTF-8 todo embaralhado. |
| 50 | Guia **"Como funciona?"** do aluno (`interface/ajuda.py`): um botão **❔** no cabeçalho de **todas** as telas (criado pelo `cabecalho()` comum) abre o guia já na explicação daquela tela; ele abre sozinho na 1ª vez que cada aluno (pelo nome) conecta no PC (`ajuda_vista_por` no `config.json`). | Não criar um 10º item no menu (o rodapé cortaria em telas menores). Pelo nome, e não pelo PC: cada aluno novo naquele computador vê o guia uma vez, e o `--fumaca` ("Teste de fumaca") não gasta a primeira vez de ninguém. Um teste garante que toda tela do menu tem explicação. |

## Versão 2.4 (Conquista de Territórios, Mapa do Radar, Grito de Guerra, Modo Demonstração)

Plano completo, ganchos nos arquivos antigos e as 10 decisões aprovadas pelo professor em 08/10/2026:
`docs/PLANO_TERRITORIOS.md`.

| # | Decisão | Por quê |
|---|---|---|
| 51 | Tudo novo em **arquivos novos** (`servidor/conquista.py`, `rotas_conquista.py`, `gritos.py`, `rotas_gritos.py`, `baixar_audio.py`, `mundo_demo.py`, `core/conquista_cliente.py`, `gritos_cliente.py`, `grito_padrao.py`, `demo.py`, `interface/mapa_galaxia.py`, `radar.py`, `audio.py`, `som_da_turma.py`, `aba_conquista.py`, `aba_gritos.py`, `telas/conquista.py`); nos antigos, ganchos curtos. A Conquista nasce **desligada**. | Mesmo cuidado da 2.3: sem o professor ativar nada, as rotas, os JSON e as telas antigas ficam como na 2.3.2. Os 80 testes antigos não mudaram. |
| 52 | **Teto de força 27** (`min(força, 27)`) só nas lutas da Conquista, inclusive nos neutros. *(aprovada: decisão 1 do plano)* | Medido: o Grand Priest (força 103) vencia 100% das lutas. Com o teto ele vira "um dos fortes" e a escolha do lutador volta a importar. O motor, os duelos e o treino não mudam. |
| 53 | Um só **tipo de poder** por Conquista (o professor escolhe no painel); o atacante escolhe só alvo e lutador. *(decisão 2)* | O motor usa uma métrica por luta. |
| 54 | As invasões usam a mesma `PartidaBatalha` dos duelos, com id `cq-…`, e passam pela rota que já existia (`/turma/partida/<id>`), mas **moram na Conquista**, nunca na Sala. | Reaproveita o motor e a tela de duelo, e nada vai para o placar da turma. |
| 55 | **Uma trava por Conquista**: tudo é conferido dentro dela, então dois cliques no mesmo planeta ao mesmo tempo → só **um** passa (o outro recebe **409**). Status: **403** (planeta seu / luta de outro), **404** (território que não existe), **409** (ocupado, escudo, parada), **429** (espera entre invasões e troca de guardião). Escudo 45 s, espera 20 s, troca de guardião a cada 60 s. | Concorrência de verdade para discutir em aula, e cada status ensina algo. Avisos do chat e ganchos (som) são entregues **fora** da trava. |
| 56 | O Guardião **se transforma sozinho** abaixo de 50% de vida. *(decisão 8)* | Equilibra com o "Transformar!" do atacante. |
| 57 | **Encerrar** com luta em andamento cancela a luta; o planeta fica com o defensor. *(decisão 9)* | O resultado final não depende de luta pela metade. |
| 58 | Ranking: territórios → conquistas → defesas → quem chegou antes àquele número. Quem chega depois entra **sem planeta** (invade um neutro); ninguém é eliminado. | Desempate previsível, e ninguém fica parado sem jogar. |
| 59 | O **mapa do radar** é só um cliente mais amigável da **mesma** rota: cada clique vira exatamente `GET /esferas/radar?cacador=N&x=X&y=Y` (mostrado embaixo do mapa). Achou: resgata sozinho, respeitando os 2 s. Interruptor "Mapa do radar no app" no painel (ligado por padrão). | A rota, o 400 e o gabarito não mudam; o aluno vê que app e navegador fazem o mesmo pedido. |
| 60 | O áudio do grito é baixado pelo **servidor** (um *proxy*), com proteção contra **SSRF**: só `http/https` nas portas 80/443; **todos** os IPs do nome precisam ser públicos (`ipaddress`); a conexão vai para o IP já conferido (contra *DNS rebinding*), com o nome certo no `Host` e no TLS; cada redirecionamento é conferido de novo (no máximo 3); 5 s de tempo; até 500 KB; formato pelos **primeiros bytes** (ID3/MPEG, RIFF/WAVE, OggS), não pela extensão. Status 400/403/413/415/429/502. | Sem isso, um aluno poderia usar o servidor para "espiar" a rede da escola (roteador, impressoras) ou mandar um arquivo disfarçado. Os testes usam um servidor HTTP local, sem internet. |
| 61 | Link recusado **só de olhar** o endereço (400: YouTube, sem `http`) não gasta a vez de trocar o grito (10 s); tentativas que usam a rede gastam. | O aluno corrige o link na hora, e quem testa endereços internos continua limitado. |
| 62 | A frase do aluno **pode** ter KAMEHAMEHA; o **sistema** nunca coloca a palavra mágica sozinho em evento, feed ou telão (o grito UDP não repassa a palavra digitada; a frase padrão é "Pela honra da Terra!"). *(decisão 3, ajustada pelo professor)* | Há teste para isso. |
| 63 | O som chega a **qualquer tela** pelo campo `novidades` do `/turma/sala` (já perguntado a cada 1,5 s), que só existe com a Caça ou a Conquista valendo. Mudou? O app pede `/gritos/eventos` e pré-carrega os áudios da turma. *(decisão 4)* | Sem polling novo; desligado, o JSON é o da 2.3.2. |
| 64 | Biblioteca de áudio: **`miniaudio`** (só no app do aluno), com `winsound` de reserva (só WAV). Comparação: `pygame-ce` traz o SDL inteiro (vários MB de DLLs) para usar só o mixer; `miniaudio` é um único módulo compilado (~1 MB) que decodifica mp3/wav/ogg/flac, tem *wheels* do Python 3.9 ao 3.14 e funciona no PyInstaller com `--hidden-import _cffi_backend` (conferido num programa de teste); `winsound` vem com o Python, mas só toca WAV e sem volume. Se nada funcionar, o app segue **mudo** com "sem áudio neste PC", sem travar. *(decisão 10)* | O instalador quase não cresce. O servidor continua só com a biblioteca padrão. |
| 65 | Player com **fila**: um som tocando e no máximo 2 esperando (o resto é descartado), cada som cortado em 6 s, volume e mudo por PC. `QUEM_OUVE = "todos"` é uma linha em `servidor/gritos.py` (trocar por `"envolvidos"` se a sala ficar barulhenta). | Nunca dois sons ao mesmo tempo no mesmo PC. |
| 66 | Moderação **mínima** e só no painel (aba 📣 Gritos): ouvir ▶ e bloquear 🔇 (um ou vários). Bloqueado volta na hora ao grito padrão e não troca até ser liberado. | Mesmo princípio do chat: nenhum controle do professor tem rota de rede. |
| 67 | **Modo demonstração** = um segundo **mundo** (`MundoDemo`) com Sala, Chat (fechado: 403), Caça (sempre valendo, números 901+), Conquista, Gritos e placar próprios. `mundo_do_pedido()` escolhe o mundo e as **mesmas** funções de rota recebem esse objeto. | Isolamento por construção, como o professor preferiu: não há `if demo` espalhado pelas rotas. |
| 68 | Entra no demo só quem manda `X-Demo` com o **token** certo (`secrets`, sorteado a cada início, só na memória, comparado com `compare_digest`) **e** vem de 127.0.0.1. O painel passa o token ao app por **variável de ambiente** (não aparece na linha de comando) e o app apaga a variável ao ler. `--demo` sem token abre o app normal. | Nenhuma rota, argumento ou nome ("Professor", "demo") liga o modo. |
| 69 | Navegador/curl/UDP (que não mandam o token): no **próprio PC do servidor**, `?cacador=901` ou mais vai para o ensaio *(decisão 5)*; **sem** número (a página `/` com o link da esfera 2 e o formulário da Área do caçador), também, mas só quando não há Caça de verdade valendo e só enquanto o app do ensaio está aberto. *(decisão minha)* | Sem isso, a esfera 2 do ensaio não tinha como começar no navegador. Um aluno nunca chega por 127.0.0.1. |
| 70 | 2 **alunos-robô** 🤖 aceitam desafios, jogam o quiz e invadem planetas neutros ou do outro robô, **nunca o do professor**; começam com 2 planetas cada (4 de robôs). Usam o grito **padrão**. *(decisão minha)* | O professor está apresentando: um robô atacando o planeta dele atrapalharia. No ensaio só toca o grito padrão ou o do próprio professor, como pedido. |
| 71 | O mundo demo nasce no clique em 🎓 e **some quando o app do ensaio fecha** (o painel acompanha o processo); clicar de novo fecha o anterior e começa do zero. O botão fica no topo do painel. | Nada do ensaio fica rodando à toa; no rodapé não havia espaço em telas de 1366 px. |
| 72 | Pedidos do demo: `Monitor.registrar(demo=True)` marca o pedido e **não** conta como aluno conectado; no "Pedidos ao vivo" aparecem em roxo com "🎓 demo" **no fim da linha**, com interruptor para esconder. | O emoji no meio desalinhava as colunas da fonte de largura fixa. |
| 73 | Subtítulo da Batalha: "O vencedor entra no Hall da Fama do telão." *(decisão 6)* Menu com rolagem que só aparece quando precisa, itens de 38 px. *(decisão 7)* | O texto antigo prometia pontos que a batalha de treino não dá; com 10 itens o menu não cabia em 1366×768 a 125%. |
| 74 | Correção (bug da 2.3): a tela Esferas e o guia ❔ usavam `bind("<Configure>")` sem `add="+"`, o que apagava o ajuste de rolagem do `CTkScrollableFrame`. Com o mapa do radar, a página ficou mais alta que a janela e o campo "Resgatar" sumia. Agora `add="+"`. | Achado ao tirar os prints do README. |
| 75 | `GET /turma/ping` passa a dizer versão `"2.4"`. | Os apps só conferem o campo `servico`; a versão é informativa. |
