# agente_investigacao.py — Seção 3 do deck: "encaminhar" (exercícios 3.4 e 3.5)
#
# Conceito central: Central de Apoio à Investigação (Polícia Judiciária / Segurança Pública).
# Implementa os exercícios 3.4 e 3.5:
#   - Exercício 3.4: dois especialistas:
#       1. Especialista Cadastral: consulta CNPJ via BrasilAPI (dados da Receita).
#       2. Especialista de Localização: geocodificação via OpenStreetMap Nominatim.
#          Atenção crítica: Nominatim exige header `User-Agent` identificando a aplicação;
#          sem esse cabeçalho, a requisição é rejeitada com HTTP 403 Forbidden.
#   - Exercício 3.5 ("O custo de um 3º especialista"):
#       3. Especialista de Telefonia: consulta DDD via BrasilAPI (https://brasilapi.com.br/api/ddd/v1/{ddd}).
#       Demonstração prática: para plugar esse 3º especialista na equipe, foram necessários
#       apenas 3 passos declarativos:
#         (1) a função/ferramenta `@function_tool`,
#         (2) a instância do `Agent` especialista,
#         (3) adicionar o agente na lista `handoffs=[...]` e uma frase na instrução do triador.
#       Nenhum `if/else` procedural foi escrito ou alterado.

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
# 1. Ferramenta Cadastral: CNPJ (BrasilAPI)
# ---------------------------------------------------------------------------
@function_tool
def consultar_cnpj(cnpj: str) -> str:
    """Consulta dados cadastrais de pessoa jurídica na Receita Federal via BrasilAPI.

    Args:
        cnpj: CNPJ de 14 dígitos (com ou sem pontuação).
    """
    cnpj_limpo = re.sub(r"\D", "", cnpj)
    if len(cnpj_limpo) != 14:
        raise ValueError(f"CNPJ inválido: '{cnpj}'. Deve conter exatamente 14 dígitos.")

    print(f"\n[TOOL CADASTRAL] Consultando CNPJ {cnpj_limpo}...")
    resposta = requests.get(f"https://brasilapi.com.br/api/cnpj/v1/{cnpj_limpo}", timeout=10)
    if resposta.status_code == 404:
        raise ValueError(f"CNPJ {cnpj} não encontrado.")
    if resposta.status_code != 200:
        raise ValueError(f"Erro na BrasilAPI (CNPJ): status {resposta.status_code}")

    d = resposta.json()
    qsa = d.get("qsa", [])
    socios = [f"{s.get('nome_socio')} ({s.get('qualificacao_socio')})" for s in qsa]
    socios_txt = ", ".join(socios) if socios else "Nenhum sócio listado"

    return (
        f"Razão Social: {d.get('razao_social')} | "
        f"Situação: {d.get('situacao_cadastral')} | "
        f"Município/UF: {d.get('municipio')}/{d.get('uf')} | "
        f"Sócios: [{socios_txt}] (CPFs mascarados na origem conforme LGPD)"
    )


# ---------------------------------------------------------------------------
# 2. Ferramenta de Georreferenciamento: Nominatim (OpenStreetMap)
# ---------------------------------------------------------------------------
@function_tool
def geocodificar_endereco(endereco: str) -> str:
    """Converte um endereço ou ponto de interesse em coordenadas geográficas (latitude e longitude)

    utilizando o serviço Nominatim (OpenStreetMap).

    Args:
        endereco: Nome da rua, praça ou ponto de referência (ex.: 'Praça dos Três Poderes, Brasília').
    """
    print(f"\n[TOOL GEOLOCALIZAÇÃO] Geocodificando endereço: '{endereco}'...")

    # Ponto de atenção exigido pelo Nominatim: User-Agent obrigatório para evitar bloqueio 403
    headers = {
        "User-Agent": "CursoPosGraduacaoSistemasMultiAgentes/1.0 (contato: aluno@posgraduacao.edu.br)"
    }
    url = "https://nominatim.openstreetmap.org/search"
    params = {"q": endereco, "format": "json", "limit": 1}

    resposta = requests.get(url, params=params, headers=headers, timeout=10)
    if resposta.status_code != 200:
        raise ValueError(f"Erro no serviço Nominatim: status {resposta.status_code}")

    resultados = resposta.json()
    if not resultados:
        raise ValueError(f"Endereço não localizado pelo Nominatim: {endereco}")

    primeiro = resultados[0]
    lat = primeiro.get("lat")
    lon = primeiro.get("lon")
    nome_completo = primeiro.get("display_name")

    return f"Endereço encontrado: {nome_completo} | Latitude: {lat} | Longitude: {lon}"


