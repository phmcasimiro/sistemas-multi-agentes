# agente6.py — Seção 2 do deck: "usar ferramentas" (exercício 2.5 — CNPJ com BrasilAPI + LGPD)
#
# Conceito central: consulta de dados cadastrais públicos de pessoas jurídicas (Receita Federal)
# via BrasilAPI (https://brasilapi.com.br/api/cnpj/v1/{cnpj}).
#
# Ponto de LGPD: a minimização de dados acontece diretamente na origem (na própria API).
# Os CPFs dos sócios no Quadro de Sócios e Administradores (QSA) já retornam mascarados
# pela fonte pública (exemplo: ***123456**). O agente consome os dados sem necessidade
# de armazenar ou expor dados pessoais não mascarados, respeitando o princípio da minimização.

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


# 2. Definição da ferramenta com extração cadastral e foco em LGPD
@function_tool
def consultar_cnpj(cnpj: str) -> str:
    """Consulta dados cadastrais de uma empresa no Brasil pelo CNPJ utilizando a BrasilAPI.

    Retorna razão social, situação cadastral, atividade principal, endereço e quadro de sócios.

    Args:
        cnpj: Cadastro Nacional da Pessoa Jurídica com 14 dígitos (com ou sem pontuação).
    """
    cnpj_limpo = re.sub(r"\D", "", cnpj)
    if len(cnpj_limpo) != 14:
        raise ValueError(f"CNPJ inválido: '{cnpj}'. Um CNPJ deve conter exatamente 14 dígitos numéricos.")

    print(f"\n[TOOL EXECUTADA] Consultando CNPJ {cnpj_limpo} na BrasilAPI...")

    url = f"https://brasilapi.com.br/api/cnpj/v1/{cnpj_limpo}"
    resposta = requests.get(url, timeout=10)

    if resposta.status_code == 404:
        raise ValueError(f"CNPJ não encontrado na base da Receita Federal: {cnpj}")
    if resposta.status_code != 200:
        raise ValueError(f"Falha na comunicação com a BrasilAPI: status {resposta.status_code}")

    dados = resposta.json()

    razao_social = dados.get("razao_social", "Não informada")
    nome_fantasia = dados.get("nome_fantasia") or "Não informado"
    situacao = dados.get("situacao_cadastral", "Não informada")
    atividade = dados.get("cnae_fiscal_descricao", "Não informada")

    logradouro = dados.get("logradouro", "")
    numero = dados.get("numero", "")
    bairro = dados.get("bairro", "")
    municipio = dados.get("municipio", "")
    uf = dados.get("uf", "")
    cep = dados.get("cep", "")
    endereco = f"{logradouro}, {numero} - {bairro}, {municipio}/{uf} (CEP: {cep})".strip()

    # Quadro de Sócios e Administradores (QSA)
    qsa_lista = dados.get("qsa", [])
    socios_formatados = []
    for s in qsa_lista:
        nome_socio = s.get("nome_socio", "Nome não informado")
        qualificacao = s.get("qualificacao_socio", "Qualificação não informada")
        cpf_mascarado = s.get("cpf_representante_legal") or s.get("cnpj_cpf_do_socio") or "N/D"
        socios_formatados.append(f"{nome_socio} ({qualificacao}) - CPF/Doc: {cpf_mascarado}")

    qsa_str = "; ".join(socios_formatados) if socios_formatados else "Nenhum sócio informado"

    return (
        f"Razão Social: {razao_social} | Nome Fantasia: {nome_fantasia} | "
        f"Situação Cadastral: {situacao} | Atividade Principal: {atividade} | "
        f"Endereço: {endereco} | Quadro de Sócios (QSA): [{qsa_str}] "
        f"(Nota LGPD: CPFs mascarados na origem pela BrasilAPI)"
    )


# 3. Fábrica do agente
def criar_agente() -> Agent:
    return Agent(
        name="Analista Cadastral e LGPD",
        instructions=(
            "Você é um assistente de inteligência cadastral e conformidade com a LGPD. "
            "Ao ser solicitado sobre dados de pessoas jurídicas ou empresas, utilize a ferramenta 'consultar_cnpj'. "
            "Apresente os dados da empresa de forma organizada (Razão Social, Situação, Atividade, Endereço e Sócios). "
            "Destaque sempre que os dados respeitam o princípio de minimização de dados da LGPD."
        ),
        model=modelo(),
        tools=[consultar_cnpj],
    )


# 4. Ponto de entrada
def main():
    print(f"🤖 Agente ativo: {criar_agente().name}")
    print(f"Modelo ativo: {modelo()}\n")

    # Exemplo com CNPJ de teste (Banco do Brasil)
    pergunta = "Poderia consultar os dados da empresa com CNPJ 00.000.000/0001-91?"
    print(f"Usuário: {pergunta}")
    resultado = rodar(criar_agente, pergunta)
    print(f"\nResposta do Agente:\n{resultado.final_output}\n")


if __name__ == "__main__":
    main()
