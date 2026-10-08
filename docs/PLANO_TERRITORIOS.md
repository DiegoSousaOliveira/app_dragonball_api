# Plano: Dragon Ball Dex 2.4 (Conquista, Mapa do Radar, Grito de Guerra, Modo Demonstração)

> 08/10/2026 · branch `conquista-territorios`, criada a partir da `cacada-esferas` em `v2.3.2` (a mais recente; igual
> ao GitHub). Antes de começar: **80 testes passando**.

Mesmo cuidado da 2.3 (`docs/PLANO_ESFERAS.md`): código novo em arquivos novos, ganchos curtos nos antigos, tudo
**desligado** até o professor ativar. Com tudo desligado, as rotas, os JSON e as telas antigas ficam como na 2.3.2.

---

## 0. O que a leitura do código mostrou (e muda o pedido)

| # | Achado | Proposta |
|---|---|---|
| A | **O Grand Priest é invencível.** O motor usa `força = log10(ki)` e limita a vantagem de dano a 2,5×. Ele tem força **103**; o 2º (Zeno) tem **26,7**. Medido com 2.000 lutas: Grand Priest vence o Zeno em **100%**, o Goku vence o Grand Priest em **0%**. Na Conquista, todo mundo escolheria ele (guardião e atacante) e o jogo viraria cara ou coroa. | **Teto de força** só nas lutas da Conquista: `min(força, 27)` (≈ Zeno). O Grand Priest vira "um dos fortes", e a escolha volta a importar (Goku × Vegeta = 50%; Krillin × Goku = 0%). O motor, os duelos e o treino **não mudam**. Também uso o teto nos neutros. |
| B | O motor usa **um único tipo de poder por luta** (`iniciar_luta(a, b, metrica)`). O pedido fala em "tipo de poder do guardião na configuração" **e** "atacante escolhe tipo de poder". | O tipo de poder é **da Conquista** (o professor escolhe no painel: Total KI, padrão, ou Base KI) e vale para todas as lutas. O atacante escolhe só **alvo + lutador**. |
| C | O exemplo "KAMEHAMEHA!" como frase de grito **choca** com a regra de nunca mostrar a palavra secreta da esfera 6 no telão nem repassá-la. | **Decisão do professor (08/10):** a frase do aluno **pode** conter a palavra (não tem problema mostrar). O que continua valendo: o **sistema** nunca coloca a palavra por conta própria em evento, feed ou telão (o grito UDP da esfera 6 não repassa a palavra digitada, e a frase padrão é "Pela honra da Terra!"). |
| D | O `/turma/partida/<id>` mora na `Sala`, e toda partida da Sala vai para o **placar da turma** (3/1/0) e marca o aluno como "Lutando". | As lutas da Conquista usam a **mesma classe** `PartidaBatalha` (motor e formato iguais), mas ficam **dentro da Conquista**, nunca na Sala. A rota `/turma/partida/<id>` ganha um gancho: id começando com `cq-` → Conquista. Assim nada vai para o placar da turma. A tela de duelo é reaproveitada (classe filha só troca o texto do fim e o botão "Voltar"). |
| E | O app só tem **um** canal que roda o tempo todo: o `GET /turma/sala` a cada 1,5 s. Os sons de eventos (conquista, esfera 6, dragão) precisam chegar em **qualquer tela**. | Sem polling novo: com a Conquista ou a Caçada **valendo**, a resposta de `/turma/sala` ganha o campo `"novidades": {"eventos": <último id>, "gritos": <versão>}`. Se mudou, o app busca `GET /gritos/eventos?depois=<id>` (raro). **Desligado, o campo não existe** e o JSON fica igual ao da 2.3.2. Apps antigos ignoram campos que não conhecem. |
| F | Esferas 2, 5 e 7 do **ensaio** (modo demo) são abertas no navegador/curl, que **não mandam** o token do professor. | No servidor, um pedido de `/esferas/*` com `?cacador=` na faixa **901+** e vindo do **próprio PC** (127.0.0.1) vai para o mundo demo. O grito UDP segue a mesma regra. Um aluno não consegue isso: o pedido dele nunca vem de 127.0.0.1 do servidor. O protocolo da esfera 6 não muda. |
| G | README × código: o subtítulo da tela Batalha diz "A vitória vai para o placar da turma!", mas a batalha de treino só entra no **Hall da Fama** (personagens), não nos pontos dos alunos. O README está certo; o subtítulo engana. | Trocar o subtítulo por "O vencedor entra no Hall da Fama do telão." (1 linha em tela existente; **peço sua aprovação**). |
| H | O menu com 10 itens precisa de ~696 px; em 1366×768 a 125% há ~558 px. Itens compactos sozinhos não resolvem (precisaria de botões de 28 px). | **Menu com rolagem** (a barra só aparece quando não cabe) + itens um pouco mais baixos (42 → 38 px). O rodapé ("Trocar conexão") fica sempre visível. |

