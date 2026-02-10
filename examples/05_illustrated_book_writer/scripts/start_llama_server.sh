#!/bin/bash
# Example script to start Llama.cpp server on a remote Linux machine
# Usage: ./start_llama_server.sh

# Configuration
MODEL_PATH="./models/Your-Model-Name.gguf"
PORT=8080
HOST="0.0.0.0"
GPU_LAYERS=35
CTX_SIZE=32768
PARALLEL=4

echo "Starting Llama.cpp server..."
echo "Model: $MODEL_PATH"
echo "Port: $PORT"

./llama-server \
    -m "$MODEL_PATH" \
    --port $PORT \
    --host $HOST \
    --n-gpu-layers $GPU_LAYERS \
    --ctx-size $CTX_SIZE \
    --parallel $PARALLEL
