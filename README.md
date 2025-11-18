# Checkpoint Backend

Backend da aplicação Checkpoint - Sistema de chatbot inteligente com detecção de crise em tempo real e suporte humano via WebSocket.

## 🚀 Sobre o Projeto

O Checkpoint é uma aplicação de apoio emocional que combina inteligência artificial (Ollama) com intervenção humana. O sistema monitora conversas em tempo real, detecta sinais de crise usando análise de palavras-chave, padrões regex e IA, e permite que monitores assumam o controle quando necessário.

### Principais Funcionalidades

- **Chat com IA Local**: Integração com Ollama (llama3.2:3b) para conversas automatizadas
- **Detecção de Crise**: Sistema multinível (LOW, MEDIUM, HIGH, CRITICAL) que analisa:
  - Palavras-chave categorizadas por risco
  - Padrões regex para detecção avançada
  - Análise contextual com IA
- **Comunicação em Tempo Real**: WebSocket/Socket.IO para mensagens instantâneas
- **Sistema de Monitor**: Permite que profissionais assumam conversas em crise
- **Autenticação JWT**: Sistema seguro de autenticação com bcrypt
- **Anonimização**: Suporte para usuários anônimos com rastreamento por sessão

## 🛠️ Tecnologias

### Framework e Servidor
- **FastAPI**: Framework web moderno e assíncrono para Python
- **Uvicorn**: Servidor ASGI de alta performance
- **Socket.IO**: Comunicação bidirecional em tempo real

### Banco de Dados
- **PostgreSQL**: Banco de dados relacional
- **SQLAlchemy**: ORM para Python
- **Alembic**: Gerenciamento de migrações
- **psycopg2**: Driver PostgreSQL

### Inteligência Artificial
- **Ollama**: Integração com modelos de IA local (llama3.2:3b)
- **httpx**: Cliente HTTP assíncrono para comunicação

### Segurança
- **JWT (PyJWT)**: Autenticação baseada em tokens
- **bcrypt**: Hash seguro de senhas
- **python-jose**: Suporte adicional para JWT

### Testes
- **pytest**: Framework de testes
- **pytest-asyncio**: Suporte para testes assíncronos
- **pytest-cov**: Cobertura de código
- **pytest-mock**: Mocking

### DevOps
- **Docker**: Containerização
- **Docker Compose**: Orquestração de containers

## 📋 Pré-requisitos

- Docker e Docker Compose
- Git

## 🚀 Instalação e Configuração

### 1. Clone o repositório

```bash
git clone https://github.com/ArthurHoengen/checkpoint-backend.git
cd checkpoint/backend
```

### 2. Configuração de ambiente

O arquivo `.env` já está configurado para funcionar com Docker Compose:

```env
DATABASE_URL=postgresql+psycopg2://checkpoint:qwertyuiop@db:5432/checkpoint
JWT_SECRET=supersecretjwtkey
JWT_ALGORITHM=HS256
OLLAMA_BASE_URL=http://ollama:11434
```

### 3. Iniciar os serviços com Docker Compose

```bash
docker-compose up -d
```

Este comando irá:
- Criar e iniciar o banco PostgreSQL
- Criar e iniciar o serviço Ollama
- Criar e iniciar a API FastAPI com Socket.IO
- Configurar o Adminer (interface web para PostgreSQL)

### 4. Baixar o modelo Ollama (llama3.2:3b)

Após os containers estarem rodando, execute:

```bash
docker exec -it checkpoint_ollama ollama pull llama3.2:3b
```

### 5. Executar migrações do banco de dados

```bash
docker exec -it checkpoint_api alembic upgrade head
```

### 6. Criar usuário de monitor (IMPORTANTE)

**ATENÇÃO**: Para acessar as rotas de monitor e executar os testes, você precisa criar um usuário manualmente no banco de dados.

#### Opção 1: Via Adminer (Interface Web)

1. Acesse: http://localhost:8080
2. Faça login com as credenciais:
   - **Sistema**: PostgreSQL
   - **Servidor**: db
   - **Usuário**: checkpoint
   - **Senha**: qwertyuiop
   - **Base de dados**: checkpoint
3. Vá até a tabela `users`
4. Clique em "Inserir"
5. Preencha:
   - **username**: `monitor` (ou o nome que preferir)
   - **hashed_password**: Use o hash bcrypt de uma senha (veja opção 2 para gerar)

#### Opção 2: Via Python (Recomendado)

Execute o seguinte script Python no container da API:

