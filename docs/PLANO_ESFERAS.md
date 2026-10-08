# Plano: Caça às Esferas do Dragão (versão 2.3.0)

> 07/10/2026 · branch `cacada-esferas` (a `main` / tag `v2.2.0` continua com a versão que funciona).
> Antes de começar: **48 testes passando** (`python tests/rodar_testes.py`, Python 3.14 do `.venv`).

A caçada é um **acréscimo desligado por padrão**: sem clicar em "🐉 Iniciar caçada", o app e o servidor se comportam
exatamente como na 2.2. Todo o código novo fica em arquivos novos; nos arquivos existentes entram só **ganchos** de 1 a
5 linhas, listados na seção 3.

---

## 1. O que a leitura do código mudou no pedido

| # | Achado | Consequência no plano |
|---|---|---|
| A | O app **não** se identifica como `python-requests`: todo pedido sai com `User-Agent: DragonBallDex/2.0` (`core/api.py:28`), inclusive os da tela Testar. | Esfera 2 aceita o pedido se o User-Agent tem `Mozilla` e **não** tem `DragonBallDex`, `python-requests`, `PowerShell` nem `curl`. |
| B | O `Invoke-WebRequest` do PowerShell manda `Mozilla/5.0 (...) WindowsPowerShell/5.1...`, ou seja, também contém `Mozilla`. | Por isso o `PowerShell` entra na lista de exclusão da esfera 2. Na esfera 7, valem `curl/...` e qualquer User-Agent com `PowerShell` (o 5.1 do Windows e o 7). |
| C | A tela **Rede → Testar** já envia o `X-Jogador` (ela copia os cabeçalhos da sessão, `core/rede.py:24`). **Mas** o menu só tem rotas fixas e `requisicao_crua` sempre põe `/api` na frente (`core/rede.py:44`). Do jeito que está, ela não alcança `/esferas/pista`. | São 2 ganchos: a opção `/esferas/pista` no menu da tela Testar e, só para caminhos que começam com `/esferas/`, montar a URL sem o `/api`. O resto da tela não muda. |
| D | O app de descoberta faz `json.loads(resposta)` e depois `info['porta']`. Se a resposta do grito fosse um JSON sem `porta`, o app 2.2 quebraria com `KeyError`. | A resposta do grito começa com o prefixo `DBDEX-ESFERA-RESPOSTA ` e, por isso, **não é JSON válido**: o app antigo cai no `except ValueError: continue` e ignora. Além disso, ela vai só para o socket de quem gritou, nunca para o da busca. |
| E | `chat.mensagem_do_professor()` corta o texto em **200 caracteres**. | Todas as dicas extras e os avisos cabem em 200 caracteres, e um teste garante isso. |
| F | O Piccolo nasceu em **"Namek"** (`dados/snapshot_personagens.json`). | A rota `caverna-namek` e a dica ficam como no pedido. |
| G | As esferas 4 e 5 são abertas no **navegador**, que não manda `X-Jogador`. | Cada rota identifica o caçador pelo `X-Jogador` (quando vem do app) **ou** por `?cacador=<n>` na URL. Ex.: `/esferas/radar?cacador=7&x=3&y=5`. Isso é bom para a aula: uma query string com 3 parâmetros. |
| H | `POST /turma/entrar` não pode mudar (regra 1). | O número de caçador é dado **sem mexer nessa rota**: quando a caçada começa (todos os alunos online na sala) ou no primeiro pedido `/esferas/...` do aluno. O número continua o mesmo até o servidor desligar, mesmo depois de "Nova caçada". |
| I | Menu lateral do aluno, medido nesta máquina: hoje precisa de **604 px**, com o 9º item **650 px**. Altura útil: 1366×768 a 100% = 697 · 1920×1080 a 150% = 673 · **1366×768 a 125% = 558**. | Só a combinação 1366×768 a 125% corta o rodapé do menu, e **ela já corta hoje**. Veja a decisão 9. |
| J | O código roda como "código-fonte" grava em `dados_usuario/` (`core/armazenamento.py:19`), pasta que não estava no `.gitignore`. | Acrescento `dados_usuario/` ao `.gitignore` (lá ficam o nome do aluno, o placar e agora os CSV das caçadas). |

