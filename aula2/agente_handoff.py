# agente_handoff.py — Seção 3 do deck (Aula 1): "encaminhar" — mesa de triagem que
# transfere o TURNO para o especialista certo (exercício 3.1).
#
# Conceito central: um único agente é limitado pelo seu contexto e instruções. Em vez de
# um `if/else` de roteamento escrito à mão, o Agents SDK deixa a decisão de "para quem
# encaminhar" inteiramente a cargo do próprio modelo, em linguagem natural.

import os
import sys

# Coloca a raiz do curso no sys.path para importar provedor (e o .env) de qualquer aula.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents import Agent, Runner
from provedor import configurar, modelo

configurar()

# Especialista 1: só sabe (por instrução) responder matemática.
agente_matematico = Agent(
    name="agente_matematico",
    instructions="Você é um especialista em matemática. Responda com precisão e clareza.",
    model=modelo(),
    # `handoff_description` é a "placa de sinalização" deste destino: é o texto que o
    # agente TRIADOR lê para decidir quando encaminhar para cá. Não é lido pelo usuário.
    handoff_description=("Se a pergunta for sobre matemática, eu devo responder."),
)

# Especialista 2: só sabe (por instrução) responder história.
agente_historiador = Agent(
    name="agente_historiador",
    instructions="Você é um especialista em história. Responda com precisão e clareza.",
    model=modelo(),
    handoff_description=("Se a pergunta for sobre história, eu devo responder."),
)

# O triador: não responde matemática nem história ele mesmo — só decide para quem mandar.
agente_triador = Agent(
    name="agente_triador",
    instructions=" Você é um agente triador. Sua função é direcionar perguntas para o agente mais adequado com base no conteúdo da pergunta. " \
    "Se a pergunta for sobre matemática, encaminhe para o agente_matematico. Se for sobre história, encaminhe para o agente_historiador. " \
    "Se não se enquadrar em nenhuma dessas categorias, responda que não sabe.",
    model=modelo(),
    # `handoffs=[...]` (em vez de `tools=[...]`) é o que ativa o mecanismo de handoff:
    # por baixo dos panos, cada agente da lista vira uma ferramenta `transfer_to_<nome>`
    # que o triador pode chamar. Ao chamá-la, o CONTROLE DO TURNO é transferido — quem
    # responde ao usuário passa a ser o especialista, não mais o triador.
    handoffs=[agente_matematico, agente_historiador],
)

def executar_agente_handoff(mensagem: str) -> str:
    resultado = Runner.run_sync(
        agente_triador,
        mensagem
    )
    # Importante: mesmo tendo começado no `agente_triador`, `.final_output` aqui é a
    # resposta de quem de fato respondeu por último (o especialista, após o handoff).
    # Para descobrir QUEM respondeu, usa-se `resultado.last_agent.name` (não usado
    # nesta função, mas é o que a Seção 3 do deck destaca como o jeito de auditar
    # o roteiro sem escrever nenhum if/else).
    return resultado.final_output


if __name__ == "__main__":
    # Aceita a mensagem como argumentos de linha de comando ou via stdin
    if len(sys.argv) > 1:
        mensagem = " ".join(sys.argv[1:])
    else:
        try:
            mensagem = input("Pergunta: ")
        except EOFError:
            sys.exit(0)

    try:
        resposta = executar_agente_handoff(mensagem)
    except Exception as e:
        # Mostrar erro para diagnóstico rápido
        print(f"Erro ao executar agente_handoff: {e}")
        raise

    print(resposta)
