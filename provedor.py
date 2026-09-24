"""provedor.py — a "central elétrica" do curso.

O que este arquivo faz, em uma frase: ele decide PARA ONDE as perguntas dos
agentes são enviadas (OpenAI de verdade, OpenCode Zen ou Ollama local) — e faz
isso baseado só no que está escrito no arquivo `.env`, sem precisar mudar
nenhuma linha de código dos agentes.

Por que isso existe? Sem este arquivo, cada script (`agente1.py`,
`agente2.py`, ...) teria que repetir a mesma lógica de "qual servidor eu uso,
com qual chave, em qual endereço". Escrever essa lógica UMA vez aqui e
reaproveitá-la em todo lugar é o princípio chamado DRY (Don't Repeat
Yourself — "não se repita").

Este arquivo é importado por TODOS os agentes das Aulas 1, 2 e 3 com a linha:

    from provedor import configurar, modelo, rodar

Por isso, os nomes das funções abaixo (`configurar`, `modelo`, `rodar`,
`cair_para_ollama`) não podem mudar — são o "contrato" que o resto do curso
espera encontrar aqui.
"""

import os
import sys

# `dotenv` é uma biblioteca externa (instalada via requirements.txt) que sabe
# ler um arquivo chamado `.env` e colocar cada linha dele como se fosse uma
# variável de ambiente do sistema operacional — as mesmas que `os.getenv()`
# consegue ler logo abaixo.
from dotenv import load_dotenv

# `AsyncOpenAI` é o cliente HTTP oficial da biblioteca openai, na versão
# assíncrona (é o que o SDK de agentes espera para poder rodar várias
# chamadas "ao mesmo tempo" sem travar o programa). "Cliente" aqui não é
# pessoa: é o objeto Python responsável por montar e enviar as requisições
# HTTP para o servidor de IA.
from openai import AsyncOpenAI

# Estas funções vêm do SDK `openai-agents` e servem para configurar,
# globalmente, COMO o SDK deve se conectar a um servidor de IA:
#   - set_default_openai_client: troca o cliente HTTP padrão usado por todo
#     `Agent` criado depois desta chamada.
#   - set_default_openai_api: escolhe qual rota da API usar
#     ("responses" ou "chat_completions" — explicado mais abaixo).
#   - set_default_openai_key: define a chave de API quando se usa a OpenAI
#     "de verdade" (sem trocar o cliente).
#   - set_tracing_disabled: liga/desliga o envio de telemetria para a OpenAI.
from agents import (
    Runner,
    set_default_openai_api,
    set_default_openai_client,
    set_default_openai_key,
    set_tracing_disabled,
)

# Lê o arquivo `.env` (que fica na raiz do curso) e carrega cada linha dele
# como uma variável de ambiente. A partir daqui, `os.getenv("PROVEDOR")`,
# por exemplo, já consegue enxergar o valor escrito no `.env`.
load_dotenv()

# ---------------------------------------------------------------------------
# Estado global: qual provedor está ativo AGORA
# ---------------------------------------------------------------------------
# Uma variável "global" (declarada fora de qualquer função) é visível e
# compartilhada por TODAS as funções deste arquivo. Usamos uma aqui porque
# `modelo()` e `rodar()` precisam saber, a qualquer momento, qual foi o
# último provedor escolhido por `configurar()` — sem repetir esse valor como
# argumento em toda chamada de função.
#
# Começa como "openai" só como valor inicial; na prática, o valor real é
# sempre definido pela primeira chamada a `configurar()` em cada script.
ATIVO = "openai"

# Códigos de escape ANSI: sequências especiais que o terminal (bash, zsh...)
# interpreta como "comece a pintar o texto de tal cor" ou "volte ao normal".
# Não são bibliotecas nem "mágica" — são só texto; você pode até digitá-los
# à mão e ver o terminal colorir a linha.
RESET = "\033[0m"   # "desliga" a cor, volta ao padrão do terminal
RED = "\033[31m"    # vermelho — usado para mensagens de falha
YELLOW = "\033[33m"  # amarelo — usado para avisos


