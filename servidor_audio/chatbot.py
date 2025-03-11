import torch, transformers, json, asyncio, sys, re
from TTS.api import TTS
import whisper
import pyaudio
import wave
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

def play_audio(file_path):
    chunk = 1024
    wf = wave.open(file_path, 'rb')
    p = pyaudio.PyAudio()
    stream = p.open(format=p.get_format_from_width(wf.getsampwidth()),
                    channels=wf.getnchannels(),
                    rate=wf.getframerate(),
                    output=True)
    data = wf.readframes(chunk)
    while data:
        stream.write(data)
        data = wf.readframes(chunk)
    stream.stop_stream()
    stream.close()
    p.terminate()

def answer_text(history):

    result = asrmodel.transcribe("paris.wav", language="pt")
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
            tts.tts_to_file(
                    text=buffer,
                    file_path=f"audio_{count}.wav",
                    speaker_wav="minhavoz.wav",
                    language="pt",
                    speed=1.5,  # Aumenta a velocidade em 50%
            )
            play_audio(f"audio_{count}.wav")
            buffer = ""  # Reseta o buffer para a próxima frase
            count += 1
        else:
            buffer += token

        generated = torch.cat([generated, new_token], dim=1)

        # Parar se encontrar EOS
        if new_token.item() == tokenizer.eos_token_id:
            break

    return tokenizer.decode(generated[0])

background = [
    "responda em uma unica sentença:",
    "me fale sobre paris"
]

answer_text(background)