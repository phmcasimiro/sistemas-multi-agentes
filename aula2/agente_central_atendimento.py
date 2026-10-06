# agente_central_atendimento.py — Seção 3 do deck: "encaminhar" (exercício 3.3)
#
# Conceito central: Central de Atendimento ao Cidadão combinando Handoff e Tools reais.
# Temos dois agentes especialistas, cada um com sua ferramenta de API externa:
#   1. Agente do Clima: consulta a API pública Open-Meteo.
#   2. Agente de Endereços: consulta a API pública ViaCEP.
#
# O Agente Triador não possui ferramentas de consulta direta; ele avalia o pedido em linguagem
# natural e delega o turno para o especialista adequado via `handoffs=[...]`.
# O modelo toma duas decisões autônomas e independentes:
#   - Decisão 1 (Triador): para qual especialista transferir o turno (handoff).
#   - Decisão 2 (Especialista): acionar a sua ferramenta e formular a resposta final.

import os
import re
import sys

# Coloca a raiz do curso no sys.path para importar provedor (e o .env) de qualquer aula.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import requests
from agents import Agent, Runner, function_tool
from provedor import configurar, modelo

configurar()


# ---------------------------------------------------------------------------
# 1. Ferramenta de Clima (Open-Meteo)
# ---------------------------------------------------------------------------
@function_tool
def get_temperatura(cidade: str) -> str:
    """Consulta a temperatura atual (°C) de uma cidade utilizando a API Open-Meteo.

    Args:
        cidade: Nome da cidade (ex.: 'Brasília', 'Curitiba').
    """
    print(f"\n[TOOL CLIMA] Consultando clima para '{cidade}'...")
    geo = requests.get(
        "https://geocoding-api.open-meteo.com/v1/search",
        params={"name": cidade, "count": 1, "language": "pt", "format": "json"},
        timeout=10,
    ).json()

    if not geo.get("results"):
        raise ValueError(f"Cidade não encontrada: {cidade}")

    local = geo["results"][0]
    lat, lon = local["latitude"], local["longitude"]
    nome_oficial = f"{local.get('name', cidade)}, {local.get('admin1', '')} - {local.get('country', '')}"

    prev = requests.get(
        "https://api.open-meteo.com/v1/forecast",
        params={"latitude": lat, "longitude": lon, "current": "temperature_2m", "timezone": "auto"},
        timeout=10,
    ).json()

    temp = prev.get("current", {}).get("temperature_2m")
    return f"Local: {nome_oficial} | Temperatura atual: {temp}°C"


# ---------------------------------------------------------------------------
# 2. Ferramenta de Endereço (ViaCEP)
# ---------------------------------------------------------------------------
@function_tool
def consultar_cep(cep: str) -> str:
    """Consulta o endereço correspondente a um CEP brasileiro via ViaCEP.

    Args:
        cep: CEP com 8 dígitos numéricos (com ou sem hífen).
    """
    cep_limpo = re.sub(r"\D", "", cep)
    if len(cep_limpo) != 8:
        raise ValueError(f"CEP inválido: '{cep}'. Deve conter exatamente 8 dígitos.")

    print(f"\n[TOOL ENDEREÇOS] Consultando CEP {cep_limpo} no ViaCEP...")
    resposta = requests.get(f"https://viacep.com.br/ws/{cep_limpo}/json/", timeout=10)
    if resposta.status_code != 200:
        raise ValueError(f"Erro na API ViaCEP: status {resposta.status_code}")

    dados = resposta.json()
    if dados.get("erro") in [True, "true"]:
        raise ValueError(f"CEP não localizado: {cep}")

    return (
        f"Logradouro: {dados.get('logradouro', 'N/D')} | "
        f"Bairro: {dados.get('bairro', 'N/D')} | "
        f"Cidade/UF: {dados.get('localidade', 'N/D')}/{dados.get('uf', 'N/D')} | "
        f"CEP: {dados.get('cep', cep_limpo)}"
    )


# ---------------------------------------------------------------------------
# 3. Especialistas
# ---------------------------------------------------------------------------
agente_clima = Agent(
    name="Especialista_Clima",
    instructions=(
        "Você é um meteorologista prestativo. Use sempre a ferramenta 'get_temperatura' "
        "para consultar a previsão e informe a temperatura ao usuário de forma cordial."
    ),
    model=modelo(),
    tools=[get_temperatura],
    handoff_description="Especialista em meteorologia, previsão do tempo e temperatura de cidades.",
)

agente_enderecos = Agent(
    name="Especialista_Enderecos",
    instructions=(
        "Você é um especialista em logística e localização urbana brasileira. "
        "Use a ferramenta 'consultar_cep' para localizar endereços e detalhe rua, bairro e cidade."
    ),
    model=modelo(),
    tools=[consultar_cep],
    handoff_description="Especialista em busca de CEP, logradouros, bairros e endereços no Brasil.",
)

# ---------------------------------------------------------------------------
# 4. Agente Triador (Central de Atendimento)
# ---------------------------------------------------------------------------
agente_triador = Agent(
    name="Triador_Central_Atendimento",
    instructions=(
        "Você é a mesa de triagem da Central de Atendimento ao Cidadão. "
        "Sua função é identificar a necessidade do usuário e encaminhar a conversa: "
        "- Se for sobre clima, tempo ou temperatura, encaminhe para o Especialista_Clima. "
        "- Se for sobre CEP, ruas ou endereços, encaminhe para o Especialista_Enderecos. "
        "Não tente responder perguntas sobre esses temas por conta própria. "
        "Se for apenas uma saudação cordial (como 'Bom dia'), responda educadamente e pergunte como ajudar."
    ),
    model=modelo(),
    handoffs=[agente_clima, agente_enderecos],
)


def executar_atendimento(mensagem: str):
    print(f"\n{'─' * 60}")
    print(f"📥 Mensagem do Cidadão: \"{mensagem}\"")
    resultado = Runner.run_sync(agente_triador, mensagem)
    agente_final = getattr(resultado.last_agent, "name", "Desconhecido")
    print(f"🎯 Agente que respondeu final: {agente_final}")
    print(f"💬 Resposta:\n{resultado.final_output}")
    print(f"{'─' * 60}")
    return resultado


def main():
    print(f"=== Central de Atendimento ao Cidadão (Handoff + Tools Reais) ===")
    print(f"Modelo configurado: {modelo()}\n")

    # Caso 1: Pergunta sobre clima
    executar_atendimento("Qual a temperatura atual em Curitiba?")

    # Caso 2: Pergunta sobre endereço / CEP
    executar_atendimento("Poderia me informar o endereço do CEP 70040-010?")


if __name__ == "__main__":
    main()
