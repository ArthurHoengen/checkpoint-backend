#!/usr/bin/env python3
"""
Script para executar o servidor Checkpoint com suporte a WebSocket/Socket.IO
"""

import uvicorn
from app.main import socket_app

if __name__ == "__main__":
    print("🚀 Iniciando servidor Checkpoint com WebSocket...")
    print("📡 WebSocket disponível em: ws://localhost:8000/socket.io/")
    print("🌐 API REST disponível em: http://localhost:8000")
    print("📚 Documentação em: http://localhost:8000/docs")
    print()

    uvicorn.run(
        socket_app,
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )