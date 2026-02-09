# Troubleshooting Guide: Fixing YouTube Download Issues

If the transcription tool stops working (e.g., stuck in a loop, `403 Forbidden` errors, or "All strategies failed"), follow these steps to fix it.

## 1. Update yt-dlp
YouTube frequently changes its API. The most common fix is updating the `yt-dlp` package.
```bash
python -m pip install -U yt-dlp
```

## 2. Check Extractor Arguments
If you get `403 Forbidden` errors even after updating, the player client might be blocked. In [transcribe.py](file:///f:/MCP/AUDIO/MCP/yt-whisper/transcribe.py), check the `cmd` list:
- **Current working config:** `--extractor-args "youtube:player_client=android,web"`
- **Fallback 1:** Try removing `android` or using `ios`.
- **Fallback 2:** Try adding `--po-token` if YouTube starts requiring Proof of Origin tokens.

## 3. Verify MCP Environment
When running through MCP, the environment might differ from your terminal.
- **Python Executable:** The script uses `sys.executable` to ensure it uses the same environment where `yt-dlp` is installed.
- **Path Issues:** If the tool isn't found, ensure [server.py](file:///f:/MCP/AUDIO/MCP/yt-whisper/server.py) is adding the current directory to `sys.path`.

## 4. Debugging with `mcp_test.py`
Before restarting the MCP server, always run:
```bash
python mcp_test.py
```
If this works but the MCP tool fails, the issue is likely:
1. The MCP server needs a restart.
2. The MCP environment doesn't have the same permissions/access as your terminal.

## 5. Cookies
If all else fails, export your YouTube cookies to a `cookies.txt` file in the project root. The script is configured to look for it automatically.
- Use a browser extension like "Get cookies.txt LOCALLY" (Chrome/Firefox).
- Save it as `F:\MCP\AUDIO\MCP\yt-whisper\cookies.txt`.

## 6. GPU/CUDA Issues
If transcription is extremely slow or "stuck" after the download finishes:
- Verify CUDA: `python -c "import torch; print(torch.cuda.is_available())"`
- If `False`, reinstall PyTorch with CUDA support:
  ```bash
  pip install torch --index-url https://download.pytorch.org/whl/cu124
  ```
