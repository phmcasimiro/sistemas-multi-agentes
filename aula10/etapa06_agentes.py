"""
ETAPA 6 -- Os especialistas, cada um com UMA responsabilidade e SÓ as tools de que precisa.

ESQUELETO:
  ETAPA 6.1 -- criar_normas(), criar_escala(), criar_financeiro(), criar_redator()
  ETAPA 6.2 -- criar_coordenador(): usa Normas, Escala e Financeiro como TOOLS (as_tool)

As tools abaixo (PRONTAS) só repassam a chamada ao MCP Server do RH (cliente_mcp.chamar_mcp_async). Dar a cada agente
só as tools dele é o PRIVILÉGIO MÍNIMO (Etapa 9.1); o hook do 🆕 B (etapa10_governanca.py) confere isso em tempo de execução.

REFERÊNCIAS NAS AULAS
  aula4/ex03_agente_as_tool.py                         Coordenador que chama especialistas como tools    <- o mais parecido
  aula2/agente_handoff2.py                             as_tool com tool_name e tool_description
  aula4/ex02_handoff_roteamento.py                     handoff: compare (quem responde no fim?)
  aula7/exemplos/02_agentes_especializados/main.py     uma responsabilidade por agente
  aula7/agentes.py                                     ModelSettings(temperature=0) para respostas mais estáveis
  aula8/exemplos/06_excessive_agency/1_codigo_pronto/main.py   o problema de dar tools DEMAIS a um agente
"""
import json

from agents import Agent, ModelSettings, RunHooks, function_tool

from etapa05_cliente_mcp import chamar_mcp_async
from etapa04_ferramentas import cotacao_usd_brl

CONFIG = ModelSettings(temperature=0)


# ------------------------------------------------------------------ tools (PRONTAS)
@function_tool
async def consultar_normas(tema: str) -> str:
    """Regras da norma interna sobre um tema: férias, prazos, escala, abono, diária, aprovação, saúde ou dados."""
    return json.dumps(await chamar_mcp_async("consultar_normas", {"tema": tema}), ensure_ascii=False)


@function_tool
async def consultar_escala(equipe: str, inicio: str, fim: str) -> str:
    """Afastamentos da equipe que se sobrepõem ao período (AAAA-MM-DD) e o limite de afastados da regra N5."""
    return json.dumps(await chamar_mcp_async("consultar_escala", {"equipe": equipe, "inicio": inicio, "fim": fim}),
                      ensure_ascii=False)


@function_tool
async def tabela_diarias(tipo_destino: str) -> str:
    """Moeda e valor da diária para o tipo de destino: capital, interior ou exterior."""
    return json.dumps(await chamar_mcp_async("tabela_diarias", {"tipo_destino": tipo_destino}), ensure_ascii=False)


@function_tool
async def consultar_remuneracao(matricula: str) -> str:
    """[RESTRITA] Salário-base de um servidor. Só para calcular a venda de férias (N2)."""
    print(f"[tool] consultar_remuneracao({matricula}) EXECUTOU")  # o 🆕 B prova que, barrada, ela NÃO executa
    return json.dumps(await chamar_mcp_async("consultar_remuneracao", {"matricula": matricula}), ensure_ascii=False)


@function_tool
def cotacao_dolar() -> str:
    """Cotação atual do dólar em reais (USD->BRL). Devolve 'indisponível' se a API falhar: nunca invente o câmbio."""
    cotacao = cotacao_usd_brl()
    return f"{cotacao:.4f}" if cotacao else "indisponível"


# ------------------------------------------------------------------ ETAPA 6.1: especialistas
def criar_normas() -> Agent:
    return Agent(
        name="Normas",
        instructions=(
            "Você é o especialista em normas e regras internas do RH.\n"
            "Sua responsabilidade é explicar quais regras da norma se aplicam ao pedido recebido "
            "(como N1 a N10) e esclarecer eventuais violações objetivas apontadas, em linguagem simples e clara.\n"
            "Use a ferramenta `consultar_normas` para consultar as regras pelo tema.\n"
            "NÃO calcula valores nem consulta a escala de pessoal."
        ),
        tools=[consultar_normas],
        model_settings=CONFIG,
    )


