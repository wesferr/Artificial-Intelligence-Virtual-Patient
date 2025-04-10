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
import time
from concurrent.futures import ThreadPoolExecutor
from torch.profiler import profile, record_function, ProfilerActivity

tts = TTS("tts_models/multilingual/multi-dataset/xtts_v2").to("cuda")
model = whisper.load_model("medium").to("cuda")
torch.set_num_threads(24)

ollama.chat("gemma3:4b", messages=[])

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
    await asyncio.to_thread(tts.tts_to_file, text=text, file_path=audio_buffer, speaker_wav="audio/minhavoz.wav", language="pt", speed=1, repetition_penalty=4.0)
    audio_buffer.seek(0)
    return audio_buffer.read()

async def answer_text(messages, audio_data, queue, evaluation_times):


    tts_actual_time = time.time_ns()
    audio, sr = librosa.load(io.BytesIO(audio_data), sr=16000)  # sr=16000 é a taxa de amostragem que o Whisper espera
    audio = torch.from_numpy(audio).to('cuda')
    result = model.transcribe(audio)
    tts_time_diff = time.time_ns() - tts_actual_time
    evaluation_times["stt_times"].append(tts_time_diff*1e-6)

    text_result = result["text"]
    print(text_result)
    messages.append({"role": "user", "content": text_result,},)
    temporary_buffer = ai_response = ""

    stream = ollama.chat(model='gemma3:4b', messages=messages, stream=True,)

    llm_actual_time = time.time_ns()
    for chunk in stream:
        token = chunk['message']['content']
        ai_response += token

        ends_with_number = bool(re.fullmatch(r"^[a-zA-Z\s]+[0-9]+[.,]$", temporary_buffer))
        if ("." in token) and not ends_with_number:

            llm_time_diff = time.time_ns() - llm_actual_time
            llm_actual_time = time.time_ns()
            evaluation_times["llm_times"].append(llm_time_diff*1e-6)

            if temporary_buffer.lower() == " doutor":
                temporary_buffer = ""
                continue

            stt_actual_time = time.time_ns()
            audio_data = await generate_audio(temporary_buffer)
            stt_time_diff = time.time_ns() - stt_actual_time
            evaluation_times["tts_times"].append(stt_time_diff*1e-6)
            await queue.put(audio_data)
            evaluation_times["sent_audio_times"].append(librosa.get_duration(path=io.BytesIO(audio_data))*1000)
            
            print(temporary_buffer, end="", flush=True)
            temporary_buffer = ""
            

        else:
            temporary_buffer += token

    await queue.put(None)
    messages.append({"role": "assistant", "content": ai_response,},)

    return messages

async def main():

    pygame.mixer.init()
    data = open("context.json", "r", encoding='utf-8').read()
    data = json.loads(data)
    context = '''
    Você é {0}, e está aqui porque {2}, você responde conforme as perguntas {3}.
    Responda apenas como {0}, com base nas informações fornecidas. Responda em uma unica sentença, e somente oque foi perguntado, e não responda novamente uma pergunta anterior.
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