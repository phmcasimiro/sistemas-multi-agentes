# Aula 4: Comunicação Agente-a-Agente (A2A)

Esta aula muda o foco de *o que um agente sabe fazer sozinho* (Aulas 1-3) para *como vários agentes conversam entre si*. O deck do professor (`aula4_A2A.pdf`, Unidade 8 · PCDF) resume o percurso em uma frase: **do 1 agente para vários — síncrono (handoffs), assíncrono (MQTT), e os contratos que dão forma a essas trocas.**

> **Infraestrutura reaproveitada:** o mesmo `provedor.py` da raiz do curso (`configurar()`, `modelo()`) e o mesmo `.env` — com três variáveis novas só desta aula (`MQTT_BROKER`, `MQTT_PORT`, `MQTT_PREFIXO`). Nada na Aula 4 troca de infraestrutura, só o *mecanismo* de conversa entre agentes.

---

## 0. Roadmap de Aprendizagem

| # | Bloco do deck | Ideia central | Exercícios | Status | Arquivo(s) |
|---|---|---|---|---|---|
| 02 | Setup | Confirmar que `provedor.py`/`.env` funcionam antes de tudo | — | ✅ | `teste.py` |
| 06 | Lab 1 — Handoffs | A2A **síncrono**, no mesmo processo | 1, 2, 3 | ✅ | `ex1_agente_handoff.py`, `ex2_agente_handoff_roteamento.py`, `ex3_agente_as_tool.py` |
| 08 | Lab 2 — MQTT Pub/Sub | A2A **assíncrono**, entre processos, via broker | 4, 5 | ✅ | `ex4_mqtt_pub.py`, `ex5_mqtt_sub.py` |
| 09 | Desafio guiado | Um terceiro assinante (fan-out sem tocar no publisher) | 6 | ✅ | `ex6_mqtt_estatistica.py` |
| 10 | Ex 7 — Request/Reply | Pedir parecer e aguardar resposta, por tópicos | 7 | ✅ | `ex7_juridico_servico.py`, `ex7_triagem_cliente.py` |
| 07 | Contratos: FIPA-ACL, gRPC, MQTT | O "idioma" que dá forma às trocas entre agentes | 8 | ✅ | `ex8_fipa_acl.py` |
| 11 | Ex 9 — Pipeline | Encadear estágios só pelo tópico (esteira) | 9 | ✅ | `ex9_pipeline_coletor.py`, `ex9_pipeline_triagem.py`, `ex9_pipeline_juridico.py` |

**Como usar este roadmap:** as 9 seções do deck estão implementadas nesta pasta. Siga a ordem 1→9 da tabela para estudar — cada bloco pressupõe o anterior (o Exercício 9, por exemplo, é literalmente a soma do Lab 2 com o Exercício 7).

---

## 1. Síncrono × Assíncrono: o eixo da aula inteira

```mermaid
flowchart TD
    subgraph Sincrono["Comunicação Síncrona (In-Process / Handoff)"]
        A1["Agente Triador"] -->|Bloqueia e transfere turno| B1["Agente Jurídico"]
        B1 -->|Retorna resposta| A1
    end

    subgraph Assincrono["Comunicação Assíncrona (Distribuída / MQTT Pub-Sub)"]
        Pub["Agente Coletor (Publisher)"] -->|Publica no tópico\npcdf/demo/ocorrencias/nova| Broker["Broker MQTT\n(EMQX / Mosquitto)"]
        Broker -->|Entrega evento| Sub1["Agente Triagem (Subscriber com LLM)"]
        Broker -->|Entrega cópia (Fan-Out)| Sub2["Agente Estatística (Subscriber Analítico)"]
    end
```

Tudo que a Aula 4 ensina se encaixa numa dessas duas colunas (deck, slide "Síncrono × assíncrono"):

| | Síncrono | Assíncrono |
|---|---|---|
| **Analogia do deck** | Um telefonema: A liga para B e fica esperando | Um recado: A publica e segue a vida |
| **Como se comporta** | Simples de raciocinar e depurar | Mais resiliente e escalável; desacopla os agentes |
| **Ponto fraco** | Ruim quando B demora, cai, ou há muitos pedidos ao mesmo tempo | Abre mão da resposta imediata; ganha complexidade nova (ordem, entrega) |
| **No código** | `Runner.run_sync(...)` **bloqueia** — a linha seguinte só roda com a resposta em mãos | `cli.publish(...)` **não espera** — quem assinou processa quando puder |
| **Implementado em** | `ex1`, `ex2`, `ex3` (handoff / `as_tool`) | `ex4`, `ex5`, `ex6` (MQTT Pub/Sub) |

