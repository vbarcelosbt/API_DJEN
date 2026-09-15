from dataclasses import dataclass, field
from datetime import datetime, timedelta
from dotenv import load_dotenv
from pathlib import Path
import os

ENV_PATH = Path(".env")
load_dotenv(dotenv_path=ENV_PATH, override=True)


# ============================================================================
# PAINEL DE CONTROLE - edite este bloco para configurar a execucao do robo.
# ============================================================================

# Planilha com a lista de processos e a coluna que guarda o numero do processo.
# O numero pode vir com ou sem mascara (1003373-45.2025.8.13.0701 ou 10033734520258130701).
ARQUIVO_BASE = 'teste.xlsx'
COLUNA_PROCESSO = 'NUMERO_PROCESSO'

# Criterios de pesquisa aplicados a TODOS os processos da base.
# Deixe vazio ('', None ou []) o criterio que nao deve ser aplicado.
CRITERIOS_PESQUISA = {
    # Periodo de disponibilizacao no diario, no formato dd/mm/aaaa.
    'data_inicio': '',
    'data_fim': '',
    # Alternativa ao periodo fixo: pesquisa os ultimos N dias, ate hoje.
    # So e usado quando data_inicio estiver vazia.
    'dias_retroativos': None,

    'sigla_tribunal': '',   # ex.: 'TJMG', 'TRF1'
    'numero_oab': '',       # exige uf_oab
    'uf_oab': '',           # ex.: 'MG'
    'nome_advogado': '',
    'nome_parte': '',
    'meio': '',             # 'D' = Diario de Justica Eletronico, 'E' = Plataforma de Editais

    # Filtros aplicados pelo robo sobre o retorno (a API nao filtra por eles).
    'tipos_comunicacao': [],  # ex.: ['Intimação', 'Citação', 'Edital']
    'somente_ativas': True,   # descarta comunicacoes canceladas
}

# Controle de requisicoes. A API limita as consultas por IP e orienta aguardar
# 1 minuto depois de um erro 429; so aceita 5 ou 100 itens por pagina.
ITENS_POR_PAGINA = 100
MAX_TENTATIVAS = 3
ESPERA_LIMITE_REQUISICOES = 60  # segundos, apos erro 429
ESPERA_ERRO = 10                # segundos, apos outros erros da API
PAUSA_JANELA_REQUISICOES = 5    # segundos, quando a janela de requisicoes esta no fim
TIMEOUT_REQUISICAO = 60         # segundos

# Destinatarios padrao dos e-mails de inicio/fim. Podem ser sobrescritos pela
# variavel LISTA_EMAIL_TI do .env (enderecos separados por virgula).
LS_ENDERECO_EMAIL_TI_PADRAO = ['email1@example.com', 'email2@example.com']

# ============================================================================


@dataclass
class ContextoExecucao:
    robo: str = ''
    cliente: str = ''
    lista_email_ti: list[str] = field(default_factory=list)
    arquivo_base: str = ARQUIVO_BASE
    coluna_processo: str = COLUNA_PROCESSO
    parametros_api: dict = field(default_factory=dict)
    tipos_comunicacao: list[str] = field(default_factory=list)
    somente_ativas: bool = True
    itens_por_pagina: int = ITENS_POR_PAGINA
    max_tentativas: int = MAX_TENTATIVAS
    espera_limite_requisicoes: int = ESPERA_LIMITE_REQUISICOES
    espera_erro: int = ESPERA_ERRO
    pausa_janela_requisicoes: int = PAUSA_JANELA_REQUISICOES
    timeout_requisicao: int = TIMEOUT_REQUISICAO
    outros_dados: dict = field(default_factory=dict)


def converter_data(data: str, nome_criterio: str) -> datetime:
    '''
    Metodo que converte uma data dd/mm/aaaa do painel de controle.
    :return: datetime
    '''

    try:
        return datetime.strptime(str(data).strip(), '%d/%m/%Y')
    except ValueError:
        raise ValueError(f"O criterio '{nome_criterio}' deve estar no formato dd/mm/aaaa. Valor informado: '{data}'.")


