# Built-in Libs
import re
import os
import sys
import datetime as dt
from collections import OrderedDict, defaultdict
from time import sleep
from contextlib import contextmanager

# Other Helpful Libs
import unidecode
from bs4 import BeautifulSoup as soup
from typing import Type, Dict, List, Tuple, Sequence, Any, Callable

# Selenium Dependencies
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select
from selenium import webdriver

# Others modules from this package
from functions import add_point_cpf_cnpj
from .common import (
    armazena_tags, 
    cria_dict_acoes, 
    string_endereço, 
    pode_expedir
)
from . import config
from page import Page, Elem


Processos = Dict[str, Any]

# TODO: Add password Encryption
# TODO: Select Normal/Teste
def login_sei(usr: str, pwd: str, driver: Callable, timeout=10)-> 'Sei':
    """
    Esta função recebe um objeto Webdrive e as credenciais
    do usuário, loga no SEI - ANATEL e retorna uma instância da classe
    SEI.
    """

    helper = config.Sei_Login.Login

    page = Page(driver)
    page.timeout = timeout
    page.driver.get(helper.get('url'))
    page.driver.maximize_window()

    page._atualizar_elemento(helper.get('log'), usr)
    page._atualizar_elemento(helper.get(pwd), pwd)

    page._clicar(helper.get('submit'), silent=True)
   
    return Sei(page)

