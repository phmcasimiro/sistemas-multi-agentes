# Aula 1 — Fundamentos de Agentes e Ferramentas

**Conceito Central:** Aprender a diferença entre LLM (função de predição) e Agente (sistema autônomo com estado, objetivos e capacidade de atuar). Introdução ao SDK `openai-agents` e ao padrão de *function tools* para integração com ferramentas externas.

---

## 🎯 Objetivos da Aula

- Entender a diferença fundamental entre **LLM** (stateless, texto→texto) e **Agente** (stateful, com laço de ação)
- Usar o SDK `openai-agents` para criar agentes simples
- Implementar **@function_tool** para expor funções Python como ferramentas JSON Schema
- Validar saídas com **output_type** (Pydantic)
- Usar a abstração **provedor.py** para suportar múltiplos provedores (OpenAI, Ollama, Zen)
- Integrar com APIs externas (ViaCEP, BrasilAPI, Receita Federal) com tratamento de erro e conformidade LGPD

---

## 📊 Arquitetura Aula 1

```
┌──────────────────────────────────────┐
│      Prompt + Setup do Agente        │
│  (instrução, ferramentas, modelo)    │
└────────────┬─────────────────────────┘
             │
             ▼
    ┌────────────────────────┐
    │  openai-agents SDK     │
    │  (Agent + Runner)      │
    └────────┬───────────────┘
             │
    ┌────────▼───────────────────┐
    │  Seleção de Ferramenta    │
    │  (LLM decide qual usar)   │
    └────────┬───────────────────┘
             │
    ┌────────▼─────────────────────────────┐
    │  @function_tool (Validação)          │
    │  Conversão: Python → JSON Schema     │
    │  Execução: Resultado tipado          │
    └────────┬─────────────────────────────┘
             │
    ┌────────▼─────────────────────────────┐
    │  Reavaliação LLM                     │
    │  (loop continua até objetivo)        │
    └─────────────────────────────────────┘
```

---

## 🛠️ Ferramentas Utilizadas

### openai-agents SDK

**O que é:**
- SDK oficial do OpenAI para criar agentes autônomos
- Componentes: `Agent` (especialista), `Runner` (motor de execução)
- Suporta function tools, structured output, handoffs

**Características:**
- Execução síncrona e assíncrona (`Runner.run()` vs `Runner.run_async()`)
- Integração nativa com ferramentas (schema automático)
- Suporte a Handoffs (transferência entre agentes)

### @function_tool (Decorador)

**O que é:**
Anotação Python que transforma funções normais em especificações JSON Schema consumíveis pelo LLM.

**Exemplo:**
```python
from openai_agents import function_tool
import inspect

@function_tool
def consultar_cep(cep: str) -> dict:
    """
    Busca informações de um CEP usando a API ViaCEP.
    
    Args:
        cep: CEP no formato 12345-678 ou 12345678
    
    Returns:
        Dicionário com endereço completo
    """
    # Implementação
```

**Benefícios:**
- Tipagem automática (str, int, float, dict)
- Docstring se torna descrição JSON
- Validação de entrada automática
- Serialização/desserialização transparente

### output_type (Validação Pydantic)

**O que é:**
Contrato Pydantic que força a saída do modelo a seguir schema específico.

**Exemplo:**
```python
from pydantic import BaseModel

class RespostaCEP(BaseModel):
    cep: str
    endereco: str
    bairro: str
    cidade: str
    estado: str

# Garantir que o LLM responda nesse formato
resultado = modelo.generate(prompt, output_type=RespostaCEP)
# Automaticamente: JSON → validação → RespostaCEP instância
```

**Vantagem:**
Evita alucinações e garante contrato estruturado cliente-servidor.

---

## 📁 Estrutura de Arquivos

```
aula1/
├── README.md                    ← Este arquivo
├── agente1.py                   ← Agente básico (sem ferramentas)
├── agente2.py                   ← Agente com @function_tool simples
├── agente3.py                   ← Múltiplas ferramentas
├── agente4.py                   ← ViaCEP (CEP → Endereço)
├── agente5.py                   ← BrasilAPI (dados públicos)
├── agente6.py                   ← Receita Federal (conformidade LGPD)
├── agente1_gemini.py            ← Variante com Google Gemini
└── aula1.md                     ← Notas da aula (teóricas)
```

---

## 🚀 Como Rodar

### Prerequisitos

```bash
# Ativar venv
cd ~/Documentos/pos_graduacao/11_Sistem_MultiAgentes
source venv/bin/activate

# Configurar .env
cat > .env << EOF
PROVIDER=openai  # ou "ollama"
OPENAI_API_KEY=sk-...  # (se openai)
OPENAI_DEFAULT_MODEL=gpt-4o-mini
OLLAMA_MODEL=llama3.1  # (se ollama)
EOF

# Instalar dependências
pip install -r requirements.txt
```

### Teste Rápido (Agente Básico)

```bash
cd aula1
python agente1.py
```

**Saída esperada:**
```
[Agent responde com o resultado da consulta]
```

### Teste com ViaCEP (Ferramenta Real)

```bash
python agente4.py
# Prompt: "Qual é o endereço do CEP 01310-100?"
```