> **Regra prática do deck:** precisa da resposta agora pra continuar? Síncrono. É uma notificação que outros processam no próprio ritmo? Assíncrono. Um sistema real quase sempre mistura os dois — como esta própria aula mistura handoff (dentro de cada agente) com MQTT (entre agentes).

---

## 2. Lab 1 — Handoffs (A2A síncrono, no mesmo processo)

**Teoria (slide "Handoff"):** é a forma mais simples de A2A no SDK — em vez de chamar uma função Python comum (como as `@function_tool` da Aula 1), um agente passa o "bastão" da conversa para **outro agente**, que assume e responde no lugar dele. Tudo síncrono, no mesmo processo — nenhuma rede envolvida ainda. `handoffs=[...]` diz ao modelo "você pode delegar para estes agentes, se achar que faz sentido" — quem decide **se** delega é sempre o modelo, lendo as `instructions`, nunca um `if/else` escrito à mão.

### 2.1 Exercício 1 — Handoff básico (`ex1_agente_handoff.py`)

Um agente Triagem com `handoffs=[juridico]`: se a ocorrência tiver indício de crime, a Triagem transfere para o Jurídico, que responde no lugar dela. `resultado.last_agent.name` é como se audita **quem respondeu de fato** depois de um handoff.

### 2.2 Exercício 2 — Roteamento entre múltiplos especialistas (`ex2_agente_handoff_roteamento.py`)

**O que muda (slide "O que muda"):** nenhuma classe nova — só uma lista maior em `handoffs=[juridico, estatistica]` e uma instrução mais explícita sobre o critério de escolha. O esforço vai para escrever bem as `instructions`, não para programar um roteador.

### 2.3 Exercício 3 — Agente como ferramenta, `as_tool` (`ex3_agente_as_tool.py`)

**A diferença crucial (slide "Agente como ferramenta"): quem fica no comando.**

| | Handoff | `as_tool()` |
|---|---|---|
| Quem responde | O outro agente | O coordenador, que consolida |
| Controle | Passa o bastão de vez | O coordenador continua no comando |
| Analogia do deck | "Transfiro a ligação" | "Consulto um especialista e sigo a chamada" |

No código, isso vira `agente.as_tool(tool_name=..., tool_description=...)`, que empacota um `Agent` inteiro como se fosse uma função `@function_tool` — chamar essa "ferramenta" roda um `Runner` completo sobre o especialista e devolve o texto dele como resultado. `tool_description` cumpre, para uma tool, o mesmo papel que `handoff_description` cumpre para um destino de handoff.

**O que observar (testado neste repo):** no `ex3`, `resultado.last_agent.name` é **sempre** `"Coordenador"` — nunca `"Jurídico"` nem `"Investigador"` diretamente. Isso não acontece no `ex1`/`ex2`, onde `last_agent` muda conforme quem assumiu a conversa.

> **Nota de implementação:** os nomes dos agentes têm acento (`"Jurídico"`, `"Estatística"`). O SDK monta o nome da ferramenta de handoff a partir do `name` (`"Jurídico"` → `"transfer_to_Jurídico"`) e depois normaliza para caber nas regras de function calling, virando `"transfer_to_jur_dico"` — um aviso aparece no terminal, mas é só informativo; o roteamento funciona normalmente.

---

## 3. Contratos: FIPA-ACL, gRPC e MQTT

**Por que isso importa (slide "Como isso vira contrato"):** *padrão* (Request/Response, Pub/Sub, Mensageria/Filas — ver Seção 4) é o **formato** da conversa; *protocolo/contrato* é o **acordo técnico** que a torna possível. Três contratos citados no deck:

