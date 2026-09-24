"""provedor.py — cópia do `provedor.py` da raiz do projeto, só para este container.

Por que existe uma cópia aqui, se o resto do curso usa um único provedor.py
na raiz? Porque este arquivo é empacotado dentro da imagem Docker do serviço
`agente` (ver `docker-compose.yml`, serviço "agente", e `Dockerfile` desta
pasta: `COPY provedor.py main.py ./`). Um build Docker só enxerga arquivos
dentro do seu "contexto de build" (aqui, a própria pasta `agente/`) — ele não
consegue alcançar o `provedor.py` da raiz do projeto sem reconfigurar o
contexto de build no `docker-compose.yml`, o que tornaria o build mais lento
(context maior) e exigiria um `.dockerignore` cuidadoso. Por isso, para este
único caso (o único serviço desta aula que corre um `Agent`, fora de um
container que só fala com o banco), mantemos uma cópia física — mas com o
MESMO conteúdo do arquivo raiz, para não divergir em comportamento.

Se você alterar o `provedor.py` da raiz do projeto, replique a mudança aqui
também (ou copie o arquivo de novo) antes de rodar `docker compose --profile
full up --build`.
"""

import os
import sys

from dotenv import load_dotenv
from openai import AsyncOpenAI
from agents import (
    Runner,
    set_default_openai_api,
    set_default_openai_client,
    set_default_openai_key,
    set_tracing_disabled,
)

load_dotenv()

# Provedor atualmente ativo (atualizado por configurar()).
ATIVO = "openai"

RESET = "\033[0m"
RED = "\033[31m"
YELLOW = "\033[33m"


def _ligar_cliente(cliente: AsyncOpenAI) -> None:
    set_default_openai_client(cliente)
    set_default_openai_api("chat_completions")
    set_tracing_disabled(True)


def _configurar_ollama() -> None:
    base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1")
    cliente = AsyncOpenAI(base_url=base_url, api_key="ollama")
    _ligar_cliente(cliente)


def _configurar_zen() -> None:
    base_url = os.getenv("OPENAI_BASE_URL", "https://opencode.ai/zen/v1")
    cliente = AsyncOpenAI(base_url=base_url, api_key=os.getenv("OPENAI_API_KEY"))
    _ligar_cliente(cliente)


def configurar(provedor: str | None = None) -> str:
    """Aplica a configuração do provedor escolhido no .env. Devolve o nome dele."""
    global ATIVO
    provedor = (provedor or os.getenv("PROVEDOR", "openai")).strip().lower()
    ATIVO = provedor

    if provedor == "ollama":
        _configurar_ollama()
    elif provedor == "zen":
        _configurar_zen()
    else:
        set_default_openai_key(os.getenv("OPENAI_API_KEY"))

    return provedor


def modelo() -> str:
    """Nome do modelo do provedor ativo (zen -> OPENAI_MODEL; senão -> OLLAMA_MODEL).

    `agente/main.py` desta aula não chama esta função hoje (não passa `model=`
    ao criar o `Agent` — ver nota no README sobre `OPENAI_DEFAULT_MODEL`), mas
    ela fica disponível aqui para manter este arquivo idêntico ao da raiz.
    """
    if ATIVO == "zen":
        return os.getenv("OPENAI_MODEL", "deepseek-v4-flash")
    return os.getenv("OLLAMA_MODEL", "llama3.2:3b")


def cair_para_ollama() -> None:
    """Força o recuo de segurança para o Ollama local."""
    configurar("ollama")


def rodar(agente_fabrica, mensagem):
    """Executa o agente via Runner. Em falha do provedor Zen, recua para o Ollama local."""
    try:
        return Runner.run_sync(agente_fabrica(), mensagem)
    except Exception as exc:
        if ATIVO != "zen":
            raise
        print(f"{RED}[FALHA - zen]{RESET} {exc}", file=sys.stderr)
        print(f"{YELLOW}[RECUO]{RESET} Alternando para Ollama local e tentando novamente...", file=sys.stderr)
        cair_para_ollama()
        return Runner.run_sync(agente_fabrica(), mensagem)


async def rodar_async(agente_fabrica, mensagem, **kwargs):
    """Igual a `rodar()`, mas para `await Runner.run(...)` (agente com MCP via HTTP)."""
    try:
        return await Runner.run(agente_fabrica(), mensagem, **kwargs)
    except Exception as exc:
        if ATIVO != "zen":
            raise
        print(f"{RED}[FALHA - zen]{RESET} {exc}", file=sys.stderr)
        print(f"{YELLOW}[RECUO]{RESET} Alternando para Ollama local e tentando novamente...", file=sys.stderr)
        cair_para_ollama()
        return await Runner.run(agente_fabrica(), mensagem, **kwargs)
