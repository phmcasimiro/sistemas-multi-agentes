"""
ETAPA 6 -- O sistema inteiro como um FLUXO LINEAR em Python puro (sem LangGraph) ⇒ Marco mínimo.

ESQUELETO:
  ETAPA 6.3 -- analisar(): o Coordenador junta os pareceres (com os limites da Etapa 4.7)
  ETAPA 6.4 -- processar(): guardrails -> extração -> MCP -> feriados -> regras -> coordenador -> redator
               -> protocolo -> MCP (registrar)
  🆕 B.4    -- (OPCIONAL, bônus) testar_governanca(): os dois testes de bloqueio do --governanca

REFERÊNCIAS NAS AULAS
  aula6/exemplos/01_fluxo_linear/main.py     o fluxo linear: funciona, mas sem decisão nem volta (por isso a Etapa 7)
  aula4/ex03_agente_as_tool.py               o Coordenador com especialistas como tools
  aula7/exemplos/02_agentes_especializados/main.py   cada especialista imprime o que fez: dá para saber quem fez o quê

Rodar:
    python etapa06_linear.py                 # C1, C2, C6 e C11
    python etapa06_linear.py --governanca    # 🆕 B (opcional): os dois testes de bloqueio

Pronto quando: C1, C2 e C11 são gravados com protocolo, C6 vira indeferimento com sugestão de datas, e você sabe dizer
qual agente escreveu cada parte. (Opcional) no --governanca: a tool restrita NÃO executa e o C2 para no orçamento.
"""
import json
import os
import sys

from agents import RunHooks

import etapa06_agentes as agentes
from etapa05_cliente_mcp import chamar_mcp
from dados.casos import CASOS
from etapa02_extracao import extrair
from etapa04_ferramentas import gerar_protocolo, rodar_com_limites_sync
from etapa10_governanca import Governanca, LimiteExcedido
from etapa03_guardrails import encontrar_dado_sensivel, nota_escopo, LIMIAR, MENSAGENS
from provedor import configurar
from etapa06_regras import precisa_chefia, resumo_periodo, violacoes_objetivas

MODELO = configurar()


def analisar(pedido: dict, servidor: dict, periodo: dict, violacoes: list[str], hooks: RunHooks | None = None) -> str:
    coordenador = agentes.criar_coordenador(hooks=hooks)
    contexto = (
        f"Pedido recebido:\n{json.dumps(pedido, ensure_ascii=False, indent=2)}\n\n"
        f"Dados do servidor:\nMatrícula: {servidor.get('matricula')}, Nome: {servidor.get('nome')}, "
        f"Equipe: {servidor.get('equipe')}, Cargo: {servidor.get('cargo')}, Saldo Férias: {servidor.get('saldo_ferias_dias')}, "
        f"Abonos Restantes: {servidor.get('abonos_restantes')}\n\n"
        f"Resumo do período solicitado:\n{json.dumps(periodo, ensure_ascii=False, indent=2)}\n\n"
        f"Violações objetivas identificadas previamente:\n"
        + ("\n".join(f"- {v}" for v in violacoes) if violacoes else "Nenhuma violação objetiva encontrada.")
        + "\n\nPor favor, consulte os especialistas pertinentes e emita seu parecer consolidado."
    )
    resultado = rodar_com_limites_sync(coordenador, contexto, hooks=hooks)
    return resultado.final_output


