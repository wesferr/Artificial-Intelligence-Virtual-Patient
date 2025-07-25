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
from transformers import pipeline
import numpy as np
# from kokoro import KPipeline
import soundfile as sf

tts = TTS("tts_models/multilingual/multi-dataset/xtts_v2").to("cuda")
model = pipeline("automatic-speech-recognition", model="zuazo/whisper-large-v3-pt")
torch.set_num_threads(24)

ollama.chat("gemma3:12b", messages=[])

async def play_audio(queue):
    while True:
        audio_data = await queue.get()
        if audio_data is None:
            break
        pygame.mixer.music.load(io.BytesIO(audio_data))
        pygame.mixer.music.play()
        while pygame.mixer.music.get_busy():
            await asyncio.sleep(0.01)
            
# def gerar_audio_kokoro(text, voice='pf_dora_triste'):
#     generator = kpipeline(text, voice=voice, pitch=0.9, duration=1.3, energy=0.6)
#     buffer = io.BytesIO()
#     for _, _, audio in generator:
#         sf.write(buffer, audio, 24000, format='WAV')
#     buffer.seek(0)
#     return buffer.read()

# async def generate_audio(text, voice='pf_dora_triste'):
#     return await asyncio.to_thread(gerar_audio_kokoro, text, voice)

async def generate_audio(text, voicefile="audio/minhavoz.wav"):
    audio_buffer = io.BytesIO()
    await asyncio.to_thread(tts.tts_to_file, text=text, file_path=audio_buffer, speaker_wav=voicefile, language="pt", speed=1, repetition_penalty=4.0)
    audio_buffer.seek(0)
    return audio_buffer.read()

async def answer_text(messages, audio_data, queue, evaluation_times, voicefile="audio/minhavoz.wav"):

    tts_actual_time = time.time_ns()
    audio, sr = librosa.load(io.BytesIO(audio_data), sr=16000)  # sr=16000 é a taxa de amostragem que o Whisper espera
    audio = torch.from_numpy(audio).to('cuda')
    # result = model.transcribe(audio)
    audio = np.array(audio.cpu(), dtype=np.float32)
    result = model(audio)
    tts_final_time = time.time_ns()
    tts_time_diff = tts_final_time - tts_actual_time

    text_result = result["text"]
    evaluation_times["stt_times"].append((tts_time_diff*1e-6, tts_actual_time*1e-6, tts_final_time*1e-6, text_result))
    
    print(text_result)
    messages.append({"role": "user", "content": text_result,},)
    temporary_buffer = ai_response = ""

    stream = ollama.chat(model='gemma3:12b', messages=messages, stream=True,)

    llm_actual_time = time.time_ns()
    for chunk in stream:
        token = chunk['message']['content']
        ai_response += token

        ends_with_number = bool(re.fullmatch(r"^[a-zA-Z\s]+[0-9]+[.,]$", temporary_buffer))
        if ("." in token or "," in token) and not ends_with_number:

            llm_final_time = time.time_ns()
            llm_time_diff = llm_final_time - llm_actual_time
            time.sleep(llm_time_diff * 2 * 1e-9)  # Simula o tempo de espera para o LLM
            evaluation_times["llm_times"].append((llm_time_diff*1e-6, llm_actual_time*1e-6, llm_final_time*1e-6, temporary_buffer))
            llm_actual_time = time.time_ns()

            if temporary_buffer.lower() == " doutor":
                temporary_buffer = ""
                continue

            stt_actual_time = time.time_ns()
            audio_data = await generate_audio(temporary_buffer, voicefile="audio/ash_felicidade.mp3")
            stt_final_time = time.time_ns()
            stt_time_diff = stt_final_time - stt_actual_time
            evaluation_times["tts_times"].append((stt_time_diff*1e-6, stt_actual_time*1e-6, stt_final_time*1e-6))
            await queue.put(audio_data)
            evaluation_times["sent_audio_size"].append(librosa.get_duration(path=io.BytesIO(audio_data))*1000)
            
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