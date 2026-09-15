from abc import ABC
from classe_objeto_pagina.page_objects import PageElement
from Logger.Logger import Logger, LogLevel
from time import sleep

URL_API_COMUNICACAO = 'https://comunicaapi.pje.jus.br/api/v1/comunicacao'

# A API limita em 10000 resultados as pesquisas por numero de processo.
LIMITE_RESULTADOS_API = 10000


class PesquisarDjen(PageElement, ABC):
    log = None

    def pesquisar(self, numero_processo: str, parametros: dict, itens_por_pagina: int,
                  pausa_janela_requisicoes: int, timeout: int) -> dict:
        '''
        Dentro deste metodo deve estar SOMENTE a comunicacao com a API do DJEN (requisicao e paginacao).
        As regras de negocio e o tratamento de erro ficam em Tarefas.__tratar_pesquisar.

        :param numero_processo: numero do processo, somente digitos.
        :param parametros: criterios de pesquisa ja no formato da API.
        :param itens_por_pagina: 5 ou 100.
        :param pausa_janela_requisicoes: segundos de espera quando a janela de requisicoes chega ao fim.
        :param timeout: timeout de cada requisicao, em segundos.
        :return: dict -> {"status": codigo HTTP, "dados": {"publicacoes": [...], "limite_atingido": bool} ou mensagem de erro}
        '''
        self.log = Logger()
        publicacoes = []
        pagina = 1
        try:
            while True:
                resposta = self.session.get(
                    URL_API_COMUNICACAO,
                    params={
                        **parametros,
                        'numeroProcesso': numero_processo,
                        'pagina': pagina,
                        'itensPorPagina': itens_por_pagina,
                    },
                    timeout=timeout,
                )

                if resposta.status_code != 200:
                    return {"status": resposta.status_code, "dados": self.__mensagem_erro(resposta)}

                itens = resposta.json().get('items') or []
                publicacoes.extend(itens)

                self.__aguardar_janela_requisicoes(resposta, pausa_janela_requisicoes)

                limite_atingido = len(publicacoes) >= LIMITE_RESULTADOS_API
                if len(itens) < itens_por_pagina or limite_atingido:
                    break
                pagina += 1
        except Exception as e:
            self.log.criarLogPrint(f"Erro ocorreu na função 'pesquisar' da classe {self.__class__.__name__}. Exception: {e}", LogLevel.WARNING, classe=self.__class__.__name__)
            # Repassa o erro para quem chamou tratar a linha da planilha.
            raise
        else:
            self.log.criarLogPrint(f"A função 'pesquisar' da classe {self.__class__.__name__} executou com sucesso! Processo {numero_processo}: {len(publicacoes)} comunicação(ões) em {pagina} página(s).", LogLevel.INFO, classe=self.__class__.__name__)
            return {"status": 200, "dados": {"publicacoes": publicacoes, "limite_atingido": limite_atingido}}

    def __aguardar_janela_requisicoes(self, resposta, pausa: int) -> None:
        # Evita o erro 429: quando a janela de requisicoes do IP esta no fim, aguarda antes da proxima.
        restantes = resposta.headers.get('x-ratelimit-remaining')
        if restantes is not None and restantes.isdigit() and int(restantes) <= 1:
            self.log.criarLogPrint(f'Janela de requisições do DJEN no fim. Aguardando {pausa}s.', LogLevel.INFO, classe=self.__class__.__name__)
            sleep(pausa)

    @staticmethod
    def __mensagem_erro(resposta) -> str:
        try:
            return str(resposta.json().get('message') or resposta.text[:300])
        except ValueError:
            return resposta.text[:300]
