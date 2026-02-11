import sys
import os

repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.append(repo_root)
sys.path.append(os.path.join(repo_root, "examples", "09_marketing_strategy", "src"))

def test_imports():
    try:
        import crewai
        print("crewai imported")
        import mcp
        print("mcp imported")
        from src.mcp_loader import MCPLoader
        print("MCPLoader imported")
        from agents import MarketingAgents
        print("MarketingAgents imported")
        from tasks import MarketingTasks
        print("MarketingTasks imported")
    except ImportError as e:
        print(f"ImportError: {e}")
        sys.exit(1)

if __name__ == "__main__":
    test_imports()
