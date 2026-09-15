# Template Bluetape (template_bluetape)

Repositório-modelo a partir do qual nascem os robôs de RPA da organização
`bluetapesd`. Não é um robô: é o **esqueleto** que se copia — o padrão Page
Object, a planilha de controle, os e-mails de início/fim e o `README.md` de
preenchimento obrigatório que aparece (às vezes ainda em branco) em dezenas de
repositórios da org.

> **Por que este arquivo não é o `README.md`.** O `README.md` deste repositório
> **é o produto**: ele é copiado para cada robô novo e precisa continuar sendo o
> modelo em branco. Em 21/08/2025 alguém acrescentou ali a documentação do `uv`
> e, seis dias depois, ela foi removida (`9ed68d7`, "Removido documentação do
> UV") — justamente para não ser herdada pelos robôs. Esta documentação fica,
> portanto, em arquivo separado. **Nos repositórios derivados, apague este
> arquivo.**
>
> Documento gerado a partir da leitura do código-fonte, do histórico do
> repositório (jan/2024 a ago/2025) e dos repositórios que descendem dele. Não
> substitui conhecimento operacional que só existe na cabeça do time — em caso
> de dúvida, valide antes de mudar o template, porque qualquer erro aqui se
> multiplica por todos os robôs criados depois.
>
> **Esta branch (`claude_sugestao`) já traz as correções sugeridas** — o
> template volta a executar, o `.gitignore` protege segredos e artefatos, e a
> planilha de exemplo bate com o que o código lê. O antes/depois está em
> [Correções aplicadas nesta branch](#correções-aplicadas-nesta-branch).

## Sumário

- [O que o template entrega](#o-que-o-template-entrega)
- [Estrutura do repositório](#estrutura-do-repositório)
- [Arquitetura do esqueleto](#arquitetura-do-esqueleto)
- [Como criar um robô a partir daqui](#como-criar-um-robô-a-partir-daqui)
- [O contrato da planilha de controle](#o-contrato-da-planilha-de-controle)
- [Dependências externas](#dependências-externas)
- [Gerenciamento de dependências: uv, pip e o que usar](#gerenciamento-de-dependências-uv-pip-e-o-que-usar)
- [Correções aplicadas nesta branch](#correções-aplicadas-nesta-branch)
- [Como registrar log](#como-registrar-log)
- [O que os robôs herdam daqui](#o-que-os-robôs-herdam-daqui)
- [Histórico](#histórico)
- [Débitos técnicos e riscos conhecidos](#débitos-técnicos-e-riscos-conhecidos)

## O que o template entrega

Um robô recém-criado já vem com:

- **Orquestração pronta** (`main.py`): criação das pastas `resultado/` e
  `dados_logging/`, leitura do `.env`, e-mail de início, `try/except/else` em
  volta da execução e e-mail de fim ou de erro.
- **Laço de tarefas** (`realizar_tarefa.py`): lê a planilha de controle, filtra
  as linhas pendentes, abre o Chrome com uma configuração anti-detecção já
  ajustada, executa duas etapas por linha (`acessar` e `realizar`) e grava o
  resultado de volta na planilha.
- **Page Objects vazios** (`classe_tratar_pages/`): as classes `Acessar` e
  `Realizar` com o corpo em `pass`, prontas para receber a automação do site.
- **Modelo de README** com as seções que a organização espera ver preenchidas.
- **Planilha de exemplo** (`teste.xlsx`) e um **PDF de exemplo** de documentação
  operacional.

## Estrutura do repositório

| Caminho | Descrição |
|---|---|
| `main.py` | Entry point: diretórios, `.env`, e-mails de início/fim, chamada a `Tarefas`. |
| `realizar_tarefa.py` | Classe `Tarefas`: filtro da planilha, laço por linha, `chrome()`, `__tratar_acessar`, `__tratar_novatarefa`. |
| `classe_tratar_pages/acessar.py` | Page Object `Acessar` — corpo `pass`, a ser implementado. |
| `classe_tratar_pages/realizar.py` | Page Object `Realizar` — corpo `pass`, a ser implementado. |
| `classe_tratar_pages/todo.py` | `PageRealizar(Page)` agregando `acessar` e `realizar`. |
| `README.md` | **O modelo** a ser preenchido no robô novo (ver nota no topo). |
| `teste.xlsx` | Planilha de controle de exemplo, com todas as colunas que o código lê e escreve: `URL`, `RESULTADO`, `login`, `senha`, `DATA RESULTADO` e `ERRO`. |
| `.env.example` | Modelo do `.env`, para ser copiado e preenchido. O `.env` em si é ignorado pelo Git. |
| `.gitignore` | Ignora IDEs, ambientes virtuais, `__pycache__`, `.env`, as bibliotecas internas clonadas na raiz e os artefatos de execução (`dados_logging/`, `resultado/`, `downloads/`, `*.log`, `*.xlsx` — com exceção do `teste.xlsx`). |
| `.gitmodules` | Declara o submódulo `Logger`, para que `git submodule update --init` funcione. |
| `Logger` | **Gitlink** (modo `160000`) fixado no commit `e080dbe` (25/03/2024). |
| `pyproject.toml` + `uv.lock` | Projeto `uv` (ago/2025), Python `>=3.10`, 9 dependências. |
| `requirements.txt` | Mesmas dependências do `pyproject.toml`, para quem usa `pip`. |
| `comandos_importantes.txt` | Comandos de `venv` + `pip` (anteriores ao `uv`). |
| `robo_lanca_andamentos.pdf` | Exemplo de documentação operacional (992 KB), referenciado pelo README. |

## Arquitetura do esqueleto

```
main.py
  ├─ get_data()        → lê teste.xlsx (pandas, tudo como str)
  ├─ Tarefas(df, dir_resultado).realizar_tarefa()      [realizar_tarefa.py]
  │     ├─ filtra df["RESULTADO"] == 'x'   (nada pendente → encerra)
  │     └─ para cada linha:
  │           ├─ __tratar_acessar()
  │           │     ├─ chrome()            → webdriver configurado
  │           │     ├─ PageRealizar(driver, row['URL']).open()
  │           │     └─ page.acessar.acessar(login=…, senha=…)
  │           ├─ __tratar_novatarefa()
  │           │     └─ page.realizar.realizar()
  │           │     → grava RESULTADO='OK' e DATA RESULTADO
  │           └─ page.webdriver.quit()
  ├─ post_data()       → regrava teste.xlsx
  └─ TratarEmail().enviar_email(...)   (início e fim/erro)
```

A divisão é sempre a mesma nos robôs da organização: **o que é interação com o
site** fica nas page objects (`acessar.py`, `realizar.py`), e **o que é regra de
negócio, tratamento de erro e registro de resultado** fica nos métodos
`__tratar_*` de `Tarefas`. Os próprios comentários do template dizem isso.

O `chrome()` já vem com a configuração que os robôs da casa costumam precisar:
`--disable-blink-features=AutomationControlled`, remoção do flag `webdriver` via
JavaScript, uso de um profile do Chrome quando ele existir, carregamento
opcional das extensões `anticaptcha-plugin_v0.63.crx`, `plugin.zip` e
`WebSigner-Extension-ESAJ.crx`, e preferências de download (PDF sem visualizador
interno). Todos os arquivos de extensão são **opcionais** — o código só os
adiciona se existirem na pasta.

## Como criar um robô a partir daqui

1. **Crie o repositório** a partir deste template (ou copie os arquivos).
2. **Preencha o `README.md`**: descrição, PDF de documentação, cliente/máquina
   onde executa, como rodar em produção e em teste, erros conhecidos.
3. **Apague este `DOCUMENTACAO.md`** e o `robo_lanca_andamentos.pdf` de exemplo.
4. **Copie o `.env.example` para `.env`** e preencha `NOME_CLIENTE` e
   `NOME_ROBO` (o `.env` já está no `.gitignore`).
5. **Defina os destinatários** dos e-mails: pela variável `LISTA_EMAIL_TI` do
   `.env` ou trocando `LS_ENDERECO_EMAIL_TI_PADRAO` em `main.py`, hoje
   `email1@example.com` / `email2@example.com`.
6. **Monte a planilha de controle** com as colunas que o robô vai usar (ver
   [contrato](#o-contrato-da-planilha-de-controle)).
7. **Implemente `Acessar.acessar(login, senha)` e `Realizar.realizar()`**, hoje
   com o corpo vazio.
8. **Clone as dependências externas** na raiz (ver seção seguinte) e instale os
   pacotes com `uv sync` ou `pip install -r requirements.txt`.

## O contrato da planilha de controle

O template lê e escreve a mesma planilha (`teste.xlsx`), que funciona como fila
e como registro de resultado:

| Coluna | Quem usa | Observação |
|---|---|---|
| `RESULTADO` | filtro de entrada (`== 'x'`) e saída (`'OK'`) | Só linhas marcadas com **`x`** minúsculo entram na execução. |
| `URL` | `PageRealizar(driver, row['URL'])` | Endereço do sistema a acessar. |
| `login`, `senha` | `page.acessar.acessar(login=…, senha=…)` | Credenciais do sistema, por linha. |
| `DATA RESULTADO` | escrita ao fim de cada linha | Carimbo de hora do desfecho. |
| `ERRO` | escrita nos caminhos de falha | Valores usados: `ERRO AO ACESSAR O TRIBUNAL.`, `TRIBUNAL NÃO IDENTIFICADO.`, `ERRO`. |

A planilha de exemplo já traz as seis colunas, então o robô roda de ponta a
ponta desde o primeiro teste. Acrescente as colunas específicas do seu robô
conforme a necessidade.

## Dependências externas

Três repositórios internos, citados no próprio `README.md` do template:

```bash
git clone https://github.com/bluetapesd/classes_complementares
git clone https://github.com/bluetapesd/classe_objeto_pagina
git clone https://github.com/bluetapesd/Logger
```

| Repositório | O que o template usa |
|---|---|
| `classes_complementares` | `TratarEmail` (e-mails de início/fim) e `TratarTempo` (`tempo_atual()`). |
| `classe_objeto_pagina` | `Page` e `PageElement`, o núcleo do framework de Page Objects. |
| `Logger` | A classe `Logger` (`criarLogPrint`). |

`Logger` está registrado como **gitlink** (modo `160000`) apontando para o commit
`e080dbe`, de **25/03/2024**. Com o `.gitmodules` desta branch,
`git submodule update --init` já resolve a pasta sozinho — só note que o commit
fixado está atrás do estado atual daquele repositório; atualize com
`git submodule update --remote Logger` se quiser a versão mais nova.

`classes_complementares` e `classe_objeto_pagina` continuam fora do índice
(agora explicitamente no `.gitignore`): precisam ser clonados à mão na raiz.

## Gerenciamento de dependências: uv, pip e o que usar

O repositório carrega **duas gerações** de gestão de dependências, sem dizer qual
vale:

| Arquivo | Origem | Conteúdo |
|---|---|---|
| `requirements.txt` | atualizado nesta branch | As mesmas dependências do `pyproject.toml`, para quem usa `pip`. Era uma lista congelada de 71 pacotes de jan/2024, com itens que o template não usa e pacotes suspeitos como `chromedriver==2.24.1`. |
| `pyproject.toml` + `uv.lock` | ago/2025 | Projeto `uv`, `requires-python = ">=3.10"`, 9 dependências (`pandas`, `selenium`, `beautifulsoup4`, `google-api-python-client`, `openpyxl`, `pipreqs`, `python-dotenv`, `pytz` e `logger` direto do GitHub). |
| `comandos_importantes.txt` | 2024 | Receita de `python -m venv` + `pip install -r requirements.txt`. |

A intenção do refactor de ago/2025 (`8db0e0a`) era migrar para o **uv** — o
`pyproject.toml` inclusive declara `Logger` como *workspace member* e busca o
pacote `logger` direto do repositório GitHub. A documentação do uv chegou a ficar
no README e foi removida em `9ed68d7` para não contaminar os robôs derivados;
com isso, o "como usar" da ferramenta **deixou de existir no repositório**. O
essencial, para não se perder:

```bash
pip install uv          # instalação global
uv sync                 # instala tudo o que está no pyproject.toml/uv.lock
uv add pandas selenium  # acrescenta dependências (atualiza pyproject + lock)
uv remove <pacote>      # remove
uv run main.py          # executa já garantindo o ambiente (.venv criado sozinho)
```

Para debugar dentro do ambiente, ative-o normalmente
(`.venv\Scripts\Activate`).

## Correções aplicadas nesta branch

O que estava quebrado no `main` e foi corrigido aqui:

### 1. O template não executava (import do `Logger`)

`python main.py` falhava na primeira chamada ao logger, **antes de qualquer
tarefa**, com `TypeError: 'module' object is not callable`.

O motivo: o repositório `Logger` não expõe a classe no pacote — o arquivo que
deveria ser `__init__.py` está gravado como `__init___.py` (três sublinhados) e
o conteúdo nem é Python válido. Assim `Logger` vira um *namespace package* e
`from Logger import Logger` devolve o **módulo** `Logger/Logger.py`, não a
classe. O import correto é `from Logger.Logger import Logger`, que era o que o
template usava (`from Logger.Logger import *`) até o refactor do uv em
21/08/2025 (`8db0e0a`) — uma regressão de quase um ano.

Corrigido em `main.py`, `realizar_tarefa.py` e nas duas page objects. De quebra,
`realizar_tarefa.py` importava `Logger` duas vezes, de origens diferentes
(`from classes_complementares import Logger` e `from Logger import Logger`); o
import redundante saiu.

### 2. Nenhum log era gravado, e o arquivo de log nunca era criado

Duas causas somadas:

- `main.py` montava o caminho `dados_logging/Execution_<data>.log` e **nunca
  chamava `logging.basicConfig`** — o arquivo não era criado.
- Todas as chamadas passavam o nível como **string** (`'INFO'`, `'ERROR'`),
  enquanto `criarLogPrint` compara com os membros do enum `LogLevel`. Nenhuma
  comparação casava, então a função só imprimia na tela e **não registrava
  nada**.

Agora `configurar_logging()` direciona o `logging` para o arquivo do dia e os
níveis são passados como `LogLevel.INFO` / `LogLevel.WARNING`. Ver
[Como registrar log](#como-registrar-log).

### 3. O resultado nunca voltava para a planilha

`Tarefas.realizar_tarefa()` não tinha `return`, então `main.py` recebia `None` e
`post_data(None)` levantava `AttributeError` — dentro do `try`, o que fazia
**toda execução bem-sucedida terminar com e-mail de erro** e a planilha nunca
ser atualizada. O método passou a devolver `self.df` (inclusive no atalho de
"nenhuma tarefa pendente").

### 4. Falha ao abrir o navegador virava "TRIBUNAL NÃO IDENTIFICADO"

`__set_page` engolia a exceção, deixando `self.page = None`. As etapas seguintes
estouravam `AttributeError` e a linha era marcada com `TRIBUNAL NÃO
IDENTIFICADO.` — mensagem que não tem relação com a causa real. Agora
`__set_page` e `__tratar_acessar` repassam o erro, e a linha falha com o motivo
verdadeiro, sem tentar executar a tarefa sem navegador.

### 5. Assinatura dos stubs incompatível com quem os chama

`__tratar_acessar` chama `acessar(login=…, senha=…)` e o stub `Acessar.acessar()`
não aceitava argumentos. Corrigido, junto com a troca de `self.log.exception(…)`
— método que a classe `Logger` não possui — por `criarLogPrint`.

### 6. Segredos e artefatos desprotegidos

O `.gitignore` só tinha `/.idea/`, e o `.env` era versionado. Agora o `.env` saiu
do índice, entrou o `.env.example`, e o `.gitignore` cobre ambientes virtuais,
`__pycache__`, `.env`, as bibliotecas internas e os artefatos de execução
(`dados_logging/`, `resultado/`, `downloads/`, `*.log`, `*.xlsx` exceto o
`teste.xlsx`). É a correção com maior efeito multiplicador: robôs derivados
nasciam commitando `.env`, logs e planilhas.

### 7. Ajustes menores

- `teste.xlsx` ganhou as colunas `login`, `senha`, `DATA RESULTADO` e `ERRO`, que
  o código lê e escreve — antes o primeiro teste falhava com `KeyError`.
- `.gitmodules` declarado para o submódulo `Logger`.
- `requirements.txt` alinhado com o `pyproject.toml` (era uma lista congelada de
  71 pacotes de jan/2024).
- Caminho do perfil do Chrome e destinatários de e-mail passaram a aceitar
  configuração por `.env` (`CHROME_PROFILE_DIR`, `LISTA_EMAIL_TI`), mantendo os
  valores atuais como padrão.
- `description` do `pyproject.toml` deixou de ser "Add your description here".
- Variáveis mortas removidas (`nomeClasse`) e `os.makedirs(..., exist_ok=True)`
  no lugar do `if not os.path.exists`.

## Como registrar log

A classe `Logger` (repositório `Logger`) tem duas particularidades que valem
conhecer antes de mexer:

| Regra | Consequência |
|---|---|
| O parâmetro `tipo` é comparado com os membros de `LogLevel` | Passar a string `'INFO'` **não registra nada** — só imprime na tela |
| `LogLevel.ERROR` e `LogLevel.CRITICAL` **levantam exceção** depois de logar | Não use nesses casos em que a execução precisa continuar (ex.: dentro de um `except` que ainda vai enviar e-mail) |

Por isso o template usa:

```python
from Logger.Logger import Logger, LogLevel

log = Logger()
log.criarLogPrint('mensagem informativa', LogLevel.INFO, classe=__name__)
log.criarLogPrint('erro tratado, execução continua', LogLevel.WARNING, classe=__name__)
```

Use `LogLevel.ERROR` apenas quando **interromper** a execução for o
comportamento desejado.

## O que os robôs herdam daqui

O template é a raiz de padrões — bons e ruins — que aparecem repetidos por toda
a organização. Alguns já observados em repositórios derivados:

- **`.gitignore` com apenas `/.idea/`** (corrigido nesta branch). Como nada era
  ignorado por padrão, robôs novos commitavam o que não deveriam:
  `extrai_documentos_caixa` e `divisor_de_fases_caixa_por_maquina` nasceram com
  o `.env` versionado no "Initial commit"; o primeiro chegou a commitar planilha
  de logins, logs de execução e PDFs de processos reais.
- **`.env` versionado** com valores de exemplo (corrigido nesta branch) — o
  hábito de versionar o arquivo vem daqui.
- **README não preenchido.** O texto "ADICIONE UM RESUMO DO QUE O ROBÔ FAZ"
  sobreviveu por meses em vários repositórios.
- **`robo_lanca_andamentos.pdf` (992 KB) copiado junto** e depois apagado no
  segundo commit (foi o que aconteceu em `divisor_de_fases_caixa_por_maquina`).
- **Sucesso registrado como erro** no `else` do `main.py` (corrigido nesta
  branch): a mensagem de fim era gravada com nível `'ERROR'`.
- **Caminho de profile do Chrome fixo** em
  `C:/Users/Administrator/AppData/Local/Google/Chrome/User Data/Profile 1`,
  amarrando o robô a um usuário Windows específico. Nesta branch o valor virou
  padrão sobrescrevível por `CHROME_PROFILE_DIR`, mas continua viajando para
  todos os robôs.

Corrigir um desses itens **aqui** vale mais do que corrigir em dez robôs depois.

## Histórico

| Commit | Data | O que mudou |
|---|---|---|
| `616b4f2` | 16/01/2024 | Primeiro commit (Rennan Alves). |
| `3439456` | 25/01/2024 | `requirements.txt` cresce para 71 pacotes pinados. |
| `ca42cd0` | 06/06/2024 | Acrescenta o gitlink `Logger` e ajusta o `main.py` (import ainda correto: `from Logger.Logger import *`). |
| `5ed9523`–`74fa027` | 17/07/2024 | Cria o `README.md` modelo e sobe o PDF de exemplo. |
| `e5a24eb` | 19/11/2024 | `realizar_tarefa.py` ganha o `chrome()` completo (+43 linhas). |
| `8137661`, `db338e8` | 21/01/2025 | Remove imports duplicados de `os` e `datetime`. |
| `8db0e0a` | 21/08/2025 | **Refactor uv**: `pyproject.toml`, `uv.lock`, novo `teste.xlsx`, documentação do uv no README — e a regressão do import do `Logger`. |
| `9745305` | 25/08/2025 | Remove emoji do README. |
| `9ed68d7` | 27/08/2025 | **Remove a documentação do uv do README** (para não ir junto nos robôs). |
| `c0baae2` | 29/08/2025 | Merge do PR #7 — HEAD atual. |

## Débitos técnicos e riscos conhecidos

Os itens corrigidos nesta branch estão em
[Correções aplicadas](#correções-aplicadas-nesta-branch). O que **continua em
aberto**:

- **Duas gerações de dependências convivendo** (`requirements.txt` e
  `pyproject.toml`/`uv.lock`) e um `comandos_importantes.txt` que ensina a
  geração antiga. Os arquivos agora estão alinhados, mas continua sem nada
  dizendo qual é a oficial — e são dois lugares para manter.
- **`Logger` fixado num commit de março/2024.** O `.gitmodules` desta branch faz
  o `git submodule update --init` funcionar, mas o commit fixado segue atrás do
  repositório de origem.
- **Nenhum teste automatizado**, num repositório cujo código é copiado para
  dezenas de robôs. Um teste que apenas importe `main.py` teria pego a regressão
  do `Logger` no dia em que ela entrou.
- **`robo_lanca_andamentos.pdf` (992 KB)** continua no repositório e viaja para
  cada robô novo.
- **README modelo depende de serviços externos** (`capsule-render.vercel.app` e
  `readme-typing-svg.herokuapp.com`) para os banners: se saírem do ar, todos os
  READMEs derivados ficam com imagem quebrada.
- **`pyproject.toml` mantém `name = "template-bluetape"`**, que ninguém troca ao
  criar o robô.
- **Extensões do Chrome não versionadas** (`anticaptcha-plugin_v0.63.crx`,
  `WebSigner-Extension-ESAJ.crx`, `plugin.zip`): o código as carrega se
  existirem, mas nada documenta onde obtê-las.
- **O `.env` não é validado:** `NOME_CLIENTE`/`NOME_ROBO` ausentes viram `None`
  no assunto dos e-mails, sem aviso.
