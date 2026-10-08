# Notas da API — Dragon Ball API

> Verificado em **06/10/2026** com `python ferramentas/explorar_api.py --completo`
> (saída completa em `docs/brutos/explorar_completo.txt`).
> Ambiente do teste: Windows 10, Python 3.14.6, requests 2.34.2, customtkinter 6.0.0, Pillow 12.3.0.

Legenda: ✅ verificado como o prompt dizia · ⚠️ divergente / com surpresa · ❌ não encontrado

---

## 1. Quadro geral

| # | Item | Resultado | Resumo |
|---|------|:---:|--------|
| 1 | Base `https://dragonball-api.com/api`, HTTPS, sem chave | ✅ | Funciona sem cadastro. Servidor Express (Node). |
| 2 | `GET /characters` com `items` / `meta` / `links` | ✅ | `totalItems=58`, `itemsPerPage=10`, `totalPages=6`. `previous` vem `""` na 1ª página. |
| 3 | Campos do personagem; `ki`/`maxKi` são texto | ✅ | Mais sujeira do que o previsto: veja a seção 4. |
| 4 | `GET /planets` (20 planetas, 2 páginas) | ✅ | IDs não são contínuos (faltam 8, 9, 10, 12, 17). |
| 5 | Filtros devolvem **lista pura** | ✅ | `?race=Saiyan` → `[...]`, sem `items`/`meta`. |
| 6 | Filtros ignoram `page`/`limit` | ⚠️ | `?race=Saiyan&limit=2` devolve os **10** saiyajins. |
| 7 | Filtros ignoram maiúsculas | ⚠️ (bom) | `race=saiyan`, `affiliation=Z fighter` funcionam. |
| 8 | `?name=` | ⚠️ | **Parcial** (contém), **ignora maiúsculas e acentos**. Não tolera erro de digitação. |
| 9 | `?limit=100` traz os 58 | ✅ | Uma chamada só. |
| 10 | Máximo de `limit` | ⚠️ | **Teto silencioso de 100** (`limit=1000` → `itemsPerPage=100`). `0`, `-1`, `abc` → volta ao padrão 10, sem erro. |
| 11 | `?page=2` | ✅ | `page=7` (além do fim) → 200 com `items: []`. `page=0` → página 1. |
| 12 | Seguir `links.next` | ✅ | 6 páginas; na última `next == ""`. |
| 13 | `GET /characters/{id}` traz planeta e transformações | ✅ | Campos novos `originPlanet` (objeto planeta completo) e `transformations` (lista). Todos os 58 têm `originPlanet`. |
| 14 | Transformações têm `ki` e `image` | ✅ | Chaves: `id`, `name`, `image`, `ki`, `deletedAt`. **14 personagens** têm transformações. |
| 15 | `GET /planets/{id}` traz os personagens | ✅ | Campo `characters` (lista de personagens resumidos). |
| 16 | `GET /transformations` | ⚠️ | Existe, mas é **lista pura** (43 itens), mesmo sem filtro. |
| 17 | `GET /transformations/{id}` | ✅ | Traz o campo `character` (dono da transformação). |
| 18 | ID inexistente → 404? | ⚠️ | **Não!** `/characters/99999` → **400** Bad Request. Veja a seção 3. |
| 19 | Limite de requisições por IP | ✅ (nada visto) | 40 requisições seguidas: todas 200, nenhum cabeçalho `RateLimit`/`Retry-After`. Mesmo assim, usaremos cache (30 alunos × 58 imagens no mesmo IP). |
| 20 | Documentação oficial | ❌ | `web.dragonball-api.com/documentation` devolve 3,6 KB de HTML montado por JavaScript; sem conteúdo útil para o `requests`. As respostas reais são a fonte da verdade. |
| 21 | Descrições em espanhol, `Celula`, `Freezer` | ✅ | `?name=Cell` → `[]`. Nomes de planeta também em espanhol (`Tierra`, `Kaiō del Norte`). |
| 22 | Imagens | ✅ | Todas `.webp`. Personagens e transformações em **RGBA** (fundo transparente → a silhueta do quiz é possível). Retratos **altos** (Goku 870×1959). Planetas em RGB. |
| 23 | Etapa 0b: 5 janelas seguidas (Windows) | ✅ | CustomTkinter **e** Tkinter puro: abriram, fecharam e devolveram o controle ao "terminal". Emoji e imagem webp aparecem (prints em `docs/brutos/janela_ctk_*.png`). |
| 24 | Etapa 0b: Linux | ❌ (ainda não testado) | O Ubuntu do WSL não tem `tkinter` (`sudo apt install python3-tk` exige senha) e o Docker Desktop estava desligado. **Pendente.** |
| 25 | Python 3.9 | ⚠️ | Não há 3.9 nesta máquina (só 3.12 e 3.14). Pillow 12 e requests 2.34 exigem **≥ 3.10**; num 3.9 o `pip` escolhe versões antigas sozinho. Impacto no pendrive offline: veja a seção 6. |

