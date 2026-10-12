"""
Exemplo 01 -- O AGENTE GENERALISTA.

Cenário da aula inteira: chega uma denúncia sobre uma contratação pública e o
sistema precisa produzir uma avaliação. Começamos como todo mundo começa: UM
agente, UMA instrução, que faz tudo.

    receber -> investigar -> interpretar (jurídico) -> avaliar risco -> recomendar
                 \_______________ tudo dentro de UM agente ______________/

O agente é o mesmo das Aulas 1 a 4:  Agent(name=..., instructions=...)  e roda com Runner.run_sync().

Rode e observe: funciona. O problema não está no resultado, está na ARQUITETURA:

  - uma instrução gigante mistura quatro responsabilidades muito diferentes;
  - não dá para ver (nem auditar) onde a investigação termina e o direito começa;
  - não dá para trocar, melhorar ou testar UMA das partes sem mexer nas outras;
  - não há onde inserir um humano: o agente entrega tudo ou nada.

Pergunta para a turma: e se investigação, análise jurídica e análise de risco
fossem responsabilidades tão diferentes que merecessem especialistas diferentes?
É o que fazemos no exemplo 02.

Rodar (LLM REAL: configure o .env; veja o README), a partir de aula7/:
    python exemplos\\01_agente_generalista\\main.py

Trocar de modelo SEM alterar este arquivo (PowerShell):
    $env:PROVEDOR = "openai"     # padrão; exige OPENAI_API_KEY (veja .env.example)
    $env:PROVEDOR = "ollama"     # local e grátis; exige `ollama serve` e o modelo baixado
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from agents import Agent, Runner

import prompts
from caso import DENUNCIA_045
from provedor import configurar

MODELO = configurar()  # LLM REAL: PROVEDOR no .env (openai ou ollama)

SOLICITACAO = DENUNCIA_045  # os FATOS vêm na denúncia (veja caso.py): o LLM não pode inventá-los


def agente_generalista(solicitacao: str) -> str:
    """UM agente, UMA instrução: investiga, interpreta, avalia risco e recomenda."""
    print("[AGENTE GENERALISTA] eu faço tudo...")
    generalista = Agent(name="Generalista", instructions=prompts.INSTR_TUDO)
    return Runner.run_sync(generalista, solicitacao).final_output


if __name__ == "__main__":
    print(f"Modelo em uso: {MODELO}\n")
    print("Solicitação:", SOLICITACAO, "\n")
    resposta = agente_generalista(SOLICITACAO)
    print("\nResposta única:")
    print(resposta)
    print("\nOnde termina a investigação? Quem fez a análise jurídica? Não dá para saber.")
