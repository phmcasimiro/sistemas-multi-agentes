"""
Desafio da Aula 7 -- parecer com aprovação humana condicionada ao risco.

Rodar, a partir de aula7/:
    python desafio\main.py
    python -m unittest desafio.test_desafio -v
"""
import sys
from pathlib import Path
from typing import TypedDict

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agents import Runner  # noqa: F401  (roda os agentes: Runner.run_sync(agente, entrada).final_output)
from langgraph.graph import END, START, StateGraph  # noqa: F401
from langgraph.types import Command, interrupt  # noqa: F401

import agentes  # noqa: F401  (os agentes prontos: investigador, classificador, redator, ...)
import prompts  # noqa: F401  (entradas dos agentes e nivel_de)
from caso import DENUNCIA_045, DENUNCIA_BAIXO_VALOR

MAX_TENTATIVAS = 3
FEEDBACK_PADRAO = "Faltam ações numeradas, responsáveis e prazos."


class Estado(TypedDict):
    solicitacao: str
    investigacao: str
    nivel_risco: str  # "alto" | "baixo"
    recomendacao: str
    aprovado: bool
    feedback_humano: str
    tentativas: int
    status: str  # "aprovada" | "aprovada_automaticamente" | "limite_de_revisoes"


def construir_grafo(checkpointer):
    """Monta o grafo (nós, roteadores e arestas) e devolve g.compile(checkpointer=checkpointer).

    Nós (nomes exatos, os testes conferem o caminho):
        receber, investigar, avaliar_risco, recomendar, validacao_humana, revisar, finalizar, encerrar

    O grafo a montar:

        START → receber → investigar → avaliar_risco ──"baixo"──────────────────┐
                                             │ "alto"                            │
                                             v                                   │
                                  ┌───> recomendar   (tentativas + 1;            │
                                  │          │        lê feedback_humano)        │
                                  │          v                                   │
                                  │   validacao_humana   <- interrupt(): PAUSA   │
                                  │          │                                   │
                                  │          ├── "aprovada" ──> finalizar <──────┘ ──> END
                                  │          ├── "desistir" ──> encerrar ──> END
                                  │          │                  (tentativas >= MAX_TENTATIVAS)
                                  │          └── "revisar"  ──┐
                                  │                           v
                                  └─────────────────────── revisar

    Roteadores (só LEEM o estado):
        após avaliar_risco    -> "baixo" | "alto"
        após validacao_humana -> "aprovada" | "revisar" | "desistir"

    Status final: finalizar -> "aprovada_automaticamente" (veio do risco baixo) ou "aprovada";
                  encerrar  -> "limite_de_revisoes".

    Como chamar os agentes (REAIS; já estão prontos em agentes.py, e as entradas em prompts.py):
        investigar     -> Runner.run_sync(agentes.investigador, estado["solicitacao"]).final_output
        avaliar_risco  -> entrada = prompts.entrada_classificar(estado["solicitacao"], estado["investigacao"])
                          texto = Runner.run_sync(agentes.classificador, entrada).final_output
                          nivel_risco = prompts.nivel_de(texto)      # "alto" | "baixo"
        recomendar     -> entrada = prompts.entrada_recomendar(estado["investigacao"], "", estado["nivel_risco"],
                                                               estado["feedback_humano"])
                          Runner.run_sync(agentes.redator, entrada).final_output

    Veja o enunciado em README.md e o exemplo 07 da aula.
    """
    def receber(estado):
        return {"solicitacao": estado["solicitacao"].strip(), "investigacao": "", "nivel_risco": "",
                "recomendacao": "", "aprovado": False, "feedback_humano": "", "tentativas": 0, "status": ""}

    def investigar(estado):
        return {"investigacao": Runner.run_sync(agentes.investigador, estado["solicitacao"]).final_output}

    def avaliar_risco(estado):
        entrada = prompts.entrada_classificar(estado["solicitacao"], estado["investigacao"])
        texto = Runner.run_sync(agentes.classificador, entrada).final_output
        return {"nivel_risco": prompts.nivel_de(texto)}

    def recomendar(estado):
        tentativa = estado["tentativas"] + 1
        entrada = prompts.entrada_recomendar(estado["investigacao"], "", estado["nivel_risco"],
                                             estado["feedback_humano"])
        recomendacao = Runner.run_sync(agentes.redator, entrada).final_output
        return {"recomendacao": recomendacao, "tentativas": tentativa}

    def validacao_humana(estado):
        linha = "=" * 60
        resumo = (
            f"{linha}\nANÁLISE PARA VALIDAÇÃO (versão {estado['tentativas']} de no máximo {MAX_TENTATIVAS})\n{linha}\n"
            f"Investigação  : {estado['investigacao']}\n"
            f"Nível de risco: {estado['nivel_risco']}\n"
            f"Recomendação  : {estado['recomendacao']}\n{linha}"
        )
        resposta = interrupt({"resumo": resumo, "pergunta": "Aprovar análise? [sim/não]"})
        return {"aprovado": resposta["aprovado"], "feedback_humano": resposta.get("feedback", "")}

    def revisar(estado):
        return {}

    def finalizar(estado):
        status = "aprovada_automaticamente" if estado["nivel_risco"] == "baixo" else "aprovada"
        return {"status": status}

    def encerrar(estado):
        return {"status": "limite_de_revisoes"}

    def rotear_apos_risco(estado):
        return estado["nivel_risco"]

    def rotear_apos_humano(estado):
        if estado["aprovado"]:
            return "aprovada"
        if estado["tentativas"] >= MAX_TENTATIVAS:
            return "desistir"
        return "revisar"

    g = StateGraph(Estado)
    for nome, funcao in [
        ("receber", receber), ("investigar", investigar), ("avaliar_risco", avaliar_risco),
        ("recomendar", recomendar), ("validacao_humana", validacao_humana), ("revisar", revisar),
        ("finalizar", finalizar), ("encerrar", encerrar),
    ]:
        g.add_node(nome, funcao)

    g.add_edge(START, "receber")
    g.add_edge("receber", "investigar")
    g.add_edge("investigar", "avaliar_risco")
    g.add_conditional_edges("avaliar_risco", rotear_apos_risco, {"baixo": "finalizar", "alto": "recomendar"})
    g.add_edge("recomendar", "validacao_humana")
    g.add_conditional_edges("validacao_humana", rotear_apos_humano,
                            {"aprovada": "finalizar", "revisar": "revisar", "desistir": "encerrar"})
    g.add_edge("revisar", "recomendar")
    g.add_edge("finalizar", END)
    g.add_edge("encerrar", END)
    return g.compile(checkpointer=checkpointer)


