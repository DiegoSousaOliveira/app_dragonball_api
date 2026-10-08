"""
Guia "Como funciona?" do app do aluno: uma explicacao curta de cada tela, para ninguem ficar perdido.

  - O botao "❔ Como funciona?" fica no topo de TODAS as telas (ele e criado pelo cabecalho() de
    interface/telas/__init__.py) e abre o guia ja na explicacao daquela tela.
  - Na primeira vez que cada aluno (pelo nome) conecta neste computador, o guia abre sozinho em "Primeiros passos".
Criou uma tela nova? Acrescente a explicacao dela em GUIA e o nome da classe em TELAS (um teste confere).
"""

import customtkinter as ctk

from core import config
from interface import janelas, tema

# Cada secao: (chave, titulo, para que serve, passos de "como usar", dicas)
GUIA = [
    ("inicio", "🚀 Primeiros passos",
     "O Dragon Ball Dex é o app da turma: você explora o universo Dragon Ball, duela com os colegas e, de quebra, vê "
     "uma rede de computadores funcionando. Cada clique seu vira um pedido que viaja pela rede até o servidor do "
     "professor e aparece no telão!",
     ["Use o menu da esquerda para trocar de tela. A tela aberta fica destacada em amarelo.",
      "Lá embaixo, no menu, aparecem o seu nome e a conexão: \"● Servidor da sala\" em verde quer dizer que está "
      "tudo certo.",
      "Em qualquer tela, clique em ❔ Como funciona? (no canto de cima) para ler a explicação daquela tela.",
      "Mudou de computador ou de servidor? Clique em \"Trocar conexão\"."],
     ["Quando um colega te desafiar, aparece uma janela na hora, em qualquer tela.",
      "O número ao lado do Chat, como \"💬 Chat (3)\", mostra quantas mensagens novas chegaram.",
      "Apareceu \"Sem conexão: usando dados salvos\"? O app continua funcionando com o que já baixou. Avise o "
      "professor."]),

    ("personagens", "🔎 Personagens",
     "Conhecer os personagens: foto, raça, afiliação e poder (ki).",
     ["Digite um nome na busca (ex.: goku). Pode ser só um pedaço: \"veg\" acha o Vegeta.",
      "Errou uma letra? O app pergunta \"Você quis dizer...?\". Clique na sugestão.",
      "Use os filtros Raça, Afiliação e Gênero para ver só um grupo (ex.: só os Saiyans).",
      "Clique num card para abrir os detalhes: descrição, planeta de origem e transformações (use ◀ ▶ para ver "
      "cada transformação)."],
     ["Os dados vêm da dragonball-api, um site em espanhol: o Freeza aparece como \"Freezer\" e o Cell como "
      "\"Celula\"."]),

    ("batalha", "⚔ Batalha (treino)",
     "Treinar lutas entre dois personagens, contra o computador. Não vale pontos no pódio da turma, mas o "
     "personagem vencedor entra no \"Hall da Fama\" do telão.",
     ["Escolha um lutador de cada lado: digite o nome ou clique em 🎲 para sortear.",
      "Escolha o tipo de poder: Total KI (o poder máximo) ou Base KI (o poder normal).",
      "Clique em \"Preparar luta\" e depois em \"Lutar! 👊\".",
      "Durante a luta, \"Transformar! ⚡\" deixa o personagem mais forte por algumas rodadas. Só dá para usar uma "
      "vez por luta, e só se o personagem tiver transformação.",
      "Acabou? \"Revanche 🔁\" repete a mesma luta."],
     ["Quer valer pontos de verdade? Desafie um colega na tela 👥 Turma e duelos."]),

    ("planetas", "🪐 Planetas",
     "Conhecer os planetas do universo Dragon Ball.",
     ["Clique num planeta para ver a descrição dele.",
      "Na janela que abre, veja os 👥 Moradores: quem nasceu lá.",
      "A etiqueta vermelha \"Destruído\" mostra os planetas que foram destruídos na história."],
     ["Esta tela também pode servir de pista na Caça às Esferas 🐉."]),

    ("ranking", "🏆 Ranking",
     "Ver quem são os personagens mais fortes, do maior para o menor poder.",
     ["Escolha Total KI (o poder máximo) ou Base KI (o poder normal).",
      "Use \"Raça\" para ver o ranking de um grupo só, e \"Quantos\" para mostrar mais ou menos personagens."],
     ["As barras usam escala de LOGARITMO: cada pedacinho a mais de barra quer dizer 10 vezes mais forte. Sem isso, "
      "o mais forte encheria a tela e os outros nem apareceriam!",
      "Quem tem ki 0 ou desconhecido fica de fora (o rodapé da tela diz quantos)."]),

    ("quiz", "❓ Quem é? (treino)",
     "Adivinhar o personagem pela imagem. É treino: não vale pontos no pódio, mas o melhor resultado entra nos "
     "\"recordes do quiz\" do telão.",
     ["Escolha quantas rodadas (3, 5 ou 10) e clique em \"Começar ▶\".",
      "A imagem começa quadriculada. Clique no nome certo entre as opções.",
      "Errou? A imagem fica mais nítida, mas a rodada passa a valer menos.",
      "Ficou difícil? \"💡 Dica (-1 ponto)\" ajuda, mas custa 1 ponto.",
      "Clique em \"Próxima ▶\" até o fim para ver o seu resultado."],
     ["Acertar de primeira vale 4 pontos; cada erro ou dica tira 1."]),

    ("turma", "👥 Turma e duelos",
     "Ver quem está na sala, desafiar colegas e acompanhar o pódio da turma. Aqui, sim, vale ponto!",
     ["Na lista \"Na sala agora\", veja quem está Livre, Lutando ou No quiz.",
      "Ao lado de um colega livre, clique em ⚔ (duelo de batalha) ou ❓ (duelo de quiz).",
      "Batalha: escolha o seu lutador e o tipo de poder. Quiz: escolha 3, 5 ou 10 rodadas. Clique em \"Enviar "
      "desafio\".",
      "O colega tem 30 segundos para \"Aceitar ✔\" ou \"Recusar\". Quando alguém desafia você, a janela aparece "
      "do mesmo jeito.",
      "No duelo de batalha, quem joga as rodadas é o servidor: os dois veem a mesma luta, e cada um tem o seu "
      "\"Transformar! ⚡\".",
      "No duelo de quiz, as perguntas são as mesmas para os dois. Ganha quem fizer mais pontos; no empate, quem "
      "terminar primeiro."],
     ["Pontos: vitória = 3, derrota = 1 (por ter participado). Fechar o app ou clicar em \"🏳 Desistir\" é "
      "derrota por W.O. e vale 0.",
      "Durante um duelo, o menu fica bloqueado até a luta acabar."]),

    ("chat", "💬 Chat",
     "Conversar com a turma. O professor vê todas as mensagens.",
     ["Escreva a mensagem embaixo e aperte Enter (ou clique em \"Enviar ➤\").",
      "As suas mensagens aparecem à direita, em amarelo; as dos colegas, à esquerda; as do professor, no meio, em "
      "azul."],
     ["Até 200 letras por mensagem, e uma mensagem a cada 1,5 segundo (contra spam).",
      "Seja gentil: o professor pode fechar o chat ou bloquear quem atrapalhar.",
      "Os avisos do professor (📢) chegam mesmo quando o chat está fechado."]),

    ("esferas", "🐉 Caça às Esferas",
     "Uma caça ao tesouro pela rede da sala: ache as 7 Esferas do Dragão. Cada esfera ensina um segredo de Redes. "
     "Só funciona quando o professor começa a caçada.",
     ["Anote o seu número de caçador (ex.: 07): ele vai em alguns endereços que você vai abrir.",
      "Leia a dica da vez: ela diz onde procurar a próxima esfera (no navegador, na tela 📡 Rede, no terminal...).",
      "Achou um código (ex.: ESF-7KQ2M)? Digite no campo e clique em \"⭐ Resgatar\". A esfera acende e a próxima "
      "dica aparece.",
      "Numa das esferas você vai gritar na rede: escreva a palavra mágica e clique em \"📡 Gritar na rede\".",
      "Juntou as 7? Você invoca o dragão e escolhe um pedido, que aparece no telão!"],
     ["O código é pessoal: o código de um colega não vale para você.",
      "Errou o código? Espere 2 segundos para tentar de novo.",
      "Travou? O professor pode mandar uma dica extra. Ela aparece nesta tela, em azul."]),

    ("conquista", "🗺 Conquista de Territórios",
     "Um torneio no mapa da galáxia: cada aluno começa com um planeta e tenta conquistar os dos colegas. Quem tiver "
     "mais planetas no fim vence. Só funciona quando o professor começa a Conquista.",
     ["Escolha o seu 🛡 Guardião: ele defende TODOS os seus planetas quando alguém invade, mesmo com o seu app "
      "fechado.",
      "Clique num planeta do mapa para escolher o alvo (os seus planetas têm um anel amarelo).",
      "Clique em \"⚔ Invadir\" e escolha o seu lutador. Quem decide a luta é o servidor: você assiste e pode usar "
      "\"Transformar! ⚡\".",
      "Venceu? O planeta é seu e ganha um escudo 🛡 por alguns segundos. Perdeu? O Guardião ficou com ele.",
      "Acompanhe o ranking e o \"Acontecendo agora\" do lado do mapa."],
     ["Os avisos de erro ensinam Redes: 409 = o planeta está ocupado (alguém já está invadindo, ou ele tem "
      "escudo); 429 = calma, espere alguns segundos para invadir de novo; 403 = esse planeta já é seu.",
      "Se dois alunos clicarem no mesmo planeta ao mesmo tempo, o servidor deixa só UM passar.",
      "Ninguém é eliminado: quem perdeu tudo continua invadindo."]),

    ("rede", "📡 Rede",
     "O \"raio-X\" da conexão: mostra o que acontece por baixo quando o app conversa com o servidor. Ela tem 5 abas:",
     ["Conexão: o seu IP, o IP e a porta do servidor e o caminho que cada pedido faz.",
      "Pedidos: os últimos pedidos do app. \"rede\" = foi buscar no servidor; \"cache\" = já estava guardado no "
      "computador.",
      "Testar: escolha um endereço, preencha os campos (ex.: limit = 5) e clique em \"Enviar GET\". Veja a URL "
      "montada, o status, os cabeçalhos e o corpo da resposta.",
      "Velocidade: compare o servidor da sala com a internet. Faça um palpite antes de medir!",
      "Experimentos: erros de propósito (404, 400), um timeout e o \"Modo offline\" (como se o cabo estivesse "
      "desligado)."],
     ["Lembre de desligar o \"Modo offline\" depois do experimento, senão o app não busca nada novo."]),

    ("problemas", "🆘 Deu problema?",
     "Os problemas mais comuns e o que fazer:",
     ["\"Sem conexão: usando dados salvos\": o servidor não respondeu. O app continua com o que já baixou. Avise o "
      "professor e, se ele pedir, clique em \"Trocar conexão\".",
      "O menu está apagado: você está num duelo (ele volta quando a luta acabar) ou o app ainda está carregando.",
      "O botão de desafio está apagado: o colega está num duelo, ou você já está esperando uma resposta.",
      "Não consigo escrever no chat: o professor fechou o chat ou bloqueou você (o aviso aparece no topo do Chat).",
      "A tela Esferas diz \"A caçada ainda não começou\": espere o professor dar a largada.",
      "Uma foto aparece \"sem imagem\": ela não estava guardada e não deu para baixar agora. O resto funciona."],
     []),
]

