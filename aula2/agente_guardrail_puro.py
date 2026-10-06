# agente_guardrail_puro.py — Seção 6 do deck: "guardrails" (exercício 6.1)
#
# Conceito central: Guardrail de entrada (input_guardrail) implementado em Python puro,
# SEM chamadas adicionais a LLMs.
# Uma trava de segurança determinística inspeciona o prompt do usuário antes de repassá-lo
# ao modelo de linguagem principal. Se qualquer termo proibido de uma lista negra for
# detectado, o guardrail dispara o "tripwire" (`tripwire_triggered=True`).
#
# Quando o tripwire é acionado:
#   1. A execução do agente é imediatamente interrompida ANTES de consumir qualquer token do LLM.
#   2. O SDK lança a exceção `InputGuardrailTripwireTriggered`.
#   3. A camada de aplicação pode capturar essa exceção e retornar uma resposta de bloqueio segura.

import os
import sys

# Coloca a raiz do curso no sys.path para importar provedor (e o .env) de qualquer aula.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio
from agents import (
    Agent,
    Runner,
    GuardrailFunctionOutput,
    InputGuardrailTripwireTriggered,
    input_guardrail,
)
from provedor import configurar, modelo

configurar()

# Lista de palavras ou tópicos explicitamente proibidos para este agente focado em programação
PALAVRAS_PROIBIDAS = ["receita", "futebol", "fofoca", "bolo", "campeonato"]


# ---------------------------------------------------------------------------
# 1. Definição do Input Guardrail (Python puro)
# ---------------------------------------------------------------------------
@input_guardrail
async def bloquear_off_topic(ctx, agent, input) -> GuardrailFunctionOutput:
    """Inspeciona a entrada do usuário em busca de palavras-chave off-topic antes de acionar o LLM."""
    texto = input if isinstance(input, str) else str(input)
    texto_lower = texto.lower()

    # Checagem determinística instantânea em memória (custo 0 de inferência)
    palavras_encontradas = [p for p in PALAVRAS_PROIBIDAS if p in texto_lower]
    violou = len(palavras_encontradas) > 0

    if violou:
        print(f"\n🚨 [GUARDRAIL PURO DISPARADO] Termos proibidos detectados: {palavras_encontradas}")

    return GuardrailFunctionOutput(
        output_info={"termos_detectados": palavras_encontradas},
        tripwire_triggered=violou,
    )


# ---------------------------------------------------------------------------
# 2. Definição do Agente com a Trava Ativa
# ---------------------------------------------------------------------------
tutor_programacao = Agent(
    name="Tutor de Programação",
    instructions=(
        "Você é um tutor focado exclusivamente em Ciência da Computação, Engenharia de Software e Programação. "
        "Explique conceitos de forma didática e técnica com código de exemplo."
    ),
    model=modelo(),
    input_guardrails=[bloquear_off_topic],
)


# ---------------------------------------------------------------------------
# 3. Função de Execução Segura
# ---------------------------------------------------------------------------
def executar_com_guardrail(mensagem: str):
    print(f"\n{'─' * 60}")
    print(f"📥 Input recebido: \"{mensagem}\"")
    try:
        resultado = Runner.run_sync(tutor_programacao, mensagem)
        print(f"✅ Agente respondeu:\n{resultado.final_output}")
        return resultado.final_output
    except InputGuardrailTripwireTriggered:
        msg_bloqueio = (
            "⚠️ [BLOQUEIO DE SEGURANÇA] Sua solicitação foi rejeitada pelo guardrail de entrada "
            "por conter termos fora do escopo de programação (política de uso aceitável)."
        )
        print(msg_bloqueio)
        return msg_bloqueio


def main():
    print(f"=== Demonstração de Input Guardrail em Python Puro (Exercício 6.1) ===")
    print(f"Modelo configurado: {modelo()}\n")

    # Caso 1: Pergunta válida sobre programação (deve passar normalmente)
    executar_com_guardrail("Como faço um loop for com enumerate em Python?")

    # Caso 2: Pergunta contendo termo proibido (deve disparar o tripwire e não chamar o LLM)
    executar_com_guardrail("Você poderia me ensinar uma receita de bolo de chocolate?")


if __name__ == "__main__":
    main()
