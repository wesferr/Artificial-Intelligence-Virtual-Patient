import ollama
import torch
from TTS.api import TTS
import whisper
import json
import asyncio
import re
import io
import librosa
import pygame

tts = TTS("tts_models/multilingual/multi-dataset/xtts_v2").to("cuda")
model = whisper.load_model("medium")

async def play_audio(queue):
    while True:
        audio_data = await queue.get()
        if audio_data is None:
            break
        pygame.mixer.music.load(io.BytesIO(audio_data))
        pygame.mixer.music.play()
        while pygame.mixer.music.get_busy():
            await asyncio.sleep(0.01)

async def generate_audio(text):
    audio_buffer = io.BytesIO()
    await asyncio.to_thread(tts.tts_to_file, text=text, file_path=audio_buffer, speaker_wav="audio/minhavoz.wav", language="pt", speed=1)
    audio_buffer.seek(0)
    return audio_buffer.read()

async def answer_text(messages, audio_data, queue):
    audio, sr = librosa.load(io.BytesIO(audio_data), sr=16000)  # sr=16000 é a taxa de amostragem que o Whisper espera
    result = model.transcribe(audio)
    text_result = result["text"]
    print(text_result)
    messages.append({"role": "system", "content": text_result,},)
    temporary_buffer = ai_response = ""
    # messages.append({"role": "user", "content": "olá, eu sou o doutor wesley, oque traz vocês aqui hoje?",},)

    stream = ollama.chat(
        model='gemma3:1b',
        messages=messages,
        stream=True,
    )
    for chunk in stream:

        token = chunk['message']['content']
        ai_response += token

        ends_with_number = bool(re.fullmatch(r"^[a-zA-Z\s]+[0-9]+[.,]$", temporary_buffer))
        if ("." in token or "," in token) and not ends_with_number:
            print(temporary_buffer)
            audio_data = await generate_audio(temporary_buffer)
            await queue.put(audio_data)
            temporary_buffer = ""
        else:
            temporary_buffer += token

    messages.append({"role": "assistant", "content": ai_response,},)
    return messages

async def main():

    pygame.mixer.init()
    data = open("context.json", "r", encoding='utf-8').read()
    data = json.loads(data)
    context = '''
    Você é {0}, e está aqui porque {2}, você responde conforme as perguntas {3}.
    Responda apenas como {0}, com base nas informações fornecidas. Responda em uma unica sentença.
    '''
    perguntas_formatadas = "\n".join(
        [f"Pergunta: {p['pergunta']}, Resposta: {p['resposta']}" for p in data['perguntas_lista']]
    )
    context = context.format(
        'mãe' + " do paciente " + data["paciente"]["nome"] if "acompanhante" in data else data["paciente"]["nome"],
        data["cenario"],
        data["descricao"],
        perguntas_formatadas)

    messages = [
        {"role": "system", "content": context,},
    ]

    audio_data = open("audio/paris.wav", "rb").read()
    queue = asyncio.Queue()

    play_task = asyncio.create_task(play_audio(queue))
    messages = await answer_text(messages, audio_data, queue)
    print(messages)

    await play_task


if __name__ == "__main__":
    asyncio.run(main())