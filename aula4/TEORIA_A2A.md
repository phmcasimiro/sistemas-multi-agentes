# SISTEMAS MULTIAGENTES - A2A

---

## De Um Agente Para Vários: Por Que A2A?

Até aqui, este material trabalhou com **um único agente**: ele percebia a entrada, raciocinava e respondia. Esse modelo funciona até o problema ficar grande demais para uma única "cabeça" resolver sozinha. Uma ocorrência real, por exemplo, passa por várias mãos institucionais — quem **coleta** o boletim, quem **tria** a gravidade, quem **avalia** o enquadramento jurídico. Decompor essas responsabilidades em agentes especializados traz ganhos diretos:

- **Simplicidade e testabilidade:** cada agente concentra uma única responsabilidade, com instruções mais curtas e mais fáceis de validar isoladamente.
- **Substituição e escala independentes:** é possível trocar ou escalar uma peça do sistema (ex.: o agente Jurídico) sem tocar nas demais.
- **O preço a pagar:** para que essa decomposição funcione, os agentes **precisam falar a mesma língua** — é exatamente disso que trata a comunicação Agente-a-Agente (A2A), o tema deste material.

**Fio condutor deste material:** um Agente **Coletor** recebe a ocorrência, um Agente de **Triagem** classifica, e um Agente **Jurídico** avalia o enquadramento legal. Esse trio aparece em todos os exemplos a seguir, aprendendo a se comunicar primeiro **na mesma sala** (síncrono, via handoff) e depois **à distância, por bilhete** (assíncrono, via MQTT).

---

Na comunicação Agente-para-Agente (A2A), a distinção fundamental entre comunicação síncrona e assíncrona reside no **acoplamento temporal** e no **bloqueio do Agent Loop (ciclo de execução)** do emissor enquanto a mensagem é processada pelo receptor.

> **Em uma analogia simples:** comunicação **síncrona** é como um **telefonema** — você liga e fica na linha esperando a resposta. Comunicação **assíncrona** é como **deixar um recado** — você registra a mensagem e segue sua vida, confiando que o destinatário vai processá-la quando puder.

## Visão Geral Comparativa

| Dimensão                     | Comunicação A2A Síncrona                                                       | Comunicação A2A Assíncrona                                               |
| ---------------------------- | ------------------------------------------------------------------------------ | ------------------------------------------------------------------------ |
| **Comportamento do Emissor** | Agent Loop do Emissor é Bloqueado e aguarda a resposta antes de prosseguir.    | Agent Loopdo emissor é liberado após despachar a mensagem.               |
| **Acoplamento Temporal**     | **Alto**: remetente e destinatário devem estar disponíveis no mesmo instante.  | **Baixo**: desacoplados no tempo (processamento diferido).               |
| **Mecanismo de Transporte**  | Request-Response direto (HTTP/REST, gRPC, chamadas RPC diretas).               | Mensageria e Eventos (Pub/Sub, filas RabbitMQ/Kafka, Event Loops).       |
| **Tratamento de Latência**   | Aditivo: a latência total é a soma do tempo de inferência de todos os agentes. | Otimizado: agentes trabalham concorrentemente em segundo plano.          |
| **Risco Arquitetural**       | _Deadlocks_ (espera circular) e estouro de _timeouts_.                         | Perda de ordem de mensagens e complexidade de rastreabilidade de estado. |

---

### O Papel dos Contratos e Protocolos na Comunicação A2A

A distinção síncrono/assíncrono descreve **quando** a mensagem é trocada (o acoplamento temporal). Ela não diz nada sobre **como** os bytes são estruturados, transportados e interpretados pelas duas pontas — essa é a função de um **contrato** (ou **protocolo**): um acordo técnico, definido antes da execução, que ambos os agentes precisam honrar para que a troca seja compreensível. Sem um contrato, cada agente teria que adivinhar o formato da mensagem do outro a cada interação — o que, em produção, é a origem de boa parte das falhas silenciosas de integração.

Esses três contratos se encaixam nos **três padrões fundamentais de troca de mensagens** entre sistemas distribuídos:

- **Request/Response** — um pede, o outro responde; direto e previsível. É o padrão por trás tanto do *handoff* do SDK (Seção 1 a seguir, dentro do mesmo processo) quanto das chamadas HTTP/gRPC em rede.
- **Publish/Subscribe (Pub/Sub)** — quem publica não sabe quem consome; um tópico, vários assinantes. É o coração do MQTT.
- **Mensageria/Filas** — mensagens ficam retidas numa fila até serem processadas, garantindo que nada se perca (RabbitMQ/Kafka; ver Dicionário, Seção 3).

Este material trabalha com três contratos/protocolos, e cada um resolve um problema em uma **camada diferente**:

| Protocolo/Contrato | Camada que resolve                                | Papel no A2A                                                                                            | Onde aparece neste material                                                         |
| ------------------- | --------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------- |
| **gRPC**             | Transporte — lado **síncrono**                       | RPC (_Remote Procedure Call_) tipado e de alta performance; alternativa ao HTTP/REST da Seção 1.        | Detalhado como alternativa formal ao REST na Seção "Casos de Uso" (item 3.1).        |
| **MQTT**             | Transporte — lado **assíncrono**                     | Mensageria leve Pub/Sub, mediada por um broker; dispensa que as pontas conheçam IP uma da outra.        | Protocolo efetivamente usado em todo o código deste material (`paho-mqtt`).          |
| **FIPA-ACL**         | **Semântica do conteúdo** da mensagem (o payload)    | Formaliza a **intenção** da troca (a _performativa_) — independe de qual transporte carrega a mensagem. | Aplicável tanto sobre uma chamada síncrona (gRPC/REST) quanto sobre um tópico MQTT.   |