def _ligar_cliente(cliente: AsyncOpenAI) -> None:
    """Aplica um cliente HTTP já configurado como o "padrão" do SDK.

    As três linhas abaixo se repetiam, idênticas, dentro de
    `_configurar_ollama()` e `_configurar_zen()`. Extraí-las para uma função
    própria evita copiar e colar o mesmo código duas vezes (DRY) — se um dia
    precisarmos mudar esse comportamento, mudamos em um único lugar.
    """
    # A partir daqui, qualquer `Agent` criado no programa usa ESTE cliente
    # para conversar com o modelo de linguagem.
    set_default_openai_client(cliente)
    # O SDK tenta, por padrão, usar a rota mais nova da OpenAI (`/responses`).
    # Ollama, OpenCode Zen e a maioria dos servidores compatíveis só
    # implementam a rota mais antiga e consolidada (`/chat/completions`).
    # Esta linha evita um erro "404 Not Found" ao forçar a rota certa.
    set_default_openai_api("chat_completions")
    # Sem isso, o SDK tentaria enviar métricas de uso para os servidores da
    # OpenAI — usando uma chave que não é da OpenAI — e isso gera erros
    # "401 Unauthorized" aparecendo no terminal sem necessidade.
    set_tracing_disabled(True)


def _configurar_ollama() -> None:
    """Liga o SDK ao Ollama, o servidor de IA que roda na sua própria máquina."""
    # `os.getenv("CHAVE", "valor_padrao")`: lê a variável de ambiente
    # OLLAMA_BASE_URL; se ela não existir no `.env`, usa o texto depois da
    # vírgula como valor padrão — assim o código não quebra por falta de
    # configuração.
    base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1")
    # O construtor de AsyncOpenAI EXIGE uma api_key, mesmo que o Ollama não
    # verifique nada — por isso passamos qualquer texto fixo aqui.
    cliente = AsyncOpenAI(base_url=base_url, api_key="ollama")
    _ligar_cliente(cliente)


def _configurar_zen() -> None:
    """Liga o SDK ao OpenCode Zen, um provedor em nuvem compatível com a API da OpenAI."""
    base_url = os.getenv("OPENAI_BASE_URL", "https://opencode.ai/zen/v1")
    cliente = AsyncOpenAI(base_url=base_url, api_key=os.getenv("OPENAI_API_KEY"))
    _ligar_cliente(cliente)


def configurar(provedor: str | None = None) -> str:
    """Liga o SDK ao provedor escolhido e devolve o nome dele.

    Como usar: chame `configurar()` (sem argumento) uma vez, no início do
    script — ela decide sozinha qual provedor usar lendo a variável
    `PROVEDOR` do `.env`. O argumento `provedor` só existe para casos
    especiais, como o recuo automático de `cair_para_ollama()` abaixo, que
    precisa FORÇAR o Ollama mesmo que o `.env` diga outra coisa.
    """
    # `global ATIVO` avisa ao Python: "a variável ATIVO usada aqui dentro é
    # a mesma que existe lá fora, no nível do módulo — não crie uma cópia
    # local só para esta função". Sem essa linha, a atribuição abaixo criaria
    # uma variável nova que desapareceria ao fim da função, e o resto do
    # arquivo nunca saberia qual provedor foi escolhido.
    global ATIVO

    # `provedor or os.getenv(...)`: se `provedor` foi passado (não é None,
    # nem uma string vazia), usa ele; senão, cai para o valor do `.env`.
    # `.strip().lower()` remove espaços em branco acidentais e ignora
    # maiúsculas/minúsculas (" Zen " e "zen" viram a mesma coisa).
    provedor = (provedor or os.getenv("PROVEDOR", "openai")).strip().lower()
    ATIVO = provedor

    if provedor == "ollama":
        _configurar_ollama()
    elif provedor == "zen":
        _configurar_zen()
    else:
        # Qualquer outro valor (ou nenhum) cai no caminho padrão: OpenAI de
        # verdade, autenticada só com a chave — sem trocar o cliente HTTP.
        set_default_openai_key(os.getenv("OPENAI_API_KEY"))

    return provedor


