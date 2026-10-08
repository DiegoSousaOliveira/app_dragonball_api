# Análise: de "projeto de aulas" para "aplicativo da turma"

> 06/10/2026. O professor pediu: projeto normal (sem aulas), **servidor do professor** na rede do laboratório
> (espelho da API + placar da turma + painel ao vivo), **aplicativo do aluno em janela completa** e **instalador .exe**.

## 1. O que existe e o que acontece com cada parte

| Parte | Destino | Motivo |
|---|---|---|
| `core/poder.py`, `batalha.py`, `quiz.py`, `filtros.py` | ✅ **Reaproveitado sem mudança** | Lógica pura e testada (27 testes) |
| `core/imagens.py` | ✅ Reaproveitado + ajuste | Ganha o "cache embutido" que vem no instalador |
| `core/api.py` | ♻️ Reaproveitado + ajuste | Passa a falar com o **servidor do professor** ou com a internet; cache separado por origem |
| `core/armazenamento.py` | ♻️ Ajuste | No `.exe`, os arquivos graváveis vão para `%LOCALAPPDATA%\DragonBallDex` |
| `core/rede.py` | ✅ Reaproveitado | Agora compara **servidor da sala × internet** |
| `janelas/tema.py`, `componentes.py` | ✅ Reaproveitados (vão para `interface/`) | Card, mini-card, barra de vida e selo continuam iguais |
| `janelas/personagem.py`, `planeta.py`, `ranking.py`, `grafico_latencia.py` | ♻️ Reaproveitados como janelas de detalhe e telas | Mesmo desenho; sem "esperar fechar" |
| `janelas/batalha.py`, `quiz.py` | ♻️ Viram **telas** dentro da janela principal | A lógica de rodadas/`after()` é a mesma |
| `terminal/` (menu, busca, opcoes, raio_x) | 🔁 Substituído por telas | Os textos do Raio-X viram a tela "Rede" |
| `main.py` | 🔁 Reescrito | `python main.py` (aluno) / `python main.py --servidor` (professor) |
| `tests/` | ✅ Reaproveitados + testes novos do servidor | |
| `dados/snapshot_*.json` | ✅ Reaproveitados | Plano B sem internet |
| `cache/` (12 MB pré-aquecidos) | ✅ Vai **dentro do instalador** | O servidor funciona mesmo com o laboratório sem internet |
| `ferramentas/explorar_api.py`, `gerar_snapshot.py` | ✅ Mantidos | Ferramentas de manutenção |
| `etapas/`, roteiro das aulas, `exemplos/`, gerador do README | 📦 **Arquivados** em `arquivo_versao_aulas.zip` | Não são mais necessários, mas nada se perde |

## 2. Arquitetura nova

```
 PC do professor (servidor)                      PCs dos alunos
 ┌───────────────────────────────┐   HTTP (rede   ┌──────────────────────────┐
 │ Painel (janela no telão)      │   da sala)     │ App Dragon Ball Dex       │
 │  - alunos conectados          │ ◀────────────▶ │  Personagens, Batalha,    │
 │  - pedidos ao vivo            │  porta 8000    │  Planetas, Ranking, Quiz, │
 │  - placar da turma            │                │  Turma, Rede (Raio-X)     │
 │ Servidor HTTP                 │ ◀── UDP 50505  │  "Procurar servidor"      │
 │  /api/...  espelho da API     │   (descoberta) │                          │
 │  /imagens/... fotos           │                └──────────────────────────┘
 │  /turma/... placar            │
 │        │ internet (se houver) → dragonball-api.com
 │        └ senão: cache embutido + snapshot
 └───────────────────────────────┘
```

- **Servidor:** biblioteca padrão (`http.server.ThreadingHTTPServer`), sem dependência nova. Ele fala o
  **mesmo formato** da dragonball-api, então o cliente reaproveita o `core/api.py` só trocando o endereço. As URLs
  das imagens são reescritas para `http://IP-do-professor:8000/imagens/...`, e assim os alunos não precisam de
  internet.
- **Descoberta automática:** o aluno clica em "Procurar servidor na rede" e o app envia um *broadcast* UDP. O
  servidor responde com o endereço dele. Se a rede bloquear broadcast, dá para digitar o IP que aparece no telão.
- **Turma:** `POST /turma/batalha` e `POST /turma/quiz` guardam resultados; `GET /turma/placar` devolve o Hall da
  Fama e os recordes da sala. Cada pedido leva o nome do aluno no cabeçalho `X-Aluno`.
- **Aplicativo do aluno:** uma janela com menu lateral. Downloads em segundo plano (threads), para a janela nunca
  travar. Sem servidor, funciona direto pela internet (ou offline, com os dados embutidos).
- **Instalador:** PyInstaller (um único `DragonBallDex.exe`, com o Python embutido) + Inno Setup. Atalhos "Dragon
  Ball Dex" (aluno) e "Dragon Ball Dex - Servidor do Professor" (o mesmo exe com `--servidor`). O instalador libera
  o servidor no Firewall do Windows. Nenhum computador precisa ter Python.
