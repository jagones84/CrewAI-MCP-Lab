from mcp.server.fastmcp import FastMCP
import os

mcp = FastMCP("ComfyUI")

@mcp.tool()
def list_workflows() -> list[str]:
    return ["default_workflow.json", "test_workflow.json"]

@mcp.tool()
def generate_image(workflow_name: str, prompt: str, negative_prompt: str = "", seed: int = None, output_path: str = None) -> str:
    print(f"MOCK: Generating image with workflow {workflow_name} for prompt: {prompt}")
    
    if output_path:
        # Check if output_path is a directory or looks like one (no extension)
        # Or if it exists as a directory
        if os.path.isdir(output_path) or (not os.path.splitext(output_path)[1]):
            os.makedirs(output_path, exist_ok=True)
            output_path = os.path.join(output_path, "mock_generated_image.png")
        else:
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # Write dummy image data (red pixel)
        # 1x1 GIF
        dummy_data = b'\x47\x49\x46\x38\x39\x61\x01\x00\x01\x00\x80\x00\x00\xFF\x00\x00\x00\x00\x00\x21\xF9\x04\x01\x00\x00\x00\x00\x2C\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02\x44\x01\x00\x3B'
        
        try:
            with open(output_path, 'wb') as f:
                f.write(dummy_data)
            return f"Generated and saved to: {output_path}"
        except Exception as e:
            return f"Failed to save mock image: {e}"
            
    return "MOCK: Workflow executed (no output path provided)"

if __name__ == "__main__":
    mcp.run()
