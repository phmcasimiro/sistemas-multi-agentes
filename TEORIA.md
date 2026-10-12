# 🎓 Teoria e Conceitos — Sistemas Multiagentes com IA

Compêndio dos conceitos fundamentais, arquiteturais e ferramentas utilizadas ao longo das 8 aulas da disciplina.

---

## 📌 Conceitos Fundamentais

### LLM (Large Language Model) vs Agente

| Aspecto | LLM | Agente |
|---------|-----|--------|
| **O que é** | Função probabilística: texto → texto | Sistema autônomo: estado + objetivos + loop de ação |
| **Memória** | Nenhuma (stateless) | Persistente entre turnos (stateful) |
| **Ação** | Gera tokens; faz previsão | Executa ferramentas; modifica ambiente |
| **Decisão** | Seleção de token mais provável | ReAct: Reasoning + Acting |
| **Composição** | Isolado | Runtime + SDK + Ferramentas + Persistência |

### ReAct (Reasoning + Acting)

Padrão de execução do agente:
```
1. Observação (ler estado, entrada do usuário)
2. Raciocínio (LLM pensa sobre o problema)
3. Ação (chama ferramenta ou handoff)
4. Reavaliação (volta ao passo 1 se não chegou ao objetivo)
```

### @function_tool

Anotação Python que transforma funções normais em especificações JSON Schema consumíveis pelo modelo:
```python
@function_tool
def consultar_cep(cep: str) -> dict:
    """Busca dados de um CEP via ViaCEP"""
    # Implementação
```
O LLM recebe a assinatura, tipos e docstring em JSON; chamadas validadas automaticamente.

### Output Type (Pydantic Validation)

Validação determinística de saída do modelo usando `output_type`:
```python
model.generate(prompt, output_type=MinhaResposta)  # Garante schema
```
Previne alucinações e garante contrato entre cliente e modelo.

---

## 🔄 Padrões de Orquestração

### Handoff (Transferência de Soberania)

Um agente transfere **completamente** o turno para outro especialista:
```python
agent1.handoffs = [agent2]  # agent1 pode fazer transfer_to_agent2
```
- **Controle:** O novo agente/especialista assume o microfone.
- **Caso de uso:** Agente jurídico → Agente de análise de risco.

### Agente como Ferramenta (as_tool)

Um agente é exposto como função/ferramenta para outro agente reutilizá-lo:
```python
agent1.tools = [agent2.as_tool()]  # agent1 chama agent2 como função
```
- **Controle:** agent1 mantém o turno; resultado de agent2 é dado a agent1.
- **Caso de uso:** Orquestrador principal contrata especialistas.

### Guardrails (Travas de Segurança)

Validações **determinísticas** que interrompem fluxos não autorizados:

**Guardrails Puros (Python):**
- Verificação sem custo de tokens
- Padrão: `if not autorizado: raise GuardrailError`

**Guardrails Neurais (NeMo):**
- Modelo de classificação treinado
- Detecta Prompt Injection, formatos malformados, dados sensíveis

### Sessão (Memória Conversacional)

Armazenamento de histórico entre turnos:
- **SQLiteSession**: Banco local (`.db`) persistindo conversas por ID de sessão
- **Isolamento:** Clientes diferentes não veem histórico alheio
- **Conformidade:** Estrutura para LGPD, retenção controlada

---

## 🌊 Padrões de Comunicação

### Assíncrono vs Síncrono

| Tipo | Mecanismo | Exemplo | Vantagem |
|------|-----------|---------|----------|
| **Síncrono** | Chamada direta (mesmo processo) | Handoff local | Simples, transacional |
| **Assíncrono** | Fila/Mensageria (processos diferentes) | MQTT Pub/Sub | Escalável, desacoplado |

### MQTT Pub/Sub

**Publish-Subscribe com tópicos:**
```
Agent_A publica em: pcdf/demo/ocorrencia → Message Broker
Agent_B assina: pcdf/demo/# → recebe automaticamente
```
- **Tópicos:** Hierarquia com `/` (ex: `pcdf/demo/ocorrencia`, `pcdf/demo/análise`)
- **Broker:** Mosquitto local ou MQTT pública (HiveMQ)
- **Persistência:** Opcional (retained messages)

### FIPA-ACL (Agent Communication Language)

Protocolo padronizado para comunicação estruturada entre agentes:
```python
{
  "performative": "REQUEST",      # Tipo: REQUEST, INFORM, PROPOSE, etc.
  "sender": "agente_coleta",
  "receiver": "agente_triagem",
  "content": {...}                # Carga JSON
}
```
- **Semantics:** Cada performative tem significado bem definido
- **Interoperabilidade:** Compatível com sistemas JADE, FIPA, heterogêneos

---

## 🔌 Protocolos de Integração

### MCP (Model Context Protocol)