---

## 1. Arquivos novos

| Arquivo | O que tem |
|---|---|
| `servidor/conquista.py` | Classe **`Conquista`** (instanciável, sem rede): territórios, donos, guardiões, invasões (cada uma é uma `PartidaBatalha`), escudo, esperas, trava contra invasões simultâneas, ranking com desempate, pausa, relógio, eventos, CSV. Relógio injetável para os testes. |
| `servidor/rotas_conquista.py` | Rotas `/conquista/*` e o gancho das partidas `cq-*`. |
| `servidor/gritos.py` | Classe **`Gritos`** (instanciável): frase + áudio de cada aluno, bloqueio, limite de troca, eventos de som, versão para pré-carregar. |
| `servidor/baixar_audio.py` | O download seguro (proxy): só http/https nas portas 80/443, IP resolvido e **fixado**, sem rede local/loopback/link-local/multicast/reservado (`ipaddress`), revalidação a cada redirecionamento (no máximo 3), timeout curto, ≤ 500 KB, formato pelos primeiros bytes. |
| `servidor/rotas_gritos.py` | Rotas `/gritos/*`. |
| `servidor/mundo_demo.py` | O **mundo demo**: `Sala`, `Chat` (fechado), `Cacada`, `Conquista`, `Gritos` e placar **próprios**, mais 2 alunos-robô e 3–4 territórios de robôs 🤖 que "jogam sozinhos". |
| `core/grito_padrao.py` | O som padrão, gerado com `wave` + matemática (sem arquivo de ninguém). |
| `core/conquista_cliente.py`, `core/gritos_cliente.py` | O lado do aluno (HTTP), no estilo de `core/esferas_cliente.py`. |
| `interface/audio.py` | O player: **fila** (um som de cada vez, no máximo 2 esperando), corte em 6 s, volume, mudo, cache. Usa `miniaudio`; sem ele, toca só WAV com `winsound`; se nada der certo, segue mudo com "sem áudio neste PC". Nunca trava. |
| `interface/telas/conquista.py` | A tela **🗺 Conquista** do aluno, a tela da invasão (filha da `TelaDueloBatalha`) e o editor do grito. |
| `interface/mapa_galaxia.py` | O mapa da galáxia em Canvas (usado no app, no painel e no telão). |
| `interface/radar.py` | O **mapa do radar** 11×11 da esfera 4. |
| `interface/aba_conquista.py`, `interface/aba_gritos.py` | As abas novas do painel (+ telão da Conquista). |
| `ferramentas/simular_conquista.py` | 15 alunos falsos que escolhem guardião, invadem e trocam de grito. |
| `tests/test_conquista.py`, `test_rotas_conquista.py`, `test_gritos.py`, `test_radar.py`, `test_demo.py`, `test_audio.py` | Testes novos (seção 6). |

## 2. Ganchos nos arquivos existentes