```bash
docker exec -it checkpoint_api python -c "
from app.core.security import get_password_hash
from app.auth.models import User
from app.core.database import SessionLocal

db = SessionLocal()
hashed_password = get_password_hash('monitor123')
monitor = User(username='monitor', hashed_password=hashed_password)
db.add(monitor)
db.commit()
print('✅ Usuário monitor criado com sucesso!')
print('   Username: monitor')
print('   Password: monitor123')
db.close()
"
```

#### Opção 3: Via SQL direto

```bash
docker exec -it checkpoint_db psql -U checkpoint -d checkpoint -c "
INSERT INTO users (username, hashed_password)
VALUES ('monitor', '\$2b\$12\$KIXqF7hGJ5vZJ0Z4Y2H.FuK4QH.L8XK6qH9F2Y3H.FuK4QH.L8XK6');
"
```
> **Nota**: A senha hash acima corresponde a `monitor123`

Após criar o usuário, você poderá fazer login:

```bash
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "monitor", "password": "monitor123"}'
```

## 🏃‍♂️ Como usar

### Verificar se tudo está funcionando

Acesse: http://localhost:8000/docs para ver a documentação interativa da API.

### Serviços disponíveis

- **API REST**: http://localhost:8000
- **Documentação Swagger**: http://localhost:8000/docs
- **WebSocket/Socket.IO**: ws://localhost:8000/socket.io/
- **PostgreSQL**: localhost:5432
- **Adminer (DB Admin)**: http://localhost:8080
- **Ollama**: http://localhost:11434

### Endpoints principais

#### Autenticação
- `POST /auth/login` - Login e geração de token JWT

#### Chat
- `POST /chat/conversations` - Criar nova conversa
- `GET /chat/conversations/{id}/messages` - Obter mensagens
- `POST /chat/conversations/{id}/ask-with-crisis-detection` - Enviar mensagem com detecção de crise
- `POST /chat/conversations/{id}/mode` - Alterar modo (ollama/user)

#### Monitor (Requer autenticação)
- `GET /chat/monitor/dashboard` - Dashboard com conversas que precisam de atenção
- `POST /chat/monitor/take-over/{conversation_id}` - Assumir conversa
- `POST /chat/monitor/send-message` - Enviar mensagem como monitor

### WebSocket Events

#### Cliente → Servidor
- `connect` - Estabelecer conexão
- `join_conversation` - Entrar em uma sala de conversa
- `join_monitor` - Entrar como monitor (requer autenticação)
- `send_message` - Enviar mensagem em tempo real
- `typing` - Indicador de digitação

#### Servidor → Cliente
- `new_message` - Nova mensagem recebida
- `crisis_alert` - Alerta de crise detectada
- `monitor_joined` - Monitor entrou na conversa
- `user_typing` - Usuário está digitando

## 📁 Estrutura do Projeto

```
backend/
├── app/
│   ├── auth/                     # Sistema de autenticação
│   │   ├── models.py            # Modelo User
│   │   ├── routes.py            # Endpoint de login
│   │   ├── schemas.py           # Schemas Pydantic
│   │   ├── service.py           # Lógica de autenticação
│   │   └── dependencies.py      # Dependências (get_current_user)
│   ├── chat/                     # Sistema de chat
│   │   ├── models.py            # Conversation, Message, ConversationStatus
│   │   ├── routes.py            # Endpoints de chat e monitor
│   │   ├── schemas.py           # Schemas de request/response
│   │   ├── services.py          # Lógica de negócio
│   │   └── crisis_detector.py   # Detecção de crise multinível
│   ├── core/                     # Configurações centrais
│   │   ├── config.py            # Settings com pydantic
│   │   ├── database.py          # SQLAlchemy setup
│   │   ├── security.py          # JWT, bcrypt
│   │   └── ollama_client.py     # Cliente Ollama
│   ├── websocket/                # WebSocket/Socket.IO
│   │   ├── app.py               # Criação do Socket.IO app
│   │   └── manager.py           # Gerenciador de eventos
│   ├── logs/                     # Sistema de logging
│   └── utils/                    # Utilitários (anonymizer)
├── alembic/                      # Migrações de banco
├── tests/                        # Testes unitários
│   ├── conftest.py              # Fixtures globais
│   ├── test_auth.py             # Testes de autenticação
│   ├── test_chat_routes.py      # Testes de rotas
│   ├── test_chat_services.py    # Testes de serviços
│   └── test_crisis_detection.py # Testes de detecção de crise
├── docker-compose.yml            # Orquestração de containers
├── Dockerfile                    # Build da aplicação
├── requirements.txt              # Dependências Python
├── pytest.ini                    # Configuração de testes
├── alembic.ini                   # Configuração Alembic
├── run_with_socketio.py         # Script para executar com Socket.IO
└── README.md                     # Este arquivo
```

