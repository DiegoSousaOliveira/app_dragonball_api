"""Tela Rede: o raio-X da conexao (pedidos, testador, velocidade, DNS e experimentos)."""

import json

import customtkinter as ctk
import requests

from core import api, descoberta, rede
from interface import tarefas, tema
from interface.telas import Tela, cabecalho

FONTE_MONO = ("Consolas", 12)


def caixa_de_texto(mestre, altura=380):
    caixa = ctk.CTkTextbox(mestre, height=altura, wrap="none", font=FONTE_MONO, fg_color=tema.CARD)
    caixa.pack(fill="both", expand=True, padx=6, pady=6)
    return caixa


def escrever(caixa, texto):
    caixa.configure(state="normal")
    caixa.delete("1.0", "end")
    caixa.insert("1.0", texto)
    caixa.configure(state="disabled")


class GraficoDeBarras(ctk.CTkCanvas):
    """Uma barra por requisicao, agrupadas por cor. Altura = tempo (regra de tres)."""

    def __init__(self, mestre, largura=860, altura=330):
        super().__init__(mestre, width=largura, height=altura, bg=tema.FUNDO, highlightthickness=0)
        self.largura, self.altura, self.margem = largura, altura, 46

    def desenhar(self, grupos):
        """grupos = [(nome, [ms, ...], cor), ...]"""
        self.delete("all")
        total = sum(len(tempos) for _, tempos, _ in grupos)
        maior = max(max(tempos) for _, tempos, _ in grupos) or 1
        largura_barra = (self.largura - 2 * self.margem) / total
        fonte = (tema.escolher_fonte(), 9)
        x = self.margem
        for nome, tempos, cor in grupos:
            inicio = x
            for ms in tempos:
                altura = (self.altura - 2 * self.margem) * ms / maior
                topo = self.altura - self.margem - altura
                self.create_rectangle(x + 3, topo, x + largura_barra - 3, self.altura - self.margem, fill=cor, width=0)
                self.create_text(x + largura_barra / 2, topo - 8, text=f"{ms:.0f}", fill=tema.TEXTO, font=fonte)
                x += largura_barra
            media = sum(tempos) / len(tempos)
            self.create_text((inicio + x) / 2, self.altura - self.margem + 18, text=f"{nome}  (média {media:.0f} ms)",
                             fill=cor, font=(tema.escolher_fonte(), 12, "bold"))
        self.create_line(self.margem, self.altura - self.margem, self.largura - self.margem,
                         self.altura - self.margem, fill=tema.TEXTO_SECUNDARIO)


