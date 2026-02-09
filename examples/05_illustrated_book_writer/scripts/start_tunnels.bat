@echo off
echo Opening tunnels for ComfyUI and Ollama to Remote GPU Server...

:: Configuration - EDIT THESE
set REMOTE_USER=username
set REMOTE_HOST=remote_ip_or_hostname

:: Tunnel for ComfyUI (Local 11002 -> Remote 8188)
:: NOTE: This maps local port 11002 to the remote port 8188 (ComfyUI default)
start /b ssh -L 11002:localhost:8188 %REMOTE_USER%@%REMOTE_HOST% -N

:: Tunnel for Ollama (Local 11435 -> Remote 11434)
:: NOTE: This maps local port 11435 to remote port 11434 (Ollama default)
start /b ssh -L 11435:localhost:11434 %REMOTE_USER%@%REMOTE_HOST% -N

:: Tunnel for llamacp (Local 11003 -> Remote 11005)
:: NOTE: This maps local port 11003 to remote port 11005 (where llama-server is running)
start /b ssh -L 11003:localhost:11005 %REMOTE_USER%@%REMOTE_HOST% -N

echo Tunnels active! You can start the application now.
pause