**Ponto-chave:** **gRPC** e **MQTT** competem entre si (você escolhe um OU outro para o transporte, conforme o par **síncrono**/**assíncrono**). Já a **FIPA-ACL** não compete com nenhum dos dois — ela opera numa camada acima, definindo a **forma do conteúdo que viaja dentro da requisição gRPC ou da mensagem MQTT**. É perfeitamente possível (e comum em sistemas multiagentes maduros) publicar uma mensagem estruturada como FIPA-ACL dentro de um payload MQTT, ou dentro do corpo de uma chamada gRPC — os dois níveis (transporte e semântica) são ortogonais/independentes.

> **Modelo mental da FIPA-ACL:** antes de existirem LLMs, agentes já trocavam mensagens estruturadas seguindo um formato clássico (uma expressão simbólica, não um JSON):
> ```
> (request :sender coletor :receiver triagem :content "classificar(ocorrencia-123)"
>           :ontology seguranca-publica :language pt-BR)
> ```
> O `msg_acl()` em Python usado neste material (Seção "Casos de Uso", item 3.2) é uma tradução direta desses mesmos campos para um dicionário — a ideia por trás é idêntica, só a sintaxe muda.

---

### 1. Comunicação A2A Síncrona

No modelo síncrono, a interação opera no paradigma estrito de **pergunta e resposta imediata**. Quando o Agente A invoca o Agente B, o loop de raciocínio do Agente A é pausado até que o Agente B receba o contexto, execute sua própria inferência de LLM (e eventuais _tools_) e retorne a carga de dados.

```text
[ Agente A ] ──── Requisição (A2A) ───► [ Agente B ]
     │                                        │
 (Bloqueado /                               (Processa LLM
  Aguardando)                                + Ferramentas)
     │                                        │
[ Agente A ] ◄─── Resposta Consolidada ── [ Agente B ]
     ▼
 (Retoma Loop)
```

**Principais Desafios em Produção:**

- **Acúmulo de Latência (_Latency Stacking_):** Se um modelo de linguagem leva 3 segundos para responder e o fluxo encadeia 3 agentes em série síncrona, a resposta final levará no mínimo $3 \times 3 = 9$ segundos, gerando degradação de experiência.
- **Propagação de Falhas em Cascata:** Se o Agente B falhar, sofrer _rate limit_ da API ou entrar em loop infinito de ferramentas, o Agente A fica preso aguardando até estourar seu tempo limite (_timeout_).
- **Risco de Impasse Circular (_Deadlock_):** Ocorre quando o Agente A chama o Agente B, e o Agente B, para responder, decide consultar o Agente A. Ambos ficam congelados aguardando a resposta um do outro.

**Quando utilizar:**

- Em validações determinísticas de curto alcance (ex.: um Agente Gerador solicitando aprovação binária sim/não de um Agente Revisor).
- Quando o próximo passo de raciocínio do emissor depende estritamente do dado que será calculado pelo receptor.

---

### 2. Comunicação A2A Assíncrona

No modelo assíncrono, a interação é orientada a **eventos ou mensagens desacopladas**. O Agente A posta uma mensagem (em uma fila, barramento ou despachante de eventos) contendo a tarefa e volta imediatamente a processar outras tarefas ou atender novos usuários. O Agente B consome a mensagem quando tiver capacidade de computação disponível.

A devolução do resultado ocorre via **Callbacks**, **Webhooks** ou publicação em um **Tópico de Eventos Compartilhado**.

```text
[ Agente A ] ─── Publica Evento/Job ───► [ Fila / Broker ]
     │                                           │
(Livre para trabalhar)                           ▼
     │                                     [ Agente B ]
     │                                  (Consome quando livre)
     │                                           │
[ Agente A ] ◄── Notificação / Callback ─────────┘
```

**Principais Vantagens:**

- **Concorrência e Padrão _Scatter-Gather_:** Um Agente Orquestrador pode disparar 10 subtarefas para 10 agentes especialistas simultaneamente (ex.: analisar 10 portarias ou documentos diferentes em paralelo) e agregar as respostas à medida que forem concluídas.
- **Resiliência a Falhas:** Se o Agente B cair ou reiniciar, a mensagem permanece segura na fila de mensagens e será processada assim que o agente se restabelecer, sem derrubar o Agente A.
- **Eficiência de Recursos:** Agentes em nuvem ou locais não gastam memória mantendo conexões abertas enquanto aguardam a conclusão de fluxos demorados.

**Principais Desafios:**

- **Gerenciamento de Estado Distribuído:** Requer uma camada externa de armazenamento (Redis, bancos de dados transacionais) para guardar o estado da conversa e saber qual tarefa pertence a qual contexto.
- **Rastreabilidade e Observabilidade:** Rastrear a causa raiz de uma alucinação torna-se mais difícil quando as mensagens trafegam por múltiplos tópicos assíncronos, exigindo IDs de correlação (_Trace IDs_) em cada cabeçalho.

**Quando utilizar:**

- Tarefas demoradas em lote (_batch processing_), como extração de dados de centenas de páginas em procedimentos investigativos.
- Arquiteturas de enxame (_Swarm_) ou coreografadas, onde múltiplos agentes especializados operam de forma contínua e autônoma sobre uma base de dados compartilhada.

---

### Síntese de Aplicação em Projetos Aplicados

Em sistemas corporativos e institucionais maduros, a arquitetura raramente adota apenas um formato de ponta a ponta. O padrão de referência combina os dois mundos: adota-se **comunicação síncrona internamente** em subgrafos fechados de decisão (como um par Agente + Tool ou Gerador + Crítico resolvendo uma tarefa pontual) e **comunicação assíncrona global** para orquestrar a passagem de bastão entre os diferentes setores, serviços e esteiras do processo institucional.

## Casos de Comunicação A2A

### 1. Comunicação Síncrona: Request-Response Direto (HTTP/REST ou RPC)

No modelo síncrono, a comunicação exige conexão ponto a ponto direta. O Agente Emissor invoca uma rota de rede (endpoint) pertencente ao Agente Receptor e **pausa seu ciclo de execução (_agent loop_)** até que a resposta trafegue de volta pelo canal aberto.

#### Cenário Prático

Um **Agente de Atendimento** recebe a denúncia de um cidadão e, antes de emitir o protocolo final, precisa que o **Agente Jurídico** valide se os fatos relatados configuram crime em tese.

```text
[ Agente Atendimento ]                                      [ Agente Jurídico ]
         │                                                           │
         │─── POST /v1/parecer (HTTP Request) ──────────────────────►│
         │    Payload: {"fato": "subtração de celular com ameaça"}    │ (Inicia inferência
         │                                                           │  do modelo local/nuvem)
   [ BLOQUEADO ]                                                     │
   (Aguarda rede e                                                   │
    processamento)                                                   │
         │                                                           │
         │◄── 200 OK (HTTP Response) ────────────────────────────────│
         │    Payload: {"crime": "Roubo", "artigo": 157}             │
         ▼
(Retoma execução e
responde ao cidadão)
```

#### Implementação Prática em Python

**Serviço do Agente Jurídico (`servidor_juridico.py` com FastAPI):**

```python
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()

class Solicitacao(BaseModel):
    fato: str

@app.post("/v1/parecer")
def analisar_fato(dados: Solicitacao):
    # Simula o raciocínio do LLM/Agente Jurídico
    if "ameaça" in dados.fato.lower():
        return {"enquadramento": "Roubo", "artigo": "Art. 157, CP"}
    return {"enquadramento": "Furto", "artigo": "Art. 155, CP"}
```

**Agente de Atendimento (`agente_atendimento.py`):**

```python
import time
import requests

def executar_agente_atendimento(relato_usuario: str):
    print("[ATENDIMENTO] Recebendo relato do cidadão...")

    # Chamada HTTP síncrona direta: O script BLOQUEIA nesta linha
    print("[ATENDIMENTO] Consultando Agente Jurídico via REST...")
    inicio = time.time()

    resposta = requests.post(
        "http://localhost:8000/v1/parecer",
        json={"fato": relato_usuario},
        timeout=10 # Se o jurídico cair ou demorar >10s, quebra com exceção
    )

    duracao = time.time() - inicio
    dados_juridicos = resposta.json()

    print(f"[ATENDIMENTO] Retorno recebido em {duracao:.2f}s!")
    print(f"[ATENDIMENTO] Conclusão: Caso enquadrado como {dados_juridicos['enquadramento']}.")

if __name__ == "__main__":
    executar_agente_atendimento("Houve subtração do aparelho mediante grave ameaça.")
```

- **Comportamento observado:** O terminal do Atendimento congela durante a requisição. Se o servidor do Jurídico estiver desligado, o Atendimento falha imediatamente com `ConnectionError` ou `Timeout`.

---

### 2. Comunicação Assíncrona: Mensageria e Eventos (Pub/Sub via Broker)

No modelo assíncrono, os agentes não conversam diretamente e não conhecem os endereços IP uns dos outros. O Emissor despacha a mensagem para um **Broker** (como MQTT, RabbitMQ ou Kafka) rotulando-a em um **Tópico** e **libera seu ciclo de execução imediatamente**.

> ⚠️ **Nota prática (LGPD):** os exemplos deste material usam um broker MQTT **público** (`broker.emqx.io`) para fins didáticos — qualquer pessoa no mundo pode publicar ou assinar qualquer tópico nele. Por isso os payloads usam sempre dados fictícios, e cada implantação isola seu tráfego prefixando os tópicos com um namespace próprio (ex.: `pcdf/...`) — sem esse prefixo, o tráfego de diferentes equipes se misturaria no mesmo canal compartilhado. **Nunca publique dado pessoal real num broker público.**

#### Cenário Prático

O **Agente Coletor** insere um novo boletim de ocorrência no sistema. Ele publica o evento no tópico `ocorrencias/novas`. O **Agente de Triagem** e o **Agente de Estatística** estão inscritos no tópico e processam a ocorrência no seu próprio tempo, de forma concorrente e sem interferir no Coletor.

```text
                                  ┌───► [ Agente Triagem ]
                                  │     (Consome via callback e
                                  │      executa classificação LLM)
                                  │
[ Agente Coletor ] ── Publica ──► [ BROKER ]
         │          no Tópico     │
         ▼          (1 milissegundo)
 (Loop liberado:                  │
  coleta próximo BO               │
  imediatamente)                  └───► [ Agente Estatística ]
                                        (Consome via callback e
                                         incrementa contadores sem LLM)
```

#### Implementação Prática em Python (com MQTT / Paho-MQTT)

**Emissor — Agente Coletor (`agente_coletor.py`):**

```python
import json
import paho.mqtt.client as mqtt

# Conecta ao intermediário (broker)
cliente = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
cliente.connect("broker.emqx.io", 1883, 60)

ocorrencia = {
    "id": 4021,
    "tipo": "Furto qualificado",
    "local": "Asa Sul",
    "detalhes": "Objeto subtraído de veículo estacionado."
}

# Publica o evento no tópico estruturado
topico = "pcdf/ocorrencias/novas"
payload = json.dumps(ocorrencia)

print("[COLETOR] Despachando ocorrência no broker...")
cliente.publish(topico, payload)

# O emissor não espera ninguém analisar: desconecta ou passa para o próximo BO
print("[COLETOR] Evento enviado! Agente livre para coletar novos dados imediatamente.")
cliente.disconnect()
```

**Consumidor — Agente de Triagem com LLM (`agente_triagem.py`):**

```python
import json
import paho.mqtt.client as mqtt

# Função executada de forma autônoma apenas QUANDO uma mensagem chegar
def on_message(client, userdata, msg):
    dados = json.loads(msg.payload.decode())
    print(f"\n[TRIAGEM - EVENTO RECEBIDO] Processando ocorrência #{dados['id']}...")
    print(f"[TRIAGEM] Disparando inferência do LLM em segundo plano para enquadramento...")
    # Aqui o Runner.run_sync() do Agente processaria o texto da ocorrência
    print(f"[TRIAGEM] Concluído: Ocorrência #{dados['id']} classificada com sucesso.")

cliente = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
cliente.on_message = on_message

cliente.connect("broker.emqx.io", 1883, 60)
# Assina o tópico de interesse (ouve os eventos de novas ocorrências)
cliente.subscribe("pcdf/ocorrencias/novas")

print("[TRIAGEM] Agente online, aguardando eventos do broker...")
# Mantém o processo ouvindo sem travar outros scripts
cliente.loop_forever()
```

- **O "pulo do gato":** repare que, em nenhum momento, o código do Coletor importa ou referencia o Agente de Triagem (e vice-versa) — os dois só compartilham o *nome* do tópico. Isso é **desacoplamento** na prática: dá para trocar, escalar ou adicionar novos consumidores (como o Agente de Estatística, à frente) sem alterar uma única linha do Coletor.
- **Comportamento observado:** O Coletor executa em cerca de 5 milissegundos e finaliza. Se o Agente de Triagem estiver temporariamente fora do ar por falta de memória ou reiniciando o servidor, a publicação não quebra o Coletor. Assim que a Triagem reconectar, o evento será entregue e processado via `on_message`.

---

### Síntese Operacional das Diferenças

| Característica                   | No Exemplo Síncrono (HTTP/REST)                                                                              | No Exemplo Assíncrono (Pub/Sub Broker)                                                                          |
| -------------------------------- | ------------------------------------------------------------------------------------------------------------ | --------------------------------------------------------------------------------------------------------------- |
| **Endereçamento**                | O Atendimento precisou saber a URL exata do Jurídico (`localhost:8000`).                                     | O Coletor conhecia apenas o nome abstrato do tópico (`pcdf/ocorrencias/novas`).                                 |
| **Tempo de Execução do Emissor** | Tempo da rede + tempo do LLM Jurídico responder (ex.: 3 a 5 segundos).                                       | Apenas o tempo de entregar o pacote TCP ao broker (ex.: ~5 milissegundos).                                      |
| **Escalabilidade**               | Se 50 usuários chamarem o Atendimento ao mesmo tempo, 50 conexões HTTP simultâneas sobrecarregam o Jurídico. | O broker enfileira os eventos; a Triagem consome uma mensagem por vez respeitando sua capacidade computacional. |

---

### 3. Contratos Formais Sobre o Transporte: gRPC e FIPA-ACL

Os Casos 1 e 2 mostraram **como transportar** a mensagem (**REST** _síncrono_, **MQTT** _assíncrono_). Falta mostrar **como formalizar o que viaja dentro dela** — é aqui que **gRPC** (como _contrato de transporte tipado_) e **FIPA-ACL** (como _contrato de conteúdo_) entram.

#### 3.1 gRPC como alternativa tipada ao REST do Caso 1

No Caso 1, o contrato entre Atendimento e Jurídico é implícito: um dicionário JSON (`{"fato": "..."}`) que o FastAPI valida via Pydantic **em tempo de execução**. Em gRPC, o contrato é declarado **antes** da execução, num arquivo `.proto` (a IDL — _Interface Definition Language_), e o compilador `protoc` gera o código cliente/servidor tipado a partir dele:

```protobuf
// juridico.proto — o CONTRATO, compilado antes de qualquer código rodar
syntax = "proto3";

service AgenteJuridico {
  rpc AnalisarFato (Solicitacao) returns (Parecer);
}

message Solicitacao {
  string fato = 1;
}

message Parecer {
  string enquadramento = 1;
  string artigo = 2;
}
```

**Diferença prática em relação ao REST do Caso 1:** se o Agente Jurídico renomear o campo `enquadramento` para `tipificacao` sem atualizar o `.proto`, o código do Agente de Atendimento **nem compila** — o erro aparece antes de qualquer chamada de rede. No REST com JSON solto, não existe essa checagem prévia: `dados_juridicos['enquadramento']` só lançaria um `KeyError` **em tempo de execução**, na primeira vez que um cidadão real disparasse esse fluxo em produção — tarde demais, sem nenhum aviso antes do deploy. É esse tipo de contrato **verificado em tempo de compilação** que justifica o uso de gRPC em integrações A2A críticas entre serviços institucionais.

#### 3.2 FIPA-ACL como contrato de conteúdo (independente do transporte)

Repare que o `analisar_fato` do Caso 1 decide o enquadramento inspecionando texto livre: `if "ameaça" in dados.fato.lower()`. Funciona no exemplo didático, mas é frágil — qualquer variação de escrita (`"ameaçou"`, `"sob ameaça"`, sinônimos) engana o filtro. A FIPA-ACL resolve isso formalizando a **intenção** da mensagem num campo estruturado (`performative`), em vez de escondê-la dentro do texto:

```python
# Implementado em aula4/ex8_fipa_acl.py deste projeto
def msg_acl(performativa: str, sender: str, receiver: str, content: str, **extra) -> dict:
    base = {
        "performative": performativa,   # a INTENÇÃO, como campo estruturado
        "sender": sender,
        "receiver": receiver,
        "content": content,              # o texto livre fica isolado aqui
        "ontology": "seguranca-publica",
        "language": "pt-BR",
    }
    base.update(extra)
    return base

# O receptor decide pela performativa, NUNCA pelo texto livre do content:
if mensagem["performative"] == "request":
    ...  # trata como uma ordem de execução
elif mensagem["performative"] == "inform":
    ...  # trata como um fato declarado, sem ação esperada
```

**Onde isso se encaixa no transporte:** esta mesma mensagem FIPA-ACL pode ser o `payload` publicado via MQTT (Caso 2) ou o corpo de uma requisição gRPC (Seção 3.1) — o contrato de conteúdo é o mesmo, independentemente de qual dos dois transportes você escolher. É a aplicação direta do "Ponto-chave" descrito na Visão Geral: transporte e semântica são camadas distintas.

---

## Handoffs: A2A Síncrono In-Process

Os exemplos até aqui de comunicação síncrona (Casos de Uso, item 1) mostraram A2A **em rede** — dois processos separados, conectados via HTTP. Mas o próprio SDK de agentes (`openai-agents`) oferece um mecanismo de comunicação síncrona **ainda mais direto**: o **handoff**, no qual dois agentes trocam o controle da conversa **dentro do mesmo processo Python**, sem abrir nenhuma porta de rede, sem serializar JSON, sem `requests.post`.

```text
[ Triagem ] ── handoffs=[jurídico] ──► [ decisão do MODELO ]
     │                                          │
     │                     (o modelo decide, lendo as instructions,
     │                      se transfere a conversa)
     ▼                                          ▼
(mesmo processo Python,               [ Jurídico assume a conversa
 nenhuma rede envolvida)                e responde diretamente ]
```

Diferente do Caso 1 (HTTP/REST), aqui não existe um "servidor" e um "cliente" — existe **um único programa Python**, com múltiplos objetos `Agent`, e o SDK decide qual deles responde, turno a turno.

### 1. Handoff Básico

**Cenário:** o Agente de Triagem recebe a ocorrência e, se identificar indício de crime, transfere a conversa inteira para o Agente Jurídico — que passa a responder diretamente, sem a Triagem voltar a intervir.

Implementado em `aula4/ex1_agente_handoff.py`:

```python
from agents import Agent, Runner
from provedor import configurar, modelo

configurar()

juridico = Agent(
    name="Jurídico",
    instructions="Avalie o enquadramento legal da ocorrência e cite o artigo provável.",
    model=modelo(),
)

triagem = Agent(
    name="Triagem",
    instructions=(
        "Classifique a ocorrência (tipo e gravidade). "
        "Se houver indício de crime, encaminhe ao agente Jurídico."
    ),
    model=modelo(),
    handoffs=[juridico],   # <- o SDK transforma isso numa ferramenta "transfer_to_Jurídico"
)

resultado = Runner.run_sync(triagem, "Furto de veículo na Asa Norte, sem vítimas, câmeras próximas.")
print(resultado.final_output)
```

- **Quem decide transferir é o modelo**, lendo as `instructions` da Triagem — nenhuma linha deste código diz `if "crime" in texto: ...`.
- `resultado.last_agent.name` revela quem respondeu de fato (`"Jurídico"`, não `"Triagem"`, se a transferência ocorreu) — é assim que se audita um handoff sem escrever nenhum roteador manual.
- **Comportamento observado:** a chamada inteira acontece dentro de um único `Runner.run_sync()` — não há pacote de rede para inspecionar entre os dois agentes, porque não existe rede nenhuma envolvida.

### 2. Roteamento Entre Múltiplos Especialistas

**Cenário:** a mesma Triagem, agora escolhendo entre **dois** destinos possíveis — Jurídico (se houver crime) ou Estatística (se for só um registro administrativo).

Implementado em `aula4/ex2_agente_handoff_roteamento.py` — a única mudança em relação ao exemplo anterior é a lista `handoffs=[juridico, estatistica]` e uma instrução mais explícita sobre o critério de escolha:

```python
triagem = Agent(
    name="Triagem",
    instructions=(
        "Você tria ocorrências. Se houver indício de crime, encaminhe ao Jurídico. "
        "Se for apenas um registro administrativo sem crime, encaminhe à Estatística."
    ),
    model=modelo(),
    handoffs=[juridico, estatistica],   # <- agora com dois destinos possíveis
)
```

Nenhuma classe nova, nenhum `if/elif` de roteamento — o esforço de "programar um roteador" vira o esforço de **escrever bem as instructions**. O SDK cria uma ferramenta `transfer_to_<nome>` para cada agente da lista; o modelo escolhe no máximo uma, ou nenhuma, se a ocorrência não se encaixar em nenhum dos dois perfis.

### 3. Agente Como Ferramenta (`as_tool`)

**Cenário:** um Agente Coordenador que **não transfere** a conversa — ele consulta especialistas em segundo plano (como quem faz duas ligações internas antes de responder ao cidadão) e monta a resposta final ele mesmo.

Implementado em `aula4/ex3_agente_as_tool.py`:

```python
coordenador = Agent(
    name="Coordenador",
    instructions=(
        "Você coordena o atendimento de uma ocorrência. "
        "Consulte o Jurídico e o Investigador e produza um resumo único "
        "com: enquadramento e próximos passos."
    ),
    model=modelo(),
    tools=[
        juridico.as_tool(
            tool_name="consultar_juridico",
            tool_description="Obtém o enquadramento legal provável da ocorrência.",
        ),
        investigador.as_tool(
            tool_name="consultar_investigador",
            tool_description="Obtém diligências investigativas iniciais.",
        ),
    ],
)
```

`agente.as_tool(...)` empacota um `Agent` inteiro como se fosse uma função `@function_tool` comum — chamar essa "ferramenta" roda um `Runner` completo sobre o especialista e devolve o texto dele como resultado, que o Coordenador consome e decide o que fazer com ele.

**A diferença que importa entre Handoff e `as_tool`:**

| | Handoff (Seções 1 e 2) | `as_tool()` (Seção 3) |
|---|---|---|
| **Quem responde ao usuário** | O especialista que recebeu a transferência | Sempre o Coordenador |
| **Controle da conversa** | Passa de vez para o especialista | O Coordenador nunca abre mão do controle |
| **Analogia** | "Transfiro a ligação" | "Consulto um especialista e sigo a chamada" |
| **`resultado.last_agent`** | Muda conforme quem assumiu | Sempre o Coordenador |

**Comportamento observado (testado no projeto):** no `ex3`, `resultado.last_agent.name` é **sempre** `"Coordenador"` — nunca `"Jurídico"` nem `"Investigador"` diretamente, mesmo que os dois especialistas tenham sido consultados durante a execução.

### Desafios e Quando Utilizar

**Principais Desafios:**

- **Acoplamento de instruções:** o comportamento do roteamento depende inteiramente de quão bem escritas estão as `instructions` do agente que decide — instruções ambíguas geram handoffs incorretos ou indecisão do modelo.
- **Ausência de rede não significa ausência de custo:** cada handoff ainda dispara uma nova chamada de inferência ao LLM — o *Acúmulo de Latência* (Seção "Comunicação A2A Síncrona") continua valendo, só sem o custo adicional de rede.
- **Auditoria exige atenção:** como não há requisição HTTP para inspecionar em nenhuma ferramenta de rede, rastrear "quem decidiu o quê" depende inteiramente de `resultado.last_agent` e de instrumentação própria (hooks/tracing, já vista na Aula 3 deste curso).

**Quando utilizar:**

- Quando os agentes envolvidos rodam **no mesmo processo/serviço** — não há necessidade de escalar componentes de forma independente.
- **Handoff:** quando o especialista deve assumir a conversa por completo (ex.: uma mesa de triagem que direciona o atendimento).
- **`as_tool`:** quando um coordenador precisa **consolidar** informações de vários especialistas numa única resposta final (ex.: um relatório que cita parecer jurídico + diligências investigativas).

---

## MQTT Distribuído: A2A Assíncrono Entre Processos

O Caso de Uso "Comunicação Assíncrona" (item 2, Coletor → Triagem) já apresentou o mecanismo básico de Pub/Sub. Este capítulo aprofunda o mesmo cenário com os padrões que tornam o MQTT útil em produção: um **terceiro assinante** sem tocar no publisher, a emulação de **Request/Reply** sobre um barramento que é nativamente Pub/Sub, e uma **esteira (pipeline)** de agentes encadeados só por tópico. Os três reaproveitam a mesma infraestrutura (broker, `PREFIXO`, `paho-mqtt`) já descrita naquela seção.

### 1. Fan-out: Um Terceiro Assinante

**Cenário:** sem tocar em uma única linha do Agente Coletor, adiciona-se um Agente de Estatística que também assina `{PREFIXO}/ocorrencias/#` — mas, diferente da Triagem, não usa LLM: só conta ocorrências por tipo.

Implementado em `aula4/ex6_mqtt_estatistica.py`:

```python
from collections import Counter
contagem = Counter()

def on_message(client, userdata, msg):
    oc = json.loads(msg.payload)
    contagem[oc.get("tipo", "desconhecido")] += 1
    print("Ocorrências por tipo:", dict(contagem))

cli = mqtt.Client(callback_api_version=mqtt.CallbackAPIVersion.VERSION2)
cli.on_message = on_message
cli.connect(BROKER, PORT)
cli.subscribe(f"{PREFIXO}/ocorrencias/#")   # MESMO tópico já assinado pela Triagem
cli.loop_forever()
```

**Comportamento observado (testado no projeto):** rodando Triagem e Estatística ao mesmo tempo e publicando uma única vez com o Coletor, **os dois recebem a mesma mensagem, de forma independente** — é o *Fan-out* do Dicionário (Seção 3) acontecendo na prática, sem nenhuma mudança no publisher.

### 2. Request/Reply Sobre MQTT

**Cenário:** o MQTT é nativamente Pub/Sub — não existe "pedir e receber resposta" pronto no protocolo. Simula-se isso com **dois tópicos e dois papéis**: um cliente (Triagem) que pede um parecer, e um serviço (Jurídico) que responde por outro canal.

| Tópico | Quem publica | Quem assina |
|---|---|---|
| `{PREFIXO}/juridico/analisar` | cliente (Triagem) | serviço (Jurídico) |
| `{PREFIXO}/juridico/resposta` | serviço (Jurídico) | cliente (Triagem) |

Serviço, implementado em `aula4/ex7_juridico_servico.py`:

```python
def on_message(client, userdata, msg):
    pedido = json.loads(msg.payload)
    parecer = rodar(criar_agente, str(pedido)).final_output
    resposta = {"id": pedido.get("id"), "parecer": parecer}
    client.publish(f"{PREFIXO}/juridico/resposta", json.dumps(resposta))
```

Cliente, implementado em `aula4/ex7_triagem_cliente.py`:

```python
cli.subscribe(f"{PREFIXO}/juridico/resposta")   # 1) assina a resposta ANTES
cli.loop_start()
cli.publish(f"{PREFIXO}/juridico/analisar", json.dumps(pedido))   # 2) só então publica o pedido
```

**⚠️ Ordem crítica:** o cliente assina a resposta **antes** de publicar o pedido. Se publicasse primeiro, e o serviço respondesse rápido o bastante, a resposta poderia chegar ao broker antes de a assinatura existir — e se perder, já que o MQTT não retém mensagens para quem assina depois do envio (ver *Idempotência em Reentrega* e *Filas de Mensageria* no Dicionário para os dois lados desse mesmo problema: duplicidade e perda).

**Comportamento observado (testado no projeto):** do ponto de vista do cliente, "parece" síncrono — pediu, recebeu. Mas por baixo são **dois processos, dois tópicos**, e nenhuma garantia de resposta se o serviço cair no meio do caminho.

### 3. Pipeline: Esteira de Agentes

**Cenário:** três estágios encadeados só pelo nome do tópico — a saída de um vira a entrada do próximo, sem que nenhum estágio conheça a implementação dos vizinhos.

```text
ex9_pipeline_coletor.py   --publica-->  {PREFIXO}/pipeline/entrada
ex9_pipeline_triagem.py   --assina .../entrada, classifica, publica-->  {PREFIXO}/pipeline/juridico
ex9_pipeline_juridico.py  --assina .../juridico, dá o parecer final (fim da esteira)
```

O estágio do meio faz as duas coisas ao mesmo tempo — assina um tópico **e** publica em outro, dentro do mesmo `on_message` (`aula4/ex9_pipeline_triagem.py`):

```python
def on_message(client, userdata, msg):
    oc = json.loads(msg.payload)
    classificacao = rodar(criar_agente, str(oc)).final_output
    saida = {"id": oc.get("id"), "relato": oc.get("relato"), "classificacao": classificacao}
    client.publish(f"{PREFIXO}/pipeline/juridico", json.dumps(saida))
```

**Comportamento observado (testado no projeto):** publicando uma vez no Coletor, a ocorrência atravessou os três processos — a Triagem classificou e repassou, o Jurídico recebeu o dado já enriquecido e produziu o parecer final — sem que nenhum dos três importasse ou referenciasse os outros diretamente.

**Pergunta de reflexão (a mesma que o material propõe):** o que aconteceria se o estágio da Triagem caísse **depois** de consumir uma mensagem, mas **antes** de publicar a saída? A mensagem se perde em trânsito — o Coletor nem percebe, e o Jurídico nunca a recebe, porque não há fila persistente retendo o dado nesse desenho (ver *Pipeline* no Dicionário, Seção 4).

### Desafios e Quando Utilizar

**Principais Desafios:**

- **Consistência de `PREFIXO`:** os três (ou mais) processos precisam concordar exatamente no mesmo prefixo de tópico — um valor padrão divergente entre arquivos quebra o encontro silenciosamente (sem erro; a mensagem só nunca chega).
- **Sem fila persistente, sem replay:** os padrões desta seção usam MQTT "puro" — se um consumidor não estiver online no instante da publicação, ele não recebe a mensagem retroativamente (diferente de Kafka, que retém um log reproduzível).
- **Correlação de mensagens:** no Request/Reply, é o campo `id` no payload que permite ao cliente casar a resposta certa com o pedido certo — sem ele, respostas de pedidos concorrentes se confundiriam.

**Quando utilizar:**

- **Fan-out:** quando múltiplos processos independentes precisam reagir ao mesmo evento sem que o publisher saiba da existência deles.
- **Request/Reply sobre Pub/Sub:** quando já existe uma infraestrutura de broker MQTT e não vale a pena abrir uma porta HTTP só para uma consulta pontual.
- **Pipeline:** quando um processamento se decompõe naturalmente em estágios sequenciais, e cada estágio se beneficia de rodar (e escalar) como um processo independente.

---

## DICIONÁRIO

### 1. Fundamentos de Execução e Dinâmica Temporal

**Event Loop (Laço de Eventos)**

- **Conceito:** Mecanismo interno assíncrono que gerencia, pausa e retoma a execução de tarefas concorrentes em uma única thread, sem travar o processador enquanto aguarda operações lentas de rede ou disco.
- **No contexto A2A:** Permite que um único agente orquestrador dispare requisições simultâneas para dezenas de agentes externos e continue processando eventos locais enquanto espera as respostas chegarem.

**Acoplamento Temporal (_Temporal Coupling_)**

- **Conceito:** Grau de dependência cronológica entre dois sistemas.
  - **Alto Acoplamento** quando emissor e receptor precisam estar disponíveis e ativos no mesmo milissegundo para que a interação ocorra.
  - **Baixo Acoplamento** quando emissor e receptor não precisam estar disponíveis e ativos simultaneamente, ou seja, podem estar com processamento desacoplado/diferido.
- **No contexto A2A:** Em interações síncronas (`Runner.run_sync`), o Agente A fica congelado até o Agente B concluir seu raciocínio. No desacoplamento temporal (assíncrono), o Agente A envia a demanda e segue sua execução, permitindo que o Agente B a processe quando tiver capacidade computacional disponível.

**Deadlock (Impasse / Bloqueio Mútuo)**

- **Conceito:** O estado em que dois ou mais processos ficam paralisados para sempre porque cada um depende da liberação de um recurso ou resposta mantida pelo outro.
- **No contexto A2A:** Ocorre quando o Agente A chama síncronamente o Agente B e fica em espera bloqueante, mas o Agente B, para formular sua resposta, consulta o Agente A de volta. O ciclo se congela até o estouro de _timeout_.

**Request/Response (Pergunta e Resposta)**

- **Conceito:** Padrão fundamental de troca de mensagens no qual um emissor formula um pedido e aguarda uma resposta direta e correlacionada antes de prosseguir — um dos três padrões estruturais de comunicação entre sistemas, ao lado de Pub/Sub e Filas de Mensageria (ver Seção 3).
- **No contexto A2A:** É o padrão por trás tanto do *handoff* do SDK (Seção 2 a seguir, dentro do mesmo processo) quanto de chamadas em rede como HTTP/REST e gRPC (ver "Casos de Uso", itens 1 e 3.1). Em todos os casos o emissor permanece bloqueado — a diferença entre eles está em *onde* o bloqueio acontece (dentro do processo ou através da rede), não na lógica do padrão em si.

---

### 2. Coordenação Síncrona no Mesmo Processo (_In-Process A2A_)

**Handoff (Passagem de Bastão)**

- **Conceito:** Padrão de transferência total de controle no qual o agente emissor delega a responsabilidade da interação para outro agente especialista.
- **No contexto A2A:** O agente emissor sai de cena por completo. O agente receptor assume a conversa diretamente com o chamador, tornando-se o autor registrado da resposta final (`resultado.last_agent`). A decisão de transferir é tomada pelo próprio LLM interpretando suas diretrizes (`instructions`).

**Agente como Ferramenta (`as_tool`)**

- **Conceito:** Padrão de subordinação hierárquica no qual um agente especialista é encapsulado e exposto como se fosse uma função executável comum (`@function_tool`).
- **No contexto A2A:** Diferente do Handoff, o coordenador **mantém o controle integral**. Ele consulta o especialista em segundo plano para extrair um dado ou parecer, mas o especialista nunca fala diretamente com o usuário — o coordenador é sempre o responsável final pela consolidação (`last_agent`).

---

### 3. Mecanismos de Transporte e Desacoplamento Distribuído

**Callback (Chamada de Retorno)**

- **Conceito:** Mensagem ou instrução: _"quando o seu processamento terminar, execute esta rotina específica entregando o resultado"_.
- **No contexto A2A:** Evita que o emissor fique consultando repetidamente se uma tarefa longa terminou (_polling_). O emissor fornece um ponto de entrada para ser notificado assim que o trabalho do receptor for concluído.

**Webhook**

- **Conceito:** Um callback implementado sobre a arquitetura da web via requisições HTTP (geralmente `POST`) disparadas automaticamente por eventos.
- **No contexto A2A:** Quando dois agentes rodam em servidores completamente isolados, o Agente B envia um payload JSON para o endpoint HTTP exposto pelo Agente A assim que terminar uma análise pericial demorada.

**Broker (Intermediário de Mensagens)**

- **Conceito:** Um servidor central desacoplador responsável por receber mensagens de emissores e encaminhá-las aos destinatários registrados, sem que as pontas se conheçam diretamente.
- **No contexto A2A:** Agentes não precisam armazenar IPs ou portas de outros agentes. Todos os nós do sistema conectam-se unicamente ao broker (ex.: Mosquitto, EMQX), que gerencia o roteamento lógico da rede.

**Descoberta de Serviço (_Service Discovery_)**

- **Conceito:** O mecanismo (manual ou automático) pelo qual um emissor descobre *para onde* enviar uma mensagem — o endereço de rede de um serviço síncrono, ou o nome do tópico correto num barramento assíncrono — sem que esse endereço precise ser fixado (_hardcoded_) no código para sempre.
- **No contexto A2A:** Nos exemplos deste material, a descoberta é **estática e combinada por convenção** (a URL `localhost:8000` do Caso 1, ou o tópico `pcdf/ocorrencias/novas` do Caso 2, ambos escritos diretamente no código). Em sistemas institucionais maiores, isso evolui para um **registro de serviços** (ex.: Consul, DNS interno) ou para convenções de nomenclatura de tópicos versionadas — sem isso, adicionar um novo agente exige recompilar/reimplantar quem precisa falar com ele, o que anula boa parte do ganho de desacoplamento do Pub/Sub.

**MQTT (_Message Queuing Telemetry Transport_)**

- **Conceito:** Protocolo leve de mensageria Pub/Sub sobre TCP/IP, originalmente concebido para redes restritas de telemetria e dispositivos IoT. Opera com cabeçalhos binários mínimos, oferece três níveis de garantia de entrega (_QoS 0, 1 e 2_) e depende obrigatoriamente de um broker central para rotear as mensagens entre publicadores e assinantes.
- **Origem:** Criado pela IBM em 1999 para monitorar oleodutos remotos via rádio, num cenário de banda praticamente nula — o que explica a leveza extrema do protocolo. Hoje é o protocolo dominante em IoT (sensores, casas conectadas, veículos); o Facebook Messenger chegou a rodar sobre MQTT em seus primeiros anos.
- **No contexto A2A:** É o protocolo de transporte utilizado nos exemplos de código deste material (via biblioteca `paho-mqtt`) para viabilizar a comunicação assíncrona entre agentes. Sua leveza permite que o Agente Coletor publique uma ocorrência em poucos milissegundos e libere seu ciclo de execução imediatamente, sem jamais conhecer o endereço de rede dos Agentes Triagem ou Estatística que consomem o mesmo tópico.

**Tópico (_Topic_) e Curinga (_Wildcard_)**

- **Conceito:** Strings estruturadas de forma hierárquica (ex.: `orgao/setor/acao`) utilizadas como canais de endereçamento lógico. O MQTT define dois curingas: `#` (multinível — assina uma ramificação inteira de uma vez) e `+` (nível único — substitui exatamente um segmento do caminho).
- **No contexto A2A:** Permite segmentar o tráfego institucional. Um agente pode monitorar estritamente `pcdf/pericias/balistica`, usar `pcdf/pericias/#` para consumir todas as perícias de todas as especialidades da corporação de uma só vez, ou `pcdf/+/novas` para ouvir apenas as novas ocorrências de qualquer setor, sem entrar nos subníveis de cada um.

**Pub/Sub (_Publish/Subscribe_ — Publicação/Assinatura)**

- **Conceito:** Padrão de mensageria onde emissores (_Publishers_) apenas etiquetam mensagens em tópicos e consumidores (_Subscribers_) apenas escutam os tópicos de seu interesse, existindo anonimato total entre as partes.
- **No contexto A2A:** Desacopla o ciclo de vida dos agentes. Um agente coletor pode publicar registros mesmo que nenhum agente processador esteja conectado naquele instante, ou mesmo que existam dez ouvintes simultâneos.

**Fan-out (Dispersão / 1-para-Muitos)**

- **Conceito:** Comportamento nativo do Pub/Sub de replicar uma única mensagem postada para todos os assinantes registrados naquele canal.
- **No contexto A2A:** Uma ocorrência publicada uma única vez pelo Coletor é recebida simultaneamente pelo Agente de Triagem com IA (para classificação) e pelo Agente Estatístico sem IA (para contagem métrica), sem sobrecarga adicional sobre o emissor.

**Filas de Mensageria (_Message Queues_ — RabbitMQ / Kafka)**

- **Conceito:** Estruturas de armazenamento intermediário que retêm mensagens de forma persistente e ordenada até que um trabalhador as processe e confirme o recebimento (_ACK_).
- **No contexto A2A:** Resolve o problema de perda de dados do MQTT puro. Se o Agente Pericial cair ou reiniciar no meio da triagem, a tarefa permanece guardada na fila do broker e será retomada assim que o agente se restabelecer.

**Idempotência em Reentrega (_Delivery Idempotency_)**

- **Conceito:** Propriedade de uma operação que produz **exatamente o mesmo resultado final**, não importa quantas vezes seja executada com a mesma entrada — executar uma vez ou dez vezes deixa o sistema no mesmo estado.
- **No contexto A2A:** O MQTT com QoS 1 ("pelo menos uma vez") pode **entregar a mesma mensagem duas vezes** em cenários de rede instável — o protocolo prioriza garantir a entrega sobre evitar duplicidade. Um Agente de Triagem que, ao receber a mesma ocorrência duas vezes, simplesmente rodasse a classificação e publicasse o resultado de novo seria inofensivo (é só uma leitura reprocessada). Já um Agente que **registra** a ocorrência num sistema (ex.: gera um número de protocolo) precisa de uma **chave de idempotência** (ex.: um hash dos campos da mensagem) para reconhecer "já processei isso" e não duplicar o registro — o mesmo princípio de retry seguro já visto na Aula 3 deste curso, agora aplicado à entrega de mensagens em vez de à chamada de uma ferramenta.

---

### 4. Topologias e Padrões de Fluxo A2A

**Request/Reply sobre Pub/Sub**

- **Conceito:** A emulação do padrão síncrono de pergunta-e-resposta utilizando dois tópicos unidirecionais distintos em um barramento assíncrono.
- **No contexto A2A:** O agente requisitante assina o canal `.../resposta`, publica sua solicitação no canal `.../requisicao` e aguarda o retorno assíncrono do prestador, garantindo rastreabilidade sem abrir mão do broker.
- **⚠️ Ordem crítica:** o requisitante precisa **assinar o tópico de resposta ANTES de publicar o pedido**. Se publicasse primeiro, e o prestador respondesse rápido o bastante, a resposta poderia chegar ao broker antes de a assinatura existir — e se perder, já que o MQTT não retém mensagens para quem assina depois do envio (diferente de uma fila persistente; ver *Filas de Mensageria* acima).

**Pipeline (Esteira de Agentes)**

- **Conceito:** Uma topologia linear em série na qual a saída de um agente torna-se automaticamente a entrada do próximo estágio através de tópicos intermediários encadeados.
- **No contexto A2A:** O Agente Coletor publica em `.../entrada`; o Agente de Triagem lê a entrada, classifica com LLM e publica em `.../juridico`; o Agente Jurídico consome o dado enriquecido e gera a peça final. Nenhum estágio conhece a implementação dos vizinhos.
- **Limitação a considerar:** se um estágio intermediário (ex.: a Triagem) cair depois de consumir uma mensagem mas antes de publicar a saída, a mensagem se perde em trânsito — o estágio anterior nunca fica sabendo, e o próximo nunca a recebe, porque não há fila persistente retendo o dado nesse desenho. Resolver isso exige trocar o MQTT puro por *Filas de Mensageria* em pontos críticos da esteira.

**Scatter-Gather (Dispersar-Agrupar)**

- **Conceito:** Padrão arquitetural composto por duas fases: quebrar e despachar subtarefas concorrentes para vários nós especializados (_scatter_) e recolher/fundir as respostas em um produto unificado (_gather_).
- **No contexto A2A:** Um Agente Investigador recebe um caso, dispara simultaneamente subconsultas para os agentes da Receita, Trânsito e Cartório e aguarda todas as devolutivas para montar um único relatório patrimonial integrado.

---

### 5. Contratos Formais e Protocolos de Integração

**Contrato / Protocolo de Comunicação**

- **Conceito:** Acordo técnico definido **antes** da execução — seja por convenção documental, esquema tipado ou padrão de mensagem — que especifica o formato, os campos obrigatórios e o significado dos dados trocados entre duas partes, permitindo que ambas interpretem a mensagem sem ambiguidade.
- **No contexto A2A:** É a camada que fica por baixo da decisão síncrono/assíncrono. Um contrato pode atuar na camada de **transporte** (gRPC para RPC tipado, MQTT para Pub/Sub) ou na camada de **semântica do conteúdo** (FIPA-ACL, que formaliza a intenção da mensagem independentemente de qual transporte a carrega). As duas camadas são ortogonais: um contrato de conteúdo pode viajar dentro de qualquer um dos transportes.

**FIPA-ACL (_Agent Communication Language_)**

- **Conceito:** Padrão formal clássico que estrutura a troca de dados entre agentes de software baseando-se na pragmática da linguagem e na Teoria dos Atos de Fala.
- **No contexto A2A:** Substitui o envio de mensagens em texto solto por estruturas semânticas rígidas contendo remetente (`sender`), destinatário (`receiver`), vocabulário (`ontology`) e intenção de controle (`performative`).

**Performativa (_Performative_)**

- **Conceito:** O parâmetro dentro da FIPA-ACL que explicita a força comunicativa e o propósito da ação (ex.: `request` para ordenar uma tarefa, `inform` para declarar um fato, `query` para interrogar).
- **No contexto A2A:** Permite que o código de roteamento do agente receptor tome decisões determinísticas inspecionando uma chave estruturada (`if msg.performative == "request"`), dispensando inferências caras ou incertas de LLMs sobre textos livres.

**Ontologia (_Ontology_)**

- **Conceito:** O esquema formal que estabelece as entidades, relacionamentos e restrições de significado dentro de um domínio de aplicação específico.
- **No contexto A2A:** Impede ambiguidades operacionais entre agentes distintos. Garante, por exemplo, que a palavra `"laudo"` tenha rigorosamente a mesma tipagem e campos de validação tanto para o Agente Pericial quanto para o Agente Correcional.

**gRPC e Protocol Buffers (_Protobuf_)**

- **Conceito:** Protocolo de alta performance criado pela Google para invocações remotas que adota serialização binária compacta (Protobuf) sobre transporte HTTP/2.
- **Origem:** Criado pela Google em 2015 a partir de um sistema RPC interno chamado *Stubby*, usado havia mais de uma década dentro da empresa; o "g" do nome é recursivo (referência à própria Google) e não tem significado fixo definido. Hoje é o padrão de fato em arquiteturas de microsserviços — usado por Google, Netflix, Uber e pelo próprio Kubernetes.
- **No contexto A2A:** Usado como alternativa ao JSON para conexões síncronas de baixíssima latência e validação estrita de tipos entre microsserviços de agentes rodando em containers diferentes.

**IDL (_Interface Definition Language_) / Arquivo `.proto`**

- **Conceito:** Linguagem de definição de interface na qual o contrato de um serviço gRPC (métodos disponíveis, formato de requisição e resposta) é declarado **antes** de qualquer implementação, num arquivo `.proto` compilado pelo `protoc`.
- **No contexto A2A:** É o que torna o contrato entre dois agentes **verificável em tempo de compilação**: se um campo mudar de nome sem atualizar o `.proto`, o código que depende dele deixa de compilar — em vez de falhar silenciosamente em produção, como pode ocorrer com um payload JSON solto.

**Stub (Código Cliente Gerado)**

- **Conceito:** O código cliente gerado automaticamente pelo `protoc` a partir do arquivo `.proto`, que expõe o serviço remoto como se fosse uma chamada de função local.
- **No contexto A2A:** Permite que o Agente Emissor invoque o Agente Receptor (`stub.AnalisarFato(solicitacao)`) sem escrever manualmente a serialização, a abertura de conexão HTTP/2 ou o parsing da resposta — tudo isso fica encapsulado pelo stub, gerado a partir do mesmo contrato que o servidor implementa.

**MCP (_Model Context Protocol_)**

- **Conceito:** Protocolo aberto criado para padronizar a forma como agentes de IA descobrem, autenticam e consultam bases de dados relacionais, arquivos locais e serviços corporativos.
- **No contexto A2A:** Evita a proliferação caótica de ferramentas ad-hoc. Em vez de cada desenvolvedor escrever conectores customizados, o agente conecta-se de maneira uniforme a servidores MCP (como SQLite ou Git) controlados por listas de permissão.

---

### 6. Rastreabilidade e Segurança Institucional

**Trace ID / Correlation ID (Identificador de Correlação)**

- **Conceito:** Um identificador criptográfico ou numérico único gerado no ponto de entrada de uma transação e propagado nos cabeçalhos de todas as mensagens subsequentes.
- **No contexto A2A:** Fundamental para auditoria pericial. Em uma esteira multiagente com múltiplos handoffs e tópicos MQTT, o _Trace ID_ permite que a corregedoria isole todos os logs e identifique com precisão qual agente causou uma eventual alucinação ou falha.

**Prompt Injection Indireta (_Indirect Prompt Injection_)**

- **Conceito:** Vetor de vulnerabilidade em que dados não confiáveis inseridos em ferramentas externas (sites, e-mails, bancos ou mensagens de outros nós) contêm instruções maliciosas ocultas que manipulam as instruções originais do agente receptor.
- **No contexto A2A:** Explica o perigo de agentes tomarem decisões de controle baseando-se no corpo de texto livre (`content`). Separar dados de comandos através de contratos formais (como as performativas da FIPA-ACL) atua como barreira defensiva contra o sequestro de contexto do agente.