---

## 2. Exemplos reais de resposta (trechos)

**Lista paginada** — `GET /characters`
```json
{"items": [{"id": 1, "name": "Goku", "ki": "60.000.000", "maxKi": "90 Septillion",
            "race": "Saiyan", "gender": "Male", "description": "El protagonista de la serie...",
            "image": "https://dragonball-api.com/characters/goku_normal.webp",
            "affiliation": "Z Fighter", "deletedAt": null}, "..."],
 "meta":  {"totalItems": 58, "itemCount": 10, "itemsPerPage": 10, "totalPages": 6, "currentPage": 1},
 "links": {"first": "https://dragonball-api.com/api/characters?limit=10", "previous": "",
           "next": "https://dragonball-api.com/api/characters?page=2&limit=10",
           "last": "https://dragonball-api.com/api/characters?page=6&limit=10"}}
```

**Com filtro: lista pura** — `GET /characters?name=go`
```json
[{"id": 1, "name": "Goku", ...}, {"id": 10, "name": "Gohan", ...},
 {"id": 15, "name": "Gotenks", ...}, {"id": 65, "name": "Gogeta", ...}]
```

**Detalhe** — `GET /characters/1` (chaves)
```
id, name, ki, maxKi, race, gender, description, image, affiliation, deletedAt,
originPlanet  -> {"id": 2, "name": "Tierra", "isDestroyed": false, "description": ..., "image": ...}
transformations -> [{"id": 1, "name": "Goku SSJ", "image": ".../transformaciones/goku_ssj.webp",
                     "ki": "3 Billion", "deletedAt": null}, ... 6 itens]
```
As 6 transformações do Goku: `Goku SSJ` (3 Billion), `Goku SSJ2` (6 Billion), `Goku SSJ3` (24 Billion),
`Goku SSJ4` (2 Quadrillion), `Goku SSJB` (9 Quintillion), `Goku Ultra Instinc` (90 Septillion; o erro de digitação é da própria API).

**Planeta com moradores** — `GET /planets/1`
```
{"id": 1, "name": "Namek", "isDestroyed": true, ..., "characters": [Piccolo, Ginyu, Dende, Nail]}
```

**Transformação com dono** — `GET /transformations/1`
```
{"id": 1, "name": "Goku SSJ", "image": ..., "ki": "3 Billion", "deletedAt": null, "character": {"id": 1, "name": "Goku", ...}}
```

---

## 3. Erros: os status codes reais (ótimo material para a Aula 10)

| Requisição | Status | Corpo |
|---|:---:|---|
| `/characters/99999` | **400** | `{"message": "Character ID not found", "error": "Bad Request", "statusCode": 400}` |
| `/planets/999` | **400** | `{"message": "Planet ID not found", "error": "Bad Request", "statusCode": 400}` |
| `/characters/abc` | **500** | `{"statusCode": 500, "message": "Internal server error"}` |
| `/transformations/999` | **200** | **corpo vazio** (0 bytes, sem `Content-Type`) → `resp.json()` dá erro |
| `/rota-que-nao-existe` | **404** | `{"statusCode": 404, "message": "ENOENT: no such file or directory, stat '/app/images/index.html'"}` |
| `timeout=0.001` | — | `requests.exceptions.ConnectTimeout` |

Conclusões para o projeto:
- O experimento "404 de propósito" vira **"erros de propósito"**: um 400 (ID que não existe; a API "deveria" responder 404), um 404 (rota que não existe), um 500 (o servidor quebrou com `abc`, um erro 5xx de verdade) e um 200 vazio (o status diz "tudo certo", mas não veio nada). É a resposta perfeita para "qual a diferença entre 4xx e 5xx?" e para mostrar que **APIs reais nem sempre seguem o livro**.
- O cliente (`core/api.py`) trata **200 com corpo vazio** como erro (`ErroDeApi("A API respondeu, mas sem dados")`).
- O 404 mostra até um caminho interno do servidor (`/app/images/index.html`), o que serve de gancho para falar de vazamento de informação.

---

## 4. Valores reais de ki (impacto no `parse_ki`)

Todos os formatos encontrados nos 58 personagens:

