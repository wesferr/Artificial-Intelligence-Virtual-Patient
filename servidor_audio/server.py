import asyncio
import websockets
import chatbot
import json
import time

# Lista de clientes conectados
clients_ai = set()
clients_oz = set()
time_delay = 0

try:
    evaluation_times = json.loads(open("time_diffs.json", "r", encoding='utf-8').read())
except Exception as e:
    evaluation_times = {
        "llm_times": [],
        "tts_times": [],
        "stt_times": [],
        "audio_times": [],
        "send_times": [],
        "receive_times": [],
    }

actual_time2 = time.time_ns()

data = open("context2.json", "r", encoding='utf-8').read()
data = json.loads(data)
context = '''
Você é {0}, e está aqui porque {2}, você responde conforme as perguntas {3}.
Responda apenas como {0}, com base nas informações fornecidas. Responda em uma unica sentença, e somente oque foi perguntado.
'''
perguntas_formatadas = "\n".join(
    [f"Pergunta: {p['pergunta']}, Resposta: {p['resposta']}" for p in data['perguntas_lista']]
)
context = context.format(
    data["acompanhante"]["nome"] + " do paciente " + data["paciente"]["nome"] if "acompanhante" in data and "nome" in data["acompanhante"] else data["paciente"]["nome"],
    data["cenario"],
    data["descricao"],
    perguntas_formatadas)

background = [
    {"role": "system", "content": context,},
]

async def send_and_recv(client, audio_data):
    global actual_time2
    actual_time2 = time.time_ns()
    await client.send(audio_data)

async def play_audio(queue, websocket):
    while True:
        audio_data = await queue.get()
        if audio_data is None:
            break
        for client in list(clients_ai):
            if client.state == 3:
                clients_ai.remove(client)
        asyncio.gather(*(send_and_recv(client, audio_data) for client in clients_ai))
        # await asyncio.gather(*(client.send(audio_data) for client in clients_ai))

async def handler(websocket):
    # Adiciona cliente à lista
    global background
    global evaluation_times
    global actual_time2
    request = websocket.request
    if websocket not in clients_ai and websocket not in clients_oz:
        actual_time1 = time.time_ns()
        ping = await websocket.send("")
        pong = await websocket.recv()
        time_delay = (time.time_ns() - actual_time1)/2

    try:
        async for message in websocket:
            try:
                if message.decode().isnumeric():
                    print(message, message.decode())
                    # print("Ping: ", message)
                    recv_time = int(message.decode())
                    # open("time_diffs.json", "a").write(json.dumps({"time_recieve": recv_time}, indent=4, ensure_ascii=False))
                    evaluation_times["receive_times"].append(recv_time*1e-6)
                    continue
            except Exception as e:
                pass
            if message == "":
                evaluation_times["send_times"].append((time.time_ns() - actual_time2 - time_delay)*1e-6)
                # network_time.append((time.time_ns() - actual_time - time_delay)*1e-6)
                # open("time_diffs.json", "a").write(json.dumps({"send_time": network_time}, indent=4, ensure_ascii=False))
                continue
            #Propaga a mensagem para todos os clientes conectados, exceto o remetente
            if request.path == "/oz":
                clients_oz.add(websocket)
                for client in list(clients_oz):
                    if client.state == 3:
                        clients_oz.remove(client)
                asyncio.gather(*(send_and_recv(client, audio_data) for client in clients_oz if client != websocket))
                # await asyncio.gather(*(client.send(message) for client in clients_oz if client != websocket))
            if request.path == "/ai":
                await websocket.send("")
                clients_ai.add(websocket)
                queue = asyncio.Queue()
                play_task = asyncio.create_task(play_audio(queue, websocket))
                background = await chatbot.answer_text(background, message, queue, evaluation_times)

            open("time_diffs.json", "w").write(json.dumps(evaluation_times, indent=4, ensure_ascii=False))
    except websockets.exceptions.ConnectionClosed as e:
        print(e)

async def main():
    server = await websockets.serve(handler, "192.168.0.120", 8765, ping_interval=20, ping_timeout=20)
    print("Servidor WebSockets iniciado em ws://localhost:8765")
    await server.wait_closed()

if __name__ == "__main__":
    asyncio.run(main())
