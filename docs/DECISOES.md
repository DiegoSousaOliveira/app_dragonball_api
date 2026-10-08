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