---

## 2. Arquivos novos

| Arquivo | O que tem |
|---|---|
| `core/esferas.py` | **Lógica pura**, sem rede e sem janela: as 7 esferas (dicas, dicas extras, conceitos), código pessoal por HMAC, normalização do código, radar, classe `Cacada` (estados, números de caçador, resgate com limite de 2 s, ordem de conclusão, bônus, pedidos, tempo, eventos para o telão), formato das mensagens UDP do grito e o CSV do resultado. Estado em memória protegido por `threading.Lock`. |
| `core/esferas_cliente.py` | O lado do aluno: `estado()`, `resgatar()`, `pedir()` (HTTP, registrados no log da tela Rede) e `gritar()` (UDP broadcast). |
| `servidor/rotas_esferas.py` | As rotas `/esferas/...`, o link condicional da página `/`, a resposta ao grito UDP, `iniciar_cacada()` (pega os alunos online da sala) e `salvar_resultado()` (CSV). |
| `interface/telas/esferas.py` | A tela **🐉 Esferas** do aluno e a janelinha do pedido (30 s). |
| `interface/aba_cacada.py` | A aba **🐉 Caçada** do painel e a janela **⛶ Telão** (a mesma grade, só que maior e em tela cheia). |
| `interface/efeito_dragao.py` | O efeito em tela cheia, os avisos menores no telão e o som (`winsound`, com mudo). |
| `interface/desenho_esfera.py` | Desenha uma esfera (círculo laranja com degradê, brilho e N estrelas vermelhas; apagada = cinza) num `Canvas`. Segue o estilo de `instalador/gerar_icone.py`. |
| `ferramentas/simular_cacada.py` | `--conectar IP:PORTA [--alunos 15] [--velocidade 2]`: alunos falsos que entram na sala e acham as esferas **do mesmo jeito que um aluno** (User-Agent de navegador, cabeçalho, radar, 404, grito UDP, curl), cada um num ritmo. Serve para ensaiar o telão sozinho. |
| `tests/test_esferas.py` | Testes da lógica (seção 7). |
| `tests/test_rotas_esferas.py` | Testes das rotas, do UDP e dos 15 alunos simultâneos (seção 7). |

---

## 3. Ganchos nos arquivos existentes (lista completa)

