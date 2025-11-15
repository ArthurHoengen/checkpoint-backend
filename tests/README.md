# Testes Unitários - Checkpoint Backend

Este diretório contém os testes unitários e de integração para o backend do Checkpoint.

## Estrutura dos Testes

```
tests/
├── conftest.py                 # Configurações e fixtures globais
├── test_auth.py               # Testes de autenticação e autorização
├── test_chat_services.py      # Testes dos serviços de chat
├── test_chat_routes.py        # Testes das rotas da API
├── test_crisis_detection.py   # Testes do detector de crise
└── README.md                  # Este arquivo
```

## Pré-requisitos

Certifique-se de que as dependências de teste estão instaladas:

```bash
pip install -r requirements.txt
```

As dependências de teste incluem:
- `pytest` - Framework de testes
- `pytest-asyncio` - Suporte para testes assíncronos
- `pytest-cov` - Cobertura de código
- `pytest-mock` - Mocking

## Executando os Testes

### Executar todos os testes

```bash
pytest
```

### Executar com cobertura de código

```bash
pytest --cov=app --cov-report=html
```

Isso gerará um relatório HTML em `htmlcov/index.html`.

### Executar testes específicos

```bash
# Por arquivo
pytest tests/test_auth.py

# Por classe
pytest tests/test_auth.py::TestAuthEndpoints

# Por teste específico
pytest tests/test_auth.py::TestAuthEndpoints::test_login_success
```

### Executar com verbose

```bash
pytest -v
```

### Executar com print statements

```bash
pytest -s
```

## Cobertura de Testes

Os testes cobrem as seguintes áreas:

### 1. Autenticação (`test_auth.py`)
- ✅ Registro de usuários
- ✅ Login com credenciais válidas/inválidas
- ✅ Geração e validação de tokens JWT
- ✅ Proteção de rotas autenticadas
- ✅ Hash de senhas

### 2. Serviços de Chat (`test_chat_services.py`)
- ✅ Criação de conversas
- ✅ Gerenciamento de mensagens
- ✅ Monitor assumindo controle
- ✅ Escalação de conversas
- ✅ Busca de conversas que precisam de atenção
- ✅ Rastreamento de atividade

### 3. Rotas da API (`test_chat_routes.py`)
- ✅ Endpoints de conversas
- ✅ Endpoints de monitor
- ✅ Autenticação em rotas protegidas
- ✅ Tratamento de erros (404, 401, etc.)
- ✅ Debug endpoints

### 4. Detecção de Crise (`test_crisis_detection.py`)
- ✅ Detecção de palavras-chave suicidas (CRITICAL)
- ✅ Detecção de auto-lesão (HIGH)
- ✅ Detecção de depressão (MEDIUM)
- ✅ Conversas normais (LOW)
- ✅ Análise de contexto
- ✅ Níveis de confiança
- ✅ Extração de keywords

## Fixtures Disponíveis

As fixtures estão definidas em `conftest.py`:

- `db_session` - Sessão de banco de dados em memória (SQLite)
- `client` - Cliente de teste para requisições HTTP
- `test_user` - Usuário de teste pré-criado
- `auth_token` - Token de autenticação válido
- `authenticated_client` - Cliente com autenticação configurada
- `test_conversation` - Conversa de teste
- `test_message` - Mensagem de teste
- `crisis_message` - Mensagem com conteúdo de crise

## Banco de Dados de Teste

Os testes utilizam **SQLite em memória** ao invés do PostgreSQL em produção. Isso:
- ✅ Torna os testes mais rápidos
- ✅ Não requer configuração de banco de dados
- ✅ Cada teste recebe um banco limpo
- ✅ Não interfere com dados de produção/desenvolvimento

## Testes Assíncronos

Testes que envolvem operações assíncronas devem usar o decorator `@pytest.mark.asyncio`:

```python
@pytest.mark.asyncio
async def test_async_function():
    result = await some_async_operation()
    assert result is not None
```

## Boas Práticas

1. **Isolamento**: Cada teste deve ser independente
2. **Fixtures**: Use fixtures para setup/teardown
3. **Nomes descritivos**: `test_login_with_wrong_password` é melhor que `test_login_2`
4. **Arrange-Act-Assert**: Organize os testes nesse padrão
5. **Cobertura**: Mantenha cobertura > 80%
6. **Mocking**: Use mocks para dependências externas (Ollama, etc.)

## Executando no CI/CD

Para integração contínua, use:

```bash
pytest --cov=app --cov-report=xml --cov-fail-under=80
```

Isso falhará se a cobertura for menor que 80%.

## Troubleshooting

### ImportError: No module named 'app'

Execute os testes do diretório raiz do backend:

```bash
cd /path/to/checkpoint/backend
pytest
```

### Testes lentos

Use `pytest -n auto` para executar testes em paralelo (requer `pytest-xdist`):

```bash
pip install pytest-xdist
pytest -n auto
```

### Banco de dados travado

Se você ver erros de "database is locked", certifique-se de que está usando `scope="function"` nas fixtures de banco.

## Contribuindo

Ao adicionar novas funcionalidades:

1. Escreva testes primeiro (TDD)
2. Mantenha cobertura de código > 80%
3. Teste casos de sucesso E erro
4. Use fixtures para código repetido
5. Adicione docstrings explicativas

## Métricas de Cobertura Atual

Execute `pytest --cov=app --cov-report=term-missing` para ver métricas atualizadas.

Meta: **> 80% de cobertura de código**