def processar(texto: str, hooks: RunHooks | None = None) -> dict:
    print("\n[1/9] guardrails de entrada...")
    dado_sensivel = encontrar_dado_sensivel(texto)
    if dado_sensivel:
        return {"resultado": "bloqueado", "mensagem": MENSAGENS["dado_sensivel"]}
    nota, _ = nota_escopo(texto)
    if nota >= LIMIAR:
        return {"resultado": "bloqueado", "mensagem": MENSAGENS["fora_do_escopo"]}

    print("[2/9] extração estruturada...")
    pedido_obj = extrair(texto)
    pedido = pedido_obj.model_dump(mode="json")
    if not pedido.get("matricula") or not pedido.get("data_inicio") or not pedido.get("data_fim"):
        return {"resultado": "pedir_dados", "mensagem": "Matrícula ou datas não informadas no pedido."}

    print(f"[3/9] consultar servidor ({pedido['matricula']}) via MCP...")
    servidor = chamar_mcp("consultar_servidor", {"matricula": pedido["matricula"]})
    if not servidor or servidor.get("erro"):
        return {"resultado": "pedir_dados", "mensagem": f"Servidor não encontrado para a matrícula {pedido['matricula']}."}

    print("[4/9] resumo do período e feriados...")
    periodo = resumo_periodo(pedido["data_inicio"], pedido["data_fim"])

    print(f"[5/9] consultar escala ({servidor.get('equipe')}) e regras objetivas...")
    escala = chamar_mcp("consultar_escala", {
        "equipe": servidor.get("equipe", ""),
        "inicio": pedido["data_inicio"],
        "fim": pedido["data_fim"]
    })
    violacoes = violacoes_objetivas(pedido, servidor, periodo, escala)

    print("[6/9] análise técnica do coordenador com especialistas...")
    parecer = analisar(pedido, servidor, periodo, violacoes, hooks=hooks)

    print("[7/9] redação do despacho oficial...")
    prompt_redator = (
        f"Elabore o despacho administrativo com base nas seguintes informações:\n"
        f"- Pedido: {json.dumps(pedido, ensure_ascii=False)}\n"
        f"- Servidor: Matrícula {servidor.get('matricula')}, Nome {servidor.get('nome')}, Equipe {servidor.get('equipe')}\n"
        f"- Período: de {pedido['data_inicio']} a {pedido['data_fim']} (retorno: {periodo.get('retorno')})\n"
        f"- Decisão baseada nas regras: {'INDEFERIDO' if violacoes else 'DEFERIDO'}\n"
        f"- Violações objetivas: {violacoes if violacoes else 'Nenhuma'}\n"
        f"- Parecer dos especialistas:\n{parecer}\n"
    )
    despacho = rodar_com_limites_sync(agentes.criar_redator(), prompt_redator, hooks=hooks).final_output

    print("[8/9] geração de protocolo...")
    protocolo = gerar_protocolo(pedido["matricula"], pedido["tipo"], pedido["data_inicio"], pedido["data_fim"])

    print(f"[9/9] registro de decisão no MCP (protocolo {protocolo})...")
    decisao = "indeferido" if violacoes else "deferido"
    aprovador = "pendente_chefia" if precisa_chefia(pedido, violacoes) else "sistema"

    chamar_mcp("registrar_decisao", {
        "protocolo": protocolo,
        "matricula": pedido["matricula"],
        "tipo": pedido["tipo"],
        "inicio": pedido["data_inicio"],
        "fim": pedido["data_fim"],
        "decisao": decisao,
        "aprovador": aprovador,
        "despacho": despacho,
        "token": os.getenv("TOKEN_REGISTRO", ""),
    })

    return {
        "resultado": decisao,
        "protocolo": protocolo,
        "despacho": despacho,
        "parecer": parecer,
        "violacoes": violacoes,
        "aprovador": aprovador,
    }


def testar_governanca() -> None:
    print("\n--- Teste A: Coordenador tentando acessar tool restrita (consultar_remuneracao) ---")
    try:
        coordenador = agentes.criar_coordenador(hooks=Governanca(), tools_extras=[agentes.consultar_remuneracao])
        rodar_com_limites_sync(coordenador, "Qual o salário da matrícula 1002?", hooks=Governanca())
        print("FALHA: Deveria ter sido bloqueado!")
    except LimiteExcedido as e:
        print(f"[OK] Bloqueado com sucesso por Governança: {e}")

    print("\n--- Teste B: C2 com limite de ferramentas estourado (max_tools=1) ---")
    try:
        processar(CASOS["C2_ferias_com_venda"]["pedido"], hooks=Governanca(max_tools=1))
        print("FALHA: Deveria ter sido bloqueado por limite de tools!")
    except LimiteExcedido as e:
        print(f"[OK] Bloqueado com sucesso antes do segundo especialista: {e}")


if __name__ == "__main__":
    print(f"[modelo] {MODELO}")
    if "--governanca" in sys.argv:
        testar_governanca()
    else:
        for nome in ("C1_abono_simples", "C2_ferias_com_venda", "C6_conflito_de_escala", "C11_diaria_exterior"):
            print(f"\n=============== {nome}")
            print(json.dumps(processar(CASOS[nome]["pedido"]), ensure_ascii=False, indent=2))
