"""
Exemplo 03 -- ESTADO COMPARTILHADO (e a diferença entre ESTADO e MEMÓRIA).

No exemplo 02 passávamos o resultado de um especialista para o outro na mão.
Agora existe UM dicionário tipado, o Estado, que todos leem e no qual cada um
escreve APENAS o que é sua responsabilidade (exatamente como na Aula 6):

                    ESTADO
                       |
                 INVESTIGADOR  -> escreve  investigacao
                       |
                   JURÍDICO    -> escreve  analise_juridica
                       |
                   ANALISTA    -> escreve  analise_risco, recomendacao
                       |
                 ESTADO FINAL

Cada especialista é uma função  estado -> atualização do estado, e por dentro roda um Agent
(os agentes já vêm prontos em agentes.py). Nenhum especialista chama outro; ninguém passa
strings "à mão". Ainda é Python puro: o "motor" que junta as atualizações são 3 linhas (veja executar()).

ESTADO x MEMÓRIA  (não são sinônimos)

    ESTADO   o que a execução ATUAL precisa: solicitacao, investigacao, ...
             nasce com a execução e é o "caderno de rascunho" dos especialistas.
    MEMÓRIA  o que sobrevive à execução e pode ser reaproveitado depois:
             histórico de análises, decisões anteriores, preferências.

Ao final deste exemplo rodamos DUAS solicitações: o estado é recriado do zero
a cada execução; a memória (uma lista) continua crescendo.

Rodar (LLM REAL: configure o .env; veja o README), a partir de aula7/:
    python exemplos\\03_estado_compartilhado\\main.py
"""
import sys
from pathlib import Path
from typing import TypedDict

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from agents import Runner

import agentes
import prompts
from caso import DENUNCIA_045, DENUNCIA_051
from provedor import configurar

MODELO = configurar()  # LLM REAL: PROVEDOR no .env (openai ou ollama)


class Estado(TypedDict):
    solicitacao: str
    investigacao: str
    analise_juridica: str
    analise_risco: str
    recomendacao: str


def investigador(estado: Estado) -> dict:
    print("[INVESTIGADOR] lê: solicitacao")
    fatos = Runner.run_sync(agentes.investigador, estado["solicitacao"]).final_output
    return {"investigacao": fatos}  # só o que é dele


def juridico(estado: Estado) -> dict:
    print("[JURÍDICO]     lê: investigacao")
    texto = Runner.run_sync(agentes.juridico, estado["investigacao"]).final_output
    return {"analise_juridica": texto}


def analista(estado: Estado) -> dict:
    print("[ANALISTA]     lê: investigacao, analise_juridica")
    fatos, enquadramento = estado["investigacao"], estado["analise_juridica"]
    risco = Runner.run_sync(agentes.risco, prompts.entrada_risco(fatos, enquadramento)).final_output
    recomendacao = Runner.run_sync(
        agentes.redator, prompts.entrada_recomendar(fatos, enquadramento, risco)).final_output
    return {"analise_risco": risco, "recomendacao": recomendacao}


ESPECIALISTAS = [investigador, juridico, analista]

# MEMÓRIA: vive fora de qualquer execução (aqui, uma lista em memória do processo;
# em um sistema real seria um banco, arquivo ou serviço).
memoria: list[dict] = []


def executar(solicitacao: str) -> Estado:
    estado: Estado = {  # ESTADO: nasce novo a cada execução
        "solicitacao": solicitacao,
        "investigacao": "",
        "analise_juridica": "",
        "analise_risco": "",
        "recomendacao": "",
    }
    for especialista in ESPECIALISTAS:
        estado.update(especialista(estado))  # o motor: aplica a atualização ao estado
    memoria.append({"solicitacao": solicitacao, "risco": estado["analise_risco"]})
    return estado


if __name__ == "__main__":
    print(f"Modelo em uso: {MODELO}\n")

    estado = executar(DENUNCIA_045)
    print("\nESTADO FINAL:")
    for campo, valor in estado.items():
        print(f"  {campo:17}: {valor}")

    print("\n--- segunda execução: o ESTADO recomeça vazio; a MEMÓRIA continua ---")
    executar(DENUNCIA_051)
    print("\nMEMÓRIA (histórico de análises):")
    for i, item in enumerate(memoria, start=1):
        print(f"  {i}. {item['solicitacao']} -> {item['risco']}")