Protocolo aberto de desacoplamento entre agentes e fontes de dados:

**Arquitetura:**
```
Agent  ←→  MCP Client  ←→  stdio/http  ←→  MCP Server  ←→  Database/API
```

**Características:**
- **Recursos:** Listas, descrições, buscias estruturadas
- **Ferramentas:** Funções expostas pelo servidor
- **Prompts:** Templates reutilizáveis
- **Transporte:** stdio (subprocess), HTTP, WebSocket

**Vantagem:** Múltiplos agentes ($N$) × Múltiplas fontes ($M$) sem acoplamento $N \times M$.

### LangGraph (StateGraph)

Framework para orquestração determinística de fluxos complexos:

**Conceitos:**
- **Estado (TypedDict):** Dicionário compartilhado entre nós (imutável)
- **Nó:** Função que lê estado, executa lógica, retorna atualizações
- **Aresta:** Conexão entre nós (condicional ou incondicional)
- **Roteador:** Função que decide próximo nó baseado em estado
- **START/END:** Nós sintéticos de entrada e saída

**Topologias:**
1. **Linear:** START → A → B → C → END
2. **DAG (Acyclical):** Ramificações paralelas sem ciclos
3. **Cíclico:** A → B → A (com condição de parada)

---

## 🤖 Modelos de Decisão

### JEV (JavaScript Expression Validator / Modelo Probabilístico)

Modelo especializado em **decisões tipadas** com probabilidades:

**Vs LLM:**
- **LLM:** "É urgente?" → texto livre (ambíguo)
- **JEV:** "É urgente?" → {p: 0.92, confiança: 0.88} (numérico)

**Tipos de decisão:**
- `noul` (yes/no/uncertain): Probabilidade 0-1
- `choice`: Opção com probabilidades para cada alternativa
- `scale`: Escala numérica (1-10)

**Critério de roteamento:**
```python
if p_urgente >= 0.8:
    caminho = "urgente"
elif p_sensível >= 0.8 and confiança < 0.6:
    caminho = "incerto → pedir_esclarecimento"
```

---

## 🔐 Segurança e Governança

### Validação em Camadas

1. **Entrada (Input Guardrails):**
   - Detecção de Prompt Injection
   - Verificação de padrões maliciosos
   - Sanitização de dados sensíveis (PII)

2. **Processamento (Tool Authorization - OPA):**
   - Autorização centralizada com Open Policy Agent
   - Políticas em `.rego` (linguagem OPA)
   - Resposta: permitir/negar/auditoria

3. **Saída (Output Guardrails):**
   - Validação de schema JSON
   - Conformidade com restrições legais
   - Detecção de alucinações (mentiras do LLM)

### OPA (Open Policy Agent)

Motor de autorização agnóstico que centraliza decisões de acesso:

**Exemplo de política `.rego`:**
```rego
allow {
    input.user.role == "investigador"
    input.action == "acessar_base_dados"
    input.resource == "ocorrencias"
}
```

**Vantagens:**
- Desacoplamento: agentes não conhecem políticas
- Auditoria: decisões rastreáveis
- Flexibilidade: políticas mutáveis sem redeployment

---

## 📊 Observabilidade e Telemetria

### OpenTelemetry (OTel)

Padrão aberto para instrumentação agnóstica de aplicações:

**Componentes:**
- **Spans:** Unidades de trabalho (chamada LLM, execução ferramenta)
- **Traces:** Sequência de spans relacionados (uma execução completa do agente)
- **Métricas:** Números agregados (latência, taxa de erro, tokens/segundo)
- **Logs:** Eventos estruturados em JSON

**Exportadores:**
- OTLP HTTP (para Langfuse, Datadog, New Relic)
- Prometheus (para métricas locais)
- Jaeger (para distribuição de traces)

### Langfuse Cloud

Plataforma específica para observabilidade de agentes de IA:

**Rastreamento:**
- Cada chamada ao modelo (custo, latência, tokens)
- Execução de ferramentas
- Scores manuais (feedback humano)

**Dashboard:**
- Traces exploráveis
- Chamadas agrupadas por tipo
- Comparação A/B de prompts

### Prometheus + Grafana

**Prometheus:**
- Time-series database: coleta métricas de endpoints `/metrics`
- Retenção: padrão 15 dias configurável
- Queries: linguagem PromQL (ex: `rate(requests_total[5m])`)

**Grafana:**
- Visualização de dashboards
- Alertas baseados em limiares
- Datasources múltiplas (Prometheus, Loki, etc)

---

## 🔄 Padrões de Resiliência

### Retry e Idempotência

**Retry com Backoff Exponencial:**
```python
for tentativa in range(max_retries):
    try:
        resultado = chamada_api()
        break
    except TemporaryError:
        espera = 2 ** tentativa  # 1s, 2s, 4s, 8s...
        time.sleep(espera)
```