| Arquivo · função | O que entra | Por quê |
|---|---|---|
| `servidor/rotas.py` · `TratadorDragonBall._atender` | `if partes.path.startswith("/esferas/"): resposta = rotas_esferas.atender(...)` antes do `if metodo == "GET"` | É o único lugar com acesso aos cabeçalhos (`User-Agent`) e ao corpo. Fica dentro do mesmo `try`, então 400/403/500 continuam tratados igual. Nenhuma rota antiga passa por ali. |
| `servidor/rotas.py` · `rota_get` (só o `/`) | `PAGINA_INICIAL.replace("</ul>", "</ul>" + rotas_esferas.link_da_area(app))` | O link "🐉 Área do caçador". Com a caçada desligada, `link_da_area` devolve `""` e a página fica **byte a byte igual** (há um teste para isso). |
| `servidor/rotas.py` · `VERSAO` | `"2.2"` → `"2.3"` (na etapa final) | É a versão que o `/turma/ping` informa. O formato do JSON não muda, só o valor. |
| `servidor/aplicacao.py` · `ServidorDragonBall.__init__` | `self.cacada = Cacada(avisar=self.chat.mensagem_do_professor)` | O estado da caçada mora no servidor. O aviso "🐉 Ana invocou o dragão!" usa a função interna do chat, sem rota nova. |
| `servidor/aplicacao.py` · `iniciar` | passa `ao_receber_outro=...` para o `RespondedorDeDescoberta` | Liga o grito UDP na **mesma porta 50505**. Dois sockets na mesma porta não funcionam de forma confiável no Windows. |
| `core/descoberta.py` · `RespondedorDeDescoberta.__init__` e `_escutar` | parâmetro opcional `ao_receber_outro=None` + um `elif` **depois** do `if dados == PERGUNTA:` (que não muda), dentro de `try/except Exception` | (a) a descoberta continua idêntica; (c) uma mensagem estranha não derruba o laço. Sem o parâmetro, o comportamento é exatamente o da 2.2. |
| `core/rede.py` · `requisicao_crua` | só se `caminho.startswith("/esferas/")`: base = `URL_BASE` sem o `/api` final | Para a tela Testar alcançar `/esferas/pista` (achado C). Os outros caminhos não mudam. |
| `interface/telas/rede.py` · `TelaRede.ENDPOINTS` | mais uma opção: `"/esferas/pista"` | Idem. Nada mais muda na tela. |
| `interface/app_aluno.py` · `MENU` | `("esferas", "🐉   Esferas", TelaEsferas)` entre Chat e Rede, mais o `import` | O item novo do menu, no padrão dos outros. |
| `interface/painel_servidor.py` · `CONSULTAS_AUTOMATICAS` | mais `"/esferas/estado"` | O polling da tela Esferas fica escondido como as outras consultas automáticas. `pista`, `radar`, `caverna-*`, `navegador`, `terminal` e o `POST /esferas/resgatar` **aparecem** no log. |
| `interface/painel_servidor.py` · `criar_colunas` | `AbaCacada(abas.add("🐉 Caçada"), self.servidor)`, mais o `import` | A aba nova, ao lado de "📡 Pedidos ao vivo" e "💬 Chat". Ela tem o próprio ciclo de atualização, então o `atualizar()` do painel não muda. |
| `interface/fumaca.py` · `rodar` (roteiro) | o passo `(2000, "esferas", lambda: app.mostrar("esferas"))` | A tela Esferas no `--fumaca`. |
| `instalador/DragonBallDex.iss` | `Versao "2.3.0"` | Versão. |
| `README.md`, `docs/DECISOES.md`, `.gitignore` | seções novas, decisões da 2.3, `dados_usuario/` | Documentação. |

**Não mudam:** `core/turma.py`, `servidor/sala.py`, `servidor/placar.py`, `servidor/chat.py`, `servidor/monitor.py`,
`servidor/espelho.py`, a autenticação por `X-Jogador` e os 48 testes antigos (nenhuma linha).

---

## 4. As esferas, rota por rota

O caçador é identificado pelo `X-Jogador` (app) **ou** por `?cacador=<n>` (navegador/terminal). Um número que não
existe dá **400**. Antes da largada, todas as rotas `/esferas/*` respondem **409**. Os corpos das páginas abertas no
navegador são texto/HTML (não JSON), porque é isso que o aluno vai ler.

| Nº | Rota | Respostas |
|---|---|---|
| 1 | (automática) | Resgatada sozinha quando a caçada começa, para cada aluno online, ou no primeiro pedido de quem chegar depois. |
| 2 | `GET /esferas/navegador` | Sem `cacador`: página com o campo "seu número de caçador" (formulário GET). Com `cacador` e User-Agent de navegador: **200** com o código. App, curl ou PowerShell: **403** "Só aceito visitas de navegadores. Eu sei quem você é pelo User-Agent!" |
| 3 | `GET /esferas/pista` | **200**, corpo "A esfera não está aqui... olhe com mais atenção 👀" e cabeçalho `X-Esfera: ESF-XXXXX`. |
| 4 | `GET /esferas/radar?cacador=7&x=3&y=5` | Sem parâmetro ou valor fora de 0..10: **400** com a explicação de como montar a URL. Errou: **200** "❄️ Frio / 🌤 Morno / 🔥 Quente / 🔥🔥 Fervendo!" pela distância (passos na horizontal + na vertical: 1 = fervendo, até 3 = quente, até 6 = morno). Acertou: **200** com o código. |
| 5 | `GET /esferas/caverna-<nome>` | O nome passa por `unquote`, minúsculas e sem acento. `namek`: **404** "Caverna vazia... ou não? 💎" + o código. Outra caverna: **404** "Caverna vazia". |
| 6 | UDP 50505 | O app manda `DBDEX-ESFERA <numero> <palavra>` por broadcast. Com `KAMEHAMEHA` (maiúsculas/minúsculas e acento tanto faz), o servidor responde **só ao remetente** `DBDEX-ESFERA-RESPOSTA {"ok": true, "codigo": ...}`. Palavra errada: `{"ok": false, "mensagem": ...}`. O telão mostra "📡 Alguém gritou na rede!" (no máximo 1 vez a cada 3 s por caçador). |
| 7 | `GET /esferas/terminal?cacador=7` | User-Agent `curl/...` ou com `PowerShell`: **200** com o código, em texto **sem acentos nem emoji** (o `cmd` mostra UTF-8 errado). Navegador ou app: **403** "Use o terminal, caçador!" |