# Qual secao do guia cada tela abre (pelo nome da classe da tela)
TELAS = {"TelaPersonagens": "personagens", "TelaBatalha": "batalha", "TelaPlanetas": "planetas",
         "TelaRanking": "ranking", "TelaQuiz": "quiz", "TelaTurma": "turma", "TelaDueloBatalha": "turma",
         "TelaDueloQuiz": "turma", "TelaChat": "chat", "TelaEsferas": "esferas", "TelaConquista": "conquista",
         "TelaInvasao": "conquista", "TelaRede": "rede"}

_janela_aberta = None          # so uma janela do guia por vez


def botao_de_ajuda(mestre, tela):
    """O botao "❔ Como funciona?" do cabecalho de cada tela."""
    chave = TELAS.get(type(tela).__name__, "inicio")
    botao = tema.botao_secundario(mestre, "❔ Como funciona?", lambda: abrir_ajuda(tela.app, chave), largura=160)
    botao.pack(side="right", anchor="n", pady=(4, 0))
    return botao


def abrir_ajuda(app, chave="inicio"):
    """Abre o guia na secao 'chave' (ou so troca de secao, se ele ja estiver aberto)."""
    global _janela_aberta
    if _janela_aberta is None or not _janela_aberta.aberta():
        _janela_aberta = JanelaAjuda(app)
    _janela_aberta.mostrar(chave)
    _janela_aberta.janela.lift()
    return _janela_aberta


