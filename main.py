from classes_complementares.tratar_email import TratarEmail
from realizar_tarefa import Tarefas
from dotenv import load_dotenv
import datetime
import logging
import pandas as pd
import os
from Logger.Logger import Logger, LogLevel
import pytz


# Destinatarios padrao dos e-mails de inicio/fim. Podem ser sobrescritos pela
# variavel LISTA_EMAIL_TI do .env (enderecos separados por virgula).
LS_ENDERECO_EMAIL_TI_PADRAO = ['email1@example.com', 'email2@example.com']

ARQUIVO_BASE = 'teste.xlsx'


def get_data() -> pd.DataFrame:
    df = pd.read_excel(ARQUIVO_BASE, dtype=str)
    return df

def post_data(df:pd.DataFrame) -> None:
    df.to_excel(ARQUIVO_BASE, index=False)

def configurar_logging() -> str:
    '''
    Metodo que cria o diretorio de log e direciona o logging para o arquivo do dia.
    :return: str -> caminho do arquivo de log.
    '''

    data_atual = datetime.datetime.now(pytz.timezone('America/Sao_Paulo'))
    data_atual_str = data_atual.strftime('%d_%m_%Y')

    dir_loggin = os.path.join(os.getcwd(), 'dados_logging')
    os.makedirs(dir_loggin, exist_ok=True)

    arquivo_log = os.path.join(dir_loggin, f'Execution_{data_atual_str}.log')

    logging.basicConfig(
        filename=arquivo_log,
        format='%(asctime)s %(name)s %(levelname)s %(message)s',
        level=logging.INFO,
        filemode='a'
    )

    return arquivo_log

def obter_destinatarios() -> list:
    '''
    Metodo que le os destinatarios do .env e usa o padrao quando a variavel nao existe.
    :return: list -> lista de e-mails.
    '''

    destinatarios = [email.strip() for email in os.getenv('LISTA_EMAIL_TI', '').split(',') if email.strip()]

    return destinatarios or LS_ENDERECO_EMAIL_TI_PADRAO

def task() -> None:
    '''
    Método que realiza a configuração de execução do rôbo.
    :return: None
    '''

    dir_resultado = os.path.join(os.getcwd(), 'resultado')
    os.makedirs(dir_resultado, exist_ok=True)

    configurar_logging()

    log = Logger()

    dotenv_path = os.path.join('.env')
    load_dotenv(dotenv_path)

    cliente = os.getenv("NOME_CLIENTE")
    robo = os.getenv("NOME_ROBO")

    ls_endereco_email_ti = obter_destinatarios()

    # Enviar o email informando que o robô foi iniciado
    assunto = f"INICIO - Robô {robo} - {cliente}"
    mensagem = f'Olá! O robô {robo} do cliente {cliente} foi iniciado.'
    log.criarLogPrint(mensagem, LogLevel.INFO, classe=__name__)
    TratarEmail().enviar_email(ls_endereco_email_ti, assunto, mensagem)

    try:
        # Metodo que obtém a base de execução
        df = get_data()
        # Metodo que realiza robo
        df = Tarefas(df, dir_resultado).realizar_tarefa()
        # Metodo que publica os resultados
        post_data(df)
    except Exception as e:
        assunto = f"ERRO AO FINALIZAR A EXECUÇÃO - Robô {robo} - {cliente}"
        mensagem = f'Olá! O robô {robo} do cliente {cliente} finalizou a execução com erro. Detalhe do erro: {e}'
        # WARNING e nao ERROR: o Logger levanta excecao em ERROR/CRITICAL e o
        # e-mail de encerramento precisa ser enviado mesmo com falha.
        log.criarLogPrint(mensagem, LogLevel.WARNING, classe=__name__)
    else:
        assunto = f"FIM - Robô {robo} - {cliente}"
        mensagem = f'Olá! O robô {robo} do cliente {cliente} finalizou a execução.'
        log.criarLogPrint(mensagem, LogLevel.INFO, classe=__name__)

    TratarEmail().enviar_email(ls_endereco_email_ti, assunto, mensagem)


if __name__ == '__main__':
    task()