class TelaRede(Tela):
    def __init__(self, app):
        super().__init__(app)
        cabecalho(self, "Rede", "O que acontece \"por baixo\" quando o app conversa com o servidor.")
        abas = ctk.CTkTabview(self, fg_color=tema.LATERAL, segmented_button_selected_color=tema.DESTAQUE,
                              segmented_button_selected_hover_color=tema.DESTAQUE_ESCURO,
                              text_color=tema.TEXTO)
        abas.pack(fill="both", expand=True, padx=20, pady=(0, 16))
        self.aba_conexao(abas.add("Conexão"))
        self.aba_pedidos(abas.add("Pedidos"))
        self.aba_testar(abas.add("Testar"))
        self.aba_velocidade(abas.add("Velocidade"))
        self.aba_experimentos(abas.add("Experimentos"))
        self._agendado = None

    def ao_mostrar(self):
        self.atualizar_pedidos()
        self.atualizar_conexao()

    def ao_esconder(self):
        if self._agendado:
            self.after_cancel(self._agendado)
            self._agendado = None

    # ---------------- Conexao ----------------

    def aba_conexao(self, aba):
        self.texto_conexao = caixa_de_texto(aba)

    def atualizar_conexao(self):
        host, porta = rede.host_da_fonte()
        meus_ips = ", ".join(descoberta.ips_locais()) or "(sem rede)"
        if api.conectado_ao_servidor():
            linhas = [
                "Você está conectado ao SERVIDOR DA SALA (rede local).", "",
                f"  Meu IP (este computador) .... {meus_ips}",
                f"  IP do servidor .............. {host}",
                f"  Porta ....................... {porta}",
                "  Protocolo ................... HTTP (sem o S: dentro da sala, sem criptografia)", "",
                "Caminho de cada pedido:",
                f"  1. TCP: aperto de mãos com {host}:{porta} (SYN, SYN-ACK, ACK)",
                "  2. HTTP: GET /api/characters  (com o cabeçalho X-Aluno: seu nome)",
                "  3. Resposta: status 200 + cabeçalhos + JSON",
                "", "Não precisa de DNS (já sabemos o IP) nem de TLS. Por isso é tão rápido!",
                "O servidor do professor busca os dados na internet UMA vez e entrega para a turma toda.",
            ]
        else:
            linhas = [
                "Você está usando a INTERNET DIRETO (sem o servidor da sala).", "",
                f"  Meu IP (rede local) ......... {meus_ips}",
                f"  Servidor .................... {host}",
                f"  Porta ....................... {porta} (HTTPS = HTTP protegido por TLS)", "",
                "Caminho de cada pedido:",
                f"  1. DNS: 'qual o IP de {host}?'",
                "  2. TCP: aperto de mãos (SYN, SYN-ACK, ACK)",
                "  3. TLS: combinam a criptografia (o cadeado do navegador)",
                "  4. HTTP: GET /api/characters",
                "  5. Resposta: status + cabeçalhos + JSON",
            ]
        escrever(self.texto_conexao, "\n".join(linhas))
        if not api.conectado_ao_servidor():
            tarefas.em_segundo_plano(self, lambda: rede.descobrir_ip(host), self._mostrar_dns,
                                     lambda erro: None)

    def _mostrar_dns(self, resultado):
        ip, ms = resultado
        texto = self.texto_conexao.get("1.0", "end").replace(f"'qual o IP de", f"(respondeu {ip} em {ms:.0f} ms) "
                                                                                 f"'qual o IP de")
        escrever(self.texto_conexao, texto)

    # ---------------- Pedidos ----------------

    def aba_pedidos(self, aba):
        self.texto_pedidos = caixa_de_texto(aba)
        self.resumo_pedidos = tema.texto_secundario(aba, "", 13)
        self.resumo_pedidos.pack(anchor="w", padx=8, pady=(0, 6))

    def atualizar_pedidos(self):
        log = api.copia_do_log()
        linhas = [f"{'hora':<9}{'origem':<7}{'met':<5}{'status':>6}{'ms':>7}{'bytes':>9}  {'tipo':<18}endereço"]
        for item in reversed(log[-60:]):
            tipo = item["content_type"].split(";")[0][:17]
            linhas.append(f"{item['hora']:<9}{item['origem']:<7}{item['metodo']:<5}{item['status']:>6}"
                          f"{item['ms']:>7}{item['bytes']:>9}  {tipo:<18}{item['url'][:90]}")
        escrever(self.texto_pedidos, "\n".join(linhas))
        da_rede = [i for i in log if i["origem"] == "rede"]
        total = sum(i["bytes"] for i in da_rede)
        self.resumo_pedidos.configure(text=f"{len(log)} pedidos nesta sessão: {len(da_rede)} pela rede, "
                                           f"{len(log) - len(da_rede)} do cache · {total / 1024:.0f} KB recebidos "
                                           "pela rede (os mais novos aparecem em cima)")
        self._agendado = self.after(2000, self.atualizar_pedidos) if self.visivel else None

    # ---------------- Testar ----------------

    ENDPOINTS = ["/characters", "/planets", "/transformations", "/characters/{id}", "/planets/{id}"]

    def aba_testar(self, aba):
        linha = ctk.CTkFrame(aba, fg_color="transparent")
        linha.pack(fill="x", padx=6, pady=6)
        self.endpoint = ctk.CTkOptionMenu(linha, values=self.ENDPOINTS, width=170, fg_color=tema.CARD,
                                          button_color=tema.CARD)
        self.endpoint.pack(side="left")
        self.campos = {}
        for nome, exemplo in (("id", "1"), ("page", ""), ("limit", ""), ("name", ""), ("race", "")):
            ctk.CTkLabel(linha, text=nome, font=tema.fonte(12)).pack(side="left", padx=(10, 2))
            campo = ctk.CTkEntry(linha, width=80, placeholder_text=exemplo)
            campo.pack(side="left")
            self.campos[nome] = campo
        tema.botao(linha, "Enviar GET", self.testar, largura=110).pack(side="left", padx=10)
        self.texto_teste = caixa_de_texto(aba, 340)
        escrever(self.texto_teste, "Escolha um endpoint, preencha (ou não) os parâmetros e clique em Enviar GET.\n"
                                   "Experimente id = 99999 ou abc, limit = 1000, race = saiyan...")

    def testar(self):
        caminho = self.endpoint.get()
        if "{id}" in caminho:
            caminho = caminho.replace("{id}", self.campos["id"].get().strip() or "1")
            params = {}
        else:
            params = {nome: c.get().strip() for nome, c in self.campos.items() if nome != "id" and c.get().strip()}
        escrever(self.texto_teste, "Enviando...")
        tarefas.em_segundo_plano(self, lambda: rede.requisicao_crua(caminho, params), self.mostrar_resposta,
                                 lambda erro: escrever(self.texto_teste, f"ERRO DE REDE: {type(erro).__name__}\n"
                                                                         f"{erro}\n\nNão houve resposta."))

    def mostrar_resposta(self, resposta):
        linhas = [f"URL montada: {resposta.url}", f"Status: {resposta.status_code} {resposta.reason}",
                  f"Tempo: {resposta.elapsed.total_seconds() * 1000:.0f} ms   Tamanho: {len(resposta.content)} bytes",
                  "", "Cabeçalhos da resposta:"]
        linhas += [f"  {nome}: {valor}" for nome, valor in resposta.headers.items()]
        try:
            corpo = json.dumps(resposta.json(), indent=2, ensure_ascii=False)
        except ValueError:
            corpo = resposta.text or "(corpo vazio)"
        linhas += ["", "Corpo (primeiros 1500 caracteres):", corpo[:1500]]
        escrever(self.texto_teste, "\n".join(linhas))

    # ---------------- Velocidade ----------------

    def aba_velocidade(self, aba):
        linha = ctk.CTkFrame(aba, fg_color="transparent")
        linha.pack(fill="x", padx=6, pady=6)
        self.botao_sala = tema.botao(linha, "Servidor da sala × Internet", self.comparar_sala_internet, largura=240)
        self.botao_sala.pack(side="left")
        self.botao_sessao = tema.botao_secundario(linha, "requests.get × Session", self.comparar_get_sessao, largura=200)
        self.botao_sessao.pack(side="left", padx=10)
        self.explicacao = tema.texto_secundario(linha, "Faça um palpite antes de medir!", 13)
        self.explicacao.pack(side="left", padx=10)
        self.grafico = GraficoDeBarras(aba)
        self.grafico.pack(pady=6)
        self.texto_velocidade = tema.texto_secundario(aba, "", 13, wraplength=850, justify="left")
        self.texto_velocidade.pack(anchor="w", padx=10)

    def _medindo(self, ligado):
        for botao in (self.botao_sala, self.botao_sessao):
            botao.configure(state="disabled" if ligado else "normal")
        if ligado:
            self.texto_velocidade.configure(text="Medindo... (alguns segundos)", text_color=tema.TEXTO_SECUNDARIO)

    def comparar_sala_internet(self):
        if not api.conectado_ao_servidor():
            self.texto_velocidade.configure(text="Conecte-se ao servidor do professor para comparar com a internet.",
                                            text_color=tema.PERIGO)
            return
        self._medindo(True)

        def medir():
            sala = rede.medir_latencias(8, base=api.URL_BASE)
            try:
                internet = rede.medir_latencias(8, base=api.URL_INTERNET)
            except requests.RequestException:
                internet = None
            return sala, internet

        def mostrar(resultado):
            sala, internet = resultado
            self._medindo(False)
            grupos = [("Servidor da sala", sala, tema.SUCESSO)]
            if internet:
                grupos.append(("Internet (dragonball-api.com)", internet, tema.PERIGO))
                vezes = (sum(internet) / len(internet)) / max(sum(sala) / len(sala), 0.1)
                texto = (f"O servidor da sala foi umas {vezes:.0f} vezes mais rápido! Ele está a poucos metros "
                         "(rede local, sem DNS e sem TLS); a internet passa por vários roteadores até outro país.")
            else:
                texto = "Sem internet agora: só deu para medir o servidor da sala (e ele continua funcionando!)."
            self.grafico.desenhar(grupos)
            self.texto_velocidade.configure(text=texto, text_color=tema.TEXTO)

        tarefas.em_segundo_plano(self, medir, mostrar, self._falhou_medida)

    def comparar_get_sessao(self):
        self._medindo(True)

        def medir():
            return (rede.medir_latencias(8, usar_sessao=False), rede.medir_latencias(8, usar_sessao=True))

        def mostrar(resultado):
            sem, com = resultado
            self._medindo(False)
            self.grafico.desenhar([("requests.get (conexão nova)", sem, tema.PERIGO),
                                   ("Session (keep-alive)", com, tema.SUCESSO)])
            self.texto_velocidade.configure(
                text="Com requests.get, CADA pedido abre uma conexão nova (aperto de mãos TCP, e na internet também "
                     "DNS e TLS). A Session abre só na 1ª vez e reaproveita a conexão: repare que só a 1ª barra "
                     "verde costuma ser alta.", text_color=tema.TEXTO)

        tarefas.em_segundo_plano(self, medir, mostrar, self._falhou_medida)

    def _falhou_medida(self, erro):
        self._medindo(False)
        self.texto_velocidade.configure(text=f"Não consegui medir: {type(erro).__name__}", text_color=tema.PERIGO)

    # ---------------- Experimentos ----------------

    def aba_experimentos(self, aba):
        linha = ctk.CTkFrame(aba, fg_color="transparent")
        linha.pack(fill="x", padx=6, pady=6)
        tema.botao(linha, "Erros de propósito", self.erros_de_proposito, largura=170).pack(side="left")
        tema.botao_secundario(linha, "Timeout de 0,001 s", self.timeout, largura=170).pack(side="left", padx=10)
        self.chave_offline = ctk.CTkSwitch(linha, text="Modo offline (simula cabo desligado)",
                                           command=self.trocar_offline, progress_color=tema.PERIGO)
        self.chave_offline.pack(side="left", padx=10)
        if api.modo_offline:
            self.chave_offline.select()
        self.texto_experimentos = caixa_de_texto(aba, 340)

    def erros_de_proposito(self):
        escrever(self.texto_experimentos, "Enviando 4 pedidos errados de propósito...")

        def enviar():
            linhas = []
            for descricao, caminho in rede.ERROS_DE_PROPOSITO:
                try:
                    resposta = rede.requisicao_crua(caminho)
                    corpo = resposta.text[:90] or "(corpo vazio!)"
                    linhas += [f"{descricao:<30} {caminho:<24} -> {resposta.status_code} {resposta.reason}",
                               f"    {corpo}"]
                except requests.RequestException as erro:
                    linhas.append(f"{descricao:<30} {caminho:<24} -> erro de rede {type(erro).__name__}")
            linhas += ["", "4xx = o PEDIDO tem problema (culpa de quem pediu). 5xx = o SERVIDOR quebrou.",
                       "Compare: o servidor da sala responde 404/400 \"certinho\"; a dragonball-api original",
                       "responde 400 para id inexistente, 500 para 'abc' e 200 VAZIO para transformação inexistente."]
            return "\n".join(linhas)

        tarefas.em_segundo_plano(self, enviar, lambda texto: escrever(self.texto_experimentos, texto))

    def timeout(self):
        tarefas.em_segundo_plano(self, rede.provocar_timeout,
                                 lambda nome: escrever(self.texto_experimentos,
                                                       f"Erro recebido: {nome}\n\nTimeout = tempo máximo de espera. "
                                                       "Pedimos uma resposta em 0,001 segundo: impossível!\n"
                                                       "Sem timeout, um programa pode ficar esperando PARA SEMPRE."))

    def trocar_offline(self):
        api.modo_offline = bool(self.chave_offline.get())
        if api.modo_offline:
            texto = ("Modo offline LIGADO. Vá nas outras telas: tudo continua funcionando com o cache e os dados "
                     "salvos, como se o cabo de rede estivesse desligado. O que nunca foi baixado aparece "
                     "'sem imagem'.")
        else:
            texto = "Modo offline desligado: o app voltou a usar a rede."
        escrever(self.texto_experimentos, texto)
