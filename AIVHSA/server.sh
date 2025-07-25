# Ativar ambiente Python
source venv/bin/activate

# Iniciar Ollama (supondo que você tenha um binário ou script de inicialização)

../ollama/bin/ollama serve &>/dev/null &

# Rodar o servidor websocket
python server.py