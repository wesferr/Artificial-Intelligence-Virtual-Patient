# import asyncio
# import websockets
# import json

# async def handle_connection(websocket):
#     request = websocket.request
#     async for message in websocket:
#         print("received message")
#         if request.path == "/audio":
#             file = open(f"audio.wav", "wb")
#             file.write(message)
#             await websocket.send(message)

# async def main():
#     server = await websockets.serve(handle_connection, "localhost", 8765)
#     await server.wait_closed()

# asyncio.run(main())  # Forma correta de iniciar o loop em Python 3.10+

import asyncio
import websockets

# Lista de clientes conectados
clients = set()

async def handler(websocket):
    # Adiciona cliente à lista
    clients.add(websocket)
    request = websocket.request
    try:
        async for message in websocket:
            # Propaga a mensagem para todos os clientes conectados, exceto o remetente
            await asyncio.gather(*(client.send(message) for client in clients if client != websocket))
    except websockets.exceptions.ConnectionClosed:
        pass
    finally:
        # Remove cliente da lista ao desconectar
        clients.remove(websocket)

async def main():
    server = await websockets.serve(handler, "localhost", 8765)
    print("Servidor WebSockets iniciado em ws://localhost:8765")
    await server.wait_closed()

if __name__ == "__main__":
    asyncio.run(main())
