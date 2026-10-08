"""Painel do professor: mostra no telao o endereco do servidor, quem esta conectado e cada pedido ao vivo."""

import threading
import webbrowser
from tkinter import messagebox

import customtkinter as ctk

from interface import janelas, tema

ATUALIZAR_A_CADA = 1000          # milissegundos
FONTE_MONO = ("Consolas", 12)


CONSULTAS_AUTOMATICAS = ("/turma/sala", "/chat?", "/turma/partida/", "/turma/placar")


def eh_automatico(pedido):
    """Pedidos que os apps fazem sozinhos o tempo todo (polling). Escondidos para nao lotar a lista."""
    return pedido["metodo"] == "GET" and pedido["caminho"].startswith(CONSULTAS_AUTOMATICAS)


def tempo_legivel(segundos):
    if segundos < 60:
        return "agora"
    if segundos < 3600:
        return f"há {segundos // 60} min"
    return f"há {segundos // 3600} h"


class PainelServidor(ctk.CTk):
    def __init__(self, servidor):
        ctk.set_appearance_mode("dark")
        super().__init__()
        self.servidor = servidor
        self.title("Dragon Ball Dex - Servidor do Professor")
        janelas.colocar_icone(self)
        self.configure(fg_color=tema.FUNDO)
        janelas.abrir_janela_principal(self, 1280, 800)
        self.minsize(820, 540)
        self.protocol("WM_DELETE_WINDOW", self.fechar)
        self.ultimo_pedido_mostrado = 0
        self.progresso_preaquecer = None
        self.criar_topo()
        self.criar_colunas()
        self.criar_rodape()
        self.atualizar()

    # ---------------- montagem ----------------

    def criar_topo(self):
        topo = ctk.CTkFrame(self, fg_color=tema.LATERAL, corner_radius=0)
        topo.pack(fill="x")
        esquerda = ctk.CTkFrame(topo, fg_color="transparent")
        esquerda.pack(side="left", padx=24, pady=14)
        ctk.CTkLabel(esquerda, text="🐉 Servidor Dragon Ball Dex", font=tema.fonte(24, negrito=True),
                     text_color=tema.DESTAQUE).pack(anchor="w")
        ctk.CTkLabel(esquerda, text="● LIGADO", font=tema.fonte(15, negrito=True),
                     text_color=tema.SUCESSO).pack(anchor="w")
        direita = ctk.CTkFrame(topo, fg_color="transparent")
        direita.pack(side="right", padx=24, pady=10)
        ctk.CTkLabel(direita, text="Alunos: abram o Dragon Ball Dex e cliquem em \"Procurar na rede\" ou digitem:",
                     font=tema.fonte(14), text_color=tema.TEXTO_SECUNDARIO).pack(anchor="e")
        enderecos = "   ou   ".join(self.servidor.enderecos())
        ctk.CTkLabel(direita, text=enderecos, font=tema.fonte(34, negrito=True),
                     text_color=tema.TEXTO).pack(anchor="e")
        self.status_dados = ctk.CTkLabel(direita, text="", font=tema.fonte(13), text_color=tema.TEXTO_SECUNDARIO)
        self.status_dados.pack(anchor="e")

    def coluna(self, mestre, titulo, coluna, peso):
        caixa = ctk.CTkFrame(mestre, fg_color=tema.CARD, corner_radius=10)
        caixa.grid(row=0, column=coluna, sticky="nsew", padx=6)
        mestre.grid_columnconfigure(coluna, weight=peso)
        rotulo = ctk.CTkLabel(caixa, text=titulo, font=tema.fonte(17, negrito=True), text_color=tema.DESTAQUE)
        rotulo.pack(anchor="w", padx=14, pady=(12, 6))
        return caixa, rotulo

    def criar_colunas(self):
        area = ctk.CTkFrame(self, fg_color="transparent")
        area.pack(fill="both", expand=True, padx=14, pady=12)
        area.grid_rowconfigure(0, weight=1)
        caixa, self.titulo_alunos = self.coluna(area, "👥 Alunos conectados", 0, 2)
        self.lista_alunos = ctk.CTkScrollableFrame(caixa, fg_color="transparent")
        self.lista_alunos.pack(fill="both", expand=True, padx=6, pady=(0, 8))
        abas = ctk.CTkTabview(area, fg_color=tema.CARD, corner_radius=10, segmented_button_selected_color=tema.DESTAQUE,
                              segmented_button_selected_hover_color=tema.DESTAQUE_ESCURO, text_color=tema.TEXTO)
        abas.grid(row=0, column=1, sticky="nsew", padx=6)
        area.grid_columnconfigure(1, weight=5)
        caixa = abas.add("📡 Pedidos ao vivo")
        self.criar_aba_chat(abas.add("💬 Chat"))
        self.ver_automaticos = ctk.CTkCheckBox(caixa, text="Mostrar as consultas automáticas (os apps perguntam "
                                                           "\"tem novidade?\" a cada segundo)",
                                               font=tema.fonte(12), fg_color=tema.DESTAQUE)
        self.ver_automaticos.pack(anchor="w", padx=10, pady=(0, 6))
        self.pedidos = ctk.CTkTextbox(caixa, wrap="none", font=FONTE_MONO, fg_color=tema.FUNDO)
        self.pedidos.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        self.pedidos.tag_config("ok", foreground=tema.SUCESSO)
        self.pedidos.tag_config("aviso", foreground=tema.DESTAQUE)
        self.pedidos.tag_config("erro", foreground=tema.PERIGO)
        self.pedidos.insert("end", f"{'hora':<9}{'aluno':<15}{'met':<5}{'status':<7}{'ms':>5}  {'rota':<44}{'ip':<16}bytes\n")
        self.pedidos.configure(state="disabled")
        caixa, _ = self.coluna(area, "🏆 Placar da turma", 2, 3)
        self.placar = ctk.CTkTextbox(caixa, wrap="word", font=tema.fonte(14), fg_color=tema.FUNDO)
        self.placar.pack(fill="both", expand=True, padx=10, pady=(0, 10))

    def criar_aba_chat(self, aba):
        """Controles do chat: so existem aqui no painel (os alunos nao tem como mexer nisso)."""
        topo = ctk.CTkFrame(aba, fg_color="transparent")
        topo.pack(fill="x", padx=6, pady=(0, 6))
        self.chave_chat = ctk.CTkSwitch(topo, text="Chat aberto para a turma", font=tema.fonte(14, negrito=True),
                                        command=self.trocar_chat, progress_color=tema.SUCESSO)
        self.chave_chat.pack(side="left")
        self.chave_chat.select()
        tema.botao_secundario(topo, "🧹 Limpar chat", self.limpar_chat, largura=140).pack(side="right")
        tema.texto_secundario(topo, "Para bloquear um aluno: 🔇 na lista à esquerda", 12).pack(side="right", padx=10)
        self.lista_chat = ctk.CTkScrollableFrame(aba, fg_color=tema.FUNDO)
        self.lista_chat.pack(fill="both", expand=True, padx=6)
        baixo = ctk.CTkFrame(aba, fg_color="transparent")
        baixo.pack(fill="x", padx=6, pady=6)
        self.campo_aviso = ctk.CTkEntry(baixo, height=36, font=tema.fonte(14),
                                        placeholder_text="Mensagem do professor para a turma...")
        self.campo_aviso.pack(side="left", fill="x", expand=True)
        self.campo_aviso.bind("<Return>", lambda evento: self.enviar_aviso())
        tema.botao(baixo, "📢 Enviar", self.enviar_aviso, largura=110, altura=36).pack(side="left", padx=(6, 0))

    def criar_rodape(self):
        rodape = ctk.CTkFrame(self, fg_color=tema.LATERAL, corner_radius=0)
        rodape.pack(fill="x", side="bottom")
        self.estatisticas = ctk.CTkLabel(rodape, text="", font=tema.fonte(14, negrito=True))
        self.estatisticas.pack(side="left", padx=20, pady=10)
        tema.botao_secundario(rodape, "🌐 Abrir no navegador", self.abrir_navegador, largura=180).pack(
            side="right", padx=(6, 20), pady=10)
        tema.botao_secundario(rodape, "🗑 Zerar placar", self.zerar_placar, largura=150).pack(side="right", padx=6)
        self.botao_preaquecer = tema.botao(rodape, "⬇ Baixar tudo agora", self.preaquecer, largura=190)
        self.botao_preaquecer.pack(side="right", padx=6)
        self.texto_preaquecer = ctk.CTkLabel(rodape, text="", font=tema.fonte(13), text_color=tema.TEXTO_SECUNDARIO)
        self.texto_preaquecer.pack(side="right", padx=10)

    # ---------------- atualizacao (a cada 1 segundo) ----------------

    def atualizar(self):
        foto = self.servidor.monitor.instantaneo()
        self.mostrar_alunos(foto["alunos"])
        self.mostrar_pedidos(foto)
        self.mostrar_chat()
        self.mostrar_placar()
        mb = foto["bytes"] / 1024 / 1024
        self.estatisticas.configure(text=f"{foto['total']} pedidos  ·  {foto['por_minuto']} no último minuto  ·  "
                                         f"{mb:.1f} MB enviados  ·  ligado {tempo_legivel(foto['ligado_ha'])}"
                                         .replace("ligado agora", "acabou de ligar"))
        avisos = []
        if self.servidor.espelho.sem_internet:
            avisos.append("⚠ Sem internet: entregando os dados salvos (funciona normalmente)")
        if self.servidor.aviso_descoberta:
            avisos.append(self.servidor.aviso_descoberta)
        self.status_dados.configure(text="  ·  ".join(avisos) or "Dados: dragonball-api.com (com cópia local)",
                                    text_color=tema.DESTAQUE if avisos else tema.TEXTO_SECUNDARIO)
        if self.progresso_preaquecer:
            self.texto_preaquecer.configure(text=self.progresso_preaquecer)
        self.after(ATUALIZAR_A_CADA, self.atualizar)

    def mostrar_alunos(self, pedidos_por_ip):
        """Alunos que entraram na sala, com o estado (lutando, no quiz) e o botao de bloquear o chat."""
        pedidos = {a["ip"]: a["pedidos"] for a in pedidos_por_ip}
        bloqueados = self.servidor.chat.instantaneo()["bloqueados"]
        alunos = self.servidor.sala.visao_do_professor()["alunos"]
        alunos.sort(key=lambda a: (a["estado"] == "ausente", a["nome"].lower()))
        online = sum(1 for a in alunos if a["estado"] != "ausente")
        self.titulo_alunos.configure(text=f"👥 Alunos conectados ({online})")
        assinatura = [(a["id"], a["estado"], a["id"] in bloqueados, pedidos.get(a["ip"], 0) // 20,
                       a["visto_ha"] // 30) for a in alunos]
        if assinatura == getattr(self, "_assinatura_alunos", None):
            return                                     # nada mudou: nao redesenha (evita piscar)
        self._assinatura_alunos = assinatura
        for filho in self.lista_alunos.winfo_children():
            filho.destroy()
        if not alunos:
            tema.texto_secundario(self.lista_alunos, "Ninguém ainda.\nPeça para os alunos\nconectarem!",
                                  14, justify="left").pack(anchor="w", pady=10)
        for aluno in alunos:
            self.linha_de_aluno(aluno, aluno["id"] in bloqueados, pedidos.get(aluno["ip"], 0))

    def linha_de_aluno(self, aluno, bloqueado, pedidos):
        linha = ctk.CTkFrame(self.lista_alunos, fg_color="transparent")
        linha.pack(fill="x", pady=2)
        presente = aluno["estado"] != "ausente"
        situacao = {"em_batalha": " · ⚔ lutando", "em_quiz": " · ❓ no quiz"}.get(aluno["estado"], "")
        if bloqueado:
            botao = ctk.CTkButton(linha, text="🔊", width=36, fg_color=tema.PERIGO, hover_color="#B83A3E",
                                  command=lambda: self.servidor.chat.desbloquear(aluno["id"]))
        else:
            botao = ctk.CTkButton(linha, text="🔇", width=36, fg_color=tema.FUNDO, hover_color="#4A4E54",
                                  command=lambda: self.servidor.chat.bloquear(aluno["id"], aluno["nome"]))
        botao.pack(side="right", padx=4)                  # primeiro o botao: ele nunca some
        textos = ctk.CTkFrame(linha, fg_color="transparent")
        textos.pack(side="left", fill="x", expand=True)
        ctk.CTkLabel(textos, text=f"● {aluno['nome']}{situacao}", font=tema.fonte(14, negrito=True),
                     text_color=tema.SUCESSO if presente else tema.TEXTO_SECUNDARIO, anchor="w").pack(fill="x")
        detalhe = f"   {aluno['ip']} · {pedidos} pedidos · {tempo_legivel(aluno['visto_ha'])}"
        ctk.CTkLabel(textos, text=detalhe, font=tema.fonte(12), anchor="w",
                     text_color=tema.TEXTO_SECUNDARIO).pack(fill="x")
        if bloqueado:
            ctk.CTkLabel(textos, text="   🔇 bloqueado no chat", font=tema.fonte(12, negrito=True), anchor="w",
                         text_color=tema.PERIGO).pack(fill="x")

    def mostrar_pedidos(self, foto):
        novos = foto["total"] - self.ultimo_pedido_mostrado
        if novos <= 0:
            return
        self.ultimo_pedido_mostrado = foto["total"]
        self.pedidos.configure(state="normal")
        for pedido in foto["pedidos"][-min(novos, len(foto["pedidos"])):]:
            if not self.ver_automaticos.get() and eh_automatico(pedido):
                continue
            status = pedido["status"]
            etiqueta = "erro" if status >= 500 else ("aviso" if status >= 400 else "ok")
            linha = (f"{pedido['hora']:<9}{(pedido['aluno'] or '-')[:14]:<15}{pedido['metodo']:<5}{status:<7}"
                     f"{pedido['ms']:>5}  {pedido['caminho'][:43]:<44}{pedido['ip']:<16}{pedido['bytes']}\n")
            self.pedidos.insert("end", linha, etiqueta)
        linhas = int(self.pedidos.index("end-1c").split(".")[0])
        if linhas > 400:                                   # guarda so as ultimas 400 linhas
            self.pedidos.delete("2.0", f"{linhas - 400}.0")
        self.pedidos.see("end")
        self.pedidos.configure(state="disabled")

    def mostrar_placar(self):
        resumo = self.servidor.placar.resumo()
        sala = self.servidor.sala.visao_do_professor()
        assinatura = (resumo["total_batalhas"], resumo["total_quiz"], resumo["total_duelos"],
                      [(d["a"], d["b"]) for d in sala["duelos"]])
        if assinatura == getattr(self, "_assinatura_placar", None):
            return
        self._assinatura_placar = assinatura
        medalhas = ["🥇", "🥈", "🥉"]
        linhas = ["CLASSIFICAÇÃO DOS ALUNOS (duelos)"]
        for i, aluno in enumerate(resumo["classificacao"][:15]):
            linhas.append(f"  {medalhas[i] if i < 3 else str(i + 1) + '.'} {aluno['nome']}: {aluno['pontos']} pts  "
                          f"(⚔ {aluno['batalha_v']}V {aluno['batalha_d']}D · ❓ {aluno['quiz_v']}V {aluno['quiz_d']}D)")
        if not resumo["classificacao"]:
            linhas.append("  nenhum duelo ainda")
        linhas += ["", "DUELOS AGORA"]
        for duelo in sala["duelos"]:
            icone = "⚔" if duelo["tipo"] == "batalha" else "❓"
            linhas.append(f"  {icone} {duelo['a']} x {duelo['b']} ({duelo['descricao']})")
        if not sala["duelos"]:
            linhas.append("  nenhum")
        linhas += ["", "TREINO: personagens mais vitoriosos"]
        for i, item in enumerate(resumo["hall_da_fama"]):
            linhas.append(f"  {medalhas[i] if i < 3 else str(i + 1) + '.'} {item['nome']}: {item['vitorias']}")
        if not resumo["hall_da_fama"]:
            linhas.append("  nenhuma batalha ainda")
        linhas += ["", "TREINO: recordes do quiz"]
        for i, item in enumerate(resumo["recordes_quiz"]):
            linhas.append(f"  {medalhas[i] if i < 3 else str(i + 1) + '.'} {item['aluno']}: "
                          f"{item['pontos']}/{item['rodadas'] * 4} pts")
        if not resumo["recordes_quiz"]:
            linhas.append("  ninguém jogou ainda")
        linhas += ["", "ÚLTIMOS DUELOS"]
        for duelo in resumo["ultimos_duelos"][:6]:
            linhas.append(f"  {duelo['vencedor']} venceu {duelo['perdedor']} ({duelo['descricao']})")
        self.placar.configure(state="normal")
        self.placar.delete("1.0", "end")
        self.placar.insert("1.0", "\n".join(linhas))
        self.placar.configure(state="disabled")

    # ---------------- chat ----------------

    def mostrar_chat(self):
        chat = self.servidor.chat.instantaneo()
        if bool(self.chave_chat.get()) != chat["liberado"]:
            if chat["liberado"]:
                self.chave_chat.select()
            else:
                self.chave_chat.deselect()
        assinatura = (chat["versao"], chat["ultimo_id"], tuple(sorted(chat["bloqueados"])))
        if assinatura == getattr(self, "_assinatura_chat", None):
            return
        self._assinatura_chat = assinatura
        for filho in self.lista_chat.winfo_children():
            filho.destroy()
        if not chat["mensagens"]:
            tema.texto_secundario(self.lista_chat, "Nenhuma mensagem ainda.", 14).pack(anchor="w", pady=8)
        for mensagem in chat["mensagens"][-100:]:
            self.linha_de_mensagem(mensagem, mensagem["id_autor"] in chat["bloqueados"])
        self.after(50, lambda: self.lista_chat._parent_canvas.yview_moveto(1.0))

    def linha_de_mensagem(self, mensagem, autor_bloqueado):
        linha = ctk.CTkFrame(self.lista_chat, fg_color="transparent")
        linha.pack(fill="x", pady=1)
        if mensagem["tipo"] == "sistema":
            cor, autor = tema.TEXTO_SECUNDARIO, ""
        elif mensagem["tipo"] == "professor":
            cor, autor = "#9CC3FF", "📢 Professor: "
        else:
            cor, autor = tema.TEXTO, f"{mensagem['autor']}{' (bloqueado)' if autor_bloqueado else ''}: "
        ctk.CTkLabel(linha, text=f"{mensagem['hora']}  {autor}{mensagem['texto']}", font=tema.fonte(13),
                     text_color=cor, anchor="w", justify="left", wraplength=560).pack(side="left", fill="x",
                                                                                    expand=True)
        if mensagem["tipo"] != "sistema":
            ctk.CTkButton(linha, text="✕", width=28, height=24, fg_color=tema.CARD, hover_color=tema.PERIGO,
                          command=lambda: self.servidor.chat.apagar(mensagem["id"])).pack(side="right", padx=4)

    def trocar_chat(self):
        self.servidor.chat.liberar(bool(self.chave_chat.get()))

    def limpar_chat(self):
        if messagebox.askyesno("Limpar chat", "Apagar TODAS as mensagens do chat?", parent=self):
            self.servidor.chat.limpar()

    def enviar_aviso(self):
        texto = self.campo_aviso.get().strip()
        if texto:
            self.servidor.chat.mensagem_do_professor(texto)
            self.campo_aviso.delete(0, "end")

    # ---------------- botoes ----------------

    def preaquecer(self):
        """Baixa todos os dados e imagens agora (numa thread), para a aula funcionar mesmo se a internet cair."""
        self.botao_preaquecer.configure(state="disabled")
        self.progresso_preaquecer = "Começando..."

        def progresso(feitos, total, texto):
            self.progresso_preaquecer = f"Baixando {texto}: {feitos}/{total}"

        def trabalho():
            try:
                total, falhas = self.servidor.espelho.preaquecer(progresso)
                self.progresso_preaquecer = (f"✔ Pronto! {total - falhas} imagens guardadas"
                                             + (f" ({falhas} falharam)" if falhas else ""))
            except Exception as erro:
                self.progresso_preaquecer = f"Erro: {erro}"

        threading.Thread(target=trabalho, daemon=True).start()

    def zerar_placar(self):
        if messagebox.askyesno("Zerar placar", "Apagar TODAS as batalhas e partidas de quiz da turma?", parent=self):
            self.servidor.placar.zerar()

    def abrir_navegador(self):
        webbrowser.open(f"http://127.0.0.1:{self.servidor.porta}/")

    def fechar(self):
        if messagebox.askyesno("Desligar servidor", "Desligar o servidor? Os alunos vão perder a conexão.",
                               parent=self):
            self.servidor.parar()
            self.destroy()