class Sei:
    """Esta subclasse da classe Page define métodos de execução de ações na
    página principal do SEI e de resgate de informações
    """

    timeout: int = 10

    def __init__(self, driver=None, processos: Processos=None)-> None:
        self.page = Page(driver)
        self.page.timeout = timeout
        self._processos = processos if processos is not None else OrderedDict()

    # Used to emulate attributes from page as if from this class
    #def __getattr__(self, k):
    #    return getattr(self.page, k)


    def _mudar_lotação(self, lotação: str)->None:

        h = config.SeiHeader

        self.page._selecionar_por_texto(h.LOTACAO, lotação, timeout=self.timeout)

    def _set_processos(self, processos)-> None:
        self._processos = OrderedDict((p["numero"],p) for p in processos)

    def pesquisa_contato(self, termo: str, timeout=timeout):
        """Pesquisa a existência de cadastro de contato `nome` 
        
        Args:
            termo (str): termo a ser pesquisado
            timeout (int, optional): tempo de espera pelos elementos da página. Defaults to 10.
        """       
        helper = config.Contato

        termo = unidecode._unidecode(termo)

        if self.page.get_title() != helper.TITLE:
            with self.page.wait_for_page_load():
                self._vai_para_pag_contato()

        try:
            chave_pesquisa = self.wait_for_element_to_click(config.Pesq_contato.ID_SEARCH, timeout=timeout
            )
        except TimeoutException:

            print("Elemento não encontrado ou tempo de carregamento excedido")

            return None

        chave_pesquisa.clear()

        chave_pesquisa.send_keys(termo)

        self.page_clicar(helper.BTN_PESQUISAR, timeout=timeout

        )

        html = soup(self.page.driver.page_source, "lxml")

        tags = html.find_all("tr", class_="infraTrClara")

        for tag in tags:

            for children in tag.children:

                if hasattr(children, "text"):

                    if termo.lower() in str(children.text).lower():
                        return tag.find_all("a")

        else:

            return None

    def _cria_contato(self, dados: Dict, timeout=10
    )-> None:

        helper = config.Contato        

        with self.page.wait_for_page_load():
            self.page._clicar(helper.BTN_NOVO)       
        
            self._mudar_dados_contato(dados, novo=True, timeout=timeout)

    def _mudar_dados_contato(self, dados: Dict, novo=False, timeout=10
    ):

        helper = config.Contato

        dados = {k: str(v).title() for k, v in dados.items() if k is not "UF"}

        dados["UF"] = dados["UF"].upper()

        self.page._selecionar_por_texto(helper.TIPO, "Pessoa Física", timeout=timeout
        )

        self.page._clicar(helper.PF, timeout=timeout)

        cpf = dados.get("CNPJ/CPF", "")

        cpf = add_point_cpf_cnpj(cpf)

        self.page._atualizar_elemento(helper.SIGLA, cpf, timeout)

        if dados.get("Sexo", "") == "FEMININO":
            self.page._clicar(helper.FEMININO, timeout=timeout)
        else:
            self.page._clicar(helper.MASCULINO, timeout=timeout)

        self.page._atualizar_elemento(
            helper.NOME, dados.get("Nome/Razão Social", "")
        )

        self.page._atualizar_elemento(
            helper.END,
            dados.get("Logradouro", "") + " " + dados.get("Número", ""), timeout
        )

        self.page._atualizar_elemento(helper.COMP, dados.get("Complemento", ""), timeout)

        self.page._atualizar_elemento(helper.BAIRRO, dados.get("Bairro", ""), timeout)

        self.page._selecionar_por_texto(helper.PAIS, "Brasil", timeout)

        self.page._selecionar_por_texto(helper.UF, dados.get("UF", ""), timeout)

        self.page._atualizar_elemento(helper.CEP, dados.get("Cep", ""), timeout)

        self.page._atualizar_elemento(helper.CPF, dados.get("Cpf_RF", ""),timeout)

        self.page._atualizar_elemento(helper.RG, dados.get("Rg", ""),timeout)

        self.page._atualizar_elemento(helper.ORG, dados.get("Org", ""),timeout)

        self.page._atualizar_elemento(helper.NASC, dados.get("Nasc", ""), timeout)

        self.page._atualizar_elemento(helper.FONE, dados.get("Fone", ""),timeout)

        self.page._atualizar_elemento(helper.CEL, dados.get("Cel", ""),timeout)

        self.page._atualizar_elemento(helper.EMAIL, dados.get("Email", ""),timeout)
        
        # Cidade por último para dar Tempo de Carregamento
        cidade = Select(self.page.wait_for_element_to_be_visible(helper.CIDADE, timeout))

        for option in cidade.options:

            ascii_option = unidecode._unidecode(option.text).lower()

            if dados.get("Município", "").lower() == ascii_option:
                cidade.select_by_visible_text(option.text, timeout)
                break

        if not novo:
            salvar = self.page._clicar(helper.SALVAR, timeout=timeout
            )
        else:
            salvar = self.page._clicar(helper.SALVAR_NOVO, timeout=timeout
            )

    def _vai_para_pag_contato(self):

        html = soup(self.page.driver.page_source, "lxml")

        tag = html.find("li", string="Listar")

        if not tag:
            raise LookupError(
                "The tag of type {0} and string {1} is not present in the page".format(
                    "<li>", "Listar"
                )
            )

        link = tag.a.attrs["href"]

        self.go(link)

    def go(self, link):
        """ Simplifies the navigation of href pages on sei.anatel.gov.br
        by pre-appending the required prefix NAV_URL       """

        prefix = config.Sei_Login.Base.url

        if prefix not in link:
            link = prefix + link

        self.page.driver.get(link)

    def get_processos(self):
        return self._processos

    def filter_processos(self, **kwargs):

        processos = {}

        for k, v in kwargs:
            processos = {p: q for p, q in self._processos.items() if p.get(k) == v}

        return processos

    def go_to_processo(self, num):

        p = self._processos.get(num, None)

        if p is not None:

            self.go(p["link"])

            return Processo(self.page, numero=num, tags=self._processos[num])

        else:

            try:

                self.page._atualizar_elemento(
                    config.Sei_Login.Base.pesquisa, num + Keys.ENTER
                )

            except NoSuchElementException:

                self.go_to_init_page()

            return Processo(self.page, num, tags=None)

    def see_detailed(self):
        """
        Expands the visualization from the main page in SEI
        """
        try:
            ver_todos = self.page.wait_for_element_to_click(config.Sei_Inicial.ATR)

            if ver_todos.text == "Ver todos os processos":
                ver_todos.click()

        except TimeoutException:

            print(
                "A página não carregou no tempo limite ou cheque o link\
                  'ver todos os processos'"
            )

        try:

            visual_detalhado = self.page.wait_for_element_to_click(
                config.Sei_Inicial.VISUAL
            )

            if visual_detalhado.text == "Visualização detalhada":
                visual_detalhado.click()

        except TimeoutException:

            print(
                "A página não carregou no tempo limite ou cheque o link\
            de visualização detalhada"
            )

    def is_init_page(self):
        """Retorna True se a página estiver na página inicial do SEI, False
        caso contrário
        """
        return self.page.get_title() == config.Sei_Inicial.TITLE

    # noinspection PyProtectedMember
    def go_to_init_page(self):
        """
        Navega até a página inicial do SEI caso já esteja nela
        a página é recarregada
        Assume que o link está presente em qualquer subpágina do SEI
        """

        try:

            self.page._clicar(config.Sei_Login.Base.init)

        except:

            self.go("")

    def show_lat_menu(self):
        """
        Exibe o Menu Lateral á Esquerda no SEI para acessos aos seus diversos
        links
        Assume que o link está presente em qualquer subpágina do SEI
        """
        menu = self.page.wait_for_element(config.Sei_Login.Base.menu)

        if menu.get_attribute("title") == "Exibir Menu do Sistema":
            menu.click()

    def itera_processos(self):
        """
        Navega as páginas de processos abertos no SEI e guarda as tags
        html dos processos como objeto soup no atributo processos_abertos
        """

        # Apaga o conteúdo atual da lista de processos
        processos = []

        # assegura que está inicial
        if not self.is_init_page():
            self.go_to_init_page()

        # Mostra página com informações detalhadas
        self.see_detailed()

        html_sei = soup(self.page.driver.page_source, "lxml")

        processos += html_sei("tr", {"class": "infraTrClara"})

        try:

            contador = self.page.wait_for_element(config.Sei_Inicial.CONT, timeout=30)

        except TimeoutException:

            print(
                "A página demorou muito tempo para carregar ou há somente 1 página de Processos"
            )

            return

        contador = Select(contador)

        paginas = [pag.text for pag in contador.options]

        counter = 1

        for pag in paginas:
            print("Registrando processos: página {}".format(pag))
            # One simple repetition to avoid more complex code
            contador = Select(self.page.wait_for_element(config.Sei_Inicial.CONT))
            contador.select_by_visible_text(pag)

            sleep(10)

            # pattern = re.compile("Lista de Processos\s{1}\((\d+).*\)")

            html_sei = soup(self.page.driver.page_source, "lxml")

            processos += html_sei("tr", {"class": "infraTrClara"})

            counter += 400

        processos_abertos = []

        for line in processos:

            tags = line("td")

            if len(tags) == 6:
                processos_abertos.append(armazena_tags(tags))

        self._set_processos(processos_abertos)

    def atualizar_contato(self, nome, dados):

        tag_contact = self.pesquisa_contato(nome)

        if not tag_contact:

            self._cria_contato(dados)

        else:

            for tag in tag_contact:

                for child in tag.children:

                    if hasattr(child, "attrs"):

                        if child.get("title") == "Alterar Contato":

                            link = tag.get("href")

                            if link:
                                with self.page.wait_for_page_load():
                                    self.go(link)

                                self._mudar_dados_contato(dados, novo=False)

                                return

    def cria_processo(self, tipo, desc="", inter="", nivel="público"):

        tipo = str(tipo)

        assert tipo in config.Criar_Processo.PROCS, print(
            "O tipo de processo digitado {0}, não é válido".format(str(tipo))
        )

        self.show_lat_menu()

        init_proc = self.page.wait_for_element_to_click(config.Sei_Menu.INIT_PROC)

        init_proc.click()

        filtro = self.page.wait_for_element_to_click(config.Criar_Processo.FILTRO)

        filtro.send_keys(tipo)

        # exibe_todos = Sei.wait_for_element_to_click(loc.Tipos.EXIBE_ALL)

        # exibe_todos.click()

        # select = Select(Sei.wait_for_element(loc.Tipos.SL_TIP_PROC))

        tipo = self.page.wait_for_element_to_click((By.LINK_TEXT, tipo))

        tipo.click()

        if desc:
            espec = self.page.wait_for_element(config.Proc_incluir.ESPEC)

            espec.send_keys(desc)

        if inter:
            # self.cadastrar_interessado(inter)

            self.pesquisa_contato(inter)

        if nivel == "público":

            nivel = self.page.wait_for_element(config.Proc_incluir.PUBL)

        elif nivel == "restrito":

            nivel = self.page.wait_for_element(config.Proc_incluir.REST)

        else:

            nivel = self.page.wait_for_element(config.Proc_incluir.SIG)

        nivel.click()