- **MQTT** (Message Queuing Telemetry Transport) — criado pela IBM em 1999 para monitorar oleodutos remotos por rádio, com banda quase zero. Hoje é o protocolo dominante em IoT. É o transporte usado pelos exercícios 4-6 desta pasta.
- **gRPC** (gRPC Remote Procedure Calls) — criado pelo Google em 2015, roda sobre HTTP/2 + Protocol Buffers (binário compacto, não JSON texto). Padrão de fato em microsserviços (Google, Netflix, Uber, Kubernetes). Não implementado nesta pasta — citado como contrato de Request/Response tipado.
- **FIPA-ACL** — a "linguagem clássica" de agentes: antes dos LLMs, agentes já trocavam mensagens padronizadas. Toda mensagem carrega uma **intenção** (`performative`: `request`, `inform`, `query`...), não só um texto — mais `sender`/`receiver` (remetente/destinatário), `content` (o que está sendo pedido/informado) e `ontology`/`language` (domínio e idioma do conteúdo). Exemplo do deck:

  ```
  (request :sender coletor :receiver triagem :content "classificar(ocorrencia-123)"
            :ontology seguranca-publica :language pt-BR)
  ```

### Exercício 8 — Colocando a performativa em prática (`ex8_fipa_acl.py`)

`msg_acl(performativa, sender, receiver, content, **extra)` monta esse dicionário, e uma função `despachar(m)` decide o que fazer **a partir do campo `performative`** (`if perf == "request": ...`), **nunca** verificando o texto livre (`content`) com algo como `"classificar" in content`. É exatamente esse ponto — decisão pela intenção estruturada, não pelo texto — que a FIPA-ACL formaliza. Testado (rodando `python -m aula4.ex8_fipa_acl`): quatro mensagens de exemplo (`request`, `inform`, `query`, `inform`) circulando entre Coletor, Triagem e Estatística, cada uma despachada corretamente pela sua performativa.

Este script não usa MQTT nem `Agent`/`Runner` — é Python puro, de propósito, para isolar o conceito (a estrutura da mensagem) da mecânica de transporte já vista nos exercícios 4-7. `**extra` na assinatura de `msg_acl` mostra como capturar argumentos nomeados extras sem prever cada um deles.

> **Conexão com segurança (ver `aula3/aula3.md` §9.2):** o mesmo motivo pelo qual o receptor da FIPA-ACL nunca decide pelo texto livre é o motivo pelo qual um agente nunca deve tratar o conteúdo de uma ferramenta como instrução — em ambos os casos, misturar "dado" com "comando" é a porta de entrada de um ataque (prompt injection indireta).

---

## 4. Lab 2 — MQTT Pub/Sub (A2A assíncrono, distribuído)

**Teoria (slide "Broker, tópico, publish/subscribe"):** um **broker** MQTT é um intermediário — ninguém fala direto com ninguém. Quem publica manda para um **tópico** (uma string, tipo um endereço: `pcdf/demo/ocorrencias/nova`); quem quiser receber **assina** esse mesmo tópico. Publisher e subscriber não se conhecem, não trocam IP — só compartilham o nome do tópico. A partir daqui, cada agente roda em um **processo separado** (um terminal cada).

### 4.1 Setup: as três variáveis novas do `.env`

```bash
MQTT_BROKER=broker.emqx.io   # broker público e gratuito (só para testes)
MQTT_PORT=1883               # porta MQTT sem criptografia
MQTT_PREFIXO=pcdf/demo       # "namespace" que isola seu tráfego no broker compartilhado
```

> ⚠️ **LGPD (slide "Preparar o ambiente"):** este broker é **público** — qualquer pessoa no mundo pode ler o que for publicado nele. Por isso os exemplos usam dados fictícios (`{"id": 123, "tipo": "furto", "local": "Asa Norte"}`). **Nunca publique CPF, nome completo ou qualquer dado pessoal real** num broker público como este — o mesmo princípio de minimização de dado já visto em `aula1/aula1.md` (Seção 6).

> **Nota de dependência:** `paho-mqtt` está listado em `requirements.txt`, mas pode não estar instalado na sua `venv` se você a criou antes dessa linha ser adicionada — rode `pip install -r requirements.txt` (ou `pip install paho-mqtt`) antes de testar os exercícios 4-6. Sem isso, o erro é `ModuleNotFoundError: No module named 'paho'`.

