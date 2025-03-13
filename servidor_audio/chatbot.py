import torch, transformers, json, asyncio, sys, re
import torchaudio
from TTS.api import TTS
import whisper
import wave
import io
import numpy as np
import tempfile
import soundfile as sf
import pygame

pygame.mixer.init()

torch.set_default_device("cuda:0")

tts = TTS("tts_models/multilingual/multi-dataset/xtts_v2").to("cuda")
# asrmodel = whisper.load_model("small").to("cuda")
transcribe = transformers.pipeline(
    task="automatic-speech-recognition",
    model="jlondonobo/whisper-medium-pt",
    chunk_length_s=30,
    device_map="auto",
)

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

def convert_wav_bytes_to_numpy(wav_bytes, target_sr=16000):
    """Lê um arquivo WAV em bytes, converte para tensor, faz resampling para 16kHz e normaliza."""
    wav_io = io.BytesIO(wav_bytes)

    try:
        # Carregar áudio a partir dos bytes
        waveform, sample_rate = torchaudio.load(wav_io, normalize=True)

        # Converter para mono se for estéreo
        if waveform.shape[0] > 1:
            waveform = torch.mean(waveform, dim=0, keepdim=True)

        # Fazer resampling para 16kHz, se necessário
        if sample_rate != target_sr:
            transform = torchaudio.transforms.Resample(orig_freq=sample_rate, new_freq=target_sr)
            waveform = transform(waveform)
            sample_rate = target_sr

        # Normalizar o áudio para -1 a 1
        waveform = waveform / waveform.abs().max()

        # Converter para NumPy e remover dimensão extra
        audio_np = waveform.squeeze(0).numpy()

        return audio_np, sample_rate

    except Exception as e:
        raise ValueError(f"Erro ao processar o arquivo WAV: {e}")

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

async def answer_text(history, audio_data, queue):

    audionp, sr = convert_wav_bytes_to_numpy(audio_data)
    result = transcribe(audionp)
    print(result["text"])
    history.append(result["text"])

    buffer = ""
    inputs = tokenizer("\n".join(history), return_tensors="pt", truncation=True).input_ids
    generated = inputs
    count = 0
    for _ in range(1000):
        output = None
        with torch.no_grad():
            output = model.generate(
                generated,
                max_new_tokens=1,
                top_k=50,
                pad_token_id=tokenizer.eos_token_id,
            )
        torch.cuda.empty_cache()
        new_token = output[:, -1].unsqueeze(0)
        token = tokenizer.decode(new_token[0], skip_special_tokens=True)

        ends_with_number = bool(re.fullmatch(r"^[a-zA-Z\s]+[0-9]+\.$", buffer))
        if ("." in token or "," in token) and not ends_with_number:  # Se o token contém um ponto final
            audio_data = await generate_audio(buffer)
            print(buffer)
            await queue.put(audio_data)
            history.append(buffer)
            buffer = ""  # Reseta o buffer para a próxima frase
            count += 1
        else:
            buffer += token

        generated = torch.cat([generated, new_token], dim=1)

        # Parar se encontrar EOS
        if new_token.item() == tokenizer.eos_token_id:
            break

    await queue.put(None)  # Sinaliza para a tarefa de reprodução de áudio que terminou

    return history

async def main():
    audio_data = open("audio/paris.wav", "rb").read()
    queue = asyncio.Queue()
    background = ["responda em uma unica sentença, sem exemplos:",]
    play_task = asyncio.create_task(play_audio(queue))
    background = await answer_text(background, audio_data, queue)
    print(background)
    await play_task


if __name__ == "__main__":
    asyncio.run(main())