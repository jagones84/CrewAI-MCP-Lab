@echo off
echo Opening DGX Spark tunnels for example 05...

:: Configuration
set REMOTE_USER=jagones
set REMOTE_HOST=DGX-SPARK-ETH

:: Default example-05 LLM path: local 11003 -> remote 8092 (DGX llama.cpp / Qwen 3.6 Opus Abliterated)
start /b ssh -L 11003:localhost:8092 %REMOTE_USER%@%REMOTE_HOST% -N

:: Default example-05 image path: local 11002 -> remote 8188 (ComfyUI)
start /b ssh -L 11002:localhost:8188 %REMOTE_USER%@%REMOTE_HOST% -N

:: Optional fallback tunnel: local 11435 -> remote 11434 (Ollama)
start /b ssh -L 11435:localhost:11434 %REMOTE_USER%@%REMOTE_HOST% -N

echo DGX tunnels active. Run python scripts\test_dgx_llm_tunnel.py before python src\main.py
pause