> **Nota de versão:** este projeto usa o paho-mqtt 2.x, que exige `mqtt.Client(callback_api_version=mqtt.CallbackAPIVersion.VERSION2)` — sem esse argumento, o cliente ainda funciona, mas imprime um aviso de depreciação a cada execução. Todos os scripts desta pasta já passam esse argumento.

### 4.2 Exercício 4 — Coletor, o publisher (`ex4_mqtt_pub.py`)

Publica uma ocorrência (um dicionário Python, convertido para texto com `json.dumps`) no tópico `f"{PREFIXO}/ocorrencias/nova"` e **desconecta na sequência, sem esperar ninguém** — é isso que caracteriza "publica e segue" (compare com `Runner.run_sync`, que fica parado até a resposta chegar). Não usa `Agent`/`Runner`/`provedor` — é troca de mensagem "crua", sem IA — por isso não precisa do truque de `sys.path` usado nos exercícios de handoff.

### 4.3 Exercício 5 — Triagem, o subscriber com LLM (`ex5_mqtt_sub.py`)

O par do Coletor: assina `f"{PREFIXO}/ocorrencias/#"` (o `#` é um *wildcard* multinível — assina todos os subtópicos de uma vez) e, a cada mensagem que chega, roda um `Agent` de verdade (`Runner.run_sync(triagem, str(oc))`) para classificar a ocorrência.

**O pulo do gato (slide "O pulo do gato"):** o Coletor não conhece a Triagem, e vice-versa — eles só compartilham um tópico. Isso é **desacoplamento**: dá para trocar, escalar ou adicionar novos consumidores sem mexer em quem publica (é exatamente o que o Exercício 6 prova).

Dois níveis de "síncrono/assíncrono" coexistem aqui: a **chegada** da mensagem é assíncrona (`on_message` dispara quando o broker decidir entregar); o **processamento** de cada mensagem, uma vez chegada, é síncrono como sempre (`Runner.run_sync` dentro do callback).

`loop_forever()` é um laço **bloqueante** — por isso a Triagem precisa rodar num terminal só para ela, separado do Coletor.

### 4.4 Exercício 6 — Estatística, um terceiro assinante (`ex6_mqtt_estatistica.py`)

**Desafio guiado do deck:** sem tocar no Coletor, adicione um agente que também assina `f"{PREFIXO}/ocorrencias/#"` e só conta ocorrências por tipo (`collections.Counter`, sem LLM nenhum). Comprovado neste repo: rodando Triagem e Estatística ao mesmo tempo e publicando uma vez com o Coletor, **os dois recebem a mesma mensagem, de forma independente** — nenhuma linha do Coletor ou da Triagem precisou mudar para isso funcionar. É a demonstração prática de *fan-out*: um publisher, múltiplos consumidores.

### Como testar o Lab 2 (3 terminais, da raiz do projeto, com a venv ativada)

```bash
# Terminal 1 — Triagem (classifica com LLM)
python -m aula4.ex5_mqtt_sub

# Terminal 2 — Estatística (só conta por tipo)
python -m aula4.ex6_mqtt_estatistica

# Terminal 3 — publica e termina
python -m aula4.ex4_mqtt_pub
```

---

## 5. Exercício 7 — Request/Reply sobre MQTT

**Teoria (slide "Request/Reply sobre MQTT"):** MQTT é nativamente Pub/Sub, mas dá para simular um pedido-e-resposta com **dois tópicos e dois papéis**:

| Tópico | Quem publica | Quem assina |
|---|---|---|
| `{PREFIXO}/juridico/analisar` | cliente (`ex7_triagem_cliente.py`) | serviço (`ex7_juridico_servico.py`) |
| `{PREFIXO}/juridico/resposta` | serviço (`ex7_juridico_servico.py`) | cliente (`ex7_triagem_cliente.py`) |

⚠️ **Ordem importa:** o cliente precisa **assinar a resposta ANTES de publicar o pedido** (`ex7_triagem_cliente.py` faz `cli.subscribe(...)` seguido de `cli.loop_start()`, e só então `cli.publish(...)`). Se publicasse antes, a resposta do serviço (se for rápido) poderia chegar antes de a assinatura existir — e se perder, já que MQTT não guarda mensagens para quem assina depois (compare com "Mensageria/Filas" na Seção 6, que garante entrega mesmo que o consumidor demore a existir).

