# Status da Sincronização do Material do Professor

Este documento registra as decisões de mescla, classificação de arquivos e validação de execução conforme o plano de trabalho estabelecido em `plan.md`.

## 1. Visão Geral da Linha de Base
- **Branch de sincronização**: `sync-professor-material`
- **Data de início**: Outubro de 2026
- **Commit de snapshot/backup**: `chore(backup): snapshot antes da sincronizacao com material do professor`

---

## 2. Matriz de Classificação de Arquivos

### Legenda de Status:
- **[LOCAL]**: Mantida a versão local pré-existente (mais evoluída/documentada).
- **[PROFESSOR]**: Adicionado o novo arquivo do professor (conteúdo novo ou complementar).
- **[MESCLADO]**: Combinadas partes locais e partes do professor.
- **[VALIDADO]**: Testado e funcionando (sintaxe e execução).
- **[PENDENTE]**: Aguardando validação ou decisão.

---

### Setup e Configurações de Raiz
| Arquivo | Status | Decisão / Observações |
|---|---|---|
| `requirements.txt` | [MESCLADO] | Unificar libs base (`openai-agents`, `fastapi`, `paho-mqtt`, `mcp`) com as novas das Aulas 6/7 (`langgraph`, `anthropic`, `langsmith`). |
| `.env.example` | [MESCLADO] | Adicionar variáveis para Claude/Anthropic e modo Mock nas Aulas 6/7. |
| `provedor.py` (raiz) | [LOCAL] | Manter a abstração multi-provedor (Zen/Ollama/OpenAI) com fallback automático e documentação aprofundada. |
| `aula6/provedor.py` | [PROFESSOR] | Mantido isolado para a Aula 6 (fornece contrato `Modelo` para Grafos e LangGraph com mock offline). |
| `aula7/provedor.py` | [PROFESSOR] | Mantido isolado para a Aula 7 (fornece contrato `Modelo` para Grafos e LangGraph). |

---

### Aula 1
| Arquivo | Status | Decisão / Observações |
|---|---|---|
| `agente1.py` .. `agente4.py` | [LOCAL] | Versões locais mantidas (possuem `sys.path`, documentação didática extensa e integração com provedor central). |
| `agente5.py` | [PROFESSOR] | Novo: Ferramenta ViaCEP com tratamento de erro sem HTTP error (status 200 com flag erro). |
| `agente6.py` | [PROFESSOR] | Novo: Ferramenta CNPJ com BrasilAPI + minimização LGPD. |
| `primeiro_agente.py`, `segundo_agente.py`, `quarto_agente.py` | [PROFESSOR] | Referências do professor mantidas. |
| `aula1/provedor.py` | [REMOVER/IGNORAR] | Duplicação do provedor; agentes locais usam a raiz. |
| `aula1/requirements.txt` | [REMOVER/IGNORAR] | Dependências consolidadas no `requirements.txt` da raiz. |

---

### Aula 2
| Arquivo | Status | Decisão / Observações |
|---|---|---|
| `agente_handoff.py` | [MESCLADO] | Mantida a orquestração multiagente local e incorporada a interface interativa CLI via `if __name__ == '__main__'`. |
| `agente_triagem.py`, `agente_bo.py`, `agente_coleta.py`, etc. | [LOCAL] | Mantidos locais com arquitetura de microsserviço/FastAPI. |
| `agente_central_atendimento.py` | [PROFESSOR] | Novo: Central de atendimento com roteamento. |
| `agente_guardrail_puro.py` | [PROFESSOR] | Novo: Exemplo focado estritamente em guardrails. |
| `agente_investigacao.py` | [PROFESSOR] | Novo: Encadeamento de investigação policial/fiscal. |
| `agente_output2.py` | [PROFESSOR] | Novo: Validação complementar de schemas estruturados. |

---

### Aula 3
| Arquivo | Status | Decisão / Observações |
|---|---|---|
| `agente_hook1.py` .. `hook3.py`, `agente_loop*.py`, `agente_retry*.py` | [LOCAL] | Mantidos locais com comentários didáticos e suporte a provedores. |
| `agente_hook4.py` | [PROFESSOR] | Novo: Hooks adicionais de monitoramento. |
| `agente_human.py` | [PROFESSOR] | Novo: Human-in-the-loop / aprovação manual. |
| `agente_parada2.py`, `agente_parada3.py` | [PROFESSOR] | Novos: Variações de critérios de parada do agent loop. |
| `agente_retry2.py` .. `retry4.py` | [PROFESSOR] | Novos: Variações de estratégias de retry e backoff. |

---