# ---------------------------------------------------------------------------
# 3. Ferramenta de Telefonia: DDD (BrasilAPI) — Exercício 3.5
# ---------------------------------------------------------------------------
@function_tool
def consultar_ddd(ddd: int) -> str:
    """Consulta o estado e os municípios atendidos por um código DDD no Brasil via BrasilAPI.

    Args:
        ddd: Número inteiro de 2 dígitos referente ao DDD (ex.: 61, 11, 41).
    """
    print(f"\n[TOOL TELEFONIA] Consultando DDD {ddd}...")
    url = f"https://brasilapi.com.br/api/ddd/v1/{ddd}"
    resposta = requests.get(url, timeout=10)

    if resposta.status_code == 404:
        raise ValueError(f"Código DDD {ddd} não encontrado ou inválido no Brasil.")
    if resposta.status_code != 200:
        raise ValueError(f"Erro na BrasilAPI (DDD): status {resposta.status_code}")

    dados = resposta.json()
    estado = dados.get("state", "N/D")
    cidades = dados.get("cities", [])
    amostra = ", ".join(cidades[:8])
    qtd = len(cidades)
    sufixo = f" e mais {qtd - 8} cidades" if qtd > 8 else ""

    return f"DDD: {ddd} | Estado correspondente: {estado} | Principais cidades ({qtd} atendidas): {amostra}{sufixo}"


# ---------------------------------------------------------------------------
# 4. Agentes Especialistas
# ---------------------------------------------------------------------------
agente_cadastral = Agent(
    name="Especialista_Cadastral",
    instructions=(
        "Você é um investigador perito em análise societária e cadastral de empresas. "
        "Use sempre 'consultar_cnpj' para obter a situação, razão social e quadro de sócios."
    ),
    model=modelo(),
    tools=[consultar_cnpj],
    handoff_description="Especialista em consulta de empresas, CNPJ, dados da Receita Federal e quadro societário (QSA).",
)

agente_localizacao = Agent(
    name="Especialista_Localizacao",
    instructions=(
        "Você é um especialista em inteligência geográfica e georreferenciamento de locais de interesse. "
        "Use a ferramenta 'geocodificar_endereco' para obter coordenadas exatas de endereços e pontos de interesse."
    ),
    model=modelo(),
    tools=[geocodificar_endereco],
    handoff_description="Especialista em geolocalização, obtenção de latitude/longitude e coordenadas de endereços via Nominatim.",
)

agente_telefonia = Agent(
    name="Especialista_Telefonia",
    instructions=(
        "Você é um perito em telecomunicações e inteligência de sinais/prefixos telefônicos. "
        "Use 'consultar_ddd' para mapear a área de cobertura e municípios vinculados a um DDD."
    ),
    model=modelo(),
    tools=[consultar_ddd],
    handoff_description="Especialista em códigos de DDD telefônico, regiões de telecomunicações e cidades vinculadas a prefixos.",
)

# ---------------------------------------------------------------------------
# 5. Triador de Apoio à Investigação (Orquestrador)
# ---------------------------------------------------------------------------
agente_triador_investigacao = Agent(
    name="Triador_Investigacao",
    instructions=(
        "Você é a mesa de triagem do Centro Integrado de Inteligência e Investigação. "
        "Analise a demanda investigativa e faça o encaminhamento sem tentar responder diretamente: "
        "- Se a solicitação mencionar CNPJ, pessoa jurídica, razão social ou sócios -> transfira para Especialista_Cadastral. "
        "- Se a solicitação mencionar coordenadas geográficas, mapas, latitude/longitude ou localização de endereço -> transfira para Especialista_Localizacao. "
        "- Se a solicitação mencionar código DDD, área de prefixo telefônico ou cobertura de telefonia -> transfira para Especialista_Telefonia. "
        "Encaminhe com rigor para a unidade especializada."
    ),
    model=modelo(),
    # Repare no exercício 3.5: adicionar o agente_telefonia exigiu apenas colocá-lo nesta lista
    handoffs=[agente_cadastral, agente_localizacao, agente_telefonia],
)


def executar_consulta_investigacao(demanda: str):
    print(f"\n{'=' * 70}")
    print(f"🔎 Demanda Operacional: \"{demanda}\"")
    resultado = Runner.run_sync(agente_triador_investigacao, demanda)
    agente_resp = getattr(resultado.last_agent, "name", "Desconhecido")
    print(f"👮 Especialista Acionado (Last Agent): {agente_resp}")
    print(f"📋 Parecer:\n{resultado.final_output}")
    print(f"{'=' * 70}")
    return resultado


def main():
    print(f"=== Central Integrada de Apoio à Investigação (Exercícios 3.4 & 3.5) ===")
    print(f"Modelo ativo: {modelo()}\n")

    # Demanda 1: Perícia Cadastral (Exercício 3.4)
    executar_consulta_investigacao("Verifique a razão social e sócios do CNPJ 00.000.000/0001-91.")

    # Demanda 2: Georreferenciamento de Local de Fato (Exercício 3.4)
    executar_consulta_investigacao("Obtenha as coordenadas geográficas da Praça dos Três Poderes em Brasília.")

    # Demanda 3: Inteligência Telefônica (Exercício 3.5 - 3º Especialista)
    executar_consulta_investigacao("Quais cidades e qual estado pertencem à cobertura do DDD 61?")


if __name__ == "__main__":
    main()
