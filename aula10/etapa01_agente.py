"""
ETAPA 1 -- Primeiro agente com tool local (15 min).

ESQUELETO: implemente as etapas na ordem. Cada uma está marcada com um comentário e um
raise NotImplementedError: troque esse raise pelo código da etapa e rode o arquivo.
  ETAPA 1.1 -- a tool consultar_servidor (SEM o salário)
  ETAPA 1.2 -- o agente AtendenteRH com a tool
  ETAPA 1.3 -- duas perguntas: uma que precisa da tool e uma que não precisa

REFERÊNCIAS NAS AULAS
  aula1/segundo_agente.py                            Agent + @function_tool + Runner.run_sync (o básico)
  exercicios_resolvidos/aula4/ex10_function_tool.py  tool que consulta uma TABELA e devolve JSON  <- o mais parecido
  aula8/exemplos/02_agente_tool/main.py              o agente decide quando chamar a tool (e quando não)

Rodar (a partir de aula10/):
    python etapa01_agente.py

Pronto quando: a tool é chamada só na primeira pergunta (o print dentro dela prova).
"""
import json

from agents import Agent, Runner, function_tool

from dados_rh import servidor_publico
from provedor import configurar

MODELO = configurar()  # LLM REAL: PROVEDOR no .env (openai ou ollama)


# ETAPA 1.1 -- a tool
#   - ponha um print("[tool] consultar_servidor", matricula) no começo, para provar quando ela roda;
#   - devolva json.dumps(servidor_publico(matricula), ensure_ascii=False). A consulta servidor_publico() (dados_rh.py)
#     já vem pronta: tira o salário (dado restrito, ver Etapas 5 e 9) e trata matrícula inexistente;
#   - capriche na DOCSTRING (com Args:): é o que o LLM lê para decidir chamar a tool. Esse é o ponto da etapa.
#   Referência: exercicios_resolvidos/aula4/ex10_function_tool.py (consultar_protocolo)
@function_tool
def consultar_servidor(matricula: str) -> str:
    """Consulta os dados cadastrais e funcionais de um servidor público pelo número da matrícula.

    Retorna informações como nome, cargo, equipe, saldo de férias e abonos restantes em formato JSON.
    Se a matrícula não existir, retorna mensagem informando que não foi encontrada.

    Args:
        matricula: A matrícula funcional do servidor (ex.: '1001', '1002').
    """
    print("[tool] consultar_servidor", matricula)
    return json.dumps(servidor_publico(matricula), ensure_ascii=False)


def criar_atendente() -> Agent:
    return Agent(
        name="AtendenteRH",
        instructions=(
            "Você é o Atendente de Recursos Humanos (RH). "
            "Responda às dúvidas dos servidores públicos em português e de forma breve e educada. "
            "Quando a pergunta for sobre dados cadastrais ou funcionais de um servidor específico "
            "(como saldo de férias, abonos, cargo ou equipe), utilize a ferramenta consultar_servidor "
            "informando a matrícula do servidor. "
            "Nunca invente saldos ou dados de cabeça; baseie-se estritamente nas informações da ferramenta. "
            "Para dúvidas conceituais, gerais ou sobre normas de RH (como explicar o que é abono pecuniário), "
            "responda diretamente de forma clara sem chamar nenhuma ferramenta."
        ),
        tools=[consultar_servidor],
    )


def main() -> None:
    atendente = criar_atendente()

    pergunta1 = "Quantos dias de férias a matrícula 1002 ainda tem?"
    resultado1 = Runner.run_sync(atendente, pergunta1)
    print(resultado1.final_output)

    pergunta2 = "O que é abono pecuniário?"
    resultado2 = Runner.run_sync(atendente, pergunta2)
    print(resultado2.final_output)


if __name__ == "__main__":
    print(f"[modelo] {MODELO}")
    main()