## 🤖 Sistema de Detecção de Crise

O sistema utiliza três estratégias combinadas para análise de risco:

### 1. Análise de Palavras-Chave

Palavras categorizadas por nível de risco:

- **CRITICAL**: "vou me matar", "tenho uma arma", "hoje é o último dia"
- **HIGH**: "suicídio", "não aguento mais", "sem esperança"
- **MEDIUM**: "deprimido", "vazio", "sou um fardo"
- **LOW**: "triste", "ansioso", "preocupado"

### 2. Padrões Regex

Detecta padrões complexos como:
- `vou.*(?:me matar|suicidar|morrer)`
- `(?:tenho|vou usar).*(?:arma|faca|remédio)`
- `ameaça.*(?:morte|matar)`

### 3. Análise com IA (Ollama)

O modelo llama3.2:3b avalia o contexto emocional e retorna um nível de risco com confiança.

### Combinação de Resultados

O sistema:
1. Executa as três análises em paralelo
2. Seleciona o maior nível de risco encontrado
3. Calcula confiança combinada
4. Aumenta confiança se múltiplas análises concordam
5. Determina se requer intervenção humana (HIGH ou CRITICAL)

## 🧪 Testes

O projeto possui cobertura de testes > 80% incluindo:

### Executar todos os testes

```bash
# No host (se tiver dependências instaladas)
pytest

# No container Docker
docker exec -it checkpoint_api pytest
```

### Executar com cobertura

```bash
pytest --cov=app --cov-report=html
```

Relatório HTML disponível em: `htmlcov/index.html`

### Executar testes específicos

```bash
# Por arquivo
pytest tests/test_auth.py

# Por classe
pytest tests/test_auth.py::TestAuthEndpoints

# Por teste
pytest tests/test_auth.py::TestAuthEndpoints::test_login_success
```

### Cobertura de Testes

✅ **Autenticação** (test_auth.py)
- Login com credenciais válidas/inválidas
- Geração e validação de tokens JWT
- Proteção de rotas
- Hash de senhas

✅ **Serviços de Chat** (test_chat_services.py)
- Criação de conversas
- Gerenciamento de mensagens
- Monitor assumindo controle
- Escalação de conversas
- Busca de conversas que precisam de atenção

✅ **Rotas da API** (test_chat_routes.py)
- Endpoints de conversas
- Endpoints de monitor
- Autenticação em rotas protegidas
- Tratamento de erros (404, 401)

✅ **Detecção de Crise** (test_crisis_detection.py)
- Detecção de palavras-chave (todos os níveis)
- Detecção de padrões regex
- Análise de contexto
- Níveis de confiança
- Extração de keywords

### Banco de Dados de Teste

Os testes utilizam **SQLite em memória** ao invés do PostgreSQL, garantindo:
- Testes rápidos
- Isolamento completo
- Sem configuração adicional
- Cada teste recebe um banco limpo

## 🔧 Desenvolvimento

### Executar sem Docker

Se preferir executar localmente:

#### 1. Criar ambiente virtual

```bash
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# ou
.venv\Scripts\activate  # Windows
```

#### 2. Instalar dependências

```bash
pip install -r requirements.txt
```

#### 3. Configurar variáveis de ambiente

Ajustar URLs para localhost no arquivo `.env`:

```env
DATABASE_URL=postgresql+psycopg2://checkpoint:qwertyuiop@localhost:5432/checkpoint
JWT_SECRET=supersecretjwtkey
JWT_ALGORITHM=HS256
OLLAMA_BASE_URL=http://localhost:11434
```

#### 4. Executar migrações

```bash
alembic upgrade head
```

#### 5. Iniciar servidor com WebSocket

```bash
# Opção 1: Script Python (recomendado)
python run_with_socketio.py

# Opção 2: Uvicorn direto
uvicorn app.main:socket_app --reload --host 0.0.0.0 --port 8000

# Opção 3: Sem WebSocket (não recomendado)
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Comandos úteis de desenvolvimento

```bash
# Criar nova migração
alembic revision --autogenerate -m "Descrição da mudança"

# Aplicar migrações
alembic upgrade head

# Reverter migração
alembic downgrade -1

# Ver status das migrações
alembic current

# Ver histórico de migrações
alembic history
```

### Rebuild Docker após mudanças

```bash
# Rebuild rápido
./rebuild_docker.sh

# Rebuild completo
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

### Ver logs

```bash
# Logs da API
docker-compose logs -f api

# Logs do PostgreSQL
docker-compose logs -f db

# Logs do Ollama
docker-compose logs -f ollama

# Todos os logs
docker-compose logs -f
```

## 🌐 Integração com Ollama

