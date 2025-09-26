# Checkpoint API - Backend

Sistema de chat com suporte emocional usando FastAPI, PostgreSQL e integração com Ollama para IA conversacional.

## 🛠️ Tecnologias

- **FastAPI**: Framework web moderno para Python
- **PostgreSQL**: Banco de dados relacional
- **SQLAlchemy**: ORM para Python
- **Alembic**: Gerenciamento de migrações de banco
- **Ollama**: Integração com modelos de IA local
- **JWT**: Autenticação baseada em tokens
- **Docker**: Containerização

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
- Criar e iniciar a API FastAPI
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

## 🏃‍♂️ Como usar

### Verificar se tudo está funcionando
Acesse: http://localhost:8000/docs para ver a documentação interativa da API.

### Serviços disponíveis:
- **API**: http://localhost:8000
- **Documentação da API**: http://localhost:8000/docs
- **PostgreSQL**: localhost:5432
- **Adminer (DB Admin)**: http://localhost:8080
- **Ollama**: http://localhost:11434

### Credenciais do banco (via Adminer):
- **Sistema**: PostgreSQL
- **Servidor**: db
- **Usuário**: checkpoint
- **Senha**: qwertyuiop
- **Base de dados**: checkpoint

## 🔧 Desenvolvimento

### Executar sem Docker
Se preferir executar localmente:

1. **Instalar dependências**:
```bash
pip install -r requirements.txt
```

2. **Configurar variáveis de ambiente** (ajustar URLs para localhost):
```env
DATABASE_URL=postgresql+psycopg2://checkpoint:qwertyuiop@localhost:5432/checkpoint
JWT_SECRET=supersecretjwtkey
JWT_ALGORITHM=HS256
OLLAMA_BASE_URL=http://localhost:11434
```

3. **Executar migrações**:
```bash
alembic upgrade head
```

4. **Iniciar servidor de desenvolvimento**:
```bash
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

## 📁 Estrutura do Projeto

```
backend/
├── app/
│   ├── auth/                 # Sistema de autenticação
│   │   ├── models.py        # Modelo User
│   │   ├── routes.py        # Endpoints de auth
│   │   ├── schemas.py       # Schemas Pydantic
│   │   ├── service.py       # Lógica de negócio
│   │   └── dependencies.py  # Dependências FastAPI
│   ├── chat/                # Sistema de chat
│   │   ├── models.py        # Modelos Conversation/Message
│   │   ├── routes.py        # Endpoints de chat
│   │   ├── schemas.py       # Schemas Pydantic
│   │   ├── services.py      # Lógica de negócio
│   │   └── crisis_detector.py # Detecção de crise
│   ├── core/                # Configurações centrais
│   │   ├── config.py        # Configurações do app
│   │   ├── database.py      # Configuração SQLAlchemy
│   │   ├── security.py      # Utilitários de segurança
│   │   └── ollama_client.py # Cliente Ollama
│   ├── logs/                # Sistema de logs
│   └── utils/               # Utilitários gerais
├── alembic/                 # Migrações de banco
├── docker-compose.yml       # Configuração Docker
├── Dockerfile              # Build da aplicação
├── requirements.txt        # Dependências Python
└── .env                    # Variáveis de ambiente
```

## 🤖 Integração com Ollama

O sistema está configurado para usar o modelo `llama3.2:3b` por padrão. O cliente Ollama (`app/core/ollama_client.py`) fornece:

- **Geração de respostas**: Método `ask()` para conversas simples
- **Chat estruturado**: Método `chat()` para conversas com contexto
- **Configuração personalizada**: Suporte a diferentes modelos

### Configuração do modelo padrão
O modelo padrão pode ser alterado em `app/core/ollama_client.py:7`:
```python
self.default_model = default_model or getattr(settings, "ollama_default_model", "llama3.2:3b")
```

## 🛡️ Funcionalidades de Segurança

- **Autenticação JWT**: Sistema completo de login/registro
- **Detecção de crise**: Monitoramento automático de mensagens de risco
- **Criptografia de senhas**: Usando bcrypt
- **Validação de dados**: Schemas Pydantic

## 📊 Banco de Dados

### Tabelas principais:
- **users**: Usuários do sistema
- **conversations**: Conversas de chat
- **messages**: Mensagens individuais com flags de segurança

### Migrações
O sistema usa Alembic para controle de versão do banco. As tabelas são criadas automaticamente na primeira execução.

## 🐳 Docker

### Serviços do Docker Compose:
- **api**: Aplicação FastAPI
- **db**: PostgreSQL 17
- **ollama**: Servidor Ollama com GPU habilitada
- **adminer**: Interface web para administração do banco

### Volumes persistentes:
- **pgdata**: Dados do PostgreSQL
- **ollama_data**: Modelos e dados do Ollama

## 🔍 Logs e Monitoramento

O sistema inclui serviços de logging configuráveis em `app/logs/service.py`.

## ❓ Solução de Problemas

### Problema: Ollama não consegue baixar modelos
```bash
# Verificar se o container está rodando
docker ps | grep ollama

# Acessar logs do Ollama
docker logs checkpoint_ollama

# Baixar modelo manualmente
docker exec -it checkpoint_ollama ollama pull llama3.2:3b
```

### Problema: Erro de conexão com banco
```bash
# Verificar se PostgreSQL está rodando
docker ps | grep postgres

# Verificar logs do banco
docker logs checkpoint_db

# Executar migrações novamente
docker exec -it checkpoint_api alembic upgrade head
```

### Problema: API não responde
```bash
# Verificar logs da API
docker logs checkpoint_api

# Reiniciar serviço da API
docker-compose restart api
```