| Arquivo · função | Gancho | Por quê |
|---|---|---|
| `servidor/aplicacao.py` · `__init__` | cria `self.conquista`, `self.gritos`, `self.token_demo` (`secrets`, só na memória) e `self.demo` (mundo demo); método `mundo_do_pedido()` | Cada mundo é um objeto separado. |
| `servidor/aplicacao.py` · UDP | números 901+ vindos de 127.0.0.1 → caçada do mundo demo | Ensaio da esfera 6. |
| `servidor/rotas.py` · `_atender` | escolhe o **mundo** (real ou demo) e passa para as mesmas funções de rota; desvia `/conquista/` e `/gritos/` | Isolamento por construção: o código das rotas não tem `if demo`. |
| `servidor/rotas.py` · `rota_partida` | ids `cq-*` → Conquista | Reaproveita `/turma/partida/<id>`. |
| `servidor/rotas.py` · `rota_get("/turma/sala")` | campo `novidades` **só com atividade valendo** | Sons em qualquer tela, sem polling novo (achado E). |
| `servidor/monitor.py` · `registrar` | parâmetro opcional `demo=False`: marca o pedido e **não** entra na lista de alunos | Etiqueta 🎓 no "Pedidos ao vivo" sem o professor virar "aluno conectado". |
| `servidor/rotas_esferas.py` | evento de som ao resgatar a esfera 6 e ao invocar o dragão; `radar_no_app` no `/esferas/estado` | Grito na caçada; interruptor do mapa. |
| `core/esferas.py` · `Cacada` | parâmetro `primeiro_numero` (demo começa em 901); atributo `radar_no_app`; dica da esfera 4 cita o mapa | Ensaio; mapa do radar. A rota `/esferas/radar`, o 400 e o gabarito **não mudam**. |
| `interface/app_aluno.py` | item 🗺 no `MENU`; menu com rolagem; botão 🔊 no rodapé (mudo + volume); faixa do modo demo; trata `novidades` (som); `abrir_duelo`/`fim_do_duelo` aceitam a invasão | Menu, som e demo. |
| `interface/telas/esferas.py` | mostra o mapa do radar quando a esfera 4 é a da vez (e o professor liberou) | Seção 2. |
| `interface/painel_servidor.py` | abas 🗺 Conquista e 📣 Gritos; botão 🎓 no rodapé; etiqueta e interruptor 🎓 em "Pedidos ao vivo"; novas consultas automáticas | Painel. |
| `interface/aba_cacada.py` | interruptor "Mapa do radar liberado no app"; o efeito do dragão toca o grito de quem invocou | Seções 2 e 3. |
| `interface/ajuda.py` | seção da 🗺 Conquista; Esferas cita o mapa; dica do 🔊 | Guia ❔ (o teste exige seção para cada tela). |
| `interface/fumaca.py`, `main.py` | passos novos; flag `--demo` (sem token não faz nada) | Fumaça e demo. |
| `requirements.txt`, `instalador/construir.py`, `instalador/DragonBallDex.iss` | `miniaudio`; versão 2.4.0 | Instalador. |

**Não mudam:** `servidor/sala.py`, `servidor/placar.py`, `servidor/chat.py`, `servidor/espelho.py`,
`core/batalha.py`, `core/turma.py`, a rota `/esferas/radar` e os 80 testes antigos.

---

## 3. Conquista de Territórios 🗺

**Estados:** `aguardando → ativa ⇄ pausada → encerrada` (como a Caçada). "↺ Nova conquista" volta para `aguardando`.

**Largada:** cada aluno online ganha 1 planeta sorteado (são os 20 de `dados/`) + N neutros (padrão 3, de 0 a 5). Com
mais alunos que planetas, os neutros diminuem e quem sobrar começa sem território. Quem chega depois também começa
sem território.

**Guardião:** escolhido a qualquer momento (até antes da largada); sorteado até o aluno escolher; trocar tem espera
de 60 s (**429**). Neutros: guardião sorteado entre os de força média.

**Invasão (`POST /conquista/invadir {"territorio", "personagem"}`):** o servidor confere tudo **dentro de uma trava**
(só um passa) e cria a luta `cq-…`. O atacante assiste pela tela de duelo reaproveitada e pode usar "Transformar!".
O guardião se transforma sozinho quando cai abaixo de 50% de vida, se o personagem tiver transformação. O defensor não
precisa estar online. A luta anda pelo relógio e termina mesmo se o atacante fechar o app.

| Situação | Status |
|---|---|
| Território inexistente | **404** |
| Invadir o próprio território | **403** |
| Alvo já em batalha · escudo de 45 s · você já está numa invasão · conquista aguardando/pausada/encerrada | **409** |
| Menos de 20 s desde a sua última invasão | **429** |