**Rotas do app (JSON):**

| Rota | Respostas |
|---|---|
| `GET /esferas/estado` | **200** com a caçada ativa: número, esferas, dica atual (com IP, porta e número já preenchidos), dica extra (se o professor mandou), tempo restante, pontos, pedido pendente. Parada: **409**, mas com os mesmos dados no corpo (para a tela mostrar o progresso). Servidor 2.2: **404**, e a tela mostra "Este servidor não tem a Caça às Esferas". |
| `POST /esferas/resgatar` `{"codigo"}` | **200** "Você encontrou a esfera de 3 estrelas!" (ou "você já tinha essa"). Código de outro caçador: **403** "Essa esfera pertence a outro caçador! 👀". Código errado: **400**. Antes de 2 s desde a última tentativa: **429** "Calma! Espere 2 segundos...". Caçada parada: **409**. |
| `POST /esferas/pedido` `{"pedido": 1, 2 ou 3}` | **200**. Pedido sem ter completado, ou já escolhido: **400**. |

**Código pessoal:** `HMAC-SHA256(segredo, f"{numero}:{esfera}")` → 5 caracteres de `23456789ABCDEFGHJKMNPQRSTUVWXYZ`
(sem 0/O, 1/I/L) → `ESF-XXXXX`. São 31⁵ ≈ 28,6 milhões de códigos; com 1 tentativa a cada 2 s, chutar é inútil. Para
reconhecer "código de outro caçador", o resgate compara com os 7 códigos de cada caçador inscrito (≈ 100 HMAC para 15
alunos, instantâneo). As coordenadas do radar também saem do HMAC (`f"{numero}:radar"`).

**Ordem:** as dicas aparecem uma de cada vez (a dica N+1 só depois do resgate da N), mas o **resgate não exige ordem**.
Quem descobrir a 7ª antes da 6ª pode resgatar. Isso evita que um aluno fique travado se a rede bloquear o grito.

---

## 5. Estados, pontos, pedido e telão

**Estados:** `aguardando` → (Iniciar) → `ativa` ⇄ (Pausar/Retomar) `pausada` → (Encerrar ou fim do tempo) → `encerrada`.
"Nova caçada" (com confirmação) gera um segredo novo, zera o progresso e volta para `aguardando`. Pausar também
congela o relógio e os 30 s do pedido.

**Pontos (placar SEPARADO do placar da turma):** 1 por esfera + bônus de conclusão (1º +5, 2º +3, 3º +2) + pedidos.
Desempate: mais esferas e, depois, quem chegou primeiro.

**Pedido:** ao completar, o app abre a escolha entre "+3 pontos na caçada para mim", "+1 ponto na caçada para todos da
turma" e "Ser o ajudante do professor na próxima atividade". Sem escolha em 30 s, vale a primeira. O "+1 para todos"
vale para quem já é caçador naquele momento.

**Telão:**
- **1º a completar:** efeito em tela cheia. O fundo escurece (transparência da janela), as 7 esferas giram e brilham,
  vem um flash e o texto "O DRAGÃO FOI INVOCADO!" com o nome do aluno. Embaixo aparecem as 3 opções de pedido enquanto
  ele escolhe, e a escolhida acende. O efeito dura **pelo menos 8 s** e espera o pedido (no máximo os 30 s). Um clique
  ou Esc fecha antes.
