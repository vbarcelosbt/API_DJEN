import re
import unicodedata
import pandas as pd
import requests
from bs4 import BeautifulSoup
from time import sleep
from classe_tratar_pages.todo import PageRealizar
from classes_complementares.tratar_data_final_semana import TratarTempo
from config import ContextoExecucao
from Logger.Logger import Logger, LogLevel

# Colunas de controle gravadas na base de processos.
COLUNAS_CONTROLE = ['RESULTADO', 'QTD PUBLICACOES', 'DATA RESULTADO', 'ERRO']

# Colunas de cada publicacao encontrada, acrescentadas as colunas da base de processos.
COLUNAS_PUBLICACAO = [
    'NUMERO PROCESSO DJEN', 'ID COMUNICACAO', 'DATA DISPONIBILIZACAO', 'TRIBUNAL', 'ORGAO',
    'TIPO COMUNICACAO', 'TIPO DOCUMENTO', 'CLASSE', 'MEIO', 'NUMERO COMUNICACAO',
    'DESTINATARIOS', 'ADVOGADOS', 'LINK', 'TEXTO', 'HASH',
]

POLOS = {'A': 'Ativo', 'P': 'Passivo', 'T': 'Terceiro interessado', 'D': 'Outros destinatários'}


class Tarefas:
    page = None

    def __init__(self, df: pd.DataFrame, dir_resultado, contexto: ContextoExecucao):
        self.df = df
        self.dir_resultado = dir_resultado
        self.contexto = contexto
        self.log = Logger()
        self.publicacoes = []
        # Evita consultar de novo o mesmo processo quando ele se repete na base.
        self.cache_pesquisas = {}

    def realizar_tarefa(self) -> dict:
        # Aqui sao inseridas as tratativas relacionadas a execucao do robo e todas as suas tarefas deverao ser chamadas aqui separadamente.
        try:
            self.__preparar_base()

            # Linhas ja pesquisadas com sucesso (RESULTADO = OK) nao sao consultadas de novo.
            df_pendente = self.df[self.df['RESULTADO'] != 'OK']
            self.log.criarLogPrint(f'Identificou "{len(df_pendente)}" processos pendentes. Critérios de pesquisa: {self.contexto.parametros_api}', LogLevel.INFO, classe=self.__class__.__name__)
            if len(df_pendente) == 0:
                return self.__montar_resultado()

            self.__set_page()

            for index, row in df_pendente.iterrows():
                try:
                    self.__tratar_pesquisar(
                        index=index,
                        row=row
                    )
                except Exception as erro:
                    self.log.criarLogPrint(str(erro), LogLevel.WARNING, classe=self.__class__.__name__)
                else:
                    self.log.criarLogPrint(f'Tarefa {index} realizada', LogLevel.INFO, classe=self.__class__.__name__)

        except Exception as e:
            self.log.criarLogPrint(f'Erro ocorreu na função "realizar_tarefa" da classe "{self.__class__.__name__}". Exception: {e}', LogLevel.WARNING, classe=self.__class__.__name__)
        else:
            self.log.criarLogPrint('O método "realizar_tarefa" executou com sucesso.', LogLevel.INFO, classe=self.__class__.__name__)
        finally:
            if self.page is not None and self.page.session is not None:
                self.page.session.close()

        # O resultado precisa voltar para o main.py, que publica a lista de publicacoes.
        return self.__montar_resultado()

    def __preparar_base(self) -> None:
        # As colunas de controle sao do tipo object para aceitar texto e numero (o pandas le a base toda como str).
        for coluna in COLUNAS_CONTROLE:
            if coluna not in self.df.columns:
                self.df[coluna] = None
            self.df[coluna] = self.df[coluna].astype(object)

    def __set_page(self) -> None:
        try:
            session = requests.Session()
            session.headers.update({'Accept': 'application/json'})
            self.page = PageRealizar(session=session, contexto_execucao=self.contexto)
        except Exception as e_session:
            self.log.criarLogPrint(f'Erro ocorreu na classe __set_page. Detalhe: {e_session}.', LogLevel.WARNING, classe=self.__class__.__name__)
            raise

    def __tratar_pesquisar(self, index, row: pd.Series) -> None:
        # Aqui sao inseridas as tratativas relacionadas a tarefa pesquisar. Ex: validacao do processo, novas tentativas, filtros e registro do resultado.
        try:
            valor_processo = row[self.contexto.coluna_processo] if pd.notna(row[self.contexto.coluna_processo]) else ''
            numero_processo = re.sub(r'\D', '', str(valor_processo))

            if len(numero_processo) != 20:
                self.df.loc[index, 'ERRO'] = 'NUMERO DE PROCESSO INVALIDO.'
                raise Exception(f'Número de processo inválido: "{valor_processo}". O número CNJ deve ter 20 dígitos.')

            if numero_processo not in self.cache_pesquisas:
                dados = self.__executar_pesquisa(index, numero_processo)
                self.cache_pesquisas[numero_processo] = {
                    'publicacoes': self.__filtrar_publicacoes(dados['publicacoes']),
                    'limite_atingido': dados['limite_atingido'],
                }
            pesquisa = self.cache_pesquisas[numero_processo]

            dados_base = self.__dados_base(row)
            for publicacao in pesquisa['publicacoes']:
                self.publicacoes.append({**dados_base, **self.__formatar_publicacao(publicacao)})

            self.df.loc[index, 'RESULTADO'] = 'OK'
            self.df.loc[index, 'QTD PUBLICACOES'] = len(pesquisa['publicacoes'])
            self.df.loc[index, 'ERRO'] = 'LIMITE DE 10000 RESULTADOS DA API ATINGIDO. LISTA INCOMPLETA.' if pesquisa['limite_atingido'] else None
        except Exception as e:
            self.df.loc[index, 'RESULTADO'] = 'ERRO'
            if pd.isna(self.df.loc[index, 'ERRO']):
                self.df.loc[index, 'ERRO'] = 'ERRO'
            self.log.criarLogPrint(f'Erro ocorreu na classe __tratar_pesquisar. Detalhe: {e}.', LogLevel.WARNING, classe=self.__class__.__name__)
            raise
        else:
            self.log.criarLogPrint(f'Processo {numero_processo}: {len(pesquisa["publicacoes"])} publicação(ões) encontrada(s).', LogLevel.INFO, classe=self.__class__.__name__)
        finally:
            self.df.loc[index, 'DATA RESULTADO'] = TratarTempo().tempo_atual().strftime('%d/%m/%Y %H:%M:%S')

    def __executar_pesquisa(self, index, numero_processo: str) -> dict:
        # Regras de erro da API: 429 aguarda o tempo orientado pelo DJEN, 422 nao adianta repetir, demais erros tentam de novo.
        detalhe = ''
        for tentativa in range(1, self.contexto.max_tentativas + 1):
            try:
                # Dentro do metodo pesquisar deve estar somente a comunicacao com a API. Os tratamentos ficam aqui.
                resultado = self.page.pesquisar_djen.pesquisar(
                    numero_processo=numero_processo,
                    parametros=self.contexto.parametros_api,
                    itens_por_pagina=self.contexto.itens_por_pagina,
                    pausa_janela_requisicoes=self.contexto.pausa_janela_requisicoes,
                    timeout=self.contexto.timeout_requisicao,
                )
            except Exception as e:
                resultado = {"status": None, "dados": str(e)}

            status = resultado['status']
            if status == 200:
                return resultado['dados']

            detalhe = f'HTTP {status}: {resultado["dados"]}' if status else str(resultado['dados'])

            if status == 422:
                self.df.loc[index, 'ERRO'] = f'CRITERIO DE PESQUISA RECUSADO PELO DJEN. {detalhe}'
                raise Exception(f'O DJEN recusou os critérios de pesquisa do processo {numero_processo}. {detalhe}')

            self.log.criarLogPrint(f'Tentativa {tentativa}/{self.contexto.max_tentativas} falhou para o processo {numero_processo}. {detalhe}', LogLevel.WARNING, classe=self.__class__.__name__)

            # Depois de um 429 a espera vale mesmo na ultima tentativa, para o proximo processo nao repetir o erro.
            if status == 429:
                sleep(self.contexto.espera_limite_requisicoes)
            elif tentativa < self.contexto.max_tentativas:
                sleep(self.contexto.espera_erro)

        self.df.loc[index, 'ERRO'] = f'ERRO NA CONSULTA AO DJEN. {detalhe}'
        raise Exception(f'Não foi possível consultar o processo {numero_processo} após {self.contexto.max_tentativas} tentativas. {detalhe}')

    def __filtrar_publicacoes(self, publicacoes: list) -> list:
        # Filtros do painel de controle que a API nao oferece, e remocao de comunicacoes repetidas entre paginas.
        tipos = {self.__normalizar(tipo) for tipo in self.contexto.tipos_comunicacao}
        unicas = {}
        for publicacao in publicacoes:
            if self.contexto.somente_ativas and (publicacao.get('ativo') is False or publicacao.get('data_cancelamento')):
                continue
            if tipos and self.__normalizar(publicacao.get('tipoComunicacao')) not in tipos:
                continue
            unicas.setdefault(publicacao.get('id') or publicacao.get('hash') or id(publicacao), publicacao)

        return sorted(unicas.values(), key=lambda p: p.get('data_disponibilizacao') or '', reverse=True)

    def __formatar_publicacao(self, publicacao: dict) -> dict:
        destinatarios = '; '.join(
            f"{d.get('nome')} ({POLOS.get(d.get('polo'), d.get('polo'))})"
            for d in publicacao.get('destinatarios') or []
        )
        advogados = '; '.join(
            f"{a.get('nome')} (OAB {a.get('numero_oab')}/{a.get('uf_oab')})"
            for item in publicacao.get('destinatarioadvogados') or []
            if (a := item.get('advogado'))
        )

        return {
            'NUMERO PROCESSO DJEN': publicacao.get('numeroprocessocommascara') or publicacao.get('numero_processo'),
            'ID COMUNICACAO': publicacao.get('id'),
            'DATA DISPONIBILIZACAO': publicacao.get('datadisponibilizacao') or publicacao.get('data_disponibilizacao'),
            'TRIBUNAL': publicacao.get('siglaTribunal'),
            'ORGAO': publicacao.get('nomeOrgao'),
            'TIPO COMUNICACAO': publicacao.get('tipoComunicacao'),
            'TIPO DOCUMENTO': publicacao.get('tipoDocumento'),
            'CLASSE': publicacao.get('nomeClasse'),
            'MEIO': publicacao.get('meiocompleto') or publicacao.get('meio'),
            'NUMERO COMUNICACAO': publicacao.get('numeroComunicacao'),
            'DESTINATARIOS': destinatarios,
            'ADVOGADOS': advogados,
            'LINK': publicacao.get('link'),
            'TEXTO': self.__html_para_texto(publicacao.get('texto')),
            'HASH': publicacao.get('hash'),
        }

    def __dados_base(self, row: pd.Series) -> dict:
        return {coluna: row[coluna] for coluna in self.__colunas_base()}

    def __colunas_base(self) -> list:
        return [coluna for coluna in self.df.columns if coluna not in COLUNAS_CONTROLE and coluna not in COLUNAS_PUBLICACAO]

    def __montar_resultado(self) -> dict:
        df_publicacoes = pd.DataFrame(self.publicacoes, columns=self.__colunas_base() + COLUNAS_PUBLICACAO)
        return {"status": 200, "dados": {"processos": self.df, "publicacoes": df_publicacoes}}

    @staticmethod
    def __html_para_texto(html) -> str:
        # O teor da comunicacao vem em HTML; mantem uma linha por paragrafo.
        if not html:
            return ''
        texto = BeautifulSoup(html, 'html.parser').get_text(separator='\n')
        linhas = [re.sub(r'\s+', ' ', linha).strip() for linha in texto.replace('\xa0', ' ').split('\n')]
        return '\n'.join(linha for linha in linhas if linha)

    @staticmethod
    def __normalizar(texto) -> str:
        texto = unicodedata.normalize('NFKD', str(texto or ''))
        return ''.join(c for c in texto if not unicodedata.combining(c)).casefold().strip()
