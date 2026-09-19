@echo off
REM ============================================================================
REM Open DGX Spark tunnels required by example 04 (ComfyUI image generation).
REM Edit REMOTE_USER / REMOTE_HOST below to match your environment.
REM ============================================================================

set REMOTE_USER=jagones
set REMOTE_HOST=DGX-SPARK-ETH

REM ComfyUI: local 11002 -> remote 8188 (DGX Spark ComfyUI)
start /b ssh -L 11002:localhost:8188 %REMOTE_USER%@%REMOTE_HOST% -N

REM Optional: LLM tunnel if you also want to point example 04 at the DGX llama.cpp server.
REM Uncomment to enable.
REM start /b ssh -L 11003:localhost:8092 %REMOTE_USER%@%REMOTE_HOST% -N

echo DGX Spark tunnels for example 04 are now active (ComfyUI on local 11002).
echo Leave this window open while the example is running.
pause