| Formato | Exemplos (personagem) | Coberto pelas regras da Seção 8.2? |
|---|---|:---:|
| Pontos como milhar | `60.000.000` (Goku), `450` (Mr. Satan) | ✅ |
| **Vírgulas** como milhar | `160,000,000` (Android 19 maxKi), `280,000,000` (Android 18) | ✅ (regra 3) |
| Espaço sobrando no fim | `"42.000 "` (Nail), `"1.500 "` (Raditz) | ✅ com `strip()` |
| Escala com decimal | `19.84 Septillion`, `34.8 Billion`, `3.2 Billion`, `99.5 septillion` | ✅ |
| Escala minúscula | `40 septillion`, `7 quadrillion` | ✅ |
| Erro de digitação | `37.4 septllion` (Trunks) | ✅ (difflib) |
| Outras escalas | `Trillion`, `Quadrillion`, `Quintillion`, `Sextillion` | ✅ |
| `0` | Bulma, Chi-Chi, Launch, Babidi | ✅ |
| **`unknown`** | **10 personagens** (Kaio del Sur, Gran Kaio, os 4 Kaio-shin, Kibito…) | ✅ (sem dígitos → 0) |
| **`969 Googolplex`** | **Grand Priest** (ki e maxKi) | ⚠️ **não previsto** |

`Googolplex` = 10^(10^100): um número com mais dígitos do que há átomos no universo. **Nem o `int` do Python consegue guardá-lo.**
Proposta (registrada em `docs/DECISOES.md`): `parse_ki` reconhece `googol` = 10^100 e trata `googolplex` como **10^100**
(o maior valor que o programa usa), com um comentário/quadro de Matemática explicando por quê. Sem isso, a regra 3 leria `969` e o
Grand Priest seria mais fraco que o Mr. Satan.

Consequências:
- Ranking e "ignorar ki 0": **14** personagens ficam de fora (4 zeros + 10 `unknown`). O rodapé da janela explica.
- Batalha: quem tem `unknown` luta com força mínima 1 (como a Bulma) e ganha o "item surpresa".

---

## 5. Outras surpresas nos dados

- **Espaços no fim dos nomes:** `"Marcarita "`, `"Grand Priest "`, `"Planeta de Bills "`. O código faz `strip()` ao carregar.
- **IDs não contínuos:** personagens vão de 1 a 78 com buracos (36, 41, 45–62). Para `aleatorio`, use `random.choice(lista)`, **não** `randint(1, 58)`.
- **Raças reais (13):** Android, Angel, Evil, Frieza Race, God, Human, Jiren Race, Majin, Namekian, Nucleico, Nucleico benigno, Saiyan, Unknown.
- **Afiliações reais (8):** Army of Frieza, Assistant of Beerus, Assistant of Vermoud, Freelancer, Other, Pride Troopers, Villain, Z Fighter.
- **Gêneros:** Male, Female.
- **`deletedAt`:** sempre `null` hoje (nenhum personagem apagado).
- **URL de imagem com espaço:** `.../planetas/otro mundo.webp` (o `requests` converte para `%20` sozinho).
- **Planetas destruídos:** Namek, Vegeta, Freezer No. 79, Kanassa (4 de 20). `?isDestroyed=true` também funciona como filtro.

---

## 6. Rede e cabeçalhos (material para a Aula 10)

```
Content-Type: application/json; charset=utf-8
Cache-Control: max-age=864000          <- o servidor diz: "pode guardar por 10 dias"
Etag: W/"1835-FciHak4QvrvFh9uJ8zyZ8ftdJ18"   <- "impressão digital" da resposta
Content-Encoding: zstd                  <- resposta comprimida (no Python 3.14; em versões antigas vem gzip)
Alt-Svc: h3=":443"                      <- o servidor também fala HTTP/3
X-Powered-By: Express
```
- IP de `dragonball-api.com` hoje: **54.37.64.53** (pode mudar; é isso que o DNS resolve).
- Latência daqui: ~600–900 ms na 1ª requisição, ~200 ms com `Session` (conexão reaproveitada): 40 requisições em 8,3 s.
- `len(resp.content)` mede os bytes **já descomprimidos**. O tamanho que passou pelo cabo é menor (bom ponto de discussão).
- Desafio ⭐⭐⭐ possível: mandar `If-None-Match: <etag>` e ver se o servidor responde **304 Not Modified**.

**Python antigo e instalação offline:** como as versões atuais (Pillow 12.3, requests 2.34) exigem Python 3.10+, o `pip download` feito em
casa precisa mirar a versão do laboratório. Exemplo: `pip download -r requirements.txt -d wheels --python-version 3.9 --only-binary=:all:`
(o README explicará isso).