**Pausa:** novas invasões ficam bloqueadas e o relógio congela; lutas já começadas terminam. **Encerrar:** lutas em
andamento são canceladas (o território fica com o defensor). Encerrar gera o pódio no telão e o CSV em
`%LOCALAPPDATA%\DragonBallDex\conquistas\` (territórios finais, conquistas, defesas, invasões e posição).

**Ranking (placar separado):** territórios → conquistas → defesas → quem chegou antes àquele número.

**Rotas:** `GET /conquista/estado?depois=<id>` (mapa, donos, escudos, lutas, ranking, meus dados e eventos novos;
**409** com os dados quando parada; o app 2.4 num servidor 2.3 recebe 404 → "Este servidor não tem a Conquista") ·
`POST /conquista/guardiao` · `POST /conquista/invadir` · `GET /turma/partida/cq-…` (+ `transformar` e `desistir`).

**Tela do aluno:** mapa clicável (dono pela cor + nome, 🛡 escudo, ⚔ em batalha) e painel lateral (relógio, meus
territórios, guardião, grito, **Invadir**, mini-ranking, feed). Polling de 1,5 s só com a tela aberta (como a Esferas).
**Painel:** configuração (duração, neutros, escudo, espera, tipo de poder), ▶ ⏸ ■ ↺, ⛶ Telão (mapa em tela cheia;
quando um território troca de dono: pulso no planeta + frase do grito grande + som), 🔊, feed, 📂.

**O que ensina:** estado compartilhado no servidor, **concorrência** (dois cliques no mesmo alvo, só um passa →
409), **409 × 429 × 403 × 404**, polling incremental (`?depois=`), o servidor como "juiz" (o app não decide quem
ganhou).

## 4. Mapa do Radar 🧭 (esfera 4)

Na tela 🐉 Esferas, quando a dica da vez é a da esfera 4 e o professor deixou o mapa liberado: grade 11×11 com cara de
radar (fundo escuro, varredura animada). Clique numa célula, ou setas + Enter/Espaço, para escanear: o app faz o
**mesmo** `GET /esferas/radar?cacador=N&x=X&y=Y` (com o `X-Jogador`, como a tela Testar), pinta a célula
(❄️/🌤/🔥/🔥🔥) e guarda o histórico com o número de tentativas. Ao acertar, ele **resgata sozinho** o código
(respeitando os 2 s) com a animação de esfera acesa. Acima do mapa fica sempre a requisição equivalente
(`GET /esferas/radar?cacador=7&x=5&y=5`), e os pedidos continuam no "Pedidos ao vivo". A rota, o 400, a posição e o
gabarito não mudam. No painel, aba Caçada, o interruptor **"Mapa do radar liberado no app"** fica ligado por padrão.

## 5. Grito de Guerra 📣

- **Frase** (até 40 caracteres, sem caracteres de controle; pode ter qualquer palavra → achado C) + **áudio**.
- **Padrão:** frase "Pela honra da Terra!" + som gerado pelo programa.
- **Personalizado:** URL de arquivo (mp3/wav/ogg). O **servidor** baixa (`servidor/baixar_audio.py`), guarda em
  `%LOCALAPPDATA%\DragonBallDex\gritos\<hash>` e serve em `GET /gritos/<hash>`. O hash vem do conteúdo, **nunca** do
  `X-Jogador`. Link do YouTube → mensagem explicando que precisa ser um link direto para o arquivo. Sem internet →
  "use o grito padrão".
- **Limites:** 1 troca a cada 10 s (**429**), ≤ 500 KB (**413**), formato pelos primeiros bytes (**415**), SSRF
  (**403**), servidor sem internet (**502**). Cada um ensina um status diferente.
- **Moderação (aba 📣 Gritos):** lista, ▶ ouvir, 🔇 bloquear (um ou vários selecionados), 🔊 liberar. O aluno
  bloqueado volta na hora ao padrão e vê "O professor bloqueou o seu grito personalizado".
- **Onde toca:** ao invadir (só no PC do atacante); ao conquistar (alunos + telão, com a frase grande); esfera 6
  resgatada; invocação do dragão (alunos + telão, junto do efeito). Quem ouve: a constante `QUEM_OUVE = "todos"`
  (ou `"envolvidos"`) em `servidor/gritos.py`.
- **No app:** 🔊/🔇 e volume (no rodapé do menu, guardados no `config.json`); fila sem sobreposição; pré-carregamento
  pela `novidades.gritos` (versão). Áudio fora do cache → toca o padrão.
- **Biblioteca:** **`miniaudio`** (MIT, ~280 KB + `cffi` ~190 KB; Python 3.8+; toca mp3/wav/ogg/flac; volume e corte
  em 6 s no próprio código). Testei nesta máquina: decodificou e tocou (mudo) um WAV gerado. `pygame-ce`: 9,8 MB,
  LGPL e **exige Python 3.10** (quebraria o 3.9). `winsound`: só WAV, sem volume (fica de reserva). Só o **app** usa
  a biblioteca; o servidor continua só com a biblioteca padrão.

## 6. Modo Demonstração 🎓

- **Acesso:** botão "🎓 Modo demonstração" no painel. Ele abre o app (o mesmo `.exe` com `--demo`) e passa o token e o
  endereço por **variável de ambiente** (não aparece na linha de comando). O app manda `X-Demo: <token>`; o servidor
  só aceita token **válido** (`secrets.compare_digest`) **e** vindo de 127.0.0.1. Fora disso: aluno normal.
- **Mundo demo isolado por construção:** `mundo_do_pedido()` devolve o mundo real ou o demo, e **as mesmas funções de
  rota** recebem esse objeto. Não há `if demo` espalhado. O mundo demo tem `Sala`, `Chat` fechado (escrever → **403**),
  `Cacada` sempre valendo (números 901+, com mapa do radar), `Conquista` com 3–4 territórios de robôs 🤖, `Gritos` e
  placar próprios, e 2 alunos-robô que aceitam desafios e jogam o quiz sozinhos.
- O professor demo não aparece em nada do mundo real (sala, placar, pódio, mapa, ranking, CSV, "Alunos conectados")
  e os gritos não cruzam os mundos. No "Pedidos ao vivo" os pedidos aparecem com **🎓 demo**, e há um interruptor
  para escondê-los.
- No app: faixa fixa "🎓 MODO DEMONSTRAÇÃO: nada aqui vale pontos nem aparece para os alunos".

## 7. Testes (além dos 80 antigos, que não mudam)

- **Conquista:** próprio território (403), inexistente (404), escudo e alvo ocupado (409), espera (429), **duas
  invasões simultâneas em threads → só uma passa**, desempate, neutros, quem chega depois, pausa, encerrar + CSV, teto
  de força, a Conquista funcionando com o grito desligado.
- **Radar:** a URL montada pelo mapa é idêntica à manual; `/esferas/radar` igual (inclusive 400); temperatura do
  histórico; interruptor.
- **Grito:** loopback, IP privado, `localhost`, link-local e **redirecionamento para IP privado** recusados; porta fora
  de 80/443; > 500 KB; mp3 falso (extensão certa, bytes errados); troca rápida; bloquear/desbloquear; fila sem
  sobreposição (player falso); **o sistema nunca coloca sozinho a palavra mágica em evento, feed ou estado** (a frase escolhida pelo aluno pode ter). Tudo com um servidor
  HTTP local de teste, sem internet.
- **Demo:** token errado/ausente = aluno normal; token certo de fora do loopback = aluno normal; o demo nunca aparece
  em `/turma/sala`, `/turma/placar`, Conquista, Caçada, CSV nem nos conectados; chat 403; gritos não cruzam.
- `--fumaca` com as telas novas.

## 8. Etapas (cada uma com testes passando e um commit)

A) Conquista no servidor + testes → B) Conquista na interface (aluno, painel, telão, menu com rolagem, guia ❔) →
C) Mapa do radar → D) Grito de guerra (download seguro, player, moderação) → E) Modo demonstração →
F) simulador, `--fumaca`, README/DECISOES, instalador 2.4.0 e tag `v2.4.0` (sem push).

## 9. Riscos

- **Barulho:** 15 PCs tocando o mesmo grito ao mesmo tempo. A fila evita sobreposição **dentro** de cada PC; entre
  PCs vira um "coro". Por isso `QUEM_OUVE` é uma linha só para trocar.
- **Conteúdo dos áudios:** a proteção é de **rede**, não de conteúdo. O professor modera bloqueando.
- **Tamanho:** a etapa B é a maior (mapa + tela + painel + telão). Áudio em PC real (fone, placa de som) eu não consigo
  testar daqui: os testes usam um player falso e tocam em volume zero.
- **Tráfego:** pré-carregar 15 gritos de até 500 KB nos 15 PCs ≈ 110 MB na rede local, espalhados no tempo. Aceitável
  numa rede de laboratório.

## 10. Decisões (aprovadas em 08/10/2026)

| # | Decisão | Proposta |
|---|---|---|
| 1 | Grand Priest invencível (achado A) | Teto de força 27, só nas lutas da Conquista |
| 2 | Tipo de poder (achado B) | Um só, da configuração da Conquista; o atacante escolhe alvo + lutador |
| 3 | Palavra mágica no grito (achado C) | ✅ Ajustada: a frase do aluno pode ter a palavra; o sistema nunca a coloca sozinho; padrão "Pela honra da Terra!" |
| 4 | Sons em qualquer tela (achado E) | Campo `novidades` em `/turma/sala` só com atividade valendo |
| 5 | Ensaio das esferas no navegador/curl (achado F) | Números 901+ vindos de 127.0.0.1 → mundo demo |
| 6 | Subtítulo da Batalha (achado G) | "O vencedor entra no Hall da Fama do telão." |
| 7 | Menu (achado H) | Rolagem que só aparece quando não cabe + itens de 38 px |
| 8 | Guardião se transforma sozinho abaixo de 50% de vida | Sim (equilibra com o "Transformar!" do atacante) |
| 9 | Encerrar com luta em andamento | Cancela a luta; o território fica com o defensor |
| 10 | Biblioteca de áudio | `miniaudio` (+ `winsound` de reserva só para WAV) |
