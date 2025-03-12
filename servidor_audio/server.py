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
import chatbot

# Lista de clientes conectados
clients = set()
background = ["responda em uma unica sentença, sem exemplos:",]

async def play_audio(queue, websocket):
    while True:
        audio_data = await queue.get()
        if audio_data is None:
            break
        await asyncio.gather(*(client.send(audio_data) for client in clients))

async def handler(websocket):
    # Adiciona cliente à lista
    clients.add(websocket)
    request = websocket.request
    try:
        async for message in websocket:
            # Propaga a mensagem para todos os clientes conectados, exceto o remetente
            if request.path == "/oz":
                await asyncio.gather(*(client.send(message) for client in clients if client != websocket))
            if request.path == "/ai":
                queue = asyncio.Queue()
                play_task = asyncio.create_task(play_audio(queue, websocket))
                await chatbot.answer_text(background, message, queue)
    except websockets.exceptions.ConnectionClosed as e:
        print(e)
    finally:
        # Remove cliente da lista ao desconectar
        clients.remove(websocket)

async def main():
    server = await websockets.serve(handler, "localhost", 8765, ping_interval=20, ping_timeout=20)
    print("Servidor WebSockets iniciado em ws://localhost:8765")
    await server.wait_closed()

if __name__ == "__main__":
    asyncio.run(main())
