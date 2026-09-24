"""
Exemplo 05 -- AGENTE + MCP com VÁRIAS TOOLS.

Mesmo agente do Exemplo 04, mas apontando para o server do Exemplo 05, que
tem três tools: listar_tipos_ocorrencia, consultar_ocorrencias e
estatisticas_ocorrencias. O agente escolhe sozinho qual usar (e em que ordem).

Rodar:
    python agente.py
    python agente.py "Quais os tipos de ocorrência que existem?"
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))  # raiz do projeto (provedor.py)

from agents import Agent
from agents.mcp import MCPServerStdio

from provedor import configurar, modelo, rodar_async

configurar()

CAMINHO_SERVER = str(Path(__file__).resolve().parent / "server.py")  # o server DESTA pasta

PERGUNTA = (
    sys.argv[1]
    if len(sys.argv) > 1
    else "Quais são os tipos de ocorrência mais comuns nos últimos 30 dias?"
)


async def main():
    async with MCPServerStdio(
        name="MCP Ocorrências",
        params={"command": sys.executable, "args": [CAMINHO_SERVER]},
    ) as mcp_ocorrencias:

        def criar_agente() -> Agent:
            return Agent(
                name="Assistente CISP",
                instructions=(
                    "Você ajuda operadores da CISP a entender as ocorrências recentes. "
                    "Use as ferramentas do MCP Ocorrências para responder com dados reais. "
                    "Antes de filtrar por tipo de ocorrência, confirme o código exato do tipo "
                    "com listar_tipos_ocorrencia; não adivinhe códigos."
                ),
                mcp_servers=[mcp_ocorrencias],
                model=modelo(),
            )

        print(f"Pergunta: {PERGUNTA}")
        resultado = await rodar_async(criar_agente, PERGUNTA)

        # Quais tools o LLM escolheu, em que ordem e com quais parâmetros.
        for item in resultado.new_items:
            if type(item).__name__ == "ToolCallItem":
                print(f"\n[tool] {item.raw_item.name}  parametros: {item.raw_item.arguments}")

        print("\n--- Resposta do agente ---")
        print(resultado.final_output)


if __name__ == "__main__":
    asyncio.run(main())