def modelo() -> str:
    """Devolve o nome do modelo de IA a usar, de acordo com o provedor ativo.

    Cada provedor tem seu próprio "cardápio" de modelos, por isso o nome
    certo depende de qual está ativo em `ATIVO` (definido por `configurar()`).
    Os agentes chamam esta função assim: `Agent(..., model=modelo())`.
    """
    if ATIVO == "zen":
        return os.getenv("OPENAI_MODEL", "deepseek-v4-flash")
    # Qualquer outro provedor ativo (incluindo "ollama") usa o modelo local.
    return os.getenv("OLLAMA_MODEL", "llama3.2:3b")


def cair_para_ollama() -> None:
    """"Recuo de segurança": força a troca para o Ollama local.

    É só um atalho para `configurar("ollama")` — existe como função própria
    para deixar bem claro, em quem lê o código, QUANDO e POR QUE esse recuo
    acontece (veja `rodar()` logo abaixo).
    """
    configurar("ollama")


def rodar(agente_fabrica, mensagem):
    """Executa um agente e devolve o resultado — com um plano B automático.

    Parâmetros:
        agente_fabrica: uma FUNÇÃO (sem argumentos) que, quando chamada,
            devolve um `Agent` pronto para uso — por exemplo, a função
            `criar_agente` que aparece nos scripts da Aula 1. Por que uma
            função e não o `Agent` já pronto? Porque, se o recuo para o
            Ollama acontecer no meio do caminho, é preciso RECRIAR o agente
            com `model=modelo()` apontando para o modelo do Ollama — e só
            uma função pode ser "chamada de novo" para gerar essa nova
            versão.
        mensagem: o texto que será enviado ao agente (a pergunta do usuário).

    Devolve o mesmo objeto que `Runner.run_sync(...)` devolveria — o
    `RunResult`, do qual normalmente se lê `.final_output`.
    """
    try:
        # Caminho feliz: cria o agente (chamando a fábrica) e executa.
        return Runner.run_sync(agente_fabrica(), mensagem)
    except Exception as exc:
        # `except Exception as exc` captura QUALQUER erro que aconteça na
        # linha acima (falha de rede, chave inválida, cota esgotada...) e
        # guarda o erro no nome `exc`, para podermos usá-lo (ex.: imprimir).
        if ATIVO != "zen":
            # O recuo automático só faz sentido quando o provedor principal
            # é o Zen (provedor em nuvem, sujeito a falhar). Se o erro
            # aconteceu rodando OpenAI ou já rodando Ollama, não há para
            # onde recuar — `raise` relança o MESMO erro, sem escondê-lo.
            raise
        # `file=sys.stderr` (não stdout): alguns scripts que chamam `rodar()`
        # são eles mesmos servidores MCP via stdio (Aula 5), e stdout é o
        # canal do protocolo JSON-RPC — imprimir aqui sem isso corromperia
        # a comunicação com o cliente MCP.
        print(f"{RED}[FALHA - zen]{RESET} {exc}", file=sys.stderr)
        print(f"{YELLOW}[RECUO]{RESET} Alternando para Ollama local e tentando novamente...", file=sys.stderr)
        cair_para_ollama()
        # Repete a mesma lógica do "caminho feliz", mas agora com o Ollama
        # já ativo — por isso `agente_fabrica()` é chamada de novo aqui:
        # ela vai embutir `model=modelo()` já apontando para o Ollama.
        return Runner.run_sync(agente_fabrica(), mensagem)


async def rodar_async(agente_fabrica, mensagem, **kwargs):
    """Igual a `rodar()`, mas para agentes assíncronos (`await Runner.run(...)`).

    Necessária para os agentes da Aula 5 que usam MCP Servers: conectar a um
    MCP Server (`async with MCPServerStdio(...)`) só funciona dentro de uma
    função `async`, e por isso a execução do agente também precisa ser
    assíncrona. `**kwargs` repassa argumentos extras do `Runner.run`, como
    `max_turns=25`.
    """
    try:
        return await Runner.run(agente_fabrica(), mensagem, **kwargs)
    except Exception as exc:
        if ATIVO != "zen":
            raise
        print(f"{RED}[FALHA - zen]{RESET} {exc}", file=sys.stderr)
        print(f"{YELLOW}[RECUO]{RESET} Alternando para Ollama local e tentando novamente...", file=sys.stderr)
        cair_para_ollama()
        return await Runner.run(agente_fabrica(), mensagem, **kwargs)
