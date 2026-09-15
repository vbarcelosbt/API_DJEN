<img width=100% src="https://capsule-render.vercel.app/api?type=waving&color=1EDDFA&height=180&section=header&text=&fontSize=30&fontColor=fff&animation=twinkling&fontAlignY=35"/> 

[![Typing SVG](https://readme-typing-svg.herokuapp.com/?color=1EDDFA&size=35&center=true&vCenter=true&width=1000&lines=A+P+I+++D+J+E+N;)](https://git.io/typing-svg)

## Repositórios Necessários

```bash
git clone https://github.com/bluetapesd/classes_complementares
git clone https://github.com/bluetapesd/classe_objeto_pagina
git submodule update --init   # Logger
```

## Descrição

- Lê uma planilha Excel com uma lista de processos, pesquisa cada um na API pública do
  **DJEN — Diário de Justiça Eletrônico Nacional** (`https://comunicaapi.pje.jus.br/api/v1/comunicacao`)
  com os critérios definidos no `config.py` e gera uma planilha com todas as publicações
  (comunicações) encontradas. Não usa navegador nem login: a consulta é pública.

- Estrutura (padrão do `template_bluetape`):

| Arquivo | Responsabilidade |
|---|---|
| `main.py` | `get_data()` lê a base de processos; `post_data()` grava a lista de publicações; e-mails de início/fim. |
| `config.py` | **Painel de controle**: planilha de entrada, critérios de pesquisa e controle de requisições. |
| `realizar_tarefa.py` | `Tarefas.realizar_tarefa()` com as regras de execução; `__tratar_pesquisar()` com os tratamentos da tarefa (validação do número, novas tentativas, filtros, registro do resultado). |
| `classe_tratar_pages/pesquisar.py` | `PesquisarDjen.pesquisar()`: somente a requisição à API e a paginação. |
| `classe_tratar_pages/todo.py` | `PageRealizar`, que agrega as tarefas da página. |

## Documentação:

- **Entrada** — planilha `ARQUIVO_BASE` (padrão `teste.xlsx`) com a coluna `COLUNA_PROCESSO`
  (padrão `NUMERO_PROCESSO`). O número pode vir com ou sem máscara. As demais colunas da planilha
  são copiadas para cada publicação encontrada (útil para levar pasta, cliente etc.).
- **Critérios de pesquisa** — bloco `CRITERIOS_PESQUISA` do `config.py`, aplicado a todos os processos:

| Critério | Parâmetro da API | Observação |
|---|---|---|
| `data_inicio` / `data_fim` | `dataDisponibilizacaoInicio` / `Fim` | Formato `dd/mm/aaaa`. |
| `dias_retroativos` | idem | Últimos N dias até hoje; só vale com `data_inicio` vazia. |
| `sigla_tribunal` | `siglaTribunal` | Ex.: `TJMG`, `TRF1`. |
| `numero_oab` + `uf_oab` | `numeroOab` + `ufOab` | Os dois juntos. |
| `nome_advogado` | `nomeAdvogado` | |
| `nome_parte` | `nomeParte` | |
| `meio` | `meio` | `D` = Diário Eletrônico, `E` = Plataforma de Editais. |
| `tipos_comunicacao` | — (filtro do robô) | Ex.: `['Intimação', 'Citação']`; ignora acento e maiúsculas. |
| `somente_ativas` | — (filtro do robô) | Descarta comunicações canceladas. |

- **Saída** — `resultado/publicacoes_djen_<data_hora>.xlsx`, com duas abas:
  - `publicacoes`: uma linha por publicação — colunas da base + `NUMERO PROCESSO DJEN`,
    `ID COMUNICACAO`, `DATA DISPONIBILIZACAO`, `TRIBUNAL`, `ORGAO`, `TIPO COMUNICACAO`,
    `TIPO DOCUMENTO`, `CLASSE`, `MEIO`, `NUMERO COMUNICACAO`, `DESTINATARIOS`, `ADVOGADOS`,
    `LINK`, `TEXTO` (teor convertido de HTML para texto) e `HASH`.
  - `processos`: a base com `RESULTADO` (`OK`/`ERRO`), `QTD PUBLICACOES`, `DATA RESULTADO` e `ERRO`.
    Pode ser usada como nova base para reprocessar só os erros: linhas com `RESULTADO = OK` são puladas.
- **Limites da API** (documentação oficial em `https://comunicaapi.pje.jus.br/swagger/index.html`):
  controle de requisições por IP (cabeçalhos `x-ratelimit-*`), orientação de aguardar 1 minuto após
  erro 429, `itensPorPagina` só aceita 5 ou 100, e no máximo 10.000 resultados por pesquisa.
  **Não** use vários IPs para contornar o limite: o DJEN considera uso abusivo.

## Clientes que utilizam o robô / Onde executa (Nome do computador - região - sistema):

* {CLIENTE}/{NOME COMPUTADOR} - {REGIÃO} - {SISTEMA OPERACIONAL}

## Como executar o robô em produção:

1. Clone os repositórios necessários na raiz e instale as dependências (`uv sync` ou `pip install -r requirements.txt`).
2. Copie `.env.example` para `.env` e preencha `NOME_CLIENTE`, `NOME_ROBO` e `LISTA_EMAIL_TI`.
3. Coloque a planilha de processos na raiz e ajuste `ARQUIVO_BASE`, `COLUNA_PROCESSO` e `CRITERIOS_PESQUISA` no `config.py`.
4. Execute `uv run main.py` (ou `python main.py`). O resultado fica em `resultado/` e o log em `dados_logging/`.

## Como executar o robô em teste:

- Use uma planilha com poucos processos e um período curto em `CRITERIOS_PESQUISA`. Para não enviar
  os e-mails de início/fim, chame direto `get_data`, `Tarefas(...).realizar_tarefa()` e `post_data`
  a partir de `criar_contexto_execucao()`.

## Possíveis Erros e Soluções

- **Erro 1**: `ValueError` ao iniciar (ex.: "deve estar no formato dd/mm/aaaa").
  - **Solução**: critério inválido no `config.py`; a mensagem indica qual. A validação existe porque a API responde erro 500 para data mal formatada.
- **Erro 2**: `A coluna "NUMERO_PROCESSO" não foi encontrada`.
  - **Solução**: ajustar `COLUNA_PROCESSO` no `config.py` para o nome exato da coluna da planilha.
- **Erro 3**: `ERRO = NUMERO DE PROCESSO INVALIDO.`
  - **Solução**: o número CNJ precisa ter 20 dígitos (com ou sem máscara).
- **Erro 4**: `ERRO = ERRO NA CONSULTA AO DJEN. HTTP 429` ou `HTTP 500`.
  - **Solução**: limite de requisições ou instabilidade do DJEN. O robô já repete (`MAX_TENTATIVAS`); reexecute usando a aba `processos` como base para consultar só as linhas com erro.
- **Erro 5**: `ERRO = CRITERIO DE PESQUISA RECUSADO PELO DJEN.`
  - **Solução**: erro 422 (negocial) — revisar a combinação de critérios no `config.py`.


<img width=100% src="https://capsule-render.vercel.app/api?type=waving&color=1EDDFA&height=120&section=footer"/>
