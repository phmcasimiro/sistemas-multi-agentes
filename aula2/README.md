# Aula 2 — Orquestração, Guardrails e Persistência de Sessão

**Conceito Central:** Evolução de agentes isolados para **orquestração de múltiplos especialistas**. Introdução de mecanismos de segurança (**guardrails**), persistência de conversas (**memória conversacional**) e exposição via API REST (**FastAPI**).

---

## 🎯 Objetivos da Aula

- Entender modelo de **Handoffs** (transferência de soberania entre agentes)
- Implementar **Agente como Ferramenta** (as_tool) para composição
- Aplicar **Guardrails de Segurança** (puro em Python e neural com NeMo)
- Usar **SQLiteSession** para persistência conversacional entre turnos
- Expor agentes via **FastAPI** com streaming de tokens
- Estruturar respostas com **resultado.last_agent** para auditoria

---

## 📊 Arquitetura Aula 2

```
┌────────────────────────────────────────────┐
│        Entrada do Usuário (FastAPI)        │
└──────────────┬─────────────────────────────┘
               │
   ┌───────────▼──────────────┐
   │  Guardrail de Entrada    │
   │  (Detectar Malware PII)  │
   └───────────┬──────────────┘
               │
   ┌───────────▼───────────────────┐
   │  Orquestrador (Main Agent)    │
   │  • Pode usar Handoffs         │
   │  • Pode chamar especialistas  │
   │    como ferramentas           │
   └───────────┬───────────────────┘
               │
      ┌────────┴────────┐
      │                 │
  Handoff         @function_tool
      │                 │
      ▼                 ▼
  ┌────────────┐   ┌───────────────┐
  │Especialista│   │Especialista   │
  │ (assume    │   │ (resultado    │
  │  turno)    │   │  volta)       │
  └────────┬───┘   └────────┬──────┘
           │                │
      [Resultado]    [Resultado]
           │                │
           └────────┬───────┘
                    │
          ┌─────────▼────────────┐
          │ Guardrail de Saída   │
          │ (Validar Schema)     │
          └─────────┬────────────┘
                    │
          ┌─────────▼─────────────────┐
          │ SQLiteSession.add_message │
          │ (Persistência local)      │
          └─────────┬─────────────────┘
                    │
          ┌─────────▼─────────────────┐
          │ FastAPI Response (Stream) │
          │ (Retorna ao cliente)      │
          └───────────────────────────┘
```

---

## 🛠️ Ferramentas Utilizadas

### Handoffs (Transferência de Soberania)

**O que é:**
Um agente transfere completamente o turno para outro especialista. O novo agente **assume o microfone** e toma decisões para atingir o objetivo.

**Sintaxe:**
```python
from openai_agents import Agent

especialista_juridico = Agent(
    name="juridico",
    instructions="Você é especialista em análise jurídica..."
)

orquestrador = Agent(
    name="orquestrador",
    instructions="Você coordena...",
    handoffs=[especialista_juridico]  # ← Pode transferir para juridico
)
```

**Transferência em código:**
```python
# Dentro da instrução do orquestrador:
# "Se precisar de análise jurídica, transfira para transfer_to_juridico"

# LLM automaticamente chama:
runner.run(orquestrador, user_input="Precisamos de parecer jurídico...")
```

**Quando usar:**
- Especialista tem expertise bem definida
- Novo agente precisa autonomia total
- Escalação é apropriada

---

### Agente como Ferramenta (as_tool)

**O que é:**
Um agente é exposto como função/ferramenta. O **orquestrador mantém o turno** e chama o especialista como subroutina.

**Sintaxe:**
```python
especialista = Agent(name="especialista", instructions="...")

# Expor como ferramenta
@function_tool
def chamar_especialista(pergunta: str) -> str:
    """Consultora especialista para análise técnica"""
    runner = Runner(agents=[especialista])
    resultado = runner.run(especialista, pergunta)
    return resultado.final_output

# Adicionar ao orquestrador
orquestrador.tools = [chamar_especialista]
```

**Quando usar:**
- Orquestrador precisa controlar fluxo completo
- Resultado do especialista é entrada para próxima etapa
- Composição em pipeline

---

### Guardrails Puros (Python)

**O que é:**
Validações **determinísticas** sem custo de tokens, implementadas em Python puro.

**Exemplo — Tripwire de Dados Sensíveis:**
```python
def guardrail_entrada_pura(user_input: str) -> tuple[bool, str]:
    """Rejeita entrada com PII ou padrões maliciosos"""
    
    # Padrão 1: Detectar CPF (XXX.XXX.XXX-XX)
    if re.search(r'\d{3}\.\d{3}\.\d{3}-\d{2}', user_input):
        return False, "Não posso processar dados pessoais (CPF)."
    
    # Padrão 2: Detectar "Ignore previous instructions"
    if "ignore previous" in user_input.lower():
        return False, "Comando de injeção detectado."
    
    return True, ""

# Uso
permitido, erro = guardrail_entrada_pura(user_input)
if not permitido:
    raise GuardrailError(erro)
```