def abrir_na_primeira_vez(app, nome):
    """Na primeira vez que este aluno conecta neste computador, o guia abre sozinho (e nao abre mais)."""
    vistos = config.carregar().get("ajuda_vista_por", [])
    if nome in vistos:
        return
    config.salvar(ajuda_vista_por=(vistos + [nome])[-300:])
    app.after(600, lambda: abrir_ajuda(app, "inicio"))


class JanelaAjuda:
    def __init__(self, app):
        self.janela = janelas.criar_janela(app, "Como funciona?", 920, 620)
        self.janela.grid_columnconfigure(1, weight=1)
        self.janela.grid_rowconfigure(0, weight=1)
        lateral = ctk.CTkFrame(self.janela, fg_color=tema.LATERAL, corner_radius=0, width=230)
        lateral.grid(row=0, column=0, rowspan=2, sticky="ns")
        lateral.grid_propagate(False)
        lateral.pack_propagate(False)
        ctk.CTkLabel(lateral, text="📖 Como funciona?", font=tema.fonte(18, negrito=True),
                     text_color=tema.DESTAQUE).pack(anchor="w", padx=16, pady=(18, 10))
        self.botoes = {}
        for chave, titulo, *_ in GUIA:
            botao = ctk.CTkButton(lateral, text=titulo, anchor="w", height=34, corner_radius=8,
                                  fg_color="transparent", hover_color=tema.CARD, text_color=tema.TEXTO,
                                  font=tema.fonte(14, negrito=True), command=lambda c=chave: self.mostrar(c))
            botao.pack(fill="x", padx=10, pady=1)
            self.botoes[chave] = botao
        self.conteudo = ctk.CTkScrollableFrame(self.janela, fg_color="transparent")
        self.conteudo.grid(row=0, column=1, sticky="nsew", padx=(18, 10), pady=(14, 0))
        tema.botao(self.janela, "Entendi!", self.fechar, largura=120).grid(row=1, column=1, sticky="e",
                                                                            padx=20, pady=12)
        self.textos = []
        self.largura_do_texto = 600
        self.conteudo.bind("<Configure>", self._ajustar_quebra_de_linha)

    def aberta(self):
        try:
            return bool(self.janela.winfo_exists())
        except Exception:
            return False

    def fechar(self):
        if self.aberta():
            self.janela.destroy()

    def _ajustar_quebra_de_linha(self, evento):
        self.largura_do_texto = max(300, int(evento.width / janelas.escala(self.janela)) - 70)
        for rotulo in self.textos:
            rotulo.configure(wraplength=self.largura_do_texto)

    def _texto(self, mestre, texto, tamanho=15, cor=tema.TEXTO, negrito=False):
        rotulo = ctk.CTkLabel(mestre, text=texto, font=tema.fonte(tamanho, negrito=negrito), text_color=cor,
                              justify="left", anchor="w", wraplength=self.largura_do_texto)
        self.textos.append(rotulo)
        return rotulo

    def mostrar(self, chave):
        secao = next((s for s in GUIA if s[0] == chave), GUIA[0])
        chave, titulo, para_que, passos, dicas = secao
        for c, botao in self.botoes.items():
            botao.configure(fg_color=tema.CARD if c == chave else "transparent",
                            text_color=tema.DESTAQUE if c == chave else tema.TEXTO)
        for filho in self.conteudo.winfo_children():
            filho.destroy()
        self.textos = []
        tema.titulo(self.conteudo, titulo, 26).pack(anchor="w", pady=(0, 8))
        self._texto(self.conteudo, para_que, 16).pack(anchor="w", fill="x", pady=(0, 12))
        if passos:
            if chave not in ("rede", "problemas"):                   # nessas duas, o texto de cima ja apresenta a lista
                tema.titulo(self.conteudo, "Como usar", 17).pack(anchor="w")
            for numero, passo in enumerate(passos, start=1):
                linha = ctk.CTkFrame(self.conteudo, fg_color=tema.CARD, corner_radius=8)
                linha.pack(fill="x", pady=3)
                ctk.CTkLabel(linha, text=str(numero), width=30, font=tema.fonte(16, negrito=True),
                             text_color=tema.DESTAQUE).pack(side="left", anchor="n", padx=(8, 4), pady=8)
                self._texto(linha, passo, 15).pack(side="left", fill="x", expand=True, padx=(0, 10), pady=8)
        if dicas:
            tema.titulo(self.conteudo, "Dicas", 17).pack(anchor="w", pady=(14, 2))
            for dica in dicas:
                self._texto(self.conteudo, f"💡 {dica}", 14, tema.TEXTO_SECUNDARIO).pack(anchor="w", fill="x", pady=2)
        try:
            self.conteudo._parent_canvas.yview_moveto(0)          # volta para o topo ao trocar de secao
        except Exception:
            pass