Do ponto de vista de quem chama, parece síncrono (pediu, recebeu) — mas por baixo são **dois processos, dois tópicos, e nenhuma garantia de resposta se o serviço cair**. O cliente não usa `Agent`/`Runner`/`provedor` (quem tem o LLM é só o serviço) — por isso não precisa do truque de `sys.path`; o serviço precisa.

`ex7_triagem_cliente.py` usa `cli.loop_start()` (a rede roda numa thread em segundo plano) em vez de `cli.loop_forever()` (usado no serviço, que fica ouvindo para sempre) — o cliente precisa continuar executando depois de assinar, para publicar o pedido e só então esperar um pouco (`time.sleep(6)`) pela resposta antes de encerrar sozinho.

**Testado neste repo:** com o serviço rodando num terminal e o cliente no outro, o pedido foi publicado, o serviço processou com o `Agent` Jurídico e respondeu, e o cliente imprimiu `[resposta] id=1 -> ...` — confirmando o round-trip completo pelos dois tópicos.

```bash
# Terminal 1 — serviço (fica ouvindo)
python -m aula4.ex7_juridico_servico
# Terminal 2 — cliente (pede e aguarda)
python -m aula4.ex7_triagem_cliente
```

---

## 6. Exercício 9 — Pipeline (esteira de 3 estágios)

```mermaid
flowchart LR
    C["ex9_pipeline_coletor.py\n(Emite ocorrência crua)"] -->|"pcdf/demo/pipeline/entrada"| T["ex9_pipeline_triagem.py\n(Classifica com LLM)"]
    T -->|"pcdf/demo/pipeline/juridico"| J["ex9_pipeline_juridico.py\n(Gera enquadramento legal)"]
    J --> Fim["Parecer Final Consolidado"]
```

**Teoria (slide "Encadeando 3 estágios pelo tópico"):** cada estágio só conhece o tópico de **entrada** que assina e o de **saída** que publica — nunca os vizinhos do vizinho:

```
ex9_pipeline_coletor.py  --publica-->  {PREFIXO}/pipeline/entrada
ex9_pipeline_triagem.py  --assina .../entrada, classifica, publica-->  {PREFIXO}/pipeline/juridico
ex9_pipeline_juridico.py --assina .../juridico, dá o parecer final (fim da esteira)
```

Tecnicamente não é mecanismo novo — é a soma do Lab 2 (subscriber + LLM, exercícios 5/6) com o publish encadeado do Exercício 7: o estágio do meio (`ex9_pipeline_triagem.py`) faz as duas coisas ao mesmo tempo — assina um tópico **e** publica em outro dentro do mesmo `on_message`, repassando a ocorrência adiante já com a classificação anexada.

**Testado neste repo** (3 terminais rodando ao mesmo tempo): o Coletor publicou uma ocorrência; a Triagem recebeu, classificou com o `Agent` e republicou no tópico do Jurídico; o Jurídico recebeu e produziu o parecer final — os três processos nunca trocaram uma referência direta entre si, só tópicos.

```bash
# Terminal 1 — último estágio (fica ouvindo)
python -m aula4.ex9_pipeline_juridico
# Terminal 2 — estágio do meio (fica ouvindo)
python -m aula4.ex9_pipeline_triagem
# Terminal 3 — dispara a esteira (publica e termina)
python -m aula4.ex9_pipeline_coletor
```

**Pergunta do deck para refletir:** o que aconteceria se a Triagem (Terminal 2) caísse no meio da esteira, depois de o Coletor já ter publicado? O Jurídico nunca receberia nada, e o Coletor nem perceberia — a ocorrência ficaria "perdida" em trânsito. Não há fila persistente neste desenho (é a mesma lacuna que "Mensageria/Filas" resolveria, ver Seção 7).

---

## 7. Três padrões de troca de mensagens (referência)

| Padrão | Ideia | Onde aparece nesta aula |
|---|---|---|
| **Request/Response** | Um pede, o outro responde. Direto e previsível. | Handoffs do SDK (Lab 1); chamadas HTTP/gRPC |
| **Publish/Subscribe (Pub/Sub)** | Quem publica não sabe quem consome. Um tópico, vários assinantes. Adicionar consumidor não muda quem publica. | MQTT (Lab 2, exercícios 4-6) — é o coração do MQTT |
| **Mensageria/Filas** | Mensagens ficam numa fila até serem processadas. Garante que nada se perde; distribui carga entre trabalhadores. | Não implementado nesta aula — mencionado como o padrão que resolveria a "perda" descrita nos Exercícios 7 e 9 |

