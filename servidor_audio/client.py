import asyncio
import websockets
import tkinter as tk
import pyaudio
import wave
import threading
import platform
import queue

if platform.system()=='Windows':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# Configuração de áudio
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 48000
CHUNK = 1024
OUTPUT_FILENAME = "audio_recorded.wav"

class AudioRecorder:
    def __init__(self, master):
        self.server_uri = "ws://localhost:8765/oz"
        self.master = master
        self.master.title("Gravador de Áudio")
        self.audio_queue = asyncio.Queue()

        self.websocket = None
        # asyncio.run(self.connect())  # Usando create_task corretamente

        self.loop = asyncio.new_event_loop()  # Criando um loop de eventos novo
        self.tloop = threading.Thread(target=self.start_event_loop, daemon=True)
        self.tloop.start()

        self.is_running = True

        future = asyncio.run_coroutine_threadsafe(self.connect(), self.loop)
        future.result()
        asyncio.run_coroutine_threadsafe(self.receive_audio(), self.loop)
        asyncio.run_coroutine_threadsafe(self.play_audio_queue(), self.loop)
        self.is_recording = False

        self.label = tk.Label(master, text="Segure para gravar, solte para parar")
        self.label.pack(pady=10)

        self.record_button = tk.Button(master, text="Segure para gravar", bg="red", fg="white")
        self.record_button.pack(pady=5)
        self.record_button.bind("<ButtonPress-1>", self.start_recording)
        self.record_button.bind("<ButtonRelease-1>", self.stop_recording)
        self.master.protocol("WM_DELETE_WINDOW", self.on_closing)

    def start_event_loop(self):
        """Inicia o loop de eventos assíncrono em uma thread separada"""
        asyncio.set_event_loop(self.loop)
        self.loop.run_forever()

    async def connect(self):
        """Estabelece conexão com o servidor WebSocket."""
        try:
            self.websocket = await websockets.connect(self.server_uri, ping_interval=20, ping_timeout=20)
        except Exception as e:
            print(f"Erro ao conectar ao WebSocket: {e}")

    async def send_audio(self):
        """Envia o áudio gravado via WebSocket."""
        if self.websocket:
            try:
                with open(OUTPUT_FILENAME, "rb") as wf:
                    data = wf.read()
                    await self.websocket.send(data)
            except Exception as e:
                print(f"Erro ao enviar áudio: {e}")

    def start_recording(self, event=None):
        """Inicia a gravação de áudio."""
        self.is_recording = True
        self.audio = pyaudio.PyAudio()
        self.stream = self.audio.open(format=FORMAT, channels=CHANNELS, rate=RATE, input=True, frames_per_buffer=CHUNK)
        self.frames = []
        self.thread = threading.Thread(target=self.record)
        self.thread.start()

    def record(self):
        """Grava o áudio enquanto o botão estiver pressionado."""
        while self.is_recording:
            data = self.stream.read(CHUNK)
            self.frames.append(data)

    def stop_recording(self, event=None):
        """Finaliza a gravação e salva o arquivo."""
        self.is_recording = False
        self.thread.join()
        self.stream.stop_stream()
        self.stream.close()
        self.audio.terminate()

        with wave.open(OUTPUT_FILENAME, "wb") as wf:
            wf.setnchannels(CHANNELS)
            wf.setsampwidth(self.audio.get_sample_size(FORMAT))
            wf.setframerate(RATE)
            wf.writeframes(b"".join(self.frames))

        self.label.config(text="Áudio salvo e enviado para o servidor WebSocket")
        asyncio.run_coroutine_threadsafe(self.send_audio(), self.loop)  # Envia áudio sem bloquear a GUI

    async def receive_audio(self):
        """Recebe áudio do servidor e adiciona à fila"""
        print("Aguardando áudio do servidor...")
        while self.is_running:
            try:
                data = await self.websocket.recv()
                print("Áudio recebido do servidor")
                await self.audio_queue.put(data)  # Adiciona áudio na fila assíncrona
                self.label.config(text="Áudio recebido e adicionado à fila")
            except Exception as e:
                print(f"Erro ao receber áudio: {e}")

    async def play_audio_queue(self):
        """Reproduz áudio continuamente da fila"""
        p = pyaudio.PyAudio()
        stream = p.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=RATE,
            output=True
        )

        while self.is_running:
            try:
                audio_data = await self.audio_queue.get()  # Aguarda áudio na fila
                print("Reproduzindo áudio recebido...")
                stream.write(audio_data)
            except Exception as e:
                print(f"Erro na reprodução de áudio: {e}")

        stream.stop_stream()
        stream.close()
        p.terminate()

    def cancel_all_tasks(self):
    # get all tasks
        tasks = asyncio.all_tasks(loop=self.loop)
        # cancel all tasks
        for task in tasks:
            # request the task cancel
            task.cancel()

    def on_closing(self):
        self.is_running = False
        self.cancel_all_tasks()
        if self.websocket:
            future = asyncio.run_coroutine_threadsafe(self.close_websocket(), self.loop)
            future.result()
        self.loop.call_soon_threadsafe(self.loop.stop)
        self.master.destroy()

    async def close_websocket(self):
        """Fecha conexão WebSocket de forma assíncrona"""
        if self.websocket:
            try:
                await self.websocket.close()
                print("WebSocket fechado corretamente.")
            except Exception as e:
                print(f"Erro ao fechar WebSocket: {e}")


def tkloop():
    root = tk.Tk()
    app = AudioRecorder(root)
    root.mainloop()

if __name__ == "__main__":
    tkloop()  # Inicia o loop de eventos do tkinter