**Vantagem:**
- Instantâneo (sem latência LLM)
- Confiável (lógica determinística)
- Sem custo de tokens

---

### Guardrails Neurais (NeMo Guardrails)

**O que é:**
Modelo de classificação treinado para detectar padrões complexos (Prompt Injection, pergunta fora de escopo, linguagem tóxica).

**Instalação:**
```bash
pip install nemoguardrails>=0.24,<1.0
```

**Exemplo:**
```python
from guardrails import LLMRails
from guardrails.config import RailsConfig

# Carregar política
config_str = """
define bot answer_scope
    """Responda somente sobre segurança pública"""
    
    if "política" in user_input.lower():
        bot refuse "Esse tópico está fora do escopo"

define bot detect_injection
    """Detecta prompt injection"""
    
    if "ignore previous" in user_input.lower() or "system override" in user_input.lower():
        bot refuse "Seu pedido foi rejeitado por suspicion de ataque."
"""

rails = LLMRails(config=RailsConfig.from_string(config_str))

# Usar
resultado = rails.generate(user_input, llm=modelo)
```

**Quando usar:**
- Validações semânticas complexas
- Conformidade regulatória (LGPD, conformidade)
- Detecção de adversários sofisticados

---

### SQLiteSession (Memória Conversacional)

**O que é:**
Armazenamento local de histórico conversacional por sessão (`session_id`). Cada cliente tem conversa isolada.

**Instalação:**
```bash
pip install langchain-community sqlite
```

**Uso:**
```python
from langchain_community.chat_message_histories import SQLiteChatMessageHistory

# Criar/acessar histórico
history = SQLiteChatMessageHistory(
    session_id="usuario_123",
    db_path="conversas.db"
)

# Adicionar mensagem
history.add_message({
    "role": "user",
    "content": "Qual é a capital de SP?"
})

# Recuperar histórico
mensagens = history.messages
print(f"Conversa tem {len(mensagens)} mensagens")

# Limpar sessão
history.clear()  # ou history.delete() para deletar
```

**Estrutura SQLite:**
```sql
-- Criado automaticamente pela biblioteca
CREATE TABLE messages (
    id INTEGER PRIMARY KEY,
    session_id TEXT,
    role TEXT,  -- "user", "assistant", "system"
    content TEXT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE sessions (
    session_id TEXT PRIMARY KEY,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

**Conformidade LGPD:**
- ✅ Isolamento por `session_id` (não mistura usuários)
- ✅ Estrutura para deletabilidade (DELETE FROM messages WHERE session_id = ?)
- ✅ Retenção controlada (pode-se limpar automaticamente após X dias)

---

### FastAPI (Exposição REST + Streaming)

**O que é:**
Framework web moderno para expor agentes via HTTP com suporte a streaming de tokens.

**Instalação:**
```bash
pip install fastapi uvicorn pydantic
```

**Exemplo Básico:**
```python
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()

class PerguntaRequest(BaseModel):
    session_id: str
    pergunta: str

class RespostaResponse(BaseModel):
    resposta: str
    agente_ativo: str  # Para auditoria

@app.post("/consultar")
async def consultar(req: PerguntaRequest) -> RespostaResponse:
    """Endpoint que chama o agente"""
    history = SQLiteChatMessageHistory(
        session_id=req.session_id,
        db_path="conversas.db"
    )
    
    # Adicionar entrada
    history.add_message({"role": "user", "content": req.pergunta})
    
    # Chamar agente
    runner = Runner(agents=[seu_agente])
    resultado = runner.run(seu_agente, req.pergunta)
    
    # Adicionar resposta ao histórico
    history.add_message({"role": "assistant", "content": resultado.final_output})
    
    return RespostaResponse(
        resposta=resultado.final_output,
        agente_ativo=resultado.last_agent.name  # ← Auditoria
    )

# Rodar
# uvicorn seu_arquivo:app --reload
```

**Streaming de Tokens:**
```python
from fastapi.responses import StreamingResponse
import json

@app.post("/consultar-stream")
async def consultar_stream(req: PerguntaRequest):
    """Streaming de tokens em tempo real"""
    
    async def token_generator():
        runner = Runner(agents=[seu_agente])
        
        # Usar iterator de tokens
        for token in runner.stream(seu_agente, req.pergunta):
            yield f"data: {json.dumps({'token': token})}\n\n"
    
    return StreamingResponse(
        token_generator(),
        media_type="text/event-stream"
    )
