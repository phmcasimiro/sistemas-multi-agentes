# agente5.py — Seção 2 do deck: "usar ferramentas" (exercício 2.4 — ViaCEP com retorno em texto estruturado)
#
# Conceito central: ferramentas conectam o agente a serviços públicos externos.
# Neste exercício, conectamos o agente à API do ViaCEP para busca de endereços.
# Ponto de atenção (a "pegadinha" da ViaCEP): quando o CEP é inexistente, a API devolve
# status HTTP 200, mas com o corpo JSON `{"erro": "true"}` (ou `{"erro": true}`).
# Uma ferramenta bem implementada deve tratar essa condição e levantar uma exceção
# informativa (`ValueError`), permitindo ao modelo de linguagem explicar a situação ao usuário.

import os
import re
import sys

# Coloca a raiz do curso no sys.path para importar provedor (e o .env) de qualquer aula.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import requests
from agents import Agent, function_tool
from provedor import configurar, modelo, rodar

# 1. Inicializa o provedor configurado no .env (Zen/Ollama/OpenAI).
configurar()


# 2. Definição da ferramenta com tratamento de erro sem HTTP error
@function_tool
def consultar_cep(cep: str) -> str:
    """Consulta o endereço completo associado a um CEP brasileiro via API ViaCEP.

    Args:
        cep: Código Postal brasileiro com 8 dígitos, com ou sem hífen (ex.: '70040-010' ou '70040010').
    """
    # Limpa caracteres não numéricos do CEP
    cep_limpo = re.sub(r"\D", "", cep)
    if len(cep_limpo) != 8:
        raise ValueError(f"CEP inválido: '{cep}'. Um CEP brasileiro deve conter exatamente 8 dígitos numéricos.")

    print(f"\n[TOOL EXECUTADA] Consultando CEP {cep_limpo} na ViaCEP...")

    url = f"https://viacep.com.br/ws/{cep_limpo}/json/"
    resposta = requests.get(url, timeout=10)

    # Verifica se houve erro HTTP na requisição
    if resposta.status_code != 200:
        raise ValueError(f"Falha na comunicação com a API ViaCEP: status {resposta.status_code}")

    dados = resposta.json()

    # Pegadinha da ViaCEP: CEP inexistente retorna HTTP 200 com {'erro': 'true'} ou {'erro': True}
    if dados.get("erro") in [True, "true"]:
        raise ValueError(f"CEP não encontrado na base de dados dos Correios: {cep}")

    logradouro = dados.get("logradouro", "Não informado")
    bairro = dados.get("bairro", "Não informado")
    localidade = dados.get("localidade", "Não informada")
    uf = dados.get("uf", "UF não informada")
    complemento = dados.get("complemento", "")
    comp_str = f" ({complemento})" if complemento else ""

    # Retorna o endereço estruturado em texto para o LLM formular a resposta final
    return (
        f"Logradouro: {logradouro}{comp_str} | "
        f"Bairro: {bairro} | "
        f"Cidade: {localidade} - {uf} | "
        f"CEP: {dados.get('cep', cep_limpo)}"
    )


# 3. Fábrica do agente
def criar_agente() -> Agent:
    return Agent(
        name="Especialista em Endereços",
        instructions=(
            "Você é um assistente prestativo especializado em localização e consulta de CEPs brasileiros. "
            "Sempre utilize a ferramenta 'consultar_cep' para validar e consultar CEPs informados pelo usuário. "
            "Apresente os dados retornados de maneira clara e natural."
        ),
        model=modelo(),
        tools=[consultar_cep],
    )


# 4. Ponto de entrada
def main():
    print(f"🤖 Agente ativo: {criar_agente().name}")
    print(f"Modelo ativo: {modelo()}\n")

    # Exemplo 1: CEP válido
    pergunta = "Qual é o endereço referente ao CEP 70040-010?"
    print(f"Usuário: {pergunta}")
    resultado = rodar(criar_agente, pergunta)
    print(f"\nResposta do Agente:\n{resultado.final_output}\n")


if __name__ == "__main__":
    main()