---

## 8. Pontos de Atenção

- **`model=modelo()` continua obrigatório** em todo `Agent(...)` desta aula — sem ele, o SDK tenta usar o modelo padrão da OpenAI, que não existe no provedor configurado (Zen/Ollama), e falha. Mesmo erro já documentado em `aula1/aula1.md` (Seção 4).
- **`sys.path.insert(...)` só é necessário em quem importa `provedor`** — ou seja, nos exercícios com `Agent`/`Runner` (`teste.py`, `ex1`-`ex3`, `ex5`, `ex7_juridico_servico.py`, `ex9_pipeline_triagem.py`, `ex9_pipeline_juridico.py`). Os scripts puramente MQTT sem IA (`ex4`, `ex6`, `ex7_triagem_cliente.py`, `ex9_pipeline_coletor.py`) não precisam desse truque, porque não importam nada da raiz do curso além do `.env` (que o `python-dotenv` já encontra sozinho, andando para cima nas pastas a partir do próprio arquivo). `ex8_fipa_acl.py` também dispensa o truque — não importa nem `provedor` nem MQTT.
- **Consistência do `MQTT_PREFIXO` entre processos:** publisher e assinantes só se encontram se usarem o **mesmo** prefixo. Como cada arquivo tem um valor padrão codificado (`os.getenv("MQTT_PREFIXO", "pcdf/demo")`) para o caso de a variável faltar no `.env`, um valor padrão diferente em um dos arquivos quebra o encontro **silenciosamente** (sem erro — a mensagem simplesmente nunca chega). Vale conferir esse valor sempre que copiar um exercício MQTT para um cenário novo — já corrigi uma inconsistência assim num teste à parte que o professor pediu.
- **`paho-mqtt` 2.x exige `callback_api_version`** no construtor do `Client()` — sem isso, funciona, mas emite aviso de depreciação a cada execução.
- **Handoff vs. `as_tool`, a escolha de arquitetura:** use handoff quando o especialista deve assumir a conversa por completo (ex.: triagem de atendimento); use `as_tool` quando um coordenador precisa consultar vários especialistas e compor uma única resposta final (ex.: um relatório que cita parecer jurídico + diligências investigativas, como no `ex3`).
- **Nenhum exercício desta pasta usa `provedor.rodar()`** (o recuo automático para Ollama visto em `aula1/agente1.py`) — todos chamam `Runner.run_sync(...)` direto sobre o `Agent`, mesmo padrão já adotado em `aula2`/`aula3` para agentes com handoff, hooks ou callbacks (o `rodar()` foi pensado para o caso simples de "uma fábrica, uma chamada", e não se encaixa bem dentro de um `on_message` do MQTT). **Na prática, isso significa que se o provedor principal (Zen) falhar, o script quebra em vez de recuar sozinho para o Ollama** — foi o que aconteceu ao testar `ex7`/`ex9` nesta sessão (`403 - Model access is disabled` na Zen); confirmei que a lógica dos scripts está correta rodando com `PROVEDOR=ollama` como alternativa manual (`export PROVEDOR=ollama` antes do comando, sem precisar editar o `.env`).

---

## 9. Fechamento — o que levamos para a Aula 5

Recap do deck (slide "Encerramento"):

- Síncrono (handoffs) × assíncrono (MQTT) — e quando usar cada um.
- Três padrões: Request/Response, Pub/Sub, Mensageria/Filas.
- Contratos que dão forma às trocas: FIPA-ACL, gRPC, MQTT.
- **Próxima aula:** agentes ganham "mãos" — ferramentas, APIs e bancos via **MCP** (Model Context Protocol). Prévia do professor: `SQLite` + `.mcp.json`, e por que **controlar o que o agente pode fazer via MCP** já nasce como o primeiro problema da Aula 5 — o mesmo tema de autonomia/freio humano que `aula3/aula3.md` (Seção 5) já preparou o terreno para discutir.