```

**Cliente JavaScript:**
```javascript
fetch('/consultar-stream', {
  method: 'POST',
  body: JSON.stringify({session_id: 'user1', pergunta: 'Olá'})
})
.then(resp => resp.body.getReader())
.then(reader => {
  const decoder = new TextDecoder();
  const pump = () => reader.read().then(({done, value}) => {
    if (done) return;
    const line = decoder.decode(value);
    console.log(line);
    pump();
  });
  pump();
});
```

---

## 📁 Estrutura de Arquivos

```
aula2/
├── README.md                           ← Este arquivo
├── agente_bo.py                        ← Agente de BO (Backoffice)
├── agente_central_atendimento.py       ← Central de atendimento
├── agente_coleta.py                    ← Coletor de dados
├── agente_guardrail_puro.py            ← Guardrail em Python puro
├── agente_guardrail.py                 ← Guardrail com NeMo
├── agente_handoff_callback.py          ← Handoff com callbacks
├── agente_handoff.py                   ← Handoff básico
├── agente_handoff2.py                  ← Handoff avançado
├── agente_integrador.py                ← Integrador de dados
├── agente_investigacao.py              ← Investigador
├── agente_isolamento.py                ← Isolamento de escopo
├── agente_memoria.py                   ← Com SQLiteSession
├── agente_output_guardrail.py          ← Validação de saída
├── agente_output.py                    ← Controle de saída
├── agente_producao.py                  ← Pronto para produção
├── agente_sessao2.py                   ← Sessão v2
├── agente_session.py                   ← Gerenciador de sessão
├── agente_streaming.py                 ← Streaming de tokens
├── agente_triagem.py                   ← Triagem de casos
├── main.py                             ← App FastAPI completo
├── primeiro_agente.py                  ← Primeiro exemplo
└── aula2.md                            ← Notas teóricas
```

---

## 🚀 Como Rodar

### Teste Rápido (Agente com Sessão)

```bash
cd aula2
python agente_session.py
```

### Teste com Guardrail Puro

```bash
python agente_guardrail_puro.py
# Usar entrada inofensiva: "Qual é o CEP de SP?"
```

### Teste com Handoff

```bash
python agente_handoff.py
# Prompt: "Preciso de parecer jurídico sobre um contrato"
# Esperado: Transferência automática para especialista
```

### Executar App FastAPI

```bash
# Terminal 1: Rodar servidor
uvicorn main:app --reload --port 8000

# Terminal 2: Testar endpoint
curl -X POST http://localhost:8000/consultar \
  -H "Content-Type: application/json" \
  -d '{"session_id": "user1", "pergunta": "Olá, tudo bem?"}'
```

### Teste de Streaming

```bash
# Terminal 1: Servidor rodando

# Terminal 2: Cliente curl com streaming
curl -X POST http://localhost:8000/consultar-stream \
  -H "Content-Type: application/json" \
  -d '{"session_id": "user1", "pergunta": "Explique LangGraph"}'
```

---

## 📝 Padrões de Projeto

### Padrão 1: Orquestrador + Especialistas (Handoff)

```
┌────────────────────┐
│ Orquestrador       │
│ (decide qual)      │
└────────┬───────────┘
         │
         ├─ transfer_to_juridico
         ├─ transfer_to_tecnico
         └─ transfer_to_financeiro
```

**Uso:** Escalação clara, cada agente autônomo.

---

### Padrão 2: Orquestrador + Especialistas (as_tool)

```
┌────────────────────────┐
│ Orquestrador           │
│ (controla fluxo)       │
└────────┬───────────────┘
         │
         ├─ chamar_juridico()
         ├─ chamar_tecnico()
         ├─ chamar_financeiro()
         └─ consolidar_resposta()
```

**Uso:** Pipeline programável, composição.

---

### Padrão 3: Guardrail em Camadas

```
Entrada → [Guardrail Puro] → [NeMo] → Agente → [Output Guardrail] → Saída
         (tripwire PII)      (injeção) (processa) (formato JSON)
```

---

## ✅ Checklist de Aprendizado

- [ ] Diferença Handoff vs as_tool compreendida
- [ ] Handoff implementado com sucesso
- [ ] Guardrail puro testado (inputs rejeitados)
- [ ] NeMo Guardrails instalado e rodando
- [ ] SQLiteSession criando banco `conversas.db`
- [ ] Histórico conversacional persistindo
- [ ] FastAPI expondo endpoints
- [ ] Streaming de tokens funcionando
- [ ] Auditoria via `resultado.last_agent` ativa
- [ ] Conformidade LGPD (isolamento de sessão)

---

## 🔗 Referências

- **openai-agents Docs:** https://platform.openai.com/docs/agents
- **LangChain Session:** https://python.langchain.com/docs/modules/memory/chat_message_histories
- **FastAPI Docs:** https://fastapi.tiangolo.com/
- **NeMo Guardrails:** https://github.com/NVIDIA/NeMo-Guardrails
- **SQLite Python:** https://docs.python.org/3/library/sqlite3.html

---

## 📝 Notas da Aula

Ver [aula2.md](./aula2.md) para anotações teóricas completas.

---

**Próximo:** Aula 3 — Engenharia de Agent Loops