**Saída esperada:**
```
O CEP 01310-100 corresponde a:
Logradouro: Avenida Paulista
Bairro: Bela Vista
Cidade: São Paulo
Estado: SP
```

---

## 📝 Conceitos-Chave

### LLM vs Agente

| Aspecto | LLM | Agente |
|---------|-----|--------|
| **Definição** | Função probabilística: tokens → tokens | Sistema autônomo com loop de ação |
| **Estado** | Nenhum (stateless) | Persistente (stateful) |
| **Memória** | Histórico no prompt (token-limitado) | Armazenamento estruturado |
| **Ação** | Gera texto | Executa ferramentas, modifica ambiente |
| **Decisão** | Token de maior probabilidade | Raciocínio estruturado + ação |

### Padrão ReAct

O agente segue ciclo de Reasoning + Acting:

```
1. Observação   → Ler entrada/estado
2. Raciocínio   → LLM pensa sobre o problema
3. Ação         → Chamar ferramenta ou responder
4. Avaliação    → Reavaliação (volta ao passo 1 se necessário)
```

### Validação em Camadas

1. **Input:** Tipagem Python (str, int, etc)
2. **Schema JSON:** Exposição ao LLM
3. **Execution:** Chamada real com retry
4. **Output:** Tipagem Pydantic (BaseModel)

---

## 🔌 Integração com APIs Externas

### ViaCEP (CEP → Endereço)

```python
import requests

@function_tool
def buscar_endereco_cep(cep: str) -> dict:
    """Busca endereço completo a partir de um CEP"""
    cep_limpo = cep.replace("-", "")
    resp = requests.get(f"https://viacep.com.br/ws/{cep_limpo}/json/")
    if resp.status_code != 200:
        return {"erro": f"CEP {cep} não encontrado"}
    return resp.json()
```

**Endpoint:** `https://viacep.com.br/ws/{cep}/json/`  
**Resposta:** Logradouro, número, complemento, bairro, cidade, estado  
**Rate limit:** ~240 req/por min por IP

### BrasilAPI (Dados Públicos)

```python
@function_tool
def consultar_cnpj(cnpj: str) -> dict:
    """Consulta dados públicos de CNPJ via BrasilAPI"""
    resp = requests.get(f"https://brasilapi.com.br/api/cnpj/v1/{cnpj}")
    if resp.status_code != 200:
        return {"erro": "CNPJ não encontrado"}
    return resp.json()
```

**Endpoints disponíveis:** CNPJ, CPF, Banco, Feriados, DDD, ISP  
**Sem autenticação:** Público  
**Rate limit:** 2 req/seg

### Receita Federal (LGPD Conformance)

```python
@function_tool
def consultar_receita(cnpj: str) -> dict:
    """
    Consulta Receita Federal (dados públicos únicos).
    LGPD: Não armazenar CPF pessoal. Apenas CNPJ corporativo.
    """
    # Integração via API oficial ou web scraping com consentimento
    pass
```

**Conformidade LGPD:**
- ✅ Dados públicos de CNPJ (permitido)
- ❌ CPF pessoal (exige consentimento)
- ❌ Armazenamento indefinido (exige deletabilidade)

---

## 📚 Provedor Desacoplado (provedor.py)

O arquivo `../provedor.py` implementa uma **abstração multi-provedor** para suportar múltiplos LLMs:

### Suportados

| Provedor | Endpoint | Autenticação | Fallback |
|----------|----------|--------------|----------|
| **OpenAI** | api.openai.com | OPENAI_API_KEY | ← Primário |
| **Ollama** | localhost:11434 | Nenhuma | ← Fallback local |
| **Zen** | Endpoint corporativo | Token | ← Corporativo |

### Uso

```python
from provedor import obter_modelo_real

# Automático: tenta OpenAI → Ollama → Zen
modelo = obter_modelo_real()

# Forçar provedor
modelo = obter_modelo_real(provedor_forcado="ollama")

# Usar modelo
resposta = modelo.generate(prompt="Qual é 2+2?")
```

**Fallback automático:** Se OpenAI falhar (rate limit, indisponibilidade), tenta Ollama local.

---

## ✅ Checklist de Aprendizado

- [ ] Diferença LLM vs Agente compreendida
- [ ] SDK `openai-agents` instalado e funcionando
- [ ] @function_tool implementado com sucesso
- [ ] Integração ViaCEP testada
- [ ] Output type (Pydantic) validando respostas
- [ ] Múltiplos provedores testados (OpenAI/Ollama)
- [ ] Tratamento de erros implementado
- [ ] LGPD/conformidade de dados compreendida

---

## 🔗 Referências

- **openai-agents Docs:** https://platform.openai.com/docs/agents
- **ViaCEP API:** https://viacep.com.br/
- **BrasilAPI:** https://brasilapi.com.br/
- **LGPD Guia:** https://www.gov.br/cidadania/pt-br/acesso-a-informacao/lgpd

---

## 📝 Notas da Aula

Ver [aula1.md](./aula1.md) para anotações teóricas completas.

---

**Próximo:** Aula 2 — Orquestração e Guardrails
