import os
from crewai import Agent, LLM
from typing import List, Any

class MarketingAgents:
    """
    Agents for the Marketing Strategy Crew.
    """
    def __init__(self, config: dict):
        """
        Initialize agents with configuration.
        
        Args:
            config (dict): Configuration dictionary loaded from preferences.yaml
        """
        self.config = config
        
        # Extract LLM config
        llm_root = config.get('llm', {})
        provider = llm_root.get('provider', 'openai')
        
        # Get provider specific config
        provider_config = llm_root.get(provider, {})
        # Fallback to root level if not found in provider dict (for backward compatibility)
        model = provider_config.get('model', llm_root.get('model', 'gpt-4o'))
        base_url = provider_config.get('base_url', llm_root.get('base_url'))
        
        # Handle OpenRouter/OpenAI/Ollama prefixing logic
        api_key = os.getenv("OPENAI_API_KEY")
        
        if provider == 'ollama':
            full_model_path = f"ollama/{model}"
            api_key = "NA" # Ollama doesn't need a key
        elif provider == 'llamacpp':
             # Treat LlamaCpp as OpenAI compatible
             full_model_path = f"openai/{model}"
             if not base_url:
                 base_url = "http://localhost:8080/v1"
             api_key = "NA" # LlamaCpp usually doesn't need a key
        elif provider == 'openrouter':
             full_model_path = f"openrouter/{model}"
             # OpenRouter uses OPENAI_API_KEY if not specified otherwise in CrewAI, 
             # but let's be explicit if we can, or rely on env.
             # CrewAI's LLM usually picks up OPENAI_API_KEY for openrouter if configured.
        elif provider == 'openai':
             full_model_path = model 
             # Check if key is actually OpenRouter
             if api_key and api_key.startswith("sk-or-v1"):
                 print("WARNING: OpenRouter key detected but provider is 'openai'. Switching to 'openrouter'.")
                 full_model_path = f"openrouter/{model}"
                 provider = 'openrouter'
        else:
             full_model_path = model

        print(f"DEBUG: Initializing Agents with model: {full_model_path}, provider: {provider}, base_url: {base_url}")
        
        self.llm = LLM(
            model=full_model_path,
            api_key=api_key,
            base_url=base_url
        )

    def market_researcher(self, tools: List[Any]) -> Agent:
        """
        Creates the Market Researcher agent.
        
        Args:
            tools (List[Any]): List of MCP tools (e.g., DuckDuckGo).
        """
        return Agent(
            role='Senior Market Researcher',
            goal='Conduct deep research on the product domain and competitors',
            backstory='Expert in digital market analysis, capable of finding trends and competitor strategies.',
            tools=tools,
            llm=self.llm,
            verbose=True
        )

    def creative_strategist(self) -> Agent:
        """
        Creates the Creative Strategist agent.
        """
        return Agent(
            role='Creative Marketing Strategist',
            goal='Develop a comprehensive marketing campaign and taglines',
            backstory='Award-winning marketing strategist known for catchy taglines and solid go-to-market plans.',
            llm=self.llm,
            verbose=True
        )

    def visual_designer(self, tools: List[Any]) -> Agent:
        """
        Creates the Visual Designer agent.
        
        Args:
            tools (List[Any]): List of MCP tools (e.g., ComfyUI).
        """
        return Agent(
            role='AI Visual Designer',
            goal='Create a visual concept image for the campaign',
            backstory='Expert in prompting AI image generators to create stunning visuals.',
            tools=tools,
            llm=self.llm,
            verbose=True
        )
