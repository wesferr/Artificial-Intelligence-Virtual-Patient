import whisper
from pathlib import Path

model = whisper.load_model("large-v3")

audio_files = [
    "./interviews/Recording_3.mp3",
    "./interviews/Recording_4.mp3",
    "./interviews/Recording_5.mp3",
    "./interviews/Recording_6.mp3",
    "./interviews/Recording_7.mp3",
    "./interviews/Recording_8.mp3",
    "./interviews/Recording_9.mp3",
    "./interviews/Recording_10.mp3",
]

# Transcrever todos os áudios
transcriptions = {}
for audio_path in audio_files:
    result = model.transcribe(audio_path, verbose=False)
    with open(f"{audio_path}.txt", "w", encoding="utf-8") as f:
        f.write(result["text"])