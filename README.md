# Sistemas Multiagentes com IA — Resumo das Aulas

Este repositório contém o material prático da disciplina "Sistemas Multiagentes com IA" (Pós-Graduação — IBMEC). Abaixo segue um resumo estruturado por aula com os principais conceitos, padrões e palavras-chave presentes nos exemplos das pastas `aula1` a `aula5`.

## Aula 1 — Fundamentos
- Fundamento: diferença entre LLM (stateless) e Agente (estado, runtime, objetivos).
- Infraestrutura: `provedor.py` — desacoplamento de provedores (OpenAI / Zen / Ollama), `modelo()`, recuo para Ollama.
- Tool Calling: `@function_tool` transforma funções em ferramentas acionáveis pelo modelo.
- Handoff vs Tools: `handoffs=[...]` transfere o turno; `as_tool()` empacota agente como ferramenta.
- Saída Estruturada: `output_type` (Pydantic) — respostas tipadas e consumíveis programaticamente.
- Memória e Guardrails: `SQLiteSession`, `input_guardrail` / `output_guardrail` para segurança e persistência.

## Aula 2 — Orquestração e Integração
- Orquestração Multiagente: handoffs, agente-como-ferramenta, triador e especialistas.
- Integração com APIs: exemplos com Open-Meteo, ViaCEP, BrasilAPI, Nominatim como `tools`.
- Sessão e Isolamento: session IDs, persistência entre turnos, isolamento de conversas.
- Streaming & Integrador: `Runner.run_streamed`, composição de tools + guardrails + `output_type`.
- Produção/API: exposição via FastAPI (`main.py`) e pontos de atenção (max_turns, prompt injection).

## Aula 3 — Engenharia do Agent Loop
- Agent Loop: anatomia do loop do `Runner` — decisões, turnos e chamadas a tools.
- Hooks e Observabilidade: `RunHooks` vs `AgentHooks` (ex.: `on_llm_start`, `on_tool_start`).
- Critérios de parada: `max_turns`, sucesso declarado via `output_type`, timeout externo.
- Retries e Idempotência: backoff exponencial, tratamento de falhas, evitar duplicidade em escritas.
- Autonomia e Freio Humano: `needs_approval` e fluxos de aprovação humana.
- Decisões Encadeadas: múltiplas tools independentes, ordem decidida pelo modelo (investigador).

## Aula 4 — Comunicação Agente-a-Agente (A2A)
- Síncrono × Assíncrono: handoffs (síncrono, no mesmo processo) vs MQTT Pub/Sub (assíncrono, distribuído).
- MQTT: broker, tópicos, publish/subscribe, fan-out; cuidado com dados sensíveis em brokers públicos.
- Contratos: FIPA-ACL (performative/intent), gRPC (RPC tipado), mensageria/filas (persistência e entrega garantida).
- Padrões práticos: handoffs locais, agent-as-tool, MQTT Pub/Sub, request-reply sobre MQTT, pipelines encadeados.
- Operação distribuída: processos separados por agente; consistência de `MQTT_PREFIXO` entre publishers/subscribers.

## Aula 5 — MCP (Model Context Protocol)
- MCP: tools como processos/serviços (MCP Servers) acessíveis via protocolo e descobríveis pelo Inspector.
- Arquitetura: Agente (cliente) → MCP Client → MCP Server → Tool (serviço), com schema/metadata de parâmetros.
- Composição e escala: múltiplos MCP Servers, fontes diversas (Postgres, SQL Server, CSV), streamable HTTP via Docker.
- Segurança e Observabilidade: autorização para tools de escrita, auditoria, logs e deploy com Docker Compose.

## Como usar este resumo
- O conteúdo do README sintetiza os conceitos e pontos práticos implementados nas pastas `aula1/` a `aula5/`.
- Para executar os exemplos, ative a `venv` na raiz e rode os scripts das pastas correspondentes (cada `aulaN` é um pacote Python).

Se quiser, eu posso também gerar uma versão mais detalhada por arquivo (lista de scripts e o que cada um faz) ou substituir este README por uma versão em inglês.