def executar(app, solicitacao: str, decisoes: list[str] | None = None, thread_id: str = "caso") -> tuple[dict, list[str]]:
    """Roda o grafo, responde cada pausa com a próxima decisão ("sim"/"nao") e devolve (estado_final, caminho)."""
    config = {"configurable": {"thread_id": thread_id}}
    decisoes = list(decisoes or [])
    caminho: list[str] = []
    entrada = {"solicitacao": solicitacao, "investigacao": "", "nivel_risco": "", "recomendacao": "", "aprovado": False,
               "feedback_humano": "", "tentativas": 0, "status": ""}
    while True:
        pausou = False
        for parte in app.stream(entrada, config, stream_mode="updates"):
            for no in parte:
                if no == "__interrupt__":
                    pausou = True
                else:
                    caminho.append(no)
        if not pausou:
            return app.get_state(config).values, caminho
        aprovado = (decisoes.pop(0) if decisoes else "nao") == "sim"
        entrada = Command(resume={"aprovado": aprovado, "feedback": "" if aprovado else FEEDBACK_PADRAO})


CASOS = [
    ("Caso 1: baixo valor (sem humano)", DENUNCIA_BAIXO_VALOR, []),
    ("Caso 2: alto risco, aprovado de primeira", DENUNCIA_045, ["sim"]),
    ("Caso 3: alto risco, rejeita 1x e aprova", DENUNCIA_045, ["nao", "sim"]),
    ("Caso 4: alto risco, rejeita sempre", DENUNCIA_045, ["nao", "nao", "nao"]),
]

if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from langgraph.checkpoint.memory import MemorySaver
    from provedor import configurar

    print(f"Modelo em uso: {configurar()}\n")  # LLM REAL: PROVEDOR no .env (openai ou ollama)
    for i, (titulo, texto, decisoes) in enumerate(CASOS):
        estado, caminho = executar(construir_grafo(MemorySaver()), texto, decisoes, f"caso-{i}")
        print(f"{titulo}\n  caminho: {' -> '.join(caminho)}\n  status={estado['status']} versões={estado['tentativas']}\n")