- **Os seguintes:** aviso menor no topo da tela: "🐉 Bruno também invocou o dragão! (2º lugar)" e, depois, o pedido.
- **Chat:** com `mensagem_do_professor()`, sai "🐉 Ana invocou o dragão! (1º lugar)" e depois "🎁 Pedido da Ana: ...".
- **Som:** `winsound` (ignorado fora do Windows): um "plim" curto a cada esfera e uma melodia no dragão. Há um botão 🔊/🔇 na aba.

**Aba 🐉 Caçada:** Iniciar · Pausar/Retomar · Encerrar · Nova caçada · tempo (sem limite / 10 / 15 / 20 / 30 / 45 min) ·
🔊 · **⛶ Telão**. Abaixo: contagem regressiva grande, a grade ao vivo (uma linha por aluno, "07 Ana" + 7 esferas +
pontos, desenhada num `Canvas` que **ajusta o tamanho das linhas para caber todo mundo**), o pódio, o feed
("10:42 · Ana encontrou a ★★★ (Cabeçalhos)") e os botões 💡1 a 💡7 de dica extra. Ao encerrar: o CSV vai para
`%LOCALAPPDATA%\DragonBallDex\cacadas\cacada_<data_hora>.csv` (`;` e UTF-8 com BOM, para o Excel abrir com acentos),
com um botão **📂 Abrir pasta**. Como a aba fica na coluna do meio do painel (≈ 600 px), o botão **⛶ Telão** abre a mesma
grade em tela cheia, com letras grandes para o projetor.

**Tela 🐉 Esferas do aluno:** "Seu número de caçador: 07", as 7 esferas (apagadas/acesas, com uma animação curta ao
acender), a dica atual (+ a dica extra, em azul, se o professor mandou), o campo do código + **Resgatar**, a área do
grito (palavra mágica + **📡 Gritar na rede**) e o tempo restante. Pergunta `GET /esferas/estado` a cada 1,5 s **só
enquanto está visível**. Sem servidor: "A caçada precisa do servidor da sala".

---

## 6. Compatibilidade

| Situação | O que acontece |
|---|---|
| Caçada nunca iniciada | Nenhuma rota antiga muda, a página `/` fica idêntica e o UDP responde à descoberta como antes. |
| App 2.2 + servidor 2.3 | Funciona normalmente. Ele nunca pede `/esferas/*`, e a resposta do grito não chega ao socket da busca e nem é JSON (achado D). *Limitação:* se ele estiver online na largada, aparece na grade com a esfera 1. |
| App 2.3 + servidor 2.2 | `/esferas/estado` → 404 → "Este servidor não tem a Caça às Esferas". O resto do app funciona. |
| "Usar sem servidor" | "A caçada precisa do servidor da sala". |
| Descoberta UDP | O `if dados == PERGUNTA` e a resposta continuam iguais. Mensagens novas passam por `try/except`. Teste: grito + lixo + descoberta antiga em seguida, que precisa continuar funcionando. |
| Python 3.9 | Sem `match`, sem `X | Y` nas anotações. Confiro com `ast.parse(..., feature_version=(3, 9))` (não há 3.9 nesta máquina para rodar de verdade). |
| Dependências | Nenhuma nova: `hmac`, `hashlib`, `csv`, `socket`, `winsound` são da biblioteca padrão. |

---

## 7. Testes

- **`tests/test_esferas.py`** (lógica, com o relógio passado como parâmetro, sem `sleep`): código pessoal (o de um
  caçador não vale para outro), formato e alfabeto, normalização (`" esf-7kq2m "`, `"ESF 7KQ2M"`, `"7kq2m"`), radar
  (frio/morno/quente/fervendo/acerto), limite de 2 s, esfera 1 automática, dicas em sequência, ordem de conclusão e
  bônus, os 3 pedidos e o padrão depois de 30 s, pausar/retomar/encerrar/nova caçada, fim pelo tempo, dicas extras e
  avisos com até 200 caracteres, mensagens UDP, CSV.
