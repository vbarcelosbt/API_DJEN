from selenium.webdriver.common.by import By
from abc import ABC
from classe_objeto_pagina.page_objects import PageElement
from Logger.Logger import Logger, LogLevel
from time import sleep

class Realizar(PageElement, ABC):
    log = None

    def realizar(self):
        '''
        Dentro deste metodo deve estar SOMENTE a interacao com a pagina via selenium.
        As regras de negocio e o tratamento de erro ficam em Tarefas.__tratar_novatarefa.
        '''
        self.log = Logger()
        try:
            # Implemente aqui a tarefa do robo.
            pass
        except Exception as e:
            self.log.criarLogPrint(f"Erro ocorreu na função 'realizar' da classe {self.__class__.__name__}. Exception: {e}", LogLevel.WARNING, classe=self.__class__.__name__)
            # Repassa o erro para quem chamou tratar a linha da planilha.
            raise
        else:
            self.log.criarLogPrint(f"A função 'realizar' da classe {self.__class__.__name__} executou com sucesso!", LogLevel.INFO, classe=self.__class__.__name__)
