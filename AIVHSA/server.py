import asyncio
import websockets
import chatbot
import json
import time
import librosa
import io
from load_context import load_context

# Lista de clientes conectados
clients_ai1 = dict()
clients_ai2 = dict()
clients_oz = dict()
time_delay = 0

try:
    evaluation_times = json.loads(open("time_diffs.json", "r", encoding='utf-8').read())
except Exception as e:
    evaluation_times = {
        "llm_times": [],
        "tts_times": [],
        "stt_times": [],
        "sent_audio_size": [],
        "recieved_audio_size": [],
        "send_times": [],
        "receive_times": [],
    }

background1 = [
    {"role": "system", "content": open("context3.json", "r", encoding='utf-8').read(),},
]
background2 = [
    {"role": "system", "content": load_context("context2.json"),},
]

evaluation_times["basal_time"] = time.time_ns() * 1e-6

async def send_and_recv(client, audio_data):
    ini_time = time.time_ns()
    await client.send(audio_data)
    end_time = time.time_ns()
    message_send_time = end_time - ini_time
    evaluation_times["send_times"].append((message_send_time, ini_time*1e-6, end_time*1e-6))

async def play_audio_oz(sender, message):
    audio_data = await chatbot.generate_audio(message, voicefile="audio/minhavoz.wav")
    # Send audio to all clients in clients_oz except the sender
    await asyncio.gather(
        *(send_and_recv(client, audio_data) for client_id, client in clients_oz.items() if client != sender)
    )

async def play_audio1(queue, websocket):
    while True:
        audio_data = await queue.get()
        if audio_data is None:
            break
        # Remove disconnected clients
        for client_id, client in list(clients_ai1.items()):
            if client.state == 3:
                del clients_ai1[client_id]
        # Send audio to all clients in clients_ai1
        await asyncio.gather(
            *(send_and_recv(client, audio_data) for client_id, client in clients_ai1.items())
        )

async def play_audio2(queue, websocket):
    while True:
        audio_data = await queue.get()
        if audio_data is None:
            break
        # Remove disconnected clie nts
        for client_id, client in list(clients_ai2.items()):
            if client.state == 3:
                del clients_ai2[client_id]
        # Send audio to all clients in clients_ai2
        await asyncio.gather(
            *(send_and_recv(client, audio_data) for client_id, client in clients_ai2.items())
        )

async def handler(websocket):
    # Adiciona cliente à lista
    global background1, background2
    global evaluation_times
    request = websocket.request

    try:
        while True:
            # Recebe mensagem do cliente
            message = await websocket.recv()
            ini_time = time.time_ns()
            message = await websocket.recv()
            end_time = time.time_ns()
            message_recieve_time = end_time - ini_time
            #Propaga a mensagem para todos os clientes conectados, exceto o remetente

            if request.path == "/oz1":
                print("message: ", message)
                clients_oz[websocket.id] = websocket  # Add websocket to the dictionary
                # Remove disconnected clients
                for client_id, client in list(clients_oz.items()):
                    if client.state == 3:
                        del clients_oz[client_id]
                # Send audio to all clients except the sender
                # for client_id, client in clients_oz.items():
                #     if client != websocket:
                await play_audio_oz(websocket, message)

            if request.path == "/oz":
                # print("message: ", message)
                clients_oz[websocket.id] = websocket  # Add websocket to the dictionary
                # Remove disconnected clients
                for client_id, client in list(clients_oz.items()):
                    if client.state == 3:
                        del clients_oz[client_id]
                # Send audio to all clients except the sender
                # for client_id, client in clients_oz.items():
                #     if client != websocket:
                await asyncio.gather(
                    *(send_and_recv(client, message) for client_id, client in clients_oz.items() if client != websocket)
                )

            if request.path == "/ai1":
                evaluation_times["receive_times"].append((message_recieve_time * 1e-6, ini_time * 1e-6, end_time * 1e-6))
                evaluation_times["recieved_audio_size"].append(librosa.get_duration(path=io.BytesIO(message)) * 1000)
                clients_ai1[websocket.id] = websocket  # Add websocket to the dictionary
                queue = asyncio.Queue()
                asyncio.create_task(play_audio1(queue, websocket))
                background1 = await chatbot.answer_text(background1, message, queue, evaluation_times, voicefile="audio/ash_felicidade.mp3")

            if request.path == "/ai2":
                evaluation_times["receive_times"].append((message_recieve_time * 1e-6, ini_time * 1e-6, end_time * 1e-6))
                evaluation_times["recieved_audio_size"].append(librosa.get_duration(path=io.BytesIO(message)) * 1000)
                clients_ai2[websocket.id] = websocket  # Add websocket to the dictionary
                queue = asyncio.Queue()
                asyncio.create_task(play_audio2(queue, websocket))
                background2 = await chatbot.answer_text(background2, message, queue, evaluation_times, voicefile="audio/minhavoz2.wav")
            open("time_diffs.json", "w").write(json.dumps(evaluation_times, indent=4, ensure_ascii=False))
    except websockets.exceptions.ConnectionClosed as e:
        print(e)

async def main():
    server = await websockets.serve(handler, "0.0.0.0", 8765, ping_interval=20, ping_timeout=20)
    print("Servidor WebSockets iniciado em ws://0.0.0.0:8765")
    await server.wait_closed()

if __name__ == "__main__":
    asyncio.run(main())