class Processo(Sei):
    def __init__(self, page, numero, tags=None):
        super().__init__(page)
        #self.page = page
        self.numero = numero
        self.tags = tags if tags is not None else dict()
        self.acoes = {}
        self.arvore = OrderedDict()
        self.link = self.page.driver.current_url

    def get_tags(self):
        return self.tags

    @contextmanager
    def _go_to_central_frame(self):

        # Switch to central frame
        self.page.driver.switch_to.frame("ifrVisualizacao")

        try:
            yield
        finally:
            # Return to main content
            self.page.driver.switch_to_default_content()

    def _acoes_central_frame(self):

        assert (
            self.page.get_title() == config.Proc_incluir.TITLE
        ), "Erro ao navegar para o processo"

        with self._go_to_central_frame():
            self.page.wait_for_element(config.Proc_central.ACOES)

            html_frame = soup(self.page.driver.page_source, "lxml")

            acoes = html_frame.find(id="divArvoreAcoes").contents

            return cria_dict_acoes(acoes)

    def _get_acoes(self, doc=None):

        # O comportamento padrão é extrair as ações do Processo Pai
        if doc is None:

            self._click_na_arvore(self.numero)

        else:

            self._click_na_arvore(doc)

        return self._acoes_central_frame()

    def _info_unidades(self):
        #return "Concluir Processo" in self._get_acoes()
        with self._go_to_central_frame():
            source = soup(self.page.driver.page_source, "lxml")
            return source.find("div", id="divInformacao")

    def is_open(self, setor):
        return self._info_unidades().find(string=setor)

    

    def close_processo(self):
        self.page.fechar()

    @contextmanager
    def _go_to_arvore(self):

        # Switch to tree frame
        self.page.driver.switch_to.frame("ifrArvore")

        try:
            # yield the iframe page source as a BeautifulSoup object
            yield
        finally:
            # Return to main content
            self.page.driver.switch_to_default_content()

    def armazena_arvore(self):

        # Switch to the frame in which arvore is in, only inside the contextmanager
        with self._go_to_arvore():

            tree = soup(self.page.driver.page_source, "lxml")

            for tag in tree.find_all("a"):

                child = tag.find("span")

                text = None

                if not child:
                    child = tag.find("img")
                    if child and "title" in child.attrs:
                        text = child["title"]
                elif hasattr(child, "text"):
                    text = child.string
                elif "title" in child.attrs:                
                    text = child["title"]

                if text is not None:
                    self.arvore[text.strip()] = tag.attrs

        return self.arvore

    def _click_na_arvore(self, label, timeout = 5):

        tree = self.armazena_arvore()

        # self.armazena_arvore updates self.arvore dict and return it
        for k, v in tree.items():

            if label in k:

                with self._go_to_arvore():
                    self.page._clicar((By.ID, v["id"]), timeout=10
                    )

                return

        else:
            raise ValueError(
                "Não foi encontrato o elemento {0} na árvore do Processo".format(label)
            )

        # finally:

    #     with self._go_to_arvore():

    #         self._click_button((By.LINK_TEXT, self.numero), timeout=10
    # )

    #         return

    def abrir_pastas(self, timeout = 10) -> None:

        h = config.Arvore.ABRIR_PASTAS

        tree = self.armazena_arvore()
        
        plus = tree.get("Abrir todas as Pastas")

        if plus:
            with self._go_to_arvore():
                try:
                    self.page._clicar((By.ID, plus["id"]), timeout=10
                    )
                except TimeoutException:
                    self.go(plus['href'])

    def edita_doc(self, num_doc, timeout = 10)-> None:

        self = Sei.go_to_processo(self, num_doc)

        key = lambda x: x.replace(" ", "_").split("_")[-2]

        with self._go_to_arvore():
            
            doc = self.page.wait_for_element((By.PARTIAL_LINK_TEXT, num_doc), timeout=10
            )

            source = soup(doc.get_attribute("innerHTML"), "lxml")
            
            source = source.find("span") 

            title = source.attrs['title'][:-10] + " - OK" + source.attrs['title'][-10:]

            self.page.driver.execute_script(fr"var elem=arguments[0]; elem.title = '{title}'; elem.text = '{title}'", doc)

            
        #    self.page._clicar(h, timeout=10
        # )

    def send_doc_por_email(self, label, dados, timeout=5):

        # script = self._get_acoes(num_doc)["Enviar Documento por Correio Eletrônico"]

        helper = config.Email

        self._click_na_arvore(label, timeout=10
        )

        with self._go_to_central_frame():
            # TODO: Why this is not working?
            # self.page.driver.execute_script(script)

            # Usamos um context manager
            # para garantir que depois de finalizar a tarefa na nova janela
            # voltamos o foco do navegador para a janela principal
            with self.page._navega_nova_janela():
                self.page._click_button_new_win((By.XPATH, '//*[@id="divArvoreAcoes"]/a[6]'))

                destinatario, assunto, mensagem = dados

                self.page._atualizar_elemento(
                    helper.get('destinatario'), destinatario, timeout=10

                )

                self.page._atualizar_elemento(helper.get('assunto'), assunto, timeout=10
                )

                self.page._selecionar_por_texto(helper.get('mensagem'), mensagem, timeout=10
                )

                # After putting the email, we must validate ir by clicking it or pressing ENTER
                self.page._atualizar_elemento(
                    helper['destinatario'], 2 * Keys.ENTER, timeout=10

                )

                self.page._clicar(helper.get('enviar'), timeout=10
                )

    def info_oficio(self, num_doc):

        assert (
            self.page.get_title() == config.Proc_incluir.TITLE
        ), "Erro ao navegar para o processo"

        # Switch to tree frame
        self._go_to_arvore()

        with self.page.wait_for_page_load():
            html_tree = soup(self.page.driver.page_source, "lxml")

            info = html_tree.find(title=re.compile(num_doc)).string

            assert info != "", "Falha ao retornar Info do Ofício da Árvore"

            # return to parent frame
            self.page.driver.switch_to_default_content()

            return info

    def update_andamento(self, buttons, info):
        assert (
            self.page.get_title() == config.Proc_incluir.TITLE
        ), "Erro ao navegar para o processo"

        andamento = buttons[4]

        link = andamento.attrs["href"]

        (proc_window, and_window) = Page.nav_link_to_new_win(self.page.driver, link)

        input_and = self.page.wait_for_element(config.Proc_central.IN_AND)

        text = (
            config.Proc_central.AND_PRE + info + config.Proc_central.AND_POS
        )

        input_and.send_keys(text)

        self.page.wait_for_element_to_click(config.Proc_central.SV_AND).click()

        self.page.fechar()

        self.page.driver.switch_to.window(proc_window)

    def send_proc_to_sede(self, buttons):

        with self.page.wait_for_page_load():
            assert (
                self.page.get_title() == config.Proc_incluir.TITLE
            ), "Erro na função 'send_proc_to_sede"

            enviar = buttons[3]

            link = enviar.attrs["href"]

            (janela_processo, janela_enviar) = Page.nav_link_to_new_win(
                self.page.driver, link
            )

        with self.page.wait_for_page_load():
            assert (
                self.page.get_title() == config.Envio.TITLE
            ), "Erro ao clicar no botão 'Enviar Processo'"

            self.page.driver.execute_script(config.Envio.LUPA)

            # Guarda as janelas do navegador presentes
            windows = self.page.driver.window_handles

            janela_unidades = windows[-1]

            # Troca o foco do navegador
            self.page.driver.switch_to.window(janela_unidades)

        assert (
            self.page.get_title() == config.Envio.UNIDS
        ), "Erro ao clicar na lupa 'Selecionar Unidades'"

        unidade = self.page.wait_for_element(config.Envio.IN_SIGLA)

        unidade.clear()

        unidade.send_keys(config.Envio.SIGLA + Keys.RETURN)

        sede = self.page.wait_for_element(config.Envio.ID_SEDE)

        assert (
            sede.get_attribute("title") == config.Envio.SEDE
        ), "Erro ao selecionar a Unidade Protocolo.Sede para envio"

        sede.click()

        self.page.wait_for_element_to_click(config.Envio.B_TRSP).click()

        # Fecha a janela_unidades
        self.page.fechar()

        # Troca o foco do navegador
        self.page.driver.switch_to.window(janela_enviar)

        self.page.wait_for_element_to_click(config.Envio.OPEN).click()

        self.page.wait_for_element_to_click(config.Envio.RET_DIAS).click()

        prazo = self.page.wait_for_element(config.Envio.NUM_DIAS)

        prazo.clear()

        prazo.send_keys(config.Envio.PRAZO)

        self.page.wait_for_element_to_click(config.Envio.UTEIS).click()

        self.page.wait_for_element_to_click(config.Envio.ENVIAR).click()

        # fecha a janela_enviar
        self.page.fechar()

        self.page.driver.switch_to.window(janela_processo)

    def expedir_oficio(self, num_doc: str):

        info = self.info_oficio(num_doc)

        buttons = self._get_acoes()

        self.update_andamento(buttons, info)

        self.send_proc_to_sede(buttons)

    def go_to_postit(self):

        link = self._get_acoes().get("Anotações")

        if link is not None:

            main, new = self.page.nav_link_to_new_win(link)

        else:

            main, new = self.page.driver.current_window_handle, None

        return main, new

    def edita_postit(self, content="", prioridade=False):

        (main, new) = self.go_to_postit()

        if new is not None:

            postit = self.page.wait_for_element(config.Proc_central.IN_AND)

            postit.clear()

            sleep(1)

            if content != "":
                postit.send_keys(content)

            chk_prioridade = self.page.wait_for_element_to_click(
                config.Proc_central.CHK_PRIOR
            )

            if prioridade:

                if not chk_prioridade.is_selected():
                    chk_prioridade.click()

                    sleep(1)

            else:

                if chk_prioridade.is_selected():
                    chk_prioridade.click()

                    sleep(1)

            btn = self.page.wait_for_element_to_click(config.Proc_central.BT_POSTIT)

            btn.click()

            sleep(1)

            selfpage.fechar()

            self.page.driver.switch_to.window(main)

            if "anotacao" and "anotacao_link" in self.tags:
                self.tags["anotacao"] = content

                self.tags["anotacao_link"] = ""

    def go_to_marcador(self):

        link = self._get_acoes().get("Gerenciar Marcador")

        if link is not None:

            self.page.nav_link_to_new_win(link)

        else:

            raise ValueError("Problemas ao retornar o link para o Marcador")

    def go_to_acomp_especial(self):

        link = self._get_acoes().get("Acompanhamento Especial")

        if link is not None:

            main, new = self.page.nav_link_to_new_win(link)

            return main, new

        else:

            return (self.page.driver.current_window_handle, None)

    def excluir_acomp_especial(self):

        (main, new) = self.go_to_acomp_especial()

        if new is not None:

            if self.page.check_element_exists(config.Acompanhamento_Especial.EXCLUIR):

                try:

                    self.page._clicar(config.Acompanhamento_Especial.EXCLUIR)

                except TimeoutException:

                    print("Não foi possível excluir o Acompanhamento Especial")

                try:

                    alert = self.page.alert_is_present(timeout=5)

                    if alert:
                        alert.accept()

                except NoAlertPresentException:

                    print("Não houve pop-up de confirmação")

                selfpage.fechar()

                self.page.driver.switch_to.window(main)

                self.tags["Acompanhamento Especial"] = ""

    def edita_marcador(self, tipo="", content="", timeout=5):

        with self.page._navega_nova_janela():
            self.go_to_marcador()

            self.page._clicar(config.Marcador.SELECT_MARCADOR, timeout=10
            )

            self.page._clicar((By.LINK_TEXT, tipo), timeout=10
            )

            self.page._atualizar_elemento(
                config.Marcador.TXT_MARCADOR, content, timeout=10

            )

            self.page._clicar(config.Marcador.SALVAR, timeout=10
            )

            selfpage.fechar()

        self.page.driver.get(self.link)

    def incluir_interessados(self, dados, checagem=False, timeout=5):

        h = config.Selecionar_Contatos

        if not isinstance(dados, list):
            dados = [dados]

        if checagem:
            dados = [self.pesquisa_contato(dado) for dado in dados]
            dados = [d for d in dados if d is not None]

        # with self.page.wait_for_page_load():
        #    Sei.go_to_processo(self, self.numero)

        link = self._get_acoes().get("Consultar/Alterar Processo")

        if link is not None:

            self.go(link)

            with self.page._navega_nova_janela():

                self.page._click_button_new_win(h.LUPA)

                for dado in dados:

                    self.page._atualizar_elemento(
                        h.INPUT_PESQUISAR, dado + Keys.RETURN, timeout=10

                    )

                    self.page._clicar(h.BTN_PESQUISAR, timeout=10
                     / 2)

                    try:
                        self.page._clicar((By.ID, "chkInfraItem0"), timeout=10
                        )

                        self.page._clicar(h.B_TRSP, timeout=10
                         / 2)

                    except TimeoutException:
                        next

                # selfpage.fechar()
                self.page._clicar(h.BTN_FECHAR, timeout=10
                 / 2)

        self.page._clicar(h.SALVAR, timeout=10
        )

        self.go(self.link)

        self = super().go_to_processo(self.numero)

    def incluir_documento(self, tipo, timeout=5):

        if tipo not in config.Gerar_Doc.TIPOS:
            raise ValueError("Tipo de Documento inválido: {}".format(tipo))

        link = self._get_acoes().get("Incluir Documento")

        if link is not None:

            with self.page.wait_for_page_load():

                self.go(link)

            self.page._clicar((By.LINK_TEXT, tipo), timeout=10
            )

        else:

            raise ValueError(
                "Problema com o link de ações do processo: 'Incluir Documento'"
            )

    def incluir_oficio(
        self, tipo, dados=None, anexo=False, acesso="publico", hipotese=None, timeout=5
    ):

        # TODO:Inclui anexo

        helper = config.Gerar_Doc.oficio

        if tipo not in config.Gerar_Doc.TEXTOS_PADRAO:
            raise ValueError("Tipo de Ofício inválido: {}".format(tipo))

        self.incluir_documento("Ofício", timeout=10
         / 2)

        self.page._clicar(helper.get("id_txt_padrao"), timeout=10
         / 2)

        self.page._selecionar_por_texto(helper.get("id_modelos"), tipo, timeout=10
         / 2)

        # self.page._atualizar_elemento(helper.get('id_dest'), dados["CNPJ/CPF"] + Keys.TAB + Keys.RETURN )

        if acesso == "publico":

            self.page._clicar(helper.get("id_pub"), timeout=10
             / 2)

        elif acesso == "restrito":

            self.page._clicar(helper.get("id_restrito"), timeout=10
            )

            hip = Select(
                self.page.wait_for_element_to_click(
                    helper.get("id_hip_legal"), timeout=10

                )
            )

            if hipotese not in config.Gerar_Doc.HIPOTESES:
                raise ValueError("Hipótese Legal Inválida: ", hipotese)

            hip.select_by_visible_text(hipotese)

        else:

            raise ValueError(
                "Você provavelmente não vai querer mandar um Ofício Sigiloso"
            )

        with self.page._navega_nova_janela():

            self.page._click_button_new_win(helper.get("submit"), timeout=10
             / 2)

            if dados:

                self.editar_oficio(string_endereço(dados), timeout=10
                )

                selfpage.fechar()

        self.page.driver.get(self.link)

    def incluir_informe(self):
        pass

    def incluir_doc_externo(
        self,
        tipo,
        path,
        arvore="",
        formato="nato",
        acesso="publico",
        hipotese=None,
        timeout=5,
    ):

        helper = config.Gerar_Doc.doc_externo

        # if tipo not in helpers.Gerar_Doc.EXTERNO_TIPOS:

        #    raise ValueError("Tipo de Documento Externo Inválido: {}".format(tipo))

        self.incluir_documento("Externo", timeout=10
        )

        self.page._selecionar_por_texto(helper.get("id_tipo"), tipo, timeout=10
        )

        today = dt.datetime.today().strftime("%d%m%Y")

        self.page._atualizar_elemento(helper.get("id_data"), today, timeout=10
        )

        if arvore:
            self.page._atualizar_elemento(helper.get("id_txt_tree"), arvore, timeout=10
            )

        if formato.lower() == "nato":
            self.page._clicar(helper.get("id_nato"), timeout=10
            )

        if acesso == "publico":

            self.page._clicar(helper.get("id_pub"), timeout=10
            )

        elif acesso == "restrito":

            self.page._clicar(helper.get("id_restrito"), timeout=10
            )

            if hipotese not in config.Gerar_Doc.HIPOTESES:
                raise ValueError("Hipótese Legal Inválida: ", hipotese)

            self.page._selecionar_por_texto(
                helper.get("id_hip_legal"), hipotese, timeout=10

            )

        else:

            raise ValueError(
                "Você provavelmente não vai querer um documento Externo Sigiloso"
            )

        self.page._atualizar_elemento(helper.get("id_file_upload"), path, timeout=10
        )

        self.page._clicar(helper.get("submit"), timeout=2 * timeout)

        self.go(self.link)

    def editar_oficio(self, dados, timeout=5, existing=False):

        links = config.Sei_Login.Oficio

        self.page.wait_for_element_to_be_visible(links.editor, timeout=10
        )

        frames = self.page.driver.find_elements_by_tag_name("iframe")

        while len(frames) < 3:

            sleep(1)

            frames = self.page.driver.find_elements_by_tag_name("iframe")

        self.page.driver.switch_to.frame(frames[2])  # text frame

        # TODO: make this more general
        for tag, value in dados.items():
            xpath = r"//p[contains(text(), '{0}')]"

            element = self.page.wait_for_element((By.XPATH, xpath.format(tag)))

            action = ActionChains(self.page.driver)

            action.move_to_element_with_offset(element, 5, 5)

            action.click()

            action.perform()

            sleep(1)

            action.key_down(Keys.RETURN)

            action.perform()

            # action.key_down(Keys.DELETE)

            # action.perform()

            script = "arguments[0].innerHTML = `{0}`;".format(value)

            self.page.driver.execute_script(script, element)

            sleep(2)

        self.page.driver.switch_to.parent_frame()

        self.page._clicar(links.submit, timeout=10
        )

        # Necessary steps to save
        # self.page.driver.execute_script('arguments[0].removeAttribute("aria-disabled")', salvar)

        # self.page.driver.execute_script('arguments[0].class = "cke_button cke_button__save cke_button_off"', salvar)

        # salvar.click()

        # sleep(5)

        # selfpage.fechar()

    def concluir_processo(self):

        excluir = self._get_acoes().get("Concluir Processo").strip()

        assert (
            excluir is not None
        ), "A ação 'Concluir Processo não foi armazenada, verfique as ações do Processo"

        # Switch to central frame
        self.page.driver.switch_to_frame("ifrVisualizacao")

        try:

            self.page.driver.execute_script(excluir)

        except JavascriptException as e:

            print("One exception was catched: {}".format(repr(e)))

        alert = self.page.alert_is_present(timeout=5)

        if alert:
            alert.accept()

        self.page.driver.switch_to_default_content()