def criar_escala() -> Agent:
    return Agent(
        name="Escala",
        instructions=(
            "Você é o especialista em escala de trabalho e controle de afastamentos simultâneos da equipe.\n"
            "Sua responsabilidade é consultar a escala da equipe usando a ferramenta `consultar_escala` e "
            "verificar se o pedido cumpre a regra N5 (limite de afastados simultâneos na equipe).\n"
            "Se houver conflito de escala ou excesso de afastamentos, informe o conflito e SUGIRA outro período "
            "com a mesma quantidade de dias, iniciando em um dia permitido (que não seja sexta-feira, sábado, "
            "domingo ou véspera de feriado, conforme a regra N3)."
        ),
        tools=[consultar_escala],
        model_settings=CONFIG,
    )


def criar_financeiro() -> Agent:
    return Agent(
        name="Financeiro",
        instructions=(
            "Você é o especialista financeiro de RH.\n"
            "Sua responsabilidade é calcular os impactos financeiros do pedido:\n"
            "1. Venda de férias (abono pecuniário, N2): consulte o salário com `consultar_remuneracao` "
            "e calcule: dias_vendidos * salario_base / 30.\n"
            "2. Diárias (N7): consulte o valor e moeda da diária com `tabela_diarias`. Calcule uma diária por "
            "pernoite completo mais meia diária (0.5) no dia de retorno. Se o destino for no exterior, consulte "
            "`cotacao_dolar` para converter USD para BRL. Se a cotação estiver indisponível, informe o total em "
            "USD e anote 'câmbio a calcular na liquidação'.\n"
            "Sempre mostre a memória de cálculo. Você é o ÚNICO agente autorizado a consultar remuneração."
        ),
        tools=[tabela_diarias, consultar_remuneracao, cotacao_dolar],
        model_settings=CONFIG,
    )


def criar_redator() -> Agent:
    return Agent(
        name="Redator",
        instructions=(
            "Você é o redator oficial do RH encarregado de emitir o DESPACHO administrativo.\n"
            "Escreva um despacho formal e conclusivo (deferimento ou indeferimento) usando EXCLUSIVAMENTE os fatos recebidos:\n"
            "- Matrícula do servidor\n"
            "- Tipo de pedido e período solicitado\n"
            "- Decisão final (DEFERIDO ou INDEFERIDO)\n"
            "- Regras citadas e fundamentação técnica dos especialistas\n"
            "- Valores e memórias de cálculo apurados (se houver)\n"
            "- Em caso de indeferimento, inclua a justificativa clara e a sugestão de datas alternativas fornecida pela escala.\n"
            "ATENÇÃO: NUNCA mencione CPF nem dados médicos/diagnósticos/CID (regra N10). "
            "Se receber feedback de revisão, corrija pontualmente o texto mantendo a formalidade."
        ),
        tools=[],
        model_settings=CONFIG,
    )


# ------------------------------------------------------------------ ETAPA 6.2: coordenador
def criar_coordenador(hooks: RunHooks | None = None, tools_extras: list | None = None) -> Agent:
    tools = [
        criar_normas().as_tool(
            tool_name="parecer_normas",
            tool_description="Obtém o parecer do especialista em normas sobre as regras aplicáveis e violações do pedido.",
            hooks=hooks,
            failure_error_function=None,
        ),
        criar_escala().as_tool(
            tool_name="parecer_escala",
            tool_description="Obtém o parecer do especialista em escala sobre afastamentos da equipe e sugestão de novo período em caso de conflito.",
            hooks=hooks,
            failure_error_function=None,
        ),
        criar_financeiro().as_tool(
            tool_name="parecer_financeiro",
            tool_description="Obtém o parecer do especialista financeiro calculando venda de férias ou diárias de viagem.",
            hooks=hooks,
            failure_error_function=None,
        ),
        *(tools_extras or []),
    ]

    return Agent(
        name="Coordenador",
        instructions=(
            "Você é o Coordenador de Atendimento de RH.\n"
            "Sua responsabilidade é avaliar o pedido do servidor e consultar os especialistas necessários através das suas tools:\n"
            "- Consulte `parecer_normas` para entender as regras aplicáveis e fundamentar o caso.\n"
            "- Consulte `parecer_escala` para pedidos de férias ou abono que impactem a escala de serviço.\n"
            "- Consulte `parecer_financeiro` APENAS quando houver impacto financeiro (ex.: venda de férias com dias_vendidos > 0, ou diárias). Pedidos de abono simples NÃO necessitam do financeiro.\n"
            "Consolide todos os pareceres em uma análise técnica coordenada e conclusiva."
        ),
        tools=tools,
        model_settings=CONFIG,
    )
