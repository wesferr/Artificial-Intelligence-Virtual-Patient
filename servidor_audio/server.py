import asyncio
import websockets
import chatbot
import json

# Lista de clientes conectados
clients_ai = set()
clients_oz = set()

data = open("context.json", "r", encoding='utf-8').read()
data = json.loads(data)
context = '''
Você é {0}, e está aqui porque {2}, você responde conforme as perguntas {3}.
Responda apenas como {0}, com base nas informações fornecidas. Responda em uma unica sentença, e somente oque foi perguntado.
'''
perguntas_formatadas = "\n".join(
    [f"Pergunta: {p['pergunta']}, Resposta: {p['resposta']}" for p in data['perguntas_lista']]
)
context = context.format(
    'mãe' + " do paciente " + data["paciente"]["nome"] if "acompanhante" in data else data["paciente"]["nome"],
    data["cenario"],
    data["descricao"],
    perguntas_formatadas)

background = [
    {"role": "system", "content": context,},
]

async def play_audio(queue, websocket):
    while True:
        audio_data = await queue.get()
        if audio_data is None:
            break
        await asyncio.gather(*(client.send(audio_data) for client in clients_ai))

async def handler(websocket):
    # Adiciona cliente à lista
    global background
    request = websocket.request
    try:
        async for message in websocket:
            #Propaga a mensagem para todos os clientes conectados, exceto o remetente
            if request.path == "/oz":
                clients_oz.add(websocket)
                print("recebi pelo oz")
                await asyncio.gather(*(client.send(message) for client in clients_oz))
            if request.path == "/ai":
                clients_ai.add(websocket)
                print("recebi pelo ai")
                queue = asyncio.Queue()
                play_task = asyncio.create_task(play_audio(queue, websocket))
                background = await chatbot.answer_text(background, message, queue)
    except websockets.exceptions.ConnectionClosed as e:
        print(e)

async def main():
    server = await websockets.serve(handler, "192.168.0.120", 8765, ping_interval=20, ping_timeout=20)
    print("Servidor WebSockets iniciado em ws://localhost:8765")
    await server.wait_closed()

if __name__ == "__main__":
    asyncio.run(main())