**Idempotência:**
- Operação pode ser repetida sem efeitos colaterais
- Exemplo: `UPDATE conta SET saldo = 1000` (seguro repetir)
- Contra-exemplo: `UPDATE conta SET saldo = saldo - 100` (não!)

### Ciclos de Validação e Revisão

Padrão LangGraph cíclico forçando qualidade:
```
A (análise) → B (validação) → 
   ├─ OK → C (finalizar)
   └─ ERRO → A (revisar) [máx 3 tentativas]
```

### Human-in-the-Loop (HITL)

Interrupção da execução automática para aprovação humana:
```python
@decision  # Marca ponto de parada
def validacao_humana(estado):
    # Execução pausa, aguarda Command(resume=...)
    return {"status": "aguardando_humano"}
```

---

## 🏗️ Padrões Arquiteturais

### Especialistas vs Generalista

| Modelo | Estrutura | Vantagem | Desvantagem |
|--------|-----------|----------|------------|
| **Generalista** | Um agente faz tudo | Simples | Menos robusto, overfitting |
| **Especialistas** | Cada agente faz uma coisa | Escalável, testável | Mais complexo, sincronização |

**LangGraph com Especialistas:**
```
START → Investigador (extrai fatos)
    ↓
    ├→ Jurídico (análise legal)  ⎤ Paralelo
    └→ Risco (avalia risco)       ⎦
    ↓
Consolidação (redige parecer)
    ↓
END
```

### Fan-Out / Fan-In

**Fan-Out:** Um nó dispara múltiplos processadores em paralelo
```
Consolidador → [Jurídico, Risco] (rodam em paralelo)
```

**Fan-In:** Múltiplos resultados são sincronizados num nó
```
[Jurídico, Risco] → Resultado (aguarda ambos)
```

### Persistência de Estado (Checkpointer)

Salvamento incremental para retomada resiliente:
- **SqliteSaver:** Banco SQLite persistindo snapshots de estado
- **MemorySaver:** Cache em memória (para testes)
- **Benefit:** Retomar grafo após falha, auditar histórico

---

## 🛠️ Stacks de Tecnologia

### Frontend de Agentes

| Ferramenta | Propósito | Linguagem |
|-----------|-----------|-----------|
| **openai-agents** | SDK oficial do OpenAI (Agent + Runner) | Python |
| **LangGraph** | Orquestração de grafos | Python |
| **FastAPI** | Exposição via API REST | Python |

### Backend de Dados

| Ferramenta | Propósito |
|-----------|-----------|
| **PostgreSQL** | Base relacional principal (ocorrências, viaturas) |
| **SQL Server** | Base secundária (compatibilidade). |
| **SQLite** | Persistência local de sessões/checkpoints |
| **CSV/JSON** | Dados estáticos (configurações, referências) |

### Messaging e Protocolos

| Ferramenta | Propósito | Tipo |
|-----------|-----------|------|
| **MQTT** | Pub/Sub assíncrono | Protocolo |
| **MCP** | Integração desacoplada | Protocolo |
| **FIPA-ACL** | Comunicação estruturada | Protocolo |

### Observabilidade

| Ferramenta | Propósito |
|-----------|-----------|
| **OpenTelemetry** | Instrumentação padrão |
| **Langfuse** | Traces LLM cloud |
| **Prometheus** | Métricas time-series |
| **Grafana** | Dashboards e alertas |

### Segurança

| Ferramenta | Propósito |
|-----------|-----------|
| **NeMo Guardrails** | Validação entrada/saída |
| **OPA** | Autorização centralizada |

---

## 🔤 Notação e Abreviações

| Sigla | Significado |
|-------|-----------|
| **LLM** | Large Language Model |
| **SDK** | Software Development Kit |
| **API** | Application Programming Interface |
| **REST** | Representational State Transfer |
| **JSON** | JavaScript Object Notation |
| **MQTT** | Message Queuing Telemetry Transport |
| **MCP** | Model Context Protocol |
| **FIPA** | Foundation for Intelligent Physical Agents |
| **OTel** | OpenTelemetry |
| **OPA** | Open Policy Agent |
| **PII** | Personally Identifiable Information |
| **LGPD** | Lei Geral de Proteção de Dados |
| **HDL** | High-Definition Language (para diagramas) |
| **UI** | User Interface |

---

## 📚 Referências Rápidas

### Documentação Oficial
- OpenAI Agents: https://platform.openai.com/docs/agents
- LangGraph: https://langchain-ai.github.io/langgraph/
- MCP Spec: https://modelcontextprotocol.io/
- OPA Docs: https://www.openpolicyagent.org/

### Padrões de P&P
- ReAct Paper: https://arxiv.org/abs/2210.03629
- FIPA Specifications: http://www.fipa.org/

---

**Fim da Documentação Teórica**