- **`tests/test_rotas_esferas.py`** (servidor de teste em 127.0.0.1): os 409 antes da largada; 403/200 por User-Agent
  (navegador × app × curl × PowerShell); cabeçalho `X-Esfera`; radar 400/200; caverna 404 com o código no corpo;
  resgate 200/400/403/429; a página `/` idêntica sem caçada e com o link durante; a tela Testar
  (`rede.requisicao_crua("/esferas/pista")`) chegando com o `X-Jogador`.
- **UDP:** o grito recebe o código **e**, em seguida, `procurar_servidores()` continua achando o servidor igual ao
  teste antigo (também depois de mandar lixo na porta).
- **15 alunos simultâneos:** 15 threads entram, acham e resgatam as 7 esferas ao mesmo tempo. No fim, cada uma tem as
  7, a ordem de conclusão vai de 1 a 15 sem repetir, os bônus estão certos e não houve nenhum 500.
- **Os 48 testes antigos** continuam sem nenhuma mudança. O `--fumaca` ganha a tela Esferas.

---

## 8. Etapas (um commit pequeno por etapa, sempre com todos os testes passando)

1. Plano + `.gitignore` · 2. Lógica (`core/esferas.py` + testes) · 3. Rotas HTTP (+ testes) · 4. Grito UDP (+ testes) ·
5. Aba do painel, telão e efeito · 6. Tela do aluno (+ fumaça) · 7. Simulador + teste dos 15 alunos ·
8. Versão 2.3.0, README e DECISOES, e tag `v2.3.0`. Depois disso, eu paro e te mostro os comandos de `push`.

---

## 9. Decisões que preciso que você aprove

| # | Decisão | Minha proposta |
|---|---|---|
| 1 | Mensagem com a caçada **pausada** | O pedido diz "A caçada ainda não começou 🐉" também na pausa. Proponho manter o **409** mas com a mensagem **"A caçada está pausada pelo professor ⏸"**, que é mais clara para o aluno (a seção 4 do pedido fala em "caçada pausada"). Antes da largada fica a mensagem original. |
| 2 | Status dos erros do resgate | **429** para "espere 2 s" (é o status certo, "muitos pedidos") · **403** para "código de outro caçador" · **400** para "código errado". |
| 3 | Plano B do grito (rede que bloqueia broadcast) | Quando o professor manda a 💡 dica extra da esfera 6, aparece na tela do aluno a opção **"Mandar direto para o servidor (unicast)"**. O pacote continua sendo UDP, só que com o endereço certo. Isso rende uma ótima comparação broadcast × unicast e resolve o problema de verdade (uma dica sozinha não faria o broadcast passar). |
| 4 | Dicas extras | Além do aviso no chat (como pedido), a dica extra também aparece na tela Esferas, embaixo da dica atual. Vem junto no `/esferas/estado`, sem polling novo. Assim quem não viu o chat não perde a dica. |
| 5 | Efeito do 1º lugar | Mínimo de 8 s, esperando o pedido (no máximo 30 s), com as 3 opções na tela. A turma assiste à escolha. Um clique fecha. |
| 6 | Dois avisos no chat por aluno que completa | "invocou o dragão" na hora + "pedido" quando ele escolhe. |
| 7 | Janela **⛶ Telão** | Além da aba (pedida), um botão abre a grade em tela cheia com letras grandes, porque a coluna do meio do painel é estreita para 15 alunos no projetor. |
| 8 | Resgate fora de ordem | Permitido (só as dicas são em sequência). |
| 9 | 9º item no menu do aluno (achado I) | Proposta: **não mexer** nos botões que já existem e registrar como limitação. Só 1366×768 com escala de 125% corta o rodapé do menu, e ele **já corta hoje**. Se os PCs do laboratório forem assim, me avise: posso diminuir a altura de todos os botões do menu de 42 para 34 px (é uma mudança visual em tela existente, por isso pergunto). |
| 10 | Número de caçador | Dado na largada para quem está online, ou no primeiro pedido `/esferas/` de quem chegar depois, sem mexer em `/turma/entrar`. O número é mantido entre caçadas (até desligar o servidor). |
