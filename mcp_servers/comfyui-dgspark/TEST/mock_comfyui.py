import uvicorn
from starlette.applications import Starlette
from starlette.responses import JSONResponse, Response
from starlette.routing import Route, WebSocketRoute
from starlette.websockets import WebSocket
import asyncio
import json
import uuid
import sys

# Store history
history = {}
clients = set()

async def notify_clients(prompt_id):
    await asyncio.sleep(0.5) # Simulate processing time
    msg = {
        "type": "executing",
        "data": {
            "node": None,
            "prompt_id": prompt_id
        }
    }
    print(f"Mock: Sending completion for {prompt_id} to {len(clients)} clients")
    for client in list(clients):
        try:
            await client.send_text(json.dumps(msg))
        except:
            pass

async def prompt(request):
    data = await request.json()
    prompt_id = str(uuid.uuid4())
    print(f"Mock: Received prompt request. Generated ID: {prompt_id}")
    
    # We need to find the output node to mock the history correctly.
    # But for now, let's just assume we return some dummy outputs.
    # The MCP server looks for 'outputs' in history[prompt_id].
    history[prompt_id] = {
        "outputs": {
            "9": { 
                "images": [{"filename": "dummy.png", "subfolder": "", "type": "output"}]
            }
        }
    }
    
    asyncio.create_task(notify_clients(prompt_id))
    
    return JSONResponse({"prompt_id": prompt_id})

async def get_history(request):
    prompt_id = request.path_params['prompt_id']
    if prompt_id in history:
        return JSONResponse({prompt_id: history[prompt_id]})
    return JSONResponse({}, status_code=404)

async def view(request):
    # Minimal 1x1 transparent PNG
    dummy_png = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82'
    return Response(dummy_png, media_type="image/png")

async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    clients.add(websocket)
    print("Mock: Client connected to WebSocket")
    try:
        while True:
            await websocket.receive_text()
    except:
        clients.remove(websocket)
        print("Mock: Client disconnected from WebSocket")

app = Starlette(debug=True, routes=[
    Route('/prompt', prompt, methods=['POST']),
    Route('/history/{prompt_id}', get_history, methods=['GET']),
    Route('/view', view, methods=['GET']),
    WebSocketRoute('/ws', websocket_endpoint),
])

if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8188
    print(f"Starting Mock Server on port {port}")
    uvicorn.run(app, host="127.0.0.1", port=port)
