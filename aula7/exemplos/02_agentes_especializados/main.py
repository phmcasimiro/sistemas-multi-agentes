"""
Exemplo 02 -- AGENTES ESPECIALIZADOS.

No exemplo 01 um agente fazia tudo. Agora dividimos por PAPÉIS:

    SOLICITAÇÃO -> INVESTIGADOR -> JURÍDICO -> ANALISTA

Cada especialista é um Agent(name=..., instructions=...) com UMA responsabilidade, uma entrada e uma saída bem definidas.

Atenção: especializar NÃO exige modelos diferentes. Os três usam o MESMO LLM.
O que os diferencia é:  instruções . responsabilidade . contexto de
entrada . critério de saída  (e, em sistemas reais, ferramentas -- veja o exemplo 05).

Repare no incômodo deste exemplo: quem leva o resultado de um especialista ao
próximo somos NÓS, à mão, passando strings de uma chamada para outra. Com três
especialistas é tolerável; com dez, vira bagunça. O exemplo 03 resolve isso com
um ESTADO COMPARTILHADO.

Rodar (LLM REAL: configure o .env; veja o README), a partir de aula7/:
    python exemplos\\02_agentes_especializados\\main.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from agents import Agent, Runner

import prompts
from caso import DENUNCIA_045
from provedor import configurar

MODELO = configurar()  # LLM REAL: PROVEDOR no .env (openai ou ollama)

SOLICITACAO = DENUNCIA_045


def executar(agente: Agent, contexto: str) -> str:
    """Roda UM agente com a entrada `contexto` e devolve o texto que ele respondeu."""
    print(f"[{agente.name.upper()}]")
    return Runner.run_sync(agente, contexto).final_output


investigador = Agent(
    name="Investigador",
    instructions=(
        "Você é o Investigador de um órgão de controle. Objetivo: levantar os fatos da contratação. "
        "Liste apenas fatos verificáveis. Não opine e não cite leis. Responda em no máximo 3 frases.\n"
        f"{prompts.REGRA}"
    ),
)
juridico = Agent(
    name="Jurídico",
    instructions=(
        "Você é o Jurídico de um órgão de controle. Objetivo: enquadrar os fatos na legislação. "
        "Aponte normas potencialmente violadas. Não avalie risco e não recomende ações. "
        "Responda em no máximo 3 frases.\n"
        f"{prompts.REGRA}"
    ),
)
analista = Agent(
    name="Analista",
    instructions=(
        "Você é o Analista de um órgão de controle. Objetivo: avaliar o risco a partir dos fatos e do enquadramento. "
        "Classifique o risco em BAIXO, MÉDIO ou ALTO e justifique em uma frase. Responda em no máximo 3 frases.\n"
        f"{prompts.REGRA}"
    ),
)

if __name__ == "__main__":
    print(f"Modelo em uso: {MODELO}\n")

    # Passamos o resultado de um para o outro NA MÃO.
    fatos = executar(investigador, SOLICITACAO)
    print("  ->", fatos, "\n")

    enquadramento = executar(juridico, fatos)
    print("  ->", enquadramento, "\n")

    risco = executar(analista, f"Fatos: {fatos}\nEnquadramento: {enquadramento}")
    print("  ->", risco, "\n")

    print("Cada especialista faz UMA coisa. Mas o encadeamento está nas variáveis soltas do script:")
    print("o fluxo e os dados ainda não são explícitos. Próximo exemplo: estado compartilhado.")