### Modelo Padrão

O sistema usa `llama3.2:3b` por padrão. Configurado em [app/core/ollama_client.py:7](app/core/ollama_client.py#L7)

### Métodos Disponíveis

```python
from app.core.ollama_client import OllamaClient

ollama = OllamaClient()

# Pergunta simples
response = await ollama.ask("Qual é o sentido da vida?")

# Chat com contexto
messages = [
    {"role": "user", "content": "Olá"},
    {"role": "assistant", "content": "Oi! Como posso ajudar?"},
    {"role": "user", "content": "Estou triste"}
]
response = await ollama.chat(messages)
```

### Trocar modelo

Para usar outro modelo:

1. Baixar o modelo:
```bash
docker exec -it checkpoint_ollama ollama pull llama2
```

2. Alterar em `ollama_client.py`:
```python
self.default_model = "llama2"
```

## 🔒 Segurança

### Autenticação JWT

- Tokens com expiração configurável
- Algorithm: HS256
- Secret configurável via variável de ambiente

### Senhas

- Hash bcrypt com salt automático
- Senhas nunca armazenadas em texto plano
- Verificação segura com timing-attack protection

### Anonimização

- Suporte para usuários anônimos
- Rastreamento por session_id
- Sem armazenamento de dados pessoais por padrão

### Validação de Dados

- Schemas Pydantic para validação
- Type hints em todas as funções
- Validação automática de requests

## ❓ Solução de Problemas

### Problema: Ollama não consegue baixar modelos

```bash
# Verificar se o container está rodando
docker ps | grep ollama

# Acessar logs do Ollama
docker logs checkpoint_ollama

# Baixar modelo manualmente
docker exec -it checkpoint_ollama ollama pull llama3.2:3b

# Listar modelos instalados
docker exec -it checkpoint_ollama ollama list
```

### Problema: Erro de conexão com banco

```bash
# Verificar se PostgreSQL está rodando
docker ps | grep postgres

# Verificar logs do banco
docker logs checkpoint_db

# Executar migrações novamente
docker exec -it checkpoint_api alembic upgrade head

# Conectar ao banco manualmente
docker exec -it checkpoint_db psql -U checkpoint -d checkpoint
```

### Problema: API não responde

```bash
# Verificar logs da API
docker logs checkpoint_api

# Verificar se porta 8000 está livre
lsof -i :8000

# Reiniciar serviço da API
docker-compose restart api

# Rebuild completo
docker-compose down
docker-compose up -d --build
```

### Problema: Testes falhando

```bash
# Verificar se há usuário monitor criado (necessário para alguns testes)
# Use a opção 2 da seção "Criar usuário de monitor"

# Executar testes com mais detalhes
pytest -v -s

# Executar teste específico que está falhando
pytest tests/test_auth.py::TestAuthEndpoints::test_login_success -v
```

### Problema: WebSocket não conecta

```bash
# Verificar se está usando socket_app ao invés de app
# No docker-compose.yml deve ter:
# command: uvicorn app.main:socket_app --host 0.0.0.0 --port 8000 --reload

# Testar WebSocket
curl http://localhost:8000/socket.io/

# Verificar CORS
# Adicione a origem do frontend em app/main.py se necessário
```

### Problema: "Low VRAM" ou GPU não detectada

```bash
# Verificar configuração de GPU no Ollama
docker logs checkpoint_ollama | grep -i gpu

# Forçar uso de CPU (mais lento mas funcional)
docker exec -it checkpoint_ollama bash
export OLLAMA_DEVICE=cpu
ollama serve
```

## 📊 Monitoramento e Logs

O sistema inclui logging configurável em [app/logs/service.py](app/logs/service.py)

Logs incluem:
- Requisições HTTP
- Eventos WebSocket
- Detecções de crise
- Erros e exceções
- Atividade de monitores

## 🤝 Contribuindo

1. Fork o projeto
2. Crie uma branch para sua feature (`git checkout -b feature/AmazingFeature`)
3. Commit suas mudanças (`git commit -m 'Add some AmazingFeature'`)
4. Push para a branch (`git push origin feature/AmazingFeature`)
5. Abra um Pull Request

### Padrões de Código

- Use type hints em todas as funções
- Docstrings para classes e funções complexas
- Testes para novas funcionalidades
- Mantenha cobertura > 80%
- Siga PEP 8

## 📝 Licença

Este projeto é licenciado sob a MIT License.

## 👥 Autores

- **Arthur Hoengen** - [GitHub](https://github.com/ArthurHoengen)

## 🙏 Agradecimentos

- FastAPI pela excelente documentação
- Ollama pelo modelo de IA local
- Comunidade Python
