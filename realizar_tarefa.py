import pandas as pd
from classe_tratar_pages.todo import PageRealizar
from classes_complementares.tratar_data_final_semana import TratarTempo
from selenium import webdriver
import os
from Logger.Logger import Logger, LogLevel

# Perfil do Chrome usado quando a pasta existir na maquina. Pode ser trocado
# pela variavel CHROME_PROFILE_DIR do .env, sem alterar o codigo.
CHROME_PROFILE_PADRAO = 'C:/Users/Administrator/AppData/Local/Google/Chrome/User Data/Profile 1'


class Tarefas:
    page = None
    download_dir = ''

    def __init__(self, df:pd.DataFrame, dir_resultado):
        self.df = df
        self.dir_resultado = dir_resultado
        self.log = Logger()

    def realizar_tarefa(self) -> pd.DataFrame:
        # Aqui sao inseridas as tratativas relacionadas a execucao do robo e todas as suas tarefas deverao ser chamadas aqui separadamente.
        try:
            # Filtro para identificar apenas informaçoes utilizadas no metodo Acessar
            df_pendente = self.df[self.df["RESULTADO"] == 'x']          # se o dataframe estiver vazio o robo finaliza a execução.
            # Indica que nâo tem nenhum processo pendente para protocolar
            self.log.criarLogPrint(f'Identificou "{len(df_pendente)}" tarefas pendentes.', LogLevel.INFO, classe=self.__class__.__name__)
            if len(df_pendente) == 0:
                return self.df

            for index, row in df_pendente.iterrows():
                try:
                    self.__tratar_acessar(
                        index=index,
                        row=row
                    )

                    self.__tratar_novatarefa(
                        index=index,
                        row=row
                    )
                except Exception as erro:
                    self.log.criarLogPrint(str(erro), LogLevel.WARNING, classe=self.__class__.__name__)
                else:
                    self.log.criarLogPrint(f'Tarefa {index} realizada', LogLevel.INFO, classe=self.__class__.__name__)

                try:
                    self.page.webdriver.quit()
                except Exception:
                    pass

        except Exception as e:
            self.log.criarLogPrint(f'Erro ocorreu na função "realizar_tarefa" da classe "{self.__class__.__name__}". Exception: {e}', LogLevel.WARNING, classe=self.__class__.__name__)
        else:
            self.log.criarLogPrint('O método "realizar_tarefa" executou com sucesso.', LogLevel.INFO, classe=self.__class__.__name__)

        # O DataFrame precisa voltar para o main.py, que grava o resultado na planilha.
        return self.df

    def chrome(self, download_dir):
        try:
            # Configurando o webdrive do chrome.
            options = webdriver.ChromeOptions()
            #options.add_argument("--headless")
            if os.path.isfile('./plugin.zip'):
                options.add_extension('./plugin.zip')
            options.add_argument('--disable-blink-features=AutomationControlled')
            #options.add_argument("--disable-extensions")
            options.add_argument("--start-maximized")
            options.add_argument("--disable-gpu")
            options.add_argument('ignore-certificate-errors')
            options.add_argument('--ignore-ssl-errors=yes')
            options.add_argument('--ignore-certificate-errors')
            arquivo_profile = os.getenv('CHROME_PROFILE_DIR', CHROME_PROFILE_PADRAO)
            if os.path.isdir(arquivo_profile):
                options.add_argument(f"--user-data-dir={arquivo_profile}")
            options.add_experimental_option("excludeSwitches", ["enable-automation"])

            options.add_experimental_option('useAutomationExtension', False)
            arquivo_pluguin = '.\\anticaptcha-plugin_v0.63.crx'
            if os.path.isfile(arquivo_pluguin):
                options.add_extension(os.path.abspath(arquivo_pluguin))
            arquivo_ext_esaj = '.\\WebSigner-Extension-ESAJ.crx'
            if os.path.isfile(arquivo_ext_esaj):
                options.add_extension(os.path.abspath(arquivo_ext_esaj))

            if download_dir != '':
                download_dir = download_dir.replace('/','\\')
                options.add_experimental_option("prefs", {
                    "download": {"prompt_for_download": False}, "plugins.always_open_pdf_externally": True,
                    "plugins.plugins_list": [{"enabled": False, "name": "Chrome PDF Viewer"}],
                    # Disable Chrome's PDF Viewer
                    "download.default_directory": download_dir, "download.extensions_to_open": "applications/pdf"})
            webdrive = webdriver.Chrome(options=options)
            webdrive.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        except Exception as e:
            raise Exception(f"Erro ocorreu na função 'chrome' da classe '{self.__class__.__name__}'. Exception: {e}")
        else:
            self.log.criarLogPrint("webdriver iniciado com sucesso!", LogLevel.INFO, classe=self.__class__.__name__)
            return webdrive

    def __set_page(self, index, row):
        try:
            instancia_webdriver = self.chrome(
                download_dir=self.download_dir
            )
            self.page = PageRealizar(instancia_webdriver, row['URL'])
            self.page.open()
        except Exception as e_web_driver:
            self.df.loc[index, 'ERRO'] = 'ERRO AO ACESSAR O TRIBUNAL.'
            self.log.criarLogPrint(f'Erro ocorreu na classe __set_page. Detalhe: {e_web_driver}.', LogLevel.WARNING, classe=self.__class__.__name__)
            raise

    def __tratar_acessar(self, index, row:dict) -> None:
        try:
            # Aqui sao inseridas as tratativas relacionadas a tarefa acessar. Ex: regras em caso de erro, registro no banco de dados;
            # Instancia o webdriver e executa o get na url indicada.

            self.log.criarLogPrint(f"\nIniciando acesso: {row}", LogLevel.INFO, classe=self.__class__.__name__)

            self.__set_page(index, row)

            try:
                # Instancia o metodo acessar da classe Acessar_{sistema}_{tribunal} - Dentro do método acessar deve estar somente a execução da tarefa via selenium. Os tratamentos relacionados a tarefa devem estar no tratar_acessar.

                self.page.__getattribute__(f"acessar").acessar(
                    login=row['login'],
                    senha=row['senha']
                )
            except AttributeError as e_acessar:
                self.df.loc[index, 'ERRO'] = 'TRIBUNAL NÃO IDENTIFICADO.'
                raise Exception(f'Erro de atributo. Detalhe: {e_acessar}. ')
            except Exception as e_acessar:
                self.df.loc[index, 'ERRO'] = 'ERRO AO ACESSAR O TRIBUNAL.'
                raise Exception(e_acessar)
        except Exception as e:
            self.df.loc[index, 'DATA RESULTADO'] = TratarTempo().tempo_atual().strftime('%d/%m/%Y %H:%M:%S')
            self.log.criarLogPrint(f'Erro ocorreu na classe __tratar_acessar. Detalhe: {e}.', LogLevel.WARNING, classe=self.__class__.__name__)
            # Sem o acesso nao ha o que realizar: interrompe esta linha da planilha.
            raise
        else:
            self.log.criarLogPrint('Acessou a página!', LogLevel.INFO, classe=self.__class__.__name__)

    def __tratar_novatarefa(self, index, row: dict) -> None:
        # Aqui sao inseridas as tratativas relacionadas a nova tarefa. Ex: regras em caso de erro, registro no banco de dados;
        try:


            # Instancia o metodo realizar da classe Realizar_{sistema}_{tribunal} - Dentro do método acessar deve estar somente a execução da tarefa via selenium. Os tratamentos relacionados a tarefa devem estar no tratar_novatarefa.
            self.page.__getattribute__(f"realizar").realizar()

            self.df.loc[index, 'RESULTADO'] = 'OK'
            self.df.loc[index, 'DATA RESULTADO'] = TratarTempo().tempo_atual().strftime('%d/%m/%Y %H:%M:%S')
        except AttributeError as e:
            self.df.loc[index, 'ERRO'] = 'TRIBUNAL NÃO IDENTIFICADO.'
            self.df.loc[index, 'DATA RESULTADO'] = TratarTempo().tempo_atual().strftime('%d/%m/%Y %H:%M:%S')
            self.log.criarLogPrint(f'Erro de atributo. Detalhe: {e}', LogLevel.WARNING, classe=self.__class__.__name__)
        except Exception as e:
            self.df.loc[index, 'ERRO'] = 'ERRO'
            self.df.loc[index, 'DATA RESULTADO'] = TratarTempo().tempo_atual().strftime('%d/%m/%Y %H:%M:%S')
            self.log.criarLogPrint(f'Exceção. Detalhe: {e}', LogLevel.WARNING, classe=self.__class__.__name__)
        else:
            self.log.criarLogPrint('Realizou a tarefa com sucesso', LogLevel.INFO, classe=self.__class__.__name__)