def exibir_bloco(sei, numero):
    if sei.get_title() != config.Blocos.TITLE:
        sei.go_to_blocos()

    try:
        sei.wait_for_element((By.LINK_TEXT, str(numero))).click()

    except:
        print(
            "O Bloco de Assinatura informado não existe ou está \
              concluído!"
        )


def armazena_bloco(sei, numero):
    if sei.get_title() != config.Bloco.TITLE + " " + str(numero):
        sei.exibir_bloco(numero)

    html_bloco = soup(sei.driver.page_source, "lxml")
    linhas = html_bloco.find_all("tr", class_=["infraTrClara", "infraTrEscura"])

    chaves = [
        "checkbox",
        "seq",
        "processo",
        "documento",
        "data",
        "tipo",
        "assinatura",
        "anotacoes",
        "acoes",
    ]

    lista_processos = []

    for linha in linhas:

        proc = {k: None for k in chaves}

        cols = [v for v in linha.contents if v != "\n"]

        assert len(chaves) == len(cols), "Verifique as linhas do bloco!"

        for k, v in zip(chaves, cols):
            proc[k] = v

        # proc["expedido"] = False

        lista_processos.append(proc)

    return lista_processos


def expedir_bloco(sei, numero):
    processos = sei.armazena_bloco(numero)

    for p in processos:

        if pode_expedir(p):
            proc = p["processo"].a.string

            num_doc = p["documento"].a.string

            link = sei.go(p["processo"].a.attrs["href"])

            (bloco_window, proc_window) = Page.nav_link_to_new_win(sei.driver, link)

            processo = Processo(sei.driver, proc_window)

            processo.expedir_oficio(num_doc)