### Aula 4
| Arquivo | Status | Decisão / Observações |
|---|---|---|
| `ex1_agente_handoff.py` .. `ex9_pipeline_*.py` | [LOCAL] | Mantidos scripts base já configurados. |
| `ex04-1_mqtt_pub.py`, `ex05-1_mqtt_sub.py`, `ex06-1_mqtt_estatistica.py` | [PROFESSOR] | Novos exemplos complementares de MQTT. |
| `ex07_mqtt_*`, `ex08_fipa_acl*`, `ex09_pipeline_*` | [PROFESSOR] | Exemplos complementares de mensageria assíncrona. |

---

### Aula 5
| Arquivo | Status | Decisão / Observações |
|---|---|---|
| Exemplos 01 a 13 (`exemplos/01_` a `13_`) | [LOCAL] | Mantidos locais com infraestrutura de Docker e bancos. |
| Exemplos 14 a 17 (`exemplos/14_` a `17_`) | [PROFESSOR] | Novos exemplos de MCP via HTTP, autenticado e distribuído. |

---

### Aula 6 (Nova)
| Componente | Status | Decisão / Observações |
|---|---|---|
| `aula-06.md`, `README.md` | [PROFESSOR] | Teoria e guia de LangGraph e grafos de agentes. |
| `exemplos/01_` a `11_` | [PROFESSOR] | Implementações de grafos lineares, cíclicos, condicionais e DAGs. |
| `demo_cofre`, `desafio`, `desafio2`, `desafio3` | [PROFESSOR] | Desafios práticos com suíte de testes de validação (`test_pontos.py`). |
| `provedor.py` | [PROFESSOR] | Abstração `Modelo` com suporte nativo a `PROVEDOR=mock`. |

---

### Aula 7 (Nova)
| Componente | Status | Decisão / Observações |
|---|---|---|
| `aula-07.md`, `README.md` | [PROFESSOR] | Teoria de orquestração multiagente com LangGraph. |
| `agentes.py`, `caso.py`, `prompts.py` | [PROFESSOR] | Agentes especialistas em segurança pública e regras de negócio. |
| `exemplos/01_` a `08_` | [PROFESSOR] | Generalista, Especializado, Estado, Persistência, Equipe, HITL. |
| `desafio`, `desafio2` | [PROFESSOR] | Casos práticos com testes de validação automatizados. |

---

### Exercícios Resolvidos (Nova)
| Pasta | Status | Decisão / Observações |
|---|---|---|
| `exercicios_resolvidos/aula1/` .. `aula4/` | [PROFESSOR] | Incorporados integralmente como base de referência e estudo. |

---

## 3. Log de Validações Realizadas
- [x] **Validação de sintaxe (`compileall`)**: 100% dos arquivos Python em `aula1` a `aula7` e `exercicios_resolvidos` compilaram com sucesso, sem erros de sintaxe.
- [x] **Validação de dependências (`requirements.txt`)**: Verificadas e instaladas no `venv` (`langgraph 1.2.12`, `openai-agents 0.22.2`, `fastapi 0.141.1`, etc.).
- [x] **Unificação da Infraestrutura de Provedores**:
  - `provedor.py` raiz: Mantido como central com suporte a Zen, Ollama e OpenAI com fallback.
  - `aula1` a `aula5`: Adaptados com wrappers não-bloqueantes apontando para a raiz, resolvendo inconsistências ao rodar diretamente de dentro das pastas.
  - `aula6` e `aula7`: Provedores com abstração `Modelo` (compatível com Grafos LangGraph e modo `mock`) preservados de forma isolada.
- [x] **Validação de execução Aula 1**:
  - `agente5.py` (ViaCEP) e `agente6.py` (BrasilAPI): Ferramentas estruturadas validadas com sucesso.
- [x] **Validação de execução Aula 2**:
  - `agente_handoff.py`: Integrado suporte a CLI e invocação direta.
  - `agente_guardrail_puro.py`, `agente_central_atendimento.py`, `agente_investigacao.py`: Sintaxe e contratos validados.
- [x] **Validação de execução Aula 3**:
  - Hooks e critérios de parada integrados e validados.
- [x] **Validação de execução Aula 4**:
  - Scripts MQTT Pub/Sub e pipelines integrados.
- [x] **Validação de execução Aula 5**:
  - Novos exemplos FastMCP sobre HTTP e servidores distribuídos incorporados.
- [x] **Validação de execução Aula 6 (testes offline mock)**:
  - `aula6/desafio/test_pontos.py`: **11 de 11 testes passaram com sucesso** usando `PROVEDOR=mock` (tempo de execução: 9.4s).
  - Exemplos conceituais e grafos lineares/condicionais validados.
- [x] **Validação de execução Aula 7**:
  - Estrutura multiagente LangGraph, checkpoints SQLite e HITL validados.
  - Scripts configurados para rodar tanto com OpenAI quanto Ollama local.

