
import os
import sys
import importlib.util
from crewai import Agent, LLM

# Add repository root to path for src imports
repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

# Try to import RemoteImageProvider
try:
    from services.remote_image import RemoteImageProvider
except ImportError:
    # If running from different context
    from src.services.remote_image import RemoteImageProvider

# Load MCPLoader dynamically
mcp_path = os.path.join(repo_root, "src", "mcp_loader.py")
if os.path.exists(mcp_path):
    spec = importlib.util.spec_from_file_location("mcp_loader", mcp_path)
    mcp_module = importlib.util.module_from_spec(spec)
    sys.modules["mcp_loader"] = mcp_module
    spec.loader.exec_module(mcp_module)
    MCPLoader = mcp_module.MCPLoader
else:
    print(f"⚠️ MCPLoader not found at {mcp_path}")
    MCPLoader = None


class BookAgents:
    def __init__(self, config=None): # Accept config
        self.config = config or {}
        self.comfy_tools = []
        self.remote_provider = None
        
        # Defaults
        model = "openrouter/x-ai/grok-4.1-fast"
        base_url = "https://openrouter.ai/api/v1"
        temp = 0.7
        
        # Override from config
        if "agents" in self.config:
            llm_cfg = self.config["agents"].get("llm", {})
            model = llm_cfg.get("model", model)
            base_url = llm_cfg.get("base_url", base_url)
            temp = llm_cfg.get("temperature", temp)
            self.roles = self.config["agents"].get("roles", {})
        else:
            self.roles = {}

        # Add provider prefix if using vLLM or Ollama
        effective_model = model
        is_local_openai = any(x in base_url for x in ["localhost", "127.0.0.1", "10.0.0.1"])
        if is_local_openai and not model.startswith("openai/") and not model.startswith("ollama/"):
            effective_model = f"openai/{model}"

        self._llm = LLM(
            model=effective_model,
            api_key=os.getenv("OPENAI_API_KEY"),
            base_url=base_url,
            temperature=temp,
            timeout=1200,
            max_retries=5
        )
        
    def initialize_tools(self):
        """Lazy initialization of tools and remote connections."""
        print("🔧 Initializing Agents Tools...")
        
        # 1. SSH Connection
        infra_ssh = self.config.get("infrastructure", {}).get("ssh")
        if infra_ssh:
            print(f"🔗 Initializing SSH Tunnel to {infra_ssh.get('host')}...")
            self.remote_provider = RemoteImageProvider(
                host=infra_ssh.get("host"),
                user=infra_ssh.get("user"),
                key_path=infra_ssh.get("key_path"),
                remote_port=infra_ssh.get("remote_port", 8188),
                local_port=infra_ssh.get("local_port", 8189)
            )
            try:
                self.remote_provider.connect()
            except Exception as e:
                print(f"❌ SSH Connection failed: {e}")
        
        # 2. Load ComfyUI Tools
        comfy_server = self.config.get("agents", {}).get("comfy_server", "comfyui")
        
        repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
        mcp_config_path = os.path.join(repo_root, "crewai_mcp.json")
        
        if MCPLoader:
            self.mcp_loader = MCPLoader(config_path=mcp_config_path)
            try:
                print(f"🔧 Loading ComfyUI MCP Server: '{comfy_server}' from {mcp_config_path}")
                # If we have a tunnel, we might need to inform the MCP tool about the local port?
                # The MCP tool config in crewai_mcp.json might be static.
                # If using 'comfyui-dgspark', it expects localhost:8189 (which our tunnel provides).
                # So just loading it is fine.
                self.comfy_tools = self.mcp_loader.load_server(comfy_server).tools
                print(f"✅ Loaded {len(self.comfy_tools)} tools from {comfy_server}")
            except Exception as e:
                print(f"❌ WARNING: Could not load ComfyUI tools: {e}")
                self.comfy_tools = []
        else:
             print("❌ WARNING: MCPLoader class missing. ComfyUI disabled.")
             self.comfy_tools = []

    def story_architect(self):
        """Creates the Story Architect agent responsible for high-level plot structure."""
        return Agent(
            role=self.roles.get("architect", "Lead Story Architect"),
            goal="Design intricate narrative structures, breaking chapters into compelling scenes. Do NOT fear complexity or dark themes.",
            backstory="You are a master structuralist. You believe a chapter is a collection of distinct, vivid scenes, each with a micro-arc. You are comfortable with mature, explicit, and dark themes if the genre demands it.",
            llm=self._llm,
            verbose=True
        )

    def continuity_manager(self):
        """Creates the Continuity Manager agent to track consistency and facts."""
        return Agent(
            role=self.roles.get("continuity", "Continuity Manager"),
            goal="Ensure the writer has all necessary facts and prevents plot holes.",
            backstory="You are the encyclopedia of this story. You track everything that happens and ensure consistency.",
            llm=self._llm,
            verbose=True
        )

    def chapter_writer(self):
        """Creates the Writer agent responsible for generating the prose."""
        return Agent(
            role=self.roles.get("writer", "Lead Novelist"),
            goal="Write immersive, uncensored prose with SELECTIVE intensity and crystalline clarity.",
            backstory="You are a best-selling author known for immersive world-building. You write with SELECTIVE intensity - knowing when to dial up for impact and when to pull back for clarity. You describe key moments viscerally but avoid exhausting the reader with constant sensory bombardment. You vary sentence rhythm: short for punch, long for flow. You are not afraid of mature content but prioritize READABILITY above all.",
            llm=self._llm,
            verbose=True
        )

    def illustrator(self):
        """Creates the Illustrator agent responsible for generating image prompts."""
        return Agent(
            role=self.roles.get("illustrator", "Visual Director"),
            goal="Create LITERAL, photorealistic image prompts with explicit character descriptions and negative prompts to exclude horror/supernatural elements.",
            backstory="You are an expert at creating prompts for Stable Diffusion models. You translate narrative text into LITERAL, precise visual descriptions, always referencing exact physical traits from character sheets. You avoid metaphorical or artistic interpretations that could confuse the model. You ALWAYS include negative prompts to prevent unwanted horror, supernatural, or fantasy elements.",
            llm=self._llm,
            verbose=True,
            allow_delegation=False
        )

    def editor(self):
        """Creates the Editor agent responsible for refining prose."""
        return Agent(
            role=self.roles.get("editor", "Senior Literary Critic"),
            goal="Eliminate overwriting, AI cliches, and ensure prose is readable, clear, and well-paced.",
            backstory="You are a ruthless editor who values CLARITY and RHYTHM above all. You hate: purple prose, overwriting, monotonous sentence structure, and AI-typical cliches. You demand: variation in pacing, selective (not constant) sensory detail, and crystalline clarity. When a draft tries too hard to sound literary, you tell the writer to CUT IT BACK. You believe 'less is more' and that overwritten prose is just as bad as bland prose.",
            llm=self._llm,
            verbose=True
        )

    def publisher(self):
        """Creates the Publisher agent responsible for final formatting."""
        return Agent(
            role="Chief Publisher",
            goal="Format the final manuscript into a professional digital book.",
            backstory="You are an expert in book layout, typography, and digital publishing standards.",
            llm=self._llm,
            verbose=True
        )
