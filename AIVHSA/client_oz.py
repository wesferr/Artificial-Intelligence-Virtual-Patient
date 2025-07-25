import asyncio
import websockets
import tkinter as tk
import pyaudio
import wave
import threading
import platform
import queue
import time 
if platform.system()=='Windows':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# Configuração de áudio
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 24000
CHUNK = 1024
OUTPUT_FILENAME = "audio_recorded.wav"

class AudioRecorder:
    def __init__(self, master):
        self.server_uri = "ws://<IP HERE>:8765/oz1"
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

        self.label = tk.Label(master, text="Mande uma mensagem")
        self.label.pack(pady=10)

        self.entry = tk.Entry(master, width=50)
        self.entry.pack(pady=10)
        
        self.entry.bind("<Return>", lambda event: self.send_message())

        self.submit_button = tk.Button(master, text="Enviar", command=self.send_message)
        self.submit_button.pack(pady=10)
        
        self.master.protocol("WM_DELETE_WINDOW", self.on_closing)

    # Adicione o método send_message na classe
    def send_message(self):
        """Envia a mensagem do TextBox para o servidor WebSocket."""
        message = self.entry.get()
        if message and self.websocket:  # Verifica se há mensagem e conexão WebSocket
            asyncio.run_coroutine_threadsafe(self.websocket.send(b""), self.loop)
            asyncio.run_coroutine_threadsafe(self.websocket.send(message), self.loop)
            print(f"Mensagem enviada: {message}")
            self.entry.delete(0, tk.END)  # Limpa o campo de texto
        else:
            print("Não foi possível enviar a mensagem. Verifique a conexão.")

    def start_event_loop(self):
        """Inicia o loop de eventos assíncrono em uma thread separada"""
        asyncio.set_event_loop(self.loop)
        self.loop.run_forever()

    async def connect(self):
        """Estabelece conexão com o servidor WebSocket."""
        try:
            self.websocket = await websockets.connect(self.server_uri, ping_interval=20, ping_timeout=20)
            print("Conectado ao servidor WebSocket.")
        except Exception as e:
            print(f"Erro ao conectar ao WebSocket: {e}")

    async def send_audio(self):
        """Envia o áudio gravado via WebSocket."""
        if self.websocket:
            try:
                with open(OUTPUT_FILENAME, "rb") as wf:
                    data = wf.read()
                    await self.websocket.send("")
                    await self.websocket.send(data)
                    print("Áudio enviado com sucesso!")


            except Exception as e:
                print(f"Erro ao enviar áudio: {e}")

    async def receive_audio(self):
        """Recebe áudio do servidor e adiciona à fila"""
        print("Aguardando áudio do servidor...")
        while self.is_running:
            try:
                print("try")
                data = await self.websocket.recv()
                print("Áudio recebido do servidor")
                await self.audio_queue.put(data)  # Adiciona áudio na fila assíncrona
                self.label.config(text="Áudio recebido e adicionado à fila")
            except Exception as e:
                print(f"Erro ao receber áudio: {e}")
                break

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