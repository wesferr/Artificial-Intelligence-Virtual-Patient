import torch, transformers, json, asyncio, sys, re
from TTS.api import TTS
import whisper
import pygame
import wave
import io

torch.set_default_device("cuda:0")

tts = TTS("tts_models/multilingual/multi-dataset/xtts_v2").to("cuda")
asrmodel = whisper.load_model("medium").to("cuda")

model_name = "microsoft/Phi-4-mini-instruct"
tokenizer = transformers.AutoTokenizer.from_pretrained(model_name)
bnb_config = transformers.BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_compute_dtype=torch.float16
)
model = transformers.AutoModelForCausalLM.from_pretrained(
    model_name,
    trust_remote_code=True,
    quantization_config=bnb_config,
    device_map="auto"
)

pygame.mixer.init()

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

async def answer_text(history, queue):
    result = asrmodel.transcribe("audio/paris.wav", language="pt")
    print(result["text"])
    history.append(result["text"])

    buffer = ""
    inputs = tokenizer("\n".join(history), return_tensors="pt", truncation=True).input_ids
    generated = inputs
    count = 0
    for _ in range(1000):
        output = model.generate(
            generated,
            max_new_tokens=1,
            top_k=50,
            pad_token_id=tokenizer.eos_token_id,
        )
        new_token = output[:, -1].unsqueeze(0)
        token = tokenizer.decode(new_token[0], skip_special_tokens=True)

        ends_with_number = bool(re.fullmatch(r"^[a-zA-Z\s]+[0-9]+\.$", buffer))
        if ("." in token or "," in token) and not ends_with_number:  # Se o token contém um ponto final
            audio_data = await generate_audio(buffer)
            print(buffer)
            await queue.put(audio_data)
            buffer = ""  # Reseta o buffer para a próxima frase
            count += 1
        else:
            buffer += token

        generated = torch.cat([generated, new_token], dim=1)

        # Parar se encontrar EOS
        if new_token.item() == tokenizer.eos_token_id:
            break

    await queue.put(None)  # Sinaliza para a tarefa de reprodução de áudio que terminou

    return tokenizer.decode(generated[0])

async def main():
    queue = asyncio.Queue()
    background = [
        "responda em uma unica sentença:",
        "me fale sobre paris"
    ]
    play_task = asyncio.create_task(play_audio(queue))
    await answer_text(background, queue)
    await play_task

asyncio.run(main())