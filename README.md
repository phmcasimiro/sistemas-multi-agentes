# Sistemas Multiagentes com IA — Resumo e Guia das Aulas

Este repositório contém o laboratório prático da disciplina **Sistemas Multiagentes com IA** (Pós-Graduação — IBMEC). O projeto abrange desde os fundamentos de agentes com o SDK `openai-agents`, passando por mensageria assíncrona (MQTT) e protocolos de ferramentas (MCP), até arquiteturas avançadas em grafos e orquestração de múltiplos agentes com **LangGraph**.

---

## 🏛️ Estrutura do Repositório

```text
11_Sistem_MultiAgentes/
  ├── provedor.py            # Central multi-provedor (Zen, Ollama, OpenAI) com fallback automático
  ├── requirements.txt       # Dependências consolidadas do projeto
  ├── .env.example           # Modelo de variáveis de ambiente para todas as aulas
  ├── docs/                  # Documentação complementar, epubs, pdfs e status de sincronização
  ├── aula1/                 # Fundamentos: Agente, Runner, @function_tool, Provedores
  ├── aula2/                 # Orquestração: Handoff, Agente-como-Tool, Guardrails, Sessão, Streaming
  ├── aula3/                 # Engenharia de Loops: RunHooks, AgentHooks, Retries, Idempotência, HITL
  ├── aula4/                 # Comunicação A2A: Síncrono vs Assíncrono, MQTT Pub/Sub, FIPA-ACL, Pipelines
  ├── aula5/                 # Model Context Protocol (MCP): Servidores HTTP, PostgreSQL, SQL Server, Docker
  ├── aula6/                 # Grafos com LangGraph: Fluxo linear, DAG, Cíclico, Condicional, Desafio Cofre
  ├── aula7/                 # Equipes Multiagente (LangGraph): Especialistas, HITL, Persistência, Casos Reais
  └── exercicios_resolvidos/ # Resoluções e exercícios guiados (Aulas 1 a 4)
```

---

## 📚 Visão Geral por Aula

### Aula 1 — Fundamentos
- **Conceito central**: Diferença entre LLM (stateless) e Agente (com estado, loop de raciocínio e runtime).
- **Provedor unificado**: `provedor.py` desacopla o backend de inferência (`zen`, `ollama` ou `openai`), garantindo recuo automático para modelos locais caso a API falhe.
- **Ferramentas (`@function_tool`)**: Conexão com serviços externos como ViaCEP (`agente5.py`) e Receita/BrasilAPI com minimização LGPD (`agente6.py`).
- **Contratos e Schemas**: Saídas estruturadas com Pydantic (`output_type`).

### Aula 2 — Orquestração e Integração
- **Mecanismos de Orquestração**: Handoff de controle de turno (`handoffs=[...]`) versus agentes usados como ferramentas (`as_tool()`).
- **Guardrails e Segurança**: Trava de entrada em Python puro (`agente_guardrail_puro.py`) para bloqueio determinístico sem custo de tokens, e guardrails via LLM.
- **Persistência de Estado**: Sessões isoladas (`SQLiteSession`) e streaming em tempo real (`Runner.run_streamed`).
- **Produção**: Microsserviços e exposição via FastAPI (`main.py`).

### Aula 3 — Engenharia do Agent Loop
- **Anatomia do Loop**: Ciclos de observação, decisão e ação executados pelo `Runner`.
- **Hooks e Observabilidade**: Interceptação em tempo de execução via `RunHooks` e `AgentHooks`.
- **Controle de Parada e Resiliência**: Limites de turnos (`max_turns`), timeouts externos, retries com backoff exponencial e garantia de idempotência.
- **Freio Humano (HITL)**: Aprovação manual (`needs_approval`) antes do disparo de ações críticas.

### Aula 4 — Comunicação Agente-a-Agente (A2A)
- **Síncrono × Assíncrono**: Handoff local (in-process, síncrono) versus mensageria distribuída (fora de processo, assíncrona).
- **MQTT Pub/Sub**: Tópicos, brokers públicos e locais, fan-out de mensagens e isolamento via prefixos de tópicos (`pcdf/demo`).
- **Contratos de Comunicação**: Semântica FIPA-ACL (performatives/intent) e pipelines encadeados de processamento de ocorrências policiais.

### Aula 5 — Model Context Protocol (MCP)
- **Desacoplamento de Fontes de Dados**: Servidores MCP como processos padronizados acessíveis por qualquer agente cliente.
- **Fontes Heterogêneas**: Integração com PostgreSQL (ocorrências), SQL Server (viaturas e equipes) e Google Sheets/CSVs (eventos).
- **Infraestrutura**: Servidores FastMCP sobre HTTP e orquestração de contêineres via Docker Compose.

### Aula 6 — Grafos de Decisão com LangGraph
- **Agentes como Grafos**: Transição para grafos com nós de computação e arestas condicionais (`langgraph`).
- **Topologias**: Fluxos lineares, DAGs (grafos acíclicos dirigidos), fluxos cíclicos e controle de estado compartilhado.
- **Modo Offline/Mock**: Abstração `Modelo` suportando `PROVEDOR=mock` para testes automatizados determinísticos sem consumo de API.
- **Desafios e Gamificação**: Desafio do Cofre, JEV AI e limiares operacionais com suíte de testes pontuados (`test_pontos.py`).

### Aula 7 — Orquestração Multiagente Avançada com LangGraph
- **Equipes de Agentes Especialistas**: Agente Geralista vs Especialistas com roteamento via estado no grafo.
- **Checkpoints e Memória**: Persistência de checkpoints com `langgraph-checkpoint-sqlite` para retomada de fluxos interrompidos.
- **Human-in-the-Loop (HITL)**: Pausa e retomada no grafo com aprovação humana e revisão de saídas.
- **Cenários do Mundo Real**: Investigação, análise de evidências e enquadramento jurídico integrado.

---

## 🚀 Como Executar

### 1. Preparação do Ambiente
```bash
# Clone ou acerte a pasta do projeto
cd 11_Sistem_MultiAgentes

# Ative o ambiente virtual
source venv/bin/activate

# Configure as variáveis de ambiente
cp .env.example .env
# Edite o arquivo .env com seu editor de preferência
```

### 2. Executando Exemplos das Aulas 1 a 5 (SDK `openai-agents`)
```bash
# Executar a partir da raiz como pacote:
python -m aula1.agente5
python -m aula2.agente_handoff "Gostaria de saber sobre a Revolução Francesa"
python -m aula3.agente_hook1

# Ou executar a API da Aula 2:
uvicorn aula2.main:app --reload
```

### 3. Executando Exemplos das Aulas 6 e 7 (LangGraph)
```bash
# Testes do Desafio da Aula 6 em modo Mock (sem chaves / sem custo):
PROVEDOR=mock python aula6/desafio/test_pontos.py

# Exemplo de fluxo condicional em grafo:
python aula6/exemplos/06_fluxo_condicional/main.py

# Exemplo de persistência multiagente na Aula 7:
python aula7/exemplos/04_persistencia/main.py
```
