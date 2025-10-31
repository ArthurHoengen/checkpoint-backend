import socketio
from fastapi import FastAPI
from .manager import socket_manager

def create_socket_app(app: FastAPI) -> socketio.ASGIApp:
    """Create and configure the Socket.IO ASGI app"""

    # Mount the Socket.IO app
    socket_app = socketio.ASGIApp(
        socket_manager.sio,
        other_asgi_app=app,
        socketio_path='/socket.io'
    )

    return socket_app