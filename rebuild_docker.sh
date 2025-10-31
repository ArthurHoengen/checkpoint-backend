#!/bin/bash

echo "🔄 Parando containers existentes..."
docker-compose down

echo "🗑️  Removendo imagem antiga..."
docker rmi checkpoint_backend-api 2>/dev/null || true

echo "🏗️  Rebuilding imagem com dependências WebSocket..."
docker-compose build --no-cache

echo "🚀 Iniciando containers..."
docker-compose up -d

echo "📊 Status dos containers:"
docker-compose ps

echo ""
echo "✅ Rebuild concluído!"
echo "🌐 API: http://localhost:8000"
echo "📡 WebSocket: ws://localhost:8000/socket.io/"
echo "📚 Docs: http://localhost:8000/docs"
echo ""
echo "Para ver logs: docker-compose logs -f api"