def montar_parametros_api(criterios: dict) -> dict:
    '''
    Metodo que valida os criterios do painel de controle e os converte para os parametros da API do DJEN.
    A validacao precisa acontecer antes da execucao: a API responde erro 500 para data em formato invalido.
    :return: dict -> parametros prontos para a requisicao (sem numeroProcesso e paginacao).
    '''

    parametros = {}

    data_inicio = converter_data(criterios['data_inicio'], 'data_inicio') if criterios.get('data_inicio') else None
    data_fim = converter_data(criterios['data_fim'], 'data_fim') if criterios.get('data_fim') else None

    dias_retroativos = criterios.get('dias_retroativos')
    if data_inicio is None and dias_retroativos not in (None, ''):
        if int(dias_retroativos) < 0:
            raise ValueError("O criterio 'dias_retroativos' nao pode ser negativo.")
        hoje = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        data_inicio = hoje - timedelta(days=int(dias_retroativos))
        data_fim = data_fim or hoje

    if data_inicio and data_fim and data_inicio > data_fim:
        raise ValueError("O criterio 'data_inicio' nao pode ser posterior a 'data_fim'.")

    if data_inicio:
        parametros['dataDisponibilizacaoInicio'] = data_inicio.strftime('%Y-%m-%d')
    if data_fim:
        parametros['dataDisponibilizacaoFim'] = data_fim.strftime('%Y-%m-%d')

    numero_oab = str(criterios.get('numero_oab') or '').strip()
    uf_oab = str(criterios.get('uf_oab') or '').strip().upper()
    if numero_oab and not uf_oab:
        raise ValueError("O criterio 'numero_oab' exige que 'uf_oab' tambem seja preenchido.")

    meio = str(criterios.get('meio') or '').strip().upper()
    if meio and meio not in ('D', 'E'):
        raise ValueError("O criterio 'meio' aceita apenas 'D' (Diario Eletronico) ou 'E' (Plataforma de Editais).")

    campos_texto = {
        'siglaTribunal': str(criterios.get('sigla_tribunal') or '').strip().upper(),
        'numeroOab': numero_oab,
        'ufOab': uf_oab,
        'nomeAdvogado': str(criterios.get('nome_advogado') or '').strip(),
        'nomeParte': str(criterios.get('nome_parte') or '').strip(),
        'meio': meio,
    }
    parametros.update({chave: valor for chave, valor in campos_texto.items() if valor})

    return parametros


def obter_destinatarios() -> list:
    '''
    Metodo que le os destinatarios do .env e usa o padrao quando a variavel nao existe.
    :return: list -> lista de e-mails.
    '''

    destinatarios = [email.strip() for email in os.getenv('LISTA_EMAIL_TI', '').split(',') if email.strip()]

    return destinatarios or LS_ENDERECO_EMAIL_TI_PADRAO


def criar_contexto_execucao() -> ContextoExecucao:
    if ITENS_POR_PAGINA not in (5, 100):
        raise ValueError("ITENS_POR_PAGINA aceita apenas 5 ou 100 (limite da API do DJEN).")

    return ContextoExecucao(
        robo=os.getenv("NOME_ROBO", "").strip(),
        cliente=os.getenv("NOME_CLIENTE", "").strip(),
        lista_email_ti=obter_destinatarios(),
        arquivo_base=ARQUIVO_BASE,
        coluna_processo=COLUNA_PROCESSO,
        parametros_api=montar_parametros_api(CRITERIOS_PESQUISA),
        tipos_comunicacao=[tipo for tipo in CRITERIOS_PESQUISA.get('tipos_comunicacao') or [] if str(tipo).strip()],
        somente_ativas=bool(CRITERIOS_PESQUISA.get('somente_ativas')),
        itens_por_pagina=ITENS_POR_PAGINA,
        max_tentativas=MAX_TENTATIVAS,
        espera_limite_requisicoes=ESPERA_LIMITE_REQUISICOES,
        espera_erro=ESPERA_ERRO,
        pausa_janela_requisicoes=PAUSA_JANELA_REQUISICOES,
        timeout_requisicao=TIMEOUT_REQUISICAO,
    )
