from classes_complementares.tratar_email import TratarEmail
from config import criar_contexto_execucao, ContextoExecucao
from realizar_tarefa import Tarefas
from openpyxl.cell.cell import ILLEGAL_CHARACTERS_RE
import datetime
import logging
import pandas as pd
import os
from Logger.Logger import Logger, LogLevel
import pytz


# Limite de caracteres de uma celula do Excel; o teor de algumas publicacoes passa disso.
LIMITE_CARACTERES_CELULA = 32767
SUFIXO_TEXTO_TRUNCADO = ' [TEXTO TRUNCADO]'


def get_data(contexto: ContextoExecucao) -> pd.DataFrame:
    df = pd.read_excel(contexto.arquivo_base, dtype=str)
    df = df.dropna(how='all').reset_index(drop=True)

    if contexto.coluna_processo not in df.columns:
        raise Exception(f'A coluna "{contexto.coluna_processo}" não foi encontrada em "{contexto.arquivo_base}". Colunas disponíveis: {list(df.columns)}.')

    return df

def post_data(df_processos: pd.DataFrame, df_publicacoes: pd.DataFrame, dir_resultado: str) -> str:
    '''
    Metodo que publica a lista de publicacoes encontradas e o resultado de cada processo da base.
    :return: str -> caminho da planilha gerada.
    '''

    data_atual_str = datetime.datetime.now(pytz.timezone('America/Sao_Paulo')).strftime('%d_%m_%Y_%H_%M_%S')
    arquivo_resultado = os.path.join(dir_resultado, f'publicacoes_djen_{data_atual_str}.xlsx')

    with pd.ExcelWriter(arquivo_resultado, engine='openpyxl') as writer:
        preparar_para_excel(df_publicacoes).to_excel(writer, sheet_name='publicacoes', index=False)
        preparar_para_excel(df_processos).to_excel(writer, sheet_name='processos', index=False)

    return arquivo_resultado

def preparar_para_excel(df: pd.DataFrame) -> pd.DataFrame:
    '''
    Metodo que remove caracteres que o Excel nao aceita e trunca textos acima do limite da celula.
    :return: pd.DataFrame
    '''

    def tratar_valor(valor):
        if isinstance(valor, str):
            valor = ILLEGAL_CHARACTERS_RE.sub('', valor)
            if len(valor) > LIMITE_CARACTERES_CELULA:
                valor = valor[:LIMITE_CARACTERES_CELULA - len(SUFIXO_TEXTO_TRUNCADO)] + SUFIXO_TEXTO_TRUNCADO
        return valor

    return df.map(tratar_valor)

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

def task() -> None:
    '''
    Método que realiza a configuração de execução do rôbo.
    :return: None
    '''

    dir_resultado = os.path.join(os.getcwd(), 'resultado')
    os.makedirs(dir_resultado, exist_ok=True)

    configurar_logging()

    log = Logger()

    # Le o .env e valida os criterios de pesquisa do config.py antes de iniciar.
    contexto = criar_contexto_execucao()

    cliente = contexto.cliente
    robo = contexto.robo

    ls_endereco_email_ti = contexto.lista_email_ti

    # Enviar o email informando que o robô foi iniciado
    assunto = f"INICIO - Robô {robo} - {cliente}"
    mensagem = f'Olá! O robô {robo} do cliente {cliente} foi iniciado.'
    log.criarLogPrint(mensagem, LogLevel.INFO, classe=__name__)
    TratarEmail().enviar_email(ls_endereco_email_ti, assunto, mensagem)

    try:
        # Metodo que obtém a base de execução
        df = get_data(contexto)
        # Metodo que realiza robo
        resultado = Tarefas(df, dir_resultado, contexto).realizar_tarefa()
        df_processos = resultado['dados']['processos']
        df_publicacoes = resultado['dados']['publicacoes']
        # Metodo que publica os resultados
        arquivo_resultado = post_data(df_processos, df_publicacoes, dir_resultado)
    except Exception as e:
        assunto = f"ERRO AO FINALIZAR A EXECUÇÃO - Robô {robo} - {cliente}"
        mensagem = f'Olá! O robô {robo} do cliente {cliente} finalizou a execução com erro. Detalhe do erro: {e}'
        # WARNING e nao ERROR: o Logger levanta excecao em ERROR/CRITICAL e o
        # e-mail de encerramento precisa ser enviado mesmo com falha.
        log.criarLogPrint(mensagem, LogLevel.WARNING, classe=__name__)
    else:
        qtd_erros = int((df_processos['RESULTADO'] == 'ERRO').sum())
        assunto = f"FIM - Robô {robo} - {cliente}"
        mensagem = (
            f'Olá! O robô {robo} do cliente {cliente} finalizou a execução.\n'
            f'Processos na base: {len(df_processos)} (com erro: {qtd_erros}).\n'
            f'Publicações encontradas: {len(df_publicacoes)}.\n'
            f'Resultado: {arquivo_resultado}'
        )
        log.criarLogPrint(mensagem, LogLevel.INFO, classe=__name__)

    TratarEmail().enviar_email(ls_endereco_email_ti, assunto, mensagem)


if __name__ == '__main__':
    task()
